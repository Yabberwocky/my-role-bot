import os
import threading

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput
from flask import Flask
from supabase import create_client, Client

# Environment variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Role IDs
REMOVE_ROLE_ID = 1360176495947022447
ADD_ROLE_ID_VERIFY = 1248708073019805717
ADD_ROLE_ID_HC = 1230235110415274004

# Discord intents and bot setup
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Flask app for keep_alive
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    threading.Thread(target=run).start()

# Permission check function
def has_manage_roles(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.manage_roles

# Modal for bulk update
class BulkUpdateModal(Modal, title="Bulk Update"):
    data = TextInput(label="Paste the list below", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        success_count = 0
        fail_count = 0
        errors = []

        lines = self.data.value.splitlines()

        for line in lines:
            if "➔" not in line:
                continue

            username, ingame_name = map(str.strip, line.split("➔", 1))
            member = discord.utils.find(lambda m: m.name.lower() == username.lower(), interaction.guild.members)

            if not member:
                fail_count += 1
                errors.append(f"❌ {username} not found.")
                continue

            try:
                supabase.table("hc_members").insert({
                    "discord_id": str(member.id),
                    "discord_name": member.name,
                    "ingame_name": ingame_name
                }).execute()
                success_count += 1

            except Exception as e:
                error_str = str(e)
                if "duplicate key value" in error_str or '"hc_members_discord_id_key"' in error_str:
                    errors.append(f"⚠️ {member.name} already exists. Skipped.")
                else:
                    errors.append(f"❌ Failed to update {member.name}: {e}")
                fail_count += 1

        result_message = (
            f"✅ Successfully updated {success_count} members.\n"
            f"❌ Failed to update {fail_count} members.\n\n"
            + "\n".join(errors)
        )

        await interaction.followup.send(result_message)


# Bot ready event
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

# Slash Commands

@tree.command(name="verify", description="Verify a user into Catercord.")
@app_commands.describe(user="The user to verify")
@app_commands.checks.has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    try:
        role_to_remove = interaction.guild.get_role(REMOVE_ROLE_ID)
        role_to_add = interaction.guild.get_role(ADD_ROLE_ID_VERIFY)

        if role_to_remove:
            await user.remove_roles(role_to_remove)
        if role_to_add:
            await user.add_roles(role_to_add)

        await interaction.response.send_message(f"✅ Verified **{user.display_name}**!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error during verify: {e}", ephemeral=True)
        print(f"[verify] Error: {e}")

@tree.command(name="hcverify", description="Verify a user into [HC1] (Catercord) and store their Florr.io in-game name.")
@app_commands.describe(user="The user to HC verify", ingame_name="Their Florr.io in-game name")
@app_commands.checks.has_permissions(manage_roles=True)
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

        try:
            supabase.table("hc_members").insert({
                "discord_id": str(user.id),
                "discord_name": user.name,
                "ingame_name": ingame_name
            }).execute()
        except Exception as e:
            error_str = str(e)
            if "duplicate key value" in error_str or '"hc_members_discord_id_key"' in error_str:
                # Duplicate found: Update ingame_name instead
                supabase.table("hc_members")\
                    .update({"ingame_name": ingame_name})\
                    .eq("discord_id", str(user.id))\
                    .execute()
            else:
                raise e  # Unknown error, re-raise

        try:
            await user.edit(nick=ingame_name)
        except Exception as e:
            print(f"Failed to change nickname for {user.name}: {e}")

        await interaction.response.send_message(f"✅ HC verified **{user.display_name}** as **{ingame_name}**!")

    except Exception as e:
        await interaction.response.send_message(f"❌ Error during hcverify: {e}", ephemeral=True)
        print(f"hcverify command error: {e}")

@tree.command(name="hcmembers", description="List all [HC1] members with their in-game names.")
async def hcmembers(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    try:
        hc_role = interaction.guild.get_role(ADD_ROLE_ID_HC)
        if not hc_role:
            await interaction.followup.send("❌ [HC1] role not found.", ephemeral=True)
            return

        members = sorted(hc_role.members, key=lambda m: m.name.lower())
        if not members:
            await interaction.followup.send("No members with [HC1] role found.", ephemeral=True)
            return

        lines = []
        for idx, member in enumerate(members, 1):
            response = supabase.table("hc_members").select("ingame_name").eq("discord_id", str(member.id)).maybe_single().execute()
            ingame_name = response.data.get("ingame_name", "Unknown") if response and response.data else "Unknown"
            lines.append(f"{idx}. {member.name} ➔ {ingame_name}")

        list_text = "\n".join(lines)
        await interaction.followup.send(f"**[HC1] Guild Members:**\n{list_text}")
    except Exception as e:
        await interaction.followup.send(f"❌ Error during hcmembers: {e}", ephemeral=True)
        print(f"[hcmembers] Error: {e}")

@tree.command(name="bulkupdate", description="Bulk update user in-game names.")
async def bulkupdate(interaction: discord.Interaction):
    if not has_manage_roles(interaction):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    try:
        await interaction.response.send_modal(BulkUpdateModal())
    except Exception as e:
        await interaction.response.send_message(f"❌ Error opening bulk update modal: {e}", ephemeral=True)
        print(f"[bulkupdate] Error: {e}")

@tree.command(name="nerdhelp", description="Show Catercord slash commands help menu.")
async def nerdhelp(interaction: discord.Interaction):
    help_text = (
        "**/verify** — Verify a normal Catercord member.\n"
        "**/hcverify** — HC verify a [HC1] member and save their Florr.io name.\n"
        "**/hcmembers** — List all [HC1] members with in-game names.\n"
        "**/bulkupdate** — Paste and update old member list manually.\n"
        "**/nerdhelp** — Show this help menu."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# Start everything
keep_alive()

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_BOT_TOKEN environment variable not set.")
