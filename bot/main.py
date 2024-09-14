from dotenv import load_dotenv
import os
import discord
from discord.ext import tasks, commands
from discord import app_commands
import asyncio
import logging
import logging.handlers

from rm_api import RootMeAPI
from db_manager import DBManager
from bot import CustomBot


async def main():

    # When taking over how the bot process is run, you become responsible for a few additional things.

    # 1. logging

    # for this example, we're going to set up a rotating file logger.
    # for more info on setting up logging,
    # see https://discordpy.readthedocs.io/en/latest/logging.html and https://docs.python.org/3/howto/logging.html

    # logger = logging.getLogger('discord')
    # logger.setLevel(logging.DEBUG)

    # handler = logging.handlers.RotatingFileHandler(
    #     filename='discord.log',
    #     encoding='utf-8',
    #     maxBytes=32 * 1024 * 1024,  # 32 MiB
    #     backupCount=5,  # Rotate through 5 files
    # )
    # dt_fmt = '%Y-%m-%d %H:%M:%S'
    # formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    # handler.setFormatter(formatter)
    # logger.addHandler(handler)

    # Alternatively, you could use:
    discord.utils.setup_logging(level=logging.INFO, root=False)

    # One of the reasons to take over more of the process though
    # is to ensure use with other libraries or tools which also require their own cleanup.

    # Here we have a web client and a database pool, both of which do cleanup at exit.
    # We also have our bot, which depends on both of these.


    load_dotenv("./.env")
    ROOTME_API = os.getenv('ROOTME_API')
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    GUILD_ID = os.getenv('GUILD_ID')
    BOT_CHANNEL = os.getenv('BOT_CHANNEL')

    async with RootMeAPI(ROOTME_API) as api:
        # 2. We become responsible for starting the bot.

        exts = ['general', 'mod', 'dice']
        intents = discord.Intents.default()
        intents.message_content = True
        async with CustomBot(
            command_prefix='!',
            db_pool=api.db,
            api=api,
            initial_extensions=exts,
            intents=intents,
            testing_guild_id = GUILD_ID,
            bot_channel_id = BOT_CHANNEL
        ) as bot:
            bot.add_commands()

            await bot.start(DISCORD_TOKEN)


# For most use cases, after defining what needs to run, we can just tell asyncio to run it:
asyncio.run(main())