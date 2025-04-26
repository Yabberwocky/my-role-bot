import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading

# Replace this with your actual bot token
TOKEN = "your-token-here"

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

# FIRST start the web server
keep_alive()

# THEN run the bot
bot.run(TOKEN)
