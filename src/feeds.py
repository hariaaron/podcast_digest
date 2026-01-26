import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import feedparser
import pytz
import yaml
from dateutil import parser as dateparser

from . import storage


CONFIG_FEEDS = os.path.join(os.path.dirname(__file__), "..", "config", "feeds.yml")


def load_feed_urls() -> List[str]:
	"""Load feed URLs from config/feeds.yml. Expected format: a YAML list of URLs."""
	if not os.path.exists(CONFIG_FEEDS):
		return []
	try:
		with open(CONFIG_FEEDS, "r", encoding="utf-8") as f:
			data = yaml.safe_load(f) or []
			if isinstance(data, list):
				return [str(x).strip() for x in data if x]
	except Exception:
		pass
	return []


def _entry_guid(entry: Dict[str, Any]) -> Optional[str]:
	# Prefer id, then guid, then link, then enclosure href
	for key in ("id", "guid", "link"):
		if key in entry and entry[key]:
			return str(entry[key])
	# enclosure
	enclosures = entry.get("enclosures") or entry.get("links")
	if enclosures:
		for e in enclosures:
			href = e.get("href") or e.get("url")
			if href:
				return str(href)
	return None


def _entry_audio_url(entry: Dict[str, Any]) -> Optional[str]:
	enclosures = entry.get("enclosures") or entry.get("links")
	if enclosures:
		for e in enclosures:
			if e.get("type", "").startswith("audio") or e.get("rel") == "enclosure":
				return e.get("href") or e.get("url")
	return None


def _parse_published(entry: Dict[str, Any]) -> Optional[datetime]:
	# Try published, published_parsed, updated
	for key in ("published", "updated", "pubDate"):
		val = entry.get(key)
		if val:
			try:
				dt = dateparser.parse(val)
				if not dt.tzinfo:
					dt = dt.replace(tzinfo=pytz.UTC)
				return dt
			except Exception:
				pass
	# feedparser may provide a struct_time
	struct = entry.get("published_parsed") or entry.get("updated_parsed")
	if struct:
		try:
			dt = datetime(*struct[:6], tzinfo=pytz.UTC)
			return dt
		except Exception:
			pass
	return None


def find_new_episodes(
	feed_urls: List[str], max_episode_age_days: int = 7, force_latest_n: int = 0
) -> List[Dict[str, Any]]:
	"""Fetch feeds and return list of new episode metadata not present in state.

	Each returned dict contains at least: `guid`, `title`, `link`, `published`, `audio_url`, `summary`.
	"""
	existing = storage.list_episodes()
	now = datetime.now(pytz.UTC)
	max_age = timedelta(days=max_episode_age_days)
	new: List[Dict[str, Any]] = []

	for url in feed_urls:
		try:
			feed = feedparser.parse(url)
		except Exception as e:
			print(f"failed to parse feed {url}: {e}")
			continue

		entries = feed.entries or []
		# if forcing latest N, slice
		if force_latest_n and force_latest_n > 0:
			entries = entries[: force_latest_n]

		for entry in entries:
			guid = _entry_guid(entry) or entry.get("title")
			if not guid:
				continue
			if guid in existing:
				continue

			published = _parse_published(entry)
			if published:
				age = now - published
				if age > max_age:
					# skip old episodes
					continue

			audio_url = _entry_audio_url(entry)

			item = {
				"guid": guid,
				"title": entry.get("title"),
				"link": entry.get("link"),
				"published": published.isoformat() if published else None,
				"audio_url": audio_url,
				"summary": entry.get("summary") or entry.get("description"),
				"feed": feed.feed.get("title") if hasattr(feed, "feed") else None,
			}
			new.append(item)

	return new


if __name__ == "__main__":
	# simple CLI for local testing
	urls = load_feed_urls()
	if not urls:
		print("No feeds configured in config/feeds.yml")
	else:
		new_eps = find_new_episodes(urls)
		print(f"Found {len(new_eps)} new episodes")
		for e in new_eps:
			print(f"- {e['title']} ({e['guid']})")

