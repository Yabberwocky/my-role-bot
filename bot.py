import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading

# Replace this with your actual bot token
TOKEN = "MTM2NTU3MjQzNzE4NTQwMDg5Mw.GZfG-P.G41IDr3AV8pUgFcgNEq8w2DfCc5QMfXGgbM3Vg"  # REMEMBER: Never share your token publicly

# Set up bot intents
intents = discord.Intents.default()
intents.members = True  # Needed to manage roles

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # For slash commands

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

@tree.command(name="addrole", description="Give a user a role")
@app_commands.describe(user="The user to give the role to", role="The role to give")
async def addrole(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    await user.add_roles(role)
    await interaction.response.send_message(f"✅ Gave **{role.name}** to **{user.display_name}**")

@tree.command(name="hcverify", description="Special verification: swap roles for HC")
@app_commands.describe(user="The user to HC verify")
async def hcverify(interaction: discord.Interaction, user: discord.Member):
    # IDs
    remove_role_id = 1360176495947022447
    add_role_ids = [1248708073019805717, 1230235110415274004]
    
    # Actions
    role_to_remove = user.guild.get_role(remove_role_id)
    roles_to_add = [user.guild.get_role(rid) for rid in add_role_ids]
    
    if role_to_remove:
        await user.remove_roles(role_to_remove)
    await user.add_roles(*roles_to_add)
    
    await interaction.response.send_message(f"✅ HC verified **{user.display_name}**!")

@tree.command(name="verify", description="Normal verification: swap roles")
@app_commands.describe(user="The user to verify")
async def verify(interaction: discord.Interaction, user: discord.Member):
    # IDs
    remove_role_id = 1360176495947022447
    add_role_id = 1248708073019805717
    
    # Actions
    role_to_remove = user.guild.get_role(remove_role_id)
    role_to_add = user.guild.get_role(add_role_id)
    
    if role_to_remove:
        await user.remove_roles(role_to_remove)
    if role_to_add:
        await user.add_roles(role_to_add)
    
    await interaction.response.send_message(f"✅ Verified **{user.display_name}**!")

@tree.command(name="nerdhelp", description="List all bot slash commands")
async def nerdhelp(interaction: discord.Interaction):
    help_text = (
        "**/addrole** - Give any role to a user.\n"
        "**/hcverify** - HC verify a user (remove old role, add 2 new roles).\n"
        "**/verify** - Normal verify a user (remove old role, add 1 new role).\n"
        "**/nerdhelp** - Show this list of commands."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# FIRST start the web server
keep_alive()

# THEN run the bot
bot.run(TOKEN)
