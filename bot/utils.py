import discord
import aiohttp
import code
import traceback
from html import unescape

from discord.utils import escape_markdown
from discord.channel import TextChannel
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import io
from PIL import Image, ImageDraw, ImageFont
import requests
import numpy as np
import textwrap


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

async def help_msg(ctx: commands.Context, all_commands: list[tuple[str, commands.HybridCommand]]) -> None:
    title = f"List of available commands :thinking:"
    embed = discord.Embed(color=Color.og_blurple(), title=title, description="")
    for name, cmd in all_commands:
        embed.add_field(name=f"**/{name}**", value=cmd.description, inline=False)
    await ctx.reply(embed=embed)

async def panic_message(channel: TextChannel, traceback: SyntaxWarning) -> None:
    """Runtime error"""
    title = f"C'est pas un bug c'est une feature"
    description = traceback
    embed = discord.Embed(color=Color.dark_red(), title=title, description=description)
    await channel.send(embed=embed)

async def init_start_msg(channel: TextChannel) -> None:
    """First time running message"""
    title = f'Good to see you :grin:'
    description = f'I am fetching the challenges, please wait.'
    embed = discord.Embed(color=Color.lighter_grey(), title=title, description=description)
    await channel.send(embed=embed)

async def init_end_msg(channel: TextChannel) -> None:
    """Initialization complete"""
    title = f'Initialization done :wink:'
    description = f'You can start using me. Enjoy !'
    embed = discord.Embed(color=Color.brand_green(), title=title, description=description)
    await channel.send(embed=embed)

async def init_not_done_msg(ctx: commands.Context) -> None:
    title = f"Initialization not done :confused:"
    description = f'Please wait a bit...'
    embed = discord.Embed(color=Color.orange(), title=title, description=description)
    await ctx.reply(embed=embed)

async def negative_days(ctx: commands.Context) -> None:
    title = f"Invalid number of days :face_with_spiral_eyes:"
    description = f"Number of days must be positive!"
    embed = discord.Embed(color=Color.brand_red(), title=title, description=description)
    await ctx.reply(embed=embed)

async def too_many_days(ctx: commands.Context, max_days: int) -> None:
    title = f"Too many days :exploding_head:"
    description = f"You can plot the last {max_days} days at most!"
    embed = discord.Embed(color=Color.brand_red(), title=title, description=description)
    await ctx.reply(embed=embed)

async def challenge_not_found(ctx: commands.Context, chall_name: str) -> None:
    title = f"Challenge {chall_name} not found :woozy_face:"
    description = f"Please use the autocompletion"
    embed = discord.Embed(color=Color.brand_red(), title=title, description=description)
    await ctx.reply(embed=embed)

async def too_many_challenges(ctx: commands.Context, chall_name: str) -> None:
    title = f"Multiple challs found for {chall_name} :face_with_spiral_eyes:"
    description = f"Start typing a chall and select the one you want"
    embed = discord.Embed(color=Color.brand_red(), title=title, description=description)
    await ctx.reply(embed=embed)

async def user_not_found(ctx: commands.Context, name_or_id: str, by_id: bool) -> None:
    title = f"User not found :woozy_face:"
    if by_id:
        description = f"User with id {name_or_id} not found"
    else:
        description = f"User {name_or_id} not found"
    embed = discord.Embed(color=Color.red(), title=title, description=description)
    await ctx.reply(embed=embed)

async def user_not_found_in_db(ctx: commands.Context, name: str) -> None:
    title = f"User not found in database :woozy_face:"
    description = f"User {name} not found in database"
    embed = discord.Embed(color=Color.red(), title=title, description=description)
    await ctx.reply(embed=embed)

async def new_chall(channel: TextChannel, chall_list) -> None:
    for chall in chall_list:
        title = f'New challenge available !'
        embed = discord.Embed(color=Color.dark_green(), title=title, description="")
        embed.add_field(name=f'{chall.title}', value=f'{chall.subtitle}')
        
        chall_card(chall).save('/tmp/chall_card.png')
        file = discord.File('/tmp/chall_card.png', filename='chall_card.png')
        embed.set_image(url='attachment://chall_card.png')

        await channel.send(file=file, embed=embed)

