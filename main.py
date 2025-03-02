import discord
import json
from discord.ext import commands
from datetime import datetime

# Load configuration
with open('config.json') as config_file:
    config = json.load(config_file)

intents = discord.Intents.default()
intents.guilds = config['intents']['guilds']
intents.voice_states = config['intents']['voice_states']
intents.messages = config['intents']['messages']

bot = commands.Bot(command_prefix=config['prefix'], intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_voice_state_update(member, before, after):
    log_channel = bot.get_channel(int(config['log_channel_id']))
    if before.channel is None and after.channel is not None:
        # User joined a voice channel
        users_in_channel = [user.name for user in after.channel.members]
        message = (f'{member.name} joined {after.channel.name} at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
                   f'Users in channel: {", ".join(users_in_channel)}')
        await log_channel.send(message)
    elif before.channel is not None and after.channel is None:
        # User left a voice channel
        users_in_channel = [user.name for user in before.channel.members]
        message = (f'{member.name} left {before.channel.name} at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
                   f'Users remaining in channel: {", ".join(users_in_channel)}')
        await log_channel.send(message)

bot.run(config['bot_token'])