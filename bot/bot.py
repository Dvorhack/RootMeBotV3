import discord
from discord.ext import tasks, commands
from discord import app_commands

class MyCog(commands.Cog):
    def __init__(self):
        self.index = 0
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=5.0)
    async def printer(self):
        print(self.index)
        self.index += 1

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.hybrid_command()
async def test(ctx):
    await ctx.send("This is a hybrid command!")

@bot.command()
async def getguild(ctx):
    id = ctx.message.guild.id
    await ctx.send(f"guild id = {id}")

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=1144008566957690990))
    await bot.change_presence(activity=discord.Game(name="Use the /help command!"))
    print("Ready!")

bot.run()
