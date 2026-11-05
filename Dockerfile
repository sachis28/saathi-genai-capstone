# Saathi API (FastAPI). Build from the repo root: az acr build -t saathi-api . (or docker build .)
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app:/app/api HF_HOME=/app/.hf

# CPU-only torch keeps the image ~2 GB smaller than the default CUDA build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt ./
COPY api/requirements.txt api/requirements.txt
COPY ml/azureml/requirements-local.txt ml/azureml/requirements-local.txt
RUN pip install -r api/requirements.txt && pip install -r ml/azureml/requirements-local.txt

COPY . .
# Train the small TF-IDF intent model and the Radar model into /app/artifacts (seconds, deterministic),
# and cache MiniLM so a RETRIEVER=local fallback starts without a download.
RUN python -m ml.train_intent && python -m ml.radar \
 && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

ENV LLM_PROVIDER=mock RETRIEVER=local INTENT_PROVIDER=tfidf_lr ML_PROVIDER=local
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "api", "--host", "0.0.0.0", "--port", "8000"]
