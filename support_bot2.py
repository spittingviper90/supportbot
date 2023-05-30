import discord
from discord.ext import commands
from discord import Colour, Embed
import pytz
import datetime
from datetime import timedelta
import schedule
import time
import asyncio
import credentials
import requests
import random


central_tz = pytz.timezone('US/Central')

intents = discord.Intents.all()
intents.members = True
intents.messages = True
intents.guilds = True
intents.guild_messages = True
intents.invites = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Define the necessary variables
TOKEN = credentials.TOKEN
channel_id = credentials.channel_id
report_channel_id = credentials.report_channel_id
guild_id = credentials.guild_id
role_id = credentials.role_id
unique_role_id = credentials.unique_role_id
user_id1 = credentials.user_id


# Define the function to count mentions and unique mentions for the previous week
async def count_mentions():
    report_channel = bot.get_channel(report_channel_id)
    # Define the time range to check (Sunday at midnight to Saturday at midnight)
    now = datetime.datetime.now(central_tz)
    end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=7)

    def check_join_date(member):
        join_date_threshold = start_time  # Use the start_time instead of end_time

        join_date = member.joined_at

        if join_date > join_date_threshold:
            return True
        else:
            return False

    # Initialize dictionaries to store the mention counts and unique mention counts
    guild = bot.get_guild(guild_id)
    mention_counts = {member.id: 0 for member in guild.members}
    unique_mention_counts = {member.id: set() for member in guild.members}

    # Iterate through the messages in the channel and count the mentions and unique mentions
    channel = bot.get_channel(channel_id)
    async for message in channel.history(after=start_time, before=end_time):
        if message.author.id not in mention_counts:
            mention_counts[message.author.id] = 0
            unique_mention_counts[message.author.id] = set()
        for user in message.mentions:
            mention_counts[message.author.id] += 1
            unique_mention_counts[message.author.id].add(user.id)

    # Update the roles based on the mention and unique mention counts
    guild = bot.get_guild(guild_id)
    for user_id, count in mention_counts.items():
        member = guild.get_member(user_id)
        role = guild.get_role(role_id)
        if member is not None and role is not None:
            if count >= 3 and role not in member.roles:
                await member.add_roles(role)
            elif count < 3 and role in member.roles and not check_join_date(member):
                await member.remove_roles(role)
            elif count == 0 and not check_join_date(member):
                await member.remove_roles(role)

    for user_id, unique_count in unique_mention_counts.items():
        member = guild.get_member(user_id)
        role = guild.get_role(unique_role_id)
        if member is not None and role is not None:
            if len(unique_count) >= 6 and role not in member.roles:
                await member.add_roles(role)
            elif len(unique_count) < 6 and role in member.roles and not check_join_date(member):
                await member.remove_roles(role)
            elif len(unique_count) == 0 and not check_join_date(member):
                await member.remove_roles(role)

    # Initialize a string to store the mention and unique mention counts
    counts_string = 'supports and people supported for last week:\n'
    for user_id, count in mention_counts.items():
        if count > 0:
            user = bot.get_user(user_id)
            unique_count = len(unique_mention_counts[user_id])
            counts_string += f'{user.name}: supports = {count}, people supported = {unique_count}\n'

    # Split the string into chunks of 2000 characters
    chunks = [counts_string[i:i + 2000] for i in range(0, len(counts_string), 2000)]

    # Send each chunk as a separate message
    for chunk in chunks:
        await report_channel.send(chunk)

# Schedule the count_mentions function to run every Sunday at midnight
schedule.every().sunday.at("00:00").do(count_mentions)


# Run the scheduler in a separate thread
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


# Define a command to start the bot and print a message to indicate that it's running
@bot.event
async def on_ready():
    print("let's get to work.")


# Define a command to test the bot
@bot.command(name='test', help='makes sure the bot is running')
async def test(ctx):
    await ctx.send('Bot is working!')


def is_author():
    async def predicate(ctx):
        return ctx.author.id == user_id1
    return commands.check(predicate)


@bot.command(name='mentions', help="viper's use only")
@is_author()
async def mentions(ctx):
    await count_mentions()
    await ctx.send('Mentions done.')
    print('Mentions done.')


@bot.command(name='top_mentions', help='shows top 20 unique mentioners of the week')
async def top_mentions(ctx):
    now = datetime.datetime.now()

    # Define the time range to check (Sunday at midnight to now)
    days_since_sunday = (now.weekday() + 1) % 7
    last_sunday = (now - timedelta(days=days_since_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"Last Sunday was {last_sunday.strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize dictionaries to store the mention counts and unique mention counts
    mention_counts = {}
    unique_mention_counts = {}

    guild = bot.get_guild(guild_id)
    for member in guild.members:
        mention_counts[member.id] = 0
        unique_mention_counts[member.id] = set()

    # Iterate through the messages in the channel and count the mentions and unique mentions
    channel = bot.get_channel(channel_id)
    async for message in channel.history(after=last_sunday, before=now):
        if message.author.id not in mention_counts:
            mention_counts[message.author.id] = 0
            unique_mention_counts[message.author.id] = set()
        for user in message.mentions:
            mention_counts[message.author.id] += 1
            unique_mention_counts[message.author.id].add(user.id)

    # Sort the unique_mention_counts dictionary by value and get the top 20
    sorted_unique_counts = sorted(unique_mention_counts.items(), key=lambda x: len(x[1]), reverse=True)[:20]

    # Create a new embed
    embed = Embed(title='Top Mentions', color=Colour.random())

    # Iterate through the sorted_unique_counts and add each mention as a field with a different color
    for user_id, unique_mentions in sorted_unique_counts:
        if len(unique_mentions) > 0:
            user = bot.get_user(user_id)
            mention_count = mention_counts[user_id]
            color = Colour.from_rgb(user_id % 256, user_id % 256, user_id % 256)
            embed.add_field(name=f'{user.name}', value=f'Supports: {mention_count}, People Supported: {len(unique_mentions)}', inline=False)
            embed.fields[-1].color = color


    # Send the embed as a message
    await ctx.send(embed=embed)


@bot.command(name='my_mentions', help='shows your mentions and unique mentions for the current week')
async def my_mentions(ctx):
    now = datetime.datetime.now()

    # Define the time range to check (Sunday at midnight to now)
    days_since_sunday = (now.weekday() + 1) % 7
    last_sunday = (now - timedelta(days=days_since_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"Last Sunday was {last_sunday.strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize variables to count the mentions and unique mentions
    mention_count = 0
    unique_mention_count = 0

    channel = bot.get_channel(channel_id)
    async for message in channel.history(after=last_sunday, before=now):
        if message.author.id == ctx.author.id:
            mention_count += len(message.mentions)
            unique_mention_count += len(set(message.mentions))

    response = f"You've supported {mention_count} times and supported {unique_mention_count} different people this week"
    await ctx.send(response)


@bot.command(name='rcg', help='random compliment generator')
async def random_response(ctx):
    responses = ['you have a pretty smile', 'you look good', 'nice shoes', 'nice shirt', 'nice pants']

    # Choose a random response
    response = random.choice(responses)

    # Send the random response to the user who used the command (without mention)
    await ctx.send(f'{ctx.author.name}, {response}')


# Run the bot
bot.run(TOKEN)