async def new_solves(channel: TextChannel, solve: tuple[User, Challenge, str, int, bool, list]) -> None:
    user, chall, next_user, points_to_reach, firstblood, overtakens = solve
    # for solve in solve_list:
    if firstblood : emoji=":drop_of_blood:"
    else : emoji=":partying_face:"

    title = f'**{user.name}** solved a new challenge !  {emoji}'
    description = f'*New score : {user.score}*'
    embed = discord.Embed(color=Color.gold(), title=title, description=description)
    
    chall_card(chall).save('/tmp/chall_card.png')
    file = discord.File('/tmp/chall_card.png', filename='chall_card.png')
    embed.set_image(url='attachment://chall_card.png')


    if requests.head(f"https://www.root-me.org/IMG/logo/auton{user.id}.jpg").status_code == 200 :
        pp = f"https://www.root-me.org/IMG/logo/auton{user.id}.jpg"
    elif requests.head(f"https://www.root-me.org/IMG/logo/auton{user.id}.png").status_code == 200 :
        pp = f"https://www.root-me.org/IMG/logo/auton{user.id}.png"
    else : 
        pp = f"https://www.root-me.org/IMG/logo/auton0.png"

    embed.set_thumbnail(url=pp)


    embed.add_field(name=f'{chall.title}', value="")
    if next_user:  # There is someone to overtake
        embed.set_footer(text=f'{points_to_reach} points to overtake {next_user}')
    else:
        embed.set_footer(text=f"{user.name} is still on top of the world!")
    await channel.send(file=file, embed=embed)
    if overtakens:
        await overtook_msg(channel, user.name, overtakens)

async def overtook_msg(channel: TextChannel, user_name: str, overtakens: list) -> None:
    if len(overtakens) == 1:
        title = f"Scoreboard changes! :rocket:"
        description = f"Congratz {user_name}! You've just overtaken {overtakens[0]} in the ranking! Keep going!"
    else:
        title = f"{len(overtakens)} in a row! Big changes in scoreboard! :rocket:"
        users_overtaken = ", ".join(overtakens[:-1]) + " and " + overtakens[-1]
        description = f"{user_name} is unstoppable! You've overtaken {users_overtaken}! You're superhuman!"
    embed = discord.Embed(color=Color.dark_gold(), title=title, description=description)
    await channel.send(embed=embed)


async def last_solves_msg(ctx: commands.Context, user: User, solves: list, n_days: int) -> None:
    message_title = f"Last solves of {user.name} the past {n_days} days"
    embed = discord.Embed(color=Color.blue(), title=message_title, description=f"*ID : {user.id}\nScore : {user.score}*")
    if requests.head(f"https://www.root-me.org/IMG/logo/auton{user.id}.jpg").status_code == 200 :
        pp = f"https://www.root-me.org/IMG/logo/auton{user.id}.jpg"
    elif requests.head(f"https://www.root-me.org/IMG/logo/auton{user.id}.png").status_code == 200 :
        pp = f"https://www.root-me.org/IMG/logo/auton{user.id}.png"
    else : 
        pp = f"https://www.root-me.org/IMG/logo/auton0.png"
    
    embed.set_thumbnail(url=pp)
    for solve in solves:
        embed.add_field(name=f"{solve[1]} ({solve[2]} points)", value=f"Solved on {solve[0].strftime('%d %B %Y')}", inline=False)

    await ctx.reply(embed=embed)


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
    embed.set_thumbnail(url="attachment://trophy.png")

    if len(users) == 0 : embed.description = f'Mmmmh...\n\'will work better if you add some users no ? :wink:'
    elif len(users) == 1 : embed.description = f'A scoreboard with only one user ? Really ?'

    for index, user in enumerate(users):
        if index < 3:
            medal = medals.get(index, "")
            embed.add_field(name=f"{medal} {user.name}",value=f"Points: {user.score}",inline=False)
        else :
            embed.add_field(name=f"#{index+1} {user.name}",value=f"Points: {user.score}",inline=False)

    await ctx.send(file=file, embed=embed)

async def today_msg(ctx: commands.Context, users) -> None:
    medals = {
        0: "🥇",
        1: "🥈",
        2: "🥉"
    }
    file = discord.File('resources/calendar.png', filename='calendar.png')  

    users.sort(key=lambda x: x[1], reverse=True)
    message_title = f'**Daily Scoreboard**'

    embed = discord.Embed(color=Color.yellow(), title=message_title, description="")
    embed.set_thumbnail(url="attachment://calendar.png")

    if len(users) == 0:
        embed.description = f'No solves for today (yet) ! \nMaybe you ?'

    for index, user in enumerate(users):
        if index < 3:
            medal = medals.get(index, "")
            embed.add_field(name=f"{medal} {user[0]}",value=f"Points: {user[1]}",inline=False)
        else :
            embed.add_field(name=f"#{index+1} {user[0]}",value=f"Points: {user[1]}",inline=False)

    await ctx.send(file=file, embed=embed)

