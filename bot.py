import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading

# Replace with your actual bot token
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

# In-memory database
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

@bot.event
async def on_ready():
    await tree.sync()  # Sync commands with Discord
    print(f"Logged in as {bot.user}")

@tree.command(name="hcverify", description="Verify a user into [HC1] (Catercord) and store their Florr.io in-game name.")
@app_commands.describe(user="The user to HC verify", ingame_name="Their Florr.io in-game name")
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
        list_text += f"{idx}. {member.name} ➔ {ingame_name}\n"  # IMPORTANT: .name not .display_name

    await interaction.response.send_message(f"**[HC1] Guild Members:**\n{list_text}", ephemeral=True)

@tree.command(name="bulkupdate", description="Paste the list of usernames ➔ in-game names to update.")
@app_commands.describe(data="Paste entries like 'username ➔ ingame_name' one per line.")
async def bulkupdate(interaction: discord.Interaction, data: str):
    count = 0
    lines = data.strip().splitlines()
    for line in lines:
        if "➔" in line:
            try:
                discord_username, ingame_name = line.split("➔")
                discord_username = discord_username.strip()
                ingame_name = ingame_name.strip()

                # Find member by username
                member = discord.utils.find(lambda m: m.name.lower() == discord_username.lower(), interaction.guild.members)
                if member:
                    hc_names[str(member.id)] = ingame_name
                    count += 1
            except Exception as e:
                print(f"Failed to process line: {line} - {e}")

    await interaction.response.send_message(f"✅ Successfully updated {count} members!", ephemeral=True)

@tree.command(name="nerdhelp", description="Show list of Catercord slash commands.")
async def nerdhelp(interaction: discord.Interaction):
    help_text = (
        "**/verify** - Verify a normal Catercord member.\n"
        "**/hcverify** - HC verify a [HC1] member + save their Florr.io name.\n"
        "**/hcmembers** - List all [HC1] members with their in-game names.\n"
        "**/bulkupdate** - Paste and update old member list manually.\n"
        "**/nerdhelp** - Show this help menu."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# Start web server
keep_alive()

# Start bot
bot.run(TOKEN)
