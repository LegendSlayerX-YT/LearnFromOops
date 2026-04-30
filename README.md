# LearnFromOops

A local Flask app that helps kids organize math mistakes from homework and tests. Snap a photo of a problem with the wrong answer; Gemini extracts the problem, classifies it into a math category, and explains the correct solution. Mistakes are browsable by category from the home page.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
cp .env.example .env
# edit .env and set GEMINI_API_KEY (get one at https://aistudio.google.com/apikey)
python3 src/app.py
```

Then open http://127.0.0.1:5000.

## Layout

- `src/app.py` — Flask routes
- `src/gemini_client.py` — image → structured analysis (problem, student answer, category, ideal answer, explanation)
- `src/storage.py` — read/write mistakes on the local filesystem
- `src/config.py` — list of categories used for classification
- `src/templates/`, `src/static/` — UI
- `data/` (gitignored, at project root) — `images/<id>.<ext>` and `mistakes/<category-slug>/<id>.{json,html}`. Each mistake is stored as both a JSON sidecar (used by the app) and a standalone HTML file you can open directly in a browser.
