#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${1:-echomem-test}"

echo "[1/4] Check conda env: ${ENV_NAME}"
conda run -n "${ENV_NAME}" python --version

echo "[2/4] Install memory frameworks into ${ENV_NAME}"
conda run -n "${ENV_NAME}" pip install \
  mem0ai \
  graphiti-core \
  llama_cloud \
  llama-index-core \
  llama-index-llms-ollama \
  llama-index-vector-stores-chroma \
  cognee \
  chromadb

echo "[3/4] Run tests in ${ENV_NAME}"
conda run -n "${ENV_NAME}" python -m unittest discover -s tests -p "test_*.py"

echo "[4/4] Build sample user knowledge map"
conda run -n "${ENV_NAME}" python scripts/build_user_knowledge_map.py --user-id u_test --query "总结用户知识体系"

echo "Done."
