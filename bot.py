import discord
from discord.ext import commands, tasks
import os
import random
import json
from dotenv import load_dotenv
from flask import Flask
import threading
import googleapiclient.discovery
import googleapiclient.errors

# Load environment variables
load_dotenv()

# Flask web server setup
app = Flask(__name__)

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bot Status</title>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background: linear-gradient(135deg, #1a1a1a, #3e0000);
            overflow: hidden;
            color: #ffffff;
        }

        /* Particle Effect */
        body::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle, rgba(255, 0, 0, 0.5) 1px, transparent 1px);
            background-size: 5px 5px;
            opacity: 0.2;
        }

        .status-box {
            position: relative;
            z-index: 2;
            background: rgba(0, 0, 0, 0.8);
            padding: 30px 50px;
            border-radius: 15px;
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.5);
            text-align: center;
            border: 2px solid rgba(255, 0, 0, 0.8);
        }

        .status-box h1 {
            margin: 0;
            font-size: 28px;
            font-weight: bold;
            color: #ff4d4d;
            text-transform: uppercase;
            text-shadow: 0 0 8px rgba(255, 0, 0, 0.8);
        }

        .status-box p {
            margin: 10px 0 0;
            font-size: 20px;
            font-weight: 400;
            color: #ffffff;
        }

        /* Bot status indicator styling */
        .status-box p span {
            display: inline-block;
            margin-left: 8px;
            padding: 2px 8px;
            border-radius: 12px;
            background-color: #ff4d4d;
            font-weight: bold;
            text-shadow: 0 0 4px rgba(0, 0, 0, 0.5);
        }

        /* Subtle Animation for particles */
        @keyframes moveParticles {
            0% {
                background-position: 0 0;
            }
            100% {
                background-position: 100px 100px;
            }
        }

        body::before {
            animation: moveParticles 20s linear infinite;
        }
    </style>
</head>
<body>
    <div class="status-box">
        <h1>Bot Status</h1>
        <p>✅ <span>Online</span></p>
    </div>
