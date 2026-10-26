"""Hugging Face zero-shot NLI and actual pretrained DistilBERT fine-tuning."""
import argparse
import copy
import os
import time

import torch
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

from ml.common import ARTIFACTS, LABELS, SEED, evaluate, load_split, write_json

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
DESCRIPTIONS = {
    "compare_products": "compare insurance products",
    "coverage_question": "ask about insurance coverage or exclusions",
    "renewal_draft": "draft an insurance renewal reminder",
    "customer_lookup": "look up customer information",
    "out_of_scope": "request help unrelated to insurance",
}


class IntentDataset(Dataset):
    def __init__(self, frame, tokenizer):
        self.encoded = tokenizer(frame.text.tolist(),truncation=True,padding="max_length",max_length=48,return_tensors="pt")
        self.labels = torch.tensor([LABELS.index(v) for v in frame.label])

    def __len__(self):
        return len(self.labels)

    def __getitem__(self,i):
        return {**{k:v[i] for k,v in self.encoded.items()},"labels":self.labels[i]}


def predict(model, loader):
    model.eval()
    values = []
    with torch.no_grad():
        for batch in loader:
            values.extend(model(**{k:v for k,v in batch.items() if k!="labels"}).logits.argmax(-1).tolist())
    return [LABELS[i] for i in values]


def distilbert(epochs=3, model_id="distilbert/distilbert-base-uncased"):
    torch.manual_seed(SEED)
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(model_id,num_labels=len(LABELS),
        id2label=dict(enumerate(LABELS)),label2id={v:i for i,v in enumerate(LABELS)})
    train,dev = load_split("train"),load_split("dev")
    loader = DataLoader(IntentDataset(train,tokenizer),batch_size=16,shuffle=True,generator=torch.Generator().manual_seed(SEED))
    devloader = DataLoader(IntentDataset(dev,tokenizer),batch_size=32)
    optimizer = torch.optim.AdamW(model.parameters(),lr=3e-5,weight_decay=0.01)
    best, history, best_state = -1, [], None
    start = time.monotonic()
    for epoch in range(epochs):
        model.train()
        loss_sum = 0
        for step,batch in enumerate(loader):
            optimizer.zero_grad()
            loss = model(**batch).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),1.0)
            optimizer.step()
            loss_sum += loss.item()*len(batch["labels"])
            if step % 20 == 0:
                print(f"DistilBERT epoch {epoch+1}, batch {step+1}/{len(loader)}",flush=True)
        score = float(f1_score(dev.label,predict(model,devloader),average="macro",zero_division=0))
        history.append({"epoch":epoch+1,"train_loss":loss_sum/len(train),"dev_macro_f1":score})
        print(history[-1],flush=True)
        if score > best:
            best,best_state = score,copy.deepcopy(model.state_dict())
    model.load_state_dict(best_state)
    out = ARTIFACTS / "distilbert"
    model.save_pretrained(out)
    tokenizer.save_pretrained(out)
    write_json(out / "history.json",history)
    test = load_split("test")
    return evaluate("distilbert",test,predict(model,DataLoader(IntentDataset(test,tokenizer),batch_size=32)),
        {"model_id":model_id,"revision":getattr(model.config,"_commit_hash",None),"epochs":epochs,"best_dev_macro_f1":best,"selection":"best dev macro F1","training_seconds":time.monotonic()-start,"target_macro_f1":0.75})


def zero_shot(model_id="typeform/distilbert-base-uncased-mnli"):
    torch.set_num_threads(4)
    classifier = pipeline("zero-shot-classification",model=model_id,device=-1)
    test = load_split("test")
    descriptions = list(DESCRIPTIONS.values())
    inverse = {v:k for k,v in DESCRIPTIONS.items()}
    predictions = []
    for i in range(0,len(test),8):
        outputs = classifier(test.text.iloc[i:i+8].tolist(),candidate_labels=descriptions,
            hypothesis_template="The user wants to {}.",multi_label=False,batch_size=16)
        predictions.extend(inverse[out["labels"][0]] for out in outputs)
    return evaluate("hf_zero_shot",test,predictions,{"model_id":model_id,
        "revision":getattr(classifier.model.config,"_commit_hash",None),"label_descriptions":DESCRIPTIONS,
        "hypothesis_template":"The user wants to {}.","fine_tuned_on_saathi":False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode",choices=["distilbert","zero-shot"])
    parser.add_argument("--epochs",type=int,default=3)
    args = parser.parse_args()
    distilbert(args.epochs) if args.mode=="distilbert" else zero_shot()
