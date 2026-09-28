# Rill — dev quickstart

Zero-friction citizen reporting for stream hazards, set in a small,
entirely fictional world: **the Cindervale Watershed**, 10 made-up
locations along one imaginary river. No real GPS, no real places — scan a
QR code, submit a photo and/or description, and it's logged against one of
the 10 locations. See `server/app/world.py` for the full catalog.

Stack: **FastAPI (Python) + MongoDB** on the backend, **Vite + React +
TypeScript** on the frontend, plus a **separate `ml/` folder** for a
ResNet-based visual similarity pipeline.

## Rill naming

| Component | Role | Status |
|---|---|---|
| **Rill Report** | Citizen intake — no location permission needed | ✅ built |
| **Rill Signal** | Severity classification of incoming reports | 🟡 built, placeholder logic (random tier) |
| **Rill Overview** | The world board — all 10 locations, live stats, visual similarity | ✅ built |
| **Rill Watch** | Notification preferences (now in the account menu, not a standalone page) | ✅ built |
| **Rill Alert** | Geo-fenced push/SMS notifications | ⏳ not yet built (Overview currently polls instead) |
| **Rill Console** | Municipal responder dashboard | ⏳ not yet built |

## How location assignment works right now

There is no geolocation permission prompt anywhere in the app. Instead,
each of the 10 printed QR codes encodes a link straight to Rill Report with
that location's segment code pre-filled (`/report?segment=SEG-03`), so
scanning a specific physical QR code logs the report against that specific
location — the QR code itself *is* the location signal, no GPS involved.

**A valid segment code is required — there is no fallback, anywhere, not
even for convenience.** A report with a missing or unrecognized segment
code is rejected outright: a 422 at the framework level if the field is
missing entirely, a 400 from `create_report()` if it's present but doesn't
match a real location. This is deliberate, not just a stricter demo
setting: a fallback that quietly substitutes fabricated location data is
the kind of thing that's tolerable in a demo and dangerous in a real
deployment, so it was removed rather than made optional.

There are two ways to get a valid segment code, both equally legitimate —
neither is a fallback, since both are a deliberate, explicit choice rather
than a guess:
1. **Scan a QR code** — the location is pre-filled from the link.
2. **Pick it manually** — opening Rill Report with no QR context (e.g. via
   the nav bar) shows a dropdown of all 10 locations instead of blocking
   outright. A scanned QR still takes priority if present; the picker only
   appears when there's no QR context to trust in the first place.

Either way, the resulting segmentCode goes through the exact same required
field and the exact same validation in `create_report()` — the backend
can't tell which path a report came in through, and doesn't need to.

## What's in here

```
server/     FastAPI + MongoDB backend
  app/            Core API: auth, world catalog, reports, alerts, Rill Signal queue
  ml/             Live inference — loaded by Rill Signal at runtime
    training/     Trains the model ml/ loads — run this BEFORE ml/ can do anything
client/     React + TypeScript (Vite) frontend
```

## 1. MongoDB (free tier)

1. Create a free cluster at https://www.mongodb.com/cloud/atlas/register
2. Create a database user and grab the connection string
   (Atlas → Connect → Drivers → copy the `mongodb+srv://...` URI)

You don't need to create any databases or collections yourself — MongoDB
creates them automatically the first time something writes to them.

## 2. Server setup

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

A `.env` file is already included with everything filled in **except**
`MONGODB_URI` — paste your real Atlas connection string in before running.

| Variable | Required? | Purpose |
|---|---|---|
| `MONGODB_URI` | **yes — you must set this** | Atlas connection string |
| `MONGODB_DB_NAME` | pre-filled (`rill`) | Used regardless of what's in the URI's path — Atlas's own copy-paste string often omits a db name, so the app never depends on it being there |
| `JWT_SECRET` | pre-filled | Signs auth tokens |
| `CLIENT_ORIGIN` | pre-filled | Allowed CORS origin (the Vite dev server) |
| `CLIENT_BASE_URL` | pre-filled | Used only by the demo QR generator |
| `UPLOAD_DIR` | pre-filled | Local folder for uploaded report photos |
| `PORT` | pre-filled, optional | Only used by `run.py` |
| `LOG_LEVEL` | pre-filled, optional | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

Run it:

```bash
python run.py
# or, equivalently:
uvicorn app.main:app --reload --port 4000
```

### Visual similarity (ResNet + triplet loss) — optional, separate install & training step

```bash
pip install -r ml/requirements.txt
python -m ml.training.train
```

This pulls in `torch` + `torchvision` (heavy — a real download) and is kept
in its own requirements file on purpose. **The app works completely fine
without any of this installed** — Rill Signal will log a `[WARN]` and skip
the visual-similarity step for each report, and everything else (tier
classification, the world board, settings) keeps working.

**Training is required before this does anything.** An untrained,
off-the-shelf ImageNet backbone has no reason to place two similar-looking
streams near each other in embedding space — it was trained to recognize
1000 unrelated object categories, not stream conditions. So `ml/` only
loads a model if `ml/training/train.py` has produced a checkpoint; until then,
`extract_embedding()` returns `None` and logs exactly that, rather than
silently running on weights that were never taught this task.

