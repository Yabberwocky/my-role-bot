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
from discord.ext import tasks
import time # For timestamp comparison if needed, although discord.utils.utcnow() is better

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
TARGET_GUILD_ID = 1200476681803137024 # Catercord server ID
active_static_list_views: Dict[int, Dict[str, Any]] = {} # channel_id -> {'view': StaticHCPagesView, 'message_id': int, 'task': tasks.Loop}
STATIC_LIST_RESET_TIMEOUT_MINUTES = 5
SORT_MODE_DISCORD_NAME = "sort_discord_name"

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

class SelfActivateButton(discord.ui.Button):
    """Button for users to mark themselves active for today."""
    def __init__(self, row: int):
        super().__init__(label="Activate Myself Today", style=discord.ButtonStyle.success, emoji="✅", custom_id="static_activate_self", row=row)

    async def callback(self, interaction: discord.Interaction):
        view: StaticHCPagesView = self.view
        guild = interaction.guild # Should always be the static list's guild

        if not view or not guild:
            await interaction.response.send_message("❌ Cannot perform action: View or Guild context lost.", ephemeral=True)
            return

        # --- Mimic /activatemyself logic ---
        user_id = interaction.user.id
        user_mention = interaction.user.mention

        # Use check_supabase_available helper first
        if not await check_supabase_available(interaction):
             # Helper handles ephemeral message + logging if needed
             return # Stop if DB down

        # 1. Fetch User's IGN
        stored_ign = await get_ign_from_user(guild, user_id)

        if not stored_ign:
            await interaction.response.send_message(
                f"❌ {user_mention}, I couldn't find a linked In-Game Name (IGN) for you in the database. "
                f"Use {get_cmd_mention('hcverify')} or contact an admin.",
                ephemeral=True
            )
            # Don't update last interaction time for view if user can't activate
            return

        # 2. Get Today's Date
        activity_date, date_error = get_utc_date()
        if date_error or not activity_date:
            await interaction.response.send_message(f"❌ Could not determine today's date.", ephemeral=True)
            await log_error(guild, f"SelfActivateButton error: Failed to get today's date ({date_error})", interaction=interaction)
            return

        # 3. Upsert Activity Log
        success, message = await upsert_activity_log(guild, stored_ign, activity_date, user_id)

        prefix = "✅" if success else "⚠️"
        response_msg = f"{prefix} {user_mention}, "
        if success:
            response_msg += f"you've been marked as active for today ({format_date_dmy(activity_date)}) with IGN `{discord.utils.escape_markdown(stored_ign)}`."
            # Update the main view's last interaction time ONLY on success
            view.last_interaction_time = discord.utils.utcnow()
        else:
            response_msg += f"failed to mark you as active: {message.split(': ', 1)[-1]}"

        # Send ephemeral confirmation/error
        await interaction.response.send_message(response_msg, ephemeral=True)

        # 4. Log and Trigger Update (if successful)
        if success:
            await log_info(guild, f"`{interaction.user}` used SelfActivateButton. Marked IGN `{stored_ign}` active for {format_date_dmy(activity_date)}. Triggering list update.")
            # Trigger the main list update task
            asyncio.create_task(update_static_list_message(guild))
            # Note: The view the user is looking at won't immediately reflect the change.
            # The update_static_list_message task will eventually refresh the data and edit the message.

# --- Buttons and Views for the NEW Static List ---

class PingDevButton(discord.ui.Button):
    """Button that pings the developer when clicked."""
    def __init__(self, requesting_user: discord.User, bot_owner_id: int):
        super().__init__(label="Notify Developer!", style=discord.ButtonStyle.success, emoji="📢")
        self.requesting_user = requesting_user
        self.bot_owner_id = bot_owner_id
        self.already_clicked = False # Add a flag to prevent double processing

    async def callback(self, interaction: discord.Interaction):
        # Prevent processing if already clicked (handles potential double-clicks)
        if self.already_clicked:
            try:
                # Just acknowledge the interaction if clicked again quickly
                await interaction.response.defer()
            except discord.InteractionResponded:
                pass # Ignore if already responded
            return
        self.already_clicked = True # Set flag immediately

        # --- 1. Respond to the interaction FIRST ---
        self.disabled = True
        self.label = "Developer Notified"
        try:
            # Try editing the original ephemeral message
            await interaction.response.edit_message(view=self.view)
            print("[PingDevButton] Successfully edited original ephemeral message.")
        except discord.NotFound:
            print("[PingDevButton] Original ephemeral message not found (likely dismissed by user). Skipping edit.")
        except discord.HTTPException as e:
             print(f"[PingDevButton] HTTP Error editing original ephemeral message: {e}. Proceeding with logging.")
             await log_error(interaction.guild, "[PingDevButton] HTTP Error editing original ephemeral message", error=e, interaction=interaction)
        except Exception as e:
             print(f"[PingDevButton] Unknown Error editing original ephemeral message: {e}. Proceeding with logging.")
             await log_error(interaction.guild, "[PingDevButton] Unknown Error editing original ephemeral message", error=e, interaction=interaction)


        # Send the ephemeral confirmation
        try:
            await interaction.followup.send("✅ The developer has been notified of your interest!", ephemeral=True)
            print("[PingDevButton] Successfully sent ephemeral confirmation.")
        except discord.NotFound as e_followup:
            print(f"[PingDevButton] Failed to send ephemeral followup (NotFound - Unknown Webhook): {e_followup}. Interaction likely expired.")
            await log_error(interaction.guild, "[PingDevButton] Failed to send ephemeral followup (NotFound/Unknown Webhook)", error=e_followup, interaction=interaction)
            return
        except discord.HTTPException as e_followup:
             print(f"[PingDevButton] Failed to send ephemeral followup (HTTPException): {e_followup}.")
             await log_error(interaction.guild, "[PingDevButton] Failed to send ephemeral followup (HTTPException)", error=e_followup, interaction=interaction)
        except Exception as e_followup:
             print(f"[PingDevButton] Failed to send ephemeral followup (Unknown): {e_followup}.")
             await log_error(interaction.guild, "[PingDevButton] Failed to send ephemeral followup (Unknown)", error=e_followup, interaction=interaction)


        # --- 2. Perform Logging Action LAST ---
        guild = interaction.guild
        if not guild:
             print("[PingDevButton] Guild object became None before logging.")
             return

        owner_mention = f"<@{self.bot_owner_id}>"
        # --- UPDATED CHANNEL ID ---
        notification_channel_id = 1200476682973364246 # <--- CHANGE HERE

        notification_message = f"User {self.requesting_user.mention} (`{self.requesting_user.id}`) is interested in the 'My Profile' feature!"
        notification_embed = discord.Embed(
            title="Interest Notification: 'My Profile' Feature",
            description=notification_message,
            color=NERDY_YELLOW # Use bot's standard color
        )
        notification_embed.timestamp = discord.utils.utcnow()
        notification_embed.set_footer(text=f"Triggered by: {self.requesting_user}")

        # Call log_to_channel
        try:
            await log_to_channel(
                channel_id=notification_channel_id, # Uses the updated ID
                guild=guild,
                embed=notification_embed,
                ping_mention=owner_mention
            )
            print(f"[PingDevButton] Successfully logged notification to developer channel {notification_channel_id}.")
        except Exception as e_log:
            # Log failure to log
            print(f"[PingDevButton] CRITICAL: Failed to send log notification to developer channel {notification_channel_id}: {e_log}")
            await log_error(guild, f"[PingDevButton] CRITICAL: Failed to send log notification to developer channel {notification_channel_id}", error=e_log)


