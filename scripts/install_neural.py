"""Download public, Apache-2.0 LLMLingua-2 BERT weights into an isolated optional runtime."""

import json
from pathlib import Path
from huggingface_hub import snapshot_download

root = (
    Path.home() / ".local/share/codex-economy/experimental/models/llmlingua-2-bert-base-multilingual-cased-meetingbank"
)
location = snapshot_download(
    "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
    local_dir=root,
    allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "README.md"],
    max_workers=2,
)
print(json.dumps({"model": location, "source": "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"}))
