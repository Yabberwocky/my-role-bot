import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput
from discord import TextStyle
from flask import Flask
import threading
import os
from supabase import create_client, Client

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

REMOVE_ROLE_ID = 1360176495947022447
ADD_ROLE_ID_VERIFY = 1248708073019805717
ADD_ROLE_ID_HC = 1230235110415274004

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
    await tree.sync()
    print(f"Logged in as {bot.user}")

class BulkUpdateModal(discord.ui.Modal, title="Bulk Update"):
    data = discord.ui.TextInput(label="Paste the list below", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            lines = self.data.value.splitlines()
            count = 0
            for line in lines:
                if "➔" in line:
                    username, ingame_name = map(str.strip, line.split("➔", 1))
                    member = discord.utils.find(lambda m: m.name.lower() == username.lower(), interaction.guild.members)
                    if member:
                        supabase.table("hc_members").upsert({
                            "discord_id": str(member.id),
                            "discord_name": member.name,
                            "ingame_name": ingame_name
                        }).execute()
                        count += 1
            await interaction.followup.send(f"✅ Successfully updated {count} members!")
        except Exception as e:
            await interaction.followup.send(f"❌ Error during bulk update: {e}", ephemeral=True)
            print(f"BulkUpdateModal error: {e}")

@tree.command(name="hcverify", description="Verify a user into [HC1] (Catercord) and store their Florr.io in-game name.")
@app_commands.describe(user="The user to HC verify", ingame_name="Their Florr.io in-game name")
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    try:
        role_to_remove = user.guild.get_role(REMOVE_ROLE_ID)
        roles_to_add = [
            user.guild.get_role(ADD_ROLE_ID_VERIFY),
            user.guild.get_role(ADD_ROLE_ID_HC)
        ]

        if role_to_remove:
            await user.remove_roles(role_to_remove)
        await user.add_roles(*roles_to_add)

        supabase.table("hc_members").upsert({
            "discord_id": str(user.id),
            "discord_name": user.name,
            "ingame_name": ingame_name
        }).execute()

        try:
            await user.edit(nick=ingame_name)
        except Exception as e:
            print(f"Failed to change nickname for {user.name}: {e}")

        await interaction.response.send_message(f"✅ HC verified **{user.display_name}** as **{ingame_name}**!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error during hcverify: {e}", ephemeral=True)
        print(f"hcverify command error: {e}")

@tree.command(name="verify", description="Normal verify a user into Catercord.")
@app_commands.describe(user="The user to verify")
async def verify(interaction: discord.Interaction, user: discord.Member):
    try:
        role_to_remove = user.guild.get_role(REMOVE_ROLE_ID)
        role_to_add = user.guild.get_role(ADD_ROLE_ID_VERIFY)

        if role_to_remove:
            await user.remove_roles(role_to_remove)
        if role_to_add:
            await user.add_roles(role_to_add)

        await interaction.response.send_message(f"✅ Verified **{user.display_name}**!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error during verify: {e}", ephemeral=True)
        print(f"verify command error: {e}")

@tree.command(name="hcmembers", description="List all [HC1] members with their in-game names.")
async def hcmembers(interaction: discord.Interaction):
    try:
        # Defer immediately
        await interaction.response.defer()

        hc_role = interaction.guild.get_role(ADD_ROLE_ID_HC)
        if not hc_role:
            await interaction.followup.send("❌ [HC1] role not found.")
            return

        members = sorted(hc_role.members, key=lambda m: m.name.lower())
        if not members:
            await interaction.followup.send("No members with [HC1] role found.")
            return

        lines = []
        for idx, member in enumerate(members, 1):
            response = supabase\
                .table("hc_members")\
                .select("ingame_name")\
                .eq("discord_id", str(member.id))\
                .maybe_single()\
                .execute()

            print(f"[hcmembers] supabase response for {member.id!r}: {response!r}")

            ingame_name = "Unknown"
            if response is not None and getattr(response, "data", None):
                ingame_name = response.data.get("ingame_name", "Unknown")

            lines.append(f"{idx}. {member.name} ➔ {ingame_name}")

        list_text = "\n".join(lines)
        await interaction.followup.send(f"**[HC1] Guild Members:**\n{list_text}")

    except Exception as e:
        await interaction.followup.send(f"❌ Error during hcmembers: {e}", ephemeral=True)
        print(f"hcmembers command error: {e}")

@tree.command(name="bulkupdate", description="Bulk update user in-game names.")
async def bulkupdate(interaction: discord.Interaction):
    try:
        await interaction.response.send_modal(BulkUpdateModal())
    except Exception as e:
        await interaction.response.send_message(f"❌ Error opening bulk update modal: {e}", ephemeral=True)
        print(f"bulkupdate command error: {e}")

@tree.command(name="nerdhelp", description="Show list of Catercord slash commands.")
async def nerdhelp(interaction: discord.Interaction):
    try:
        help_text = (
            "**/verify** - Verify a normal Catercord member.\n"
            "**/hcverify** - HC verify a [HC1] member + save their Florr.io name.\n"
            "**/hcmembers** - List all [HC1] members with their in-game names.\n"
            "**/bulkupdate** - Paste and update old member list manually.\n"
            "**/nerdhelp** - Show this help menu."
        )
        await interaction.response.send_message(help_text)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error during nerdhelp: {e}", ephemeral=True)
        print(f"nerdhelp command error: {e}")

keep_alive()

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_BOT_TOKEN environment variable not set.")
