"""OCR pipeline tests (no Azure calls): scans are committed, the skillset runs OCR -> merge -> embed,
and the indexer writes into the main index with the citation fields."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ocr_pipeline", ROOT / "rag" / "azure" / "ocr_pipeline.py")
ocr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ocr)


def test_sample_scans_are_committed():
    for scan in json.loads(ocr.MANIFEST.read_text(encoding="utf-8")):
        assert (ocr.SCAN_DIR / scan["file"]).stat().st_size > 10_000


def test_skillset_runs_ocr_then_merge_then_embedding():
    _, skillset, _ = ocr.build_definitions("insurance-index", "saathi-scans", "UseDevelopmentStorage=true")
    kinds = [s.as_dict()["@odata.type"] for s in skillset.skills]
    assert kinds == ["#Microsoft.Skills.Vision.OcrSkill", "#Microsoft.Skills.Text.MergeSkill",
                     "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill"]


def test_indexer_writes_into_the_main_index_with_citation_fields():
    _, _, indexer = ocr.build_definitions("insurance-index", "saathi-scans", "UseDevelopmentStorage=true")
    assert indexer.target_index_name == "insurance-index"
    targets = {m.target_field_name for m in indexer.field_mappings + indexer.output_field_mappings}
    assert {"id", "source_id", "clause_id", "product", "tier", "version", "text", "embedding"} <= targets
    assert indexer.parameters.configuration.image_action == "generateNormalizedImages"
