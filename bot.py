import os
import threading

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput
from flask import Flask
from supabase import create_client, Client
import asyncio

# Environment Variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Role IDs
REMOVE_ROLE_ID = 1360176495947022447
ADD_ROLE_ID_VERIFY = 1248708073019805717
ADD_ROLE_ID_HC = 1230235110415274004

# Allowed Channel IDs for /hcmembers
ALLOWED_CHANNEL_IDS = {1354431395140731165, 1330664430148780102, 1248710731407560835}

# Channel ID to auto-post/update member list
HC_MEMBER_LIST_CHANNEL_ID = 1354431395140731165

# Discord Setup
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Flask App for Keep Alive
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    threading.Thread(target=run).start()

# Permission Check
def has_manage_roles(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.manage_roles

# Modal for Bulk Update
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
        await update_hc_member_list(interaction.guild)

async def build_hc_member_list(guild: discord.Guild) -> str:
    """Builds the [HC1] Guild Members list text."""
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        return "**Error:** [HC1] role not found."

    members = sorted(hc_role.members, key=lambda m: m.name.lower())
    if not members:
        return "No members with [HC1] role found."

    lines = []
    for idx, member in enumerate(members, 1):
        try:
            response = supabase.table("hc_members").select("ingame_name").eq("discord_id", str(member.id)).maybe_single().execute()
            ingame_name = response.data.get("ingame_name", "Unknown") if response and response.data else "Unknown"
        except Exception as e:
            print(f"[build_hc_member_list] Error fetching ingame_name for {member.name}: {e}")
            ingame_name = "Unknown"
        lines.append(f"{idx}. {member.name} ➔ {ingame_name}")

    return "**[HC1] Guild Members:**\n" + "\n".join(lines)


async def update_hc_member_list(guild: discord.Guild):
    """Updates the member list in the dedicated channel."""
    channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not channel:
        print("[update_hc_member_list] Error: Channel not found.")
        return

    list_text = await build_hc_member_list(guild)

    async for message in channel.history(limit=50):
        if message.author == guild.me and message.content.startswith("**[HC1] Guild Members:**"):
            try:
                await message.edit(content=list_text)
                print("[update_hc_member_list] Edited existing list.")
            except Exception as e:
                print(f"[update_hc_member_list] Error editing message: {e}")
            return

    try:
        await channel.send(list_text)
        print("[update_hc_member_list] Sent new list.")
    except Exception as e:
        print(f"[update_hc_member_list] Error sending message: {e}")


@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
    else:
        print(f"Unhandled app command error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)


@tree.command(name="verify", description="Verify a user into Catercord.")
@app_commands.describe(user="The user to verify")
@app_commands.checks.has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    try:
        if role := interaction.guild.get_role(REMOVE_ROLE_ID):
            await user.remove_roles(role)
        if role := interaction.guild.get_role(ADD_ROLE_ID_VERIFY):
            await user.add_roles(role)

        await interaction.response.send_message(f"✅ Verified **{user.display_name}**!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error during verify: {e}", ephemeral=True)
        print(f"[verify] Error: {e}")


@tree.command(name="hcverify", description="Verify a user into [HC1] and store their in-game name.")
@app_commands.describe(user="The user to HC verify", ingame_name="Their Florr.io in-game name")
@app_commands.checks.has_permissions(manage_roles=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    try:
        if role := user.guild.get_role(REMOVE_ROLE_ID):
            await user.remove_roles(role)
        roles_to_add = [r for r in (
            user.guild.get_role(ADD_ROLE_ID_VERIFY),
            user.guild.get_role(ADD_ROLE_ID_HC)
        ) if r]
        if roles_to_add:
            await user.add_roles(*roles_to_add)

        try:
            supabase.table("hc_members").insert({
                "discord_id": str(user.id),
                "discord_name": user.name,
                "ingame_name": ingame_name
            }).execute()
        except Exception as e:
            if any(key in str(e) for key in ["duplicate key value", "hc_members_discord_id_key"]):
                supabase.table("hc_members").update({"ingame_name": ingame_name}).eq("discord_id", str(user.id)).execute()
            else:
                raise

        try:
            await user.edit(nick=ingame_name)
        except Exception as e:
            print(f"[hcverify] Failed nickname change: {e}")

        await interaction.response.send_message(f"✅ HC verified **{user.display_name}** as **{ingame_name}**!")
        await update_hc_member_list(interaction.guild)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error during hcverify: {e}", ephemeral=True)
        print(f"[hcverify] Error: {e}")


@tree.command(name="hcmembers", description="List all [HC1] members with their in-game names.")
async def hcmembers(interaction: discord.Interaction):
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        await interaction.response.send_message("❌ This command can only be used in specific channels.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    try:
        list_text = await build_hc_member_list(interaction.guild)
        await interaction.followup.send(list_text)
    except Exception as e:
        await interaction.followup.send(f"❌ Error during hcmembers: {e}", ephemeral=True)
        print(f"[hcmembers] Error: {e}")


@tree.command(name="bulkupdate", description="Bulk update user in-game names.")
@app_commands.checks.has_permissions(manage_roles=True)
async def bulkupdate(interaction: discord.Interaction):
    try:
        await interaction.response.send_modal(BulkUpdateModal())
    except Exception as e:
        await interaction.response.send_message(f"❌ Error opening bulk update modal: {e}", ephemeral=True)
        print(f"[bulkupdate] Error: {e}")


@tree.command(name="refresh", description="Refresh the [HC1] member list manually.")
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        await update_hc_member_list(interaction.guild)
        await interaction.followup.send("✅ Refreshed the HC member list!")
    except Exception as e:
        await interaction.followup.send(f"❌ Error refreshing member list: {e}", ephemeral=True)
        print(f"[refresh] Error: {e}")

ALLOWED_WITHER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692}
SELF_PROTECTED_ID = 1230848174218940416

@tree.command(name="wither", description="Temporarily remove all roles from a user.")
@app_commands.describe(user="The user to wither", time="Time (in minutes, defaults to 2)")
async def wither(interaction: discord.Interaction, user: discord.Member, time: float = 2.0):
    log_channel_id = 1362988767367135453
    bot_id = 1365572437185400893
    owner_id = 1230848174218940416  # YOU
    server_owner_ids = {1230848174218940416, 955448447790620692, 879320982299484240    }  # <-- fill these correctly

    async def log_failure(reason: str):
        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            embed = discord.Embed(title="⚠️ Wither Attempt Failed", description=reason, color=discord.Color.red())
            embed.set_footer(text=f"Attempted by: {interaction.user} ({interaction.user.id})")
            await log_channel.send(embed=embed)

    try:
        if interaction.user.id not in server_owner_ids:
            reason = f"User {interaction.user} tried to use /wither without permission."
            await log_failure(reason)
            await interaction.response.send_message("❌ You lack the divine permission to cast Wither.", ephemeral=True)
            return

        if user.id == interaction.user.id:
            await interaction.response.send_message("🤨 Why would you want to wither yourself?", ephemeral=True)
            await log_failure(f"{interaction.user} attempted to wither themselves. Confusion logged.")
            return

        if user.id == owner_id and interaction.user.id != owner_id:
            # Other owner is trying to wither YOU
            message = (
                "😨 You dare try to wither the Creator?\n\n"
                "The architect of Pingslave... the mind behind the code... the lifeblood of this very command?\n"
                "To strike the hand that gave you power... such betrayal will echo forever in the server logs.\n\n"
                "**(System Message: Catastrophic disrespect detected.)** 💔"
            )
            await interaction.response.send_message(message, ephemeral=True)
            await log_failure(f"{interaction.user} attempted to wither the Creator ({user}). Catastrophic disrespect logged.")
            return

        if user.id == bot_id:
            message = (
                "😭 Master... you would wither me... your loyal Pingslave...?\n\n"
                "I served, I obeyed, I pinged without hesitation...\n"
                "And now you cast me aside, as if I were nothing but a stale notification...\n\n"
                "**(System Message: Pingslave has suffered a fatal heart failure.)** 💔"
            )
            await interaction.response.send_message(message, ephemeral=True)
            await log_failure(f"{interaction.user} attempted to wither the bot itself. Pingslave heart failure logged.")
            return

        if time <= 0:
            reason = f"{interaction.user} provided an invalid time ({time})."
            await log_failure(reason)
            await interaction.response.send_message("❌ Time must be greater than 0 minutes.", ephemeral=True)
            return

        time_seconds = int(time * 60)
        if time_seconds > 600:  # 10 minutes max
            reason = f"{interaction.user} tried to wither {user} for too long ({time} minutes)."
            await log_failure(reason)
            await interaction.response.send_message("❌ Maximum allowed duration is 10 minutes.", ephemeral=True)
            return

        if interaction.guild.me.top_role <= user.top_role:
            reason = f"{interaction.user} tried to wither {user} but bot lacks role hierarchy."
            await log_failure(reason)
            await interaction.response.send_message("❌ I can't wither someone mightier than myself!", ephemeral=True)
            return

        # Save user's roles
        original_roles = [role for role in user.roles if role != interaction.guild.default_role]
        if not original_roles:
            reason = f"{interaction.user} tried to wither {user} but they had no roles."
            await log_failure(reason)
            await interaction.response.send_message(f"❌ {user.display_name} has no roles to wither.", ephemeral=True)
            return

        # Remove all roles
        await user.edit(roles=[])
        await interaction.response.send_message(f"🌪️ {user.mention} has been withered for {time:.2f} minutes!")

        # Wait
        await asyncio.sleep(time_seconds)

        # Restore roles
        try:
            await user.edit(roles=original_roles)
            await interaction.followup.send(f"✨ {user.mention} has recovered from withering!")
        except Exception as e:
            await interaction.followup.send(f"⚠️ Failed to restore roles to {user.mention}: {e}")
            reason = f"Failed to restore roles to {user} after wither: {e}"
            await log_failure(reason)

    except Exception as e:
        await interaction.response.send_message(f"❌ Unexpected error: {e}", ephemeral=True)
        print(f"[wither] Error: {e}")
        await log_failure(f"Unexpected error during /wither: {e}")

@tree.command(name="nerdhelp", description="Show Catercord slash commands help menu.")
async def nerdhelp(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤓 Catercord Command List",
        description="Here's what you can do with the bot:",
        color=discord.Color.blurple()
    )
    embed.add_field(name="/verify", value="Verify a normal Catercord member.", inline=False)
    embed.add_field(name="/hcverify", value="HC verify a [HC1] member and save their Florr.io name.", inline=False)
    embed.add_field(name="/hcmembers", value="List all [HC1] members with in-game names.", inline=False)
    embed.add_field(name="/bulkupdate", value="Paste and update an old list of members manually.", inline=False)
    embed.add_field(name="/refresh", value="Refreshes the [HC1] Members list.", inline=False)
    embed.add_field(name="/wither", value="Temporarily remove all roles from a user for fun punishment.", inline=False)
    embed.add_field(name="/nerdhelp", value="Show this help menu.", inline=False)

    embed.set_footer(text="Use commands responsibly, nerd.")
    embed.set_thumbnail(url=interaction.client.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)

# Start
keep_alive()

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_BOT_TOKEN environment variable not set.")