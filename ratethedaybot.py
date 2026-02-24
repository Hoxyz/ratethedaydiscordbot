import discord

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

TARGET_CHANNEL_ID = 1475990996075544758  # Replace with your channel ID

allowed = {"1", "2", "3", "4", "5", "6", "8", "9", "10"}

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    channel = client.get_channel(TARGET_CHANNEL_ID)
    if channel:
        await channel.send("⚠️ Only numbers 1–10 are allowed in this channel. The number 7 is excluded!")

@client.event
async def on_message(message):
    if message.author == client.user:  # Ignore the bot's own messages
        return

    if message.channel.id != TARGET_CHANNEL_ID:
        return

    if message.content.strip() not in allowed:
        await message.delete()
        try:
            await message.author.send("❌ Only numbers 1–10 (excluding 7) are allowed in that channel!")
        except discord.Forbidden:
            pass

client.run("MTQ3NTk5MTYwNTc5NzQ1Mzg5NA.GIzD9K.Cikf_-qu6CFuUDj2zuvD96uvPDNWmIOGqfXl10")