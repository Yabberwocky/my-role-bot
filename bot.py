# -*- coding: utf-8 -*-
import os
import threading
import asyncio
import discord
from discord import app_commands
from typing import Dict, Optional
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button, button
from flask import Flask
from supabase import create_client, Client
from postgrest import APIError
import traceback
import math
from typing import Optional, Tuple, List, Dict, Any # Keep this one, it's used more broadly
from dotenv import load_dotenv
import datetime
import pytz # Add this import at the top
from dateutil.parser import parse as date_parse # Add this import at the top
from dateutil.relativedelta import relativedelta # Add this import at the top

# --- CONTEXT FOR FUTURE LLMS ---
# (Please do not remove this comment block)
#
# Bot Name: TheNerd's Pingslave
# Owner: Vibhor / TheNerd / sweet_honey (Discord ID: 1230848174218940416)
# Target Server: Catercord (This bot is intended for use only in this specific server)
# Primary Purpose: Manage verification and information related to the "[HC1]" guild within the game Florr.io.
#   - "[HC1]" is a guild in Florr.io, originally named "HC". Members can be HC or non-HC.
#   - The bot verifies members, stores their in-game names (IGNs) in Supabase,
#     maintains a static public list of HC members in a dedicated channel (numbered, username#tag ➔ IGN format),
#     provides an interactive paginated list via /hcmembers (numbered, username#tag ➔ IGN format),
#     and offers utility commands. /bulkupdate expects username#tag ➔ IGN format (no numbers).
# Hosting Environment:
#   - Code Files: `bot.py` (this file), `requirements.txt` (listing discord, supabase, flask)
#   - Platform: Render (Free Tier) via a private GitHub repository.
#   - Keep-Alive: Uses a basic Flask web server (`keep_alive` function) monitored by an external
#     service (like Uptime Robot) hitting the Flask endpoint to prevent Render's free instance from sleeping.
#   - Environment Variables: DISCORD_BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY are set directly in Render's environment settings.
# Database: Supabase (PostgreSQL) used to store HC member IGNs linked to Discord IDs.
# Key Features: /verify, /hcverify (stores IGN), static list updates, /hcmembers (interactive list), /syncnicknames, /wither, /nerdhelp.
# (Check /nerdhelp's code for latest list of features. This list might be outdated.)
# --- LLM INSTRUCTION ---
# (Please do not remove this comment block)
# NOTE TO FUTURE LLMS: This `bot.py` file is quite large.
# When providing modifications, please **DO NOT** rewrite the entire file.
# Instead, provide **ONLY** the specific functions, classes, commands,
# or relevant code blocks that need to be changed or added.
# This makes merging changes much easier. Thank you!
# --- END LLM INSTRUCTION ---
# --- END CONTEXT ---

# --- Configuration ---
load_dotenv()  # harmless in production; only loads if a .env file exists
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
REMOVE_ROLE_ID = 1360176495947022447 # "Unverified" role
ADD_ROLE_ID_VERIFY = 1248708073019805717 # "Verified" role
ADD_ROLE_ID_HC = 1230235110415274004 # "HC" role
ALLOWED_CHANNEL_IDS = {1354431395140731165, 1330664430148780102, 1248710731407560835, 1367362849122549801} # Channels for /hcmembers
HC_MEMBER_LIST_CHANNEL_ID = 1354431395140731165 # Channel for static list
HC_LIST_EMBED_TITLE = "**\[HC1\] Guild Members**"
ALLOWED_WITHER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692} # User IDs for /wither
SELF_PROTECTED_ID = 1230848174218940416 # Protected from /wither
BOT_ID: Optional[int] = None # Bot's own User ID (set in on_ready)
MAX_WITHER_SECONDS = 600 # Max duration for /wither (10 minutes)
INFO_LOG_CHANNEL_ID = 1317943895606165579 # Info log channel
ERROR_LOG_CHANNEL_ID = 1362988767367135453 # Error log channel
MEMBERS_PER_PAGE = 50 # Members per page in lists
NERDY_YELLOW = discord.Color.gold() # Embed color
ROLE_ID_MAYBE_EXHC = 1267882075390873681 # Role to add on HC leave, remove on HC verify
VIEW_MODE_DISCORD = "discord_view"
VIEW_MODE_ACTIVITY_ALL = "activity_all_view" # Renamed for clarity
VIEW_MODE_ACTIVITY_DAILY = "activity_daily_view"
VIEW_MODE_ACTIVITY_WEEKLY = "activity_weekly_view"
VIEW_MODE_ACTIVITY_MONTHLY = "activity_monthly_view" # Using 30 days for simplicity
SORT_MODE_IGN = "sort_ign"
SORT_MODE_ACTIVITY = "sort_activity"
ACTIVITY_COLUMN_WIDTH = 18 # Increase width for "Count (Last Seen)"
COMMAND_PREFIX = "." # Define the prefix
AUTODELETE_CHANNEL_ID = 1354431395140731165
AUTODELETE_DELAY_SECONDS = 5.0

# --- Supabase Client ---
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try: supabase = create_client(SUPABASE_URL, SUPABASE_KEY); print("Supabase client created successfully.")
    except Exception as e: print(f"CRITICAL: Failed Supabase client creation: {e}"); supabase = None
else: print("CRITICAL: Supabase credentials missing."); supabase = None

# --- Discord Setup ---
intents = discord.Intents.default()
intents.members = True       # You already have this for member events/fetching
intents.message_content = True # <<<--- ADD THIS LINE
# Define bot instance here before using it in logging setup
# Use the defined COMMAND_PREFIX here if you want bot.process_commands for other text commands later
# If you ONLY have slash commands + the .p handler, command_prefix doesn't strictly matter for .p
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents) # Use COMMAND_PREFIX here
tree = bot.tree
command_ids: Dict[str, int] = {} # Dictionary to store command IDs after sync

# --- Flask App (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Pingslave bot is alive!"
def run_flask():
    try: port = int(os.environ.get('PORT', 8080)); print(f"Starting Flask server on 0.0.0.0:{port}"); app.run(host='0.0.0.0', port=port)
    except Exception as e: print(f"Flask server failed: {e}\n{traceback.format_exc()}")
def keep_alive(): flask_thread = threading.Thread(target=run_flask, daemon=True); flask_thread.start(); print("Keep alive thread initiated.")

# --- Utility Functions ---


# --- Bulk Active Modal ---
class BulkActiveModal(Modal, title="Bulk Mark Active"):
    igns_input = TextInput(
        label="In-Game Names (IGNs)",
        style=discord.TextStyle.paragraph,
        placeholder="Enter one IGN per line or separate by spaces/commas...",
        required=True,
        max_length=2000 # Adjust as needed
    )

    def __init__(self, date_str: Optional[str]):
        super().__init__(timeout=300.0) # 5 minute timeout for modal
        self.target_date_str = date_str # Store the date passed from the command

    async def on_submit(self, interaction: discord.Interaction):
        # Defer the modal's interaction response ephemerally
        await interaction.response.defer(thinking=True, ephemeral=False)

        guild = interaction.guild
        if not guild or not supabase: # Ensure guild and supabase are available
            await interaction.followup.send("❌ Error: Command context or database unavailable.", ephemeral=False)
            return

        # --- Get Date ---
        activity_date, date_error = get_utc_date(self.target_date_str)
        if date_error:
            await interaction.followup.send(f"❌ {date_error}", ephemeral=False)
            return
        if not activity_date:
            await interaction.followup.send("❌ Could not determine activity date.", ephemeral=False)
            return

        # --- Process IGNs ---
        raw_text = self.igns_input.value
        # Split by newline, space, comma, and filter out empty strings
        potential_igns = [ign.strip() for line in raw_text.split('\n') for part in line.replace(',', ' ').split(' ') if ign.strip()]

        if not potential_igns:
            await interaction.followup.send("❌ No IGNs were entered.", ephemeral=False)
            return

        processed_count = 0
        success_count = 0
        already_marked_count = 0 # Technically upsert handles this, but good for feedback
        failed_igns = []
        log_details = []

        # Consider fetching all known IGNs first for validation if performance allows and is needed
        # For now, we'll just try the upsert for each

        progress_msg = await interaction.followup.send(f"⏳ Processing {len(potential_igns)} IGNs for {format_date_dmy(activity_date)}...", ephemeral=False)

        for ign in potential_igns:
            processed_count += 1
            # Basic validation (e.g., length) could be added here
            if not ign: continue

            success, msg = await upsert_activity_log(guild, ign, activity_date, interaction.user.id)

            if success:
                success_count += 1
                log_details.append(f"OK: {ign}")
                # We can't easily tell if it was new or updated from upsert without another query
                # For simplicity, we just count successes.
            else:
                failed_igns.append(f"`{ign}` ({msg.split(': ')[-1]})") # Add IGN and brief reason
                log_details.append(f"Fail: {ign} ({msg})")

            # Optional: Update progress message periodically if processing many IGNs
            # if processed_count % 10 == 0:
            #     try: await progress_msg.edit(content=f"⏳ Processing... ({processed_count}/{len(potential_igns)})")
            #     except discord.HTTPException: pass # Ignore edit errors

        # --- Final Feedback ---
        summary_title = "✅ Bulk Activity Update Complete"
        summary_desc = [f"Date Processed: **{format_date_dmy(activity_date)}**"]
        summary_desc.append(f"Total Entries Submitted: {len(potential_igns)}")
        summary_desc.append(f"Successfully Recorded/Updated: {success_count}")
        # summary_desc.append(f"Already Marked: {already_marked_count}") # If we add check later
        if failed_igns:
            summary_title = "⚠️ Bulk Activity Update Partially Complete"
            summary_desc.append(f"Failed Entries ({len(failed_igns)}):")
            # Show first few failed IGNs directly in message
            max_failed_display = 10
            summary_desc.extend([f"- {f}" for f in failed_igns[:max_failed_display]])
            if len(failed_igns) > max_failed_display:
                 summary_desc.append(f"- ...and {len(failed_igns) - max_failed_display} more (check logs).")
        else:
             summary_desc.append("Failed Entries: 0")

        summary_embed = discord.Embed(title=summary_title, description="\n".join(summary_desc), color=NERDY_YELLOW if not failed_igns else discord.Color.orange())

        try:
            await progress_msg.edit(content=None, embed=summary_embed)
        except discord.HTTPException: # Handle if original progress message gone
             await interaction.followup.send(embed=summary_embed, ephemeral=False) # Send new message

        await log_info(guild, f"`{interaction.user}` used /bulkactive. Summary: {len(potential_igns)} submitted, {success_count} success, {len(failed_igns)} failed. Details: {'; '.join(log_details)}")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await log_error(interaction.guild, "Error in BulkActiveModal", error=error, interaction=interaction)
        # Ensure the user gets some feedback even if the modal logic fails
        try:
             if interaction.response.is_done():
                 await interaction.followup.send("❌ An unexpected error occurred in the modal.", ephemeral=False)
             else:
                 # This case is less likely if on_submit deferred, but handle defensively
                 await interaction.response.send_message("❌ An unexpected error occurred in the modal.", ephemeral=False)
        except Exception:
             pass # Ignore errors during error reporting

async def ign_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes In-Game Names from the hc_members table."""
    if not supabase:
        print("IGN Autocomplete: Supabase unavailable.")
        return [] # Return empty list if DB is down

    # Limit the number of suggestions returned
    limit = 25
    choices = []

    # Avoid querying if input is too short (optional, but can reduce load)
    # if len(current) < 1:
    #     return []

    try:
        # Use ilike for case-insensitive matching, % for wildcard
        # Select distinct IGNs to avoid duplicates if schema allows multiple entries per IGN
        query = supabase.table("hc_members").select("ingame_name", count='exact').ilike("ingame_name", f"%{current}%").not_.is_("ingame_name", "null").limit(limit)
        resp = await run_supabase_sync(lambda: query.execute())

        if resp and hasattr(resp, 'data') and resp.data:
            seen_igns = set() # Prevent duplicate suggestions if DB returns them
            for item in resp.data:
                ign = item.get("ingame_name")
                if ign and ign not in seen_igns:
                     # Ensure name and value are strings
                    ign_str = str(ign)
                    # Truncate suggestion name if too long for Discord UI
                    display_name = (ign_str[:97] + '...') if len(ign_str) > 100 else ign_str
                    choices.append(app_commands.Choice(name=display_name, value=ign_str))
                    seen_igns.add(ign)

    except (ConnectionError, APIError) as e:
        print(f"IGN Autocomplete Error: Failed to fetch IGNs matching '{current}'. Error: {e}")
        # Optionally return a choice indicating an error
        # choices = [app_commands.Choice(name="Error fetching suggestions...", value="ERROR")]
    except Exception as e:
         print(f"IGN Autocomplete Unexpected Error: {e}")

    # print(f"IGN Autocomplete: Found {len(choices)} choices for '{current}'") # Debugging
    return choices

async def remove_activity_log(guild: discord.Guild, ign: str, activity_date: datetime.date, remover_id: int) -> Tuple[bool, str]:
    """Removes an activity record. Returns (success, message). Handles case-insensitivity."""
    if not supabase: return False, "Database unavailable."
    if not ign: return False, "IGN cannot be empty."

    # Standardize IGN to lowercase for lookup
    ign_lower = ign.lower()

    try:
        # Execute the delete operation
        resp = await run_supabase_sync(
            lambda: supabase.table("activity_log")
                           .delete()
                           .eq("member_identifier", ign_lower) # Match lowercase IGN
                           .eq("activity_date", activity_date.isoformat()) # Match exact date
                           .execute()
        )

        # Check if any rows were actually deleted.
        # The structure of 'resp.data' for delete might vary.
        # A common pattern is that it contains the deleted records.
        # If resp.data is non-empty, deletion occurred.
        if resp and hasattr(resp, 'data') and resp.data:
            return True, f"Activity record removed for `{ign}` on {format_date_dmy(activity_date)}."
        else:
            # No error, but nothing deleted - likely record didn't exist
            return False, f"No activity record found for `{ign}` on {format_date_dmy(activity_date)} to remove."

    except APIError as e:
        err_msg = f"Database API error removing activity for `{ign}`: {e.message}"
        await log_error(guild, err_msg, error=e)
        return False, err_msg
    except (ConnectionError, Exception) as e:
        err_msg = f"Database connection/unexpected error removing activity for `{ign}`."
        await log_error(guild, err_msg, error=e)
        return False, err_msg

def get_utc_date(date_str: Optional[str] = None) -> Tuple[Optional[datetime.date], Optional[str]]:
    """Parses a YYYY-MM-DD string or defaults to today's UTC date. Returns date object and error message."""
    if date_str:
        try:
            # Lenient parsing, but enforce basic structure checks if needed
            if len(date_str) != 10 or date_str[4] != '-' or date_str[7] != '-':
                 raise ValueError("Expected YYYY-MM-DD format.")
            # Attempt to parse
            dt_obj = date_parse(date_str)
            # Return only the date part, assuming UTC context from input string is less relevant than just the date itself
            return dt_obj.date(), None
        except ValueError as e:
            return None, f"Invalid date format or value: `{date_str}`. Please use YYYY-MM-DD. Error: {e}"
        except Exception as e: # Catch other potential parsing errors
             return None, f"Could not parse date `{date_str}`. Error: {e}"
    else:
        # Default to today's UTC date
        return datetime.datetime.now(pytz.utc).date(), None

def format_date_dmy(date_obj: Optional[datetime.date]) -> str:
    """Formats a date object as DD/MM/YYYY or returns 'N/A'."""
    if date_obj:
        return date_obj.strftime("%d/%m/%Y")
    return "N/A"

async def get_ign_from_user(guild: discord.Guild, user_id: int) -> Optional[str]:
    """Fetches the stored IGN for a given Discord user ID from hc_members."""
    if not supabase: return None
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("ingame_name")
                           .eq("discord_id", str(user_id))
                           .maybe_single() # Fetch single record or None
                           .execute()
        )
        if resp and hasattr(resp, 'data') and resp.data and resp.data.get("ingame_name"):
            return resp.data["ingame_name"]
        return None
    except (ConnectionError, APIError, Exception) as e:
        await log_error(guild, f"Failed to fetch IGN for user ID {user_id}", error=e)
        return None # Return None on error

async def upsert_activity_log(guild: discord.Guild, ign: str, activity_date: datetime.date, recorder_id: int) -> Tuple[bool, str]:
    """Upserts an activity record. Returns (success, message). Handles case-insensitivity."""
    if not supabase: return False, "Database unavailable."
    if not ign: return False, "IGN cannot be empty."

    # Standardize IGN to lowercase for storage/lookup
    ign_lower = ign.lower()

    try:
        # Use upsert with ON CONFLICT to handle duplicates based on the unique constraint
        await run_supabase_sync(
            lambda: supabase.table("activity_log")
                           .upsert({
                               "member_identifier": ign_lower, # Store lowercase IGN
                               "activity_date": activity_date.isoformat(), # Format date as YYYY-MM-DD string
                               "recorded_by_id": str(recorder_id) # Optional: store who recorded it
                               # 'created_at' should be handled by DB default
                           }, on_conflict="member_identifier, activity_date") # Use the unique constraint columns
                           .execute()
        )
        # Note: Upsert response doesn't reliably tell if insert or update happened easily.
        # We assume success if no error. Check logs for specific errors if needed.
        return True, f"Activity recorded for `{ign}` on {format_date_dmy(activity_date)}."
    except APIError as e:
        err_msg = f"Database API error recording activity for `{ign}`: {e.message}"
        await log_error(guild, err_msg, error=e)
        return False, err_msg
    except (ConnectionError, Exception) as e:
        err_msg = f"Database connection/unexpected error recording activity for `{ign}`."
        await log_error(guild, err_msg, error=e)
        return False, err_msg

async def fetch_activity_data(guild: discord.Guild, identifiers: List[str], start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None) -> Dict[str, Dict[str, Any]]:
    """
    Fetches activity counts and last seen date for given IGN identifiers (case-insensitive) within a date range.
    Returns: {'ign_lower': {'count': int, 'last_seen': date | None}}
    """
    if not supabase or not identifiers:
        return {}

    # Standardize identifiers to lowercase for querying
    identifiers_lower = [ign.lower() for ign in identifiers]
    results: Dict[str, Dict[str, Any]] = {ign_lower: {'count': 0, 'last_seen': None} for ign_lower in identifiers_lower}

    try:
        query = supabase.table("activity_log").select("member_identifier, activity_date").in_("member_identifier", identifiers_lower)
        if start_date:
            query = query.gte("activity_date", start_date.isoformat())
        if end_date:
            query = query.lte("activity_date", end_date.isoformat())

        # Fetch all relevant activity logs in chunks if needed (though likely fine for typical ranges)
        all_logs = []
        # Simple fetch for now, add pagination if needed for very large ranges/servers
        resp = await run_supabase_sync(lambda: query.execute())

        if resp and hasattr(resp, 'data') and resp.data:
            all_logs = resp.data

        # Process logs in Python
        for log in all_logs:
            ign_lower = log['member_identifier'] # Already lowercase from query filter
            activity_date_str = log['activity_date']
            try:
                 current_log_date = datetime.datetime.strptime(activity_date_str, '%Y-%m-%d').date()
            except ValueError:
                 print(f"Warning: Skipping invalid date format '{activity_date_str}' in activity log for {ign_lower}")
                 continue # Skip this invalid record

            if ign_lower in results:
                results[ign_lower]['count'] += 1
                # Update last_seen date if this log is newer
                if results[ign_lower]['last_seen'] is None or current_log_date > results[ign_lower]['last_seen']:
                    results[ign_lower]['last_seen'] = current_log_date

        return results

    except (ConnectionError, APIError, Exception) as e:
        await log_error(guild, f"Failed to fetch activity data for {len(identifiers)} identifiers", error=e)
        return {} # Return empty dict on error

async def check_supabase_available(interaction: discord.Interaction) -> bool:
    """
    Checks if Supabase client is initialized. If not, sends an ephemeral error
    response/followup to the interaction and logs the error. Returns True if available, False otherwise.
    """
    if supabase:
        return True
    else:
        # Supabase client is None (failed initialization or not configured)
        error_message_user = "❌ Database connection unavailable. This feature cannot be used right now."
        log_description = f"Command '/{interaction.command.name if interaction.command else 'Unknown'}' failed: Supabase client is not available."

        # Log the error internally
        await log_error(interaction.guild, log_description, interaction=interaction)

        # Try to inform the user ephemerally
        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_message_user, ephemeral=False)
            else:
                # If not deferred/responded yet, respond directly
                await interaction.response.send_message(error_message_user, ephemeral=False)
        except (discord.NotFound, discord.InteractionResponded, discord.HTTPException) as e:
             # Log if sending the user message fails, but the function still returns False
             print(f"Error sending Supabase check failure message to user (InteractionID: {interaction.id}): {type(e).__name__} - {e}")
        except Exception as e_send:
            print(f"Unexpected Error sending Supabase check failure message (InteractionID: {interaction.id}): {e_send}")

        return False # Indicate Supabase is not available

