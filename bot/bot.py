from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    AIORateLimiter,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    ContextTypes,
)

from config import Settings
from qoest_client import JobPost, QoestClient
from storage import Storage, WatchEntry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = (
        "Available commands:\n"
        "/add <name> <url> - Save an Upwork search URL\n"
        "/list - List all saved searches\n"
        "/show <name> - Show the last 5 jobs for a saved search\n"
        "/remove <name> - Delete a saved search\n"
    )
    await update.message.reply_text(
        "Welcome! Send me an Upwork search link with /add to start monitoring new jobs.\n\n" + commands
    )


async def add_watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /add <name> <url>")
        return
    name = context.args[0]
    url = context.args[1]
    storage: Storage = context.application.bot_data["storage"]
    client: QoestClient = context.application.bot_data["qoest_client"]
    chat_id = update.effective_chat.id
    try:
        jobs = await asyncio.to_thread(client.fetch_jobs, url, 5)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to fetch jobs for new watch")
        await update.message.reply_text(f"Could not validate the URL: {exc}")
        return

    initial_ids = [job.id for job in jobs]
    try:
        await storage.add_watch(chat_id, name, url, last_seen_ids=initial_ids)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return

    await update.message.reply_text(f"Saved watch '{name}'. I'll notify you about new jobs as they appear.")

    if jobs:
        await send_jobs(update, name, jobs, header=f"Here are the latest {min(len(jobs), 5)} jobs for '{name}':")


async def list_watches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    storage: Storage = context.application.bot_data["storage"]
    watches = await storage.list_watches(update.effective_chat.id)
    if not watches:
        await update.message.reply_text("No watches saved yet. Use /add <name> <url> to add one.")
        return
    lines = [f"• {watch.name}: {watch.url}" for watch in watches]
    await update.message.reply_text("Saved watches:\n" + "\n".join(lines))


async def show_watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /show <name>")
        return
    name = context.args[0]
    storage: Storage = context.application.bot_data["storage"]
    client: QoestClient = context.application.bot_data["qoest_client"]
    watch = await storage.get_watch(update.effective_chat.id, name)
    if not watch:
        await update.message.reply_text(f"No watch named '{name}' found.")
        return
    try:
        jobs = await asyncio.to_thread(client.fetch_jobs, watch.url, 5)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to fetch jobs for /show")
        await update.message.reply_text(f"Could not fetch jobs: {exc}")
        return
    await send_jobs(update, name, jobs, header=f"Latest jobs for '{name}':")


async def remove_watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /remove <name>")
        return
    name = context.args[0]
    storage: Storage = context.application.bot_data["storage"]
    removed = await storage.remove_watch(update.effective_chat.id, name)
    if removed:
        await update.message.reply_text(f"Removed watch '{name}'.")
    else:
        await update.message.reply_text(f"No watch named '{name}' found.")


async def send_jobs(update: Update, name: str, jobs: List[JobPost], header: str | None = None) -> None:
    if not jobs:
        await update.message.reply_text(f"No jobs found for '{name}'.")
        return
    chunks: List[str] = []
    if header:
        chunks.append(header)
    for job in jobs[:5]:
        location = job.client_location or "Unknown location"
        chunks.append(
            "\n".join(
                [
                    f"<b>{job.title}</b>",
                    job.short_description(),
                    job.rate,
                    f"Client location: {location}",
                    f"<a href=\"{job.url}\">Apply on Upwork</a>",
                ]
            )
        )
    message = "\n\n".join(chunks)
    await update.message.reply_html(message, disable_web_page_preview=True)


async def poll_watches(context: CallbackContext) -> None:
    storage: Storage = context.application.bot_data["storage"]
    client: QoestClient = context.application.bot_data["qoest_client"]
    all_watches = await storage.all_watches()

    for chat_id, watches in all_watches.items():
        for watch in watches:
            try:
                jobs = await asyncio.to_thread(client.fetch_jobs, watch.url, 10)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to poll watch %s for chat %s: %s", watch.name, chat_id, exc)
                continue
            new_jobs = [job for job in jobs if job.id not in watch.last_seen_ids]
            if not new_jobs:
                continue
            # Update last seen IDs keeping a buffer
            latest_ids = list(dict.fromkeys([job.id for job in jobs]))[:20]
            watch.last_seen_ids = latest_ids
            await storage.update_watch(chat_id, watch)
            bot = context.application.bot
            for job in reversed(new_jobs):  # send oldest new job first
                text = "\n".join(
                    [
                        f"<b>{job.title}</b>",
                        job.short_description(),
                        job.rate,
                        f"Client location: {job.client_location or 'Unknown location'}",
                        f"<a href=\"{job.url}\">Apply on Upwork</a>",
                    ]
                )
                await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


async def main() -> None:
    settings = Settings.from_env()
    storage = Storage(settings.storage_path)
    await storage.load()
    client = QoestClient(settings.qoest_api_key, settings.qoest_base_url)

    application = (
        ApplicationBuilder()
        .token(settings.telegram_token)
        .rate_limiter(AIORateLimiter())
        .build()
    )

    application.bot_data["storage"] = storage
    application.bot_data["qoest_client"] = client

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_watch))
    application.add_handler(CommandHandler("list", list_watches))
    application.add_handler(CommandHandler("show", show_watch))
    application.add_handler(CommandHandler("remove", remove_watch))

    application.job_queue.run_repeating(poll_watches, interval=settings.poll_interval_seconds, first=10)

    await application.initialize()
    await application.start()
    logger.info("Bot started. Listening for updates...")
    try:
        await application.updater.start_polling()
        await application.updater.idle()
    finally:
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
