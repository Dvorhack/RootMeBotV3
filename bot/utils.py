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

async def scoreboard_msg(ctx: commands.Context, users: Users) -> None:
    users.sort(key=lambda x: x.score, reverse=True)
    message = ""
    for user in users:
        message += f"{user.name} has {user.score} points\n"
    await ctx.send(message)

async def too_many_users_msg(ctx: commands.Context, name) -> None:
    message = f"Too many users found for name {name}"
    await ctx.send(message)

async def who_solved_msg(ctx: commands.Context, chall_name, solvers: Users) -> None:
    message = f"Users who solved {chall_name}\n"
    for x in solvers:
        message += f"--- {x.name}\n"
    await ctx.send(message)