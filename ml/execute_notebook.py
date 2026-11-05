"""Execute the notebook with this Python interpreter, not an unrelated kernel."""
import sys

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient

from ml.common import ROOT


def main():
    path = ROOT / "ml/notebooks/mini_transformer.ipynb"
    notebook = nbformat.read(path,as_version=4)
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable,"-m","ipykernel_launcher","-f","{connection_file}"]
    client = NotebookClient(notebook,km=manager,timeout=120,resources={"metadata":{"path":str(ROOT)}})
    try:
        client.execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    nbformat.validate(notebook)
    nbformat.write(notebook,path)
    print("Executed and validated notebook:",path)


if __name__ == "__main__":
    main()
