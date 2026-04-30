from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, send_from_directory, url_for

load_dotenv()

import gemini_client
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

    try:
        analysis = gemini_client.analyze_image(image_bytes, mime)
    except Exception as exc:
        return render_template("upload.html", error=f"Analysis failed: {exc}"), 500

    mistake_id, category_slug = storage.save_mistake(image_bytes, ext, analysis)
    return redirect(url_for("view_mistake", category=category_slug, mistake_id=mistake_id))


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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
