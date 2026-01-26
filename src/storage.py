import json
import os
import tempfile
from typing import Any, Dict

STATE_DIR = os.path.join(os.path.dirname(__file__), "..", "state")
STATE_FILE = os.path.join(STATE_DIR, "state.json")


def _ensure_state_dir() -> None:
	os.makedirs(STATE_DIR, exist_ok=True)


def read_state() -> Dict[str, Any]:
	"""Read and return the JSON state file. Returns an empty dict if missing or invalid."""
	_ensure_state_dir()
	if not os.path.exists(STATE_FILE):
		return {}
	try:
		with open(STATE_FILE, "r", encoding="utf-8") as f:
			return json.load(f) or {}
	except Exception:
		return {}


def write_state(state: Dict[str, Any]) -> None:
	"""Atomically write the state dict to disk as JSON."""
	_ensure_state_dir()
	# write to a temp file in same dir then atomically replace
	fd, tmp_path = tempfile.mkstemp(dir=STATE_DIR)
	try:
		with os.fdopen(fd, "w", encoding="utf-8") as tmp:
			json.dump(state, tmp, ensure_ascii=False, indent=2)
			tmp.flush()
			os.fsync(tmp.fileno())
		os.replace(tmp_path, STATE_FILE)
	finally:
		if os.path.exists(tmp_path):
			try:
				os.remove(tmp_path)
			except Exception:
				pass


def update_episode(guid: str, data: Dict[str, Any]) -> None:
	"""Merge episode data into state under episodes[guid]."""
	state = read_state()
	episodes = state.setdefault("episodes", {})
	existing = episodes.get(guid, {})
	# shallow merge
	existing.update(data)
	episodes[guid] = existing
	state["episodes"] = episodes
	write_state(state)


def list_episodes() -> Dict[str, Any]:
	state = read_state()
	return state.get("episodes", {})

