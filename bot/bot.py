import discord
from discord.ext import tasks, commands, tasks
from discord import app_commands
import os, json
from typing import List, Optional
from discord.channel import TextChannel
import traceback
import datetime

from db_manager import DBManager
from rm_api import RootMeAPI
from constants import UPDATE_CHALLS_DELAY, UPDATE_SOLVES_DELAY
import asyncio
import utils
from errors import *


class MultipleUserButton(discord.ui.Select):
    def __init__(self, users):

        options = [
                discord.SelectOption(label=i['nom'], description=f'ID {i["id_auteur"]}', value=i["id_auteur"]) for i in users
        ]

        super().__init__(placeholder='Which user :', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction): 
        await interaction.response.send_message(f"Button clicked")
        await self.view.add_user(self.values[0])

class MultipleUserFoundView(discord.ui.View):
    def __init__(self, channel: TextChannel, users, api: RootMeAPI):
        super().__init__()
        self.channel = channel
        self.users = users
        self.api = api

        self.add_item(MultipleUserButton(users))
    async def add_user(self, idx: str):
        auteur = next(filter(lambda x: x['id_auteur'] == idx, self.users))
        await self.api.loadUser(idx=int(auteur['id_auteur']))
        message_title = 'Success'
        message = f'{auteur["nom"]} was successfully added :+1:'
        embed = discord.Embed(color=discord.Color.green(), title=message_title, description=message)
        await self.channel.send(embed=embed)


