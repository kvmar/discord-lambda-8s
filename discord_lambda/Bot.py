import asyncio
import datetime
import os

import discord
from discord import Message, Guild
from discord.state import Channel

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

def edit_message(message_id: str, channel_id: str, guild_id: str):
    bot.run(os.environ.get('BOT_TOKEN'))
    loop = asyncio.get_event_loop()
    guild = loop.run_until_complete(fetch_guild(int(guild_id)))

    loop = asyncio.get_event_loop()
    channel = loop.run_until_complete(fetch_channel(guild, int(channel_id)))

    loop = asyncio.get_event_loop()
    msg = loop.run_until_complete(fetch_channel(channel, int(message_id)))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(edit_message(msg))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(close_bot())



async def fetch_guild(guild_id: int):
    return await bot.fetch_guild(int(guild_id))

async def fetch_channel(guild: Guild, channel_id: int):
    return await guild.fetch_channel(int(channel_id))

async def fetch_message(channel: Channel, message_id: int):
    return await channel.fetch_message(int(message_id))

async def edit_message(msg: Message):
    await msg.edit(content="edit" + str(datetime.datetime.now()))

async def close_bot():
    await bot.close()