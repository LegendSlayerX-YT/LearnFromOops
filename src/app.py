import socket
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, url_for

load_dotenv()

import inbox
import storage

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


@app.route("/")
def index():
    categories = storage.list_categories()
    total = sum(c["count"] for c in categories)
    return render_template("index.html", categories=categories, total=total)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return render_template("upload.html")

    file = request.files.get("image")
    if not file or not file.filename:
        return render_template("upload.html", error="Please choose an image."), 400

    image_bytes = file.read()
    ext = Path(file.filename).suffix.lower() or ".jpg"
    mime = file.mimetype or "image/jpeg"

    job_id = inbox.enqueue(image_bytes, ext, mime)
    return redirect(url_for("status", job_id=job_id))


@app.route("/status/<job_id>")
def status(job_id):
    return render_template("status.html", job_id=job_id)


@app.route("/status/<job_id>/check")
def status_check(job_id):
    return jsonify(inbox.lookup_status(job_id))


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
    return render_template("mistake.html", mistake=mistake, slug=category)


@app.route("/images/<filename>")
def serve_image(filename):
    return send_from_directory(storage.IMAGES_DIR, filename)


def _lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    port = 5000
    print(f" * LAN access: http://{_lan_ip()}:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