**How it's trained**, stated plainly: there's no real labeled dataset of
stream photos, so `ml/training/dataset.py` procedurally generates one — six
visually distinct condition classes (`clear`, `murky`, `flooded`,
`whitewater`, `algae`, `debris`), each with a distinct base color and
texture pattern plus per-sample random jitter. **Every image a training
run generates is also saved to `ml/training/data/<class_name>/`** — open
them directly if you want to see exactly what the model trained on, rather
than trusting this description. `ml/training/train.py` fine-tunes a
ResNet18 backbone (ImageNet-pretrained starting point) with **triplet
loss** — for each anchor image, it pulls a same-class "positive" closer in
embedding space and pushes a different-class "negative" further away.
That's what actually teaches the model "these look similar" rather than
just "these are both streams." Result: a 128-dim embedding model saved to
`ml/checkpoints/stream_embedding.safetensors` (+ a small `.json` metadata
sidecar), loaded automatically by Rill Signal on the next report — no
server restart needed, even if a report already ran (and got skipped)
before training finished; the loader checks the checkpoint files
themselves, not a one-time flag.

The same trained embedding model also classifies each new report's
condition via nearest-centroid matching (`classify_condition()` in
`ml/inference.py`) — no separate classifier head needed, since a
triplet-trained embedding space already clusters same-class images near
their centroid. It returns the **full ranked breakdown across all 6
classes**, not just the winning label — a confident call (0.95 vs 0.20)
and a close call (0.61 vs 0.58) are very different signals even when they
pick the same label, and that margin is exactly what's shown on each
report's location page as a set of ranked bars, not a single chip.

Honest limitation, worth restating: this proves the training pipeline
works end-to-end on classes that are distinguishable by construction. It
says nothing about how these embeddings would generalize to real stream
photography — that would need real labeled data, which doesn't exist for
this project.

```bash
# defaults are reasonable for a quick CPU run; all tunable:
python -m ml.training.train --epochs 6 --samples-per-class 150
```

### A couple of small supporting endpoints

- `GET /api/ml/status` — public, no auth. Returns `{torchInstalled, trained,
  classes, instructions}` so the frontend can show a "train the model
  first" banner instead of a silently-empty condition filter.
- `GET /api/users/me/alerts` — a user's alert history. Honestly empty right
  now (nothing writes to it — Rill Alert dispatch isn't built), but wired
  up and ready for when it is.

### Generate demo QR codes

```bash
python -m app.scripts.generate_demo_qr
```

Writes 10 QR codes to `server/demo-qr-codes/`, one per Cindervale
Watershed location, each pointing at Rill Report with that location's
segment code pre-filled. Print these (or display them on separate screens/
devices for the demo) — scanning `SEG-03.png` logs a report at Cinderwood
Ford, scanning `SEG-07.png` logs one at Ashgrove Footbridge, and so on.

### Logs

Every request and background event is logged with a level tag:

```
[INFO] 23:04:11 rill.server: starting up…
[INFO] 23:04:11 rill.db: connected to MongoDB (database=rill)
[INFO] 23:06:01 POST /api/reports -> 201 (42.3ms)
[INFO] 23:06:04 rill.signal: classified report ... as caution (confidence=0.81)
[WARN] 23:06:04 rill.ml.embedding: torch/torchvision not installed — visual similarity is disabled.
[ERR ] 23:07:10 rill.db: failed to connect to MongoDB
```

## 3. Client setup

```bash
cd client
npm install
cp .env.example .env
npm run dev
```

Client runs on `http://localhost:5173`.

## 4. Try it

1. Register a username + password (no email, no location permission).
2. Go to **Report** — pick a location from the dropdown (or open a
   specific `/report?segment=SEG-xx` link to simulate scanning a real QR
   code, which skips the dropdown), add a photo and/or description, submit.
3. Rill Signal picks it up within a few seconds and assigns a
   (currently placeholder/random) tier, plus a visual-similarity match if
   the ML dependencies are installed and an image was attached.
4. Go to **Overview** — the world board: stat strip, a card per location
   (illustration, current tier, report/image counts). Click a card to open
   that location's own page — every report there shows its photo, notes,
   timestamp, and (if a model is trained) the full AI condition breakdown
   across all 6 classes, not just the top guess, plus any "visually
   resembles" matches to other locations.
5. Click the **avatar icon** (top right) — the account menu holds your
   Watch settings (channels, minimum tier, home location, radius), your
   past-alerts history (empty until Rill Alert dispatch exists), and log out.

## Known placeholders (intentional, for this build stage)

- **Rill Signal's severity classification is random**, not real — see
  `server/app/services/queue.py`. This is the seam where the real Nemotron +
  LangGraph classification call plugs in later.
- **Rill Alert doesn't exist yet** — Rill Overview currently polls every
  10s instead of receiving pushed alerts.
- **No moderation queue UI yet** — classifications go straight to
  "classified" status with no human-in-the-loop gate.
- **Rill Console doesn't exist yet** — no separate municipal-facing view.
- **The visual similarity model is real but trained on synthetic data** —
  triplet-loss fine-tuning on procedurally generated "condition" classes
  (see `ml/training/dataset.py`), not real stream photography. It
  won't do anything at all until you've run `python -m ml.training.train`
  at least once. A `[WARN]` also logs at server startup either way, and
  `GET /api/ml/status` lets the frontend show this without you having to
  read the server logs.
