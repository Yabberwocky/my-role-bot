import os
import threading
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask

# Replace this with your actual bot token
TOKEN = "MTM2NTU3MjQzNzE4NTQwMDg5Mw.GSfrrD.-aChqNHcSz6oR7j4Xv4AyCA6iiO-_xYp6l3hcc"

# Flask server to keep the bot alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# Set up bot intents
intents = discord.Intents.default()
intents.members = True  # Needed to manage roles

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # For slash commands

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

@tree.command(name="addrole", description="Give a user a role")
@app_commands.describe(user="The user to give the role to", role="The role to give")
async def addrole(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    await user.add_roles(role)
    await interaction.response.send_message(f"✅ Gave **{role.name}** to **{user.display_name}**")

# Important: Start Flask first, then start bot
keep_alive()
bot.run(TOKEN)
