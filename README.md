# LearnFromOops

A local Flask app that helps kids organize math mistakes from homework and tests. Snap a photo of a problem with the wrong answer; Gemini extracts the problem, classifies it into a math category, and explains the correct solution. Mistakes are browsable by category from the home page.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
cp .env.example .env
# edit .env and set GEMINI_API_KEY (get one at https://aistudio.google.com/apikey)
python3 src/app.py        # in one terminal — serves the UI
python3 src/worker.py     # in a second terminal — analyzes uploads
```

Then open http://127.0.0.1:5000. Uploading an image enqueues a job; the worker picks it up on its next poll (every 60s) and the status page redirects automatically when it's done.

## Layout

- `src/app.py` — Flask routes
- `src/inbox.py` — filesystem-backed job queue (enqueue + status lookup)
- `src/worker.py` — long-running poller that calls Gemini and saves results
- `src/gemini_client.py` — image → structured analysis (problem, student answer, category, ideal answer, explanation)
- `src/storage.py` — read/write mistakes on the local filesystem
- `src/config.py` — list of categories used for classification
- `src/templates/`, `src/static/` — UI
- `data/` (gitignored, at project root):
  - `inbox/{pending,processing,failed}/<id>.{json,<ext>}` — job queue. `pending/` is what the worker scans; `processing/` is the in-flight claim; `failed/` is jobs that exhausted retries.
  - `images/<id>.<ext>` and `mistakes/<category-slug>/<id>.{json,html}` — finished mistakes. Each is stored as both a JSON sidecar (used by the app) and a standalone HTML file you can open directly in a browser.
