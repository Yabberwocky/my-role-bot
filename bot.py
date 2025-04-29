# -*- coding: utf-8 -*-
import os
import threading
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput # View, Button, button removed as pagination view is removed
from flask import Flask
from supabase import create_client, Client
from postgrest import APIError
import traceback
import math

# --- CONTEXT FOR FUTURE LLMS ---
# (Please do not remove this comment block)
#
# Bot Name: TheNerd's Pingslave
# Owner: Vibhor / TheNerd / sweet_honey (Discord ID: 1230848174218940416)
# Target Server: Catercord (This bot is intended for use only in this specific server)
# Primary Purpose: Manage verification and information related to the "[HC1]" guild within the game Florr.io.
#   - "[HC1]" is a guild in Florr.io, originally named "HC". Members can be HC or non-HC.
#   - The bot verifies members, stores their in-game names (IGNs) in Supabase,
#     maintains a public list of HC members, and provides related utility commands.
# Hosting Environment:
#   - Code Files: `bot.py` (this file), `requirements.txt` (listing discord, supabase, flask)
#   - Platform: Render (Free Tier) via a private GitHub repository.
#   - Keep-Alive: Uses a basic Flask web server (`keep_alive` function) monitored by an external
#     service (like Uptime Robot) hitting the Flask endpoint to prevent Render's free instance from sleeping.
#   - Environment Variables: DISCORD_BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY are set directly in Render's environment settings,
#     not via a .env file in the repository.
# Database: Supabase (PostgreSQL) used to store HC member IGNs linked to Discord IDs.
# Key Features: /verify, /hcverify (stores IGN), /hcmembers (updates list), /syncnicknames, /wither (admin fun).
# --- END CONTEXT ---

# --- Configuration ---
# Load environment variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Define Role and Channel IDs
REMOVE_ROLE_ID = 1360176495947022447 # Unverified role ID
ADD_ROLE_ID_VERIFY = 1248708073019805717 # Verified role ID
ADD_ROLE_ID_HC = 1230235110415274004 # [HC1] role ID

# Allowed Channel IDs for commands like /hcmembers trigger
ALLOWED_CHANNEL_IDS = {1354431395140731165, 1330664430148780102, 1248710731407560835}

# Channel ID for the HC member list messages
HC_MEMBER_LIST_CHANNEL_ID = 1354431395140731165
HC_LIST_EMBED_TITLE = "**\[HC1\] Guild Members**" # Use to find the messages

# Wither command specific IDs
ALLOWED_WITHER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692}
SELF_PROTECTED_ID = 1230848174218940416
BOT_ID = 1365572437185400893
MAX_WITHER_SECONDS = 600 # 10 minutes

# Log Channel IDs
INFO_LOG_CHANNEL_ID = 1317943895606165579
ERROR_LOG_CHANNEL_ID = 1362988767367135453

# Pagination Settings
MEMBERS_PER_PAGE = 50 # Changed back to 50

# --- Style ---
NERDY_YELLOW = discord.Color.gold() # Standard embed color

# --- Supabase Client ---
# (Same as before)
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase client created.")
    except Exception as e:
        print(f"CRITICAL: Failed to create Supabase client: {e}")
        supabase = None
else:
    print("CRITICAL: SUPABASE_URL or SUPABASE_KEY not set. Supabase functionality will be disabled.")
    supabase = None

# --- Discord Setup ---
# (Same as before)
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# --- Flask App for Keep Alive ---
# (Same as before)
app = Flask('')
@app.route('/')
def home(): return "Bot is alive!"
def run_flask():
    try: app.run(host='0.0.0.0', port=8080)
    except Exception as e: print(f"Flask server failed to start: {e}")
def keep_alive():
    t = threading.Thread(target=run_flask)
    t.start()
    print("Keep alive thread started.")

# --- Utility Functions ---
# (run_supabase_sync is the same)
async def run_supabase_sync(func):
    try:
        result = await bot.loop.run_in_executor(None, func)
        return result
    except APIError as api_err:
        print(f"Supabase API Error occurred in executor: {api_err}")
        raise
    except Exception as e:
        print(f"Error running Supabase function in executor: {e}")
        raise

# --- Logging Utility Functions ---
# (Same as before, but using NERDY_YELLOW for info/error embeds)
async def log_to_channel(channel_id: int, guild: discord.Guild, message: str = None, embed: discord.Embed = None):
    if not guild:
        print(f"Log Error: Guild object missing for channel {channel_id}. Message: {message or 'Embed present'}")
        return
    log_channel = guild.get_channel(channel_id)
    if log_channel:
        try:
            if embed:
                await log_channel.send(embed=embed)
            elif message:
                if len(message) > 2000:
                    await log_channel.send(message[:1997] + "...")
                else:
                    await log_channel.send(message)
        except discord.Forbidden:
            print(f"Log Error: Bot lacks permission for channel ID {channel_id} ({guild.name}).")
        except discord.HTTPException as http_err:
            print(f"Log Error: Discord API error sending to {channel_id} ({guild.name}): {http_err.status} {http_err.code} - {http_err.text}")
        except Exception as e:
            print(f"Log Error: Failed to send to channel ID {channel_id} ({guild.name}): {e}")
    else:
        print(f"Log Error: Channel ID {channel_id} not found in guild {guild.name}.")

