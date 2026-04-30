import socket
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, send_from_directory, url_for

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
    total = sum(c["count"] for c in categories)
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
    lan_url = None if _is_mobile() else LAN_URL
    if request.method == "GET":
        return render_template("upload.html", lan_url=lan_url)

    file = request.files.get("image")
    if not file or not file.filename:
        return render_template("upload.html", error="Please choose an image.", lan_url=lan_url), 400

    image_bytes = file.read()
    ext = Path(file.filename).suffix.lower() or ".jpg"
    mime = file.mimetype or "image/jpeg"

    inbox.enqueue(image_bytes, ext, mime)
    return render_template("upload.html", queued=True, lan_url=lan_url)


@app.route("/category/<category>")
def view_category(category):
    mistakes = storage.list_mistakes_in_category(category)
    if not mistakes:
        abort(404)
    return render_template("category.html", category=mistakes[0]["category"], slug=category, mistakes=mistakes)


@app.route("/mistake/<category>/<mistake_id>")
def view_mistake(category, mistake_id):
    mistake = storage.get_mistake(category, mistake_id)
    if not mistake:
        abort(404)
    storage.mark_seen(category, mistake_id)
    return render_template("mistake.html", mistake=mistake, slug=category)


@app.route("/images/<filename>")
def serve_image(filename):
    return send_from_directory(storage.IMAGES_DIR, filename)


if __name__ == "__main__":
    print(f" * LAN access: {LAN_URL}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