</body>
</html>
    """

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_flask).start()

# YouTube API configuration
CHANNEL_ID = 'UCQI4EhkeYTcsp0bJ2aNAOCQ'  # Replace with your YouTube channel ID
YOUTUBE_API_KEY = 'AIzaSyB5m2BMejMci824GjeqoBYll_jjncvAk_c'  # Replace with your YouTube API key
LAST_VIDEO_ID = None

# Load or initialize prefixes and custom commands
try:
    with open("prefixes.json", "r") as file:
        prefixes = json.load(file)
except FileNotFoundError:
    prefixes = {}

try:
    with open("custom_commands.json", "r") as file:
        custom_commands = json.load(file)
except FileNotFoundError:
    custom_commands = {}

def save_prefixes():
    with open("prefixes.json", "w") as file:
        json.dump(prefixes, file)

def save_custom_commands():
    with open("custom_commands.json", "w") as file:
        json.dump(custom_commands, file)

# Bot setup with dynamic prefix
def get_prefix(bot, message):
    return prefixes.get(str(message.guild.id), "!")  # Default to "!" if no custom prefix

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Bot status rotation
status_list = [
    "Powered by ShadowMods!",
    "Use !help for help!",
]

@tasks.loop(seconds=30)
async def change_status():
    await bot.change_presence(activity=discord.Game(name=random.choice(status_list)))

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    change_status.start()

# --------------------------
# Welcome System
# --------------------------

@bot.event
async def on_member_join(member):
    # You can choose a channel where the welcome message will be sent
    channel = discord.utils.get(member.guild.text_channels, name="👋🏼｜welcome")  # Change to your desired channel
    if channel:
        embed = discord.Embed(
            title="Welcome!",
            description=f"Welcome to {member.guild.name}, {member.mention}! We're glad to have you here! 🎉",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url)
        await channel.send(embed=embed)

    # Optionally, you can also send a direct message to the user
    try:
        await member.send(f"Hello {member.name}, welcome to {member.guild.name}! 😊")
    except discord.Forbidden:
        pass  # If the bot cannot DM the user

# --------------------------
# Bot Join Server Embed
# --------------------------

@bot.event
async def on_guild_join(guild):
    # Attempt to find a specific channel like "welcome" or "general"
    channel = discord.utils.get(guild.text_channels, name="👋🏼｜welcome") or discord.utils.get(guild.text_channels, name="general")
    
    # If no specific channel is found, fallback to the first available text channel
    if not channel:
        channel = discord.utils.get(guild.text_channels, permissions__send_messages=True)
    
    if channel:
        embed = discord.Embed(
            title="Thanks for Adding Me!",
            description=(
                f"Hello! I'm **Dark Phoenix(V3)**, your all-in-one server bot.\n"
                f"Use `!help` to see my commands and features!\n\n"
            ),
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else "https://i.imgur.com/AfFp7pu.png")
        embed.set_footer(text="Dark Phoenix Bot • Ready to serve!")
        
        await channel.send(embed=embed)
    else:
        print(f"No suitable channel to send a welcome message in {guild.name}")

# --------------------------
# YouTube Video Notification System
# --------------------------

def get_latest_video():
    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    request = youtube.search().list(
        part="snippet",
        channelId=CHANNEL_ID,
        order="date",  # Order by latest
        maxResults=1  # Get only the most recent video
    )
    
    response = request.execute()
    print(response)  # Log the API response for debugging

    latest_video = response['items'][0]
    video_id = latest_video['id']['videoId']
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    video_title = latest_video['snippet']['title']

    return video_title, video_url, video_id


@tasks.loop(minutes=1)  # Check every 10 minutes for new video
async def check_for_new_video():
    global LAST_VIDEO_ID

    video_title, video_url, video_id = get_latest_video()

    if video_id != LAST_VIDEO_ID:
        LAST_VIDEO_ID = video_id

        # Send notification to all guilds
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name="general")  # Replace with the desired channel name
            if channel:
                embed = discord.Embed(
                    title="New Video Released!",
                    description=f"Check out the latest video: **{video_title}**\n{video_url}",
                    color=discord.Color.red()
                )
                embed.set_footer(text="Powered by ShadowMods")
                await channel.send(embed=embed)


# --------------------------
# General Commands
# --------------------------

@bot.command(name="help")
async def commands_list(ctx):
    embed = discord.Embed(
        title="Available Commands",
        description=(
            "**General Commands:**\n"
            "`!help` – List of all commands.\n"
            "`!ping` – Check bot latency.\n"
            "`!avatar [user]` – Get a user's avatar.\n"
            "`!invite` – Get the invite link for the current server.\n"
            "`!serverinfo` – Get server information.\n"
            "`!userinfo [user]` – Get user information.\n"
            "**Fun Commands:**\n"
            "`!joke` – Get a random joke.\n"
            "`!roll [sides]` – Roll a dice.\n"
            "`!coinflip` – Flip a coin.\n"
            "**Moderation Commands:**\n"
            "`!kick [member] [reason]` – Kick a member.\n"
            "`!ban [member] [reason]` – Ban a member.\n"
            "`!unban [user_id]` – Unban a user.\n"
            "`!lock [channel]` – Lock a channel.\n"
            "`!unlock [channel]` – Unlock a channel.\n"
            "`!slowmode [seconds] [channel]` – Set slowmode.\n"
            "`!role [add/remove] [member] [role]` – Manage roles.\n"
            "`!nick [member] [nickname]` – Change a nickname.\n"
            "`!deafen [member]` – Deafen a user.\n"
            "`!undeafen [member]` – Undeafen a user.\n"
            "`!move [member] [channel]` – Move a user to a voice channel.\n"
            "`!purge [number]` – Delete the last N messages.\n"
        ),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(name="apply")
async def apply(ctx):
    # Define the category ID where the new channel will be placed
    category_id = 1327779882234810551  # Replace with the desired category ID
    category = discord.utils.get(ctx.guild.categories, id=category_id)

    if category is None:
        await ctx.send("The specified category does not exist.")
        return

    # Create a private text channel for the user who sent the command
    channel = await ctx.guild.create_text_channel(f"{ctx.author.name}-apply", category=category)

    # Set permissions so only the user and certain roles can see the channel
    await channel.set_permissions(ctx.guild.default_role, read_messages=False)  # Hide the channel from everyone else
    await channel.set_permissions(ctx.author, read_messages=True)  # Allow the user to see their own channel
    # Here you can also set permissions for any specific roles if needed:
    # Example:
    # await channel.set_permissions(some_role, read_messages=True)

    # Send the questions in the new channel
    questions = [
        "1. What experience do you have with game cheats, web development, AI development, or Discord bot development?",
        "2. How would you handle a situation where a user is discussing or sharing cheats in a game where it is not allowed?",
        "3. What is your approach to handling technical questions from users who need help with coding or development issues?",
        "4. How would you manage a situation where a user posts malicious code or harmful scripts in the server?",
        "5. What steps would you take if a user reported another for violating the server’s rules or using cheats unethically?",
        "6. How familiar are you with server management tools, and which tools would you use to maintain a secure environment in ShadowMods?",
        "7. How would you handle a disagreement between two members on a development project or hack you’re working on?",
        "8. How do you ensure the server stays informative and helpful, especially for users learning about development or game cheats?",
        "9. What would you do if a user was spamming the server with development tools or tools related to game cheats that are not relevant to the current topic?",
        "10. Why do you want to be a moderator for ShadowMods, and how would your technical knowledge benefit the server community?"
    ]

    # Send the questions to the new private channel
    for question in questions:
        await channel.send(question)

    # Notify the user the channel has been created
    await ctx.send(f"Your application channel has been created: {channel.mention}")

@bot.command(name="applyhelp")
async def applyhelp(ctx):
    # Send the list of questions to the user who called the command
    questions = [
        "1. What experience do you have with game cheats, web development, AI development, or Discord bot development?",
        "2. How would you handle a situation where a user is discussing or sharing cheats in a game where it is not allowed?",
        "3. What is your approach to handling technical questions from users who need help with coding or development issues?",
        "4. How would you manage a situation where a user posts malicious code or harmful scripts in the server?",
        "5. What steps would you take if a user reported another for violating the server’s rules or using cheats unethically?",
        "6. How familiar are you with server management tools, and which tools would you use to maintain a secure environment in ShadowMods?",
        "7. How would you handle a disagreement between two members on a development project or hack you’re working on?",
        "8. How do you ensure the server stays informative and helpful, especially for users learning about development or game cheats?",
        "9. What would you do if a user was spamming the server with development tools or tools related to game cheats that are not relevant to the current topic?",
        "10. Why do you want to be a moderator for ShadowMods, and how would your technical knowledge benefit the server community?"
    ]

    # Send the questions to the user who called the command
    for question in questions:
        await ctx.send(question)

@bot.command(name="delete_ticket")
async def delete_ticket(ctx, channel_id: int):
    # Fetch the channel by ID
    channel = ctx.guild.get_channel(channel_id)

    if channel is None:
        await ctx.send(f"Channel with ID {channel_id} does not exist.")
        return

    # Ensure that the user has the appropriate permissions to delete the channel
    if not ctx.author.permissions_in(channel).manage_channels:
        await ctx.send("You do not have permission to delete this channel.")
        return

    # Delete the channel
    await channel.delete()

    # Notify the user that the ticket has been deleted
    await ctx.send(f"Ticket channel {channel.name} has been deleted.")

@bot.command(name="close_ticket")
async def close_ticket(ctx):
    # Check if the author is in a ticket channel (i.e., channel name contains "-ticket")
    if "-ticket" not in ctx.channel.name:
        await ctx.send("This command can only be used in a ticket channel.")
        return

    # Define the category ID where closed tickets will be moved
    closed_category_id = 1327779969983840357  # Replace with your desired "Closed Tickets" category ID
    closed_category = discord.utils.get(ctx.guild.categories, id=closed_category_id)

    if closed_category is None:
        await ctx.send("The specified closed tickets category does not exist.")
        return

    # Move the ticket channel to the "Closed Tickets" category
    await ctx.channel.edit(category=closed_category)

    # Optionally, you can lock the channel to prevent further messages from being sent after closing
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)

    # Notify the user that the ticket has been closed and moved to the "Closed Tickets" category
    await ctx.send(f"This ticket has been closed and moved to {closed_category.name}. If you need further assistance, please create a new ticket.")

@bot.command(name="create_ticket")
async def create_ticket(ctx):
    # Define the category ID where the help ticket will be placed
    category_id = 1327780139911872532  # Replace with the desired category ID for help tickets
    category = discord.utils.get(ctx.guild.categories, id=category_id)

    if category is None:
        await ctx.send("The specified category does not exist.")
        return

    # Create a private text channel for the user to describe their issue
    channel = await ctx.guild.create_text_channel(f"{ctx.author.name}-ticket", category=category)

    # Set permissions so only the user and staff can see the channel
    await channel.set_permissions(ctx.guild.default_role, read_messages=False)  # Hide from everyone else
    await channel.set_permissions(ctx.author, read_messages=True)  # Allow the user to see their own ticket
    # Set permissions for staff/support role
    support_role = discord.utils.get(ctx.guild.roles, name="Support")  # Replace with your role name
    if support_role:
        await channel.set_permissions(support_role, read_messages=True)

    # Send a message to the newly created channel, instructing the user
    await channel.send(f"Hello {ctx.author.mention}, please describe your issue and a staff member will assist you shortly.")
    
    # Optionally, notify the user that the ticket has been created
    await ctx.send(f"Your ticket has been created: {channel.mention}. Please check the channel to describe your issue.")

@bot.command(name="ping")
async def ping(ctx):
    embed = discord.Embed(
        title="Pong! 🏓",
        description=f"Latency: {round(bot.latency * 1000)}ms",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="avatar")
async def avatar(ctx, user: discord.User = None):
    user = user or ctx.author
    embed = discord.Embed(
        title=f"{user.name}'s Avatar",
        color=discord.Color.blue()
    )
    embed.set_image(url=user.avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="invite")
async def invite(ctx):
    invite_url = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions.all())
    embed = discord.Embed(
        title="Invite Me to Your Server",
        description=f"Click [here]({invite_url}) to invite me to your server!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    embed = discord.Embed(title=f"{ctx.guild.name} Info", description="Information of this Server", color=discord.Colour.blue())
    embed.add_field(name='🆔 Server ID', value=f"{ctx.guild.id}", inline=True)
    embed.add_field(name='📆 Created On', value=ctx.guild.created_at.strftime("%b %d %Y"), inline=True)
    embed.add_field(name='👑 Owner', value=f"{ctx.guild.owner.mention}", inline=True)
    embed.add_field(name='👥 Members', value=f'{ctx.guild.member_count} Members', inline=True)
    embed.add_field(name='💬 Channels', value=f'{len(ctx.guild.text_channels)} Text | {len(ctx.guild.voice_channels)} Voice', inline=True)
    embed.add_field(name='🌎 Region', value=f'{ctx.guild.preferred_locale}', inline=True)
    embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="⭐ • ShadowMods")    
    embed.set_author(name=f'{ctx.author.name}', icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="announce")
@commands.is_owner()  # This ensures only the bot owner can use the command
async def announce(ctx, *, message: str):
    # Send @everyone mention in plain text
    await ctx.send(f"@everyone {message}")
    
    # Create an embed with the provided message
    embed = discord.Embed(
        title="Announcement",
        description=message,
        color=discord.Color.blue()
    )
    embed.set_footer(text="Announcement from the bot owner")
    
    # Send the embed in the same channel
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def userinfo(ctx, user: discord.User = None):
    user = user or ctx.author
    embed = discord.Embed(
        title=f"User Info for {user.name}",
        color=discord.Color.purple()
    )
    embed.add_field(name="User ID", value=user.id)
    embed.add_field(name="Account Created", value=user.created_at.strftime("%b %d, %Y"))
    embed.add_field(name="Joined Server", value=user.joined_at.strftime("%b %d, %Y"))
    embed.set_thumbnail(url=user.avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="joke")
async def joke(ctx):
    jokes = [
        "Why don't skeletons fight each other? They don't have the guts!",
        "I told my wife she was drawing her eyebrows too high. She looked surprised!",
        "I used to play piano by ear, but now I use my hands!",
        "I told my computer I needed a break, and now it won't stop sending me Kit-Kats."
    ]
    await ctx.send(random.choice(jokes))

@bot.command(name="roll")
async def roll(ctx, sides: int = 6):
    result = random.randint(1, sides)
    await ctx.send(f"You rolled a {result}!")

@bot.command(name="coinflip")
async def coinflip(ctx):
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"The coin landed on {result}!")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"Kicked {member.mention} for {reason or 'no reason'}.")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"Banned {member.mention} for {reason or 'no reason'}.")

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"Unbanned {user.mention}.")

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock_channel(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"Channel {channel.mention} is now locked.")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock_channel(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"Channel {channel.mention} is now unlocked.")

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.edit(slowmode_delay=seconds)
    await ctx.send(f"Slowmode for {channel.mention} is set to {seconds} seconds.")

@bot.command(name="role")
@commands.has_permissions(manage_roles=True)
async def manage_role(ctx, action: str, member: discord.Member, role: discord.Role):
    if action == "add":
        await member.add_roles(role)
        await ctx.send(f"Added {role.mention} to {member.mention}.")
    elif action == "remove":
        await member.remove_roles(role)
        await ctx.send(f"Removed {role.mention} from {member.mention}.")
    else:
        await ctx.send("Invalid action. Use `add` or `remove`.")

@bot.command(name="nick")
@commands.has_permissions(manage_nicknames=True)
async def nick(ctx, member: discord.Member, *, nickname: str):
    await member.edit(nick=nickname)
    await ctx.send(f"Changed {member.mention}'s nickname to {nickname}.")

@bot.command(name="deafen")
@commands.has_permissions(deafen_members=True)
async def deafen(ctx, member: discord.Member):
    await member.edit(deafen=True)
    await ctx.send(f"Deafened {member.mention}.")

@bot.command(name="undeafen")
@commands.has_permissions(deafen_members=True)
async def undeafen(ctx, member: discord.Member):
    await member.edit(deafen=False)
    await ctx.send(f"Undeafened {member.mention}.")

@bot.command(name="move")
@commands.has_permissions(move_members=True)
async def move(ctx, member: discord.Member, channel: discord.VoiceChannel):
    await member.move_to(channel)
    await ctx.send(f"Moved {member.mention} to {channel.mention}.")

@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"Deleted {len(deleted)} messages.", delete_after=5)

@bot.command(name="setprefix")
@commands.has_permissions(administrator=True)
async def setprefix(ctx, new_prefix: str = None):
    # Check if the new_prefix argument is missing
    if not new_prefix:
        await ctx.send("Please provide a new prefix. Example: `!setprefix !`")
        return

    # Check if the new prefix is too long
    if len(new_prefix) > 5:
        await ctx.send("The prefix is too long! Please use a shorter prefix (maximum 5 characters).")
        return
    
    # Update the prefix for the guild in the prefixes dictionary
    prefixes[str(ctx.guild.id)] = new_prefix

    # Save the updated prefixes dictionary
    save_prefixes()

    # Send confirmation message
    embed = discord.Embed(
        title="Prefix Updated",
        description=f"The command prefix has been set to `{new_prefix}`",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="addcommand")
@commands.has_permissions(administrator=True)
async def add_custom_command(ctx, command_name: str, *, response: str):
    if command_name in custom_commands:
        await ctx.send("This command already exists!")
        return
    custom_commands[command_name] = response
    save_custom_commands()
    await ctx.send(f"Custom command `{command_name}` added!")

@bot.command(name="removecommand")
@commands.has_permissions(administrator=True)
async def remove_custom_command(ctx, command_name: str):
    if command_name not in custom_commands:
        await ctx.send("This command doesn't exist!")
        return
    del custom_commands[command_name]
    save_custom_commands()
    await ctx.send(f"Custom command `{command_name}` removed!")

# Dynamically add custom commands
@bot.event
async def on_message(message):
    if message.content.startswith(get_prefix(bot, message)):
        command_name = message.content[len(get_prefix(bot, message)):].split()[0]
        if command_name in custom_commands:
            await message.channel.send(custom_commands[command_name])
            return
    await bot.process_commands(message)

bot.run(os.getenv("BOT_TOKEN"))
