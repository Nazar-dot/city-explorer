from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Mapping, MutableMapping, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class JobPost:
    id: str
    title: str
    description: str
    rate: str
    client_location: Optional[str]
    url: str

    def short_description(self, max_length: int = 280) -> str:
        description = " ".join(self.description.split())
        if len(description) <= max_length:
            return description
        return description[: max_length - 3].rstrip() + "..."


class QoestClient:
    """Minimal Qoest Upwork Scraping API client."""

    def __init__(self, api_key: str, base_url: str = "https://api.qoest.com/upwork/jobs") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def fetch_jobs(self, search_url: str, limit: int = 10) -> List[JobPost]:
        params = {"url": search_url, "limit": limit}
        headers = {
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }
        response = requests.get(self.base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        jobs_payload = self._extract_jobs_payload(data)
        return [self._convert_job(raw) for raw in jobs_payload]

    def _extract_jobs_payload(self, payload: Mapping[str, object]) -> List[Mapping[str, object]]:
        if "data" in payload and isinstance(payload["data"], list):
            return payload["data"]  # type: ignore[return-value]
        if isinstance(payload, list):
            return payload  # type: ignore[return-value]
        raise ValueError("Unexpected Qoest API response format")

    def _convert_job(self, raw: MutableMapping[str, object]) -> JobPost:
        job_id = self._extract_first(raw, ["id", "job_id", "uid", "url"])
        title = str(self._extract_first(raw, ["title", "job_title"]) or "Untitled job")
        description = str(
            self._extract_first(raw, ["description", "snippet", "job_description"]) or "No description provided"
        )
        url = str(self._extract_first(raw, ["url", "link", "job_url"]) or "")
        rate = self._format_rate(raw)
        location = self._extract_first(raw, ["client_location", "location", "country", "client_country"])
        return JobPost(
            id=str(job_id),
            title=title,
            description=description,
            rate=rate,
            client_location=str(location) if location else None,
            url=url,
        )

    def _format_rate(self, raw: Mapping[str, object]) -> str:
        hourly = self._extract_first(raw, ["hourly_rate", "hourly", "rate"])
        budget = self._extract_first(raw, ["budget", "fixed_price", "amount"])
        if hourly:
            return f"Hourly: {hourly}"
        if budget:
            return f"Fixed: {budget}"
        return "Rate unavailable"

    def _extract_first(self, raw: Mapping[str, object], keys: Iterable[str]) -> Optional[object]:
        for key in keys:
            if key in raw and raw[key]:
                return raw[key]
        return None


__all__ = ["QoestClient", "JobPost"]