async def log_info(guild: discord.Guild, message: str, embed: discord.Embed = None):
    if not embed:
        embed = discord.Embed(description=message, color=NERDY_YELLOW) # Use standard yellow
    await log_to_channel(INFO_LOG_CHANNEL_ID, guild, embed=embed)

async def log_error(guild: discord.Guild, message: str, error: Exception = None, interaction: discord.Interaction = None, embed: discord.Embed = None):
    if not embed:
        embed = discord.Embed(title="⚠️ Error / Warning", description=message, color=discord.Color.red()) # Keep errors red
        if interaction:
            context = f"Command: `/{interaction.command.name if interaction.command else 'N/A'}`"
            if interaction.guild: context += f" in #{interaction.channel.name}"
            context += f"\nUser: `{interaction.user}` ({interaction.user.id})"
            embed.add_field(name="Context", value=context, inline=False)
        if error:
            error_details = f"**Type:** `{type(error).__name__}`\n**Message:** `{str(error)}`\n"
            tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__, limit=5))
            if len(tb_str) > 1000: tb_str = tb_str[:1000] + "..."
            error_details += f"**Traceback:**\n```py\n{tb_str}\n```"
            embed.add_field(name="Error Details", value=error_details, inline=False)
            print(f"--- ERROR TRACEBACK ---\nGuild: {guild.id if guild else 'N/A'}\nContext: {message}\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}\n--- END TRACEBACK ---")
    await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, embed=embed)

# --- Core HC List Logic (Refactored for Multi-Message) ---

async def fetch_hc_member_data(guild: discord.Guild) -> tuple[list[tuple[discord.Member, str]], int]:
    # (Same logic as before to fetch data)
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"[fetch_hc_member_data] Error: [HC1] role ({ADD_ROLE_ID_HC}) not found.")
        return [], 0

    members_with_role_unsorted = [m for m in guild.members if hc_role in m.roles]
    total_hc_members_count = len(members_with_role_unsorted)
    members_with_role = sorted(members_with_role_unsorted, key=lambda m: m.display_name.lower())

    member_data_tuples = []
    member_ids = [str(m.id) for m in members_with_role]
    ingame_names = {}

    if supabase and member_ids:
        try:
            response = await run_supabase_sync(
                lambda: supabase.table("hc_members").select("discord_id, ingame_name").in_("discord_id", member_ids).execute()
            )
            if response and response.data:
                for record in response.data:
                    ingame_names[record['discord_id']] = record.get("ingame_name", "Unknown")
            # else: await log_info(guild, f"[fetch_hc_member_data] Supabase returned no IGN data for {len(member_ids)} members.")
        except Exception as e:
            await log_error(guild, f"[fetch_hc_member_data] Error fetching bulk IGNs.", error=e)
            for member_id in member_ids: ingame_names[member_id] = "Error Fetching"

    for member in members_with_role:
        ingame_name = ingame_names.get(str(member.id), "Unknown")
        member_data_tuples.append((member, ingame_name))

    return member_data_tuples, total_hc_members_count

def generate_hc_list_embeds(data: list[tuple[discord.Member, str]], total_members: int) -> list[discord.Embed]:
    """Generates a list of embeds, one for each page."""
    embeds = []
    total_pages = math.ceil(len(data) / MEMBERS_PER_PAGE) if data else 1 # Ensure at least one page even if empty

    for page_num in range(total_pages):
        start_index = page_num * MEMBERS_PER_PAGE
        end_index = start_index + MEMBERS_PER_PAGE
        page_data = data[start_index:end_index]

        embed = discord.Embed(
            title=HC_LIST_EMBED_TITLE,
            color=NERDY_YELLOW # Use standard yellow
        )

        description_lines = []
        current_index = start_index + 1
        for member, ingame_name in page_data:
            safe_member_name = discord.utils.escape_markdown(member.display_name) # Use display_name
            safe_ingame_name = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
            description_lines.append(f"{current_index}. {safe_member_name} ➔ {safe_ingame_name}")
            current_index += 1

        if not description_lines:
            embed.description = "No members found with the [HC1] role." if page_num == 0 else " " # Avoid empty description on later pages if calc is odd
        else:
            embed.description = "\n".join(description_lines)

        embed.set_footer(text=f"Page {page_num + 1}/{total_pages} | Total HC Members: {total_members}")
        embeds.append(embed)

    # Handle completely empty case specifically
    if not data and total_pages == 1:
        embed = discord.Embed(
            title=HC_LIST_EMBED_TITLE,
            description="No members found with the [HC1] role.",
            color=discord.Color.orange() # Use orange for empty state
        )
        embed.set_footer(text="Page 1/1 | Total HC Members: 0")
        return [embed] # Return list with one specific embed

    return embeds


