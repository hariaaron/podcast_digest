# Podcast Digest (MVP)

This repository contains a minimal automation pipeline (GitHub Actions) to produce a daily podcast digest using RSS feeds, optional ASR transcription via OpenAI, and LLM summarization (OpenAI).

Quick start (local)

1. Create a Python 3.11 environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Add feed URLs to `config/feeds.yml` as a YAML list, e.g.:

```yaml
- https://feeds.simplecast.com/abcd
- https://rss.example.com/podcast
```

3. Set environment variables (for local testing you can export them):

```bash
export OPENAI_API_KEY="sk-..."
# Optional: enable ASR and email behaviour
export ASR_ENABLED=0
export DRY_RUN=1
export SMOKE_TEST=1
# For sending mail (not recommended for initial local runs):
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USER=...
export SMTP_PASSWORD=...
export MAIL_FROM=you@example.com
export MAIL_TO=recipient@example.com
```

4. Run the pipeline locally:

```bash
python -m src.main
```

Notes
- `SMOKE_TEST=1` disables ASR and LLM summarization and is useful to verify feed parsing and state persistence.
- `DRY_RUN=1` prevents mail send in CI and local runs where mailer is invoked.
- The GitHub Actions workflow installs dependencies, runs `python -m src.main`, commits `state/state.json` and `preview.html` if changed, and optionally sends the preview via SMTP.

Files of interest
- `src/feeds.py` - RSS parsing and new-episode detection
- `src/asr.py` - download & transcribe audio (OpenAI)
- `src/summarizer.py` - call OpenAI to summarize transcripts
- `src/storage.py` - atomic read/write of `state/state.json`
- `src/main.py` - orchestration
- `.github/workflows/podcast_digest.yml` - CI orchestration

License: MIT (as in repo)

Workshop wrap / Decisions
--------------------------------
- Persistence: state is stored in `state/state.json` inside the repo and updated by the workflow. This keeps the pipeline deterministic from repo + feeds.
- LLM / ASR provider: OpenAI only (via `OPENAI_API_KEY`). ASR is optional (`ASR_ENABLED`), transcripts cached in state.
- Safety: `SMOKE_TEST=1` to validate feed parsing/state without invoking costly LLM/ASR; `DRY_RUN=1` to avoid sending mail.

Required GitHub Secrets (add these to repo Settings → Secrets):
- `OPENAI_API_KEY` — OpenAI API key for LLM and ASR calls
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` — SMTP credentials for mail delivery (optional)
- `MAIL_FROM`, `MAIL_TO` — sender and recipient addresses for preview email

What was implemented (MVP):
- Feed monitoring and deduplication (`src/feeds.py`)
- Atomic state read/write (`src/storage.py`) and per-episode storage
- ASR download + OpenAI transcription wrapper (`src/asr.py`) with size checks and caching
- LLM summarizer wrapper calling OpenAI ChatCompletion (`src/summarizer.py`) and storing `summary_ai`
- Orchestration (`src/main.py`) to run E2E and render `preview.html` using Jinja2 template
- SMTP mailer (`src/mailer.py`) and CI integration in `.github/workflows/podcast_digest.yml`

Next improvements (post‑workshop suggestions):
- Add robust chunking for very long audio (ffmpeg re-encode + chunk uploads)
- Add structured JSON summaries (title, bullets, timestamps) and tests for prompt stability
- Rate‑limit and backoff improvements for large feed lists
- Add unit tests and CI matrix for linting and smoke tests

How to verify quickly (recommended):
1. Add one or two feed URLs to `config/feeds.yml`.
2. Run locally with `SMOKE_TEST=1 DRY_RUN=1 python -m src.main` to ensure parsing and state updates.
3. Remove `SMOKE_TEST` and enable `ASR_ENABLED=1` (and `OPENAI_API_KEY`) for a full run.

If you want, I can now:
- run a dry smoke test locally in this environment, or
- add unit tests for `storage` and `feeds`.
## Daily Podcast Digest

Podcasts liefern häufig nur Shownotes. Der eigentliche Mehrwert steckt im Audio. Ziel dieses Projekts ist ein automatisierter Workflow, der neue Podcast-Episoden erkennt, den Audioinhalt per ASR transkribiert, daraus prägnante Episoden-Summaries erzeugt und das Ergebnis als Digest bereitstellt. 
 
## Ansatz
Baue mit einem Vibe-Coding Ansatz ein MVP, das 2–3 Podcast-RSS-Feeds überwacht, neue Episoden robust dedupliziert, Audio (MP3) verarbeitet, per AI transkribiert und pro Episode eine strukturierte Zusammenfassung erzeugt. 
Konkretes Ergebnis am Ende:

Ein lauffähiger Workflow, der:  
- 2–3 Podcast-RSS-Feeds einliest (MP3-Enclosures) 
- neue Episoden erkennt (Dedupe über stabilen Episode-Key) 
- Audio herunterlädt (mit Max-Size-Limit), ggf. in Chunks splittet (ffmpeg) 
- ASR (automatic speech recognition) ausführt und (optional) cached 
- pro Episode per LLM ein strukturiertes Summary erzeugt 
- Ergebnis als HTML (oder Markdown) in einem preview.html ablegt 
- optional Mail versendet (DRY_RUN steuert Versand) 
- State als JSON persistiert, sodass beim nächsten Run keine Doppelverarbeitung stattfindet 
- auch bei Teilausfällen Fortschritt persistiert 
- Betriebsmodi unterstützt: BOOTSTRAP, SMOKE_TEST, DRY_RUN, FORCE_LATEST_N 
