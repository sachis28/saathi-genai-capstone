"""OCR ingestion: scanned policy endorsements -> Blob Storage -> AI Search indexer + OCR skill -> main index.

Some policy paperwork only exists as scans or photos (signed endorsements, stamped letters).
There is no text to search in an image, so the Azure AI Search OCR skill reads the words out
of the picture first. The indexer then embeds that text and writes it into the SAME index the
app searches (AZURE_SEARCH_INDEX_NAME), with the usual source_id / clause_id / product / tier /
version fields, so Saathi can cite a scanned clause like any typed one.

    python rag/azure/ocr_pipeline.py render   # draw the sample scans into rag/corpus/scanned/ (already committed)
    python rag/azure/ocr_pipeline.py all      # upload scans, create data source + skillset + indexer, run, verify

Env vars (same .env as ingest.py, plus storage):
    AZURE_STORAGE_CONNECTION_STRING   Blob Storage account (portal: Storage account -> Access keys)
    AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_ADMIN_KEY, AZURE_SEARCH_INDEX_NAME
    AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_EMBED_DEPLOYMENT
    optional: AZURE_OPENAI_RESOURCE_URL (https://<name>.openai.azure.com, if the endpoint above is a Foundry URL),
              AZURE_OPENAI_EMBED_MODEL (default text-embedding-3-small),
              AZURE_AI_SERVICES_KEY (needed only beyond the free 20 OCR images per indexer per day),
              OCR_CONTAINER (default saathi-scans)
"""
import json
import os
import random
import sys
import time
from pathlib import Path

# Paths: the repo root, the folder with the scan images, and the manifest describing them.
ROOT = Path(__file__).resolve().parents[2]
SCAN_DIR = ROOT / "rag" / "corpus" / "scanned"
MANIFEST = SCAN_DIR / "scans.json"
# Every Azure object this script creates (data source, skillset, indexer) starts with this name.
PREFIX = "saathi-ocr"

# Clauses that exist ONLY as scans, so a cited answer to these questions proves OCR worked.
SCANS = [
    {
        "file": "endorsement_health_gold_air_ambulance.png",
        "source_id": "SCAN-HEALTH-GOLD-END-17", "clause_id": "CL-AIR-01",
        "product": "Health", "tier": "Gold", "version": "v1",
        "title": "POLICY ENDORSEMENT E-17  |  HEALTH GOLD",
        "text": ("Air ambulance transfer to the nearest network hospital is covered up to INR 2.5 lakh "
                 "per policy year when the treating doctor advises it in writing."),
        "question": "Is air ambulance covered for Health Gold?",
    },
    {
        "file": "endorsement_motor_gold_key_replacement.png",
        "source_id": "SCAN-MOTOR-GOLD-END-22", "clause_id": "CL-KEY-01",
        "product": "Motor", "tier": "Gold", "version": "v1",
        "title": "POLICY ENDORSEMENT E-22  |  MOTOR GOLD",
        "text": ("Replacement of lost or stolen car keys, including the lock reset, is covered up to "
                 "INR 15,000 once per policy year. A police report is required for stolen keys."),
        "question": "Is car key replacement covered for Motor Gold?",
    },
]


# ---------- 1. Sample scans ----------