async def update_hc_member_list(guild: discord.Guild):
    """Fetches data and updates the static multi-message list."""
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not list_channel:
        await log_error(guild, f"[update_hc_member_list] Target Channel ({HC_MEMBER_LIST_CHANNEL_ID}) not found.")
        return

    try:
        member_data, total_count = await fetch_hc_member_data(guild)
        new_embeds = generate_hc_list_embeds(member_data, total_count)
        num_new_pages = len(new_embeds)

        # Find existing messages by the bot with the correct embed title
        existing_messages = []
        try:
            async for message in list_channel.history(limit=10): # Check recent messages first
                if message.author == guild.me and message.embeds:
                    if message.embeds[0].title == HC_LIST_EMBED_TITLE:
                        existing_messages.append(message)
            # Sort messages (optional, assuming order doesn't strictly matter or history gives newest first)
            # existing_messages.sort(key=lambda m: m.created_at) # Sort oldest first if needed
        except discord.Forbidden:
            await log_error(guild, f"[update_hc_member_list] Cannot read history in {list_channel.name}.")
            # Attempt to send new messages blindly if history fails? Risky. Better to stop.
            return
        except Exception as e:
            await log_error(guild, "[update_hc_member_list] Error searching message history.", error=e)
            return # Stop if history search fails unexpectedly

        num_existing = len(existing_messages)

        # Update/Send Messages
        for i in range(num_new_pages):
            embed_to_use = new_embeds[i]
            if i < num_existing:
                # Edit existing message
                try:
                    msg_to_edit = existing_messages[i]
                    await msg_to_edit.edit(embed=embed_to_use)
                    await asyncio.sleep(0.5) # Small delay to avoid rate limits
                except (discord.Forbidden, discord.NotFound, discord.HTTPException) as e:
                     await log_error(guild, f"[update_hc_member_list] Failed to edit message {i+1}/{num_existing} (ID: {msg_to_edit.id}).", error=e)
                except Exception as e:
                     await log_error(guild, f"[update_hc_member_list] Unexpected error editing message {i+1}.", error=e)

            else:
                # Send new message
                try:
                    await list_channel.send(embed=embed_to_use)
                    await asyncio.sleep(0.5) # Small delay
                except (discord.Forbidden, discord.HTTPException) as e:
                    await log_error(guild, f"[update_hc_member_list] Failed to send new list message page {i+1}.", error=e)
                except Exception as e:
                    await log_error(guild, f"[update_hc_member_list] Unexpected error sending page {i+1}.", error=e)


        # Delete Extra Old Messages
        if num_existing > num_new_pages:
            messages_to_delete = existing_messages[num_new_pages:]
            for msg_to_delete in messages_to_delete:
                try:
                    await msg_to_delete.delete()
                    await log_info(guild, f"[update_hc_member_list] Deleted surplus list message (ID: {msg_to_delete.id}).")
                    await asyncio.sleep(0.5)
                except (discord.Forbidden, discord.NotFound, discord.HTTPException) as e:
                    await log_error(guild, f"[update_hc_member_list] Failed to delete surplus message (ID: {msg_to_delete.id}).", error=e)
                except Exception as e:
                     await log_error(guild, f"[update_hc_member_list] Unexpected error deleting surplus msg.", error=e)


        await log_info(guild, f"[update_hc_member_list] List update completed. {num_new_pages} pages processed.")

    except Exception as e:
         await log_error(guild, f"[update_hc_member_list] Unexpected error during overall update process.", error=e)

# --- Discord Events ---
# (on_ready, on_member_update, on_app_command_error are the same, relying on updated helpers/list logic)
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} command(s).")
        for guild in bot.guilds:
            await log_info(guild, f"✅ Bot Ready & Commands Synced ({len(synced)} commands).")
            await update_hc_member_list(guild) # Update list on startup
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        try: await log_error(bot.guilds[0], "Bot failed to sync commands on startup.", error=e)
        except Exception as log_e: print(f"Could not log sync failure: {log_e}")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    guild = after.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role: return

    before_has_role = hc_role in before.roles
    after_has_role = hc_role in after.roles

    if before_has_role != after_has_role:
        action = "added to" if after_has_role else "removed from"
        log_embed = discord.Embed(
            description=f"HC role `{hc_role.name}` {action} user `{after.name}` ({after.id}). Triggering list update.",
            color=discord.Color.purple() # Keep event color distinct
        )
        await log_info(guild, "", embed=log_embed)
        await update_hc_member_list(guild)

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    error_message = "❌ An unexpected error occurred."
    log_title = f"App Command Error: /{interaction.command.name if interaction.command else 'N/A'}"
    guild = interaction.guild

    if not guild:
         print(f"App command error outside guild: {error}")
         if not interaction.response.is_done():
             try: await interaction.response.send_message("An error occurred.", ephemeral=True)
             except: pass
         return

    log_description = "An unhandled error occurred."
    log_error_obj = error

    if isinstance(error, app_commands.MissingPermissions):
        missing_perms = ", ".join(error.missing_permissions)
        error_message = f"❌ You lack permissions: `{missing_perms}`"
        log_description = f"User `{interaction.user}` lacked permissions ({missing_perms})."
        log_error_obj = None
    elif isinstance(error, app_commands.CheckFailure):
         error_message = "❌ You failed a required check."
         log_description = f"User `{interaction.user}` failed checks."
         log_error_obj = None
    elif isinstance(error, app_commands.CommandNotFound):
         print(f"Command not found: {interaction.command.name if interaction.command else 'N/A'}")
         return
    elif isinstance(error, app_commands.CommandInvokeError):
        original_error = error.original
        error_message = f"❌ Error executing command: `{type(original_error).__name__}`"
        log_description = f"Error invoking command logic."
        log_error_obj = original_error
    else:
        error_message = "❌ An unknown error occurred."
        log_description = f"Unhandled app command error type: `{type(error).__name__}`"
        log_error_obj = error

    await log_error(guild, log_description, error=log_error_obj, interaction=interaction)

    if not interaction.response.is_done():
        try: await interaction.response.send_message(error_message, ephemeral=True)
        except Exception: pass
    else:
        try: await interaction.followup.send(error_message, ephemeral=True)
        except Exception: pass

