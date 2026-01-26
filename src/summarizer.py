import os
import time
from typing import Dict, Any, Optional

import openai

from . import storage


DEFAULT_MODEL = os.environ.get("MODEL_TEXT", "gpt-4o-mini")
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT_S", "60"))
LLM_RETRIES = int(os.environ.get("LLM_RETRIES", "2"))
LLM_BACKOFF = int(os.environ.get("LLM_BACKOFF_S", "2"))


def _call_openai(prompt: str, model: str = DEFAULT_MODEL) -> Optional[str]:
	openai.api_key = os.environ.get("OPENAI_API_KEY")
	for attempt in range(LLM_RETRIES + 1):
		try:
			resp = openai.ChatCompletion.create(
				model=model,
				messages=[{"role": "user", "content": prompt}],
				timeout=LLM_TIMEOUT,
			)
			# extract text
			if isinstance(resp, dict):
				choices = resp.get("choices") or []
				if choices:
					return choices[0].get("message", {}).get("content")
			else:
				# fallback attribute access
				return getattr(resp.choices[0].message, "content", None)
		except Exception as e:
			if attempt < LLM_RETRIES:
				time.sleep(LLM_BACKOFF * (attempt + 1))
				continue
			else:
				raise


def summarize_transcript(guid: str, transcript: str) -> Optional[Dict[str, Any]]:
	"""Generate a concise summary and key takeaways for a transcript and store in state."""
	if not transcript:
		return None

	prompt = (
		"You are an assistant that creates concise podcast episode summaries.\n"
		"Provide a short summary (2-4 sentences) and 3-5 bullet key takeaways.\n"
		"Input transcript: \n" + transcript
	)

	model = DEFAULT_MODEL
	try:
		content = _call_openai(prompt, model=model)
	except Exception:
		return None

	if not content:
		return None

	# store summary
	storage.update_episode(guid, {"summary_ai": content})
	return {"summary": content}


if __name__ == "__main__":
	print("summarizer module. Use summarize_transcript(guid, transcript)")

