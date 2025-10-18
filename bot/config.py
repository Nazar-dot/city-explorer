from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = lambda: None


load_dotenv()


@dataclass
class Settings:
    telegram_token: str
    qoest_api_key: str
    qoest_base_url: str
    storage_path: Path
    poll_interval_seconds: int = 60

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        api_key = os.getenv("QOEST_API_KEY")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")
        if not api_key:
            raise RuntimeError("QOEST_API_KEY environment variable is required")
        base_url = os.getenv("QOEST_BASE_URL", "https://api.qoest.com/upwork/jobs")
        storage_path = Path(os.getenv("BOT_STORAGE_PATH", "bot/data/watches.json"))
        poll = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
        return cls(
            telegram_token=token,
            qoest_api_key=api_key,
            qoest_base_url=base_url,
            storage_path=storage_path,
            poll_interval_seconds=poll,
        )


__all__ = ["Settings"]