class CustomBot(commands.Bot):
    def __init__(
        self,
        *args,
        initial_extensions: List[str],
        db_pool: DBManager,
        api: RootMeAPI,
        testing_guild_id: Optional[int] = None,
        bot_channel_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.db_pool = db_pool
        self.api = api
        self.testing_guild_id = testing_guild_id
        self.bot_channel_id = int(bot_channel_id)
        self.initial_extensions = initial_extensions
        self.init_done = False

    async def init_db(self) -> None:
        """Checks if the database seems populated or not (first run)"""
        await self.wait_until_ready()
        print("Starting...")
        channel = self.get_channel(self.bot_channel_id)

        # await self.db_pool.create_scoreboard('global')
        # print('Nombre chall',self.db_pool.count_challenges())
        #if self.db_pool.count_challenges() < 450:
        
        await self.change_presence(status=discord.Status.online, activity=discord.Game("Busy: fetching challenges"))
        await utils.init_start_msg(channel)
        await self.api.loadAllChallenges()
        await utils.init_end_msg(channel)
        await self.change_presence(status=discord.Status.online, activity=discord.Game("I'm ready"))

        self.init_done = True

    async def cron_check_challs(self) -> None:
        """Checks for new challs"""

        await self.wait_until_ready()
        channel = self.get_channel(self.bot_channel_id)

        while not self.init_done:
            await asyncio.sleep(1)

        while True:
            await asyncio.sleep(UPDATE_CHALLS_DELAY)
            try:
                # new_challs: liste des nouveaux challenges, au format JSON (fetch depuis l'api)
                new_challs = await self.api.loadAllChallenges()
                if len(new_challs):
                    full_chall_list = [self.db_pool.getChallengeById(x) for x in new_challs]
                    await utils.new_chall(channel, full_chall_list)
            except Exception:
                # utils.panic_message(channel, traceback.format_exc())
                pass

            print(f"{datetime.datetime.now()} | OK challs")

    async def cron_check_solves(self) -> None:
        """Checks for new challs"""

        await self.wait_until_ready()
        channel = self.get_channel(self.bot_channel_id)

        while not self.init_done:
            await asyncio.sleep(1)

        while True:
            await asyncio.sleep(UPDATE_SOLVES_DELAY)
            try:
                for user in self.db_pool.getAllUsers():
                    async for solve in self.api.updateUser(user):
                        await utils.new_solves(channel, solve)
            except Exception:
                # await utils.panic_message(channel, traceback.format_exc())
                pass

            print(f"{datetime.datetime.now()} | OK solves")


    async def start(self, *args):
        await self.api.loadAllChallenges()
        return await super().start(*args)
    
    async def choose_user_autocomplete(
            self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:

        if current == '':
            users = self.db_pool.getAllUsers()
        else:
            users = self.db_pool.getUserByName(current)

        choices = [app_commands.Choice(name=u.name, value=u.name) for u in users[:25]]
        return sorted(choices, key=lambda choice: choice.name.lower())

    async def choose_challenge_autocomplete(
            self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:

        if current == '':
            challenges =  []
        else:
            challenges = self.db_pool.getChallengesByName(current)

        choices = [app_commands.Choice(name=u.title, value=u.title) for u in challenges[:25]]
        return sorted(choices, key=lambda choice: choice.name.lower())


    def add_commands(self):

        @self.check
        def is_init_done(ctx):
            if not self.init_done:
                raise InitNotDone()
            return self.init_done

        @self.hybrid_command(name="help", description="available commands")
        async def help(ctx: commands.Context):
            print(self.all_commands)
            await utils.help_msg(ctx, self.all_commands.items())

        @self.hybrid_command(name="who_solved", description="who solved a specifique challenge")
        @app_commands.autocomplete(name=self.choose_challenge_autocomplete)
        async def who_solved(ctx: commands.Context, name: str):
            name = discord.utils.escape_markdown(name)
            try:
                chall_name, solvers = self.db_pool.who_solved(name)
            except ChallengeNotFound:
                await utils.challenge_not_found(ctx, name)
            except FoundMultipleChallenges:
                await utils.too_many_challenges(ctx, name)
            else:
                await utils.who_solved_msg(ctx, chall_name, solvers)


        @self.hybrid_command(name="sync", description="lol")
        async def sync(ctx: commands.Context):
            await self.sync_guid()
            await ctx.send("Synced !")
        
        # @self.hybrid_command(name="update_challs", description="on garde ou pas ?")
        # async def update_challs(ctx: commands.context):
        #     await ctx.defer()
        #     channel = self.get_channel(self.bot_channel_id)
        #     # new_challs: liste des nouveaux challenges, au format JSON (fetch depuis l'api)
        #     new_challs = await self.api.loadAllChallenges()
        #     if len(new_challs):
        #         print(new_challs)
        #         await utils.new_chall(channel, new_challs)
        #     await ctx.reply("Challenges updated successfully")
        
        # @self.hybrid_command(name="update_solves", description="on garde ou pas ?")
        # async def update_solves(ctx: commands.context):
        #     await ctx.defer()
        #     channel = self.get_channel(self.bot_channel_id)
        #     for user in self.db_pool.getAllUsers():
        #         solves_data = await self.api.updateUser(user)
        #         if solves_data:
        #             await utils.new_solves(ctx, solves_data)
        
        @self.hybrid_command(name="scoreboard", description="scoreboard of registered users")
        async def scoreboard(ctx: commands.Context):
            users = self.db_pool.getAllUsers()
            await utils.scoreboard_msg(ctx, users)

        @self.hybrid_command(name="today", description="today's scoreboard")
        async def today(ctx: commands.Context):
            users = self.db_pool.getTodayScoreboard()
            await utils.today_msg(ctx, users)
        
        @self.hybrid_command(name="graph", description="plot users score in last N days")
        async def graph(ctx: commands.Context, n_days: int):
            max_days = 4000
            if n_days <= 0:
                await utils.negative_days(ctx)
            elif n_days > max_days:
                await utils.too_many_days(ctx, max_days)
            else:
                last_solves = self.db_pool.getLastSolves(n_days)
                await utils.graph_msg(ctx, last_solves, n_days)

        @self.hybrid_command(name="last_solves", description="last solves for a hacker")
        @app_commands.autocomplete(name_or_id=self.choose_user_autocomplete)
        async def last_solves(ctx: commands.Context, name_or_id: str, n_days: int):
            await ctx.defer()
            name_or_id = discord.utils.escape_markdown(name_or_id)
            user = self.db_pool.getUserById(name_or_id)
            if not user: 
                user = self.db_pool.getUserByName(name_or_id)
            if user:
                user = user[0]
                # user_stats = self.db_pool.getStats(user.id)    
                solves = self.db_pool.getLastSolvesByUser(user.id, n_days)
                await utils.last_solves_msg(ctx, user, solves, n_days)
            else:
                # await ctx.reply(f"User {name} not found in database")
                await utils.user_not_found_in_db(ctx, name_or_id)


        @self.hybrid_command(name="add_user", description="register a user either by it's name or uid")
        async def add_user(ctx: commands.Context, name_or_id):
            await ctx.defer()
            name_or_id = discord.utils.escape_markdown(name_or_id)
            users = await self.api.fetchUserByName(name_or_id)
            if len(users) == 1:
                await self.api.loadUser(idx=int(users["0"]["id_auteur"]))
                await utils.added_ok(ctx, users["0"]['nom'])
            elif len(users) > 25:
                await utils.too_many_users_msg(ctx, name_or_id)
            elif len(users) > 1:
                await self.possible_users(ctx, users.values())
            else:  # no user found => try by id
                users = await self.api.fetchUserById(name_or_id)
                if users:
                    await self.api.loadUser(idx=name_or_id)
                    await utils.added_ok(ctx, users['nom'])
                else:
                    await utils.user_not_found(ctx, name_or_id, by_id=False)

        @self.hybrid_command(name="remove_user", description="remove a user from db")
        @app_commands.autocomplete(name_or_id=self.choose_user_autocomplete)
        async def remove_user(ctx: commands.Context, name_or_id: str):
            name_or_id = discord.utils.escape_markdown(name_or_id)
            user = self.db_pool.getUserById(name_or_id)
            if not user:
                user = self.db_pool.getUserByName(name_or_id)
            if user:
                user = user[0]
                self.db_pool.deleteUserByName(user.name)
                await utils.removed_ok(ctx, user.name)
            else:
                # await ctx.reply(f"User {input} not found in database")
                await utils.user_not_found_in_db(ctx, name_or_id)

        @self.hybrid_command(name="profile", description="show many info about a user")
        @app_commands.autocomplete(name_or_id=self.choose_user_autocomplete)
        async def profile(ctx: commands.Context, name_or_id: str):
            await ctx.defer()
            name_or_id = discord.utils.escape_markdown(name_or_id)
            user = self.db_pool.getUserById(name_or_id)
            if not user: 
                user = self.db_pool.getUserByName(name_or_id)
            if user:
                user = user[0]
                user_stats = self.db_pool.getStats(user.id)    
                await utils.profile(ctx, user, user_stats)
            else:
                # await ctx.reply(f"User {name} not found in database")
                await utils.user_not_found_in_db(ctx, name_or_id)

        @self.hybrid_command(name="compare", description="compare progression of two users")
        @app_commands.autocomplete(input1=self.choose_user_autocomplete, input2=self.choose_user_autocomplete)
        async def compare(ctx: commands.Context, input1, input2):
            input1 = discord.utils.escape_markdown(input1)
            input2 = discord.utils.escape_markdown(input2)
            user1 = self.db_pool.getUserById(input1)
            if not user1: 
                user1 = self.db_pool.getUserByName(input1)

            user2 = self.db_pool.getUserById(input2)
            if not user2: 
                user2 = self.db_pool.getUserByName(input2)
            
            if user1 and user2:
                user1, user2 = user1[0], user2[0]
                user1_stats = self.db_pool.getStats(user1.id)
                user2_stats = self.db_pool.getStats(user2.id)
                await utils.compare_graph(ctx, user1, user1_stats, user2, user2_stats)
            else:
                if not user1:
                    # await ctx.reply(f"User {input1} not found in database")
                    await utils.user_not_found_in_db(ctx, input1)
                if not user2:
                    # await ctx.reply(f"User {input2} not found in database")
                    await utils.user_not_found_in_db(ctx, input2)

    async def possible_users(self, channel: TextChannel, auteurs) -> None:
            message = f'Multiple users found :'
            view = MultipleUserFoundView(channel.message.channel, auteurs, self.api)
            await channel.send(message, view=view)

    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, InitNotDone):
            await utils.init_not_done_msg(ctx)
            return
        
        if isinstance(error, TooManyUsers):
            await utils.too_many_users_msg(ctx, error.name)
            return

        debug = self.get_channel(int(self.bot_channel_id))
        formatted_lines = traceback.format_exception(type(error), error, error.__traceback__)
        traceback_str = ''.join(formatted_lines)
        printed = 0
        print(traceback_str)
        while printed < len(traceback_str):
            size = 1992 if (len(traceback_str)-printed) > 1992 else len(traceback_str)-printed
            await debug.send('```\n'+traceback_str[printed:printed+size]+'\n```')
            printed += size

    async def on_ready(self):
        debug = self.get_channel(self.bot_channel_id)
        print("Bot ready")
        # await debug.send("Bot ready")
        # await self.change_presence(status=discord.Status.online, activity=discord.Game("Hacking stuff..."))

    async def sync_guid(self):
        if self.testing_guild_id:
            guild = discord.Object(self.testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            # followed by syncing to the testing guild.
            await self.tree.sync(guild=guild)
            print("guild synced")


    async def setup_hook(self) -> None:

        # here, we are loading extensions prior to sync to ensure we are syncing interactions defined in those extensions.

        # for extension in self.initial_extensions:
        #     await self.load_extension(extension)

        # In overriding setup hook,
        # we can do things that require a bot prior to starting to process events from the websocket.
        # In this case, we are using this to ensure that once we are connected, we sync for the testing guild.
        # You should not do this for every guild or for global sync, those should only be synced when changes happen.
        await self.sync_guid()

        # This would also be a good place to connect to our database and
        # load anything that should be in memory prior to handling events.

    async def start(self, *args, **kwargs):
        self.loop.create_task(self.init_db())
        self.loop.create_task(self.cron_check_challs())
        self.loop.create_task(self.cron_check_solves())

        await super().start(*args, **kwargs)
