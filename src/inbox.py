import json
import uuid
from datetime import datetime
from pathlib import Path

import storage

INBOX_DIR = storage.DATA_DIR / "inbox"
PENDING_DIR = INBOX_DIR / "pending"
PROCESSING_DIR = INBOX_DIR / "processing"
FAILED_DIR = INBOX_DIR / "failed"


def ensure_dirs() -> None:
    for d in (PENDING_DIR, PROCESSING_DIR, FAILED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def enqueue(image_bytes: bytes, ext: str, mime: str) -> str:
    ensure_dirs()
    job_id = uuid.uuid4().hex[:12]
    (PENDING_DIR / f"{job_id}{ext}").write_bytes(image_bytes)
    sidecar = {
        "id": job_id,
        "ext": ext,
        "mime": mime,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "attempts": 0,
    }
    # Sidecar appearing in pending/ is the worker's "ready" signal, so write it
    # last and rename atomically — image bytes are already on disk by then.
    tmp = PENDING_DIR / f"{job_id}.json.tmp"
    tmp.write_text(json.dumps(sidecar, indent=2))
    tmp.rename(PENDING_DIR / f"{job_id}.json")
    return job_id


def lookup_status(job_id: str) -> dict:
    ensure_dirs()
    if (PENDING_DIR / f"{job_id}.json").exists():
        return {"state": "pending"}
    if (PROCESSING_DIR / f"{job_id}.json").exists():
        return {"state": "processing"}
    if (FAILED_DIR / f"{job_id}.json").exists():
        meta = json.loads((FAILED_DIR / f"{job_id}.json").read_text())
        return {"state": "failed", "error": meta.get("last_error", "unknown error")}
    found = list(storage.MISTAKES_DIR.glob(f"*/{job_id}.json"))
    if found:
        return {"state": "done", "category_slug": found[0].parent.name}
    return {"state": "unknown"}
