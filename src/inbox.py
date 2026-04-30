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


def list_inflight() -> list[dict]:
    ensure_dirs()
    jobs = []
    for state, dir_ in (("pending", PENDING_DIR), ("processing", PROCESSING_DIR), ("failed", FAILED_DIR)):
        for sidecar in dir_.glob("*.json"):
            try:
                meta = json.loads(sidecar.read_text())
            except (json.JSONDecodeError, FileNotFoundError):
                continue
            jobs.append({
                "id": meta.get("id", sidecar.stem),
                "state": state,
                "created_at": meta.get("created_at", ""),
                "attempts": meta.get("attempts", 0),
                "last_error": meta.get("last_error"),
            })
    jobs.sort(key=lambda j: j["created_at"], reverse=True)
    return jobs


def retry_failed(job_id: str) -> bool:
    ensure_dirs()
    sidecar = FAILED_DIR / f"{job_id}.json"
    if not sidecar.exists():
        return False
    meta = json.loads(sidecar.read_text())
    ext = meta.get("ext", "")
    meta["attempts"] = 0
    meta.pop("last_error", None)
    tmp = sidecar.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, indent=2))
    tmp.rename(sidecar)
    # Move image first so the sidecar landing in pending/ — the worker's "ready"
    # signal — only appears after the bytes are in place.
    image = FAILED_DIR / f"{job_id}{ext}"
    if image.exists():
        image.rename(PENDING_DIR / image.name)
    sidecar.rename(PENDING_DIR / sidecar.name)
    return True

