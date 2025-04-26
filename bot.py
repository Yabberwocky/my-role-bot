import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading
import json
import os

# Replace this with your actual bot token
TOKEN = "MTM2NTU3MjQzNzE4NTQwMDg5Mw.GZfG-P.G41IDr3AV8pUgFcgNEq8w2DfCc5QMfXGgbM3Vg"

# Set up bot intents
intents = discord.Intents.default()
intents.members = True  # Needed to manage roles

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # For slash commands

# Role IDs
REMOVE_ROLE_ID = 1360176495947022447
ADD_ROLE_ID_VERIFY = 1248708073019805717
ADD_ROLE_ID_HC = 1230235110415274004

# File to store in-game names
DATA_FILE = 'hcnames.json'

# Load stored in-game names
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        hc_names = json.load(f)
else:
    hc_names = {}

# Flask App
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

def save_hc_names():
    with open(DATA_FILE, 'w') as f:
        json.dump(hc_names, f)

@bot.event
async def on_ready():
    await tree.sync()  # Sync commands with Discord
    print(f"Logged in as {bot.user}")

@tree.command(name="addrole", description="Give any role to a user manually.")
@app_commands.describe(user="The user to give the role to", role="The role to give")
async def addrole(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    await user.add_roles(role)
    await interaction.response.send_message(f"✅ Gave **{role.name}** to **{user.display_name}**.")

@tree.command(name="hcverify", description="Verify a user into [HC1] (Catercord) and store in-game name.")
@app_commands.describe(user="The user to HC verify", ingame_name="Their in-game name")
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    role_to_remove = user.guild.get_role(REMOVE_ROLE_ID)
    roles_to_add = [
        user.guild.get_role(ADD_ROLE_ID_VERIFY),
        user.guild.get_role(ADD_ROLE_ID_HC)
    ]

    if role_to_remove:
        await user.remove_roles(role_to_remove)
    await user.add_roles(*roles_to_add)

    hc_names[str(user.id)] = ingame_name
    save_hc_names()

    await interaction.response.send_message(f"✅ HC verified **{user.display_name}** as **{ingame_name}**!")

@tree.command(name="verify", description="Normal verify a user into Catercord.")
@app_commands.describe(user="The user to verify")
async def verify(interaction: discord.Interaction, user: discord.Member):
    role_to_remove = user.guild.get_role(REMOVE_ROLE_ID)
    role_to_add = user.guild.get_role(ADD_ROLE_ID_VERIFY)

    if role_to_remove:
        await user.remove_roles(role_to_remove)
    if role_to_add:
        await user.add_roles(role_to_add)

    await interaction.response.send_message(f"✅ Verified **{user.display_name}**!")

@tree.command(name="hcmembers", description="List all [HC1] members with their in-game names.")
async def hcmembers(interaction: discord.Interaction):
    hc_role = interaction.guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await interaction.response.send_message("❌ [HC1] role not found.", ephemeral=True)
        return

    members = [member for member in hc_role.members]
    if not members:
        await interaction.response.send_message("No members with [HC1] role found.", ephemeral=True)
        return

    list_text = ""
    for idx, member in enumerate(members, 1):
        ingame_name = hc_names.get(str(member.id), "Unknown")
        list_text += f"{idx}. {member.display_name} ➔ {ingame_name}\n"

    await interaction.response.send_message(f"**[HC1] Guild Members:**\n{list_text}")

@tree.command(name="nerdhelp", description="Show list of Catercord slash commands.")
async def nerdhelp(interaction: discord.Interaction):
    help_text = (
        "**/addrole** - Give any role to a user manually.\n"
        "**/verify** - Verify a new Catercord member.\n"
        "**/hcverify** - Verify a [HC1] member + save their in-game name.\n"
        "**/hcmembers** - List all [HC1] members with in-game names.\n"
        "**/nerdhelp** - Show this help menu."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# FIRST start the web server
keep_alive()

# THEN run the bot
bot.run(TOKEN)
