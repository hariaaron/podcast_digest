import os
import tempfile
import urllib.request
from typing import Optional, Dict, Any

import openai

from . import storage


def _download_to_temp(url: str, max_mb: int = 100) -> Optional[str]:
	"""Download URL to a temporary file. Returns path or None on failure or if too large."""
	try:
		with urllib.request.urlopen(url, timeout=30) as resp:
			info = resp.info()
			length = resp.getheader("Content-Length")
			if length:
				size = int(length)
				if size > max_mb * 1024 * 1024:
					return None

			fd, tmp_path = tempfile.mkstemp(suffix=".audio")
			os.close(fd)
			with open(tmp_path, "wb") as out:
				chunk_size = 64 * 1024
				total = 0
				while True:
					chunk = resp.read(chunk_size)
					if not chunk:
						break
					out.write(chunk)
					total += len(chunk)
					if total > max_mb * 1024 * 1024:
						out.close()
						try:
							os.remove(tmp_path)
						except Exception:
							pass
						return None
			return tmp_path
	except Exception:
		return None


def transcribe_from_url(
	guid: str,
	url: str,
	model: str = "gpt-4o-mini-transcribe",
	max_download_mb: int = 100,
) -> Optional[Dict[str, Any]]:
	"""Download audio and transcribe using OpenAI API. Caches result in state under episodes[guid].transcript."""
	# check cache
	episodes = storage.list_episodes()
	ep = episodes.get(guid, {})
	if ep.get("transcript"):
		return {"transcript": ep["transcript"], "cached": True}

	tmp = _download_to_temp(url, max_mb=max_download_mb)
	if not tmp:
		return None

	try:
		openai.api_key = os.environ.get("OPENAI_API_KEY")
		with open(tmp, "rb") as f:
			# modern openai-python may expose Audio.transcribe; we try a generic path
			try:
				resp = openai.Audio.transcribe(model=model, file=f)
			except Exception:
				# fallback to ChatCompletions style (older SDKs) - attempt to call 'transcriptions' endpoint
				resp = openai.Transcription.create(model=model, file=f)

		# resp may be dict-like with 'text'
		text = None
		if isinstance(resp, dict):
			text = resp.get("text") or resp.get("transcript")
		else:
			# try attribute
			text = getattr(resp, "text", None) or getattr(resp, "transcript", None)

		if text:
			storage.update_episode(guid, {"transcript": text})
			return {"transcript": text, "cached": False}
	finally:
		try:
			os.remove(tmp)
		except Exception:
			pass

	return None


if __name__ == "__main__":
	print("asr module. Use transcribe_from_url(guid, url)")