def render() -> None:
    """Draw each endorsement as a slightly rotated, noisy 'scanned' page."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    import textwrap

    # Use a real TTF font if the machine has it, otherwise Pillow's built-in font.
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        title_font, body_font, small = (ImageFont.truetype(font_path, s) for s in (34, 30, 22))
    except OSError:
        title_font = body_font = small = ImageFont.load_default(size=30)

    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    # Fixed random seed, so the "noise" on each scan is the same every time we render.
    rng = random.Random(42)
    for scan in SCANS:
        # A light-grey 1400x900 greyscale page ("L" mode = one brightness value per pixel).
        page = Image.new("L", (1400, 900), 246)
        d = ImageDraw.Draw(page)
        d.text((80, 60), "SAATHI GENERAL INSURANCE (SYNTHETIC)", font=small, fill=60)
        d.text((80, 110), scan["title"], font=title_font, fill=20)
        d.line((80, 170, 1320, 170), fill=40, width=3)
        y = 220
        for line in textwrap.wrap(scan["text"], width=62):
            d.text((80, y), line, font=body_font, fill=25)
            y += 52
        d.text((80, y + 40), f"Ref: {scan['source_id']} / {scan['clause_id']}   Version {scan['version']}", font=small, fill=70)
        d.text((80, 800), "Authorised signatory  ____________________", font=small, fill=70)
        for _ in range(2500):  # scanner speckle
            x, yy = rng.randrange(1400), rng.randrange(900)
            page.putpixel((x, yy), rng.choice((150, 200, 255)))
        # Tilt and blur the page slightly so it looks like a real scan, which makes OCR do real work.
        page = page.rotate(1.2, expand=False, fillcolor=246).filter(ImageFilter.GaussianBlur(0.6))
        page.save(SCAN_DIR / scan["file"])
    # Save the metadata for each scan next to the images; upload() reads this file.
    MANIFEST.write_text(json.dumps([{k: v for k, v in s.items()} for s in SCANS], indent=1), encoding="utf-8")
    print(f"Wrote {len(SCANS)} scans to {SCAN_DIR}")


# ---------- 2. Azure definitions ----------

# Read a required setting from the environment, or stop with a clear message.
def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        sys.exit(f"Missing environment variable {name}")
    return value.strip()


# The embedding skill needs the classic https://<name>.openai.azure.com URL, without /openai/v1.
def openai_resource_url() -> str:
    url = os.getenv("AZURE_OPENAI_RESOURCE_URL") or os.getenv("AZURE_OPENAI_ENDPOINT", "")
    url = url.strip().rstrip("/")
    return url[: -len("/openai/v1")] if url.endswith("/openai/v1") else url


# An Azure AI Search "skillset" is a mini pipeline that runs on every document the indexer reads.
# Ours has three skills: OCR (image -> text), Merge (add that text to the document), Embed (text -> vector).
def build_definitions(index_name: str, container: str, connection_string: str):
    """Data source, skillset (OCR -> merge -> embed) and indexer. No network calls."""
    from azure.search.documents.indexes.models import (
        AzureOpenAIEmbeddingSkill, CognitiveServicesAccountKey, FieldMapping, FieldMappingFunction,
        IndexingParameters, IndexingParametersConfiguration, InputFieldMappingEntry, MergeSkill, OcrSkill,
        OutputFieldMappingEntry, SearchIndexer, SearchIndexerDataContainer, SearchIndexerDataSourceConnection,
        SearchIndexerSkillset,
    )

    # Data source: tells the indexer to read files from our Blob Storage container.
    data_source = SearchIndexerDataSourceConnection(
        name=f"{PREFIX}-blob", type="azureblob", connection_string=connection_string,
        container=SearchIndexerDataContainer(name=container))

    # Skill 1, OCR: reads the printed words from every image Azure extracted from the file.
    ocr = OcrSkill(
        name="ocr", description="Read the printed words out of each scanned page",
        context="/document/normalized_images/*", default_language_code="en", should_detect_orientation=True,
        inputs=[InputFieldMappingEntry(name="image", source="/document/normalized_images/*")],
        outputs=[OutputFieldMappingEntry(name="text", target_name="text")])
    # Skill 2, Merge: inserts the OCR text into the document's own text at the right offsets.
    merge = MergeSkill(
        name="merge", description="Put the OCR text back into the document text", context="/document",
        inputs=[InputFieldMappingEntry(name="text", source="/document/content"),
                InputFieldMappingEntry(name="itemsToInsert", source="/document/normalized_images/*/text"),
                InputFieldMappingEntry(name="offsets", source="/document/normalized_images/*/contentOffset")],
        outputs=[OutputFieldMappingEntry(name="mergedText", target_name="merged_text")])
    # Skill 3, Embed: turns the merged text into a 1536-number vector, same model as the typed clauses,
    # so vector search treats scanned and typed clauses the same way.
    embed = AzureOpenAIEmbeddingSkill(
        name="embed", description="Same embedding model as the typed clauses", context="/document",
        resource_url=openai_resource_url(), deployment_name=os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "").strip(),
        model_name=os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-3-small"), dimensions=1536,
        api_key=os.getenv("AZURE_OPENAI_API_KEY", "").strip(),
        inputs=[InputFieldMappingEntry(name="text", source="/document/merged_text")],
        outputs=[OutputFieldMappingEntry(name="embedding", target_name="embedding")])
    # Beyond the free 20 images per day, OCR is billed to an Azure AI services key.
    services_key = os.getenv("AZURE_AI_SERVICES_KEY")
    skillset = SearchIndexerSkillset(
        name=f"{PREFIX}-skillset", description="OCR for scanned policy endorsements", skills=[ocr, merge, embed],
        cognitive_services_account=CognitiveServicesAccountKey(key=services_key.strip()) if services_key else None)

    # Indexer: the job that reads the data source, runs the skillset, and writes into OUR main index.
    indexer = SearchIndexer(
        name=f"{PREFIX}-indexer", data_source_name=data_source.name, target_index_name=index_name,
        skillset_name=skillset.name,
        field_mappings=[
            # Map file properties into index fields. The blob path, base64-encoded, becomes the unique document id.
            FieldMapping(source_field_name="metadata_storage_path", target_field_name="id",
                         mapping_function=FieldMappingFunction(name="base64Encode")),
            # source_id, clause_id, product, tier and version come from the blob metadata set in upload().
            *(FieldMapping(source_field_name=f, target_field_name=f)
              for f in ("source_id", "clause_id", "product", "tier", "version")),
        ],
        # Map skill outputs into index fields: OCR text -> "text", vector -> "embedding".
        output_field_mappings=[
            FieldMapping(source_field_name="/document/merged_text", target_field_name="text"),
            FieldMapping(source_field_name="/document/embedding", target_field_name="embedding"),
        ],
        # generateNormalizedImages = pull images out of each file so the OCR skill can read them.
        parameters=IndexingParameters(configuration=IndexingParametersConfiguration(
            data_to_extract="contentAndMetadata", image_action="generateNormalizedImages", parsing_mode="default")))
    return data_source, skillset, indexer


# ---------- 3. Run it ----------

# Upload each scan image to Blob Storage, with its citation fields attached as blob metadata.
def upload(container: str, connection_string: str) -> None:
    from azure.storage.blob import BlobServiceClient
    service = BlobServiceClient.from_connection_string(connection_string)
    client = service.get_container_client(container)
    if not client.exists():
        client.create_container()
    for scan in json.loads(MANIFEST.read_text(encoding="utf-8")):
        metadata = {k: scan[k] for k in ("source_id", "clause_id", "product", "tier", "version")}
        with open(SCAN_DIR / scan["file"], "rb") as fh:
            client.upload_blob(scan["file"], fh, overwrite=True, metadata=metadata)
        print(f"Uploaded {scan['file']}  ({scan['source_id']}#{scan['clause_id']})")


# The full run: upload scans, create or update the three Azure objects, run the indexer, verify.
def setup_and_run() -> None:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes import SearchIndexerClient

    index_name = env("AZURE_SEARCH_INDEX_NAME")
    container = env("OCR_CONTAINER", "saathi-scans")
    connection_string = env("AZURE_STORAGE_CONNECTION_STRING")
    upload(container, connection_string)

    client = SearchIndexerClient(env("AZURE_SEARCH_ENDPOINT"), AzureKeyCredential(env("AZURE_SEARCH_ADMIN_KEY")))
    data_source, skillset, indexer = build_definitions(index_name, container, connection_string)
    client.create_or_update_data_source_connection(data_source)
    client.create_or_update_skillset(skillset)
    client.create_or_update_indexer(indexer)
    # reset + run = process every blob again, even ones the indexer has seen before.
    client.reset_indexer(indexer.name)
    client.run_indexer(indexer.name)
    print(f"Indexer {indexer.name} started; waiting for it to finish...")

    # Poll every 5 seconds, for up to 5 minutes, until the indexer finishes.
    for _ in range(60):
        time.sleep(5)
        status = client.get_indexer_status(indexer.name).last_result
        if status and status.status in ("success", "transientFailure", "persistentFailure"):
            print(f"Indexer {status.status}: {status.item_count} processed, {status.failed_item_count} failed")
            for err in (status.errors or [])[:5]:
                print("  error:", err.error_message)
            break
    # This "else" belongs to the for loop: it runs only if we never hit "break" (still running).
    else:
        print("Still running; check AI Search -> Indexers -> saathi-ocr-indexer in the portal.")
    verify(index_name)


def verify(index_name: str) -> None:
    """Show the OCR text that landed in the main index for each scan."""
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    search = SearchClient(env("AZURE_SEARCH_ENDPOINT"), index_name, AzureKeyCredential(env("AZURE_SEARCH_ADMIN_KEY")))
    # Look up each scan's clause in the index by source_id and show the OCR text that was stored.
    for scan in SCANS:
        rows = list(search.search(search_text="*", filter=f"source_id eq '{scan['source_id']}'",
                                  select=["source_id", "clause_id", "text"], top=1))
        if rows:
            print(f"OK  {scan['source_id']}#{scan['clause_id']}: {rows[0]['text'][:120]!r}")
            print(f"    try in Saathi: {scan['question']}")
        else:
            print(f"MISSING  {scan['source_id']} not in {index_name} yet")


# Command line entry point: render | all | verify.
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    if command == "render":
        render()
    elif command == "all":
        setup_and_run()
    elif command == "verify":
        verify(env("AZURE_SEARCH_INDEX_NAME"))
    else:
        sys.exit("Usage: python rag/azure/ocr_pipeline.py [render|all|verify]")
