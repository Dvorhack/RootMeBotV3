import discord
import aiohttp
import code
import traceback
from html import unescape

from discord.utils import escape_markdown
from discord.channel import TextChannel

# from database.manager import DatabaseManager

# from classes.enums import Color, Stats
# from classes.views import ManageView, ScoreboardView, MultipleChallFoundView, MultipleUserFoundView
# from constants import PING_DEV, PING_ROLE_ROOTME

from db_manager import User
# from db_manager import Scoreboard TODO
from db_manager import Challenge
from db_manager import Solve

from discord.ext import commands


Users = list[User]
Challenges = list[Challenge]

async def init_start_msg(channel: TextChannel) -> None:
    """First time running message"""
    message = f'I am fetching the challenges'
    await channel.send(message)

async def init_end_msg(channel: TextChannel) -> None:
    """Initialization complete"""
    message = f'init done, you can start use me'
    await channel.send(message)

async def init_not_done_msg(ctx: commands.Context) -> None:
    message = f'init not done, please wait'
    await ctx.send(message)