async def graph_msg(ctx: commands.Context, last_solves: list, n_days: int) -> None:
    def make_graph():
        texts_color = "#d3d3d3"
        graph_face_color = "#2b2d31"
        legend_face_color = "#383a40"
        font_path = "resources/LiberationSans-Bold.ttf"
        custom_font = FontProperties(fname=font_path)

        fig, ax = plt.subplots(figsize=(8, 6))
        fig.subplots_adjust(bottom=0.3)
        fig.patch.set_facecolor(graph_face_color)
        ax.set_facecolor(graph_face_color)
        days_axis = [d for d in range(n_days+2)]
        for username, cumsum in last_solves:
            wrapped_username = "\n".join(textwrap.wrap(username, width=12))
            ax.plot(days_axis, cumsum, label=wrapped_username)
            ax.legend()

        ax.spines["bottom"].set_color(texts_color)
        ax.spines["left"].set_color(texts_color)
        ax.spines["top"].set_color("none")
        ax.spines["right"].set_color("none")

        ax.tick_params(axis="both", colors=texts_color)
        ax.xaxis.label.set_color(color=texts_color)
        ax.yaxis.label.set_color(color=texts_color)
        ax.xaxis.label.set_fontproperties(custom_font)
        ax.yaxis.label.set_fontproperties(custom_font)

        legend = ax.legend(loc='upper left', bbox_to_anchor=(0, -0.15), ncol=3)
        plt.setp(legend.get_texts(), fontproperties=custom_font, fontsize=13, color=texts_color)
        legend.get_frame().set_facecolor(legend_face_color)
        legend.get_frame().set_edgecolor("none")

        ax.set_xlabel("days", fontproperties=custom_font)
        ax.set_ylabel("points earned", fontproperties=custom_font)
        plt.savefig("/tmp/graph.png")

        plt.close()

    make_graph()
    file = discord.File("/tmp/graph.png", filename="graph.png")
    message_title = f"Top 10 last {n_days} days"
    embed = discord.Embed(color=Color.yellow(), title=message_title)
    embed.set_image(url="attachment://graph.png")
    await ctx.send(embed=embed, file=file)


async def too_many_users_msg(ctx: commands.Context, name) -> None:
    title = f'Too many users found for {name} :woozy_face:'
    description = f'Try using your full username, or use your UID instead'
    embed = discord.Embed(color=Color.red(), title=title, description=description)
    await ctx.reply(embed=embed)

async def added_ok(ctx: commands.Context, name) -> None:
    message_title = 'Success'
    message = f'{escape_markdown(name)} was successfully added :+1:'

    embed = discord.Embed(color=Color.green(), title=message_title, description=message)
    await ctx.reply(embed=embed)

async def removed_ok(ctx: commands.Context, name) -> None:
    message_title = 'Success'
    message = f'{escape_markdown(name)} was successfully removed :cry:\nWe will miss him/her :('

    embed = discord.Embed(color=Color.green(), title=message_title, description=message)
    await ctx.reply(embed=embed)

async def who_solved_msg(ctx: commands.Context, chall_name, solvers) -> None:
    title = f'Solvers of {chall_name} :sunglasses:'
    embed = discord.Embed(color=Color.purple(), title=title, description="")
    solvers = sorted(solvers, key=lambda s: s[1], reverse=True)

    if len(solvers) == 0 : embed.description = f'Nobody has solved {chall_name}. \nTry hard and be the first ! :index_pointing_at_the_viewer:'
    if len(solvers) == 1 : embed.description = f'That\'s what we call a giga boss :heart_eyes:'

    for users, date in solvers:
        embed.add_field(name=f"{users.name}", value=f"Solved on {date.strftime('%d %B %Y')}", inline=False)

    await ctx.reply(embed=embed)

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
        plt.close()
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

    concatenate_images(images).save('/tmp/score.png')
    plt.close()
    file = discord.File('/tmp/score.png', filename='score.png')

    message_title = f"Profile of {user.name}"
    embed = discord.Embed(color=Color.blue(), title=message_title, description=f"*ID : {user.id}\nScore : {user.score}*")

    if requests.head(f"https://www.root-me.org/IMG/logo/auton{user.id}.jpg").status_code == 200 :
        pp = f"https://www.root-me.org/IMG/logo/auton{user.id}.jpg"
    elif requests.head(f"https://www.root-me.org/IMG/logo/auton{user.id}.png").status_code == 200 :
        pp = f"https://www.root-me.org/IMG/logo/auton{user.id}.png"
    else : 
        pp = f"https://www.root-me.org/IMG/logo/auton0.png"

    embed.set_thumbnail(url=pp)

    embed.set_image(url="attachment://score.png")
    await ctx.send(embed=embed, file=file)

