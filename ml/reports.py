"""Build reports only from measured local artifacts; missing work stays pending."""
import json
import shutil
import xml.etree.ElementTree as ET

from ml.common import ARTIFACTS, DOCS, LABELS, ROOT, write_json


def main():
    DOCS.mkdir(exist_ok=True)
    evidence = DOCS / "evidence"
    evidence.mkdir(exist_ok=True)
    lines = ["# Intent classification experiment", "", "Owner: Sairaj. Seed: 42. All inputs are synthetic ML fixtures, not Sachi's approved CRM data. Labels are a proposed integration contract pending team review.",
        "", "Dataset: 1,000 training rows, 200 development rows and 150 locked test rows. Template families are assigned before expansion. There is no normalized text or family overlap; entities and insurance vocabulary recur. CSV SHA-256 hashes are stored in data/generated/manifest.json. Test labels are versioned for audit; the hash lock detects edits but is not access control.",
        "", "Model selection uses development macro F1 only. Test results are reported after selecting the checkpoint. No test-driven retuning is performed in this version. The five proposed labels are: "+", ".join(LABELS)+".",
        "", "| Model | Test macro F1 | Best/selected dev macro F1 | Target | Result |", "|---|---:|---:|---|---|"]
    models = {}
    for name in ["tfidf_lr","mini_transformer","hf_zero_shot","distilbert"]:
        path = ARTIFACTS / name / "metrics.json"
        if not path.exists():
            lines.append(f"| {name} | — | — | {'≥ 0.75' if name=='distilbert' else 'Record baseline'} | Not run |")
            continue
        metrics = json.loads(path.read_text(encoding="utf-8"))
        models[name] = metrics
        write_json(evidence / f"{name}_metrics.json",metrics)
        for filename in ["predictions.csv","history.json","selection.json"]:
            if (path.parent / filename).exists():
                shutil.copy2(path.parent / filename,evidence / f"{name}_{filename}")
        score = metrics["macro_f1"]
        dev = metrics["metadata"].get("best_dev_macro_f1",metrics["metadata"].get("dev_macro_f1"))
        devtext = f"{dev:.4f}" if dev is not None else "N/A"
        target = "≥ 0.75" if name=="distilbert" else "Record baseline"
        status = ("Met on synthetic holdout" if score>=0.75 else "NOT MET") if name=="distilbert" else "Measured"
        lines.append(f"| {name} | {score:.4f} | {devtext} | {target} | {status} |")
    for name,metrics in models.items():
        lines += ["", f"## {name}", "", "Confusion matrix: rows are true labels, columns are predicted labels.", "",
                  "| True / predicted | "+" | ".join(LABELS)+" |", "|---|"+"---:|"*len(LABELS)]
        for label,row in zip(LABELS,metrics["confusion_matrix"]):
            lines.append("| "+label+" | "+" | ".join(map(str,row))+" |")
        lines += ["", "Run metadata", "", "```json", json.dumps(metrics["metadata"],indent=2), "```"]
    lines += ["", "## Interpretation and limitations", "", "Low baseline and mini-Transformer results on held-out sentence families expose vocabulary memorization. These are measured failures, not reasons to adjust the locked test set. Production rollout requires independent human-authored questions, domain-reviewed labels, ambiguous/multi-intent cases, multilingual evaluation, calibrated confidence, and an abstention strategy.",
        "", "Intent output is routing assistance only. It does not authorize customer access, prove grounding, or permit sending messages. The API defaults to the locally trained DistilBERT model; INTENT_PROVIDER=tfidf_lr selects the lightweight baseline with its disclosed quality limitation. No production release approval is claimed. The existing /chat answer and citations remain upstream dummy placeholders.",
        "", "The protected-attribute metadata is artificial and not representative. See fairness_report.md for subgroup results and limits. The 50-question intent smoke evaluation is separate from the team's end-to-end RAG evaluation."]
    (DOCS / "experiment_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    radar_path = ARTIFACTS / "radar/metrics.json"
    if radar_path.exists():
        shutil.copy2(radar_path,evidence / "radar_metrics.json")
        shutil.copy2(ARTIFACTS / "radar/top10.json",evidence / "radar_top10.json")
    for relative in ["data_validation.json","fairness.json","intent_acceptance_50/metrics.json","local_api_smoke.json","test_results.xml","dotnet_test_results.trx"]:
        path = ARTIFACTS / relative
        if path.exists():
            shutil.copy2(path,evidence / relative.replace("/","_"))
    distil = models.get("distilbert")
    gate = "NOT RUN" if not distil else "PASS on synthetic holdout" if distil["macro_f1"]>=0.75 else "FAIL"
    test_summary = "Not run"
    if (ARTIFACTS / "test_results.xml").exists():
        suites = list(ET.parse(ARTIFACTS / "test_results.xml").getroot().iter("testsuite"))
        total = sum(int(s.get("tests",0)) for s in suites)
        failed = sum(int(s.get("failures",0))+int(s.get("errors",0)) for s in suites)
        skipped = sum(int(s.get("skipped",0)) for s in suites)
        test_summary = f"{total-failed-skipped} passed, {failed} failed, {skipped} skipped"
    evaluation = ["# Sairaj evaluation and delivery status", "", "Local ML work is implemented. Azure and full-product acceptance are incomplete. No deployed URL, cloud screenshot, team sign-off, or rehearsal is claimed.",
        "", "| Assignment | Evidence | Status |", "|---|---|---|",
        "| Pandera data quality | evidence/data_validation.json; data/validate.py | Local ML fixtures validated; CRM schemas await team |",
        "| 1,000 train / 150 locked test | data/generated/manifest.json | Complete; 200 extra dev rows |",
        "| TF-IDF + Logistic Regression | evidence/tfidf_lr_metrics.json | Measured |",
        "| Mini Transformer | ml/notebooks/mini_transformer.ipynb | Implemented and locally trained |",
        "| HF zero-shot baseline | evidence/hf_zero_shot_metrics.json | "+("Measured" if "hf_zero_shot" in models else "Not run")+" |",
        "| DistilBERT Macro F1 ≥ 0.75 | evidence/distilbert_metrics.json | "+gate+" |",
        "| Fairness report | fairness_report.md | Synthetic subgroup audit; no fairness certification |",
        "| Renewal Radar | evidence/radar_metrics.json; evidence/radar_top10.json | Locally trained and scored |",
        "| Azure ML training/register/deploy | ml/azureml/ | Scripts ready; no Azure account/workspace configured |",
        "| Azure /worklist provider | api/app/services/ml_service.py | Local scoring tested; cloud path tested with mocked HTTP only |",
        "| V1/V2/V3 × 25 cases × 2 models | prompt_experiment.md | Design and runner ready; live Azure/Ollama runs pending |",
        "| 50-query evaluation | evidence/intent_acceptance_50_metrics.json | Intent-only local smoke check; not full RAG acceptance |",
        "| Full-product acceptance, 2 rehearsals, offline demo | team_acceptance.md | Pending team application and participants |",
        "| Local Python test suite | evidence/test_results.xml | "+test_summary+" |",
        "| Real HTTP local API check | evidence/local_api_smoke.json | "+("Passed: DistilBERT intent and 10 local Radar entries" if (ARTIFACTS / "local_api_smoke.json").exists() else "Not run")+" |",
        "| Existing .NET client tests | dotnet/Saathi.slnx | Attempted; no .NET SDK installed, so tests could not run |",
        "", "Reports are generated from actual JSON metrics. Model weights are local under artifacts/ and ignored by Git; recreate them with the documented commands. Small evidence files are included in docs/evidence/ for review.",
        "", "Remaining dependencies: Sachi's approved data/features; Shreya's orchestration, authorization, and policy contracts; Azure subscription/workspace and deployed GPT model; installed Ollama model; Rohan's retrieval gold set; Soham's acceptance workflow."]
    (DOCS / "evaluation_report.md").write_text("\n".join(evaluation)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
