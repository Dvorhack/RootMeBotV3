import discord
import aiohttp
import code
import traceback
from html import unescape

from discord.utils import escape_markdown
from discord.channel import TextChannel
import matplotlib.pyplot as plt
import io
from PIL import Image, ImageDraw, ImageFont
import requests

# from database.manager import DatabaseManager

# from classes.enums import Color, Stats
# from classes.views import ManageView, ScoreboardView, MultipleChallFoundView, MultipleUserFoundView
# from constants import PING_DEV, PING_ROLE_ROOTME

from db_manager import User
# from db_manager import Scoreboard TODO
from db_manager import Challenge
from db_manager import Solve

from discord.ext import commands
from discord import Color


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
    medals = {
        0: "🥇",
        1: "🥈",
        2: "🥉"
    }
    file = discord.File('resources/trophy.png', filename='trophy.png')  

    users.sort(key=lambda x: x.score, reverse=True)
    message_title = f'**Scoreboard**'

    embed = discord.Embed(color=Color.yellow(), title=message_title, description="")
    embed.add_field(name=" ", value=" ", inline=False)
    embed.set_thumbnail(url="attachment://trophy.png")
    for index, user in enumerate(users):
        if index < 3:
            medal = medals.get(index, "")
            embed.add_field(name=f"{medal} {user.name}",value=f"Points: {user.score}",inline=False)
        else :
            embed.add_field(name=f"#{index+1} {user.name}",value=f"Points: {user.score}",inline=False)

    await ctx.send(file=file, embed=embed)

async def too_many_users_msg(ctx: commands.Context, name) -> None:
    message = f"Too many users found for name {name}"
    await ctx.send(message)

async def added_ok(ctx: commands.Context, name) -> None:
    message_title = 'Success'
    message = f'{escape_markdown(name)} was successfully added :+1:'

    embed = discord.Embed(color=Color.green(), title=message_title, description=message)
    await ctx.reply(embed=embed)

async def who_solved_msg(ctx: commands.Context, chall_name, solvers: Users) -> None:
    message = f"Users who solved {chall_name}\n"
    for x in solvers:
        message += f"--- {x.name}\n"
    await ctx.send(message)

async def profile(ctx: commands.Context, user:User, stats) -> None:
    
    def create_text_image(title, value, width=350, height=200):
        border_thickness = -1
        img = Image.new('RGB', (width, height), color='#2b2d31')
        draw = ImageDraw.Draw(img)
        
        draw.rectangle(
            [(border_thickness, border_thickness), (width-border_thickness, height-border_thickness)],
            outline='black'
        )
        
        title_font = ImageFont.truetype("resources/LiberationSans-Bold.ttf", size=42)
        value_font = ImageFont.truetype("resources/LiberationSans-Bold.ttf", size=34)
        
        title_size = draw.textbbox((0, 0), title, font=title_font)
        draw.text((30, 30), title, fill='white', font=title_font)
        
        value_y = title_size[1] + 90
        draw.text((60, value_y), value, fill='#D3D3D3', font=value_font)

        draw.line([(40, value_y+10), (40, value_y+65)], fill='#D3D3D3', width=2)

        return img

    def create_pie_chart(sizes, center_text):
        fig, ax = plt.subplots(figsize=(2,2))
        fig.patch.set_facecolor("#2b2d31") 
        ax.pie(sizes,startangle=90,colors=['#2b2d31', '#66b3ff'],wedgeprops=dict(width=0.3, edgecolor='w'))
        
        ax.text(0, 0,center_text,ha='center',va='center',fontsize=20, fontweight='bold', color='white') 
        ax.axis('off')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        img = Image.open(buf)
        return img

    def img_concat_h(im1, im2):
        res = Image.new('RGB', (im1.width + im2.width, im1.height))
        res.paste(im1, (0, 0))
        res.paste(im2, (im1.width, 0))
        return res

    def concatenate_images(images, columns=2):

        img_width, img_height = images[0].size
        total_images = len(images)
        rows = (total_images + columns - 1) // columns
        final_width = columns * img_width
        final_height = rows * img_height
        
        final_image = Image.new('RGB', (final_width, final_height), color='#2b2d31')
        
        for index, img in enumerate(images):
            row = index // columns
            col = index % columns
            x = col * img_width
            y = row * img_height
            final_image.paste(img, (x, y))
        
        return final_image

    images = []

    for cat, stat in stats.items() :

        text_img = create_text_image(cat,f"Points : {stat['points']}\nSolved : {stat['solved_chall']}/{stat['tot_chall']}")
        chart_img = create_pie_chart([100-stat['rate'], stat['rate']], f"{stat['rate']}%")
        images.append(img_concat_h(text_img, chart_img))

    full_scoring = concatenate_images(images).save('resources/score.png')
    file = discord.File('resources/score.png', filename='score.png')

    message_title = f"Profile of {user.name}"
    embed = discord.Embed(color=Color.yellow(), title=message_title, description=f"*ID : {user.id}\nScore : {user.score}*")

    if requests.head(f"https://www.root-me.org/IMG/logo/auton{user.id}.jpg").status_code == 200 :
        pp = f"https://www.root-me.org/IMG/logo/auton{user.id}.jpg"
    elif requests.head(f"https://www.root-me.org/IMG/logo/auton{user.id}.png").status_code == 200 :
        pp = f"https://www.root-me.org/IMG/logo/auton{user.id}.png"
    else : 
        pp = f"https://www.root-me.org/IMG/logo/auton0.png"

    embed.set_thumbnail(url=pp)

    embed.set_image(url="attachment://score.png")
    await ctx.send(embed=embed, file=file)

    