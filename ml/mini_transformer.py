"""Explicit attention + sinusoidal positions; no pretrained weights."""
import argparse
import copy
import math
import re
from collections import Counter

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import f1_score

from ml.common import ARTIFACTS, LABELS, SEED, evaluate, load_split, write_json


def tokens(text):
    return re.findall(r"[a-z]+|\d+", text.lower())


def make_vocab(texts):
    counts = Counter(t for text in texts for t in tokens(text))
    return {"<pad>": 0, "<unk>": 1, **{t: i+2 for i,t in enumerate(sorted(counts))}}


def encode(texts, vocab, length=40):
    rows = []
    for text in texts:
        ids = [vocab.get(t, 1) for t in tokens(text)][:length] or [1]
        rows.append(ids + [0]*(length-len(ids)))
    return torch.tensor(rows, dtype=torch.long)


class MultiHeadAttention(nn.Module):
    def __init__(self, width=64, heads=4):
        super().__init__()
        if width % heads:
            raise ValueError("Embedding width must be divisible by heads")
        self.heads, self.dim = heads, width // heads
        self.qkv = nn.Linear(width, width*3)
        self.output = nn.Linear(width, width)

    def forward(self, x, mask):
        batch, length, width = x.shape
        q, k, v = self.qkv(x).reshape(batch, length, 3, self.heads, self.dim).permute(2,0,3,1,4).unbind(0)
        logits = q @ k.transpose(-1,-2) / math.sqrt(self.dim)
        logits = logits.masked_fill(~mask[:,None,None,:], float("-inf"))
        weights = logits.softmax(-1)
        attended = (weights @ v).transpose(1,2).reshape(batch,length,width)
        return self.output(attended), weights


class MiniTransformer(nn.Module):
    def __init__(self, vocab_size, classes=5, width=64, heads=4, length=40):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, width, padding_idx=0)
        position = torch.arange(length).float().unsqueeze(1)
        divisor = torch.exp(torch.arange(0,width,2).float()*(-math.log(10000.0)/width))
        pe = torch.zeros(length,width)
        pe[:,0::2], pe[:,1::2] = torch.sin(position*divisor), torch.cos(position*divisor)
        self.register_buffer("position", pe)
        self.attention = MultiHeadAttention(width,heads)
        self.norm1, self.norm2 = nn.LayerNorm(width), nn.LayerNorm(width)
        self.feedforward = nn.Sequential(nn.Linear(width,128), nn.GELU(), nn.Linear(128,width))
        self.classifier = nn.Linear(width,classes)

    def forward(self, ids):
        mask = ids.ne(0)
        if not mask.any(dim=1).all():
            raise ValueError("Each input must contain a non-padding token")
        x = self.embedding(ids)*math.sqrt(self.embedding.embedding_dim) + self.position[:ids.shape[1]]
        attended, weights = self.attention(x,mask)
        x = self.norm1(x + attended)
        x = self.norm2(x + self.feedforward(x))
        pooled = (x*mask.unsqueeze(-1)).sum(1)/mask.sum(1,keepdim=True)
        return self.classifier(pooled), weights


def train(epochs=30):
    torch.manual_seed(SEED)
    torch.set_num_threads(4)
    train, dev = load_split("train"), load_split("dev")
    vocab = make_vocab(train.text)
    x, y = encode(train.text,vocab), torch.tensor([LABELS.index(v) for v in train.label])
    dx = encode(dev.text,vocab)
    model = MiniTransformer(len(vocab))
    optimizer = torch.optim.AdamW(model.parameters(),lr=0.002,weight_decay=0.01)
    loader = DataLoader(TensorDataset(x,y),batch_size=32,shuffle=True,generator=torch.Generator().manual_seed(SEED))
    history, best_score, best_state = [], -1, None
    for epoch in range(epochs):
        model.train()
        loss_sum = 0
        for batch, targets in loader:
            optimizer.zero_grad()
            logits,_ = model(batch)
            loss = nn.functional.cross_entropy(logits,targets)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),1.0)
            optimizer.step()
            loss_sum += loss.item()*len(batch)
        model.eval()
        with torch.no_grad():
            predictions = [LABELS[i] for i in model(dx)[0].argmax(-1).tolist()]
        score = float(f1_score(dev.label,predictions,average="macro",zero_division=0))
        history.append({"epoch":epoch+1,"loss":loss_sum/len(x),"dev_macro_f1":score})
        if score > best_score:
            best_score,best_state = score,copy.deepcopy(model.state_dict())
    model.load_state_dict(best_state)
    model.eval()
    out = ARTIFACTS / "mini_transformer"
    out.mkdir(parents=True,exist_ok=True)
    torch.save(model.state_dict(),out / "weights.pt")
    write_json(out / "vocab.json",vocab)
    write_json(out / "history.json",history)
    test = load_split("test")
    with torch.no_grad():
        predictions = [LABELS[i] for i in model(encode(test.text,vocab))[0].argmax(-1).tolist()]
    return evaluate("mini_transformer",test,predictions,{"epochs":epochs,"selection":"best dev macro F1", "best_dev_macro_f1":best_score,"parameters":sum(p.numel() for p in model.parameters())})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs",type=int,default=30)
    train(parser.parse_args().epochs)
