import os
import json
import asyncio
import discord
from datetime import datetime, timedelta, timezone

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

TARGET_CHANNEL_ID = 1475990996075544758

allowed = {"1", "2", "3", "4", "5", "6", "8", "9", "10"}

STATS_FILE = "stats.json"
today_ratings = []  # list of {"rating": int, "author": str}
midnight_task = None


def load_yesterday_avg():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            return json.load(f).get("yesterday_avg")
    return None


def save_yesterday_avg(avg):
    with open(STATS_FILE, "w") as f:
        json.dump({"yesterday_avg": avg}, f)


def build_stats_message(is_daily=False):
    if not today_ratings:
        return "📊 No ratings yet today."

    ratings = [r["rating"] for r in today_ratings]
    avg = sum(ratings) / len(ratings)
    yesterday_avg = load_yesterday_avg()
    highest = max(today_ratings, key=lambda x: x["rating"])
    lowest = min(today_ratings, key=lambda x: x["rating"])

    delta_str = ""
    if yesterday_avg is not None:
        delta = avg - yesterday_avg
        if delta > 0:
            delta_str = f" (+{delta:.1f} vs yesterday)"
        elif delta < 0:
            delta_str = f" ({delta:.1f} vs yesterday)"
        else:
            delta_str = " (same as yesterday)"

    title = "📊 **Daily Summary**" if is_daily else "📊 **Stats so far today**"

    return (
        f"{title}\n"
        f"Average: **{avg:.1f}**{delta_str}\n"
        f"Participants: **{len(today_ratings)}**\n"
        f"Highest rated day: **{highest['rating']}** — {highest['author']}\n"
        f"Lowest rated day: **{lowest['rating']}** — {lowest['author']}\n"
        f"-# Type **stats** in this channel anytime to see current stats."
    )


async def send_daily_stats():
    global today_ratings
    channel = client.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        return
    await channel.send(build_stats_message(is_daily=True))
    if today_ratings:
        ratings = [r["rating"] for r in today_ratings]
        save_yesterday_avg(sum(ratings) / len(ratings))
    today_ratings = []


async def midnight_loop():
    await client.wait_until_ready()
    while True:
        now = datetime.now(timezone.utc)
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await asyncio.sleep((tomorrow - now).total_seconds())
        await send_daily_stats()


@client.event
async def on_ready():
    global today_ratings, midnight_task
    print(f'Logged in as {client.user}')
    channel = client.get_channel(TARGET_CHANNEL_ID)
    if channel:
        # Delete invalid messages from full history
        async for message in channel.history(limit=None):
            if message.author == client.user:
                continue
            if message.content.strip() not in allowed:
                await message.delete()

        # Populate today's ratings from messages sent since midnight UTC
        today_ratings = []
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        async for message in channel.history(limit=None, after=today_start):
            if message.author == client.user:
                continue
            if message.content.strip() in allowed:
                today_ratings.append({
                    "rating": int(message.content.strip()),
                    "author": message.author.display_name
                })

        await channel.send("⚠️ Only numbers 1–10 are allowed in this channel. The number 7 is excluded! Type **stats** to see today's stats.")

    if midnight_task is None:
        midnight_task = asyncio.create_task(midnight_loop())


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    if message.content.strip().lower() == "stats":
        await message.delete()
        await message.channel.send(build_stats_message(is_daily=False))
        return

    if message.content.strip() not in allowed:
        await message.delete()
        try:
            await message.author.send("❌ Only numbers 1–10 (excluding 7) are allowed in that channel!")
        except discord.Forbidden:
            pass
    else:
        today_ratings.append({
            "rating": int(message.content.strip()),
            "author": message.author.display_name
        })


client.run(os.environ["DISCORD_TOKEN"])