async def run_supabase_sync(func):
    """Runs sync Supabase func in executor."""
    if not supabase: raise ConnectionError("Supabase client unavailable.")
    try: loop = asyncio.get_running_loop(); return await loop.run_in_executor(None, func)
    except APIError as e: print(f"Supabase API Error: {e}"); raise
    except Exception as e: print(f"Supabase executor Error: {e}"); raise

# --- Logging ---
async def log_to_channel(channel_id: int, guild: Optional[discord.Guild], message: Optional[str] = None, embed: Optional[discord.Embed] = None):
    """Sends log to a channel, checking permissions."""
    if not guild: print(f"Log Error: No Guild for channel {channel_id}."); return
    log_channel = guild.get_channel(channel_id)
    if not isinstance(log_channel, discord.TextChannel): print(f"Log Error: Channel {channel_id} invalid in {guild.name}."); return
    # Check bot object exists before accessing bot.user
    if not bot or not bot.user: print(f"Log Error: Bot not ready, cannot get member object in {guild.name}."); return
    bot_member = guild.get_member(bot.user.id)
    if not bot_member: print(f"Log Error: Cannot find bot ({bot.user.id if bot.user else 'N/A'}) in {guild.name}."); return
    perms = log_channel.permissions_for(bot_member)
    if not perms.send_messages or (embed and not perms.embed_links): print(f"Log Error: Missing Send/Embed perms in {log_channel.mention}."); return
    try:
        if embed: await log_channel.send(embed=embed)
        elif message: await log_channel.send((message[:1997] + "...") if len(message) > 2000 else message)
    except discord.Forbidden: print(f"Log Error: Forbidden in {log_channel.mention}.")
    except discord.HTTPException as e: print(f"Log Error: HTTP {e.status} in {log_channel.mention}: {e.text}")
    except Exception as e: print(f"Log Error: Send fail in {log_channel.mention}: {e}")

async def log_info(guild: Optional[discord.Guild], message: str, embed: Optional[discord.Embed] = None):
    """Logs an info message."""
    if not embed: embed = discord.Embed(description=message, color=NERDY_YELLOW); embed.timestamp = discord.utils.utcnow()
    await log_to_channel(INFO_LOG_CHANNEL_ID, guild, embed=embed)

async def log_error(guild: Optional[discord.Guild], message: str, error: Optional[Exception] = None, interaction: Optional[discord.Interaction] = None, embed: Optional[discord.Embed] = None):
    """Logs an error with context and traceback."""
    if not embed:
        embed = discord.Embed(title="⚠️ Bot Error / Warning", description=message, color=discord.Color.red()); embed.timestamp = discord.utils.utcnow()
        if interaction:
            cmd_name = interaction.command.name if interaction.command else 'N/A'
            cmd = f"`/{cmd_name}`"
            chan_mention = interaction.channel.mention if isinstance(interaction.channel, discord.TextChannel) else ""
            chan_info = f" in {chan_mention}" if chan_mention else f" Ch:{interaction.channel_id}" if interaction.channel else ""
            user = f"{interaction.user.mention} (`{interaction.user.id}`)"
            embed.add_field(name="Context", value=f"Cmd: {cmd}{chan_info}\nUser: {user}", inline=False)
        if error:
            etype, emsg = type(error).__name__, str(error)
            tb = "".join(traceback.format_exception(type(error), error, error.__traceback__, limit=6))
            # Truncate traceback more aggressively
            tb_short = (tb[:900] + "\n... (Truncated)") if len(tb) > 900 else tb # ADJUSTED TRUNCATION
            details = f"**Type:** `{etype}`\n" + (f"**Msg:** `{emsg}`\n" if emsg else "") + f"**Traceback:**\n```py\n{tb_short}\n```"
            # Keep the final check, but reduce its limit slightly too for safety
            if len(details) > 1024:
                 details = details[:1000] + "...```" # ADJUSTED TRUNCATION
            embed.add_field(name="Error Details", value=details, inline=False)
            full_tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            print(f"---\nERROR LOGGED:\nGuild: {guild.id if guild else 'N/A'}\nCtx: {message}\nErr: {etype}: {emsg}\n{full_tb}---\n")
    await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, embed=embed)

# --- Embed Pagination View ---

class ActivitySortButton(Button):
     def __init__(self, current_sort: str, row: int):
          # Determine label and style based on current sort
          label = "Sort by IGN" if current_sort == SORT_MODE_ACTIVITY else "Sort by Activity"
          style = discord.ButtonStyle.success # Or choose another style
          super().__init__(label=label, style=style, custom_id="hc_toggle_sort", row=row)

     async def callback(self, interaction: discord.Interaction):
          # Tell the view to handle the sort toggle
          view: HCPagesView = self.view # Type hint for clarity
          if view:
               await view.toggle_sort(interaction)



class ViewModeSelect(discord.ui.Select):
     def __init__(self, current_mode: str, row: int):
          options = [
               discord.SelectOption(label="View Discord Names + IGN", value=VIEW_MODE_DISCORD, description="Show Discord usernames and IGNs.", emoji="👤"),
               discord.SelectOption(label="View Activity (Today)", value=VIEW_MODE_ACTIVITY_DAILY, description="Show IGNs active today.", emoji="📅"),
               discord.SelectOption(label="View Activity (Last 7 Days)", value=VIEW_MODE_ACTIVITY_WEEKLY, description="Show IGNs active in the last week.", emoji="📅"),
               discord.SelectOption(label="View Activity (Last 30 Days)", value=VIEW_MODE_ACTIVITY_MONTHLY, description="Show IGNs active in the last 30 days.", emoji="📅"), # Or use a calendar month emoji
               discord.SelectOption(label="View Activity (All-Time)", value=VIEW_MODE_ACTIVITY_ALL, description="Show IGNs and total activity count.", emoji="📊"),
          ]
          # Ensure the current mode is set as default
          for option in options:
                option.default = option.value == current_mode

          super().__init__(placeholder="Select View Mode...", min_values=1, max_values=1, options=options, custom_id="hc_view_select", row=row)

     async def callback(self, interaction: discord.Interaction):
          view: HCPagesView = self.view
          if view:
               selected_mode = self.values[0]
               # Let the view handle the mode change and potential data refetching
               await view.change_view_mode(interaction, selected_mode)


class HCPagesView(View):
    # Data is List[Dict[str, Any]] from fetch_hc_member_data (includes ALL-TIME activity)
    def __init__(self, original_data: List[Dict[str, Any]], initial_display_data: List[Dict[str, Any]], total_members: int, guild: discord.Guild, timeout=300.0): # Added guild parameter
        super().__init__(timeout=timeout)
        # original_data holds the base info + all-time activity fetched initially
        self.original_data = original_data
        # current_data is initialized with the pre-fetched data for the default view
        self.current_data = initial_display_data # Use the passed initial data
        self.total_members = total_members
        self.current_page = 0
        self.message: Optional[discord.Message] = None
        self.guild = guild # Store guild if needed later

        # --- State ---
        # SET DEFAULTS HERE
        self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY # <<< DEFAULT VIEW
        self.sort_mode = SORT_MODE_ACTIVITY       # <<< DEFAULT SORT for activity views
        self.is_fetching_activity = False # Lock to prevent concurrent fetches

        # --- Initial Sort ---
        # Sort the initial data based on the default sort mode
        self.sort_data() # This sorts self.current_data

        # --- Recalculate total pages AFTER initial sort ---
        self.total_pages = math.ceil(len(self.current_data) / MEMBERS_PER_PAGE) if self.current_data else 1

        # --- Add UI Elements ---
        # Pass the INITIAL sort mode to the button
        self.add_item(ActivitySortButton(current_sort=self.sort_mode, row=1))
        # Pass the INITIAL view mode to the select menu
        self.add_item(ViewModeSelect(current_mode=self.view_mode, row=2))
        # Buttons added via decorators

        # Update UI elements based on the initial state
        self.update_buttons_and_ui()

    def sort_data(self):
        """Sorts self.current_data based on self.sort_mode and retains page number if valid."""
        # --- Store current page before sorting ---
        stored_page = self.current_page

        # Ensure activity_count exists, default to 0 if missing
        if self.sort_mode == SORT_MODE_IGN:
            self.current_data.sort(key=lambda item: item.get('ign', 'zzz').lower())
        elif self.sort_mode == SORT_MODE_ACTIVITY:
            # Sort descending by count, then ascending by IGN as tie-breaker
            self.current_data.sort(key=lambda item: (item.get('activity_count', 0) * -1, item.get('ign', 'zzz').lower()))

        # --- Recalculate total pages ---
        self.total_pages = math.ceil(len(self.current_data) / MEMBERS_PER_PAGE) if self.current_data else 1

        # --- Restore or adjust current page ---
        if stored_page < self.total_pages:
            # If stored page is still valid in the new page range, keep it
            self.current_page = stored_page
        else:
            # Otherwise, go to the last available page (or page 0 if no pages)
            self.current_page = max(0, self.total_pages - 1)


    def update_buttons_and_ui(self):
        """Updates UI elements based on state."""
        # --- Update Page Buttons ---
        prev_button = discord.utils.find(lambda i: hasattr(i, 'custom_id') and i.custom_id == 'hc_prev_interactive', self.children)
        next_button = discord.utils.find(lambda i: hasattr(i, 'custom_id') and i.custom_id == 'hc_next_interactive', self.children)
        if isinstance(prev_button, Button): prev_button.disabled = self.current_page == 0 or self.is_fetching_activity
        if isinstance(next_button, Button): next_button.disabled = self.current_page >= self.total_pages - 1 or self.is_fetching_activity

        # --- Update Sort Button ---
        sort_button = discord.utils.find(lambda i: hasattr(i, 'custom_id') and i.custom_id == 'hc_toggle_sort', self.children)
        if isinstance(sort_button, Button):
             sort_button.label = "Sort by IGN" if self.sort_mode == SORT_MODE_ACTIVITY else "Sort by Activity"
             # Disable sort button while fetching data or if in discord view
             sort_button.disabled = self.is_fetching_activity or self.view_mode == VIEW_MODE_DISCORD

        # --- Update Select Default & Disable ---
        select_menu = discord.utils.find(lambda i: hasattr(i, 'custom_id') and i.custom_id == 'hc_view_select', self.children)
        if isinstance(select_menu, discord.ui.Select):
             select_menu.disabled = self.is_fetching_activity # Disable dropdown during fetch
             for option in select_menu.options:
                  option.default = option.value == self.view_mode

    # --- REVISED create_page_embed ---
    def create_page_embed(self) -> discord.Embed:
        """Creates embed based on current view_mode and sort_mode."""
        start = self.current_page * MEMBERS_PER_PAGE
        page_data = self.current_data[start : start + MEMBERS_PER_PAGE]

        IDX_WIDTH = 3
        if self.view_mode == VIEW_MODE_DISCORD:
             NAME_WIDTH = 15
             IGN_WIDTH = 15
             ACT_WIDTH = 0 # No activity column
             TOTAL_WIDTH = IDX_WIDTH + NAME_WIDTH + IGN_WIDTH
             header = (f"{'#':<{IDX_WIDTH}}{'Discord':<{NAME_WIDTH}}{'In-Game':<{IGN_WIDTH}}")
        # All activity views use the same layout now
        elif self.view_mode in [VIEW_MODE_ACTIVITY_ALL, VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
             IGN_WIDTH = 20
             ACT_WIDTH = ACTIVITY_COLUMN_WIDTH # Use constant
             TOTAL_WIDTH = IDX_WIDTH + IGN_WIDTH + ACT_WIDTH
             header = (f"{'#':<{IDX_WIDTH}}{'In-Game':<{IGN_WIDTH}}{'Activity':<{ACT_WIDTH}}")
        else: # Fallback
             NAME_WIDTH = 15; IGN_WIDTH = 15; ACT_WIDTH = 0
             TOTAL_WIDTH = IDX_WIDTH + NAME_WIDTH + IGN_WIDTH
             header = (f"{'#':<{IDX_WIDTH}}{'Discord':<{NAME_WIDTH}}{'In-Game':<{IGN_WIDTH}}")

        separator = "-" * TOTAL_WIDTH

        desc_lines = [f"```", header, separator]
        idx = start + 1

        if not page_data:
            desc_lines = ["```\nNo members found matching criteria.\n```"]
        else:
            for item_dict in page_data:
                member = item_dict.get('member')
                ign = item_dict.get('ign', 'Unknown')

                if self.view_mode == VIEW_MODE_DISCORD:
                    if member: user_display = f"{member.name}#{member.discriminator}" if member.discriminator != '0' else member.name
                    else: user_display = "[No Discord]"
                    ign_display = ign
                    if len(user_display) > NAME_WIDTH: user_display = user_display[:NAME_WIDTH-1] + "…"
                    if len(ign_display) > IGN_WIDTH: ign_display = ign_display[:IGN_WIDTH-1] + "…"
                    line = (f"{str(idx)+'.':<{IDX_WIDTH}}"
                            f"{user_display:<{NAME_WIDTH}}"
                            f"{ign_display:<{IGN_WIDTH}}")

                elif self.view_mode in [VIEW_MODE_ACTIVITY_ALL, VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
                    activity_count = item_dict.get('activity_count', 0)
                    last_seen_date = item_dict.get('last_seen') # date object or None
                    ign_display = ign
                    # Format activity: Count (Last Seen DD/MM/YY)
                    activity_display = f"{activity_count} ({format_date_dmy(last_seen_date)})"

                    if len(ign_display) > IGN_WIDTH: ign_display = ign_display[:IGN_WIDTH-1] + "…"
                    if len(activity_display) > ACT_WIDTH: activity_display = activity_display[:ACT_WIDTH-1] + "…"
                    line = (f"{str(idx)+'.':<{IDX_WIDTH}}"
                            f"{ign_display:<{IGN_WIDTH}}"
                            f"{activity_display:<{ACT_WIDTH}}")
                else: # Fallback
                     line = f"{str(idx)+'.':<{IDX_WIDTH}} Error: Invalid View Mode"

                desc_lines.append(line)
                idx += 1
            desc_lines.append("```")

        embed = discord.Embed(
            title=HC_LIST_EMBED_TITLE,
            description="\n".join(desc_lines),
            color=NERDY_YELLOW
        )

        # --- Update Footer Text Based on View Mode ---
        sort_text = "IGN" if self.sort_mode == SORT_MODE_IGN else "Activity"
        view_text_map = {
            VIEW_MODE_DISCORD: "Discord+IGN",
            VIEW_MODE_ACTIVITY_ALL: "Activity (All)",
            VIEW_MODE_ACTIVITY_DAILY: "Activity (Today)",
            VIEW_MODE_ACTIVITY_WEEKLY: "Activity (7d)",
            VIEW_MODE_ACTIVITY_MONTHLY: "Activity (30d)",
        }
        view_text = view_text_map.get(self.view_mode, "Unknown View")
        footer_text=f"Page {self.current_page + 1}/{self.total_pages} | Total: {self.total_members} | View: {view_text} | Sort: {sort_text}"
        if self.is_fetching_activity:
             footer_text += " | Fetching data..."

        embed.set_footer(text=footer_text)
        embed.timestamp = discord.utils.utcnow()
        return embed

    async def edit_message(self, interaction: discord.Interaction, show_loading: bool = False):
        """Updates the message embed and view components. Optionally shows loading state."""
        # Update button states etc. *before* creating embed
        self.update_buttons_and_ui()
        embed = self.create_page_embed() # Embed reflects current state (incl. loading footer if show_loading=True)
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.NotFound:
            print(f"Paginator edit fail: Interaction {interaction.id} or message not found.")
            self.stop()
        except discord.HTTPException as e:
            guild = interaction.guild or (self.message.guild if self.message else None)
            # Avoid logging interaction cancelled errors if user was quick
            if e.code != 10062: # Unknown Interaction
                 await log_error(guild, "Paginator edit fail (HTTP)", error=e, interaction=interaction)
        except Exception as e:
            guild = interaction.guild or (self.message.guild if self.message else None)
            await log_error(guild, "Paginator edit fail (General)", error=e, interaction=interaction)

    # --- Button Callbacks (No changes needed) ---
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="hc_prev_interactive", row=0)
    async def previous_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0 and not self.is_fetching_activity:
            self.current_page -= 1
            await self.edit_message(interaction)
        else:
            await interaction.response.defer() # Ack the interaction

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple, custom_id="hc_next_interactive", row=0)
    async def next_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1 and not self.is_fetching_activity:
            self.current_page += 1
            await self.edit_message(interaction)
        else:
            await interaction.response.defer() # Ack

    # --- Sort Callback (Disable during fetch) ---
    async def toggle_sort(self, interaction: discord.Interaction):
        """Called by the ActivitySortButton."""
        if self.is_fetching_activity:
             await interaction.response.defer() # Ignore if fetching
             return

        if self.view_mode == VIEW_MODE_DISCORD:
             # Maybe allow sorting by discord name/ign? For now, just ack.
             await interaction.response.send_message("Sorting is only available in Activity views.", ephemeral=True)
             return

        if self.sort_mode == SORT_MODE_IGN:
            self.sort_mode = SORT_MODE_ACTIVITY
        else:
            self.sort_mode = SORT_MODE_IGN
        self.sort_data() # Re-sort the current data
        await self.edit_message(interaction) # Update the message

