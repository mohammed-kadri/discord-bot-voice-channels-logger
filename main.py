import discord
import json
from discord.ext import commands
from discord import app_commands
from datetime import datetime

# Load configuration
with open('config.json') as config_file:
    config = json.load(config_file)

intents = discord.Intents.default()
intents.guilds = config['intents']['guilds']
intents.voice_states = config['intents']['voice_states']
intents.messages = config['intents']['messages']

bot = commands.Bot(command_prefix=config['prefix'], intents=intents)

logging_paused = False

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    if logging_paused:
        return

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

@bot.tree.command(name="pause_logging", description="Pause voice channel logging")
async def pause_logging(interaction: discord.Interaction):
    global logging_paused
    logging_paused = True
    await interaction.response.send_message("Voice channel logging has been paused.", ephemeral=True)

@bot.tree.command(name="resume_logging", description="Resume voice channel logging")
async def resume_logging(interaction: discord.Interaction):
    global logging_paused
    logging_paused = False
    await interaction.response.send_message("Voice channel logging has been resumed.", ephemeral=True)

bot.run(config['bot_token'])
