import os
from typing import List

from jinja2 import Environment, FileSystemLoader

from . import feeds, asr, summarizer, storage


TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
PREVIEW_OUT = os.path.join(os.path.dirname(__file__), "..", "preview.html")


def generate_preview(episodes: List[dict]) -> None:
	env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
	try:
		tpl = env.get_template("email.html")
	except Exception:
		# fallback simple rendering
		html = "<html><body><h1>Daily Podcast Digest</h1>"
		for e in episodes:
			html += f"<h2>{e.get('title')}</h2><p>{e.get('summary_ai') or e.get('summary') or ''}</p>"
		html += "</body></html>"
		with open(PREVIEW_OUT, "w", encoding="utf-8") as f:
			f.write(html)
		return

	rendered = tpl.render(episodes=episodes)
	with open(PREVIEW_OUT, "w", encoding="utf-8") as f:
		f.write(rendered)


def run(dry_run: bool = False):
	# respect env DRY_RUN if caller didn't override
	if not dry_run:
		dry_run = os.environ.get("DRY_RUN", "0") == "1"
	smoke_test = os.environ.get("SMOKE_TEST", "0") == "1"

	urls = feeds.load_feed_urls()
	if not urls:
		print("No feeds configured in config/feeds.yml")
		return

	max_age = int(os.environ.get("MAX_EPISODE_AGE_DAYS", "7"))
	force_latest = int(os.environ.get("FORCE_LATEST_N", "0"))
	asr_enabled = int(os.environ.get("ASR_ENABLED", "0"))
	asr_cache = int(os.environ.get("ASR_CACHE_ENABLED", "1"))
	max_download_mb = int(os.environ.get("ASR_MAX_DOWNLOAD_MB", "100"))
	# In smoke test mode, disable ASR and LLM calls
	if smoke_test:
		print("SMOKE_TEST=1 enabled: skipping ASR and LLM summarization")
		asr_enabled = 0

	new_eps = feeds.find_new_episodes(urls, max_episode_age_days=max_age, force_latest_n=force_latest)
	print(f"Discovered {len(new_eps)} new episodes")

	processed = []
	for ep in new_eps:
		guid = ep.get("guid")
		# persist basic metadata
		storage.update_episode(guid, {"title": ep.get("title"), "link": ep.get("link"), "published": ep.get("published"), "feed": ep.get("feed")})

		# SMOKE_TEST: skip heavy operations
		if smoke_test:
			processed_entry = storage.list_episodes().get(guid, {})
			processed.append(processed_entry)
			continue

		transcript = None
		if asr_enabled and ep.get("audio_url"):
			res = asr.transcribe_from_url(guid, ep.get("audio_url"), max_download_mb=max_download_mb)
			if res:
				transcript = res.get("transcript")

		# if transcript available, summarize; else if summary from feed exists, keep it
		summary = None
		if transcript:
			s = summarizer.summarize_transcript(guid, transcript)
			if s:
				summary = s.get("summary")
		else:
			# feed provided summary: attempt to generate an AI summary from it (unless smoke_test)
			summary = ep.get("summary")
			if summary:
				storage.update_episode(guid, {"summary": summary})
				if not smoke_test:
					s = summarizer.summarize_text(guid, summary)
					if s:
						summary = s.get("summary")

		processed_entry = storage.list_episodes().get(guid, {})
		processed.append(processed_entry)

	if processed:
		generate_preview(processed)
		print(f"Wrote preview to {PREVIEW_OUT}")

	if dry_run:
		print("Dry run - no mail sent")


if __name__ == "__main__":
	run(dry_run=False)