# --- REVISED change_view_mode (within HCPagesView class) ---
    async def change_view_mode(self, interaction: discord.Interaction, new_mode: str):
        """Called by the ViewModeSelect. Handles data fetching for activity views."""
        if self.view_mode == new_mode or self.is_fetching_activity:
            await interaction.response.defer() # Ack if mode didn't change or already fetching
            return

        # --- Set Loading State ---
        self.is_fetching_activity = True
        self.view_mode = new_mode # Update mode immediately for UI feedback
        # This is the FIRST response to the interaction - OK
        await self.edit_message(interaction, show_loading=True)

        guild = interaction.guild # Needed for logging/fetching

        try:
            # ... [Keep all the data fetching logic exactly as it is] ...
            start_date: Optional[datetime.date] = None
            end_date: Optional[datetime.date] = None
            today_utc = datetime.datetime.now(pytz.utc).date()

            # Determine date range based on new mode
            if new_mode == VIEW_MODE_ACTIVITY_DAILY:
                start_date = end_date = today_utc
            elif new_mode == VIEW_MODE_ACTIVITY_WEEKLY:
                end_date = today_utc
                start_date = today_utc - datetime.timedelta(days=6)
            elif new_mode == VIEW_MODE_ACTIVITY_MONTHLY:
                end_date = today_utc
                start_date = today_utc - datetime.timedelta(days=29)
            # VIEW_MODE_ACTIVITY_ALL and VIEW_MODE_DISCORD don't need specific range fetch here

            # --- Fetch and Update Data ---
            if new_mode in [VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
                # Fetch activity data ONLY for the required range
                all_igns = [item['ign'] for item in self.original_data if item.get('ign')]
                if not all_igns:
                     print("Change View Mode: No IGNs found in original data.")
                     self.current_data = list(self.original_data) # Reset to original
                else:
                    print(f"Change View Mode: Fetching activity for {len(all_igns)} IGNs between {start_date} and {end_date}")
                    ranged_activity_data = await fetch_activity_data(guild, all_igns, start_date, end_date)
                    print(f"Change View Mode: Fetched {len(ranged_activity_data)} activity results.")

                    # Update self.current_data with the new activity counts/dates
                    temp_data = []
                    for item in self.original_data:
                        ign_lower = item.get('ign', '').lower()
                        activity_info = ranged_activity_data.get(ign_lower, {'count': 0, 'last_seen': None})
                        # Create a new dict to avoid modifying original_data
                        updated_item = item.copy()
                        updated_item['activity_count'] = activity_info['count']
                        updated_item['last_seen'] = activity_info['last_seen']
                        temp_data.append(updated_item)
                    self.current_data = temp_data
                    print(f"Change View Mode: Updated current_data with ranged activity.")

            elif new_mode == VIEW_MODE_ACTIVITY_ALL:
                # Reset to the all-time activity data stored in original_data
                self.current_data = list(self.original_data) # Make a fresh copy
                print("Change View Mode: Reset to All-Time activity view.")
            else: # VIEW_MODE_DISCORD
                # Reset to original data, activity counts are irrelevant here but keep structure
                self.current_data = list(self.original_data)
                print("Change View Mode: Reset to Discord view.")


            # --- Finalize Update ---
            # Set appropriate sort mode for the new view
            if new_mode == VIEW_MODE_DISCORD:
                 self.sort_mode = SORT_MODE_IGN # Default sort for discord view
            else: # All activity views default to sorting by activity
                 self.sort_mode = SORT_MODE_ACTIVITY

            self.sort_data() # Sort the newly updated data

        except Exception as e:
            # Handle errors during data fetch/processing
            await log_error(guild, f"Error changing view mode to {new_mode}", error=e, interaction=interaction)
            # Reset to a safe state (e.g., Discord view) and notify user
            self.view_mode = VIEW_MODE_DISCORD
            self.current_data = list(self.original_data)
            self.sort_mode = SORT_MODE_IGN
            self.sort_data()
            self.is_fetching_activity = False # Release lock on error

            # --- EDIT BLOCK IN ERROR CASE ---
            # Update UI state (buttons etc.) before creating final embed
            self.update_buttons_and_ui()
            # Create the embed reflecting the error/reset state
            embed = self.create_page_embed()
            # Edit the original message directly
            if self.message:
                 try:
                      await self.message.edit(embed=embed, view=self)
                 except (discord.NotFound, discord.HTTPException) as edit_err:
                      await log_error(guild, "Failed to edit message in view change error handler", error=edit_err)
            # --- END EDIT BLOCK ---

            # Send a follow-up error message
            try:
                # Use edit_original_response if the initial response was just a deferral,
                # otherwise use followup. Since we already sent an edit_message, use followup.
                await interaction.followup.send("❌ An error occurred while fetching data for the selected view.", ephemeral=True)
            except Exception: pass # Ignore if followup fails
            return # Stop further processing

        finally:
            # --- Release Loading State ---
            self.is_fetching_activity = False

            # --- START MODIFIED BLOCK ---
            # Edit message one last time to remove loading state and show final data
            # Update the view's UI state (buttons, select default etc.) BEFORE creating embed
            self.update_buttons_and_ui()
            # Create the final embed reflecting the loaded data and correct state
            final_embed = self.create_page_embed()
            # Edit the MESSAGE OBJECT directly, not the interaction response again
            if self.message:
                try:
                    await self.message.edit(embed=final_embed, view=self)
                except discord.NotFound:
                    print(f"Paginator edit fail: Message {self.message.id} not found in finally block.")
                    self.stop() # Stop view if message gone
                except discord.HTTPException as e:
                    # Log HTTP errors during the final edit
                    await log_error(guild, "Paginator final edit fail (HTTP)", error=e, interaction=interaction)
                except Exception as e:
                     # Log any other errors during the final edit
                     await log_error(guild, "Paginator final edit fail (General)", error=e, interaction=interaction)
            else:
                 print("Warning: self.message object was None in change_view_mode finally block. Cannot update view.")
            # --- END MODIFIED BLOCK ---


    # --- on_timeout (Disable lock) ---
    async def on_timeout(self):
        self.is_fetching_activity = False # Ensure lock is released on timeout
        if self.message:
            try:
                for item in self.children:
                    if hasattr(item, 'disabled'):
                         item.disabled = True
                await self.message.edit(view=self)
                print(f"Paginator timeout: Disabled components on message {self.message.id}")
            except discord.NotFound: print(f"Paginator timeout edit fail: Message {self.message.id} not found.")
            except discord.HTTPException as e:
                 if e.status != 404: await log_error(self.message.guild, f"Paginator timeout edit HTTP fail", error=e)
            except Exception as e:
                 await log_error(self.message.guild, f"Paginator timeout edit general fail", error=e)
        self.stop()

# --- REVISED fetch_hc_member_data ---
async def fetch_hc_member_data(guild: discord.Guild) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fetches HC members from Discord and Supabase, including all-time activity counts.
    Returns a list of dicts: [{'member': discord.Member | None, 'ign': str, 'activity_count': int, 'last_seen': date | None}]
    and the total count.
    Data is sorted by Discord name (if available), then IGN (case-insensitive).
    """
    print(f"Fetch HC Data ({guild.name}): Starting fetch...")
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"HC Role {ADD_ROLE_ID_HC} not found during fetch.")
        return [], 0

    # 1. Fetch ALL entries from Supabase hc_members table
    all_db_members: Dict[str, Dict] = {} # discord_id -> {'ign': ign, 'processed': False}
    ign_only_members: Dict[str, Dict] = {} # ign_lower -> {'ign_original': ign, 'processed': False}
    all_igns_in_db: List[str] = [] # List of all original-case IGNs for activity fetching

    try:
        if not supabase: raise ConnectionError("Supabase client unavailable.")
        print(f"Fetch HC Data ({guild.name}): Fetching all from Supabase hc_members table...")
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members").select("discord_id, ingame_name").execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            for entry in resp.data:
                ign = entry.get("ingame_name")
                if not ign: continue # Skip entries without an IGN
                all_igns_in_db.append(ign) # Add original case IGN
                d_id = entry.get("discord_id")
                if d_id:
                    all_db_members[str(d_id)] = {"ign": ign, "processed": False}
                else:
                    ign_only_members[ign.lower()] = {"ign_original": ign, "processed": False}
            print(f"Fetch HC Data ({guild.name}): Found {len(all_db_members)} DB entries with Discord ID, {len(ign_only_members)} without.")
        else:
            print(f"Fetch HC Data ({guild.name}): No data returned from Supabase hc_members.")

    except (ConnectionError, APIError, Exception) as e:
        await log_error(guild, "Failed to fetch all data from Supabase hc_members", error=e)
        return [], 0 # Return empty on critical DB failure

    # 2. Fetch ALL activity data for the IGNs found
    print(f"Fetch HC Data ({guild.name}): Fetching all-time activity for {len(all_igns_in_db)} IGNs...")
    # Fetch activity counts using the helper function (pass original case IGNs)
    # The helper will handle lowercase matching internally for the query
    activity_counts = await fetch_activity_data(guild, all_igns_in_db) # Fetches count and last_seen
    print(f"Fetch HC Data ({guild.name}): Fetched activity data for {len(activity_counts)} IGNs.")

    # 3. Get Discord members with the HC role
    discord_hc_members: List[discord.Member] = []
    try:
        # Ensure guild is chunked if needed
        if not guild.chunked and guild.member_count is not None and guild.member_count > 1000:
             try:
                 print(f"Fetch HC Data ({guild.name}): Chunking guild..."); await guild.chunk(cache=True)
             except Exception as chunk_e: print(f"WARN: Chunking failed: {chunk_e}")

        discord_hc_members = [m for m in guild.members if hc_role in m.roles and not m.bot]
        print(f"Fetch HC Data ({guild.name}): Found {len(discord_hc_members)} Discord members with HC role.")
    except Exception as e:
        await log_error(guild, "Guild chunking/member fetch failed", error=e)
        # Continue, Supabase entries might still exist

    # 4. Correlate and Build Final Data Structure
    final_data: List[Dict[str, Any]] = []

    # Process Discord members with HC role
    for member in discord_hc_members:
        member_id_str = str(member.id)
        db_entry = all_db_members.get(member_id_str)
        ign = "Unknown"
        activity = {'count': 0, 'last_seen': None} # Default activity

        if db_entry:
            ign = db_entry["ign"]
            db_entry["processed"] = True
            # Get activity for this member's IGN (use lowercase for lookup)
            activity = activity_counts.get(ign.lower(), {'count': 0, 'last_seen': None})
        else:
            # Member has role but no DB entry? Log it.
            await log_info(guild, f"Fetch HC Data Warning: Discord member {member.mention} (`{member.id}`) has HC role but no matching DB entry found.")

        final_data.append({
            "member": member,
            "ign": ign,
            "activity_count": activity['count'],
            "last_seen": activity['last_seen'] # Store the date object or None
        })

    # Process remaining DB entries (Discord member lost role/left or IGN-only)
    # Add Discord-linked entries first
    for d_id, entry_data in all_db_members.items():
        if not entry_data["processed"]:
            ign = entry_data["ign"]
            activity = activity_counts.get(ign.lower(), {'count': 0, 'last_seen': None})
            final_data.append({
                "member": None,
                "ign": ign,
                "activity_count": activity['count'],
                "last_seen": activity['last_seen']
            })

    # Add IGN-only entries
    for ign_lower, entry_data in ign_only_members.items():
         # No need to check 'processed' here as they weren't handled by Discord member loop
         ign = entry_data["ign_original"]
         activity = activity_counts.get(ign_lower, {'count': 0, 'last_seen': None})
         final_data.append({
             "member": None,
             "ign": ign,
             "activity_count": activity['count'],
             "last_seen": activity['last_seen']
         })


    # 5. Sort the final list (Default: Discord name if available, then IGN case-insensitive)
    final_data.sort(key=lambda item: (
        item['member'].name.lower() if item.get('member') else 'zzz', # Sort None members last initially
        item['member'].discriminator if item.get('member') else 'zzz',
        item['ign'].lower()
    ))

    total_members = len(final_data)
    print(f"Fetch HC Data ({guild.name}): Finished. Total members for list: {total_members}.")
    return final_data, total_members

# Update generate_hc_list_embeds to use the new data format and add activity column

def generate_hc_list_embeds(data: List[Dict[str, Any]], total: int) -> List[discord.Embed]:
    """ Generates static list embeds (Discord Name, IGN, All-Time Activity)."""

    # --- Define Column Widths (Mobile Optimized) ---
    IDX_WIDTH = 3
    NAME_WIDTH = 15 # Keep reasonable width for names
    IGN_WIDTH = 15  # Keep reasonable width for IGNs
    ACT_WIDTH = 5   # Width for "Act: X"
    TOTAL_WIDTH = IDX_WIDTH + NAME_WIDTH + IGN_WIDTH + ACT_WIDTH

    if not data:
        embed = discord.Embed(
            title=HC_LIST_EMBED_TITLE,
            description="```\nNo HC members found.\n```",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Page 1/1 | Total: 0")
        embed.timestamp = discord.utils.utcnow()
        return [embed]

    embeds = []
    pages = math.ceil(len(data) / MEMBERS_PER_PAGE)

    # --- Create Header and Separator (once) ---
    header = (
        f"{'#':<{IDX_WIDTH}}"
        f"{'Discord':<{NAME_WIDTH}}"
        f"{'In-Game':<{IGN_WIDTH}}"
        f"{'Act':<{ACT_WIDTH}}" # New Activity column header
    )
    separator = "-" * TOTAL_WIDTH

    for page in range(pages):
        start = page * MEMBERS_PER_PAGE
        page_data = data[start : start + MEMBERS_PER_PAGE]

        desc_lines = [f"```", header, separator]
        idx = start + 1
        for item_dict in page_data: # Iterate through the list of dictionaries
            member = item_dict.get('member')
            ign = item_dict.get('ign', 'Unknown')
            activity_count = item_dict.get('activity_count', 0) # Get activity count

            # Prepare display strings
            if member:
                user_display = f"{member.name}#{member.discriminator}" if member.discriminator != '0' else member.name
            else:
                user_display = "[No Discord]"

            ign_display = ign
            activity_display = str(activity_count) # Display the count

            # Truncate aggressively
            if len(user_display) > NAME_WIDTH: user_display = user_display[:NAME_WIDTH-1] + "…"
            if len(ign_display) > IGN_WIDTH: ign_display = ign_display[:IGN_WIDTH-1] + "…"
            if len(activity_display) > ACT_WIDTH: activity_display = activity_display[:ACT_WIDTH-1] + "…" # Truncate activity if needed

            # Format the line
            line = (
                f"{str(idx)+'.':<{IDX_WIDTH}}"
                f"{user_display:<{NAME_WIDTH}}"
                f"{ign_display:<{IGN_WIDTH}}"
                f"{activity_display:<{ACT_WIDTH}}" # Add activity column
            )
            desc_lines.append(line)
            idx += 1

        desc_lines.append("```") # Close code block
        full_desc = "\n".join(desc_lines)

        # Description limit check (same as before)
        if len(full_desc) > 4096:
            print(f"Warning: Embed description length ({len(full_desc)}) exceeded 4096 chars on page {page+1}. Truncating.")
            full_desc = full_desc[:4093] + "..."

        # --- Create Embed for the page ---
        e = discord.Embed(
            title=HC_LIST_EMBED_TITLE,
            description=full_desc,
            color=NERDY_YELLOW
        )
        e.set_footer(text=f"Page {page+1}/{pages} | Total: {total}")
        e.timestamp = discord.utils.utcnow()
        embeds.append(e)

    return embeds

async def _fetch_existing_list_messages(channel: discord.TextChannel, bot_user_id: int) -> List[discord.Message]:
    """Fetches existing messages from the bot in the channel with the correct title."""
    existing = []
    try:
        # Fetch a reasonable number of recent messages based on expected max pages + buffer
        fetch_limit = max(MEMBERS_PER_PAGE // 5, 15) + 10 # Heuristic limit
        print(f"Static List: Fetching up to {fetch_limit} messages from {channel.mention} for history.")
        async for msg in channel.history(limit=fetch_limit):
             # Ensure message is from the bot and has the specific embed title
             if msg.author and msg.author.id == bot_user_id and msg.embeds:
                  # Check embed structure carefully before accessing attributes
                  if len(msg.embeds) > 0 and msg.embeds[0].title == HC_LIST_EMBED_TITLE:
                       existing.append(msg)
    except discord.Forbidden:
        # Let the caller handle logging the Forbidden error
        print(f"Static List: Forbidden error fetching history in {channel.mention}.")
        raise
    except Exception as e:
        # Log other history fetch errors
        print(f"Static List: Error fetching history in {channel.mention}: {e}") # Simple console log
        raise # Re-raise to be handled by caller
    # Sort existing messages chronologically (oldest first) for consistent editing
    existing.sort(key=lambda m: m.created_at)
    print(f"Static List: Found {len(existing)} relevant existing messages.")
    return existing

async def _update_or_send_list_pages(channel: discord.TextChannel, existing_messages: List[discord.Message], new_embeds: List[discord.Embed], guild_for_log: discord.Guild):
    """Edits existing messages or sends new ones for the list pages, returning error counts."""
    num_new = len(new_embeds)
    num_exist = len(existing_messages)
    tasks = []
    edit_errors = 0
    send_errors = 0
    # Use a slightly longer delay for edits/sends to be safer with rate limits
    delay = 1.5

    for i in range(num_new):
        await asyncio.sleep(delay) # Apply delay before each Discord API action
        if i < num_exist:
            action_desc = f"Editing message {existing_messages[i].id} (Page {i+1})"
            print(f"  {action_desc}")
            tasks.append(existing_messages[i].edit(embed=new_embeds[i]))
        else:
            action_desc = f"Sending new message (Page {i+1})"
            print(f"  {action_desc}")
            tasks.append(channel.send(embed=new_embeds[i]))

    # Execute edits/sends concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and log errors
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            action = "Edit" if i < num_exist else "Send"
            msg_id = existing_messages[i].id if i < num_exist and i < len(existing_messages) else "New"
            error_log_msg = f"Static list {action} failed for Page {i+1} (MsgID: {msg_id})"

            if action == "Edit": edit_errors += 1
            else: send_errors += 1

            # Log the error using the bot's standard logging
            await log_error(guild_for_log, error_log_msg, error=res)

    return edit_errors, send_errors # Return error counts

async def _delete_surplus_list_pages(channel: discord.TextChannel, messages_to_delete: List[discord.Message], guild_for_log: discord.Guild):
    """Deletes surplus list messages, attempting bulk delete first, returning error count."""
    delete_errors = 0
    if not messages_to_delete:
        return delete_errors

    num_to_delete = len(messages_to_delete)
    print(f"Static List: Attempting to delete {num_to_delete} surplus message(s).")
    # Use a slightly longer delay for delete operations as well
    delay = 1.5
    # Ensure bot member object is valid before checking permissions
    bot_member = channel.guild.me
    if not bot_member:
        print("Static List Error: Cannot get bot member to check permissions for deletion.")
        # Indicate potential failure without ability to check/perform delete
        return num_to_delete # Assume all deletions will fail if bot object isn't found

    perms = channel.permissions_for(bot_member)
    can_bulk_delete = perms.manage_messages and num_to_delete > 1

    if can_bulk_delete:
        try:
            # Check if messages are too old for bulk delete (older than 14 days)
            fourteen_days_ago = discord.utils.utcnow() - datetime.timedelta(days=14)
            valid_for_bulk = [m for m in messages_to_delete if m.created_at > fourteen_days_ago]
            invalid_for_bulk = [m for m in messages_to_delete if m not in valid_for_bulk]

            if valid_for_bulk:
                 await asyncio.sleep(delay) # Delay before bulk action
                 await channel.delete_messages(valid_for_bulk)
                 print(f"  Bulk deleted {len(valid_for_bulk)} recent surplus messages.")
                 messages_to_delete = invalid_for_bulk # Update list to only contain old messages
            else:
                 print("  Skipping bulk delete: All surplus messages are too old.")
                 can_bulk_delete = False # Proceed to individual deletion for old messages

        except discord.HTTPException as e:
            # Handle potential 400 Bad Request if mix of old/new messages caused issues
            print(f"  Bulk delete failed (HTTP {e.status}): {e.text}. Falling back to individual deletion.")
            # Fallback required, keep original messages_to_delete list
            messages_to_delete = messages_to_delete # Ensure we process all if bulk fails
            can_bulk_delete = False # Force fallback
        except discord.Forbidden:
            print(f"  Bulk delete failed: Forbidden. Falling back.")
            await log_error(guild_for_log, "Static list bulk delete failed (Forbidden)")
            can_bulk_delete = False
        except Exception as e:
            print(f"  Bulk delete failed unexpectedly: {e}. Falling back.")
            await log_error(guild_for_log, "Static list bulk delete failed (Unknown)", error=e)
            can_bulk_delete = False

    # Fallback to individual deletion if bulk failed, wasn't possible, or messages were old
    if messages_to_delete: # Check if there are still messages needing deletion
         print(f"  Attempting individual deletion for {len(messages_to_delete)} remaining/old messages.")
         for msg_del in messages_to_delete:
            await asyncio.sleep(delay) # Delay each individual delete
            try:
                await msg_del.delete()
                print(f"  Individually deleted surplus message {msg_del.id}")
            except discord.NotFound:
                print(f"  Skipped deleting message {msg_del.id} (already gone).")
            except discord.Forbidden:
                delete_errors += 1
                await log_error(guild_for_log, f"Failed to delete surplus message {msg_del.id} (Forbidden)")
                # Stop trying if forbidden, likely a persistent issue
                print("  Stopping further individual deletes due to Forbidden error.")
                break # Exit the loop for individual deletes
            except Exception as e:
                delete_errors += 1
                await log_error(guild_for_log, f"Failed to delete surplus message {msg_del.id}", error=e)

    return delete_errors

# --- REFACTORED update_hc_member_list ---
async def update_hc_member_list(guild: discord.Guild):
    """ Updates static HC list (username#tag ➔ IGN format using helper functions)."""
    list_channel_id = HC_MEMBER_LIST_CHANNEL_ID
    chan = guild.get_channel(list_channel_id)
    if not isinstance(chan, discord.TextChannel):
        await log_error(guild, f"Static list channel {list_channel_id} invalid or not found.")
        return

    # Ensure bot object is ready
    if not bot or not bot.user:
        await log_error(guild, "Cannot update static list: Bot user object not available.", guild=guild)
        return
    bot_user_id = bot.user.id

    # Simplified Permission Check (as per user context - assumes bot has high roles)
    # Basic check for sending capability is still wise.
    bot_mem = guild.me
    if not bot_mem:
        try:
            bot_mem = await guild.fetch_member(bot_user_id) # Attempt fetch if not cached
        except (discord.NotFound, discord.HTTPException):
             await log_error(guild, f"Cannot update static list: Failed to get bot member object in guild {guild.name}.")
             return
    if not bot_mem: # Check again after fetch attempt
         await log_error(guild, f"Cannot update static list: Bot member object unavailable in {guild.name}.")
         return

    perms = chan.permissions_for(bot_mem)
    if not perms.send_messages or not perms.embed_links:
         await log_error(guild, f"Bot missing Send Messages or Embed Links in {chan.mention} for static list.")
         # Consider returning here as these are fundamental
         return
    # Log warnings if other perms needed for efficiency are missing
    if not perms.read_message_history:
         await log_info(guild, f"Warning: Bot missing Read Message History in {chan.mention}. List update might be inefficient.")
    if not perms.manage_messages:
         await log_info(guild, f"Warning: Bot missing Manage Messages in {chan.mention}. Surplus message cleanup may fail or be slow.")


    try:
        await log_info(guild, f"Starting static list update in {chan.mention}...")

        # 1. Fetch member data and generate new embeds
        data, total = await fetch_hc_member_data(guild)
        new_embeds = generate_hc_list_embeds(data, total)
        num_new = len(new_embeds)

        # 2. Fetch existing messages using helper
        try:
             existing_messages = await _fetch_existing_list_messages(chan, bot_user_id)
             num_exist = len(existing_messages)
             print(f"Static List Update ({guild.name}): Found {num_exist} existing bot messages, Need {num_new} pages.")
        except discord.Forbidden:
             # Specific logging for forbidden on history read
             await log_error(guild, f"Static list update failed: Bot lacks Read Message History permission in {chan.mention}.")
             return # Cannot proceed reliably without history
        except Exception as e:
             # General error during history fetch
             await log_error(guild, "Error fetching message history for static list update", error=e)
             return # Stop if history fetch fails critically

        # 3. Update/Send pages using helper
        # Pass guild object for logging context within the helper
        edit_errors, send_errors = await _update_or_send_list_pages(chan, existing_messages, new_embeds, guild)

        # 4. Delete surplus pages using helper
        messages_to_delete = existing_messages[num_new:] if num_exist > num_new else []
        # Pass guild object for logging context within the helper
        delete_errors = await _delete_surplus_list_pages(chan, messages_to_delete, guild)

        # 5. Log final status
        total_errors = edit_errors + send_errors + delete_errors
        status_msg = f"Static list update complete ({num_new} pages displayed)."
        if total_errors > 0:
            status_msg += f" Encountered {total_errors} error(s) during update (Edit:{edit_errors}, Send:{send_errors}, Delete:{delete_errors}). Check error logs."
        else:
             status_msg += " No errors encountered."

        # Log as error if any step had issues, otherwise info
        log_level = log_error if total_errors > 0 else log_info
        await log_level(guild, status_msg)

        # 5. Log final status (Moved up slightly to log list update completion first)
        EXPLANATORY_FOOTER_TEXT = "This list is automatically updated." # Keep for identification, shortened footer
        BOT_CREATOR_ID = SELF_PROTECTED_ID # Use the constant

        # --- NEW Concise Explanatory Embed ---
        explanatory_embed = discord.Embed(
            description=(
                f"# ✅ \[HC1] Guild Member List\n"
                f"*Official list of **\[HC1]** Florr.io guild members.*\n\n"
                f"**Format:** `Discord ➔ IGN (Activity)`\n"
                f"*Activity is a count of logged active days.*\n\n"
                f"**Want more detail?**\n"
                f"• Use {get_cmd_mention('hcmembers')} for **search, filters, and detailed activity dates**.\n"
                f"• Mark yourself active today with {get_cmd_mention('activatemyself')}! 🤓\n\n"
                f"--- \n"
                f"*Bot built by <@{BOT_CREATOR_ID}>.*"
            ),
            color=NERDY_YELLOW
        )
        explanatory_embed.set_footer(text=EXPLANATORY_FOOTER_TEXT)
        # Removed timestamp for a cleaner look, optional
        # explanatory_embed.timestamp = discord.utils.utcnow()

        # --- Keep the rest of the logic for fetching/editing/sending the message ---
        last_message: Optional[discord.Message] = None
        try:
            # Fetch the very last message in the channel
            async for message in chan.history(limit=1, oldest_first=False):
                 last_message = message
                 break # We only need the last one

            if last_message and last_message.author.id == bot_user_id and last_message.embeds:
                 # Check if the last message is already our explanatory embed
                 if last_message.embeds[0].footer and last_message.embeds[0].footer.text == EXPLANATORY_FOOTER_TEXT:
                      # It exists, just edit it to ensure content is up-to-date
                      print(f"Static List: Found existing explanatory message ({last_message.id}), editing.")
                      await last_message.edit(embed=explanatory_embed)
                 else:
                      # It's a bot message, but not the right one
                      print(f"Static List: Last bot message ({last_message.id}) is not the explanatory message. Sending new one.")
                      await chan.send(embed=explanatory_embed)
            else:
                 # No message, or last message not from bot, or no embeds. Send fresh.
                 print(f"Static List: No existing explanatory message found at the end. Sending new one.")
                 await chan.send(embed=explanatory_embed)

        except discord.Forbidden:
             await log_error(guild, f"Static list explanatory message failed: Bot lacks Send/Read History/Embed Links permissions in {chan.mention}.")
        except discord.HTTPException as http_err:
             await log_error(guild, f"Static list explanatory message failed: HTTP Error", error=http_err)
        except Exception as e_explain:
             await log_error(guild, f"Static list explanatory message failed: Unexpected error", error=e_explain)

    except Exception as e:
        # Catch-all for unexpected errors in the main orchestration logic
        await log_error(guild, "Unhandled error during the main static list update process", error=e)

# --- Discord Events ---
@bot.event
async def on_ready():
    print("--- on_ready event started ---")
    global BOT_ID, command_ids
    if bot.user:
        BOT_ID = bot.user.id
        print(f"Logged in as {bot.user} (ID: {BOT_ID})")
        print(f"Discord.py v{discord.__version__}")
    else:
        print("CRITICAL ERROR: Bot user object not found on ready.")
        return

    print("Syncing application commands...")
    synced_commands = []
    try:
        # Sync globally. Consider syncing per-guild if commands are guild-specific
        synced_commands = await tree.sync() # Global sync
        print(f"Synced {len(synced_commands)} application commands globally.")

        command_ids.clear() # Clear old IDs before populating

        # --- CORRECTED LOOP ---
        # Iterate through the AppCommand objects returned by tree.sync()
        # These objects directly have .name and .id attributes.
        for cmd in synced_commands:
            # Check if it's a command object with name and id (should generally be true)
            if hasattr(cmd, 'name') and hasattr(cmd, 'id'):
                command_ids[cmd.name] = cmd.id
                print(f"  Stored ID for /{cmd.name}: {cmd.id}")
            else:
                # Log if we encounter something unexpected in the synced list
                print(f"  Skipped storing ID for an item during sync (type: {type(cmd)}, name: {getattr(cmd, 'name', 'N/A')})")
        # --- END CORRECTED LOOP ---

        # Check if the dictionary is populated after the loop
        if command_ids:
            print(f"Stored command IDs: {command_ids}")
        else:
             # This warning should now only appear if sync returned nothing or encountered issues
             print("Warning: command_ids dictionary is empty after sync. Help command may not show clickable links.")

    except discord.HTTPException as e:
        print(f"Command Sync failed (HTTPException): {e}")
        first_guild = bot.guilds[0] if bot.guilds else None
        if first_guild:
            # Avoid await in except block if it causes issues, log directly
            print(f"Error logged for Guild {first_guild.id}: Command Sync failed (HTTPException).")
            # Consider a non-async logging mechanism here if needed
            # await log_error(first_guild, "Application Command Sync failed on startup (HTTPException).", error=e)
    except Exception as e:
        print(f"Command Sync failed (Unexpected Error): {e}\n{traceback.format_exc()}")
        first_guild = bot.guilds[0] if bot.guilds else None
        if first_guild:
            print(f"Error logged for Guild {first_guild.id}: Command Sync failed (Exception).")
            # await log_error(first_guild, "Application Command Sync failed on startup (Exception).", error=e)

    # Ensure the bot has guilds before proceeding with guild-specific setup
    if not bot.guilds:
        print("Bot is not currently in any guilds. Skipping guild setup.")
        print("--- on_ready event finished (no guilds) ---")
        return

    print(f"Performing initial setup for {len(bot.guilds)} guild(s)...")
    # Process guilds one by one to avoid potential rate limits on setup tasks
    guilds_to_process = list(bot.guilds) # Create a copy
    for guild in guilds_to_process:
        print(f"  Processing guild: {guild.name} (ID: {guild.id})")
        try:
            # Ensure member cache is populated for this guild if necessary
            if not guild.chunked and guild.member_count is not None and guild.member_count > 1000: # Optional: Only chunk larger guilds
                 print(f"    Attempting to chunk guild {guild.name} (Members: {guild.member_count})...")
                 try:
                     await guild.chunk(cache=True)
                     print(f"    Successfully chunked guild {guild.name}.")
                 except Exception as chunk_e:
                     print(f"    Warning: Guild chunking failed for {guild.name}: {chunk_e}")
                     # Log this error using your logger if needed
                     # await log_error(guild, "Guild chunking failed during on_ready setup", error=chunk_e)


            # Log bot readiness per guild
            await log_info(guild, f"Bot ready and online. Synced {len(synced_commands)} commands.")
            # Update the static list on startup for each relevant guild
            await update_hc_member_list(guild)
            # Add a small delay between processing guilds if necessary
            await asyncio.sleep(1)
        except Exception as e:
            # Log errors specific to the guild setup
            await log_error(guild, f"Error during on_ready setup for this guild", error=e)

    print("--- on_ready event finished ---")


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Ignore updates for bots or if roles haven't changed
    if after.bot or before.roles == after.roles:
        return

    guild = after.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    # If HC role isn't configured or found, no need to proceed
    if not hc_role: return

    had_hc_role = hc_role in before.roles
    has_hc_role = hc_role in after.roles

    # Trigger update only if the HC role status changed
    if had_hc_role != has_hc_role:
        action = "added to" if has_hc_role else "removed from"
        await log_info(guild, f"HC role (`{hc_role.name}`) {action} user {after.mention} (`{after.id}`). Triggering static list update.")
        try:
            # Schedule the update, don't block the event handler for too long
            asyncio.create_task(update_hc_member_list(guild))
        except Exception as e:
             # Log the error if task creation or the update itself fails immediately
             await log_error(guild, f"Failed to trigger static list update after role change for {after.mention}", error=e)


# --- App Command Error Handling ---
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    guild = interaction.guild # Can be None if in DMs
    user_msg = "❌ An unexpected error occurred. Please try again later or contact an admin." # Default user message
    log_desc = "Unhandled App Command Error" # Default log description
    error_to_log: Optional[Exception] = error # Default error to log

    # Specific error handling
    if isinstance(error, app_commands.CommandNotFound):
        # This usually shouldn't happen with synced commands, but log just in case
        print(f"CommandNotFound error received for interaction: {interaction.data.get('name', 'N/A')}")
        # Don't notify the user, Discord handles this
        return
    elif isinstance(error, app_commands.MissingPermissions):
        perms = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
        user_msg = f"❌ You lack the required permissions to use this command: {perms}"
        log_desc = f"User Missing Permissions: {perms}"
        error_to_log = None # Don't log traceback for user permission issues
    elif isinstance(error, app_commands.BotMissingPermissions):
        perms = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
        user_msg = f"❌ I lack the required permissions to perform this action: {perms}. Please contact an admin."
        log_desc = f"Bot Missing Permissions: {perms}"
        error_to_log = None # Don't log traceback for bot permission issues (config error)
    elif isinstance(error, app_commands.CheckFailure):
        # General check failure (could be custom checks or decorators like has_permissions)
        user_msg = "❌ You do not meet the requirements to use this command in this context."
        # Improve logging if the check has a specific message
        log_desc = f"Check Failure ({type(error).__name__})"
        if hasattr(error, 'message') and error.message:
            log_desc += f": {error.message}"
        error_to_log = None # Usually no need for traceback
    elif isinstance(error, app_commands.CommandInvokeError):
        # Error occurred inside the command's callback
        original_error = error.original
        error_to_log = original_error # Log the original error
        user_msg = f"❌ An error occurred while running the command. Please report this if it persists."
        # Add original error type to user message for slightly more info if desired
        # user_msg += f" (`{type(original_error).__name__}`)"
        log_desc = f"Command Invoke Error in `/{interaction.command.name if interaction.command else 'Unknown'}`"
        # Print full traceback to console for immediate debugging
        print(f"CommandInvokeError in command '{interaction.command.name if interaction.command else 'Unknown'}':")
        traceback.print_exception(type(original_error), original_error, original_error.__traceback__)
    elif isinstance(error, app_commands.TransformerError):
        # Error converting an argument (e.g., invalid user mention, bad number format)
        user_msg = f"❌ Invalid input provided: {error}"
        log_desc = f"Transformer Error: {error}"
        error_to_log = error # Log the transformer error details
    elif isinstance(error, app_commands.CommandOnCooldown):
        user_msg = f"⏳ This command is on cooldown. Please try again in {error.retry_after:.1f} seconds."
        log_desc = f"Command Cooldown Hit ({error.retry_after:.1f}s)"
        error_to_log = None # No traceback needed
    elif isinstance(error, app_commands.NoPrivateMessage):
         user_msg = "❌ This command cannot be used in Direct Messages."
         log_desc = "Command used in DM"
         error_to_log = None
    # Add more specific checks if needed (e.g., app_commands.ArgumentParsingError)
    else:
        # Catch-all for other discord.py app command errors
        log_desc = f"Unknown App Command Error Type: `{type(error).__name__}`"

    # Log the error to the designated channel
    # Pass the original error if it's more informative (like from CommandInvokeError)
    await log_error(guild, log_desc, error=error_to_log, interaction=interaction)

    # Respond to the user ephemerally
    try:
        if interaction.response.is_done():
            # If already responded (e.g., deferred), send a followup
            await interaction.followup.send(user_msg, ephemeral=False)
        else:
            # Otherwise, send the initial response
            await interaction.response.send_message(user_msg, ephemeral=False)
    except discord.NotFound:
        # Interaction might have expired between error and response
        print(f"Error Handler: Interaction {interaction.id} already expired or deleted.")
    except discord.InteractionResponded:
         # Should ideally be caught by is_done(), but handle defensively
         try:
             await interaction.followup.send(user_msg, ephemeral=False)
         except Exception as e_followup:
             print(f"Error Handler: Failed to send followup after InteractionResponded state: {e_followup}")
    except Exception as e_send:
        # Catch any other exceptions during the response sending
        print(f"Error Handler: Failed to send error message to user: {e_send}")


# --- Modals ---
def create_embed(description: str, color: discord.Color = NERDY_YELLOW, title: Optional[str] = None) -> discord.Embed:
     """Creates a simple Discord embed."""
     embed = discord.Embed(title=title, description=description, color=color)
     # Consider adding a timestamp by default
     # embed.timestamp = discord.utils.utcnow()
     return embed

# --- Helper Function ---
def get_cmd_mention(name: str) -> str:
    """Helper to create a clickable command mention string."""
    cmd_id = command_ids.get(name)
    if cmd_id:
        return f"</{name}:{cmd_id}>" # Correct clickable format
    else:
        # Fallback if the ID wasn't found (e.g., sync issue)
        print(f"Warn: No ID found for cmd '/{name}' in nerdhelp generation.")
        return f"`/{name}`" # Non-clickable fallback

# --- Slash Commands ---

# --- Verify Command ---
@tree.command(name="verify", description="Verify a standard user (adds Verified, removes Unverified).")
@app_commands.describe(user="The user to verify.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=False)
        return

    role_to_remove = guild.get_role(REMOVE_ROLE_ID)
    role_to_add = guild.get_role(ADD_ROLE_ID_VERIFY)

    # Role existence checks
    missing_roles = []
    if REMOVE_ROLE_ID and not role_to_remove: missing_roles.append(f"Unverified Role (ID: {REMOVE_ROLE_ID})")
    if ADD_ROLE_ID_VERIFY and not role_to_add: missing_roles.append(f"Verified Role (ID: {ADD_ROLE_ID_VERIFY})")
    if missing_roles:
        msg = f"❌ Setup Error: Roles not found: {', '.join(missing_roles)}. Please configure the bot."
        await interaction.response.send_message(msg, ephemeral=False)
        await log_error(guild, f"Verify failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return
    # We definitely need the role to add
    if not role_to_add:
         msg = f"❌ Setup Error: Verified Role (ID: {ADD_ROLE_ID_VERIFY}) not configured correctly."
         await interaction.response.send_message(msg, ephemeral=False)
         await log_error(guild, msg, interaction=interaction)
         return

    # Hierarchy checks
    bot_member = guild.me # Get bot's member object
    hierarchy_fail = False
    hierarchy_reason = ""
    # Check if bot can assign the 'Verified' role
    if bot_member.top_role.position <= role_to_add.position:
        hierarchy_fail=True
        hierarchy_reason=f"Cannot assign the '{role_to_add.name}' role."
    # Check if bot can remove the 'Unverified' role (if it exists and is configured)
    elif role_to_remove and bot_member.top_role.position <= role_to_remove.position:
        hierarchy_fail=True
        hierarchy_reason=f"Cannot remove the '{role_to_remove.name}' role."

    if hierarchy_fail:
        msg = f"❌ Hierarchy Error: {hierarchy_reason} My highest role ('{bot_member.top_role.name}') is not high enough."
        await interaction.response.send_message(msg, ephemeral=False)
        await log_error(guild, f"Verify failed: Bot hierarchy issue. Reason: {hierarchy_reason}", interaction=interaction)
        return

    # Defer ephemerally while roles are changed
    await interaction.response.defer(thinking=True, ephemeral=False)

    actions_taken = []
    reason = f"Verified by {interaction.user} (ID: {interaction.user.id})"
    modified = False

    try:
        # Check current roles
        has_verified = role_to_add in user.roles
        # Check if unverified role exists and user has it
        has_unverified = bool(role_to_remove and role_to_remove in user.roles)

        # If already correctly verified, inform user
        if has_verified and not has_unverified:
            await interaction.followup.send(f"ℹ️ {user.mention} is already verified (has '{role_to_add.name}' and not '{role_to_remove.name if role_to_remove else ''}').", ephemeral=False)
            return

        roles_to_add_list = []
        roles_to_remove_list = []

        # Determine changes needed
        if has_unverified and role_to_remove: # Ensure role_to_remove exists before adding
             roles_to_remove_list.append(role_to_remove)
             actions_taken.append(f"➖ Removed `{role_to_remove.name}`")
             modified = True
        if not has_verified:
             roles_to_add_list.append(role_to_add)
             actions_taken.append(f"➕ Added `{role_to_add.name}`")
             modified = True

        # Apply changes if any are needed
        if modified:
            if roles_to_add_list: await user.add_roles(*roles_to_add_list, reason=reason)
            if roles_to_remove_list: await user.remove_roles(*roles_to_remove_list, reason=reason)

            await log_info(guild, f"`{interaction.user}` verified {user.mention}. Actions: {', '.join(actions_taken)}.")
            await interaction.followup.send(f"✅ Successfully verified {user.mention}.", ephemeral=False)

            # Send public notification (optional, consider configuration)
            public_embed = create_embed(f"✅ **{user.display_name}** has been verified!\n" + "\n".join(actions_taken), discord.Color.green())
            try:
                # Send in the channel where command was used, if it's a text channel
                if isinstance(interaction.channel, discord.TextChannel):
                    await interaction.channel.send(embed=public_embed)
                else:
                     await log_info(guild, f"Skipped public verify notification for {user.mention} (command used in non-text channel).")
            except (discord.Forbidden, discord.HTTPException) as e:
                 await log_error(guild,"Failed to send public verify notification", error=e, interaction=interaction)

        else:
             # This case should ideally be caught earlier, but handle defensively
             await interaction.followup.send("ℹ️ No role changes were needed.", ephemeral=False)

    except discord.Forbidden:
        await log_error(guild, "Verify failed: Bot lacks permissions (Forbidden).", interaction=interaction)
        await interaction.followup.send("❌ Failed: I don't have the necessary permissions to manage roles for this user.", ephemeral=False)
    except discord.HTTPException as e:
        await log_error(guild, "Verify failed: Discord API error.", error=e, interaction=interaction)
        await interaction.followup.send("❌ Failed: A Discord API error occurred. Please try again later.", ephemeral=False)
    except Exception as e:
        await log_error(guild, "Unexpected error during /verify.", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=False)


# --- Unverify Command ---
@tree.command(name="unverify", description="Revert user to Unverified (adds Unverified, removes Verified).")
@app_commands.describe(user="The user to unverify.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def unverify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=False)
        return

    role_to_add = guild.get_role(REMOVE_ROLE_ID) # Role to ADD is 'Unverified'
    role_to_remove = guild.get_role(ADD_ROLE_ID_VERIFY) # Role to REMOVE is 'Verified'

    # Role existence checks
    missing_roles = []
    if REMOVE_ROLE_ID and not role_to_add: missing_roles.append(f"Unverified Role (ID: {REMOVE_ROLE_ID})")
    if ADD_ROLE_ID_VERIFY and not role_to_remove: missing_roles.append(f"Verified Role (ID: {ADD_ROLE_ID_VERIFY})")
    if missing_roles:
        msg = f"❌ Setup Error: Roles not found: {', '.join(missing_roles)}. Please configure the bot."
        await interaction.response.send_message(msg, ephemeral=False)
        await log_error(guild, f"Unverify failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return
    # We definitely need the 'Unverified' role to add it
    if not role_to_add:
         msg = f"❌ Setup Error: Unverified Role (ID: {REMOVE_ROLE_ID}) not configured correctly."
         await interaction.response.send_message(msg, ephemeral=False)
         await log_error(guild, msg, interaction=interaction)
         return

    # Hierarchy checks
    bot_member = guild.me
    hierarchy_fail = False
    hierarchy_reason = ""
    # Check if bot can assign the 'Unverified' role
    if bot_member.top_role.position <= role_to_add.position:
        hierarchy_fail=True
        hierarchy_reason=f"Cannot assign the '{role_to_add.name}' role."
    # Check if bot can remove the 'Verified' role (if it exists and is configured)
    elif role_to_remove and bot_member.top_role.position <= role_to_remove.position:
        hierarchy_fail=True
        hierarchy_reason=f"Cannot remove the '{role_to_remove.name}' role."

    if hierarchy_fail:
         msg = f"❌ Hierarchy Error: {hierarchy_reason} My highest role ('{bot_member.top_role.name}') is not high enough."
         await interaction.response.send_message(msg, ephemeral=False)
         await log_error(guild, f"Unverify failed: Bot hierarchy issue. Reason: {hierarchy_reason}", interaction=interaction)
         return

    # Defer ephemerally
    await interaction.response.defer(thinking=True, ephemeral=False)

    actions_taken = []
    reason = f"Unverified by {interaction.user} (ID: {interaction.user.id})"
    modified = False

    try:
        # Check current roles
        has_unverified = role_to_add in user.roles
        # Check if verified role exists and user has it
        has_verified = bool(role_to_remove and role_to_remove in user.roles)

        # If already correctly unverified, inform user
        if has_unverified and not has_verified:
            await interaction.followup.send(f"ℹ️ {user.mention} is already Unverified (has '{role_to_add.name}' and not '{role_to_remove.name if role_to_remove else ''}').", ephemeral=False)
            return

        roles_to_add_list = []
        roles_to_remove_list = []

        # Determine changes needed
        if has_verified and role_to_remove: # Ensure role_to_remove exists
             roles_to_remove_list.append(role_to_remove)
             actions_taken.append(f"➖ Removed `{role_to_remove.name}`")
             modified = True
        if not has_unverified:
             roles_to_add_list.append(role_to_add)
             actions_taken.append(f"➕ Added `{role_to_add.name}`")
             modified = True

        # Apply changes if any
        if modified:
            if roles_to_add_list: await user.add_roles(*roles_to_add_list, reason=reason)
            if roles_to_remove_list: await user.remove_roles(*roles_to_remove_list, reason=reason)

            await log_info(guild, f"`{interaction.user}` unverified {user.mention}. Actions: {', '.join(actions_taken)}.")
            await interaction.followup.send(f"✅ Successfully unverified {user.mention}.", ephemeral=False)

            # Send public notification (optional)
            public_embed = create_embed(f"↩️ **{user.display_name}** has been unverified.\n" + "\n".join(actions_taken), discord.Color.orange())
            try:
                 if isinstance(interaction.channel, discord.TextChannel):
                     await interaction.channel.send(embed=public_embed)
                 else:
                     await log_info(guild, f"Skipped public unverify notification for {user.mention} (non-text channel).")
            except (discord.Forbidden, discord.HTTPException) as e:
                 await log_error(guild, "Failed to send public unverify notification", error=e, interaction=interaction)

        else:
             await interaction.followup.send("ℹ️ No role changes were needed.", ephemeral=False)

    except discord.Forbidden:
        await log_error(guild, "Unverify failed: Bot lacks permissions (Forbidden).", interaction=interaction)
        await interaction.followup.send("❌ Failed: I don't have the necessary permissions to manage roles for this user.", ephemeral=False)
    except discord.HTTPException as e:
        await log_error(guild, "Unverify failed: Discord API error.", error=e, interaction=interaction)
        await interaction.followup.send("❌ Failed: A Discord API error occurred. Please try again later.", ephemeral=False)
    except Exception as e:
        await log_error(guild, "Unexpected error during /unverify.", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=False)


# --- REFINED HC Verify Command (incorporating ROLE_ID_MAYBE_EXHC removal) ---
@tree.command(name="hcverify", description="Verify user into HC, store IGN, set nickname.")
@app_commands.describe(user="User to HC verify.", ingame_name="User's Florr IGN (will be used as nickname).")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    guild = interaction.guild
    if not await check_supabase_available(interaction):
        # Helper sends ephemeral msg & logs if needed.
        try: # Attempt to clean up deferred message if applicable
            if interaction.response.is_done(): await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        except (discord.NotFound, discord.HTTPException): pass
        return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return
    if not supabase: # Double check after helper, though unlikely needed
        await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=False)
        await log_error(guild, "HCVerify failed: Supabase client unavailable.", interaction=interaction)
        return

    # Defer publicly as this command makes visible changes (roles, nick, list update)
    await interaction.response.defer(thinking=True, ephemeral=False)

    # --- Role Setup ---
    role_unverified = guild.get_role(REMOVE_ROLE_ID)
    role_verified = guild.get_role(ADD_ROLE_ID_VERIFY)
    role_hc = guild.get_role(ADD_ROLE_ID_HC)
    role_maybe_exhc = guild.get_role(ROLE_ID_MAYBE_EXHC) # Fetch the new role
    bot_member = guild.me

    # --- Role Existence Checks ---
    missing_roles = []
    critical_roles_found = True
    if ADD_ROLE_ID_VERIFY and not role_verified:
        missing_roles.append(f"Verified (ID: {ADD_ROLE_ID_VERIFY})")
        critical_roles_found = False
    if ADD_ROLE_ID_HC and not role_hc:
        missing_roles.append(f"HC (ID: {ADD_ROLE_ID_HC})")
        critical_roles_found = False

    # Check optional roles (don't block but log/warn)
    if REMOVE_ROLE_ID and not role_unverified: print(f"HCVerify Warning ({guild.name}): Unverified Role (ID: {REMOVE_ROLE_ID}) not found.")
    if ROLE_ID_MAYBE_EXHC and not role_maybe_exhc: print(f"HCVerify Warning ({guild.name}): Maybe-ExHC Role (ID: {ROLE_ID_MAYBE_EXHC}) not found.")

    if not critical_roles_found:
        msg = f"❌ Setup Error: Missing critical roles: {', '.join(missing_roles)}. Please configure the bot."
        await interaction.followup.send(msg, ephemeral=False) # Use followup since deferred
        await log_error(guild, f"HCVerify failed: Missing critical roles - {', '.join(missing_roles)}", interaction=interaction)
        return

    # --- Prepare for actions ---
    log_summary = []
    result_summary = []
    errors_occurred = False
    db_success = False
    role_changes_succeeded = False
    maybe_exhc_role_removed_flag = False # Flag to track if the specific role was targeted for removal
    nick_success = False
    reason = f"HC Verified by {interaction.user} (ID: {interaction.user.id})"
    can_manage_user_roles = bot_member.top_role.position > user.top_role.position
    can_manage_user_nick = can_manage_user_roles
    original_hc_status = role_hc in user.roles

    # --- Role Management ---
    roles_to_add_final = []
    roles_to_remove_final = []

    # Determine desired state
    desired_adds = []
    desired_removes = []
    if role_verified and not (role_verified in user.roles): desired_adds.append(role_verified) # Check role exists
    if role_hc and not original_hc_status: desired_adds.append(role_hc) # Check role exists
    if role_unverified and (role_unverified in user.roles): desired_removes.append(role_unverified) # Check role exists
    if role_maybe_exhc and (role_maybe_exhc in user.roles): # Check role exists and user has it
        desired_removes.append(role_maybe_exhc)
        # Set flag ONLY if user HAS the role AND bot can POTENTIALLY remove it (hierarchy check later)
        if bot_member.top_role.position > role_maybe_exhc.position:
             maybe_exhc_role_removed_flag = True # Mark that we intend to remove it


    # Check bot hierarchy for each desired change
    for role in desired_adds:
        if bot_member.top_role.position > role.position:
            roles_to_add_final.append(role)
        else:
            errors_occurred=True
            reason_skip=f"Bot hierarchy too low to add role '{role.name}'"
            result_summary.append(f"⚠️ Skipped adding `{role.name}` (Hierarchy).")
            log_summary.append(f"Role add skip: {reason_skip}")
            await log_info(guild, f"HCVerify: {reason_skip} for {user.mention}")
    for role in desired_removes:
        if bot_member.top_role.position > role.position:
            roles_to_remove_final.append(role)
        else:
            # If hierarchy prevents removing maybe_exhc, reset the flag
            if role == role_maybe_exhc: maybe_exhc_role_removed_flag = False

            errors_occurred=True
            reason_skip=f"Bot hierarchy too low to remove role '{role.name}'"
            result_summary.append(f"⚠️ Skipped removing `{role.name}` (Hierarchy).")
            log_summary.append(f"Role remove skip: {reason_skip}")
            await log_info(guild, f"HCVerify: {reason_skip} for {user.mention}")

    # Apply role changes if any are possible and needed
    if roles_to_add_final or roles_to_remove_final:
        try:
            # Perform additions and removals using edit
            current_roles = user.roles
            final_role_set = [r for r in current_roles if r not in roles_to_remove_final] + roles_to_add_final
            # Ensure @everyone is not accidentally included if manage_roles perm is missing (unlikely here)
            final_role_set = [r for r in final_role_set if r.id != guild.default_role.id]

            await user.edit(roles=final_role_set, reason=reason)

            # --- Build Result Summary ---
            added_names_list = [f"`{r.name}`" for r in roles_to_add_final]
            removed_names_list = [f"`{r.name}`" for r in roles_to_remove_final]

            added_names = ', '.join(added_names_list)
            removed_names = ', '.join(removed_names_list)

            if added_names: result_summary.append(f"➕ Roles Added: {added_names}")
            if removed_names: result_summary.append(f"➖ Roles Removed: {removed_names}")

            # Check the flag AFTER successful removal
            if role_maybe_exhc in roles_to_remove_final: # Check if it was ACTUALLY in the list of roles removed
                 if maybe_exhc_role_removed_flag: # Double check the flag which incorporates hierarchy check
                    result_summary.append(f"✅ (Removed `{role_maybe_exhc.name}` - Welcome back!)") # Explicit mention
                    log_summary.append(f"Removed role '{role_maybe_exhc.name}'")
                 else:
                     # This case shouldn't happen if logic is right, but log if it does
                     print(f"HCVerify Logic Warning: Removed {role_maybe_exhc.name} but flag was false.")
            # --- End Result Summary Building ---

            log_summary.append("Role update successful for applicable roles.")
            role_changes_succeeded = True

        except discord.Forbidden:
            errors_occurred=True
            result_summary.append("⚠️ Role Error: Permissions error during update.")
            log_summary.append("Role update failed: Forbidden")
            await log_error(guild, "HCVerify role update failed (Forbidden)", interaction=interaction)
            # Reset flag if role removal failed
            if role_maybe_exhc in roles_to_remove_final: maybe_exhc_role_removed_flag = False
        except discord.HTTPException as e:
            errors_occurred=True
            result_summary.append("⚠️ Role Error: Discord API Error during update.")
            log_summary.append(f"Role update failed: HTTP {e.status}")
            await log_error(guild, "HCVerify role update failed (HTTPException)", error=e, interaction=interaction)
            if role_maybe_exhc in roles_to_remove_final: maybe_exhc_role_removed_flag = False
        except Exception as e:
            errors_occurred=True
            result_summary.append("⚠️ Role Error: Unknown error during update.")
            log_summary.append(f"Role update fail: {type(e).__name__}")
            await log_error(guild, "HCVerify unexpected role error", error=e, interaction=interaction)
            if role_maybe_exhc in roles_to_remove_final: maybe_exhc_role_removed_flag = False
    elif not desired_adds and not desired_removes:
        # Only report this if no hierarchy skips happened for roles
        if not any("Role add skip" in s or "Role remove skip" in s for s in log_summary):
             result_summary.append("ℹ️ Roles already correct.")
             log_summary.append("No role changes needed.")

    # --- Database Update ---
    ign_to_store = ingame_name.strip()
    if not ign_to_store:
        errors_occurred=True
        result_summary.append(f"⚠️ DB Error: In-game name cannot be empty.")
        log_summary.append(f"DB fail: Empty IGN provided.")
        # Don't log error here, handled by user feedback
    else:
        try:
            # Upsert based on discord_id being the unique constraint (or primary key before change)
            # Ensure table schema matches: discord_id should allow unique constraint
            await run_supabase_sync( lambda: supabase.table("hc_members").upsert({
                    "discord_id": str(user.id),
                    "discord_name": f"{user.name}#{user.discriminator}" if user.discriminator != '0' else user.name,
                    "ingame_name": ign_to_store
                }, on_conflict="discord_id" # Assumes discord_id is UNIQUE constraint now
                 # If using the new UUID 'id' primary key and discord_id is just unique,
                 # you might need different logic if you want to update based on discord_id.
                 # An explicit check-then-update/insert might be safer if schema changed significantly.
                 # Current 'upsert on conflict discord_id' assumes discord_id has a UNIQUE constraint.
                 ).execute()
            )
            result_summary.append(f"💾 IGN Stored/Updated: `{discord.utils.escape_markdown(ign_to_store)}`")
            log_summary.append("Supabase upsert OK")
            db_success = True
        except APIError as e:
            # Check for unique constraint on ingame_name if upsert fails weirdly
            if "unique constraint" in str(e.message).lower() and "hc_members_ingame_name_unique" in str(e.message).lower():
                errors_occurred=True
                err_detail=f"IGN Conflict: '{ign_to_store}' might be linked to another Discord account or exist as an IGN-only entry."
                result_summary.append(f"⚠️ DB Error: {err_detail}")
                log_summary.append(f"DB upsert fail: IGN Unique Conflict for {ign_to_store}")
                await log_info(guild, f"HCVerify DB Error: IGN '{ign_to_store}' unique conflict for user {user.mention}. Maybe use /link command?", interaction=interaction)
            else:
                errors_occurred=True
                err_detail=f"API Error ({e.code or 'N/A'}): {e.message or 'Unknown'}"
                result_summary.append(f"⚠️ DB Error: {err_detail}")
                log_summary.append(f"DB fail: {e}")
                await log_error(guild, "HCVerify DB upsert fail (APIError)", error=e, interaction=interaction)
        except Exception as e: # Catch ConnectionError here too via run_supabase_sync
            errors_occurred=True
            err_type = type(e).__name__
            result_summary.append(f"⚠️ DB Error: {err_type}.")
            log_summary.append(f"DB fail: {err_type}")
            await log_error(guild, f"HCVerify DB upsert fail ({err_type})", error=e, interaction=interaction)

    # --- Nickname Management ---
    nickname_to_set = ign_to_store[:32] if ign_to_store else ""
    truncated = ign_to_store != nickname_to_set and ign_to_store

    if not nickname_to_set:
        if db_success: # Only log error if DB step was ok but IGN was empty
            errors_occurred=True
            result_summary.append("⚠️ Nickname Error: Cannot set empty nickname.")
            log_summary.append("Nick skipped (empty IGN)")
    elif user.nick == nickname_to_set:
        result_summary.append(f"🏷️ Nickname already matches stored IGN.")
        log_summary.append("Nick already set")
        nick_success = True
    elif not can_manage_user_nick:
        errors_occurred=True
        result_summary.append(f"⚠️ Nickname Skipped (Hierarchy).")
        log_summary.append("Nick skipped (Hierarchy)")
    else:
        try:
            await user.edit(nick=nickname_to_set, reason=reason)
            nick_msg = f"🏷️ Nickname Set: `{discord.utils.escape_markdown(nickname_to_set)}`"
            if truncated: nick_msg += " (truncated)"
            result_summary.append(nick_msg)
            log_summary.append(f"Nick set{' (trunc)' if truncated else ''}")
            nick_success = True
        except discord.Forbidden:
            errors_occurred=True
            result_summary.append("⚠️ Nickname Error: Permissions error.")
            log_summary.append("Nick fail: Forbidden")
            await log_error(guild, "HCVerify nick fail (Forbidden)", interaction=interaction)
        except discord.HTTPException as e:
            errors_occurred=True
            result_summary.append("⚠️ Nickname Error: API Error.")
            log_summary.append(f"Nick fail: HTTP {e.status}")
            await log_error(guild, "HCVerify nick fail (HTTPException)", error=e, interaction=interaction)
        except Exception as e:
            errors_occurred=True
            result_summary.append("⚠️ Nickname Error: Unknown error.")
            log_summary.append(f"Nick fail: {type(e).__name__}")
            await log_error(guild, "HCVerify unexpected nick error", error=e, interaction=interaction)

    # --- Final Response & Logging ---
    final_color = discord.Color.green() if not errors_occurred else discord.Color.orange()
    final_title = f"{'✅' if not errors_occurred else '⚠️'} HC Verify Processed: {user.display_name}"
    if errors_occurred: final_title += " (with issues/skips)"

    if not result_summary: result_summary.append("ℹ️ No actions were performed or needed.")

    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    try:
        await interaction.followup.send(embed=final_embed)
    except (discord.NotFound, discord.HTTPException) as e:
        await log_error(guild, "HCVerify failed final followup send", error=e, interaction=interaction)

    await log_info(guild, f"`{interaction.user}` HCVerify for {user.mention}. Summary: {'; '.join(log_summary)}.")

    # Trigger list update if roles changed to add HC OR if DB was updated successfully
    if (role_changes_succeeded and role_hc in roles_to_add_final) or db_success:
         print(f"HCVerify: Triggering list update for {user.name} (HC role added: {role_hc in roles_to_add_final}, DB success: {db_success}).")
         asyncio.create_task(update_hc_member_list(guild))

# --- New HCLeave Command (MODIFIED WITH AUTOCOMPLETE) ---
@tree.command(name="hcleave", description="Remove member from HC (Discord role/nick + DB entry).")
@app_commands.describe(
    user="Optional: The Discord user to process.",
    ingame_name="Optional: The IGN to remove from DB (use if no Discord user)."
)
@app_commands.autocomplete(ingame_name=ign_autocomplete) # <--- ADD THIS LINE
@app_commands.checks.has_permissions(manage_roles=True) # Or adjust permission
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def hcleave(interaction: discord.Interaction, user: Optional[discord.Member] = None, ingame_name: Optional[str] = None):
    """Removes HC status, optionally adds ExHC role, resets nick, removes DB entry."""
    guild = interaction.guild
    if not await check_supabase_available(interaction):
        return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return
    if not supabase:
        await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=False)
        await log_error(guild, "hcleave failed: Supabase unavailable.", interaction=interaction)
        return

    # --- Input Validation ---
    if not user and not ingame_name:
        await interaction.response.send_message("❌ You must provide either a Discord `@user` or an `ingame_name`.", ephemeral=False)
        return

    # Defer ephemerally (common admin/cleanup task)
    await interaction.response.defer(thinking=True, ephemeral=False)

    # --- Role Setup ---
    role_hc = guild.get_role(ADD_ROLE_ID_HC)
    role_maybe_exhc = guild.get_role(ROLE_ID_MAYBE_EXHC)
    bot_member = guild.me

    # --- Role Existence Checks ---
    error_msg_setup = ""
    if not role_hc: error_msg_setup += f"HC Role (ID: {ADD_ROLE_ID_HC}) not found.\n"
    # Allow Maybe-ExHC role to be optional for this command
    if ROLE_ID_MAYBE_EXHC and not role_maybe_exhc:
        print(f"hcleave Warning ({guild.name}): Maybe-ExHC Role (ID: {ROLE_ID_MAYBE_EXHC}) not found. Will proceed without adding it.")
        # Don't block the command if this role is missing
    if not role_hc: # Only block if critical HC role is missing
        msg = f"❌ Setup Error:\n{error_msg_setup}Please configure the bot."
        await interaction.followup.send(msg, ephemeral=False)
        await log_error(guild, f"hcleave failed: Missing critical HC role.\n{error_msg_setup}", interaction=interaction)
        return

    # --- Prepare for actions ---
    log_summary = []
    result_summary = []
    errors_occurred = False
    db_removed = False
    hc_role_removed = False
    exhc_role_added = False
    nick_reset = False
    reason = f"HC Leave processed by {interaction.user} (ID: {interaction.user.id})"
    cleaned_ign = ingame_name.strip() if ingame_name else None
    # Determine target identifier for logging/messages early
    target_identifier = f"IGN: `{discord.utils.escape_markdown(cleaned_ign)}`" if cleaned_ign else (f"User: {user.mention}" if user else "Unknown Target")

    # --- Database Deletion ---
    identifier_for_db = None
    target_identifier_db = "Unknown"
    # Prioritize IGN if provided
    if cleaned_ign:
        identifier_for_db = {'ingame_name': cleaned_ign}
        target_identifier_db = f"IGN `{discord.utils.escape_markdown(cleaned_ign)}`"
    elif user:
        # If only user is provided, use their ID to find the DB entry
        identifier_for_db = {'discord_id': str(user.id)}
        target_identifier_db = f"Discord ID `{user.id}`"

    if identifier_for_db:
        try:
            print(f"hcleave: Attempting to delete DB entry matching {identifier_for_db}")
            delete_result = await run_supabase_sync(
                lambda: supabase.table("hc_members")
                               .delete()
                               .match(identifier_for_db)
                               .execute()
            )

            # Check if deletion occurred based on response data
            if delete_result and hasattr(delete_result, 'data') and delete_result.data:
                 db_removed = True
                 result_summary.append(f"🗑️ Database entry removed for {target_identifier_db}.")
                 log_summary.append(f"DB entry delete OK for {identifier_for_db}")
            else:
                 # No error, but nothing deleted - entry might not have existed
                 result_summary.append(f"ℹ️ No database entry found matching {target_identifier_db} to remove.")
                 log_summary.append(f"DB entry delete: No match found for {identifier_for_db}")


        except APIError as e:
            errors_occurred = True
            result_summary.append(f"⚠️ DB Error removing {target_identifier_db}: {e.message}")
            log_summary.append(f"DB delete fail: APIError {e.code} - {e.message}")
            await log_error(guild, f"hcleave DB delete APIError for {identifier_for_db}", error=e, interaction=interaction)
        except ConnectionError as e:
            errors_occurred = True
            result_summary.append(f"⚠️ DB Error removing {target_identifier_db}: Connection failed.")
            log_summary.append("DB delete fail: ConnectionError")
            await log_error(guild, f"hcleave DB delete ConnectionError for {identifier_for_db}", error=e, interaction=interaction)
        except Exception as e:
            errors_occurred = True
            result_summary.append(f"⚠️ DB Error removing {target_identifier_db}: Unexpected error.")
            log_summary.append(f"DB delete fail: {type(e).__name__}")
            await log_error(guild, f"hcleave DB delete unexpected error for {identifier_for_db}", error=e, interaction=interaction)
    else:
        # Should not happen due to initial check, but log defensively
        log_summary.append("DB delete skipped: No identifier provided.")


    # --- Discord User Actions (Only if 'user' is provided) ---
    if user:
        target_identifier = user.mention # Update identifier for Discord context
        can_manage_user_roles = bot_member.top_role.position > user.top_role.position
        can_manage_user_nick = can_manage_user_roles # Nick management requires same hierarchy check

        # 1. Remove HC Role (role_hc guaranteed to exist from earlier check)
        if role_hc not in user.roles:
            result_summary.append(f"ℹ️ User doesn't have the `{role_hc.name}` role.")
            log_summary.append("HC role already absent.")
        elif not can_manage_user_roles or bot_member.top_role.position <= role_hc.position:
            errors_occurred = True
            result_summary.append(f"⚠️ Skipped removing `{role_hc.name}` (Hierarchy).")
            log_summary.append("HC role remove skip: Hierarchy")
        else:
            try:
                await user.remove_roles(role_hc, reason=reason)
                result_summary.append(f"➖ Role Removed: `{role_hc.name}`")
                log_summary.append("HC role remove OK")
                hc_role_removed = True
            except discord.Forbidden: errors_occurred=True; result_summary.append("⚠️ Role Error: Permissions error removing HC role."); log_summary.append("HC role remove fail: Forbidden")
            except discord.HTTPException as e: errors_occurred=True; result_summary.append("⚠️ Role Error: API Error removing HC role."); log_summary.append(f"HC role remove fail: HTTP {e.status}")
            except Exception as e: errors_occurred=True; result_summary.append("⚠️ Role Error: Unknown error removing HC role."); log_summary.append(f"HC role remove fail: {type(e).__name__}")

        # 2. Add Maybe-ExHC Role (only if the role exists)
        if role_maybe_exhc: # Check if role was found during setup
            if role_maybe_exhc in user.roles:
                result_summary.append(f"ℹ️ User already has the `{role_maybe_exhc.name}` role.")
                log_summary.append("ExHC role already present.")
            elif not can_manage_user_roles or bot_member.top_role.position <= role_maybe_exhc.position:
                 errors_occurred = True
                 result_summary.append(f"⚠️ Skipped adding `{role_maybe_exhc.name}` (Hierarchy).")
                 log_summary.append("ExHC role add skip: Hierarchy")
            else:
                try:
                    await user.add_roles(role_maybe_exhc, reason=reason)
                    result_summary.append(f"➕ Role Added: `{role_maybe_exhc.name}`")
                    log_summary.append("ExHC role add OK")
                    exhc_role_added = True
                except discord.Forbidden: errors_occurred=True; result_summary.append("⚠️ Role Error: Permissions error adding ExHC role."); log_summary.append("ExHC role add fail: Forbidden")
                except discord.HTTPException as e: errors_occurred=True; result_summary.append("⚠️ Role Error: API Error adding ExHC role."); log_summary.append(f"ExHC role add fail: HTTP {e.status}")
                except Exception as e: errors_occurred=True; result_summary.append("⚠️ Role Error: Unknown error adding ExHC role."); log_summary.append(f"ExHC role add fail: {type(e).__name__}")
        else:
             log_summary.append("ExHC role add skipped: Role not configured/found.")

        # 3. Reset Nickname
        if user.nick is None:
            result_summary.append("🏷️ User has no nickname to reset.")
            log_summary.append("No nickname reset needed.")
        elif not can_manage_user_nick:
            errors_occurred=True
            result_summary.append(f"⚠️ Nickname Reset Skipped (Hierarchy).")
            log_summary.append("Nick reset skipped (Hierarchy)")
        else:
             try:
                 await user.edit(nick=None, reason=reason)
                 result_summary.append("🏷️ Nickname Reset.")
                 log_summary.append("Nick reset OK")
                 nick_reset = True
             except discord.Forbidden: errors_occurred=True; result_summary.append("⚠️ Nickname Error: Permissions error resetting nick."); log_summary.append("Nick reset fail: Forbidden")
             except discord.HTTPException as e: errors_occurred=True; result_summary.append("⚠️ Nickname Error: API Error resetting nick."); log_summary.append(f"Nick reset fail: HTTP {e.status}")
             except Exception as e: errors_occurred=True; result_summary.append("⚠️ Nickname Error: Unknown error resetting nick."); log_summary.append(f"Nick reset fail: {type(e).__name__}")

    # --- Final Response & Logging ---
    final_color = discord.Color.green() if not errors_occurred else discord.Color.orange()
    # Use the target_identifier determined earlier
    final_title = f"{'✅' if not errors_occurred else '⚠️'} HC Leave Processed: {target_identifier}"
    if errors_occurred: final_title += " (with issues/skips)"

    if not result_summary: result_summary.append("ℹ️ No actions were performed or needed.")

    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    try:
        await interaction.followup.send(embed=final_embed, ephemeral=False)
    except (discord.NotFound, discord.HTTPException) as e:
        await log_error(guild, "hcleave failed final followup send", error=e, interaction=interaction)

    await log_info(guild, f"`{interaction.user}` processed /hcleave for {target_identifier}. Summary: {'; '.join(log_summary)}.")

    # Trigger list update if DB entry was removed OR if HC role was removed from a Discord user
    if db_removed or hc_role_removed:
        print(f"hcleave: Triggering list update for {target_identifier} (DB removed: {db_removed}, HC role removed: {hc_role_removed}).")
        asyncio.create_task(update_hc_member_list(guild))

@tree.command(name="hconly", description="Register an HC member by IGN only (no Discord link).")
@app_commands.describe(ingame_name="The player's unique in-game name.")
@app_commands.checks.has_permissions(manage_roles=True) # Or another suitable permission
async def hconly(interaction: discord.Interaction, ingame_name: str):
    """Adds a member to the HC database using only their IGN."""
    guild = interaction.guild
    # Use the check_supabase_available helper function early
    if not await check_supabase_available(interaction):
        # Helper function handles ephemeral message and logging if Supabase is down.
        # No deferral needed yet, as the helper responds if needed.
        return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    # Ensure supabase client is valid after the check (though check_supabase_available should guarantee it)
    if not supabase:
        # This case should technically be caught by check_supabase_available, but defensive check
        await interaction.response.send_message("❌ Database client error after check.", ephemeral=False)
        await log_error(guild, "hconly: Supabase client became None unexpectedly after check_supabase_available passed.", interaction=interaction)
        return

    # Defer ephemerally as this is primarily an admin action
    await interaction.response.defer(thinking=True, ephemeral=False)

    cleaned_ign = ingame_name.strip()
    if not cleaned_ign:
        await interaction.followup.send("❌ In-game name cannot be empty.", ephemeral=False)
        return

    try:
        # Prepare data for insertion, explicitly setting discord_id and discord_name to None
        data_to_insert = {
            "ingame_name": cleaned_ign,
            "discord_id": None,
            "discord_name": None # Keep consistency, set to None as well
        }

        # Attempt to insert the new record
        insert_result = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .insert(data_to_insert)
                           .execute()
        )

        # Check if insert was successful (basic check, Supabase client might evolve)
        # Typically, if no exception is raised, it's considered successful for basic inserts.
        # You might want to inspect insert_result for more details if needed.

        success_msg = f"✅ Successfully registered **{discord.utils.escape_markdown(cleaned_ign)}** (IGN only) in the database."
        await interaction.followup.send(success_msg, ephemeral=False)
        await log_info(guild, f"`{interaction.user}` used /hconly to register IGN: `{cleaned_ign}`.")

        # Trigger list update since the underlying data changed
        print(f"HCOnly: Triggering list update after adding IGN {cleaned_ign}.")
        asyncio.create_task(update_hc_member_list(guild))

    except APIError as e:
        # Check for unique constraint violation (PostgREST code 23505)
        # Note: Error structure/codes might vary slightly. Check Supabase/PostgREST docs.
        # Example structure check: hasattr(e, 'code') and e.code == '23505'
        # Or check the message content: 'duplicate key value violates unique constraint "hc_members_ingame_name_unique"'
        if "unique constraint" in str(e.message).lower() and "hc_members_ingame_name_unique" in str(e.message).lower():
             error_msg = f"❌ Failed: In-game name **{discord.utils.escape_markdown(cleaned_ign)}** already exists in the database."
             await interaction.followup.send(error_msg, ephemeral=False)
             await log_info(guild, f"/hconly failed for IGN `{cleaned_ign}` (already exists). User: `{interaction.user}`")
        else:
            # Other Supabase API errors
            await log_error(guild, f"Supabase API Error during /hconly for IGN: {cleaned_ign}", error=e, interaction=interaction)
            await interaction.followup.send(f"❌ Database API Error: {e.message}", ephemeral=False)
    except ConnectionError as e:
        # Handle cases where run_supabase_sync raises ConnectionError itself
        await log_error(guild, f"Database connection error during /hconly for IGN: {cleaned_ign}", error=e, interaction=interaction)
        await interaction.followup.send("❌ Database connection error.", ephemeral=False)
    except Exception as e:
        # Catch any other unexpected errors during the insert process
        await log_error(guild, f"Unexpected error during /hconly for IGN: {cleaned_ign}", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=False)

# --- Activate Myself Command ---
@tree.command(name="activatemyself", description="Mark yourself as active for today in the HC activity log.")
# No extra permissions needed by default, relies on user having a linked IGN
async def activatemyself(interaction: discord.Interaction):
    guild = interaction.guild
    if not await check_supabase_available(interaction):
        return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    # Defer ephemerally as it's a personal action confirmation
    await interaction.response.defer(thinking=True, ephemeral=False) # Change to False since we are not making it ephemeral

    user_id = interaction.user.id
    user_mention = interaction.user.mention

    # 1. Fetch User's IGN
    stored_ign = await get_ign_from_user(guild, user_id)

    if not stored_ign:
        await interaction.followup.send(
            f"❌ {user_mention}, I couldn't find a linked In-Game Name (IGN) for you in the database. "
            f"You might need to be verified with {get_cmd_mention('hcverify')} or contact an admin to link your account.",
            ephemeral=False # Change to False since we are not making it ephemeral
        )
        await log_info(guild, f"{user_mention} tried /activatemyself but has no linked IGN.")
        return

    # 2. Get Today's Date
    activity_date, date_error = get_utc_date() # No date string needed, defaults to today
    if date_error or not activity_date:
        await interaction.followup.send(f"❌ Could not determine today's date. Please try again later.", ephemeral=False) # Change to False since we are not making it ephemeral
        await log_error(guild, f"/activatemyself internal error: Failed to get today's date ({date_error})", interaction=interaction)
        return

    # 3. Upsert Activity Log
    success, message = await upsert_activity_log(guild, stored_ign, activity_date, user_id)

    prefix = "✅" if success else "⚠️"
    # Tailor the message slightly
    response_msg = f"{prefix} {user_mention}, "
    if success:
        response_msg += f"you've been marked as active for today ({format_date_dmy(activity_date)}) with IGN `{discord.utils.escape_markdown(stored_ign)}`."
    else:
        # Provide the error message from upsert_activity_log
        response_msg += f"failed to mark you as active: {message.split(': ', 1)[-1]}" # Get message part after "IGN `...`:" if structure is consistent

    await interaction.followup.send(response_msg, ephemeral=False) # Change to False since we are not making it ephemeral

    # 4. Log and Trigger Update (if successful)
    if success:
        await log_info(guild, f"`{interaction.user}` used /activatemyself. Marked IGN `{stored_ign}` active for {format_date_dmy(activity_date)}. Triggering list update.")
        asyncio.create_task(update_hc_member_list(guild))
    # else: Error already logged by upsert_activity_log if it failed internally

# --- Active Command ---
@tree.command(name="active", description="Mark an In-Game Name (IGN) as active for a specific date.")
@app_commands.describe(
    ingame_name="The In-Game Name (IGN) to mark active.",
    date="Date of activity (YYYY-MM-DD, defaults to today UTC)."
)
@app_commands.autocomplete(ingame_name=ign_autocomplete)
# @app_commands.checks.has_permissions(manage_roles=True) # Optional permission check
async def active(interaction: discord.Interaction, ingame_name: str, date: Optional[str] = None):
    # <<< NO EXTRA TEXT BETWEEN HERE...
    guild = interaction.guild
    # ...AND HERE >>>
    if not await check_supabase_available(interaction): return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    await interaction.response.defer(thinking=True, ephemeral=False)

    activity_date, date_error = get_utc_date(date)
    if date_error:
        await interaction.followup.send(f"❌ {date_error}", ephemeral=False)
        return
    if not activity_date:
         await interaction.followup.send("❌ Could not determine activity date.", ephemeral=False)
         return

    target_ign = ingame_name.strip()
    if not target_ign:
        await interaction.followup.send(f"❌ In-game name cannot be empty.", ephemeral=False)
        return
    display_target = f"IGN `{discord.utils.escape_markdown(target_ign)}`"

    success, message = await upsert_activity_log(guild, target_ign, activity_date, interaction.user.id)

    prefix = "✅" if success else "⚠️"
    await interaction.followup.send(f"{prefix} {message}", ephemeral=False)

    if success:
        await log_info(guild, f"`{interaction.user}` used /active for {display_target} on {format_date_dmy(activity_date)}. Triggering list update.")
        asyncio.create_task(update_hc_member_list(guild))


# --- Inactive Command (CORRECTED DECORATOR) ---
@tree.command(name="inactive", description="Remove an activity record for an IGN on a specific date.")
@app_commands.describe(
    # user="The Discord user to mark inactive (fetches their IGN).", # <-- REMOVED THIS LINE
    ingame_name="The In-Game Name (IGN) to mark inactive.",
    date="Date of activity to remove (YYYY-MM-DD, defaults to today UTC)."
)
@app_commands.autocomplete(ingame_name=ign_autocomplete)
async def inactive(interaction: discord.Interaction, ingame_name: str, date: Optional[str] = None):
    guild = interaction.guild
    if not await check_supabase_available(interaction): return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    await interaction.response.defer(thinking=True, ephemeral=False)

    activity_date, date_error = get_utc_date(date)
    if date_error:
        await interaction.followup.send(f"❌ {date_error}", ephemeral=False)
        return
    if not activity_date:
         await interaction.followup.send("❌ Could not determine activity date.", ephemeral=False)
         return

    target_ign = ingame_name.strip()
    if not target_ign:
        await interaction.followup.send(f"❌ In-game name cannot be empty.", ephemeral=False)
        return
    display_target = f"IGN `{discord.utils.escape_markdown(target_ign)}`"

    success, message = await remove_activity_log(guild, target_ign, activity_date, interaction.user.id)

    if "removed" in message: prefix = "✅"
    elif "No activity record found" in message: prefix = "ℹ️"
    else: prefix = "❌"
    await interaction.followup.send(f"{prefix} {message}", ephemeral=False)

    if success:
        await log_info(guild, f"`{interaction.user}` used /inactive for {display_target} on {format_date_dmy(activity_date)}. Record removed. Triggering list update.")
        asyncio.create_task(update_hc_member_list(guild))
    elif prefix == "ℹ️":
         await log_info(guild, f"`{interaction.user}` used /inactive for {display_target} on {format_date_dmy(activity_date)}. No record found.")

# @app_commands.checks.has_permissions(manage_roles=True) # Mirror permissions of /active if needed
async def inactive(interaction: discord.Interaction, user: Optional[discord.Member] = None, ingame_name: Optional[str] = None, date: Optional[str] = None):
    guild = interaction.guild
    if not await check_supabase_available(interaction): return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    # --- Input Validation ---
    if not user and not ingame_name:
        await interaction.response.send_message("❌ You must provide either a Discord `@user` or an `ingame_name`.", ephemeral=False)
        return
    if user and ingame_name:
        await interaction.response.send_message("❌ Please provide either a Discord `@user` or an `ingame_name`, not both.", ephemeral=False)
        return

    # Defer ephemerally
    await interaction.response.defer(thinking=True, ephemeral=False)

    # --- Get Date ---
    activity_date, date_error = get_utc_date(date)
    if date_error:
        await interaction.followup.send(f"❌ {date_error}", ephemeral=False)
        return
    if not activity_date:
         await interaction.followup.send("❌ Could not determine activity date.", ephemeral=False)
         return

    # --- Determine IGN ---
    target_ign: Optional[str] = None
    if user:
        fetched_ign = await get_ign_from_user(guild, user.id)
        if not fetched_ign:
            await interaction.followup.send(f"❌ Could not find a stored IGN for {user.mention}. Cannot remove activity.", ephemeral=False)
            return
        target_ign = fetched_ign
        display_target = user.mention
    else: # ingame_name must be provided
        target_ign = ingame_name.strip() # Ensure IGN is stripped
        if not target_ign:
             await interaction.followup.send(f"❌ In-game name cannot be empty.", ephemeral=False)
             return
        display_target = f"IGN `{target_ign}`"

    if not target_ign: # Should not happen
        await interaction.followup.send("❌ Failed to determine the target IGN.", ephemeral=False)
        await log_error(guild, "/inactive command failed: target_ign became None unexpectedly.", interaction=interaction)
        return

    # --- Remove Activity Log ---
    # 'success' here means a record was actually found and deleted.
    # 'message' contains details (deleted, not found, or error).
    success, message = await remove_activity_log(guild, target_ign, activity_date, interaction.user.id)

    # --- Send Feedback ---
    # Use different prefixes based on outcome
    if "removed" in message:
        prefix = "✅" # Record was found and removed
    elif "No activity record found" in message:
         prefix = "ℹ️" # Record wasn't there, not an error but info
    else:
         prefix = "❌" # Actual error occurred

    await interaction.followup.send(f"{prefix} {message}", ephemeral=False)

    # --- Trigger List Refresh and Log ---
    # Only trigger refresh if a record was actually deleted (success == True)
    if success:
        await log_info(guild, f"`{interaction.user}` used /inactive for {display_target} on {format_date_dmy(activity_date)}. Record removed. Triggering list update.")
        # Trigger the static list update in the background
        asyncio.create_task(update_hc_member_list(guild))
    elif prefix == "ℹ️":
         # Log that the command was used but nothing changed
         await log_info(guild, f"`{interaction.user}` used /inactive for {display_target} on {format_date_dmy(activity_date)}. No record found.")
    # else: # Error case is logged by remove_activity_log


# --- Bulk Active Command ---
@tree.command(name="bulkactive", description="Mark multiple members active via IGNs using a modal.")
@app_commands.describe(
    date="Date of activity (YYYY-MM-DD, defaults to today UTC)."
)
# @app_commands.checks.has_permissions(manage_roles=True) # Or your chosen permission
async def bulkactive(interaction: discord.Interaction, date: Optional[str] = None):
    # Pass the date string to the modal constructor
    modal = BulkActiveModal(date_str=date)
    await interaction.response.send_modal(modal)

@tree.command(name="hcmembers", description="Show interactive list of [HC1] members (username#tag ➔ IGN / Activity).")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    # Keep Supabase check
    if not await check_supabase_available(interaction):
        try: # Attempt cleanup if deferred
            if interaction.response.is_done(): await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        except (discord.NotFound, discord.HTTPException): pass
        return
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=False)
        return

    # Channel check (same as before)
    if interaction.user.id != SELF_PROTECTED_ID and interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        allowed_mentions = [f"<#{ch_id}>" for ch_id in ALLOWED_CHANNEL_IDS if guild.get_channel(ch_id)]
        msg = f"❌ This command only works in: {', '.join(allowed_mentions) or 'configured channels'}"
        if interaction.user.id != SELF_PROTECTED_ID:
            await log_info(guild, f"User `{interaction.user}` attempted /hcmembers in disallowed channel {interaction.channel.mention if interaction.channel else interaction.channel_id}.")
        await interaction.response.send_message(msg, ephemeral=False)
        return

    await interaction.response.defer(thinking=True, ephemeral=False)

    try:
        # 1. Fetch base data (includes all-time activity)
        original_data, total = await fetch_hc_member_data(guild)

        if not original_data:
            embed = create_embed(title=HC_LIST_EMBED_TITLE, description="No HC members found in the database or matching roles.", color=discord.Color.orange())
            await interaction.followup.send(embed=embed)
            return

        # 2. Fetch initial data for the default view (Monthly Activity)
        initial_display_data = list(original_data) # Start with a copy of original data
        try:
            # Calculate date range for monthly view
            today_utc = datetime.datetime.now(pytz.utc).date()
            end_date_monthly = today_utc
            start_date_monthly = today_utc - datetime.timedelta(days=29)
            all_igns = [item['ign'] for item in original_data if item.get('ign')]

            if all_igns:
                print(f"/hcmembers: Fetching initial monthly activity for {len(all_igns)} IGNs...")
                monthly_activity_data = await fetch_activity_data(guild, all_igns, start_date_monthly, end_date_monthly)
                print(f"/hcmembers: Fetched {len(monthly_activity_data)} monthly activity results.")

                # Update initial_display_data with the monthly activity
                temp_data = []
                for item in original_data: # Iterate original to keep structure
                    ign_lower = item.get('ign', '').lower()
                    activity_info = monthly_activity_data.get(ign_lower, {'count': 0, 'last_seen': None})
                    updated_item = item.copy() # Create a new dict
                    # Overwrite activity_count and last_seen with monthly data
                    updated_item['activity_count'] = activity_info['count']
                    updated_item['last_seen'] = activity_info['last_seen']
                    temp_data.append(updated_item)
                initial_display_data = temp_data # Replace with monthly-updated data
                print("/hcmembers: Updated initial_display_data with monthly activity.")
            else:
                 print("/hcmembers: No IGNs found, skipping initial monthly fetch.")

        except Exception as fetch_err:
             # Log error during initial fetch but proceed with original (all-time) data
             await log_error(guild, "Failed to fetch initial monthly activity for /hcmembers", error=fetch_err, interaction=interaction)
             initial_display_data = list(original_data) # Fallback to original data

        # 3. Create and send the view, passing BOTH original and initial data
        # The view will handle sorting the initial_display_data based on default sort mode
        view = HCPagesView(
            original_data=original_data, # Pass the base data with all-time activity
            initial_display_data=initial_display_data, # Pass the data prepped for the default view
            total_members=total,
            guild=guild # Pass guild for potential future use in view if needed
        )
        initial_embed = view.create_page_embed() # create_page_embed uses self.current_data
        message = await interaction.followup.send(embed=initial_embed, view=view)
        view.message = message # Link message to view

        # Log success (same as before)
        log_detail = ""
        if interaction.user.id == SELF_PROTECTED_ID and interaction.channel_id not in ALLOWED_CHANNEL_IDS:
            log_detail = " (Protected user bypass)"
        await log_info(guild, f"/hcmembers used by `{interaction.user}` in {interaction.channel.mention if interaction.channel else 'N/A'}{log_detail}.")

    # Keep existing error handling (same as before)
    except ConnectionError as e:
        await log_error(guild, "/hcmembers DB connection error", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Database Connection Error.", discord.Color.red()))
    except APIError as e:
        await log_error(guild, "/hcmembers Supabase API error", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Database API Error.", discord.Color.red()))
    except Exception as e:
        await log_error(guild, "Unhandled /hcmembers error", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ An unexpected error occurred.", discord.Color.red()))

# --- Refresh Static List Command (MODIFIED - Removed manual delete logic) ---
@tree.command(name="refresh", description="Manually refresh static [HC1] list.") # Removed "(auto-deletes confirmation)" from description
@app_commands.checks.has_permissions(manage_roles=True) # Keep permission check
async def refresh(interaction: discord.Interaction):
    guild = interaction.guild
    # --- Initial Checks ---
    if not await check_supabase_available(interaction):
        try:
             if interaction.response.is_done():
                  await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        except (discord.NotFound, discord.HTTPException): pass
        return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return
    if not supabase: # Check again just in case
        await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=False)
        await log_error(guild, "/refresh failed: Supabase unavailable post-check.", interaction=interaction)
        return

    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(list_channel, discord.TextChannel):
        msg = f"❌ Configuration Error: Static list channel (ID: {HC_MEMBER_LIST_CHANNEL_ID}) is invalid or not found."
        await interaction.response.send_message(msg, ephemeral=False)
        await log_error(guild, f"/refresh failed: Static list channel invalid.", interaction=interaction)
        return

    # --- Defer Publicly ---
    await interaction.response.defer(thinking=True, ephemeral=False)

    try:
        await log_info(guild, f"Manual static list refresh initiated by `{interaction.user}`.")

        # --- Run the update function and wait for completion ---
        await update_hc_member_list(guild)
        # --- List update is now complete ---

        # --- Send Confirmation (NOT ephemeral) ---
        # REMOVED: ", This message will self-destruct shortly."
        confirmation_message = await interaction.followup.send(
            f"✅ Refresh complete for the static list in {list_channel.mention}.",
            ephemeral=False # MUST be False for the bot's on_message to see and potentially delete it
        )
        await log_info(guild, f"Refresh command confirmed complete to user {interaction.user}.")

        # --- REMOVED ASYNCIO.SLEEP AND MANUAL DELETE BLOCK ---
        # The on_message event handler will now take care of deleting
        # the confirmation_message if interaction.channel_id == AUTODELETE_CHANNEL_ID

    except Exception as e:
        # Catch errors during the main refresh process or sending the initial confirmation
        await log_error(guild, "Error during /refresh process", error=e, interaction=interaction)
        # Try to inform the user if the main process failed
        try:
            # Use edit_original_response since we definitely deferred
            await interaction.edit_original_response(content="❌ An unexpected error occurred during the refresh process.", embed=None, view=None)
        except Exception: pass # Ignore errors during error reporting             

# --- Sync Nicknames Command (Optimized DB Query) ---
@tree.command(name="syncnicknames", description="Sync all HC members' nicknames with their stored IGNs.")
@app_commands.checks.has_permissions(manage_nicknames=True) # User needs manage nicknames
@app_commands.checks.bot_has_permissions(manage_nicknames=True) # Bot needs manage nicknames
async def syncnicknames(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    # Defer ephemerally while processing
    await interaction.response.defer(thinking=True, ephemeral=False)

    if not supabase:
        await interaction.edit_original_response(content="❌ Database connection unavailable.")
        await log_error(guild, "/syncnicknames failed: Supabase unavailable.", interaction=interaction)
        return

    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await interaction.edit_original_response(content=f"❌ Configuration Error: HC Role (ID: {ADD_ROLE_ID_HC}) not found.")
        await log_error(guild, f"/syncnicknames failed: HC role not found.", interaction=interaction)
        return

    # --- Start Sync Process ---
    start_time = discord.utils.utcnow()
    await log_info(guild, f"Nickname sync initiated by `{interaction.user}`.")
    loading_emoji = "🔄" # Simple fallback emoji
    await interaction.edit_original_response(content=f"{loading_emoji} Fetching members...")

    # 1. Get all members with the HC role first
    hc_members: List[discord.Member] = []
    try:
        # Ensure members are cached
        if not guild.chunked:
            print(f"Chunking guild {guild.name} for sync nicknames...")
            await guild.chunk(cache=True)
        hc_members = [m for m in guild.members if hc_role in m.roles and not m.bot]
        total_hc_members = len(hc_members)
        print(f"SyncNick ({guild.name}): Found {total_hc_members} members with the '{hc_role.name}' role.")
    except Exception as e:
        await log_error(guild, "SyncNick: Member fetch/chunking failed", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Failed to fetch server members.")
        return

    if total_hc_members == 0:
        await interaction.edit_original_response(content=f"ℹ️ No members found with the `{hc_role.name}` role. Nothing to sync.")
        return

    # Get IDs of members with the HC role
    hc_member_ids = [str(m.id) for m in hc_members]

    # 2. Fetch IGNs *only* for these specific members from Supabase
    await interaction.edit_original_response(content=f"{loading_emoji} Fetching IGN data for {total_hc_members} members...")
    ign_data = {} # discord_id (str) -> ingame_name (str)
    try:
        # Chunk the query if there are many members (e.g., > 500)
        chunk_size = 500
        for i in range(0, len(hc_member_ids), chunk_size):
            id_chunk = hc_member_ids[i:i+chunk_size]
            print(f"SyncNick ({guild.name}): Fetching IGNs for chunk {i//chunk_size + 1}/{math.ceil(len(hc_member_ids)/chunk_size)}")
            resp = await run_supabase_sync(
                lambda: supabase.table("hc_members")
                                .select("discord_id, ingame_name")
                                .in_("discord_id", id_chunk)
                                .execute()
            )
            if resp and hasattr(resp, 'data') and resp.data:
                ign_data.update({str(item['discord_id']): item['ingame_name']
                                 for item in resp.data
                                 if item.get('discord_id') and item.get('ingame_name')})
            await asyncio.sleep(0.1) # Small delay between chunks

        print(f"SyncNick ({guild.name}): Fetched {len(ign_data)} relevant IGNs from database.")
    except ConnectionError as e:
        await log_error(guild, "SyncNick: Database connection failed during IGN fetch.", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Database connection failed. Cannot proceed.")
        return
    except APIError as e:
        await log_error(guild, "SyncNick: Database API error during IGN fetch.", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Database API error. Cannot proceed.")
        return
    except Exception as e:
        await log_error(guild, "SyncNick: Database fetch failed (unexpected)", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Database fetch failed. Cannot proceed.")
        return

    # 3. Iterate and Update Nicknames
    await interaction.edit_original_response(content=f"{loading_emoji} Syncing {total_hc_members} members...")
    counts = {'proc': 0, 'upd': 0, 'skip_match': 0, 'skip_no_ign': 0, 'skip_empty': 0, 'skip_hier': 0, 'fail_forbid': 0, 'fail_http': 0, 'fail_other': 0}
    bot_member = guild.me # Get bot member once
    bot_pos = bot_member.top_role.position
    last_prog_update_time = asyncio.get_event_loop().time()
    update_interval = 5.0 # Update progress every 5 seconds

    for idx, member in enumerate(hc_members):
        counts['proc'] += 1
        member_id_str = str(member.id)

        # Hierarchy check: Bot must be higher than the member to change nick
        # Still important even if bot has admin, as owner/higher roles can exist
        if bot_pos <= member.top_role.position:
            counts['skip_hier'] += 1
            continue

        # Get stored IGN from the data we fetched
        stored_ign = ign_data.get(member_id_str)
        if not stored_ign:
            counts['skip_no_ign'] += 1
            continue # Skip if no IGN stored for this specific member

        target_nick = stored_ign.strip()
        if not target_nick:
            counts['skip_empty'] += 1
            continue # Skip if stored IGN is empty/whitespace

        target_nick = target_nick[:32] # Truncate

        if member.nick == target_nick:
            counts['skip_match'] += 1
            continue # Skip if nickname already matches

        # Attempt nickname update
        try:
            await member.edit(nick=target_nick, reason=f"Nickname Sync initiated by {interaction.user.id}")
            counts['upd'] += 1
            await asyncio.sleep(0.2) # Keep delay to avoid rate limits
        except discord.Forbidden:
            counts['fail_forbid'] += 1
        except discord.HTTPException as e_http:
            counts['fail_http'] += 1
            if e_http.status == 429: print(f"SyncNick ({guild.name}): Rate limit hit!") # Log rate limits
        except Exception as e_other:
            counts['fail_other'] += 1
            await log_error(guild, f"SyncNick: Unexpected error updating nick for {member.mention}", error=e_other, interaction=interaction)

        # Update progress periodically
        now = asyncio.get_event_loop().time()
        if (now - last_prog_update_time > update_interval) or (counts['proc'] == total_hc_members):
             if interaction.is_expired(): # Check if interaction expired before editing
                  print(f"SyncNick ({guild.name}): Interaction expired, cannot update progress.")
                  last_prog_update_time = now + 999 # Prevent further attempts
                  continue
             try:
                await interaction.edit_original_response(content=f"{loading_emoji} Syncing... ({counts['proc']}/{total_hc_members})")
                last_prog_update_time = now
             except (discord.NotFound, discord.HTTPException):
                print(f"SyncNick ({guild.name}): Progress update failed. Continuing sync...")
                last_prog_update_time = now + 999 # Prevent further attempts

    # 4. Send Final Summary (Same as before)
    end_time = discord.utils.utcnow()
    duration = (end_time - start_time).total_seconds()
    summary_embed = discord.Embed(title="✅ Nickname Sync Complete!", color=NERDY_YELLOW, timestamp=end_time)
    total_skipped = counts['skip_match'] + counts['skip_no_ign'] + counts['skip_empty'] + counts['skip_hier']
    total_failed = counts['fail_forbid'] + counts['fail_http'] + counts['fail_other']
    summary_lines = [
        f"⏱️ **Duration:** {duration:.2f} seconds",
        f"👥 **Total HC Members Found:** {total_hc_members}",
        f"📊 **Relevant IGNs Fetched:** {len(ign_data)}", # Added relevant fetch count
        f"🔄 **Members Processed:** {counts['proc']}",
        f"✅ **Nicknames Updated:** {counts['upd']}",
        f"ℹ️ **Skipped (No Change/Hierarchy/No IGN):** {total_skipped}",
        f"   - Already Matched: {counts['skip_match']}",
        f"   - No/Empty IGN Stored: {counts['skip_no_ign'] + counts['skip_empty']}",
        f"   - Bot Hierarchy Too Low: {counts['skip_hier']}",
        f"❌ **Failed Updates:** {total_failed}",
        f"   - Permissions Error: {counts['fail_forbid']}",
        f"   - API/HTTP Error: {counts['fail_http']}",
        f"   - Other Errors: {counts['fail_other']}"
    ]
    summary_embed.description = "\n".join(summary_lines)

    # Try edit first, then followup
    try:
        if not interaction.is_expired():
            await interaction.edit_original_response(content=None, embed=summary_embed)
        else:
            print(f"SyncNick ({guild.name}): Interaction expired before final summary edit. Attempting followup.")
            await interaction.followup.send(embed=summary_embed, ephemeral=False)
    except (discord.NotFound, discord.HTTPException) as e_edit:
        print(f"SyncNick ({guild.name}): Final summary edit failed ({e_edit}). Attempting followup.")
        try: await interaction.followup.send(embed=summary_embed, ephemeral=False)
        except Exception as e_followup: print(f"SyncNick ({guild.name}): Final followup send also failed: {e_followup}")
        await log_error(guild, "SyncNick: Could not send final summary to user.", embed=summary_embed, interaction=interaction) # Log summary if user notification failed
    except Exception as e_outer:
        print(f"SyncNick ({guild.name}): Unknown error sending final summary: {e_outer}")
        await log_error(guild, "SyncNick: Unknown error sending final summary.", error=e_outer, embed=summary_embed, interaction=interaction)

    # Log detailed summary internally
    log_embed = discord.Embed(title="Nickname Sync Finished", description="\n".join(summary_lines), color=NERDY_YELLOW)
    log_embed.set_footer(text=f"Initiated by {interaction.user}")
    await log_info(guild, "", embed=log_embed)


# --- Wither Command ---
@tree.command(name="wither", description="Temporarily remove roles from a user.")
@app_commands.describe(
    user="User to wither.",
    time="Duration in minutes (0.1 to 10, default 2)."
)
async def wither(interaction: discord.Interaction, user: discord.Member, time: app_commands.Range[float, 0.1, 10.0] = 2.0):
    guild = interaction.guild
    invoker = interaction.user # Member object of the user running the command

    # Pre-checks (must be done before deferring potentially)
    if not guild:
        await interaction.response.send_message("This command cannot be used outside a server.", ephemeral=False)
        return

    bot_member = guild.me # Bot's member object in the guild

    async def fail_check(log_reason: str, user_message: str):
        """Helper to send ephemeral failure message and log error."""
        # Ensure response is only sent once
        send_method = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        try:
            # Use create_embed helper
            await send_method(embed=create_embed(user_message, discord.Color.red()), ephemeral=False)
        except (discord.NotFound, discord.InteractionResponded, discord.HTTPException) as e:
             # Catch common errors if sending fails
            print(f"Wither Check Fail Send Error: {type(e).__name__} - {e}")
        except Exception as e:
             print(f"Wither Check Fail Send Error (Unknown): {e}")
        # Log the failure reason
        await log_error(guild, f"Wither check fail ({invoker.name} -> {user.name}): {log_reason}", interaction=interaction)

    # 1. Permission Check (Invoker)
    if invoker.id not in ALLOWED_WITHER_IDS:
        # Defer ephemerally *before* sending fail message if not already done
        if not interaction.response.is_done():
            try: await interaction.response.defer(ephemeral=False)
            except discord.InteractionResponded: pass # Race condition handled
        await fail_check("Invoker permission denied.", "❌ You do not have permission to use this command.")
        return

    # 2. Defer Publicly (thinking state visible) - DO THIS *AFTER* invoker check
    # If the invoker check passed, we intend to proceed publicly.
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(thinking=True, ephemeral=False)
        except discord.InteractionResponded:
             # If it was already responded to (e.g., by the failed ephemeral defer above somehow)
             # This shouldn't normally happen if logic flow is correct, but handle defensively.
             print(f"Warning: Interaction {interaction.id} was already responded to before public defer in wither.")
             pass

    # 3. Target Checks (Self, Protected, Bot, Hierarchy)
    if user.id == invoker.id: await fail_check("Target self.", "🤨 You cannot wither yourself."); return
    # Check protected ID, allow if invoker IS the protected ID
    if user.id == SELF_PROTECTED_ID and invoker.id != SELF_PROTECTED_ID: await fail_check("Target protected.", f"😨 Cannot wither the protected user (<@{SELF_PROTECTED_ID}>)."); return
    if user.id == BOT_ID: await fail_check("Target bot.", "😭 You cannot wither me!"); return
    if user.bot: await fail_check("Target other bot.", "🤖 You cannot wither other bots."); return
    # Check guild owner, allow if invoker IS the owner
    if guild.owner_id and user.id == guild.owner_id and invoker.id != guild.owner_id: await fail_check("Target guild owner.", f"👑 You cannot wither the server owner (<@{guild.owner_id}>)."); return
    # Bot hierarchy check
    if bot_member.top_role.position <= user.top_role.position: await fail_check("Bot hierarchy low.", f"❌ My highest role ('{bot_member.top_role.name}') is not high enough to manage {user.mention}'s roles."); return
    # Invoker hierarchy check (unless invoker is owner)
    if invoker.id != guild.owner_id and invoker.top_role.position <= user.top_role.position: await fail_check("Invoker hierarchy low.", f"❌ Your highest role ('{invoker.top_role.name}') is not high enough to wither {user.mention}."); return
    # Bot permissions check
    if not bot_member.guild_permissions.manage_roles: await fail_check("Bot missing manage_roles perm.", "❌ I lack the `Manage Roles` permission needed for this command."); return


    # 4. Get Original Roles (excluding @everyone)
    original_roles = [r for r in user.roles if r.id != guild.default_role.id]
    if not original_roles:
        # Use followup since we deferred publicly
        await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} has no roles (other than @everyone) to remove.", discord.Color.orange()), ephemeral=False)
        return

    # --- Start of Main Wither Logic (Outer Try Block) ---
    try:
        # Calculate duration
        wither_seconds = min(max(1, int(time * 60)), int(MAX_WITHER_SECONDS or 600)) # Ensure bounds, convert minutes to seconds
        actual_minutes = wither_seconds / 60.0
        reason_wither = f"Withered by {invoker.name} ({invoker.id}) for {actual_minutes:.1f}m."

        # --- Role Removal ---
        # Filter roles the bot can actually manage based on hierarchy
        roles_to_remove_actually = [r for r in original_roles if bot_member.top_role.position > r.position]
        skipped_roles_remove = [r for r in original_roles if r not in roles_to_remove_actually]

        if not roles_to_remove_actually:
             await interaction.followup.send(embed=create_embed(f"ℹ️ Cannot wither {user.display_name}: None of their roles are below my highest role.", color=discord.Color.orange()), ephemeral=False)
             await log_info(guild, f"Wither attempt on {user.name} by {invoker.name} failed: No manageable roles.")
             return

        # Perform role removal using edit (replace roles with only @everyone)
        # Ensure @everyone role exists (should always be true)
        everyone_role = guild.default_role
        await user.edit(roles=[everyone_role], reason=reason_wither)

        # --- Send Confirmation ---
        roles_removed_names = (', '.join(f"`{r.name}`" for r in roles_to_remove_actually) or 'None Manageable')
        # Truncate if too long for embed description field part
        if len(roles_removed_names) > 900: roles_removed_names = roles_removed_names[:897] + "..."

        wither_desc = f"{user.mention} has been withered by {invoker.mention} for **{actual_minutes:.1f} minutes**!\n\n**Roles Removed:** {roles_removed_names}"
        if skipped_roles_remove:
            skipped_names = (', '.join(f"`{r.name}`" for r in skipped_roles_remove))
            if len(skipped_names) > 100: skipped_names = skipped_names[:97] + "..."
            wither_desc += f"\n*(Skipped {len(skipped_roles_remove)} role(s) due to hierarchy: {skipped_names})*"

        await interaction.followup.send(embed=create_embed(title="🌪️ Wither Cast! 🌪️", description=wither_desc, color=discord.Color.dark_purple()), ephemeral=False)

        # --- Log Action ---
        log_msg = f"`{user.name}` ({user.id}) withered by `{invoker.name}` ({invoker.id}) for {actual_minutes:.1f}m. Roles removed: {', '.join(r.name for r in roles_to_remove_actually) or 'N/A'}."
        if skipped_roles_remove: log_msg += f" Skipped (hierarchy): {', '.join(r.name for r in skipped_roles_remove)}."
        await log_info(guild, log_msg)

        # --- Wait Period ---
        await asyncio.sleep(wither_seconds)

        # --- Role Restore (Inner Try Block) ---
        try:
            # Refetch member and bot objects to ensure data/perms are current
            # Use fetch_member as user might have rejoined/roles changed externally
            member_after = await guild.fetch_member(user.id)
            # Fetch bot member too in case its roles changed
            bot_member_after = await guild.fetch_member(bot.user.id) if bot.user else await guild.fetch_me()
            reason_restore = f"Wither expired after {actual_minutes:.1f}m. Restoring roles."

            # --- Pre-Restore Checks ---
            # Check bot permissions again before restore attempt
            if not bot_member_after.guild_permissions.manage_roles:
                await log_error(guild, f"Wither restore fail for {member_after.mention}: Bot lost `Manage Roles` permission.")
                # Attempt to notify in channel
                if interaction.channel: await interaction.channel.send(f"⚠️ Failed to restore roles for {member_after.mention}: Bot permissions missing.")
                return

            # Check bot hierarchy again (user might have gotten higher roles)
            if bot_member_after.top_role.position <= member_after.top_role.position:
                await log_error(guild, f"Wither restore fail: Bot hierarchy now too low for {member_after.mention}.")
                if interaction.channel: await interaction.channel.send(f"⚠️ Failed to restore roles for {member_after.mention}: Hierarchy issue.")
                return

            # --- Determine Roles to Restore ---
            # Check existence and hierarchy for each original role again
            valid_restore_roles = [] # Roles that still exist and bot can assign
            skipped_deleted_names = [] # Names of roles that were deleted
            skipped_hierarchy_names = [] # Names of roles now above bot

            original_role_ids = {r.id for r in original_roles} # Set for efficient lookup
            current_valid_roles = {r.id: r for r in guild.roles} # Map of current roles in guild

            for role_id in original_role_ids:
                role_obj = current_valid_roles.get(role_id)
                if not role_obj:
                    # Find original name if possible (might be inaccurate if ID reused)
                    original_name = next((r.name for r in original_roles if r.id == role_id), f"ID {role_id}")
                    skipped_deleted_names.append(original_name)
                elif bot_member_after.top_role.position > role_obj.position:
                    valid_restore_roles.append(role_obj) # Add the valid Role object
                else:
                    skipped_hierarchy_names.append(role_obj.name)

            if skipped_deleted_names: await log_info(guild, f"Wither restore notice for {member_after.name}: Roles seem deleted: {', '.join(skipped_deleted_names)}.")
            if skipped_hierarchy_names: await log_info(guild, f"Wither restore notice for {member_after.name}: Roles skipped (hierarchy): {', '.join(skipped_hierarchy_names)}.")

            if not valid_restore_roles:
                await log_info(guild, f"Wither restore: No valid roles left to restore for {member_after.name}.")
                if interaction.channel: await interaction.channel.send(f"ℹ️ Wither ended for {member_after.mention}, but no valid roles could be restored (deleted or hierarchy issues).")
                return

            # --- Attempt Role Restore ---
            # Combine valid roles to restore with the @everyone role
            final_roles_to_set = valid_restore_roles + [guild.default_role]
            await member_after.edit(roles=final_roles_to_set, reason=reason_restore)

            # --- Send Restore Confirmation ---
            restored_names = (', '.join(f"`{r.name}`" for r in valid_restore_roles))
            restore_msg = f"✨ {member_after.mention}'s roles have been restored!"
            # Add details about skipped roles if any
            if skipped_deleted_names or skipped_hierarchy_names:
                restore_msg += "\n*(Some original roles were not restored due to being deleted or hierarchy issues.)*"

            # Use followup for restore message if original interaction is still valid
            # otherwise send to channel directly.
            try:
                 await interaction.followup.send(embed=create_embed(restore_msg, color=NERDY_YELLOW), ephemeral=False)
            except (discord.NotFound, discord.HTTPException) as e_followup:
                print(f"Wither restore followup failed ({e_followup}), attempting to send to channel.")
                # Fallback to sending in the original channel if followup fails
                if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                    try: await interaction.channel.send(embed=create_embed(restore_msg, color=NERDY_YELLOW))
                    except Exception as e_chan_send: await log_error(guild, "Wither failed channel send after followup fail", error=e_chan_send)
                else: await log_info(guild, f"Wither restore OK for {member_after.mention}, but couldn't send followup or channel message.")

            await log_info(guild, f"Restored roles for `{member_after.name}` ({member_after.id}). Roles: {', '.join(r.name for r in valid_restore_roles)}")

        # --- Inner Except Blocks (Handling Restore Errors) ---
        except discord.NotFound:
            # User left the server during the wither period
            await log_info(guild, f"Wither restore skipped: User `{user.name}` ({user.id}) left the server.")
            # Attempt to notify channel
            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                try: await interaction.channel.send(f"ℹ️ Wither ended for {user.display_name}, but they have left the server.")
                except Exception: pass # Ignore failure to notify
        except discord.Forbidden:
            await log_error(guild, f"Wither restore failed: Forbidden error for {user.name} ({user.id}).")
            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                try: await interaction.channel.send(f"⚠️ Failed to restore roles for {user.display_name}: Permissions error.")
                except Exception: pass
        except discord.HTTPException as e:
            await log_error(guild, f"Wither restore failed: API error for {user.name} ({user.id}).", error=e)
            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                try: await interaction.channel.send(f"⚠️ Failed to restore roles for {user.display_name}: Discord API error.")
                except Exception: pass
        except Exception as e:
            # Catch any other unexpected errors during restore
            await log_error(guild, f"Wither restore failed: Unexpected error for {user.name} ({user.id}).", error=e)
            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                try: await interaction.channel.send(f"⚠️ An unexpected error occurred trying to restore roles for {user.display_name}.")
                except Exception: pass

    # --- Outer Except Blocks (Handling Role Removal Errors) ---
    except discord.Forbidden:
        # This implies the initial role removal failed
        await log_error(guild, f"Wither initial remove failed: Forbidden for {user.name} ({user.id}).", interaction=interaction)
        # Try to edit the deferred response to show failure
        try: await interaction.edit_original_response(content=f"❌ Failed to remove roles for {user.display_name}: Permissions error.", embed=None, view=None)
        except Exception: pass # Ignore if editing fails
    except discord.HTTPException as e:
        await log_error(guild, f"Wither initial remove failed: API error for {user.name} ({user.id}).", error=e, interaction=interaction)
        try: await interaction.edit_original_response(content=f"❌ Failed to remove roles for {user.display_name}: Discord API error.", embed=None, view=None)
        except Exception: pass
    except Exception as e:
        # Catch any other unexpected errors during the initial removal phase
        await log_error(guild, f"Wither initial remove failed: Unexpected error for {user.name} ({user.id}).", error=e, interaction=interaction)
        try: await interaction.edit_original_response(content=f"❌ An unexpected error occurred trying to wither {user.display_name}.", embed=None, view=None)
        except Exception: pass

@bot.event
async def on_message(message: discord.Message):
    # --- Initial Checks (Ignore DMs, ensure bot user is ready) ---
    if not message.guild or not bot.user:
        return

    # --- Auto-Delete Logic ---
    # Check if the message is from the bot itself AND in the target channel
    if message.author.id == bot.user.id and message.channel.id == AUTODELETE_CHANNEL_ID:
        # Check if this message is a response to a slash command interaction
        # This works for interaction.response.send_message and interaction.followup.send
        if message.interaction is not None:
            try:
                # Schedule the deletion using the defined delay
                await message.delete(delay=AUTODELETE_DELAY_SECONDS)
                # Optional: Print log for debugging scheduled deletions
                # print(f"Scheduled auto-delete for bot message {message.id} in channel {message.channel.id}")
            except discord.Forbidden:
                # Log an error ONCE if the bot lacks permissions in that channel
                # You might want a flag to prevent spamming this log
                print(f"ERROR: Cannot auto-delete in channel {message.channel.id}. Bot lacks 'Manage Messages' permission.")
                # Consider logging this via your log_error function too, perhaps less frequently.
            except discord.NotFound:
                pass # Message was likely deleted manually before delay expired
            except discord.HTTPException as e:
                await log_error(message.guild, f"Failed to schedule auto-delete for message {message.id}: HTTP Error.", error=e)
            except Exception as e:
                await log_error(message.guild, f"Unexpected error during auto-delete scheduling for message {message.id}.", error=e)
            finally:
                # IMPORTANT: Return after handling bot's own message to prevent processing as a command
                return

    # --- Prefix Command Logic (e.g., .p) ---
    # Now, handle messages *from users* that start with the command prefix
    if message.author.bot: # Double check we are not processing bot messages here
        return
    if not message.content.startswith(COMMAND_PREFIX):
        # If you used `await bot.process_commands(message)` before, call it here for other potential prefix commands.
        # If ONLY .p exists, you don't need process_commands.
        # await bot.process_commands(message) # Uncomment if using discord.ext.commands framework features
        return
    if not isinstance(message.channel, discord.TextChannel): # Ensure it's a text channel for .p
         return

    # --- Parse Prefix Command ---
    content_without_prefix = message.content[len(COMMAND_PREFIX):].strip()
    parts = content_without_prefix.split()
    if not parts: return
    command_name = parts[0].lower()
    args = parts[1:]

    # --- Handle the '.p' command ---
    if command_name == "p":
        guild = message.guild
        channel = message.channel # Already confirmed TextChannel
        author = message.author # Member object

        # --- PASTE YOUR ENTIRE .p COMMAND LOGIC HERE ---
        # (Starting from the argument check down to the error handling)
        # Example structure:
        # 1. Argument Check (Amount)
        if not args:
            try: await channel.send("❌ Please specify the number of messages to delete (e.g., `.p 10`).", delete_after=5.0)
            except (discord.Forbidden, discord.HTTPException): pass
            return
        # ... (rest of your .p logic: amount parsing, permission checks, purge execution, logging, confirmation delete) ...
        try:
            amount = int(args[0])
            if not 1 <= amount <= 100:
                raise ValueError("Amount out of range.")
        except ValueError:
            try: await channel.send("❌ Invalid amount. Please provide a number between 1 and 100.", delete_after=5.0)
            except (discord.Forbidden, discord.HTTPException): pass
            return

        bot_perms = channel.permissions_for(guild.me)
        user_perms = channel.permissions_for(author)

        if not bot_perms.manage_messages:
            try: await channel.send(f"{author.mention}, I lack the `Manage Messages` permission here.")
            except (discord.Forbidden, discord.HTTPException): pass
            await log_error(guild, f".p command failed in {channel.mention}: Bot missing Manage Messages permission (invoked by {author}).")
            return

        if not user_perms.manage_messages:
            try: await channel.send(f"{author.mention}, you need the `Manage Messages` permission to use this.", delete_after=7.0)
            except (discord.Forbidden, discord.HTTPException): pass
            try: await message.delete()
            except (discord.Forbidden, discord.NotFound, discord.HTTPException): pass
            return

        confirmation_message: Optional[discord.Message] = None
        try:
            try:
                await message.delete()
            except discord.NotFound: pass # Already gone
            except discord.Forbidden: await log_error(guild, f".p: Failed to delete trigger message {message.id} (Forbidden) in {channel.mention}.")
            except discord.HTTPException as e_trig_del: await log_error(guild, f".p: Failed to delete trigger message {message.id} (HTTP Error)", error=e_trig_del)

            deleted_messages = await channel.purge(limit=amount)
            delete_count = len(deleted_messages)

            if delete_count == 0:
                try: confirmation_message = await channel.send("ℹ️ No messages were found to delete.", delete_after=2.0);
                except (discord.Forbidden, discord.HTTPException): pass
                return

            author_counts: Dict[str, int] = {}
            for msg in deleted_messages:
                author_name = str(msg.author)
                author_counts[author_name] = author_counts.get(author_name, 0) + 1
            authors_log = ", ".join(f"{name}({count})" for name, count in author_counts.items())
            if len(authors_log) > 100: authors_log = authors_log[:97]+"..."

            confirm_content = f"🗑️ Deleted {delete_count} message(s). ({authors_log})"
            confirmation_message = await channel.send(confirm_content)

            await log_info(guild, f"`{author}` used .p to delete {delete_count} messages in {channel.mention}. Authors: {authors_log}")

            delete_delay_seconds_p = 1.5 # Use a different variable name if needed
            await asyncio.sleep(delete_delay_seconds_p)

            try:
                if confirmation_message: await confirmation_message.delete()
            except discord.NotFound: pass
            except discord.Forbidden: await log_error(guild, f"Failed to auto-delete .p confirmation message (ID: {confirmation_message.id if confirmation_message else 'N/A'}): Bot Missing Permissions in channel {channel.mention}")
            except discord.HTTPException as e_del_conf: await log_error(guild, f"Failed to auto-delete .p confirmation message (ID: {confirmation_message.id if confirmation_message else 'N/A'}): HTTP Error", error=e_del_conf)

        except discord.Forbidden:
            await log_error(guild, f".p command failed during purge in {channel.mention}: Bot missing Manage Messages permission (Invoked by {author}).")
            try: await channel.send(f"{author.mention}, I lack permissions to delete messages here.")
            except Exception: pass
        except discord.HTTPException as e:
            await log_error(guild, f".p command failed during purge/send in {channel.mention}: HTTP Exception.", error=e)
            try: await channel.send(f"⚠️ Discord API error during purge (HTTP {e.status}). Some messages might not be deletable.", delete_after=7.0)
            except Exception: pass
        except Exception as e:
            await log_error(guild, f".p command failed unexpectedly in {channel.mention}.", error=e)
            if confirmation_message:
                try:
                    await asyncio.sleep(1)
                    await confirmation_message.delete()
                except Exception: pass
        # --- END OF PASTED .p LOGIC ---

# --- MODIFIED Nerd Help Command (Added activatemyself) ---
@tree.command(name="nerdhelp", description="Show the list of available bot commands.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return
    if not bot or not bot.user:
        print("Error: Bot object not available in nerdhelp command.")
        await interaction.response.send_message("Bot is not fully ready, cannot generate help. Please try again shortly.", ephemeral=False)
        return
    if not command_ids:
        print("Warning: command_ids dictionary is empty during nerdhelp execution! Links may not be clickable.")

    embed = discord.Embed(
        title="🤓 Pingslave Bot Commands",
        color=NERDY_YELLOW
    )
    embed.add_field(name="\u200B", value="\u200B", inline=False)

    # Section: Verification & HC Management
    embed.add_field(name="🔑 Verification & HC Management", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('verify')}  · Verify a standard user.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('unverify')}  · Revert a user to unverified.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('hcverify')}  · Verify a user into HC.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('hconly')} · Register member by IGN only.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('hcleave')} · Remove member from HC.", value="\u200B", inline=False)

    # Section: [HC1] Member List
    embed.add_field(name="\u200B\n📊 [HC1] Member List", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('hcmembers')}  · Show interactive HC member list.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('refresh')}  · Refresh the static HC member list.", value="\u200B", inline=False)

    # Section: Activity Tracking
    embed.add_field(name="\u200B\n⏱️ Activity Tracking", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('activatemyself')} · Mark *yourself* as active for today.", value="\u200B", inline=False) # <-- ADDED
    embed.add_field(name=f"{get_cmd_mention('active')}  · Mark *any* member as active for a date.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('inactive')}  · Remove an activity record for a date.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('bulkactive')}  · Mark multiple members active via modal.", value="\u200B", inline=False)

    # Section: Utilities
    embed.add_field(name="\u200B\n⚙️ Utilities", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('syncnicknames')}  · Sync HC nicknames to stored IGNs.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('wither')}  · Temporarily remove user roles.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('nerdhelp')}  · Shows this help message.", value="\u200B", inline=False)

    embed.set_footer(text="Bot by TheNerd | sweet_honey")
    if bot.user and bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)

    try:
        await interaction.response.send_message(embed=embed, ephemeral=False)
    except Exception as e:
        print(f"Error sending nerdhelp response: {e}")
        await log_error(guild, "Failed to send nerdhelp response", error=e, interaction=interaction)
        try:
            if interaction.response.is_done():
                await interaction.followup.send("Failed to generate help embed.", ephemeral=False)
        except Exception: pass

# --- Bot Startup ---
if __name__ == "__main__":
    print("--- Initializing Pingslave Bot ---")
    # Essential checks before starting
    if not TOKEN:
        print("CRITICAL: DISCORD_BOT_TOKEN environment variable not found. Bot cannot start.")
    elif not supabase:
        print("CRITICAL: Supabase client initialization failed. Check URL/Key and connection. Bot may have limited functionality.")
        # Decide if you want the bot to run without Supabase or exit
        # exit(1) # Example: exit if Supabase fails
    else:
        print("Discord Token and Supabase Client OK.")
        print("Starting Keep Alive Flask server...")
        keep_alive() # Starts Flask in a separate thread

        try:
            print("Attempting to start Discord Bot...")
            # --- IMPORTANT: REMOVED log_handler=None ---
            # This allows default discord.py logging to show connection/sync status
            bot.run(TOKEN)
        except discord.LoginFailure:
            # Token is invalid
            print("CRITICAL: Discord Login Failed. The provided DISCORD_BOT_TOKEN is invalid or expired.")
        except discord.PrivilegedIntentsRequired:
            # Member intent is likely missing in Discord Dev Portal settings
            print("CRITICAL: Privileged Intents (Server Members Intent) required but not enabled in the Discord Developer Portal.")
        except Exception as e:
            # Catch any other unexpected errors during startup
            print(f"CRITICAL: Unexpected error during bot execution: {e}")
            print(traceback.format_exc()) # Print full traceback for debugging

    print("--- Bot process has potentially ended (check logs for specific errors) ---")
