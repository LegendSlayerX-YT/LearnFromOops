import json
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import gemini_client
import inbox
import storage

MAX_ATTEMPTS = 3
POLL_SECONDS = 60


def _recover_stuck_jobs() -> None:
    # Anything in processing/ at startup means a previous run died mid-job.
    # Move it back to pending/ so it gets retried (attempts counter persists).
    inbox.ensure_dirs()
    for path in inbox.PROCESSING_DIR.iterdir():
        path.rename(inbox.PENDING_DIR / path.name)


def _claim(sidecar: Path) -> Path | None:
    target = inbox.PROCESSING_DIR / sidecar.name
    try:
        sidecar.rename(target)
    except FileNotFoundError:
        return None
    return target


def _write_sidecar(path: Path, meta: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(meta, indent=2))
    tmp.rename(path)


def _process(sidecar: Path) -> None:
    meta = json.loads(sidecar.read_text())
    job_id = meta["id"]
    ext = meta["ext"]
    mime = meta["mime"]

    image_path = inbox.PROCESSING_DIR / f"{job_id}{ext}"
    pending_image = inbox.PENDING_DIR / f"{job_id}{ext}"
    if pending_image.exists():
        pending_image.rename(image_path)

    if not image_path.exists():
        # Sidecar without an image — give up and quarantine the sidecar so we
        # don't loop on it.
        meta["last_error"] = "image file missing"
        _write_sidecar(sidecar, meta)
        sidecar.rename(inbox.FAILED_DIR / sidecar.name)
        print(f"[worker] {job_id} FAILED: image file missing")
        return

    image_bytes = image_path.read_bytes()
    try:
        analysis = gemini_client.analyze_image(image_bytes, mime)
        analysis.subcategory = gemini_client.classify_subcategory(analysis)
    except Exception as exc:
        meta["attempts"] = meta.get("attempts", 0) + 1
        meta["last_error"] = f"{type(exc).__name__}: {exc}"
        if meta["attempts"] >= MAX_ATTEMPTS:
            _write_sidecar(sidecar, meta)
            sidecar.rename(inbox.FAILED_DIR / sidecar.name)
            image_path.rename(inbox.FAILED_DIR / image_path.name)
            print(f"[worker] {job_id} FAILED after {MAX_ATTEMPTS} attempts: {exc}")
        else:
            _write_sidecar(sidecar, meta)
            image_path.rename(inbox.PENDING_DIR / image_path.name)
            sidecar.rename(inbox.PENDING_DIR / sidecar.name)
            print(f"[worker] {job_id} retry {meta['attempts']}/{MAX_ATTEMPTS}: {exc}")
        return

    storage.save_mistake(image_bytes, ext, analysis, mistake_id=job_id)
    sidecar.unlink()
    image_path.unlink()
    label = f"{analysis.category} / {analysis.subcategory}" if analysis.subcategory else analysis.category
    print(f"[worker] {job_id} done — {label}")


def _scan_once() -> None:
    for sidecar in sorted(inbox.PENDING_DIR.glob("*.json")):
        claimed = _claim(sidecar)
        if claimed is None:
            continue
        try:
            _process(claimed)
        except Exception:
            # Anything that escapes _process is a worker bug — log and leave the
            # job in processing/ so the next startup recovers it.
            traceback.print_exc()


def main() -> None:
    inbox.ensure_dirs()
    _recover_stuck_jobs()
    print(f"[worker] watching {inbox.PENDING_DIR}, polling every {POLL_SECONDS}s")
    while True:
        try:
            _scan_once()
        except Exception:
            traceback.print_exc()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
