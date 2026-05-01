import html
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from config import CATEGORIES, TOP_CATEGORIES

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


def save_mistake(image_bytes: bytes, image_ext: str, analysis, mistake_id: str | None = None) -> str:
    _ensure_dirs()
    if mistake_id is None:
        mistake_id = uuid.uuid4().hex[:12]
    created_at = datetime.now().isoformat(timespec="seconds")
    category = analysis.category
    subcategory = getattr(analysis, "subcategory", "") or ""

    image_filename = f"{mistake_id}{image_ext}"
    (IMAGES_DIR / image_filename).write_bytes(image_bytes)

    metadata = {
        "id": mistake_id,
        "category": category,
        "category_slug": slugify(category),
        "subcategory": subcategory,
        "subcategory_slug": slugify(subcategory) if subcategory else "",
        "created_at": created_at,
        "image_filename": image_filename,
        "problem": analysis.problem,
        "student_answer": analysis.student_answer,
        "ideal_answer": analysis.ideal_answer,
        "explanation": analysis.explanation,
    }
    (MISTAKES_DIR / f"{mistake_id}.json").write_text(json.dumps(metadata, indent=2))
    (MISTAKES_DIR / f"{mistake_id}.html").write_text(_render_standalone_html(metadata))
    return mistake_id


def _iter_mistakes() -> list[dict]:
    _ensure_dirs()
    out: list[dict] = []
    for jf in MISTAKES_DIR.glob("*.json"):
        try:
            out.append(json.loads(jf.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return out


def list_categories() -> list[dict]:
    items = _iter_mistakes()
    counts: dict[str, dict] = {}
    for m in items:
        cat = m.get("category", "")
        slug = m.get("category_slug", slugify(cat))
        if not cat:
            continue
        bucket = counts.setdefault(slug, {"slug": slug, "name": cat, "count": 0, "subcategories": set()})
        bucket["count"] += 1
        sub = m.get("subcategory", "")
        if sub:
            bucket["subcategories"].add(sub)
    out = []
    for bucket in counts.values():
        out.append({
            "slug": bucket["slug"],
            "name": bucket["name"],
            "count": bucket["count"],
            "sub_count": len(bucket["subcategories"]),
        })
    # Stable order: by configured top-category order, then alphabetic for unknown.
    order = {slugify(name): i for i, name in enumerate(TOP_CATEGORIES)}
    out.sort(key=lambda c: (order.get(c["slug"], 999), c["name"]))
    return out


def list_subcategories(category_slug: str) -> tuple[str, list[dict]]:
    items = _iter_mistakes()
    category_name = ""
    counts: dict[str, dict] = {}
    for m in items:
        if m.get("category_slug") != category_slug:
            continue
        category_name = m.get("category", category_name)
        sub = m.get("subcategory", "")
        sub_slug = m.get("subcategory_slug", slugify(sub) if sub else "")
        key = sub_slug or "__none__"
        bucket = counts.setdefault(key, {"slug": sub_slug, "name": sub or "Uncategorized", "count": 0})
        bucket["count"] += 1
    out = list(counts.values())
    sub_order = {slugify(s): i for i, s in enumerate(CATEGORIES.get(category_name, []))}
    out.sort(key=lambda s: (sub_order.get(s["slug"], 999), s["name"]))
    return category_name, out


def list_mistakes_in_subcategory(category_slug: str, subcategory_slug: str) -> tuple[str, str, list[dict]]:
    items = _iter_mistakes()
    category_name = ""
    subcategory_name = ""
    out: list[dict] = []
    for m in items:
        if m.get("category_slug") != category_slug:
            continue
        if (m.get("subcategory_slug") or "") != subcategory_slug:
            continue
        category_name = m.get("category", category_name)
        subcategory_name = m.get("subcategory", subcategory_name)
        out.append(m)
    out.sort(key=lambda m: m["created_at"], reverse=True)
    return category_name, subcategory_name, out


def get_mistake(mistake_id: str) -> dict | None:
    _ensure_dirs()
    json_file = MISTAKES_DIR / f"{mistake_id}.json"
    if not json_file.exists():
        return None
    return json.loads(json_file.read_text())


def mark_seen(mistake_id: str) -> None:
    json_file = MISTAKES_DIR / f"{mistake_id}.json"
    if not json_file.exists():
        return
    data = json.loads(json_file.read_text())
    data["last_seen_at"] = datetime.now().isoformat(timespec="seconds")
    tmp = json_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(json_file)


def list_new_mistakes() -> list[dict]:
    items = [m for m in _iter_mistakes() if not m.get("last_seen_at")]
    items.sort(key=lambda m: m["created_at"], reverse=True)
    return items


def _render_standalone_html(m: dict) -> str:
    e = html.escape
    sub = m.get("subcategory") or ""
    sub_chip = f' <span class="badge">{e(sub)}</span>' if sub else ""
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
<p><span class="badge">{e(m['category'])}</span>{sub_chip}</p>
<img src="../images/{e(m['image_filename'])}" alt="Original problem">
<section><h2>Problem</h2><p>{e(m['problem'])}</p></section>
<section class="wrong"><h2>Student Answer</h2><p>{e(m['student_answer'])}</p></section>
<section class="right"><h2>Correct Answer</h2><p><strong>{e(m['ideal_answer'])}</strong></p></section>
<section><h2>How to Solve</h2><p class="explanation">{e(m['explanation'])}</p></section>
<p class="meta">Captured {m['created_at']}</p>
</body></html>
"""
