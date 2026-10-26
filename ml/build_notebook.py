"""Generate a teaching notebook from the executable, tested Transformer source."""
from pathlib import Path

import nbformat as nbf

from ml.common import ROOT


def main():
    notebook = nbf.v4.new_notebook()
    cells = [
        nbf.v4.new_markdown_cell("# Mini Transformer for Saathi intent classification\n\nSairaj's Day 34 exercise. This encoder classifier is trained from scratch on synthetic intent data. It demonstrates attention; it is not a production language model. The training implementation is shared with `ml/mini_transformer.py` so tests exercise the same code."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport sys\nroot = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'ml' / 'mini_transformer.py').exists())\nif str(root) not in sys.path:\n    sys.path.insert(0, str(root))\nimport torch\nfrom ml.common import ARTIFACTS, LABELS, load_split\nfrom ml.mini_transformer import MultiHeadAttention, MiniTransformer, encode, make_vocab\ntorch.manual_seed(42)\ntorch.set_num_threads(4)\ntrain = load_split('train')\nvocab = make_vocab(train.text)\nprint('Training examples:', len(train), 'Vocabulary:', len(vocab))"),
        nbf.v4.new_markdown_cell("## Scaled dot product attention and multiple heads\n\nEach head computes $\\mathrm{softmax}(QK^T/\\sqrt{d_k})V$. Keys at padding positions receive negative infinity before softmax. Four heads learn separate projections; their outputs are concatenated and projected back to the embedding width."),
        nbf.v4.new_code_cell("import inspect\nprint(inspect.getsource(MultiHeadAttention))\nmodel = MiniTransformer(len(vocab)).eval()\nids = encode(['Compare Silver and Gold for C-204'], vocab)\nwith torch.no_grad():\n    logits, attention = model(ids)\nprint('Logits:', tuple(logits.shape))\nprint('Attention: batch, heads, query, key =', tuple(attention.shape))\nassert torch.all(attention.masked_select(~ids.ne(0)[:, None, None, :]) == 0)\nprint('Padding attention is exactly zero.')"),
        nbf.v4.new_markdown_cell("## Positional encoding and encoder classifier\n\nSinusoidal positions use $PE_{pos,2i}=\\sin(pos/10000^{2i/d})$ and $PE_{pos,2i+1}=\\cos(pos/10000^{2i/d})$. Residual connections, layer normalization, and a feed-forward network form one encoder block. Masked mean pooling feeds a five-class output layer. There is no autoregressive decoder because the task predicts a class, not a generated sequence."),
        nbf.v4.new_code_cell("print(inspect.getsource(MiniTransformer))\nprint('First positions, first eight dimensions:')\nprint(model.position[:4, :8])\nprint('Parameters:', sum(p.numel() for p in model.parameters()))"),
        nbf.v4.new_markdown_cell("## Training and held-out result\n\nRun `python -m ml.mini_transformer` from the project root to reproduce 30 epochs. The vocabulary is fit only on training text, the checkpoint is selected using the development set, and the locked test set is evaluated afterward. Do not tune using the test score; new model iterations need new independent test data."),
        nbf.v4.new_code_cell("import json\nmetrics = json.loads((ARTIFACTS / 'mini_transformer' / 'metrics.json').read_text())\nhistory = json.loads((ARTIFACTS / 'mini_transformer' / 'history.json').read_text())\nprint('Held-out macro F1:', metrics['macro_f1'])\nprint('Best development macro F1:', metrics['metadata']['best_dev_macro_f1'])\nprint('Last epoch:', history[-1])\nprint('Confusion matrix label order:', metrics['label_order'])\nfor row in metrics['confusion_matrix']:\n    print(row)"),
        nbf.v4.new_markdown_cell("## Limitations\n\nTemplate-family holdout is stricter than a random row split, but these sentences are still synthetic. A tiny encoder trained on 1,000 examples may memorize vocabulary and fail on paraphrases. Compare its actual score with TF-IDF, pretrained zero-shot NLI, and fine-tuned DistilBERT in the experiment report. The notebook does not claim real-world accuracy or fairness."),
    ]
    notebook.cells = cells
    notebook.metadata = {"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"}}
    path = ROOT / "ml/notebooks/mini_transformer.ipynb"
    path.parent.mkdir(parents=True,exist_ok=True)
    nbf.write(notebook,path)
    print(path)


if __name__ == "__main__":
    main()