async def compare_graph(ctx: commands.Context, user1, user1_stats, user2, user2_stats) -> None:

    def create_bar_chart(profile, inverse):

        y_pos = - np.arange(len(categories))*0.5
        fig, ax = plt.subplots(figsize=(5, 10))
        fig.patch.set_facecolor("#2b2d31")
        bar_width = 0.3
        sens = 1
        color = '#feb800'
        ha = 'right'

        if inverse :
            profile = [-x for x in profile]
            sens=-1
            color = '#37a7e6'
            ha = 'left'

        ax.barh(y_pos, [sens*100 for _ in profile], bar_width, color="#2b2d31", align='center')
        ax.barh(y_pos, profile, bar_width, color=color, align='center')

        for i, v in enumerate(profile):
            if abs(v) < 20 : label_offset = -15
            else : label_offset = 2
            ax.text(v-sens*label_offset, y_pos[i]-0.02, f"{abs(v)}%", verticalalignment='center', horizontalalignment=ha, color='white', fontweight='bold', fontsize=20)

        ax.axis('off')
        plt.tight_layout(pad=0)

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        img = Image.open(buf)
        return img

    def categories_image(text_list, img_height):
        image = Image.new('RGB', (270, img_height), color='#2b2d31')
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("resources/LiberationSans-Bold.ttf", size=30)

        y = 55
        line_spacing = 86

        for text in text_list:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x = (270 - text_width) / 2
            draw.text((x, y), text, font=font, fill='white')
            y += line_spacing
        return image

    def img_concat_h(im1, im2, im3):
        res = Image.new('RGB', (im1.width + im2.width + im3.width, max(im1.height, im2.height, im3.height)))
        res.paste(im1, (0, 0))
        res.paste(im2, (im1.width, 0))
        res.paste(im3, (im1.width + im2.width, 0))
        return res
    
    categories, profile1, profile2 = [], [], []

    for categorie, _ in user1_stats.items():
        categories.append(categorie)
        profile1.append(user1_stats[categorie]['rate'])
        profile2.append(user2_stats[categorie]['rate'])

    profile1_chart = create_bar_chart(profile1, 1)
    profile2_chart = create_bar_chart(profile2, 0)

    categories_title = categories_image(categories, profile1_chart.height)

    full_image = img_concat_h(profile1_chart, categories_title, profile2_chart)
    full_image.save('/tmp/test.png')

    embed = discord.Embed(color=Color.blue(), title=f"{user1.name} VS {user2.name}", description=f":blue_circle: **{user1.name}** - *Score : {user1.score}*\n:orange_circle: **{user2.name}** - *Score : {user2.score}*")
 
    file = discord.File('/tmp/test.png', filename='test.png')
    embed.set_image(url='attachment://test.png')
    await ctx.send(embed=embed, file=file)  

def chall_card(chall) -> Image :
    def img_concat_h(im1, im2, im3):
        res = Image.new('RGB', (im1.width + im2.width + im3.width + 400, max(im1.height, im2.height, im3.height)), color='#2b2d31')
        res.paste(im1, (0, 0))
        res.paste(im2, (im1.width +200, 0))
        res.paste(im3, (im1.width +400 + im2.width, 0))
        return res

    def points_widget(points):
        points = str(points)
        image = Image.new('RGB', (800, 712), color='#2b2d31')
        draw = ImageDraw.Draw(image)
        main_font = ImageFont.truetype("resources/LiberationSans-Bold.ttf", size=300)
        second_font = ImageFont.truetype("resources/LiberationSans-Bold.ttf", size=100)

        bbox = draw.textbbox((0, 0), points, font=main_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (800 - text_width) / 2
        y = (512 - text_height) / 2
        draw.text((x, y), points, font=main_font, fill='white')

        bbox = draw.textbbox((0, 0), "Points", font=second_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (800 - text_width) / 2
        y = 256 + (150 - text_height) / 3
        draw.text((x, 2*y), "Points", font=second_font, fill='white')

        return image

    score_img = points_widget(chall.score)
    cat_img = Image.open(f'./resources/categories/{chall.category}.png')
    dif_img = Image.open(f'./resources/difficulties/{chall.difficuly}.png')

    full = img_concat_h(cat_img, dif_img, score_img)
    return full

async def not_implemented(channel: TextChannel) -> None:
    """When a command is in the callable ones but not implemented"""
    title = f'Command not implemented'
    description = f'I\'m still under construction\n Buy a beer to my developpers if you want it quick'
    embed = discord.Embed(color=Color.lighter_grey(), title=title, description=description)
    await channel.send(embed=embed)