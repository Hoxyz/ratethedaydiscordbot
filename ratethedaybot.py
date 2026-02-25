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


def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            return json.load(f)
    return {}


def save_stats(data):
    with open(STATS_FILE, "w") as f:
        json.dump(data, f)


def build_stats_message(is_daily=False):
    if not today_ratings:
        return "📊 No ratings yet today."

    ratings = [r["rating"] for r in today_ratings]
    avg = sum(ratings) / len(ratings)
    yesterday_avg = load_stats().get("yesterday_avg")
    max_rating = max(ratings)
    min_rating = min(ratings)
    highest_names = ", ".join(r["author"] for r in today_ratings if r["rating"] == max_rating)
    lowest_names = ", ".join(r["author"] for r in today_ratings if r["rating"] == min_rating)

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
        f"Highest rated day: **{max_rating}** — {highest_names}\n"
        f"Lowest rated day: **{min_rating}** — {lowest_names}\n"
        f"-# Type **stats** for today's stats · **my stats** for your personal stats."
    )


def build_my_stats_message(name):
    stats = load_stats()
    user_data = stats.get("users", {}).get(name)
    today_user_ratings = [r["rating"] for r in today_ratings if r["author"] == name]

    if not user_data and not today_user_ratings:
        return f"📊 **{name}** hasn't rated any days yet."

    hist_sum = user_data["sum"] if user_data else 0
    hist_count = user_data["count"] if user_data else 0

    total_sum = hist_sum + sum(today_user_ratings)
    total_count = hist_count + len(today_user_ratings)
    avg = total_sum / total_count

    best = max(today_user_ratings + ([user_data["best"]] if user_data else []))
    worst = min(today_user_ratings + ([user_data["worst"]] if user_data else []))

    return (
        f"📊 **{name}'s stats**\n"
        f"All-time average: **{avg:.1f}** across **{total_count}** rating(s)\n"
        f"Personal best: **{best}** · Personal worst: **{worst}**"
    )


async def send_daily_stats():
    global today_ratings
    channel = client.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        return

    await channel.send(build_stats_message(is_daily=True))

    stats = load_stats()
    if today_ratings:
        ratings = [r["rating"] for r in today_ratings]
        stats["yesterday_avg"] = sum(ratings) / len(ratings)

        users = stats.get("users", {})
        for entry in today_ratings:
            name = entry["author"]
            rating = entry["rating"]
            if name not in users:
                users[name] = {"sum": 0, "count": 0, "best": rating, "worst": rating}
            users[name]["sum"] += rating
            users[name]["count"] += 1
            users[name]["best"] = max(users[name]["best"], rating)
            users[name]["worst"] = min(users[name]["worst"], rating)
        stats["users"] = users

    save_stats(stats)
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

        await channel.send("⚠️ Only numbers 1–10 are allowed in this channel. The number 7 is excluded! Type **stats** for today's stats · **my stats** for your personal stats.")

    if midnight_task is None:
        midnight_task = asyncio.create_task(midnight_loop())


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    content = message.content.strip().lower()

    if content == "stats":
        await message.delete()
        await message.channel.send(build_stats_message(is_daily=False))
        return

    if content == "my stats":
        await message.delete()
        await message.channel.send(build_my_stats_message(message.author.display_name))
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