# --- Modals ---
# (BulkUpdateModal is the same, using NERDY_YELLOW for result/log embeds)
class BulkUpdateModal(Modal, title="Bulk Update"):
    data = TextInput(label="Paste list (Format: DiscordName ➔ InGameName)", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.guild

        if not supabase:
            embed = discord.Embed(description="❌ Supabase is not configured.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            await log_error(guild, "Bulk update: Supabase not configured.", interaction=interaction)
            return

        success_count, fail_count, not_found_count = 0, 0, 0
        results = []

        lines = self.data.value.strip().splitlines()
        if not lines:
            embed = discord.Embed(description="⚠️ No data provided.", color=discord.Color.orange())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        guild_members = {m.name.lower(): m for m in guild.members} # Use username for matching input

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if "➔" not in line:
                if line: results.append(('fail', f"L{i}: ⚠️ Invalid format: `{line}`"))
                continue
            try:
                username, ingame_name = map(str.strip, line.split("➔", 1))
                if not username or not ingame_name:
                    results.append(('fail', f"L{i}: ⚠️ Missing name: `{line}`"))
                    continue
            except ValueError:
                 results.append(('fail', f"L{i}: ⚠️ Bad separator: `{line}`"))
                 continue

            member = guild_members.get(username.lower())
            if not member:
                fail_count += 1; not_found_count += 1
                results.append(('fail', f"L{i}: ❌ User `{username}` not found."))
                continue

            try:
                await run_supabase_sync(
                    lambda: supabase.table("hc_members").upsert({
                        "discord_id": str(member.id),
                        "discord_name": member.name, # Store current discord username
                        "ingame_name": ingame_name
                    }, on_conflict="discord_id").execute()
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                results.append(('fail', f"L{i}: ❌ Failed {member.name}: `{type(e).__name__}`"))
                await log_error(guild, f"Bulk update Supabase error for {member.name} ({member.id})", error=e, interaction=interaction)

        # Build result embed
        embed = discord.Embed(title="Bulk Update Results", color=NERDY_YELLOW) # Yellow results
        summary = (
            f"✅ Successfully Processed: {success_count}\n"
            f"❌ Failed: {fail_count}\n"
            f"   - User Not Found: {not_found_count}\n"
            f"   - Supabase/Other Errors: {fail_count - not_found_count}"
        )
        embed.description = summary

        error_details = "\n".join([r[1] for r in results if r[0] == 'fail'])
        if error_details:
            if len(error_details) > 1024: error_details = error_details[:1021] + "..."
            embed.add_field(name="Issues", value=error_details, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)
        log_embed = discord.Embed(
            description=f"Bulk update completed by `{interaction.user}`. Success: {success_count}, Failed: {fail_count}.",
            color=NERDY_YELLOW # Yellow log
        )
        await log_info(guild, "", embed=log_embed)

        await update_hc_member_list(guild) # Update list after changes


# --- Slash Commands (Embedified Responses with NERDY_YELLOW) ---

def create_embed(description: str, color: discord.Color = NERDY_YELLOW, title: str = None) -> discord.Embed:
    # Default color is now NERDY_YELLOW
    return discord.Embed(title=title, description=description, color=color)

@tree.command(name="verify", description="Verify a user into Catercord.")
@app_commands.describe(user="The user to verify")
@app_commands.checks.has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    remove_role = guild.get_role(REMOVE_ROLE_ID)
    add_role_verify = guild.get_role(ADD_ROLE_ID_VERIFY)
    actions_taken = []
    log_messages = []

    if not remove_role: log_messages.append(f"Unverified role ({REMOVE_ROLE_ID}) not found.")
    if not add_role_verify: log_messages.append(f"Verified role ({ADD_ROLE_ID_VERIFY}) not found.")
    if log_messages: await log_error(guild, f"/verify setup: {'; '.join(log_messages)}", interaction=interaction)

    try:
        if remove_role and remove_role in user.roles: await user.remove_roles(remove_role); actions_taken.append(f"➖ Removed `{remove_role.name}`")
        if add_role_verify and add_role_verify not in user.roles: await user.add_roles(add_role_verify); actions_taken.append(f"➕ Added `{add_role_verify.name}`")

        if not actions_taken:
            if not remove_role and not add_role_verify: embed = create_embed("❌ Verification roles not found.", discord.Color.red())
            else: embed = create_embed(f"ℹ️ No role changes needed for **{user.display_name}**.", discord.Color.orange())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            log_msg = f"Verified `{user.display_name}`. Actions: {', '.join(actions_taken)}."
            await log_info(guild, f"User `{interaction.user}` triggered: {log_msg}")
            embed = create_embed(f"✅ Verified **{user.display_name}**!\n" + "\n".join(actions_taken), discord.Color.green())
            await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await log_error(guild, "Bot lacks permissions for /verify.", interaction=interaction)
        await interaction.response.send_message(embed=create_embed("❌ I lack role permissions.", discord.Color.red()), ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Error during /verify for {user.display_name}", error=e, interaction=interaction)
        await interaction.response.send_message(embed=create_embed("❌ Verification error.", discord.Color.red()), ephemeral=True)

# (unverify command follows similar embed pattern)
@tree.command(name="unverify", description="Revert a user to unverified status.")
@app_commands.describe(user="The user to unverify")
@app_commands.checks.has_permissions(manage_roles=True)
async def unverify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    remove_role = guild.get_role(ADD_ROLE_ID_VERIFY) # Verified
    add_role = guild.get_role(REMOVE_ROLE_ID)     # Unverified
    actions_taken = []
    log_messages = []

    if not remove_role: log_messages.append(f"Verified role ({ADD_ROLE_ID_VERIFY}) not found.")
    if not add_role: log_messages.append(f"Unverified role ({REMOVE_ROLE_ID}) not found.")
    if log_messages: await log_error(guild, f"/unverify setup: {'; '.join(log_messages)}", interaction=interaction)

    try:
        if remove_role and remove_role in user.roles: await user.remove_roles(remove_role); actions_taken.append(f"➖ Removed `{remove_role.name}`")
        if add_role and add_role not in user.roles: await user.add_roles(add_role); actions_taken.append(f"➕ Added `{add_role.name}`")

        if not actions_taken:
            if not remove_role and not add_role: embed = create_embed("❌ Verification roles not found.", discord.Color.red())
            else: embed = create_embed(f"ℹ️ No role changes needed for **{user.display_name}**.", discord.Color.orange())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            log_msg = f"Unverified `{user.display_name}`. Actions: {', '.join(actions_taken)}."
            await log_info(guild, f"User `{interaction.user}` triggered: {log_msg}")
            embed = create_embed(f"✅ Unverified **{user.display_name}**!\n" + "\n".join(actions_taken), discord.Color.green())
            await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await log_error(guild, "Bot lacks permissions for /unverify.", interaction=interaction)
        await interaction.response.send_message(embed=create_embed("❌ I lack role permissions.", discord.Color.red()), ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Error during /unverify for {user.display_name}", error=e, interaction=interaction)
        await interaction.response.send_message(embed=create_embed("❌ Unverification error.", discord.Color.red()), ephemeral=True)


# (hcverify command follows similar embed pattern)
@tree.command(name="hcverify", description="Verify a user into [HC1], store IGN, and set nickname.")
@app_commands.describe(user="The user to HC verify", ingame_name="Their Florr.io in-game name")
@app_commands.checks.has_permissions(manage_roles=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    await interaction.response.defer(thinking=True)
    guild = interaction.guild
    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Supabase not configured.", discord.Color.red()), ephemeral=True)
        await log_error(guild, "HC verify: Supabase not configured.", interaction=interaction)
        return

    remove_role = guild.get_role(REMOVE_ROLE_ID)
    add_role_verify = guild.get_role(ADD_ROLE_ID_VERIFY)
    add_role_hc = guild.get_role(ADD_ROLE_ID_HC)
    roles_to_add = []
    actions_log, response_details = [], []
    setup_errors = []
    if not add_role_verify: setup_errors.append(f"Verified role ({ADD_ROLE_ID_VERIFY}) missing")
    if not add_role_hc: setup_errors.append(f"HC role ({ADD_ROLE_ID_HC}) missing")
    if setup_errors: await log_error(guild, f"/hcverify setup: {'; '.join(setup_errors)}", interaction=interaction)

    try:
        original_hc_status = add_role_hc and add_role_hc in user.roles
        if remove_role and remove_role in user.roles: await user.remove_roles(remove_role); actions_log.append("Removed Unverified")
        if add_role_verify and add_role_verify not in user.roles: roles_to_add.append(add_role_verify)
        if add_role_hc and add_role_hc not in user.roles: roles_to_add.append(add_role_hc)
        if roles_to_add:
            await user.add_roles(*roles_to_add)
            added_names = ', '.join([f"`{r.name}`" for r in roles_to_add])
            actions_log.append(f"Added: {added_names}"); response_details.append(f"➕ Roles: {added_names}")

        supabase_updated = False
        try:
            await run_supabase_sync(lambda: supabase.table("hc_members").upsert({"discord_id": str(user.id),"discord_name": user.name,"ingame_name": ingame_name}, on_conflict="discord_id").execute())
            actions_log.append("Upserted IGN"); response_details.append(f"💾 IGN: `{ingame_name}`"); supabase_updated = True
        except Exception as e:
            await log_error(guild, f"Supabase upsert failed /hcverify for {user.display_name}", error=e, interaction=interaction)
            actions_log.append("Supabase FAILED"); response_details.append("⚠️ Supabase Failed!")

        target_nick = ingame_name[:32]; nickname_status_msg = ""
        if user.nick != target_nick:
            try:
                await user.edit(nick=target_nick)
                actions_log.append(f"Set nick: '{target_nick}'"); response_details.append(f"🏷️ Nick: `{target_nick}`")
                if target_nick != ingame_name: nickname_status_msg = " (truncated)"
            except discord.Forbidden: actions_log.append("Nick FAILED (Forbidden)"); response_details.append("⚠️ Nick Failed (Perms)"); nickname_status_msg = " (nick fail)"
            except Exception as e: await log_error(guild, f"Nick change fail /hcverify {user.display_name}", error=e, interaction=interaction); actions_log.append(f"Nick FAILED ({type(e).__name__})"); response_details.append("⚠️ Nick Failed (Error)"); nickname_status_msg = " (nick fail)"
        else: actions_log.append("Nick correct"); response_details.append("🏷️ Nick OK")

        log_msg = f"User `{interaction.user}` HC verified `{user.display_name}`. {'; '.join(actions_log)}."
        await log_info(guild, log_msg)
        embed = create_embed(title=f"✅ HC Verified: {user.display_name}{nickname_status_msg}", description="\n".join(response_details) if response_details else "No actions.", color=discord.Color.green() if supabase_updated else discord.Color.orange())
        await interaction.followup.send(embed=embed, ephemeral=False)

        newly_added_hc = add_role_hc and add_role_hc in roles_to_add
        if newly_added_hc or (original_hc_status and supabase_updated): await update_hc_member_list(guild)

    except discord.Forbidden as fe:
        await log_error(guild, "Bot lacks role perms /hcverify.", error=fe, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ I lack role permissions.", discord.Color.red()), ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Unexpected error /hcverify {user.display_name}", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Unexpected error.", discord.Color.red()), ephemeral=True)

# (unhcverify command follows similar embed pattern)
@tree.command(name="unhcverify", description="Remove [HC1] role and reset nickname for a user.")
@app_commands.describe(user="The user to remove from HC.")
@app_commands.checks.has_permissions(manage_roles=True)
async def unhcverify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    actions_log, response_details = [], []

    if not hc_role:
        await log_error(guild, f"/unhcverify: HC role ({ADD_ROLE_ID_HC}) not found.", interaction=interaction)
        await interaction.response.send_message(embed=create_embed("❌ HC Role not found.", discord.Color.red()), ephemeral=True)
        return

    try:
        if hc_role in user.roles: await user.remove_roles(hc_role); actions_log.append(f"Removed HC role"); response_details.append(f"➖ Role: `{hc_role.name}`")
        else: await interaction.response.send_message(embed=create_embed(f"ℹ️ **{user.display_name}** lacks `{hc_role.name}`.", discord.Color.orange()), ephemeral=True); return

        nickname_status_msg = ""
        if user.nick is not None:
            try: await user.edit(nick=None); actions_log.append("Reset nick"); response_details.append("🏷️ Reset Nickname")
            except discord.Forbidden: actions_log.append("Nick reset FAILED (Forbidden)"); response_details.append("⚠️ Nick Reset Failed (Perms)"); nickname_status_msg = " (nick fail)"
            except Exception as e: await log_error(guild, f"Nick reset fail /unhcverify {user.display_name}", error=e, interaction=interaction); actions_log.append(f"Nick reset FAILED ({type(e).__name__})"); response_details.append("⚠️ Nick Reset Failed (Error)"); nickname_status_msg = " (nick fail)"
        else: actions_log.append("No nick"); response_details.append("🏷️ No Nickname")

        log_msg = f"User `{interaction.user}` un-HC-verified `{user.display_name}`. {'; '.join(actions_log)}."
        await log_info(guild, log_msg)
        embed = create_embed(title=f"✅ Un-HC-Verified: {user.display_name}{nickname_status_msg}", description="\n".join(response_details), color=discord.Color.green())
        await interaction.response.send_message(embed=embed) # Public response

    except discord.Forbidden as fe:
        await log_error(guild, "Bot lacks role perms /unhcverify.", error=fe, interaction=interaction)
        await interaction.response.send_message(embed=create_embed("❌ I lack role permissions.", discord.Color.red()), ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Unexpected error /unhcverify {user.display_name}", error=e, interaction=interaction)
        if not interaction.response.is_done(): await interaction.response.send_message(embed=create_embed("❌ Unexpected error.", discord.Color.red()), ephemeral=True)
        else: await interaction.followup.send(embed=create_embed("❌ Unexpected error.", discord.Color.red()), ephemeral=True)


@tree.command(name="hcmembers", description="Update and show the location of the [HC1] member list.")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)

    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        embed = create_embed("❌ This command requires specific channels.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True) # Ephemeral response

    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Supabase not configured.", discord.Color.red()), ephemeral=True)
        return
    if not list_channel:
         await interaction.followup.send(embed=create_embed("❌ List channel not found.", discord.Color.red()), ephemeral=True)
         return

    try:
        # Trigger an update first
        await update_hc_member_list(guild)
        # Then respond telling the user where to look
        embed = create_embed(f"✅ The HC member list in {list_channel.mention} has been updated!", color=discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_info(guild, f"/hcmembers triggered list update by `{interaction.user}`.")

    except Exception as e:
        await log_error(guild, "[hcmembers] Error triggering update.", error=e, interaction=interaction)
        embed = create_embed("❌ Error updating the member list.", discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)


# (bulkupdate, refresh commands follow similar embed patterns)
@tree.command(name="bulkupdate", description="Bulk update user in-game names via modal.")
@app_commands.checks.has_permissions(manage_roles=True)
async def bulkupdate(interaction: discord.Interaction):
    try:
        await interaction.response.send_modal(BulkUpdateModal())
        await log_info(interaction.guild, f"Opened bulk update modal for `{interaction.user}`.")
    except Exception as e:
        await log_error(interaction.guild, "Error opening bulk update modal.", error=e, interaction=interaction)
        if not interaction.response.is_done(): await interaction.response.send_message(embed=create_embed("❌ Error opening modal.", discord.Color.red()), ephemeral=True)

@tree.command(name="refresh", description="Refresh the [HC1] member list manually.")
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    guild = interaction.guild
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)

    if not supabase: await interaction.followup.send(embed=create_embed("❌ Supabase not configured.", discord.Color.red()), ephemeral=True); return
    if not list_channel: await interaction.followup.send(embed=create_embed("❌ List channel not found.", discord.Color.red()), ephemeral=True); return

    try:
        await update_hc_member_list(guild)
        embed = create_embed(f"✅ Refreshed HC list in {list_channel.mention}!", discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_info(guild, f"Manual refresh triggered by `{interaction.user}`.")
    except Exception as e:
        await log_error(guild, "Error during manual /refresh.", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Error refreshing list.", discord.Color.red()), ephemeral=True)


# (syncnicknames command follows similar embed patterns)
@tree.command(name="syncnicknames", description="Sync all HC members' nicknames with their stored IGN.")
@app_commands.checks.has_permissions(manage_roles=True)
async def syncnicknames(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    guild = interaction.guild

    if not supabase: await interaction.followup.send(embed=create_embed("❌ Supabase not configured.", discord.Color.red()), ephemeral=True); return
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role: await interaction.followup.send(embed=create_embed("❌ HC Role not found.", discord.Color.red()), ephemeral=True); return

    await log_info(guild, f"Starting nickname sync triggered by `{interaction.user}`.")
    await interaction.edit_original_response(content="🔄 Fetching data...")

    ign_data = {}
    try:
        response = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").execute())
        if response and response.data: ign_data = {item['discord_id']: item['ingame_name'] for item in response.data if item.get('ingame_name')}
        # await log_info(guild, f"Fetched {len(ign_data)} records for sync.")
    except Exception as e: await log_error(guild, "Failed fetch Supabase /syncnicknames.", error=e, interaction=interaction); await interaction.edit_original_response(content="❌ DB Fetch Failed."); return

    counts = {'success': 0, 'skipped': 0, 'no_ign': 0, 'perm_error': 0, 'other_error': 0, 'processed': 0}
    hc_members_in_guild = [m for m in guild.members if hc_role in m.roles]
    total_hc_members = len(hc_members_in_guild)

    await interaction.edit_original_response(content=f"🔄 Syncing {total_hc_members} members...")

    for i, member in enumerate(hc_members_in_guild):
        counts['processed'] += 1
        if i % 25 == 0 and i > 0: await interaction.edit_original_response(content=f"🔄 Syncing... ({i}/{total_hc_members})")

        member_id_str = str(member.id)
        if member_id_str not in ign_data: counts['no_ign'] += 1; continue
        ingame_name = ign_data[member_id_str]; target_nick = ingame_name[:32]
        if member.nick == target_nick: counts['skipped'] += 1; continue

        try: await member.edit(nick=target_nick); counts['success'] += 1
        except discord.Forbidden: counts['perm_error'] += 1
        except Exception as e: counts['other_error'] += 1; await log_error(guild, f"SyncNick Error: {member.name}", error=e, interaction=interaction)

    embed = discord.Embed(title="Nickname Sync Complete!", color=NERDY_YELLOW) # Yellow report
    summary = f"Processed: {counts['processed']} | ✅ Updated: {counts['success']} | ℹ️ Skipped: {counts['skipped']} | ⚠️ No IGN: {counts['no_ign']} | ❌ Perm Errors: {counts['perm_error']} | ❌ Other Errors: {counts['other_error']}"
    embed.description = summary
    await interaction.edit_original_response(content=None, embed=embed)

    log_embed = discord.Embed(title="Nickname Sync Finished", description=summary, color=NERDY_YELLOW)
    log_embed.set_footer(text=f"Triggered by {interaction.user}")
    await log_info(guild, "", embed=log_embed)


# (wither command follows similar embed patterns)
@tree.command(name="wither", description="Temporarily remove all roles from a user.")
@app_commands.describe(user="The user to wither", time="Time (in minutes, defaults to 2, max 10)")
async def wither(interaction: discord.Interaction, user: discord.Member, time: float = 2.0):
    guild = interaction.guild
    interaction_user = interaction.user

    async def wither_fail_log(reason: str, error: Exception = None): await log_error(guild, f"Wither Failure: {reason}", error=error, interaction=interaction)

    if interaction_user.id not in ALLOWED_WITHER_IDS: await wither_fail_log(f"User lacks permission."); await interaction.response.send_message(embed=create_embed("❌ No wither permission.", discord.Color.red()), ephemeral=True); return
    if user.id == interaction_user.id: await wither_fail_log("Self-wither attempt."); await interaction.response.send_message(embed=create_embed("🤨 Don't wither yourself.", discord.Color.orange()), ephemeral=True); return
    # Add other protected user checks similarly...

    time_seconds = int(time * 60)
    if time <= 0 or time_seconds > MAX_WITHER_SECONDS: await wither_fail_log(f"Invalid time: {time}"); await interaction.response.send_message(embed=create_embed(f"❌ Time must be > 0 and <= {MAX_WITHER_SECONDS/60:.0f} mins.", discord.Color.red()), ephemeral=True); return
    if guild.me.top_role <= user.top_role: await wither_fail_log(f"Bot role too low for {user.name}."); await interaction.response.send_message(embed=create_embed("❌ Cannot wither someone mightier!", discord.Color.red()), ephemeral=True); return

    original_roles = [role for role in user.roles if role != guild.default_role]
    if not original_roles: await wither_fail_log(f"{user.name} has no roles."); await interaction.response.send_message(embed=create_embed(f"❌ {user.display_name} has no roles.", discord.Color.red()), ephemeral=True); return

    try:
        await user.edit(roles=[])
        role_names = ', '.join([f"`{r.name}`" for r in original_roles])
        embed = create_embed(title="🌪️ Wither Cast! 🌪️", description=f"{user.mention} withered by {interaction_user.mention} for **{time:.2f} mins**!\nRoles removed: {role_names}", color=discord.Color.dark_purple())
        await interaction.response.send_message(embed=embed)
        await log_info(guild, f"`{user.name}` withered by `{interaction_user.name}` for {time:.2f} mins.")

        await asyncio.sleep(time_seconds)

        try:
             member_after_wait = await guild.fetch_member(user.id)
             if member_after_wait:
                 await member_after_wait.edit(roles=original_roles)
                 await interaction.followup.send(embed=create_embed(f"✨ {user.mention} recovered!", color=NERDY_YELLOW)) # Yellow recovery
                 await log_info(guild, f"Restored roles for `{user.name}`.")
             else: await log_info(guild, f"`{user.name}` left before roles restored.")
        except discord.NotFound: await log_info(guild, f"`{user.name}` not found for role restore.")
        except discord.Forbidden as fe: await wither_fail_log("Restore roles Forbidden.", error=fe); await interaction.followup.send(embed=create_embed(f"⚠️ Failed role restore (Perms).", discord.Color.red()), ephemeral=True)
        except Exception as e: await wither_fail_log("Restore roles failed.", error=e); await interaction.followup.send(embed=create_embed(f"⚠️ Error restoring roles.", discord.Color.red()), ephemeral=True)

    except discord.Forbidden as fe: await wither_fail_log("Remove roles Forbidden.", error=fe); await interaction.response.send_message(embed=create_embed("❌ Lacked perms to remove roles!", discord.Color.red()), ephemeral=True) # Wither failed to start
    except Exception as e: await wither_fail_log("Unexpected wither error.", error=e); await interaction.response.send_message(embed=create_embed("❌ Unexpected wither error.", discord.Color.red()), ephemeral=True) # Wither failed to start


@tree.command(name="nerdhelp", description="Show Catercord slash commands help menu.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(
        title="🤓 Catercord Command List",
        description="Use these commands to manage members and the HC list.",
        color=NERDY_YELLOW # Yellow help
    )
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)

    # Helper to format command help fields
    def add_help_field(name: str, value: str, permissions: str = None, notes: str = None):
        full_value = value
        if permissions: full_value += f"\n**Permissions:** `{permissions}`"
        if notes: full_value += f"\n**Note:** {notes}"
        embed.add_field(name=name, value=full_value, inline=False)

    # Add fields using the helper
    add_help_field(name="/verify <user>", value="Verify a standard member.", permissions="Manage Roles")
    add_help_field(name="/unverify <user>", value="Revert a member to unverified.", permissions="Manage Roles")
    add_help_field(name="/hcverify <user> <ingame_name>", value="Verify member into HC, store IGN, set nickname.", permissions="Manage Roles")
    add_help_field(name="/unhcverify <user>", value="Remove HC role and reset nickname.", permissions="Manage Roles")
    add_help_field(name="/hcmembers", value=f"Triggers an update of the HC member list.", notes=f"List is posted in {list_channel.mention if list_channel else 'designated channel'}. Command usable in allowed channels.")
    add_help_field(name="/bulkupdate", value="Open modal to bulk add/update IGNs.", permissions="Manage Roles")
    add_help_field(name="/refresh", value=f"Manually refresh the HC member list.", permissions="Manage Roles", notes=f"Updates list in {list_channel.mention if list_channel else 'designated channel'}.")
    add_help_field(name="/syncnicknames", value="Sync all HC members' nicknames from stored IGNs.", permissions="Manage Roles")
    add_help_field(name="/wither <user> [time]", value="Temporarily remove all roles.", notes=f"Max {MAX_WITHER_SECONDS/60:.0f} mins. Requires special permission.")
    add_help_field(name="/nerdhelp", value="Show this help menu.")

    embed.set_footer(text="Stay nerdy!")
    if interaction.client.user.display_avatar:
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True) # Keep help ephemeral


# --- Bot Startup ---
if __name__ == "__main__":
    if TOKEN:
        if supabase:
            keep_alive()
            try: print("Starting Bot..."); bot.run(TOKEN)
            except Exception as e: print(f"CRITICAL: Bot run failed: {e}")
        else: print("CRITICAL: Supabase client failed. Bot not started.")
    else: print("CRITICAL: DISCORD_BOT_TOKEN not set. Bot not started.")
