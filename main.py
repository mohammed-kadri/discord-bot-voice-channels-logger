import discord
import json
import boto3
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

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('VoiceChannelActivityLogger')

log_channel_id = None


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

    # Fetch the log channel ID from DynamoDB
    response = table.get_item(Key={'guild_id': str(member.guild.id)})
    log_channel_id = response['Item']['log_channel_id'] if 'Item' in response else config['log_channel_id']
    log_channel = bot.get_channel(int(log_channel_id))
    
    if before.channel is None and after.channel is not None:
        # User joined a voice channel
        users_in_channel = [user.name for user in after.channel.members]
        message = (
            f'**{member.name}** joined **{after.channel.name}** at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            f'**Users in channel:** {", ".join(users_in_channel)}'
        )
        await log_channel.send(message)
    
    elif before.channel is not None and after.channel is None:
        # User left a voice channel
        users_in_channel = [user.name for user in before.channel.members]
        message = (
            f'**{member.name}** left **{before.channel.name}** at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            f'**Users remaining in channel:** {", ".join(users_in_channel)}'
        )
        await log_channel.send(message)
    
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        # User switched voice channels
        users_in_before_channel = [user.name for user in before.channel.members]
        users_in_after_channel = [user.name for user in after.channel.members]
        message = (
            f'**{member.name}** switched from **{before.channel.name}** to **{after.channel.name}** at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            f'**Users in previous channel:** {", ".join(users_in_before_channel)}\n'
            f'**Users in current channel:** {", ".join(users_in_after_channel)}'
        )
        await log_channel.send(message)


@bot.event
async def on_guild_channel_delete(channel):
    # Fetch the log channel ID from DynamoDB
    response = table.get_item(Key={'guild_id': str(channel.guild.id)})
    if 'Item' in response:
        log_channel_id = response['Item']['log_channel_id']
        if str(channel.id) == log_channel_id:
            # Update the log channel ID to null in DynamoDB
            table.update_item(
                Key={'guild_id': str(channel.guild.id)},
                UpdateExpression="set log_channel_id = :val",
                ExpressionAttributeValues={':val': None}
            )
            print(f"Log channel for guild {channel.guild.name} has been deleted and set to null.")


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

@bot.tree.command(name="set_log_channel", description="Set the log channel for voice channel activity")
@app_commands.describe(channel="The channel to send logs to")
async def set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    # Save the log channel ID to DynamoDB
    table.put_item(Item={'guild_id': str(interaction.guild.id), 'log_channel_id': str(channel.id)})
    await interaction.response.send_message(f"Log channel set to {channel.mention}", ephemeral=True)

@bot.tree.command(name="get_log_channel", description="Get the current log channel for voice channel activity")
async def get_log_channel(interaction: discord.Interaction):
    # Fetch the log channel ID from DynamoDB
    response = table.get_item(Key={'guild_id': str(interaction.guild.id)})
    if 'Item' in response:
        log_channel_id = response['Item']['log_channel_id']
        log_channel = bot.get_channel(int(log_channel_id))
        await interaction.response.send_message(f"The current log channel is {log_channel.mention}", ephemeral=True)
    else:
        await interaction.response.send_message("No log channel set for this server.", ephemeral=True)



bot.run(config['bot_token'])
