# Upwork Job Alert Telegram Bot

This project provides a Telegram bot that monitors Upwork search result pages via the [Qoest Scraping API](https://developers.qoest.com/docs/qoest-scraping-api/upwork-scraping/) and delivers real-time notifications when new jobs are posted.

## Features

- Save any Upwork search URL under a friendly name.
- View the last five jobs found for a saved search at any time.
- Receive automatic notifications with job title, summary, rate, client location, and a direct link to apply when new jobs appear.
- Manage multiple saved searches per chat.

## Prerequisites

1. **Python 3.10+**
2. **Telegram Bot Token** – Obtain one from [@BotFather](https://t.me/BotFather).
3. **Qoest API Key** – Create one following the [Qoest dashboard instructions](https://developers.qoest.com/docs/qoest-scraping-api/upwork-scraping/).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

The bot reads configuration from environment variables. You can create a `.env` file in the project root to avoid exporting them manually:

```env
TELEGRAM_BOT_TOKEN=your-telegram-token
QOEST_API_KEY=your-qoest-api-key
# Optional overrides
# QOEST_BASE_URL=https://api.qoest.com/upwork/jobs
# BOT_STORAGE_PATH=bot/data/watches.json
# POLL_INTERVAL_SECONDS=60
```

> **Note:** The bot persists chat configuration in `bot/data/watches.json`. Ensure the process can read and write to this location.

## Running the Bot

```bash
python bot/bot.py
```

Once the bot is running, open Telegram and interact with it:

- `/start` – Display help text.
- `/add ux-design https://www.upwork.com/...` – Save a search URL.
- `/list` – Show all saved searches.
- `/show ux-design` – Show the five most recent jobs for the saved search.
- `/remove ux-design` – Delete the saved search.

New job posts that were not previously seen will be pushed automatically every polling cycle (default: 60 seconds).

## How It Works

1. When you add a search link, the bot uses the Qoest API to validate the URL and stores the five latest job IDs. This prevents spam from historical posts.
2. A background job polls each saved search on a schedule. If previously unseen job IDs are detected, the bot sends formatted notifications immediately.
3. All data is stored per chat, so different users or groups can maintain independent watch lists.

## Troubleshooting

- **No messages received?** Double-check that your bot is running and that the Telegram token is correct.
- **Qoest errors?** Make sure the API key is valid and has access to the Upwork scraping endpoint.
- **Permission issues writing `watches.json`?** Update `BOT_STORAGE_PATH` to a writable location or adjust file permissions.

## Development Notes

- The Qoest client expects responses that either wrap job data inside a `data` array or return an array directly. Adjust `QoestClient` if your account returns a different payload structure.
- The polling interval can be tuned through the `POLL_INTERVAL_SECONDS` environment variable.
- Extend the bot easily by adding more commands or richer message formatting inside `bot/bot.py`.
