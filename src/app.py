import base64
import io
import socket
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, send_from_directory, url_for
import qrcode

load_dotenv()

import inbox
import storage

PORT = 5000


def _lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


LAN_URL = f"http://{_lan_ip()}:{PORT}"
UPLOAD_URL = f"{LAN_URL}/upload"


def _make_qr_b64(url: str) -> str:
    buf = io.BytesIO()
    qrcode.make(url).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


_UPLOAD_QR_B64 = _make_qr_b64(UPLOAD_URL)


def _is_mobile() -> bool:
    if request.headers.get("Sec-CH-UA-Mobile") == "?1":
        return True
    ua = request.headers.get("User-Agent", "")
    return "Mobile" in ua or "Android" in ua

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


@app.route("/")
def index():
    categories = storage.list_categories()
    total = sum(c.count for c in categories)
    new_count = len(storage.list_new_mistakes())
    inflight = inbox.list_inflight()
    return render_template(
        "index.html",
        categories=categories,
        total=total,
        new_count=new_count,
        inflight=inflight,
    )


@app.route("/inbox/<job_id>/retry", methods=["POST"])
def retry_job(job_id):
    if not inbox.retry_failed(job_id):
        abort(404)
    return redirect(url_for("index"))


@app.route("/new")
def view_new():
    mistakes = storage.list_new_mistakes()
    return render_template("new.html", mistakes=mistakes)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    mobile = _is_mobile()
    lan_url = None if mobile else UPLOAD_URL
    qr_code = None if mobile else _UPLOAD_QR_B64
    if request.method == "GET":
        return render_template("upload.html", lan_url=lan_url, qr_code=qr_code)

    file = request.files.get("image")
    if not file or not file.filename:
        return render_template("upload.html", error="Please choose an image.", lan_url=lan_url, qr_code=qr_code), 400

    image_bytes = file.read()
    ext = Path(file.filename).suffix.lower() or ".jpg"
    mime = file.mimetype or "image/jpeg"

    inbox.enqueue(image_bytes, ext, mime)
    return render_template("upload.html", queued=True, lan_url=lan_url, qr_code=qr_code)


@app.route("/category/<category>")
def view_category(category):
    name, subcategories = storage.list_subcategories(category)
    if not subcategories:
        abort(404)
    return render_template(
        "category.html",
        category=name,
        slug=category,
        subcategories=subcategories,
    )


@app.route("/category/<category>/<subcategory>")
def view_subcategory(category, subcategory):
    cat_name, sub_name, mistakes = storage.list_mistakes_in_subcategory(category, subcategory)
    if not mistakes:
        abort(404)
    return render_template(
        "subcategory.html",
        category=cat_name,
        subcategory=sub_name,
        category_slug=category,
        subcategory_slug=subcategory,
        mistakes=mistakes,
    )


@app.route("/mistake/<mistake_id>")
def view_mistake(mistake_id):
    mistake = storage.get_mistake(mistake_id)
    if not mistake:
        abort(404)
    storage.mark_seen(mistake_id)
    return render_template("mistake.html", mistake=mistake)


@app.route("/images/<filename>")
def serve_image(filename):
    return send_from_directory(storage.IMAGES_DIR, filename)


if __name__ == "__main__":
    print(f" * LAN access: {LAN_URL}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
