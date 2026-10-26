"""One command for a reproducible local workstream. No cloud mutations."""
import argparse
import subprocess
import sys

from ml.common import DATA, ROOT


def main(include_hf=False):
    steps = []
    if not (DATA / "manifest.json").exists():
        steps.append(["data.generate_ml"])
    steps += [["data.validate"],["ml.train_intent"],["ml.mini_transformer"],["ml.radar"],
              ["ml.evaluate_50"],["ml.prompt_experiment"]]
    if include_hf:
        steps += [["ml.hf_models","zero-shot"],["ml.hf_models","distilbert"]]
    steps += [["ml.fairness"],["ml.reports"],["ml.build_notebook"],["ml.execute_notebook"],["pytest","-q"]]
    for arguments in steps:
        print("Running", " ".join(arguments),flush=True)
        subprocess.run([sys.executable,"-m",*arguments],cwd=ROOT,check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-hf",action="store_true")
    main(parser.parse_args().include_hf)
