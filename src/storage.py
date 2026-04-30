import html
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
IMAGES_DIR = DATA_DIR / "images"
MISTAKES_DIR = DATA_DIR / "mistakes"


def _ensure_dirs() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    MISTAKES_DIR.mkdir(parents=True, exist_ok=True)


def slugify(name: str) -> str:
    s = name.lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "uncategorized"


def save_mistake(image_bytes: bytes, image_ext: str, analysis) -> tuple[str, str]:
    _ensure_dirs()
    mistake_id = uuid.uuid4().hex[:12]
    created_at = datetime.now().isoformat(timespec="seconds")
    category_slug = slugify(analysis.category)

    image_filename = f"{mistake_id}{image_ext}"
    (IMAGES_DIR / image_filename).write_bytes(image_bytes)

    category_dir = MISTAKES_DIR / category_slug
    category_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "id": mistake_id,
        "category": analysis.category,
        "category_slug": category_slug,
        "created_at": created_at,
        "image_filename": image_filename,
        "problem": analysis.problem,
        "student_answer": analysis.student_answer,
        "ideal_answer": analysis.ideal_answer,
        "explanation": analysis.explanation,
    }
    (category_dir / f"{mistake_id}.json").write_text(json.dumps(metadata, indent=2))
    (category_dir / f"{mistake_id}.html").write_text(_render_standalone_html(metadata))
    return mistake_id, category_slug


def list_categories() -> list[dict]:
    _ensure_dirs()
    out = []
    for path in sorted(MISTAKES_DIR.iterdir()):
        if not path.is_dir():
            continue
        files = list(path.glob("*.json"))
        if not files:
            continue
        display = json.loads(files[0].read_text())["category"]
        out.append({"slug": path.name, "name": display, "count": len(files)})
    return out


def list_mistakes_in_category(category_slug: str) -> list[dict]:
    _ensure_dirs()
    category_dir = MISTAKES_DIR / category_slug
    if not category_dir.exists():
        return []
    items = [json.loads(f.read_text()) for f in category_dir.glob("*.json")]
    items.sort(key=lambda m: m["created_at"], reverse=True)
    return items


def get_mistake(category_slug: str, mistake_id: str) -> dict | None:
    _ensure_dirs()
    json_file = MISTAKES_DIR / category_slug / f"{mistake_id}.json"
    if not json_file.exists():
        return None
    return json.loads(json_file.read_text())


def _render_standalone_html(m: dict) -> str:
    e = html.escape
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>{e(m['category'])} mistake — {m['created_at']}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #1f2937; }}
img {{ max-width: 100%; border-radius: 8px; }}
.badge {{ display: inline-block; background: #e0e7ff; color: #4338ca; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.85rem; }}
h2 {{ font-size: 1rem; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; margin-bottom: 0.25rem; }}
.wrong h2 {{ color: #dc2626; }}
.right h2 {{ color: #059669; }}
.explanation {{ white-space: pre-line; }}
.meta {{ color: #9ca3af; font-size: 0.85rem; }}
</style></head>
<body>
<p><span class="badge">{e(m['category'])}</span></p>
<img src="../../images/{e(m['image_filename'])}" alt="Original problem">
<section><h2>Problem</h2><p>{e(m['problem'])}</p></section>
<section class="wrong"><h2>Student Answer</h2><p>{e(m['student_answer'])}</p></section>
<section class="right"><h2>Correct Answer</h2><p><strong>{e(m['ideal_answer'])}</strong></p></section>
<section><h2>How to Solve</h2><p class="explanation">{e(m['explanation'])}</p></section>
<p class="meta">Captured {m['created_at']}</p>
</body></html>
"""
