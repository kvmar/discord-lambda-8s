import os

import discord

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
print(os.environ.values())
bot.run(os.environ.get('BOT_TOKEN'))

async def edit_message(message_id: str, channel_id: str, guild_id: str):
    guild = await bot.fetch_guild(int(guild_id))
    channel = await guild.fetch_channel(int(channel_id))
    msg = await channel.fetch_message(int(message_id))
    await msg.edit(content="edit")