class MyProfileWIPView(discord.ui.View):
    """View for the ephemeral 'My Profile' WIP message."""
    def __init__(self, requesting_user: discord.User, bot_owner_id: int, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.add_item(PingDevButton(requesting_user, bot_owner_id))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        # We can't edit an ephemeral message after timeout easily, so just let it be.


class InfoButton(discord.ui.Button):
    """Button to toggle the info display on the static list."""
    def __init__(self, is_info_active: bool, row: int):
        label = "Back to List" if is_info_active else "Info / Help"
        style = discord.ButtonStyle.secondary if is_info_active else discord.ButtonStyle.primary
        emoji = "⬅️" if is_info_active else "ℹ️"
        super().__init__(label=label, style=style, emoji=emoji, custom_id="static_toggle_info", row=row)

    async def callback(self, interaction: discord.Interaction):
        view: StaticHCPagesView = self.view
        if view:
            await view.toggle_info_mode(interaction)


class MyProfileButton(discord.ui.Button):
     """Button to show the 'My Profile' WIP message."""
     def __init__(self, row: int):
          super().__init__(label="My Profile", style=discord.ButtonStyle.blurple, emoji="👤", custom_id="static_my_profile", row=row) # Changed style

     async def callback(self, interaction: discord.Interaction):
          view: StaticHCPagesView = self.view
          if view:
               await view.show_my_profile(interaction)

# --- Static List View (New Class, borrows heavily from HCPagesView) ---
# Inherits directly from View, copies logic as needed.
class StaticHCPagesView(View):

    async def update_data_and_refresh(self, new_original_data: List[Dict[str, Any]], new_initial_display_data: List[Dict[str, Any]], new_total_members: int):
        """Updates the view's internal data and refreshes its display."""
        print(f"[Static View {self.message_id}] Updating internal data and refreshing.")
        self.original_data = new_original_data
        self.current_data = new_initial_display_data # Use the new pre-fetched data
        self.total_members = new_total_members

        # Reset state to default view/sort/page
        self.current_page = 0
        self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY
        self.sort_mode = SORT_MODE_ACTIVITY
        self.info_mode_active = False
        self.is_fetching_activity = False # Ensure lock is released

        self.sort_data() # Sort the new initial data

        # Recalculate total pages
        self.total_pages = math.ceil(len(self.current_data) / MEMBERS_PER_PAGE) if self.current_data else 1

        # Now, edit the message with the updated state
        if self.message_id and self.guild:
            channel = self.guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
            if channel and isinstance(channel, discord.TextChannel):
                 try:
                      message = await channel.fetch_message(self.message_id)
                      await self.edit_message(message=message) # Use the internal edit method
                      self.last_interaction_time = discord.utils.utcnow() # Update timestamp on successful refresh
                 except discord.NotFound:
                      print(f"[Static View Update] Message {self.message_id} not found during data update. Stopping view.")
                      self.stop()
                      if self.guild.id in active_static_list_views: del active_static_list_views[self.guild.id]
                 except Exception as e:
                      print(f"[Static View Update] Error editing message {self.message_id} during data update: {e}")
                      await log_error(self.guild, f"Static View: Error editing message {self.message_id} during data update", error=e)
            else:
                 print(f"[Static View Update] Could not find channel {HC_MEMBER_LIST_CHANNEL_ID} during data update.")
        else:
             print("[Static View Update] Cannot edit message: Missing message ID or guild context.")

    # Data is List[Dict[str, Any]] from fetch_hc_member_data (includes ALL-TIME activity)
    def __init__(self, original_data: List[Dict[str, Any]], initial_display_data: List[Dict[str, Any]], total_members: int, guild: discord.Guild, message_id: Optional[int] = None, timeout=None): # NO TIMEOUT BY DEFAULT!
        super().__init__(timeout=timeout) # Timeout managed by external task + reset
        self.original_data = original_data # Holds base data + all-time activity
        self.current_data = initial_display_data # Use the passed initial data <--- CHANGE HERE
        self.total_members = total_members
        self.current_page = 0
        self.message_id: Optional[int] = message_id # Store message ID
        self.guild = guild
        self.is_target_guild = True # Static list is always in the target guild
        self.bot_owner_id = SELF_PROTECTED_ID # Needed for PingDev button

        # --- State ---
        self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY # Default view
        self.sort_mode = SORT_MODE_ACTIVITY       # Default sort for activity
        self.info_mode_active = False             # Is the info embed being shown?
        self.is_fetching_activity = False         # Lock for data fetches
        self.last_interaction_time = discord.utils.utcnow() # Track last interaction

        # --- Initial Sort (using the pre-fetched initial_display_data) ---
        self.sort_data() # Sorts self.current_data

        # --- Recalculate total pages AFTER initial sort and data load ---
        self.total_pages = math.ceil(len(self.current_data) / MEMBERS_PER_PAGE) if self.current_data else 1

        # --- Add UI Elements ---
        self.update_ui_elements() # Centralized method to add/remove/update items

    # --- Methods copied/adapted from HCPagesView ---

    async def fetch_and_set_data_for_mode(self, mode: str, start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None): # <--- Added async
        """Fetches activity if needed and sets self.current_data. Now ASYNC."""
        print(f"[Static View] Async setting data for mode: {mode}")

        # Determine date range based on mode (if not provided)
        if start_date is None and end_date is None:
             today_utc = datetime.datetime.now(pytz.utc).date()
             if mode == VIEW_MODE_ACTIVITY_DAILY:
                 start_date = end_date = today_utc
             elif mode == VIEW_MODE_ACTIVITY_WEEKLY:
                 end_date = today_utc
                 start_date = today_utc - datetime.timedelta(days=6)
             elif mode == VIEW_MODE_ACTIVITY_MONTHLY:
                 end_date = today_utc
                 start_date = today_utc - datetime.timedelta(days=29)

        # Fetch and Update Data
        if mode in [VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
            all_igns = [item['ign'] for item in self.original_data if item.get('ign')]
            if not all_igns:
                print("[Static View] No IGNs found in original data.")
                self.current_data = list(self.original_data) # Reset to original
                return

            try:
                 # Directly await the async fetch function
                 ranged_activity_data = await fetch_activity_data(self.guild, all_igns, start_date, end_date) # <--- CHANGE HERE

            except Exception as e:
                  print(f"[Static View] Error fetching activity data: {e}")
                  await log_error(self.guild, f"Static View: Error fetching activity data for mode {mode}", error=e) # Log error
                  self.current_data = list(self.original_data) # Fallback
                  return


            temp_data = []
            for item in self.original_data:
                ign_lower = item.get('ign', '').lower()
                activity_info = ranged_activity_data.get(ign_lower, {'count': 0, 'last_seen': None})
                updated_item = item.copy()
                updated_item['activity_count'] = activity_info['count']
                updated_item['last_seen'] = activity_info['last_seen']
                temp_data.append(updated_item)
            self.current_data = temp_data
            print(f"[Static View] Updated current_data with ranged activity.")

        elif mode == VIEW_MODE_ACTIVITY_ALL:
            self.current_data = list(self.original_data) # Use all-time data from original fetch
            print("[Static View] Set to All-Time activity view.")
        else: # VIEW_MODE_DISCORD
            self.current_data = list(self.original_data)
            print("[Static View] Set to Discord view.")

    def sort_data(self):
        """Sorts self.current_data based on self.sort_mode."""
        stored_page = self.current_page

        if self.view_mode == VIEW_MODE_DISCORD:
            if self.sort_mode == SORT_MODE_DISCORD_NAME:
                # Sort by Discord name (case-insensitive), push None members ('[No Discord]') last
                def sort_key_discord(item):
                    member = item.get('member')
                    db_name = item.get('discord_name')
                    if member:
                        # Use name and discriminator for uniqueness
                        key_part = (member.name.lower(), member.discriminator)
                        is_none_equivalent = False
                    elif db_name:
                        key_part = (db_name.lower(),) # Sort by stored name if no member object
                        is_none_equivalent = False
                    else:
                        key_part = ('zzz',) # Fallback sorting value
                        is_none_equivalent = True
                    # Tuple key: (is_none, actual_name_parts...)
                    return (is_none_equivalent, key_part)
                self.current_data.sort(key=sort_key_discord)

            else: # Default to IGN sort in Discord view if sort_mode isn't discord_name
                self.current_data.sort(key=lambda item: item.get('ign', 'zzz').lower())

        elif self.sort_mode == SORT_MODE_ACTIVITY: # Activity views
            # Sort descending by count, then ascending by IGN as tie-breaker
            self.current_data.sort(key=lambda item: (item.get('activity_count', 0) * -1, item.get('ign', 'zzz').lower()))
        else: # Default to IGN sort for Activity views if sort_mode isn't activity
             self.current_data.sort(key=lambda item: item.get('ign', 'zzz').lower())


        self.total_pages = math.ceil(len(self.current_data) / MEMBERS_PER_PAGE) if self.current_data else 1
        self.current_page = min(stored_page, max(0, self.total_pages - 1))


    def update_ui_elements(self):
        """Clears and re-adds UI elements based on the current state."""
        self.clear_items() # Remove all existing items

        if self.info_mode_active:
            # Only show the "Back" button in info mode
            self.add_item(InfoButton(is_info_active=True, row=0))
        else:
            # --- UPDATED ROW LAYOUT ---
            # Row 0: Navigation
            self.add_item(discord.ui.Button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="static_prev", row=0, disabled=self.current_page == 0 or self.is_fetching_activity))
            self.add_item(discord.ui.Button(label="Next", style=discord.ButtonStyle.blurple, custom_id="static_next", row=0, disabled=self.current_page >= self.total_pages - 1 or self.is_fetching_activity))

            # Row 1: Sorting & Info
            sort_button_disabled = self.is_fetching_activity # Base condition

            if self.view_mode == VIEW_MODE_DISCORD:
                # Toggle between IGN and Discord Name sort in Discord view mode
                sort_label = "Sort by IGN" if self.sort_mode == SORT_MODE_DISCORD_NAME else "Sort by Discord Name"
                # Sort button is generally enabled in Discord view unless fetching
            else:
                # Toggle between IGN and Activity sort in Activity view modes
                sort_label = "Sort by IGN" if self.sort_mode == SORT_MODE_ACTIVITY else "Sort by Activity"
                # Disable sort button if fetching OR if not in an activity view (redundant but safe)
                # sort_button_disabled = sort_button_disabled or self.view_mode == VIEW_MODE_DISCORD # This line is actually not needed here as Discord view handled above

            self.add_item(discord.ui.Button(label=sort_label, style=discord.ButtonStyle.success, custom_id="static_toggle_sort", row=1, disabled=sort_button_disabled))
            self.add_item(InfoButton(is_info_active=False, row=1))

            # Row 2: Actions (Self Activate & My Profile)
            self.add_item(SelfActivateButton(row=2))
            self.add_item(MyProfileButton(row=2))

            # Row 3: View Mode Select (Moved to bottom)
            options = [
               discord.SelectOption(label="View Discord Names + IGN", value=VIEW_MODE_DISCORD, description="Show Discord usernames and IGNs.", emoji="👤"),
               discord.SelectOption(label="View Activity (Today)", value=VIEW_MODE_ACTIVITY_DAILY, description="Show IGNs active today.", emoji="📅"),
               discord.SelectOption(label="View Activity (Last 7 Days)", value=VIEW_MODE_ACTIVITY_WEEKLY, description="Show IGNs active in the last week.", emoji="📅"),
               discord.SelectOption(label="View Activity (Last 30 Days)", value=VIEW_MODE_ACTIVITY_MONTHLY, description="Show IGNs active in the last 30 days.", emoji="📅"),
               discord.SelectOption(label="View Activity (All-Time)", value=VIEW_MODE_ACTIVITY_ALL, description="Show IGNs and total activity count.", emoji="📊"),
            ]
            # Ensure the current mode is set as default
            for option in options: option.default = option.value == self.view_mode
            self.add_item(discord.ui.Select(placeholder="Select View Mode...", min_values=1, max_values=1, options=options, custom_id="static_view_select", row=3, disabled=self.is_fetching_activity))


    def create_page_embed(self) -> discord.Embed:
        """Creates embed based on current view_mode, sort_mode, and page."""
        # --- Info Mode Embed ---
        if self.info_mode_active:
             # --- ENSURE THIS DESCRIPTION IS CORRECT ---
             info_description = (
                 "This is an interactive list of members in the **[HC1]** Florr.io guild.\n\n"
                 "**Features:**\n"
                 f"• **Pagination:** Use `Previous`/`Next` buttons.\n"
                 f"• **View Modes:** Use the dropdown to see different activity periods (Today, 7/30 days, All-Time) or Discord names.\n"
                 f"• **Sorting:** Toggle between sorting by IGN (A-Z) or Activity (most active first) using the `Sort by...` button (only in Activity views).\n"
                 f"• **Actions:** Use `Activate Myself Today` or check the WIP `My Profile`.\n\n" # Added Activate Myself here
                 f"**Activity Tracking:**\n"
                 f"• Activity means a member was marked present on a given day using {get_cmd_mention('active')}, {get_cmd_mention('a')}, {get_cmd_mention('bulkactive')} or {get_cmd_mention('activatemyself')}.\n"
                 f"• The `Activity` column shows: `Count (Last Seen DD/MM/YY)` within the selected view period.\n\n"
                 f"*This message automatically resets to the default view ({VIEW_MODE_ACTIVITY_MONTHLY.replace('_view','')}) after {STATIC_LIST_RESET_TIMEOUT_MINUTES} minutes of inactivity.*\n"
             )
             embed = discord.Embed(
                  title=f"ℹ️ About the {HC_LIST_EMBED_TITLE} List",
                  description=info_description, # Use the variable here
                  color=NERDY_YELLOW # Use bot's standard color
             )
             current_unix_ts = int(discord.utils.utcnow().timestamp())
             embed.set_footer(text=f"Info Mode | Updated: <t:{current_unix_ts}:R>")
             return embed

        # --- Standard Page Embed (Copied/Adapted from HCPagesView) ---
        # ... (rest of the standard page embed logic remains the same) ...
        start = self.current_page * MEMBERS_PER_PAGE
        page_data = self.current_data[start : start + MEMBERS_PER_PAGE]

        IDX_WIDTH = 3
        if self.view_mode == VIEW_MODE_DISCORD:
             NAME_WIDTH = 18; IGN_WIDTH = 15; ACT_WIDTH = 0
             TOTAL_WIDTH = IDX_WIDTH + NAME_WIDTH + IGN_WIDTH
             header = (f"{'#':<{IDX_WIDTH}}{'Discord (Stored)':<{NAME_WIDTH}}{'In-Game':<{IGN_WIDTH}}")
        elif self.view_mode in [VIEW_MODE_ACTIVITY_ALL, VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
             IGN_WIDTH = 20; ACT_WIDTH = ACTIVITY_COLUMN_WIDTH
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
                ign = item_dict.get('ign', 'Unknown')
                if self.view_mode == VIEW_MODE_DISCORD:
                    member = item_dict.get('member') # May be None if fetched via Supabase only
                    if member: user_display = f"{member.name}#{member.discriminator}" if member.discriminator != '0' else member.name
                    else: user_display = item_dict.get('discord_name') or "[No Discord]"
                    ign_display = ign
                    if len(user_display) > NAME_WIDTH: user_display = user_display[:NAME_WIDTH-1] + "…"
                    if len(ign_display) > IGN_WIDTH: ign_display = ign_display[:IGN_WIDTH-1] + "…"
                    line = (f"{str(idx)+'.':<{IDX_WIDTH}}{user_display:<{NAME_WIDTH}}{ign_display:<{IGN_WIDTH}}")
                elif self.view_mode in [VIEW_MODE_ACTIVITY_ALL, VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
                    activity_count = item_dict.get('activity_count', 0)
                    last_seen_date = item_dict.get('last_seen') # date object or None
                    ign_display = ign
                    activity_display = f"{activity_count} ({format_date_dmy(last_seen_date)})"
                    if len(ign_display) > IGN_WIDTH: ign_display = ign_display[:IGN_WIDTH-1] + "…"
                    if len(activity_display) > ACT_WIDTH: activity_display = activity_display[:ACT_WIDTH-1] + "…"
                    line = (f"{str(idx)+'.':<{IDX_WIDTH}}{ign_display:<{IGN_WIDTH}}{activity_display:<{ACT_WIDTH}}")
                else: line = f"{str(idx)+'.':<{IDX_WIDTH}} Error: Invalid View Mode"
                desc_lines.append(line)
                idx += 1
            desc_lines.append("```")

        # Use the standard title
        title = HC_LIST_EMBED_TITLE

        embed = discord.Embed(
            title=title,
            description="\n".join(desc_lines),
            color=NERDY_YELLOW
        )

        sort_text = "IGN" if self.sort_mode == SORT_MODE_IGN else "Activity"
        view_text_map = { VIEW_MODE_DISCORD: "Discord+IGN", VIEW_MODE_ACTIVITY_ALL: "Activity (All)", VIEW_MODE_ACTIVITY_DAILY: "Activity (Today)", VIEW_MODE_ACTIVITY_WEEKLY: "Activity (7d)", VIEW_MODE_ACTIVITY_MONTHLY: "Activity (30d)" }
        view_text = view_text_map.get(self.view_mode, "Unknown View")
        current_unix_ts = int(discord.utils.utcnow().timestamp())
        footer_text = (
            f"Page {self.current_page + 1}/{self.total_pages} | Total: {self.total_members} | "
            f"View: {view_text} | Sort: {sort_text}"
        )
        if self.is_fetching_activity: footer_text += " | Fetching data..."
        footer_text += f" | Updated: <t:{current_unix_ts}:R>"
        embed.set_footer(text=footer_text)
        return embed

    async def edit_message(self, interaction: Optional[discord.Interaction] = None, message: Optional[discord.Message] = None):
        """Updates the message embed and view components. Needs either interaction or message."""
        if not interaction and not message:
            print("[Static View] Error: edit_message called without interaction or message.")
            return

        self.update_ui_elements() # Update button states etc. *before* creating embed
        embed = self.create_page_embed()

        try:
            if interaction:
                await interaction.response.edit_message(embed=embed, view=self)
            elif message:
                await message.edit(embed=embed, view=self)
        except discord.NotFound:
            print(f"[Static View] Paginator edit fail: Interaction {interaction.id if interaction else 'N/A'} or message {message.id if message else 'N/A'} not found.")
            self.stop()
            # Also remove from global tracking if message is gone
            if self.guild and self.message_id:
                 if self.guild.id in active_static_list_views and active_static_list_views[self.guild.id]['message_id'] == self.message_id:
                      del active_static_list_views[self.guild.id]
                      print(f"[Static View] Removed view tracking for message {self.message_id} as it was not found.")

        except discord.HTTPException as e:
            # Avoid logging interaction cancelled errors if user was quick
            if interaction and e.code == 10062: # Unknown Interaction
                 pass
            else:
                 ctx = f"Interaction: {interaction.id}" if interaction else f"Message: {message.id}"
                 await log_error(self.guild, f"Static list Paginator edit fail (HTTP {e.status})", error=e) # Removed interaction=interaction if it might be invalid
        except Exception as e:
             ctx = f"Interaction: {interaction.id}" if interaction else f"Message: {message.id}"
             await log_error(self.guild, f"Static list Paginator edit fail (General) for {ctx}", error=e)

    async def update_view(self, interaction: discord.Interaction):
        """Central handler for most interactions."""
        if self.is_fetching_activity:
            await interaction.response.defer() # Ack if fetching
            return
        self.last_interaction_time = discord.utils.utcnow() # Update timestamp
        await self.edit_message(interaction)

    # --- Interaction Callbacks ---
    # Use interaction_check to update timestamp? Or do it in each callback. Let's do it in each.

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="static_prev", row=0)
    async def previous_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0 and not self.is_fetching_activity:
            self.current_page -= 1
            await self.update_view(interaction)
        else:
            await interaction.response.defer() # Ack the interaction

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple, custom_id="static_next", row=0)
    async def next_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1 and not self.is_fetching_activity:
            self.current_page += 1
            await self.update_view(interaction)
        else:
            await interaction.response.defer() # Ack

    @discord.ui.button(label="Sort by Activity/IGN", style=discord.ButtonStyle.success, custom_id="static_toggle_sort", row=1)
    async def sort_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_fetching_activity:
            await interaction.response.defer()
            return # Don't update last interaction time if fetching

        self.last_interaction_time = discord.utils.utcnow() # Update timestamp

        if self.view_mode == VIEW_MODE_DISCORD:
            # Toggle between Discord Name and IGN sort
            self.sort_mode = SORT_MODE_IGN if self.sort_mode == SORT_MODE_DISCORD_NAME else SORT_MODE_DISCORD_NAME
        else:
            # Toggle between Activity and IGN sort for Activity views
             if self.sort_mode == SORT_MODE_IGN:
                 self.sort_mode = SORT_MODE_ACTIVITY
             else:
                 self.sort_mode = SORT_MODE_IGN

        self.sort_data() # Re-sort the current data
        await self.edit_message(interaction) # Update the message

    @discord.ui.select(placeholder="Select View Mode...", min_values=1, max_values=1, custom_id="static_view_select", row=2) # Options added in update_ui_elements
    async def view_select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        new_mode = select.values[0]
        if self.view_mode == new_mode or self.is_fetching_activity:
            await interaction.response.defer()
            return

        self.last_interaction_time = discord.utils.utcnow() # Update timestamp
        self.is_fetching_activity = True
        self.view_mode = new_mode
        await self.edit_message(interaction) # Show loading state

        try:
            # Directly await the now async method
            await self.fetch_and_set_data_for_mode(new_mode) # <--- CHANGE HERE

            # Set appropriate sort mode for the new view
            self.sort_mode = SORT_MODE_IGN if new_mode == VIEW_MODE_DISCORD else SORT_MODE_ACTIVITY
            self.sort_data() # Sort the newly updated data

        except Exception as e:
            await log_error(self.guild, f"Error changing static list view mode to {new_mode}", error=e, interaction=interaction)
            # Reset to a safe state
            self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY
            # Await the async method here too for reset
            await self.fetch_and_set_data_for_mode(self.view_mode) # <--- CHANGE HERE
            self.sort_mode = SORT_MODE_ACTIVITY
            self.sort_data()
            try: await interaction.followup.send("❌ Error fetching data for view.", ephemeral=True)
            except Exception: pass # Ignore if followup fails
        finally:
            self.is_fetching_activity = False
            # Edit message one last time to remove loading state and show final data
            try:
                 await self.edit_message(interaction=interaction)
            except discord.NotFound:
                 print("[Static View] Interaction expired before final view mode edit.")
                 if self.message_id:
                     try:
                         # Ensure channel is valid before fetching
                         if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                            msg = await interaction.channel.fetch_message(self.message_id)
                            await self.edit_message(message=msg)
                         elif self.guild: # Fallback to fetching channel from guild if interaction context lost
                             list_channel = self.guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
                             if list_channel and isinstance(list_channel, discord.TextChannel):
                                 msg = await list_channel.fetch_message(self.message_id)
                                 await self.edit_message(message=msg)
                             else:
                                 print(f"[Static View] Could not get channel {HC_MEMBER_LIST_CHANNEL_ID} to edit message {self.message_id}")
                         else:
                            print(f"[Static View] Could not get channel context to edit message {self.message_id}")

                     except Exception as e_fetch_edit:
                         print(f"[Static View] Failed to fetch/edit message {self.message_id} after interaction expired: {e_fetch_edit}")

    # --- NEW Callbacks for Info and My Profile ---

    async def toggle_info_mode(self, interaction: discord.Interaction):
        """Callback for the InfoButton."""
        self.last_interaction_time = discord.utils.utcnow() # Update timestamp
        self.info_mode_active = not self.info_mode_active
        await self.edit_message(interaction)

    async def show_my_profile(self, interaction: discord.Interaction):
        """Callback for the MyProfileButton."""
        wip_message = (
             f"👋 Hey {interaction.user.mention}!\n\n"
             "The **My Profile** feature is still under construction 🚧.\n\n"
             "It will eventually show your personal stats like activity history, verification date, etc.\n\n"
             "Thanks for your interest! Click the button below if you'd like to let the developer know you're waiting eagerly for this feature."
        )
        # --- UPDATED EMBED COLOR ---
        wip_embed = discord.Embed(description=wip_message, color=NERDY_YELLOW)
        wip_view = MyProfileWIPView(requesting_user=interaction.user, bot_owner_id=self.bot_owner_id)
        await interaction.response.send_message(embed=wip_embed, view=wip_view, ephemeral=True)


    # --- Timeout and Reset ---
    async def on_timeout(self):
        # Standard view timeout (if set, e.g., for ephemeral views)
        # For the persistent static view, timeout is handled by the external task.
        # However, if this view *were* to timeout (e.g., bot restarted and didn't resume), disable items.
        print(f"[Static View] Default on_timeout triggered for view on message {self.message_id}. Disabling items.")
        self.update_ui_elements() # Refresh to get all items
        for item in self.children:
             if hasattr(item, 'disabled'):
                  item.disabled = True
        # Try to edit the message one last time (might fail)
        if self.message_id and self.guild:
            try:
                 channel = self.guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
                 if channel:
                      message = await channel.fetch_message(self.message_id)
                      await message.edit(view=self)
            except Exception as e:
                 print(f"[Static View] Error editing message on standard timeout: {e}")
        self.stop() # Stop the view instance


    async def reset_view(self):
        """Resets the view state to default (called by background task)."""
        print(f"[Static View] Resetting view state for message {self.message_id} due to inactivity.")
        self.current_page = 0
        self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY
        self.sort_mode = SORT_MODE_ACTIVITY # Default sort for activity view
        self.info_mode_active = False
        self.is_fetching_activity = True # Prevent interactions during reset fetch

        # Ensure we have a valid guild and channel
        if not self.guild:
             print("[Static View] Reset Error: Guild object is None.")
             self.is_fetching_activity = False
             return
        channel = self.guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
             print(f"[Static View] Reset Error: Channel {HC_MEMBER_LIST_CHANNEL_ID} not found or not TextChannel.")
             self.is_fetching_activity = False
             return

        # --- Refetch Data and Update ---
        message_to_edit = None
        success = False # Flag to track success
        try:
             # Directly await the async method to fetch data for the default mode
             await self.fetch_and_set_data_for_mode(self.view_mode)
             self.sort_data() # Sort the newly fetched default data

             # Fetch the message to edit
             if self.message_id:
                  message_to_edit = await channel.fetch_message(self.message_id)

        except discord.NotFound:
             print(f"[Static View] Reset Error: Message {self.message_id} not found. Stopping tracking.")
             # Remove from global tracking
             if self.guild.id in active_static_list_views:
                 # Add check if key exists before deleting
                 if channel.id in active_static_list_views:
                     del active_static_list_views[channel.id]
             self.stop()
             return # Don't proceed if message is gone
        except Exception as e:
             print(f"[Static View] Reset Error during data fetch or message fetch: {e}")
             await log_error(self.guild, "[Static View] Reset Error during data/message fetch", error=e) # Log error
             self.is_fetching_activity = False # Release lock even on error
             return # Stop reset if data fetch failed critically
        finally:
             # Ensure lock is always released unless we returned early
             self.is_fetching_activity = False # Release lock

        # --- Edit the Message ---
        if message_to_edit:
             try:
                  await self.edit_message(message=message_to_edit)
                  print(f"[Static View] Successfully reset and edited message {self.message_id}.")
                  self.last_interaction_time = discord.utils.utcnow() # Update timestamp on successful reset
                  success = True
             except discord.NotFound:
                # Message disappeared between fetch and edit
                print(f"[Static View] Reset Error: Message {self.message_id} not found during final edit. Stopping tracking.")
                if self.guild.id in active_static_list_views:
                     if channel.id in active_static_list_views:
                        del active_static_list_views[channel.id]
                self.stop()
             except Exception as e_edit:
                  print(f"[Static View] Reset Error: Failed to edit message {self.message_id} after reset: {e_edit}")
                  await log_error(self.guild, f"[Static View] Failed to edit message {self.message_id} after reset", error=e_edit) # Log error
        else:
             print(f"[Static View] Reset Warning: message_to_edit object was None, could not finalize reset edit.")

        # Optional: return success status if needed elsewhere
        # return success

async def fetch_all_supabase_hc_data(guild_for_log: Optional[discord.Guild]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fetches ALL HC member data directly from Supabase (IGN, Discord ID/Name)
    and correlates with ALL activity data. Used when Discord context is unavailable/irrelevant.
    Returns a list of dicts: [{'discord_id': str | None, 'discord_name': str | None, 'ign': str, 'activity_count': int, 'last_seen': date | None}]
    and the total count. Sorted by IGN case-insensitive.
    """
    print("Fetch All Supabase Data: Starting fetch...")
    if not supabase:
        await log_error(guild_for_log, "fetch_all_supabase_hc_data failed: Supabase client unavailable.", ping_owner=True)
        return [], 0

    # 1. Fetch all members from hc_members table
    all_members_data = []
    try:
        print("Fetch All Supabase Data: Fetching all from hc_members...")
        resp_members = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("discord_id, discord_name, ingame_name")
                           .execute()
        )
        if resp_members and hasattr(resp_members, 'data') and resp_members.data:
            all_members_data = resp_members.data
            print(f"Fetch All Supabase Data: Found {len(all_members_data)} total entries in hc_members.")
        else:
            print("Fetch All Supabase Data: No data returned from hc_members.")
            # No need to fetch activity if no members found
            return [], 0

    except (ConnectionError, APIError, Exception) as e:
        await log_error(guild_for_log, "Failed to fetch all data from Supabase hc_members", error=e, ping_owner=True)
        return [], 0 # Return empty on critical DB failure

    # 2. Fetch all activity data
    activity_summary: Dict[str, Dict[str, Any]] = {} # ign_lower -> {'count': int, 'last_seen': date}
    all_igns_in_db = [entry['ingame_name'] for entry in all_members_data if entry.get('ingame_name')]

    if not all_igns_in_db:
         print("Fetch All Supabase Data: No IGNs found in fetched member data. Skipping activity fetch.")
    else:
        print(f"Fetch All Supabase Data: Fetching all-time activity for {len(all_igns_in_db)} IGNs...")
        try:
            # Use fetch_activity_data with no date range to get all-time counts/last_seen
            activity_summary = await fetch_activity_data(guild_for_log, all_igns_in_db)
            print(f"Fetch All Supabase Data: Fetched activity summary for {len(activity_summary)} IGNs.")
        except Exception as e_act:
             # Log error but proceed, activity will be 0
             await log_error(guild_for_log, "Failed during all-time activity fetch in fetch_all_supabase_hc_data", error=e_act, ping_owner=True)


    # 3. Combine Member and Activity Data
    final_data: List[Dict[str, Any]] = []
    for member_entry in all_members_data:
        ign = member_entry.get("ingame_name")
        if not ign: continue # Skip entries without an IGN (shouldn't happen based on fetch)

        ign_lower = ign.lower()
        activity = activity_summary.get(ign_lower, {'count': 0, 'last_seen': None})

        final_data.append({
            "discord_id": member_entry.get("discord_id"), # Can be None
            "discord_name": member_entry.get("discord_name"), # Can be None
            "ign": ign,
            "activity_count": activity.get('count', 0),
            "last_seen": activity.get('last_seen') # date object or None
            # No 'member' object here
        })

    # 4. Sort by IGN (case-insensitive) as default
    final_data.sort(key=lambda item: item['ign'].lower())

    total_members = len(final_data)
    print(f"Fetch All Supabase Data: Finished. Total entries prepared: {total_members}.")
    return final_data, total_members

async def activity_date_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Provides autocomplete choices for activity dates: Today, Yesterday, Last 7 days (D/M/YYYY format)."""
    choices = []
    today = datetime.datetime.now(pytz.utc).date()
    yesterday = today - datetime.timedelta(days=1)

    # Helper to format date as D/M/YYYY for display name
    def format_dmy_no_zero(date_obj: datetime.date) -> str:
        return f"{date_obj.day}/{date_obj.month}/{date_obj.year}"

    # --- Add Shortcuts ---
    # Name uses new format, Value remains YYYY-MM-DD
    choices.append(app_commands.Choice(name=f"Today ({format_dmy_no_zero(today)})", value=today.isoformat()))
    choices.append(app_commands.Choice(name=f"Yesterday ({format_dmy_no_zero(yesterday)})", value=yesterday.isoformat()))

    # --- Add Last 7 Days ---
    for i in range(2, 8): # Days 2 to 7 ago
        past_date = today - datetime.timedelta(days=i)
        # Name uses new format, Value remains YYYY-MM-DD
        choices.append(app_commands.Choice(name=format_dmy_no_zero(past_date), value=past_date.isoformat()))

    # --- Filtering (Remains the same) ---
    filtered_choices = [
        choice for choice in choices
        if current.lower() in choice.name.lower() or current in choice.value
    ]

    # Return up to 25 choices
    return filtered_choices[:25]

async def check_activity_exists(guild: discord.Guild, ign_lower: str, activity_date: datetime.date) -> Optional[bool]:
    """
    Checks if an activity log entry exists for a given lowercase IGN and date.
    Returns True if exists, False if not, None on error.
    """
    if not supabase:
        await log_error(guild, f"check_activity_exists failed: Supabase unavailable for IGN {ign_lower}.")
        return None # Indicate error

    try:
        # Select a minimal column, check if any row matches
        resp = await run_supabase_sync(
            lambda: supabase.table("activity_log")
                           .select("activity_date", count='exact') # Select a small column, count needed
                           .eq("member_identifier", ign_lower)
                           .eq("activity_date", activity_date.isoformat())
                           .limit(1) # Only need to know if at least one exists
                           .execute()
        )

        # Check the count attribute in the response
        return resp.count is not None and resp.count > 0

    except (APIError, ConnectionError, Exception) as e:
        # Log the error but return None to signal check failure
        await log_error(guild, f"Error checking activity existence for IGN '{ign_lower}' on {activity_date}", error=e)
        return None # Indicate error

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
        potential_igns = [part.strip() for line in raw_text.split('\n') for part in line.replace(',', ' ').split(' ') if part.strip()]

        if not potential_igns:
            await interaction.followup.send("❌ No IGNs were entered.", ephemeral=False)
            return

        # --- NEW Counters and Lists ---
        processed_count = 0
        newly_added_count = 0
        already_marked_count = 0
        failed_count = 0
        check_failed_count = 0 # Count how many existence checks failed

        newly_added_igns = []
        already_marked_igns = []
        failed_igns = [] # Format: "`IGN` (Reason)"
        check_failed_igns = [] # IGNs where the existence check itself failed

        log_details = []
        # --- END NEW ---

        progress_msg = await interaction.followup.send(f"⏳ Processing {len(potential_igns)} IGNs for {format_date_dmy(activity_date)}...", ephemeral=False)

        for current_ign in potential_igns:
            processed_count += 1
            if not current_ign: continue # Skip empty

            ign_lower = current_ign.lower() # Use lowercase for checks and upsert

            # --- Check if activity already exists ---
            exists = await check_activity_exists(guild, ign_lower, activity_date)

            if exists is True:
                # Record already exists
                already_marked_count += 1
                already_marked_igns.append(f"`{current_ign}`")
                log_details.append(f"Skip (Exists): {current_ign}")
                continue # Skip the upsert call

            elif exists is False:
                # Record does not exist, proceed with upsert
                success, msg = await upsert_activity_log(guild, current_ign, activity_date, interaction.user.id) # Pass original case to upsert if needed, though upsert likely lowercases too

                if success:
                    newly_added_count += 1
                    newly_added_igns.append(f"`{current_ign}`")
                    log_details.append(f"OK (Added): {current_ign}")
                else:
                    failed_count += 1
                    # Extract reason more robustly if possible, fallback to full message
                    reason = msg.split(':', 1)[-1].strip() if ':' in msg else msg
                    failed_igns.append(f"`{current_ign}` ({reason})")
                    log_details.append(f"Fail (Upsert): {current_ign} ({msg})")

            else: # exists is None (check failed)
                check_failed_count += 1
                check_failed_igns.append(f"`{current_ign}`")
                log_details.append(f"Fail (Check): {current_ign}")
                # Treat check failure as an overall failure for this IGN
                failed_count += 1 # Also increment failed count
                failed_igns.append(f"`{current_ign}` (DB Check Error)")


            # Optional: Update progress message periodically
            # if processed_count % 10 == 0:
            #     try: await progress_msg.edit(content=f"⏳ Processing... ({processed_count}/{len(potential_igns)})")
            #     except discord.HTTPException: pass

        # --- Final Feedback ---
        total_failures = failed_count # Combines upsert failures and check failures

        if total_failures == 0 and newly_added_count > 0:
             summary_title = "✅ Bulk Activity Update Successful"
             final_color = NERDY_YELLOW # Or Green
        elif total_failures == 0 and newly_added_count == 0:
             summary_title = "ℹ️ Bulk Activity Update: No Changes Needed"
             final_color = discord.Color.blue()
        else:
             summary_title = "⚠️ Bulk Activity Update Partially Complete"
             final_color = discord.Color.orange()

        summary_desc = [
            f"Date Processed: **{format_date_dmy(activity_date)}**",
            f"Total Submitted: {len(potential_igns)}",
            f"---", # Separator
            f"✅ **Newly Added:** {newly_added_count}",
            f"⏭️ **Already Marked (Skipped):** {already_marked_count}",
            f"❌ **Failed / Check Error:** {total_failures}",
            f"---" # Separator
        ]

        # Function to format list of IGNs for embed field
        def format_ign_list(igns: List[str], max_display: int = 15) -> str:
            if not igns: return "None"
            display_str = ", ".join(igns[:max_display])
            if len(igns) > max_display:
                display_str += f", ... *(+{len(igns) - max_display} more)*"
            # Ensure the field value doesn't exceed Discord limits
            return (display_str[:1021] + '...') if len(display_str) > 1024 else display_str

        summary_embed = discord.Embed(title=summary_title, description="\n".join(summary_desc), color=final_color)

        # Add fields for details only if there are entries in that category
        if newly_added_igns:
            summary_embed.add_field(name="Newly Added IGNs", value=format_ign_list(newly_added_igns), inline=False)
        if already_marked_igns:
            summary_embed.add_field(name="Skipped IGNs (Already Marked)", value=format_ign_list(already_marked_igns), inline=False)
        if failed_igns: # Includes check failures now
             # Sort failed IGNs maybe? Optional.
             summary_embed.add_field(name="Failed IGNs (Reason)", value=format_ign_list(failed_igns), inline=False)
        # Optionally report check_failed_igns separately if needed for debugging
        # if check_failed_igns:
        #     summary_embed.add_field(name="DB Check Failed For", value=format_ign_list(check_failed_igns), inline=False)

        try:
            await progress_msg.edit(content=None, embed=summary_embed)
        except discord.HTTPException: # Handle if original progress message gone
             await interaction.followup.send(embed=summary_embed, ephemeral=False) # Send new message

        # Update log message with new counts
        log_msg = (f"`{interaction.user}` used /bulkactive for {format_date_dmy(activity_date)}. "
                   f"Submitted: {len(potential_igns)}, Added: {newly_added_count}, "
                   f"Skipped: {already_marked_count}, Failed: {total_failures}. "
                   f"Details: {'; '.join(log_details)}")
        # Truncate log message if needed before sending
        await log_info(guild, (log_msg[:1950] + "...") if len(log_msg) > 1990 else log_msg)


    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        # Keep this error handler as is
        await log_error(interaction.guild, "Error in BulkActiveModal", error=error, interaction=interaction)
        try:
             if interaction.response.is_done():
                 await interaction.followup.send("❌ An unexpected error occurred within the modal processing.", ephemeral=False)
             else:
                 await interaction.response.send_message("❌ An unexpected error occurred within the modal processing.", ephemeral=False)
        except Exception:
             pass
                
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
async def log_to_channel(channel_id: int, guild: Optional[discord.Guild], message: Optional[str] = None, embed: Optional[discord.Embed] = None, ping_mention: Optional[str] = None):
    """Sends log to a channel, checking permissions, optionally prepending a ping."""
    if not guild: print(f"Log Error: No Guild for channel {channel_id}."); return
    log_channel = guild.get_channel(channel_id)
    if not isinstance(log_channel, discord.TextChannel): print(f"Log Error: Channel {channel_id} invalid in {guild.name}."); return
    # Check bot object exists before accessing bot.user
    if not bot or not bot.user: print(f"Log Error: Bot not ready, cannot get member object in {guild.name}."); return
    bot_member = guild.get_member(bot.user.id)
    if not bot_member: print(f"Log Error: Cannot find bot ({bot.user.id if bot.user else 'N/A'}) in {guild.name}."); return
    perms = log_channel.permissions_for(bot_member)
    if not perms.send_messages or (embed and not perms.embed_links): print(f"Log Error: Missing Send/Embed perms in {log_channel.mention}."); return

    content_to_send = ping_mention if ping_mention else None

    try:
        if embed:
            # Send ping as content separate from embed if needed
            await log_channel.send(content=content_to_send, embed=embed, allowed_mentions=discord.AllowedMentions(users=True)) # Ensure user pings work
        elif message:
            # Prepend ping to text message if provided
            full_message = f"{ping_mention} {message}" if ping_mention else message
            # Truncate combined message if needed
            await log_channel.send((full_message[:1997] + "...") if len(full_message) > 2000 else full_message, allowed_mentions=discord.AllowedMentions(users=True)) # Ensure user pings work
    except discord.Forbidden: print(f"Log Error: Forbidden in {log_channel.mention}.")
    except discord.HTTPException as e: print(f"Log Error: HTTP {e.status} in {log_channel.mention}: {e.text}")
    except Exception as e: print(f"Log Error: Send fail in {log_channel.mention}: {e}")

async def log_info(guild: Optional[discord.Guild], message: str, embed: Optional[discord.Embed] = None):
    """Logs an info message."""
    # Simplified: always create an embed for consistency if only message is passed
    if not embed:
        embed = discord.Embed(description=message, color=NERDY_YELLOW)
        embed.timestamp = discord.utils.utcnow()
    # Use log_to_channel but target INFO channel and no ping
    await log_to_channel(INFO_LOG_CHANNEL_ID, guild, embed=embed, ping_mention=None)

# --- REVISED log_error (Always pings owner) ---
async def log_error(guild: Optional[discord.Guild], message: str, error: Optional[Exception] = None, interaction: Optional[discord.Interaction] = None, embed: Optional[discord.Embed] = None):
    """Logs an error to the error channel, ALWAYS pinging the owner."""

    # --- Always set ping content for the error channel ---
    ping_content = f"<@{SELF_PROTECTED_ID}>"

    if not embed:
        # Use a consistent "Critical Error" title since it always pings
        title_prefix = "🚨 Bot Critical Error"
        embed = discord.Embed(title=title_prefix, description=message, color=discord.Color.red())
        embed.timestamp = discord.utils.utcnow()
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
            # Print to console with ping indication
            print(f"---\nERROR LOGGED (OWNER PING SENT):\nGuild: {guild.id if guild else 'N/A'}\nCtx: {message}\nErr: {etype}: {emsg}\n{full_tb}---\n")
        else:
             # Print non-exception errors too, indicating ping status
             print(f"---\nERROR/WARN LOGGED (OWNER PING SENT):\nGuild: {guild.id if guild else 'N/A'}\nCtx: {message}\n---\n")

    # Pass the ping content to log_to_channel, targeting the ERROR channel
    await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, embed=embed, ping_mention=ping_content)

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
    def __init__(self, original_data: List[Dict[str, Any]], initial_display_data: List[Dict[str, Any]], total_members: int, guild: Optional[discord.Guild], is_catercord_context: bool, timeout=300.0):
        super().__init__(timeout=timeout)
        # original_data holds the base info fetched for the context
        self.original_data = original_data
        # current_data is initialized with the pre-fetched data for the default view
        self.current_data = initial_display_data # Use the passed initial data
        self.total_members = total_members
        self.current_page = 0
        self.message: Optional[discord.Message] = None
        self.guild = guild # Store guild if needed later (e.g., for logging inside view)
        self.is_catercord_context = is_catercord_context # Store the context flag

        # --- State ---
        # Set default view based on context
        # If in Catercord, default to monthly. If outside, default to all-time activity.
        self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY if is_catercord_context else VIEW_MODE_ACTIVITY_ALL
        # Default sort depends on default view - activity seems reasonable for both contexts
        self.sort_mode = SORT_MODE_ACTIVITY
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
        # Buttons added via decorators (@discord.ui.button)

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

    # --- REVISED create_page_embed (within HCPagesView class) ---
    def create_page_embed(self) -> discord.Embed:
        """Creates embed based on current view_mode, sort_mode, and context."""
        start = self.current_page * MEMBERS_PER_PAGE
        page_data = self.current_data[start : start + MEMBERS_PER_PAGE]

        IDX_WIDTH = 3
        if self.view_mode == VIEW_MODE_DISCORD:
             # Use a slightly wider name column to accommodate potentially longer stored names
             NAME_WIDTH = 18
             IGN_WIDTH = 15
             ACT_WIDTH = 0 # No activity column
             TOTAL_WIDTH = IDX_WIDTH + NAME_WIDTH + IGN_WIDTH
             header = (f"{'#':<{IDX_WIDTH}}{'Discord (Stored)':<{NAME_WIDTH}}{'In-Game':<{IGN_WIDTH}}") # Indicate stored name might be shown
        # All activity views use the same layout now
        elif self.view_mode in [VIEW_MODE_ACTIVITY_ALL, VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
             IGN_WIDTH = 20
             ACT_WIDTH = ACTIVITY_COLUMN_WIDTH # Use constant
             TOTAL_WIDTH = IDX_WIDTH + IGN_WIDTH + ACT_WIDTH
             header = (f"{'#':<{IDX_WIDTH}}{'In-Game':<{IGN_WIDTH}}{'Activity':<{ACT_WIDTH}}")
        else: # Fallback (shouldn't happen)
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
                ign = item_dict.get('ign', 'Unknown')

                if self.view_mode == VIEW_MODE_DISCORD:
                    # Check if live discord.Member object exists (only available in Catercord context)
                    member = item_dict.get('member')
                    if member: # If we have the live member object (Catercord context)
                        user_display = f"{member.name}#{member.discriminator}" if member.discriminator != '0' else member.name
                    else: # Use the stored name from Supabase (Outside Catercord or member left/no longer has role)
                        user_display = item_dict.get('discord_name') or "[No Discord]" # Use DB name or fallback placeholder

                    ign_display = ign
                    # Truncate display names if necessary
                    if len(user_display) > NAME_WIDTH: user_display = user_display[:NAME_WIDTH-1] + "…"
                    if len(ign_display) > IGN_WIDTH: ign_display = ign_display[:IGN_WIDTH-1] + "…"
                    # Format line
                    line = (f"{str(idx)+'.':<{IDX_WIDTH}}"
                            f"{user_display:<{NAME_WIDTH}}"
                            f"{ign_display:<{IGN_WIDTH}}")

                elif self.view_mode in [VIEW_MODE_ACTIVITY_ALL, VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
                    # Activity view logic remains the same, using data present in item_dict
                    activity_count = item_dict.get('activity_count', 0)
                    last_seen_date = item_dict.get('last_seen') # date object or None
                    ign_display = ign
                    # Format activity: Count (Last Seen DD/MM/YY)
                    activity_display = f"{activity_count} ({format_date_dmy(last_seen_date)})"

                    # Truncate display names if necessary
                    if len(ign_display) > IGN_WIDTH: ign_display = ign_display[:IGN_WIDTH-1] + "…"
                    if len(activity_display) > ACT_WIDTH: activity_display = activity_display[:ACT_WIDTH-1] + "…"
                    # Format line
                    line = (f"{str(idx)+'.':<{IDX_WIDTH}}"
                            f"{ign_display:<{IGN_WIDTH}}"
                            f"{activity_display:<{ACT_WIDTH}}")
                else: # Fallback
                     line = f"{str(idx)+'.':<{IDX_WIDTH}} Error: Invalid View Mode"

                desc_lines.append(line)
                idx += 1
            desc_lines.append("```")

        # Use context flag to potentially adjust title
        # If in Catercord, use standard title. Otherwise, indicate it's DB-only.
        title = HC_LIST_EMBED_TITLE if self.is_catercord_context else "HC Database Members (All)"

        embed = discord.Embed(
            title=title,
            description="\n".join(desc_lines),
            color=NERDY_YELLOW
        )

        # --- Footer Update (Remains the same) ---
        sort_text = "IGN" if self.sort_mode == SORT_MODE_IGN else "Activity"
        view_text_map = {
            VIEW_MODE_DISCORD: "Discord+IGN",
            VIEW_MODE_ACTIVITY_ALL: "Activity (All)",
            VIEW_MODE_ACTIVITY_DAILY: "Activity (Today)",
            VIEW_MODE_ACTIVITY_WEEKLY: "Activity (7d)",
            VIEW_MODE_ACTIVITY_MONTHLY: "Activity (30d)",
        }
        view_text = view_text_map.get(self.view_mode, "Unknown View")
        current_unix_ts = int(discord.utils.utcnow().timestamp())
        footer_text = (
            f"Page {self.current_page + 1}/{self.total_pages} | Total: {self.total_members} | "
            f"View: {view_text} | Sort: {sort_text}"
        )
        if self.is_fetching_activity:
             footer_text += " | Fetching data..."
        footer_text += f" | <t:{current_unix_ts}:R>" # Dynamic timestamp
        embed.set_footer(text=footer_text)
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

# --- REVISED fetch_hc_member_data (Adding logs for scenario 2) ---
async def fetch_hc_member_data(guild: discord.Guild) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fetches HC members from Discord and Supabase, including all-time activity counts.
    Logs warnings for mismatches (Role w/o DB, DB w/o Role/Member).
    Returns a list of dicts: [{'member': discord.Member | None, 'ign': str, 'activity_count': int, 'last_seen': date | None}]
    and the total count.
    Data is sorted by Discord name (if available), then IGN (case-insensitive).
    """
    print(f"Fetch HC Data ({guild.name}): Starting fetch...")
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"HC Role {ADD_ROLE_ID_HC} not found during fetch.", ping_owner=True) # Ping owner on critical role missing
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
                    # Store discord_id as string consistently
                    all_db_members[str(d_id)] = {"ign": ign, "processed": False}
                else:
                    ign_only_members[ign.lower()] = {"ign_original": ign, "processed": False}
            print(f"Fetch HC Data ({guild.name}): Found {len(all_db_members)} DB entries with Discord ID, {len(ign_only_members)} without.")
        else:
            print(f"Fetch HC Data ({guild.name}): No data returned from Supabase hc_members.")

    except ConnectionError as e: # Specific catch for connection error
        await log_error(guild, "Failed to fetch data from Supabase hc_members: Connection Error.", error=e, ping_owner=True)
        return [], 0
    except APIError as e: # Specific catch for API errors
         await log_error(guild, "Failed to fetch data from Supabase hc_members: API Error.", error=e, ping_owner=True)
         return [], 0
    except Exception as e: # Catch other exceptions during Supabase fetch
        await log_error(guild, "Failed to fetch data from Supabase hc_members: Unexpected Error.", error=e, ping_owner=True)
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
             except Exception as chunk_e: print(f"WARN: Chunking failed: {chunk_e}") # Log warning, don't stop

        discord_hc_members = [m for m in guild.members if hc_role in m.roles and not m.bot]
        print(f"Fetch HC Data ({guild.name}): Found {len(discord_hc_members)} Discord members with HC role.")
    except Exception as e:
        # Log as error but continue if possible, Supabase entries might still be processed
        await log_error(guild, "Guild chunking/member fetch failed during data fetch. List might be incomplete.", error=e, ping_owner=False) # Don't necessarily ping for this unless severe

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
            # *** SCENARIO 1 LOG ***
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

            # *** SCENARIO 2 LOGGING ***
            try:
                member_in_guild = guild.get_member(int(d_id)) # Check cache first
                if not member_in_guild and not guild.chunked: # If not found and not chunked, maybe try fetching? Risky performance-wise.
                     # Optional: try fetch member, but be careful with performance impact
                     # try: member_in_guild = await guild.fetch_member(int(d_id))
                     # except discord.NotFound: member_in_guild = None
                     # except Exception: member_in_guild = None # Ignore other fetch errors
                     pass

                if member_in_guild:
                    # User is IN the guild, check if they have the HC role
                    if hc_role not in member_in_guild.roles:
                        await log_info(guild, f"Fetch HC Data Warning: DB entry exists for {member_in_guild.mention} (`{d_id}`), but they do **not** currently have the HC role.")
                    # else: # User exists and HAS the role, but wasn't processed in loop 1? This is odd.
                    #     await log_warning(guild, f"Fetch HC Data Anomaly: DB entry for {member_in_guild.mention} (`{d_id}`) has HC role but wasn't processed initially.")
                else:
                    # User is NOT in the guild (or couldn't be found)
                    # Fetch discord name from DB if available, fallback to ID
                    db_name = entry_data.get("discord_name", f"ID {d_id}")
                    await log_info(guild, f"Fetch HC Data Info: DB entry exists for user `{db_name}` (`{d_id}`), but they are not currently in this server (or couldn't be found). IGN: `{ign}`")

            except ValueError: # Handle if d_id is somehow not a valid integer string
                 await log_error(guild, f"Fetch HC Data Error: Invalid Discord ID '{d_id}' found in database for IGN '{ign}'.", ping_owner=True)
            except Exception as e_log: # Catch errors during the logging check itself
                 await log_error(guild, f"Fetch HC Data Error: Failed during Scenario 2 check for ID '{d_id}'", error=e_log, ping_owner=False) # Don't ping for logging errors

            # Add to final data regardless of log status
            final_data.append({
                "member": None, # Display as [No Discord]
                "ign": ign,
                "activity_count": activity['count'],
                "last_seen": activity['last_seen']
            })
            # *** END SCENARIO 2 LOGGING ***

    # Add IGN-only entries (no discord_id)
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

# --- Background Task for Static List Reset ---

@tasks.loop(minutes=1.0) # Check every minute
async def check_static_view_timeout():
    await bot.wait_until_ready() # Wait until the bot is ready

    channel_ids_to_check = list(active_static_list_views.keys())

    for channel_id in channel_ids_to_check:
        view_data = active_static_list_views.get(channel_id)
        # ... (keep checks for view_data, view_instance, message_id, is_finished) ...
        if not view_data: continue
        view_instance = view_data.get('view')
        message_id = view_data.get('message_id')
        if not view_instance or not message_id or not isinstance(view_instance, StaticHCPagesView):
            print(f"[Task Loop] Invalid data found for channel {channel_id}. Cleaning up.")
            if channel_id in active_static_list_views: del active_static_list_views[channel_id]
            continue
        if view_instance.is_finished():
             print(f"[Task Loop] View for message {message_id} already finished. Cleaning up.")
             if channel_id in active_static_list_views: del active_static_list_views[channel_id]
             continue

        now = discord.utils.utcnow()
        last_active = view_instance.last_interaction_time
        time_since_last_active = now - last_active

        if time_since_last_active.total_seconds() > (STATIC_LIST_RESET_TIMEOUT_MINUTES * 60):
            if not view_instance.info_mode_active:
                try:
                    # --- Directly await the async reset method ---
                    await view_instance.reset_view()
                    # --- Update timestamp AFTER reset ---
                    # (reset_view should ideally update this internally upon success,
                    # but doing it here is a safety measure if reset_view fails early)
                    # Let's rely on reset_view updating it upon successful edit.
                    # view_instance.last_interaction_time = discord.utils.utcnow() # Removed for now
                except Exception as e:
                    print(f"[Task Loop] Error occurred during view reset for message {message_id}: {e}")
                    # Log error properly
                    guild = bot.get_guild(view_instance.guild.id) if view_instance.guild else None
                    await log_error(guild, f"Task Loop: Error during view reset for message {message_id}", error=e)
            # else: keep comment about skipping if info mode active

# --- Start the task in on_ready ---
@bot.event
async def on_ready():
    # ... (your existing on_ready code) ...

    print("Starting background tasks...")
    if not check_static_view_timeout.is_running():
        check_static_view_timeout.start()
        print(" Static view timeout checker task started.")

    print("--- on_ready event finished ---")


# --- Ensure task is stopped on cleanup (optional but good practice) ---
@bot.event
async def on_close():
     print("Closing bot connection. Stopping tasks...")
     if check_static_view_timeout.is_running():
          check_static_view_timeout.cancel()
          print(" Static view timeout checker task stopped.")

# --- REVISED update_static_list_message Function ---

async def update_static_list_message(guild: discord.Guild):
    """ Creates or updates the SINGLE interactive HC list message."""
    list_channel_id = HC_MEMBER_LIST_CHANNEL_ID
    chan = guild.get_channel(list_channel_id)

    # --- Initial Checks ---
    if not isinstance(chan, discord.TextChannel):
        await log_error(guild, f"Static list update failed: Channel {list_channel_id} invalid.")
        return
    if not bot or not bot.user:
        await log_error(guild, "Static list update failed: Bot not ready.")
        return
    bot_perms = chan.permissions_for(guild.me)
    if not bot_perms.send_messages or not bot_perms.embed_links or not bot_perms.read_message_history:
        await log_error(guild, f"Static list update failed: Bot missing Send/Embed/History permissions in {chan.mention}.")
        return

    await log_info(guild, f"Updating interactive static list in {chan.mention}...")

    # --- Fetch Fresh Base Data ---
    member_data = []
    total_count = 0
    try:
        member_data, total_count = await fetch_hc_member_data(guild)
        if not member_data:
            await log_info(guild, "Static list update: No HC members found. Will show empty state.")
            # Proceeding with empty member_data is fine, the view handles it.

    except Exception as e_fetch:
        await log_error(guild, "Static list update failed: Error fetching base member data.", error=e_fetch)
        return

    # --- Fetch Initial Display Data (Monthly Activity) ASYNCHRONOUSLY ---
    initial_display_data = list(member_data) # Default to base data
    try:
        today_utc = datetime.datetime.now(pytz.utc).date()
        end_date_monthly = today_utc
        start_date_monthly = today_utc - datetime.timedelta(days=29)
        all_igns = [item['ign'] for item in member_data if item.get('ign')]

        if all_igns:
            print(f"[Static Update] Fetching initial monthly activity for {len(all_igns)} IGNs...")
            monthly_activity_data = await fetch_activity_data(guild, all_igns, start_date_monthly, end_date_monthly)
            print(f"[Static Update] Fetched initial monthly activity.")
            temp_data = []
            for item in member_data: # Iterate base data
                ign_lower = item.get('ign', '').lower()
                activity_info = monthly_activity_data.get(ign_lower, {'count': 0, 'last_seen': None})
                updated_item = item.copy() # Create copy from base data
                updated_item['activity_count'] = activity_info['count']
                updated_item['last_seen'] = activity_info['last_seen']
                temp_data.append(updated_item)
            initial_display_data = temp_data # Set the prepared data
        else:
            print("[Static Update] No IGNs found in base data, skipping initial monthly fetch.")
    except Exception as fetch_err:
         await log_error(guild, "[Static Update] Failed to fetch initial monthly activity", error=fetch_err)
         # initial_display_data already defaults to member_data, so we fallback safely

    # --- Try to Get Existing View and Message ---
    existing_view_instance: Optional[StaticHCPagesView] = None
    existing_message: Optional[discord.Message] = None
    tracked_data = active_static_list_views.get(list_channel_id)

    if tracked_data:
        view = tracked_data.get('view')
        msg_id = tracked_data.get('message_id')
        # Check if view is the correct type and not stopped
        if msg_id and isinstance(view, StaticHCPagesView) and not view.is_finished():
            try:
                existing_message = await chan.fetch_message(msg_id)
                if existing_message:
                    # Minimal check: does it have components? A more robust check is complex.
                    if existing_message.components:
                        existing_view_instance = view
                        print(f"[Static Update] Found existing tracked message {msg_id} and running view instance.")
                    else:
                        print(f"[Static Update] Tracked message {msg_id} has no components. Will send new.")
                        existing_message = None # Treat as non-existent for view update
            except discord.NotFound:
                print(f"[Static Update] Tracked message {msg_id} not found. Cleaning up tracker.")
                if list_channel_id in active_static_list_views: del active_static_list_views[list_channel_id]
            except Exception as e_fetch_tracked:
                 print(f"[Static Update] Error fetching/validating tracked message {msg_id}: {e_fetch_tracked}. Will send new.")
                 # Clear potentially bad references
                 existing_message = None
                 existing_view_instance = None

    # --- Update Existing View or Send New Message ---
    try:
        if existing_view_instance and existing_message:
            print(f"[Static Update] Updating data within existing view for message {existing_message.id}")
            # Call the new method to update data and refresh
            await existing_view_instance.update_data_and_refresh(
                new_original_data=member_data,
                new_initial_display_data=initial_display_data,
                new_total_members=total_count
            )
            await log_info(guild, f"Interactive static list updated (existing view) successfully in {chan.mention}.") # Log specific action
        else:
            # --- No existing view found or it was invalid, create and send new ---
            print("[Static Update] No valid existing view found/reusable. Creating and sending new message.")

            # Optionally delete old message(s) here if desired, checking history
            # ... (history checking logic omitted for clarity, focus on sending new) ...

            new_view = StaticHCPagesView(
                original_data=member_data,
                initial_display_data=initial_display_data,
                total_members=total_count,
                guild=guild,
                message_id=None # Will be set after sending
            )
            initial_embed = new_view.create_page_embed()
            sent_message: Optional[discord.Message] = None

            sent_message = await chan.send(embed=initial_embed, view=new_view)
            print(f"[Static Update] New message sent: {sent_message.id}")

            # Update tracking with the NEW view instance
            if sent_message:
                 # Stop previous view if accidentally tracked but not reused
                 if list_channel_id in active_static_list_views:
                      old_view_data = active_static_list_views[list_channel_id]
                      if old_view_data.get('view') and not old_view_data['view'].is_finished():
                           old_view_data['view'].stop()
                      print(f"[Static Update] Stopped previous tracked view instance (if any).")

                 # Track the new message and view
                 active_static_list_views[list_channel_id] = {
                      'view': new_view,
                      'message_id': sent_message.id
                 }
                 new_view.message_id = sent_message.id # Ensure view instance knows its message ID
                 print(f"[Static Update] Updated tracking for channel {list_channel_id} with NEW message {sent_message.id}")

                 # Ensure background task is running
                 if not check_static_view_timeout.is_running():
                      print("[Static Update] Background task wasn't running. Starting it.")
                      try: check_static_view_timeout.start()
                      except RuntimeError: print("[Static Update] Background task already started (RuntimeError).")
            await log_info(guild, f"Interactive static list updated (new message) successfully in {chan.mention}.") # Log specific action

    except discord.Forbidden as e:
        await log_error(guild, f"Static list update failed: Bot lacks permissions in {chan.mention}.", error=e)
    except discord.HTTPException as e:
        await log_error(guild, "Static list update failed: Discord API error.", error=e)
    except Exception as e:
        await log_error(guild, "Static list update failed: Unexpected error during send/edit/update.", error=e)

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

    # --- Command Syncing ---
    print("Syncing application commands...")
    synced_commands = []
    try:
        # Consider syncing only within the target guild if commands are guild-specific
        # target = discord.Object(id=TARGET_GUILD_ID) # Optional: Specify target guild
        # synced_commands = await tree.sync(guild=target)
        synced_commands = await tree.sync() # Global sync (current implementation)
        print(f"Synced {len(synced_commands)} application commands.")
        command_ids.clear()
        for cmd in synced_commands:
            if hasattr(cmd, 'name') and hasattr(cmd, 'id'):
                command_ids[cmd.name] = cmd.id
            else:
                print(f"  Skipped storing ID during sync (type: {type(cmd)}, name: {getattr(cmd, 'name', 'N/A')})")
        if command_ids: print(f"Stored command IDs: {command_ids}")
        else: print("Warning: command_ids dictionary is empty after sync.")
    except discord.HTTPException as e:
        print(f"Command Sync failed (HTTPException): {e}")
    except Exception as e:
        print(f"Command Sync failed (Unexpected Error): {e}\n{traceback.format_exc()}")

    # --- Signal Bot Ready ---
    print(f"Bot is ready and connected to {len(bot.guilds)} guild(s).")
    first_guild = bot.guilds[0] if bot.guilds else None
    if first_guild:
        try:
             await log_info(first_guild, f"Bot ready and online. Synced {len(synced_commands)} commands.")
        except Exception as log_e:
             print(f"Failed to send initial ready log message: {log_e}")

    # --- Start Background Tasks ---
    print("Starting background tasks...")
    if not check_static_view_timeout.is_running():
        try:
            check_static_view_timeout.start()
            print(" Static view timeout checker task started.")
        except Exception as e_task:
            print(f"Failed to start static view timeout task: {e_task}")
            await log_error(first_guild, "Failed to start static view timeout task", error=e_task)


    # --- Schedule Delayed Static List Update --- <--- NEW SECTION
    async def delayed_update(delay_seconds: int):
        await asyncio.sleep(delay_seconds)
        print(f"--- Running delayed static list update after {delay_seconds}s ---")
        guild = bot.get_guild(TARGET_GUILD_ID)
        if not guild:
            print(f"ERROR: Could not find target guild {TARGET_GUILD_ID} for delayed update.")
            # Log error if guild isn't found
            await log_error(None, f"Delayed update failed: Target guild {TARGET_GUILD_ID} not found.")
            return

        if not supabase:
            print("ERROR: Supabase client not available for delayed update.")
            await log_error(guild, "Delayed update failed: Supabase client not available.")
            return

        try:
            await update_static_list_message(guild)
        except Exception as e:
             print(f"ERROR during delayed initial list update: {e}\n{traceback.format_exc()}")
             await log_error(guild, "Error during delayed initial list update", error=e)
        print(f"--- Delayed static list update finished ---")

    # Schedule the task to run 60 seconds after on_ready finishes
    # Ensure bot is connected to guilds before scheduling
    if bot.is_ready() and any(g.id == TARGET_GUILD_ID for g in bot.guilds):
        print("Scheduling delayed static list update for target guild...")
        bot.loop.create_task(delayed_update(delay_seconds=60))
    else:
        print("Skipping delayed static list update (Bot not fully ready or not in target guild).")

    print("--- on_ready event finished ---")


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Ignore updates for bots or if roles haven't changed
    if after.bot or before.roles == after.roles:
        return

    guild = after.guild # Define guild here
    # If HC role isn't configured or found, no need to proceed
    hc_role = guild.get_role(ADD_ROLE_ID_HC) # Define hc_role here
    if not hc_role:
        print(f"on_member_update ({guild.name}): HC Role {ADD_ROLE_ID_HC} not found, cannot check role change.")
        return # Exit early if the role doesn't exist

    # Define had_hc_role and has_hc_role *after* defining hc_role
    had_hc_role = hc_role in before.roles
    has_hc_role = hc_role in after.roles

    # Trigger update only if the HC role status changed
    if had_hc_role != has_hc_role:
        action = "added to" if has_hc_role else "removed from"
        # Use the correctly defined guild and hc_role variables
        await log_info(guild, f"HC role (`{hc_role.name}`) {action} user {after.mention} (`{after.id}`). Triggering static list message update.")
        try:
            # Schedule the NEW update function
            asyncio.create_task(update_static_list_message(guild)) # Call the new function
        except Exception as e:
             # Use the correctly defined guild variable
             await log_error(guild, f"Failed to trigger static list message update after role change for {after.mention}", error=e)

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


# --- REFINED HC Verify Command (Handles existing IGN-only entries, ROLE_ID_MAYBE_EXHC removal) ---
@tree.command(name="hcverify", description="Verify user into HC, store/link IGN, set nickname.") # Slightly updated description
@app_commands.describe(user="User to HC verify.", ingame_name="User's Florr IGN (will link/update DB & set nickname).") # Updated description
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    guild = interaction.guild
    if not await check_supabase_available(interaction):
        try:
            if interaction.response.is_done(): await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        except (discord.NotFound, discord.HTTPException): pass
        return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return
    if not supabase:
        await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=False)
        await log_error(guild, "HCVerify failed: Supabase client unavailable.", interaction=interaction)
        return

    # Defer publicly
    await interaction.response.defer(thinking=True, ephemeral=False)

    # --- Role Setup & Checks ---
    role_unverified = guild.get_role(REMOVE_ROLE_ID)
    role_verified = guild.get_role(ADD_ROLE_ID_VERIFY)
    role_hc = guild.get_role(ADD_ROLE_ID_HC)
    role_maybe_exhc = guild.get_role(ROLE_ID_MAYBE_EXHC)
    bot_member = guild.me

    missing_roles = []
    critical_roles_found = True
    if ADD_ROLE_ID_VERIFY and not role_verified:
        missing_roles.append(f"Verified (ID: {ADD_ROLE_ID_VERIFY})")
        critical_roles_found = False
    if ADD_ROLE_ID_HC and not role_hc:
        missing_roles.append(f"HC (ID: {ADD_ROLE_ID_HC})")
        critical_roles_found = False
    if REMOVE_ROLE_ID and not role_unverified: print(f"HCVerify Warning ({guild.name}): Unverified Role (ID: {REMOVE_ROLE_ID}) not found.")
    if ROLE_ID_MAYBE_EXHC and not role_maybe_exhc: print(f"HCVerify Warning ({guild.name}): Maybe-ExHC Role (ID: {ROLE_ID_MAYBE_EXHC}) not found.")

    if not critical_roles_found:
        msg = f"❌ Setup Error: Missing critical roles: {', '.join(missing_roles)}. Configure the bot."
        await interaction.followup.send(msg, ephemeral=False)
        await log_error(guild, f"HCVerify failed: Missing critical roles - {', '.join(missing_roles)}", interaction=interaction)
        return

    # --- Prepare for actions ---
    log_summary = []
    result_summary = []
    errors_occurred = False
    db_success = False
    role_changes_succeeded = False
    maybe_exhc_role_removed_flag = False
    nick_success = False
    reason = f"HC Verified by {interaction.user} (ID: {interaction.user.id})"
    can_manage_user_roles = bot_member.top_role.position > user.top_role.position
    can_manage_user_nick = can_manage_user_roles
    original_hc_status = role_hc in user.roles
    ign_to_process = ingame_name.strip()

    # --- Role Management ---
    # (Keep the existing role management logic exactly as it was in the previous version)
    # ... (Includes desired_adds, desired_removes, hierarchy checks, user.edit(roles=...)) ...
    roles_to_add_final = []
    roles_to_remove_final = []
    desired_adds = []
    desired_removes = []
    if role_verified and not (role_verified in user.roles): desired_adds.append(role_verified) # Check role exists
    if role_hc and not original_hc_status: desired_adds.append(role_hc) # Check role exists
    if role_unverified and (role_unverified in user.roles): desired_removes.append(role_unverified) # Check role exists
    if role_maybe_exhc and (role_maybe_exhc in user.roles): # Check role exists and user has it
        desired_removes.append(role_maybe_exhc)
        if bot_member.top_role.position > role_maybe_exhc.position:
             maybe_exhc_role_removed_flag = True

    for role in desired_adds:
        if bot_member.top_role.position > role.position: roles_to_add_final.append(role)
        else: errors_occurred=True; reason_skip=f"Bot hierarchy too low to add role '{role.name}'"; result_summary.append(f"⚠️ Skipped adding `{role.name}` (Hierarchy)."); log_summary.append(f"Role add skip: {reason_skip}"); await log_info(guild, f"HCVerify: {reason_skip} for {user.mention}")
    for role in desired_removes:
        if bot_member.top_role.position > role.position: roles_to_remove_final.append(role)
        else:
            if role == role_maybe_exhc: maybe_exhc_role_removed_flag = False
            errors_occurred=True; reason_skip=f"Bot hierarchy too low to remove role '{role.name}'"; result_summary.append(f"⚠️ Skipped removing `{role.name}` (Hierarchy)."); log_summary.append(f"Role remove skip: {reason_skip}"); await log_info(guild, f"HCVerify: {reason_skip} for {user.mention}")

    if roles_to_add_final or roles_to_remove_final:
        try:
            current_roles = user.roles
            final_role_set = [r for r in current_roles if r not in roles_to_remove_final] + roles_to_add_final
            final_role_set = [r for r in final_role_set if r.id != guild.default_role.id]
            await user.edit(roles=final_role_set, reason=reason)
            added_names_list = [f"`{r.name}`" for r in roles_to_add_final]; removed_names_list = [f"`{r.name}`" for r in roles_to_remove_final]
            added_names = ', '.join(added_names_list); removed_names = ', '.join(removed_names_list)
            if added_names: result_summary.append(f"➕ Roles Added: {added_names}")
            if removed_names: result_summary.append(f"➖ Roles Removed: {removed_names}")
            if role_maybe_exhc in roles_to_remove_final:
                 if maybe_exhc_role_removed_flag: result_summary.append(f"✅ (Removed `{role_maybe_exhc.name}` - Welcome back!)"); log_summary.append(f"Removed role '{role_maybe_exhc.name}'")
                 else: print(f"HCVerify Logic Warning: Removed {role_maybe_exhc.name} but flag was false.")
            log_summary.append("Role update successful for applicable roles.")
            role_changes_succeeded = True
        except discord.Forbidden: errors_occurred=True; result_summary.append("⚠️ Role Error: Permissions error during update."); log_summary.append("Role update failed: Forbidden"); await log_error(guild, "HCVerify role update failed (Forbidden)", interaction=interaction); maybe_exhc_role_removed_flag = False
        except discord.HTTPException as e: errors_occurred=True; result_summary.append("⚠️ Role Error: Discord API Error during update."); log_summary.append(f"Role update failed: HTTP {e.status}"); await log_error(guild, "HCVerify role update failed (HTTPException)", error=e, interaction=interaction); maybe_exhc_role_removed_flag = False
        except Exception as e: errors_occurred=True; result_summary.append("⚠️ Role Error: Unknown error during update."); log_summary.append(f"Role update fail: {type(e).__name__}"); await log_error(guild, "HCVerify unexpected role error", error=e, interaction=interaction); maybe_exhc_role_removed_flag = False
    elif not any("Role add skip" in s or "Role remove skip" in s for s in log_summary): result_summary.append("ℹ️ Roles already correct."); log_summary.append("No role changes needed.")

    # --- MODIFIED Database Update ---
    if not ign_to_process:
        errors_occurred=True
        result_summary.append(f"⚠️ DB Error: In-game name cannot be empty.")
        log_summary.append(f"DB fail: Empty IGN provided.")
    else:
        try:
            # 1. Check if IGN exists and if it's linked
            print(f"HCVerify: Checking DB for IGN '{ign_to_process}' before upsert/update.")
            existing_entry_resp = await run_supabase_sync(
                lambda: supabase.table("hc_members")
                               .select("discord_id, ingame_name") # Select needed fields
                               .eq("ingame_name", ign_to_process)
                               .maybe_single() # Expect 0 or 1 result
                               .execute()
            )
            existing_entry = existing_entry_resp.data if existing_entry_resp and hasattr(existing_entry_resp, 'data') else None

            operation_type = "link" # Default to linking if IGN exists but unlinked

            if existing_entry:
                existing_discord_id = existing_entry.get("discord_id")
                if existing_discord_id is None:
                    # Case 1: IGN exists, discord_id is NULL -> Update existing row
                    print(f"HCVerify: IGN '{ign_to_process}' found with NULL discord_id. Updating...")
                    await run_supabase_sync(
                        lambda: supabase.table("hc_members")
                                       .update({
                                           "discord_id": str(user.id),
                                           "discord_name": f"{user.name}#{user.discriminator}" if user.discriminator != '0' else user.name
                                       })
                                       .eq("ingame_name", ign_to_process) # Match by IGN
                                       .is_("discord_id", "null") # Ensure we only update unlinked entries
                                       .execute()
                    )
                    result_summary.append(f"🔗 IGN Linked: `{discord.utils.escape_markdown(ign_to_process)}` linked to {user.mention}.")
                    log_summary.append("Supabase update OK (linked existing IGN)")
                    db_success = True
                elif str(existing_discord_id) == str(user.id):
                    # Case 2: IGN exists and already linked to THIS user -> Upsert to potentially update IGN case/discord name
                    print(f"HCVerify: IGN '{ign_to_process}' already linked to this user ({user.id}). Performing upsert...")
                    operation_type = "update"
                    await run_supabase_sync( lambda: supabase.table("hc_members").upsert({
                            "discord_id": str(user.id),
                            "discord_name": f"{user.name}#{user.discriminator}" if user.discriminator != '0' else user.name,
                            "ingame_name": ign_to_process # Use potentially corrected case
                        }, on_conflict="discord_id").execute()
                    )
                    result_summary.append(f"💾 IGN Stored/Updated: `{discord.utils.escape_markdown(ign_to_process)}`")
                    log_summary.append("Supabase upsert OK (updated existing user link)")
                    db_success = True
                else:
                    # Case 3: IGN exists and linked to ANOTHER user -> Error
                    errors_occurred=True
                    err_detail=f"IGN Conflict: '{ign_to_process}' is already linked to another Discord account (<@{existing_discord_id}>)."
                    result_summary.append(f"⚠️ DB Error: {err_detail}")
                    log_summary.append(f"DB upsert fail: IGN Unique Conflict for {ign_to_process} (linked to {existing_discord_id})")
                    await log_info(guild, f"HCVerify DB Error: IGN '{ign_to_process}' conflict for user {user.mention}. Already linked to ID {existing_discord_id}.", interaction=interaction)
            else:
                # Case 4: IGN does not exist -> Upsert normally
                print(f"HCVerify: IGN '{ign_to_process}' not found. Performing upsert...")
                operation_type = "store/update"
                await run_supabase_sync( lambda: supabase.table("hc_members").upsert({
                        "discord_id": str(user.id),
                        "discord_name": f"{user.name}#{user.discriminator}" if user.discriminator != '0' else user.name,
                        "ingame_name": ign_to_process
                    }, on_conflict="discord_id").execute()
                )
                result_summary.append(f"💾 IGN Stored/Updated: `{discord.utils.escape_markdown(ign_to_process)}`")
                log_summary.append("Supabase upsert OK (new/updated user link)")
                db_success = True

        except APIError as e:
            errors_occurred=True
            err_detail=f"API Error ({e.code or 'N/A'}): {e.message or 'Unknown'}"
            result_summary.append(f"⚠️ DB Error during {operation_type}: {err_detail}")
            log_summary.append(f"DB {operation_type} fail: {e}")
            await log_error(guild, f"HCVerify DB {operation_type} fail (APIError)", error=e, interaction=interaction)
        except Exception as e:
            errors_occurred=True
            err_type = type(e).__name__
            result_summary.append(f"⚠️ DB Error during {operation_type}: {err_type}.")
            log_summary.append(f"DB {operation_type} fail: {err_type}")
            await log_error(guild, f"HCVerify DB {operation_type} fail ({err_type})", error=e, interaction=interaction)
    # --- END MODIFIED Database Update ---

    # --- Nickname Management ---
    # (Keep the existing nickname management logic exactly as it was)
    # ... (Checks nickname_to_set, hierarchy, user.edit(nick=...)) ...
    nickname_to_set = ign_to_process[:32] if ign_to_process else ""
    truncated = ign_to_process != nickname_to_set and ign_to_process

    if not nickname_to_set:
        if db_success: errors_occurred=True; result_summary.append("⚠️ Nickname Error: Cannot set empty nickname."); log_summary.append("Nick skipped (empty IGN)")
    elif user.nick == nickname_to_set: result_summary.append(f"🏷️ Nickname already matches stored IGN."); log_summary.append("Nick already set"); nick_success = True
    elif not can_manage_user_nick: errors_occurred=True; result_summary.append(f"⚠️ Nickname Skipped (Hierarchy)."); log_summary.append("Nick skipped (Hierarchy)")
    else:
        try:
            await user.edit(nick=nickname_to_set, reason=reason)
            nick_msg = f"🏷️ Nickname Set: `{discord.utils.escape_markdown(nickname_to_set)}`"; nick_success = True
            if truncated: nick_msg += " (truncated)"
            result_summary.append(nick_msg); log_summary.append(f"Nick set{' (trunc)' if truncated else ''}")
        except discord.Forbidden: errors_occurred=True; result_summary.append("⚠️ Nickname Error: Permissions error."); log_summary.append("Nick fail: Forbidden"); await log_error(guild, "HCVerify nick fail (Forbidden)", interaction=interaction)
        except discord.HTTPException as e: errors_occurred=True; result_summary.append("⚠️ Nickname Error: API Error."); log_summary.append(f"Nick fail: HTTP {e.status}"); await log_error(guild, "HCVerify nick fail (HTTPException)", error=e, interaction=interaction)
        except Exception as e: errors_occurred=True; result_summary.append("⚠️ Nickname Error: Unknown error."); log_summary.append(f"Nick fail: {type(e).__name__}"); await log_error(guild, "HCVerify unexpected nick error", error=e, interaction=interaction)

    # --- Final Response & Logging ---
    # (Keep the existing final response/logging logic exactly as it was)
    # ... (Creates embed, sends followup, logs summary, triggers list update) ...
    final_color = discord.Color.green() if not errors_occurred else discord.Color.orange()
    final_title = f"{'✅' if not errors_occurred else '⚠️'} HC Verify Processed: {user.display_name}"
    if errors_occurred: final_title += " (with issues/skips)"
    if not result_summary: result_summary.append("ℹ️ No actions were performed or needed.")
    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    try: await interaction.followup.send(embed=final_embed)
    except (discord.NotFound, discord.HTTPException) as e: await log_error(guild, "HCVerify failed final followup send", error=e, interaction=interaction)
    await log_info(guild, f"`{interaction.user}` HCVerify for {user.mention}. Summary: {'; '.join(log_summary)}.")
    if (role_changes_succeeded and role_hc in roles_to_add_final) or db_success:
         print(f"HCVerify: Triggering list update for {user.name} (HC role added: {role_hc in roles_to_add_final}, DB success: {db_success}).")
         asyncio.create_task(update_static_list_message(guild))

# --- New HCLeave Command (MODIFIED: IGN Only, Required, Autocomplete) ---
@tree.command(name="hcleave", description="Remove member from HC database by IGN.") # MODIFIED Description
@app_commands.describe(
    # REMOVED user description
    ingame_name="The IGN to remove from the database." # MODIFIED Description
)
@app_commands.autocomplete(ingame_name=ign_autocomplete) # Kept autocomplete for IGN
@app_commands.checks.has_permissions(manage_roles=True) # Or adjust permission
# REMOVED bot_has_permissions for manage_nicknames as it's no longer used
@app_commands.checks.bot_has_permissions(manage_roles=True) # Keep manage_roles check (though maybe not strictly needed now?)
# MODIFIED: Removed 'user' parameter, made 'ingame_name' required (no Optional)
async def hcleave(interaction: discord.Interaction, ingame_name: str):
    """Removes HC database entry based on IGN."""
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

    # REMOVED Input Validation check for user/ign as IGN is now required.

    # Defer ephemerally (admin action)
    await interaction.response.defer(thinking=True, ephemeral=False) # Keep ephemeral=False

    # REMOVED Role Setup (role_hc, role_maybe_exhc, bot_member) as roles aren't changed

    # REMOVED Role Existence Checks as roles aren't changed

    # --- Prepare for actions ---
    log_summary = []
    result_summary = []
    errors_occurred = False
    db_removed = False
    # REMOVED flags: hc_role_removed, exhc_role_added, nick_reset
    reason = f"HC DB Entry Removed by {interaction.user} (ID: {interaction.user.id})" # Updated reason
    cleaned_ign = ingame_name.strip() # Already required, but strip anyway
    # MODIFIED target identifier: Always based on IGN now
    target_identifier = f"IGN: `{discord.utils.escape_markdown(cleaned_ign)}`" if cleaned_ign else "Invalid Target (Empty IGN)"

    # --- Database Deletion ---
    # MODIFIED: Logic simplified as identifier is always IGN
    if cleaned_ign:
        identifier_for_db = {'ingame_name': cleaned_ign}
        target_identifier_db = f"IGN `{discord.utils.escape_markdown(cleaned_ign)}`"
        try:
            print(f"hcleave: Attempting to delete DB entry matching {identifier_for_db}")
            delete_result = await run_supabase_sync(
                lambda: supabase.table("hc_members")
                               .delete()
                               .match(identifier_for_db)
                               .execute()
            )
            if delete_result and hasattr(delete_result, 'data') and delete_result.data:
                 db_removed = True
                 result_summary.append(f"🗑️ Database entry removed for {target_identifier_db}.")
                 log_summary.append(f"DB entry delete OK for {identifier_for_db}")
            else:
                 result_summary.append(f"ℹ️ No database entry found matching {target_identifier_db} to remove.")
                 log_summary.append(f"DB entry delete: No match found for {identifier_for_db}")
        # Keep existing error handling for DB delete
        except APIError as e: errors_occurred = True; result_summary.append(f"⚠️ DB Error removing {target_identifier_db}: {e.message}"); log_summary.append(f"DB delete fail: APIError {e.code} - {e.message}"); await log_error(guild, f"hcleave DB delete APIError for {identifier_for_db}", error=e, interaction=interaction)
        except ConnectionError as e: errors_occurred = True; result_summary.append(f"⚠️ DB Error removing {target_identifier_db}: Connection failed."); log_summary.append("DB delete fail: ConnectionError"); await log_error(guild, f"hcleave DB delete ConnectionError for {identifier_for_db}", error=e, interaction=interaction)
        except Exception as e: errors_occurred = True; result_summary.append(f"⚠️ DB Error removing {target_identifier_db}: Unexpected error."); log_summary.append(f"DB delete fail: {type(e).__name__}"); await log_error(guild, f"hcleave DB delete unexpected error for {identifier_for_db}", error=e, interaction=interaction)
    else:
        # This case should not be reachable since IGN is required
        errors_occurred = True
        result_summary.append(f"⚠️ Logic Error: In-game name was empty despite being required.")
        log_summary.append("DB delete skipped: Empty IGN (Error)")

    # REMOVED --- Discord User Actions block (if user:) ---
    # This includes role removal, ExHC role addition, nickname reset

    # --- Final Response & Logging ---
    final_color = discord.Color.green() if not errors_occurred else discord.Color.orange()
    final_title = f"{'✅' if not errors_occurred else '⚠️'} HC Leave Processed: {target_identifier}" # Uses IGN identifier
    if errors_occurred: final_title += " (with issues/skips)"
    if not result_summary: result_summary.append("ℹ️ No actions were performed or needed.")

    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    try:
        await interaction.followup.send(embed=final_embed, ephemeral=False) # Kept ephemeral=False
    except (discord.NotFound, discord.HTTPException) as e:
        await log_error(guild, "hcleave failed final followup send", error=e, interaction=interaction)

    await log_info(guild, f"`{interaction.user}` processed /hcleave for {target_identifier}. Summary: {'; '.join(log_summary)}.")

    # MODIFIED List Update Trigger: Only depends on DB removal now
    if db_removed:
        print(f"hcleave: Triggering list update for {target_identifier} (DB removed: {db_removed}).")
        asyncio.create_task(update_static_list_message(guild))

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
        asyncio.create_task(update_static_list_message(guild))

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
        asyncio.create_task(update_static_list_message(guild))
    # else: Error already logged by upsert_activity_log if it failed internally

# --- Active Command (MODIFIED: No date, Manage Server perm required) ---
@tree.command(name="active", description="Mark an In-Game Name (IGN) as active for today.") # MODIFIED Description
@app_commands.describe(
    ingame_name="The In-Game Name (IGN) to mark active."
    # REMOVED date description
)
@app_commands.autocomplete(ingame_name=ign_autocomplete) # REMOVED date autocomplete
@app_commands.checks.has_permissions(manage_guild=True) # ADDED Permission Check
# VV Ensure this 'async' keyword is present VV
# MODIFIED: Removed 'date: str' parameter
async def active(interaction: discord.Interaction, ingame_name: str):
    guild = interaction.guild
    if not await check_supabase_available(interaction): return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    await interaction.response.defer(thinking=True, ephemeral=False)

    # MODIFIED: Get today's date by default, no date string needed
    activity_date, date_error = get_utc_date()
    # REMOVED check for date_error specifically from parsing, but kept check if date fetch failed internally
    if not activity_date:
         await interaction.followup.send("❌ Could not determine today's activity date.", ephemeral=False)
         await log_error(guild, f"/active internal error: Failed to get today's date", interaction=interaction) # Log internal error
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
        asyncio.create_task(update_static_list_message(guild))


# --- Alias Command /a for /active ---
@tree.command(name="a", description="Alias for /active: Mark an IGN as active for a specific date.") # New command name "a"
@app_commands.describe( # Use the SAME descriptions as /active
    ingame_name="The In-Game Name (IGN) to mark active.",
    date="Date of activity (Select from list)."
)
@app_commands.autocomplete( # Use the SAME autocomplete functions as /active
    ingame_name=ign_autocomplete,
    date=activity_date_autocomplete
)
# Optional: Add permission checks if /active has them
# @app_commands.checks.has_permissions(...)
# Function name MUST be different from the original 'active'
async def active_alias(interaction: discord.Interaction, ingame_name: str, date: str):
    """Handles the /a alias by calling the /active command's logic."""
    # Directly call the implementation of the original /active command
    # Pass the interaction and all arguments along
    await active(interaction, ingame_name, date)


# --- Inactive Command (CORRECTED DECORATOR and Date Handling) ---
@tree.command(name="inactive", description="Remove an activity record for an IGN on a specific date.")
@app_commands.describe(
    ingame_name="The In-Game Name (IGN) to mark inactive.",
    # MODIFIED: Changed description, date is now required via autocomplete
    date="Date of activity to remove (Select from list)."
)
@app_commands.autocomplete(ingame_name=ign_autocomplete, date=activity_date_autocomplete) # ADDED date autocomplete
# @app_commands.checks.has_permissions(manage_roles=True) # Optional permission check
# MODIFIED: date type is now str (required), removed Optional and default
async def inactive(interaction: discord.Interaction, ingame_name: str, date: str):
    guild = interaction.guild
    if not await check_supabase_available(interaction): return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    await interaction.response.defer(thinking=True, ephemeral=False)

    # MODIFIED: No need to check if date is None, it's now required.
    activity_date, date_error = get_utc_date(date)
    if date_error:
        await interaction.followup.send(f"❌ Error parsing selected date: {date_error}", ephemeral=False)
        return
    if not activity_date:
         await interaction.followup.send("❌ Could not determine activity date from selection.", ephemeral=False)
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
        asyncio.create_task(update_static_list_message(guild))
    elif prefix == "ℹ️":
         await log_info(guild, f"`{interaction.user}` used /inactive for {display_target} on {format_date_dmy(activity_date)}. No record found.")


# --- Bulk Active Command (MODIFIED: No date, Manage Server perm required) ---
@tree.command(name="bulkactive", description="Mark multiple members active for today via IGNs using a modal.") # MODIFIED Description
# REMOVED date describe
# REMOVED date autocomplete decorator entirely
@app_commands.checks.has_permissions(manage_guild=True) # ADDED Permission Check
# MODIFIED: Removed 'date: str' parameter
async def bulkactive(interaction: discord.Interaction):
    # MODIFIED: Pass None to the modal constructor, indicating no specific date was provided.
    modal = BulkActiveModal(date_str=None)
    await interaction.response.send_modal(modal)


# --- REVISED /hcmembers Command ---
@tree.command(name="hcmembers", description="Show interactive list of [HC1] members (Discord/DB data).")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    # --- Initial Checks ---
    if not await check_supabase_available(interaction):
        try: # Attempt cleanup if deferred
            if interaction.response.is_done(): await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        except (discord.NotFound, discord.HTTPException): pass
        return
    if not guild:
        # Allow command in DMs or other contexts, but treat as non-target guild
        current_guild_id = None
        print("/hcmembers: Command used outside a guild context.")
    else:
        current_guild_id = guild.id

    is_target_guild = current_guild_id == TARGET_GUILD_ID

    # --- Defer Publicly ---
    # Defer early before potentially long data fetch
    await interaction.response.defer(thinking=True, ephemeral=False)

    # --- Channel Check (only relevant if in a guild) ---
    # Perform check *after* deferral
    if guild and not is_target_guild: # If in a guild, but not Catercord
        # Log info but allow command to proceed with DB-only data
        await log_info(guild, f"/hcmembers used by `{interaction.user}` in non-target guild {guild.name} ({guild.id}). Showing DB data only.")
    elif guild and is_target_guild: # If in Catercord guild
         # Check allowed channels ONLY if in Catercord
         if interaction.channel_id not in ALLOWED_CHANNEL_IDS and interaction.user.id != SELF_PROTECTED_ID:
             allowed_mentions = [f"<#{ch_id}>" for ch_id in ALLOWED_CHANNEL_IDS if guild.get_channel(ch_id)]
             msg = f"❌ In this server, the command only works in: {', '.join(allowed_mentions) or 'configured channels'}"
             await log_info(guild, f"User `{interaction.user}` attempted /hcmembers in disallowed channel {interaction.channel.mention if interaction.channel else interaction.channel_id} within target guild.")
             # Edit the deferred response
             await interaction.edit_original_response(content=msg, embed=None, view=None)
             return
         else:
             # Log successful use in allowed channel/by owner
             log_detail = ""
             if interaction.user.id == SELF_PROTECTED_ID and interaction.channel_id not in ALLOWED_CHANNEL_IDS:
                 log_detail = " (Protected user bypass)"
             await log_info(guild, f"/hcmembers used by `{interaction.user}` in {interaction.channel.mention if interaction.channel else 'N/A'}{log_detail} (Target Guild).")
    # Else (outside a guild entirely): No channel check needed, proceed with DB data

    # --- Data Fetching based on Context ---
    try:
        data_for_view = []
        total_count = 0
        initial_fetch_error = False

        if is_target_guild:
            print("/hcmembers: Running in Target Guild context.")
            # Fetch data using the original function that includes Discord context
            original_data, total_count = await fetch_hc_member_data(guild) # Fetches all-time activity initially

            if not original_data:
                embed = create_embed(title=HC_LIST_EMBED_TITLE, description="No HC members found matching roles/DB.", color=discord.Color.orange())
                await interaction.edit_original_response(embed=embed, view=None)
                return

            # Fetch initial data for the default view (Monthly Activity) - Keep this logic
            initial_display_data = list(original_data)
            try:
                today_utc = datetime.datetime.now(pytz.utc).date()
                end_date_monthly = today_utc
                start_date_monthly = today_utc - datetime.timedelta(days=29)
                all_igns = [item['ign'] for item in original_data if item.get('ign')]

                if all_igns:
                    print(f"/hcmembers (Target Guild): Fetching initial monthly activity...")
                    monthly_activity_data = await fetch_activity_data(guild, all_igns, start_date_monthly, end_date_monthly)
                    print(f"/hcmembers (Target Guild): Fetched monthly activity.")
                    temp_data = []
                    for item in original_data:
                        ign_lower = item.get('ign', '').lower()
                        activity_info = monthly_activity_data.get(ign_lower, {'count': 0, 'last_seen': None})
                        updated_item = item.copy()
                        updated_item['activity_count'] = activity_info['count']
                        updated_item['last_seen'] = activity_info['last_seen']
                        temp_data.append(updated_item)
                    initial_display_data = temp_data
                else:
                    print("/hcmembers (Target Guild): No IGNs found, skipping initial monthly fetch.")
            except Exception as fetch_err:
                 await log_error(guild, "Failed to fetch initial monthly activity for /hcmembers (Target Guild)", error=fetch_err, interaction=interaction)
                 initial_display_data = list(original_data) # Fallback to original data

            # Set the data for the view in this context
            data_for_view = initial_display_data
            # Pass original_data as well for the view to hold base info
            original_data_param = original_data

        else: # Outside Target Guild (or no guild context)
            print("/hcmembers: Running in Non-Target Guild / DM context.")
            # Fetch data using the new Supabase-only function
            # Pass guild object if available for logging context inside fetch function
            supabase_only_data, total_count = await fetch_all_supabase_hc_data(guild)

            if not supabase_only_data:
                embed = create_embed(title="HC Database Members (All)", description="No members found in the HC database.", color=discord.Color.orange())
                await interaction.edit_original_response(embed=embed, view=None)
                return

            # In this context, the fetched data IS the only data set.
            data_for_view = supabase_only_data
            # Pass the same list for both initial display and "original" base data
            original_data_param = supabase_only_data


        # --- Create and Send View ---
        # Pass the context flag to the view constructor
        view = HCPagesView(
            original_data=original_data_param,
            initial_display_data=data_for_view, # Use the prepared data
            total_members=total_count,
            guild=guild, # Pass guild if available
            is_catercord_context=is_target_guild # Pass the flag
        )
        initial_embed = view.create_page_embed()
        message = await interaction.edit_original_response(embed=initial_embed, view=view)
        view.message = message # Link message to view

    # --- Error Handling ---
    except ConnectionError as e:
        await log_error(guild, "/hcmembers DB connection error", error=e, interaction=interaction, ping_owner=True)
        try: await interaction.edit_original_response(content=None, embed=create_embed("❌ Database Connection Error.", discord.Color.red()), view=None)
        except (discord.NotFound, discord.HTTPException): pass
    except APIError as e:
        await log_error(guild, "/hcmembers Supabase API error", error=e, interaction=interaction, ping_owner=True)
        try: await interaction.edit_original_response(content=None, embed=create_embed("❌ Database API Error.", discord.Color.red()), view=None)
        except (discord.NotFound, discord.HTTPException): pass
    except Exception as e:
        await log_error(guild, "Unhandled /hcmembers error", error=e, interaction=interaction, ping_owner=True)
        try: await interaction.edit_original_response(content=None, embed=create_embed("❌ An unexpected error occurred.", discord.Color.red()), view=None)
        except (discord.NotFound, discord.HTTPException): pass

@tree.command(name="refresh", description="Manually refresh the interactive [HC1] list message.") # Updated description
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    guild = interaction.guild
    # ... (keep initial checks: supabase, guild, channel config) ...

    await interaction.response.defer(thinking=True, ephemeral=False) # Defer publicly

    try:
         # Send immediate feedback using followup
         list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID) # Assume valid from checks
         await interaction.followup.send(f"⏳ Starting interactive list refresh in {list_channel.mention if list_channel else 'the list channel'}...", ephemeral=False)
    except Exception as e_followup:
         await log_error(guild, "Failed initial refresh followup", error=e_followup, interaction=interaction)


    try:
        await log_info(guild, f"Manual interactive static list refresh initiated by `{interaction.user}`.")
        # --- Run the NEW update function ---
        await update_static_list_message(guild) # <--- CHANGE HERE
        # --- Update complete ---

        # Edit the original deferred response to show completion
        await interaction.edit_original_response(content=f"✅ Interactive list refresh complete in {list_channel.mention if list_channel else 'the list channel'}.", embed=None, view=None) # Clear embed/view
        await log_info(guild, f"Refresh command confirmed complete for user {interaction.user}.")

    except Exception as e:
        await log_error(guild, "Error during /refresh process execution", error=e, interaction=interaction)
        try:
            await interaction.edit_original_response(content=f"❌ An error occurred during refresh.", embed=None, view=None)
        except Exception: pass

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

    # ... (keep member fetching logic) ...
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

    hc_member_ids = [str(m.id) for m in hc_members]

    # ... (keep IGN fetching logic) ...
    await interaction.edit_original_response(content=f"{loading_emoji} Fetching IGN data for {total_hc_members} members...")
    ign_data = {} # discord_id (str) -> ingame_name (str)
    try:
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

    # ... (keep nickname update logic) ...
    await interaction.edit_original_response(content=f"{loading_emoji} Syncing {total_hc_members} members...")
    counts = {'proc': 0, 'upd': 0, 'skip_match': 0, 'skip_no_ign': 0, 'skip_empty': 0, 'skip_hier': 0, 'fail_forbid': 0, 'fail_http': 0, 'fail_other': 0}
    bot_member = guild.me
    bot_pos = bot_member.top_role.position
    last_prog_update_time = asyncio.get_event_loop().time()
    update_interval = 5.0

    for idx, member in enumerate(hc_members):
        counts['proc'] += 1
        member_id_str = str(member.id)
        if bot_pos <= member.top_role.position:
            counts['skip_hier'] += 1
            continue
        stored_ign = ign_data.get(member_id_str)
        if not stored_ign:
            counts['skip_no_ign'] += 1
            continue
        target_nick = stored_ign.strip()
        if not target_nick:
            counts['skip_empty'] += 1
            continue
        target_nick = target_nick[:32]
        if member.nick == target_nick:
            counts['skip_match'] += 1
            continue
        try:
            await member.edit(nick=target_nick, reason=f"Nickname Sync initiated by {interaction.user.id}")
            counts['upd'] += 1
            await asyncio.sleep(0.2)
        except discord.Forbidden: counts['fail_forbid'] += 1
        except discord.HTTPException as e_http:
            counts['fail_http'] += 1
            if e_http.status == 429: print(f"SyncNick ({guild.name}): Rate limit hit!")
        except Exception as e_other:
            counts['fail_other'] += 1
            await log_error(guild, f"SyncNick: Unexpected error updating nick for {member.mention}", error=e_other, interaction=interaction)

        now = asyncio.get_event_loop().time()
        if (now - last_prog_update_time > update_interval) or (counts['proc'] == total_hc_members):
             if interaction.is_expired():
                  print(f"SyncNick ({guild.name}): Interaction expired, cannot update progress.")
                  last_prog_update_time = now + 999
                  continue
             try:
                await interaction.edit_original_response(content=f"{loading_emoji} Syncing... ({counts['proc']}/{total_hc_members})")
                last_prog_update_time = now
             except (discord.NotFound, discord.HTTPException):
                print(f"SyncNick ({guild.name}): Progress update failed. Continuing sync...")
                last_prog_update_time = now + 999


    # 4. Send Final Summary
    end_time = discord.utils.utcnow()
    duration = (end_time - start_time).total_seconds()

    # --- MODIFIED EMBED CREATION ---
    # Get Unix timestamp from the datetime object
    end_unix_ts = int(end_time.timestamp())
    # Create embed without the timestamp attribute
    summary_embed = discord.Embed(title="✅ Nickname Sync Complete!", color=NERDY_YELLOW)
    # --- END MODIFIED EMBED CREATION ---

    total_skipped = counts['skip_match'] + counts['skip_no_ign'] + counts['skip_empty'] + counts['skip_hier']
    total_failed = counts['fail_forbid'] + counts['fail_http'] + counts['fail_other']
    summary_lines = [
        f"⏱️ **Duration:** {duration:.2f} seconds",
        f"👥 **Total HC Members Found:** {total_hc_members}",
        f"📊 **Relevant IGNs Fetched:** {len(ign_data)}",
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

    # --- MODIFIED FOOTER ---
    # Add the dynamic timestamp to the footer
    summary_embed.set_footer(text=f"Completed: <t:{end_unix_ts}:R>")
    # REMOVED: summary_embed.timestamp = end_time
    # --- END MODIFIED FOOTER ---

    # ... (keep the final sending logic) ...
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
        await log_error(guild, "SyncNick: Could not send final summary to user.", embed=summary_embed, interaction=interaction)
    except Exception as e_outer:
        print(f"SyncNick ({guild.name}): Unknown error sending final summary: {e_outer}")
        await log_error(guild, "SyncNick: Unknown error sending final summary.", error=e_outer, embed=summary_embed, interaction=interaction)

    # Log detailed summary internally
    log_embed = discord.Embed(title="Nickname Sync Finished", description="\n".join(summary_lines), color=NERDY_YELLOW)
    # Add dynamic timestamp to log embed footer as well
    log_embed.set_footer(text=f"Initiated by {interaction.user} | Completed: <t:{end_unix_ts}:R>")
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
