# -*- coding: utf-8 -*-
# --- LLM INSTRUCTION ---
# (Please do not remove this comment block. Read it carefully before making changes.)
#
# STYLE GUIDELINES FOR CODE MODIFICATIONS:
#
# 1.  **PRIMARY METHOD: FULL FUNCTION REPLACEMENT**
#     - When a function is modified, please provide the *entire function* in your response.
#     - This helps ensure accuracy and minimizes integration errors.
#
# 2.  **HANDLING VERY LONG FUNCTIONS WITH MINOR CHANGES:**
#     - If a function is exceptionally long (e.g., over 150-200 lines) and only
#       a small, clearly definable portion is changed:
#       1.  Mark the beginning and end of significant *unchanged* blocks of code
#           within that function using comments like:
#           ```python
#           # // --- UNCHANGED SECTION (A) --- //
#           # <original, unchanged code block>
#           # // --- END UNCHANGED SECTION (A) --- //
#           ```
#       2.  In your narrative, *explicitly state* that "SECTION (A) (and B, C, etc.)
#           remains unchanged."
#       3.  Provide the rest of the function's code (the parts that *are* new or modified,
#           plus the surrounding structure) in full.
#     - **Use this method sparingly.** Prefer providing the whole function if the
#       changes are complex or spread out, even if it's long. The goal is clarity
#       and ease of integration.
#
# 3.  **ADDING NEW FUNCTIONS OR CLASSES:**
#     - Provide the complete new function or class.
#     - Indicate clearly where it should be placed (e.g., "Add this new function
#       after the `existing_function_name()` function.").
#
# 4.  **REMOVING FUNCTIONS OR CLASSES:**
#     - Clearly state: "Remove the `function_to_remove_name()` function entirely."
#
# 5.  **GLOBAL SCOPE CHANGES (Imports, Constants):**
#     - For changes to imports or global constants, clearly list the additions,
#       removals, or modifications. For example:
#       - "Add `import new_module` at the top."
#       - "Change `MY_CONSTANT = 10` to `MY_CONSTANT = 20`."
#       - "Remove the constant `OLD_CONSTANT`."
#
# 6.  **NO META-COMMENTS ABOUT UNCHANGED CODE (Unless Marked as Above):**
#     - **DO NOT** include comments like `# ... rest of the code ...` or
#       `# Your existing code here` within the code you provide, *unless*
#       it's part of a formally marked "UNCHANGED SECTION" as described in point 2.
#     - The code you provide should be directly usable.
#
# 7.  **FULL FILE REWRITES ARE STRICTLY PROHIBITED:**
#     This `bot.py` file is large and complex. Under no circumstances should you
#     attempt to rewrite the entire file. Only provide the specific functions,
#     classes, or import/constant changes requested.
#
# 8.  **INTEGRITY OF EXISTING COMMENTS:**
#     - When providing a modified function, ensure that all original comments
#       within that function (that are intended to remain) are preserved in their
#       correct positions.
#
# --- BOT CONTEXT (TheNerd's Pingslave) ---
# (This information is for your understanding and may be useful for generating accurate code.)
#
# Bot Name: TheNerd's Pingslave (also referred to as Sweet Honey Bot by the user)
# Owner: Vibhor / TheNerd / sweet_honey (Discord ID: 1230848174218940416)
# Target Server: Catercord (This bot is primarily intended for use only in this specific server)
# Primary Purpose: Manage verification and information related to the "[HC1]" guild within the game Florr.io.
#   - "[HC1]" is a guild in Florr.io.
#   - The bot verifies members, stores their in-game names (IGNs) in Supabase,
#     maintains an interactive list of HC members, and offers utility commands.
# Hosting Environment:
#   - Code Files: `bot.py` (this file), `ai_cog.py`, `requirements.txt` (listing discord.py, supabase, Flask, google-generativeai, Pillow, python-dateutil, pytz, aiohttp).
#   - Platform: Render (Free Tier) via a private GitHub repository.
#   - Keep-Alive: Uses a basic Flask web server (`keep_alive` function) monitored by an external
#     service (like Uptime Robot) hitting the Flask endpoint.
#   - Environment Variables: DISCORD_BOT_MAIN_TOKEN, SUPABASE_URL, SUPABASE_ADMIN_KEY, GEMINI_API_KEY are set in Render.
# Database: Supabase (PostgreSQL) used for:
#   - `hc_members`: Stores HC member IGNs linked to Discord IDs and names.
#   - `activity_log`: Tracks daily member activity.
#   - `keyword_phrases`: Stores configurations for AI keyword-triggered responses (managed by `ai_cog.py`).
# Key Features (not exhaustive, check `/nerdhelp` in code for command list):
#   - Verification & HC Management: `/verify`, `/unverify`, `/hcverify`, `/hconly`, `/hcleave`.
#   - Listing & Activity: Interactive static list in `HC_MEMBER_LIST_CHANNEL_ID` (updated by `update_static_list_message`),
#     `/hcmembers`, `/active`, `/inactive`, `/activatemyself`, screenshot processing for activity.
#   - Utilities: `/syncnicknames`, `/wither`, `/message` (optional AI), `/florr` (custom avatar msg), `/refresh`.
#   - AI Features: Primarily handled by `ai_cog.py` (see details below).
#
# --- AI COG (`ai_cog.py`) OVERVIEW & INTERACTIONS ---
# (This bot uses a separate `ai_cog.py` file for most AI functionalities.)
#
# The `ai_cog.py` is responsible for:
# 1.  **AI Model Interaction (Google Gemini):**
#     - Interfaces with Google's Gemini models (e.g., Gemini 2.5 Flash, Gemini 2.0 Flash)
#       using the `google-generativeai` library.
#     - Manages model selection, fallbacks, and API calls for text and image-based generation.
# 2.  **Keyword-Triggered Responses:**
#     - Loads keyword rules from the `keyword_phrases` table in Supabase. Each rule defines
#       matching regex, AI instructions, and discovery status.
#     - Detects keyword matches in user messages (in allowed contexts) and generates themed AI responses.
#     - Handles "discovery" of new keywords (first-time trigger) and records it.
#     - The `/addkeyword` and `/discoveries` commands are part of this cog.
# 3.  **Image Analysis (Florr.io IGN Extraction for Screenshots):**
#     - The `on_message` event in `bot.py` (specifically for `SCREENSHOTS_DROPBOX_CHANNEL_ID`)
#       calls `AICog.get_ai_response_with_image()`.
#     - This method uses an AI model to analyze Florr.io screenshots and extract online player IGNs.
#     - The prompt `FLORR_IMAGE_NAME_EXTRACTION` (in `ai_cog.py`) and a list of known IGNs
#       (passed as `ai_cog.ingame_name_cache_ref` from `bot.py`, which refers to `bot.ingame_name_cache`)
#       are used to guide the AI.
# 4.  **AI for `/message` Command (in `bot.py`):**
#     - When the `/message` command in `bot.py` is used with the AI option, it calls
#       `AICog.get_ai_response()` with the user's prompt.
#     - It typically uses the `HUMAN_SYSTEM_INSTRUCTION_V3` prompt from `ai_cog.py`.
# 5.  **General AI Chat & "Mob Mode":**
#     - The `on_message` listener in `ai_cog.py` handles:
#       - Responding to messages in "Always-On AI Channels".
#       - Responding to direct replies to the bot or mentions of the bot (with channel/context restrictions).
#       - A chance-based "Mob Mode" in Always-On channels, where the AI adopts a Florr.io mob persona
#         using a custom avatar (from `Mobs` folder, path configured in `bot.py`) and a specific
#         system instruction (`MOB_PERSONA_SYSTEM_INSTRUCTION_V2`).
# 6.  **Configuration and Initialization (`ai_cog.py`'s `setup` function):**
#     - `bot.py` loads `ai_cog.py` as an extension (in `on_ready`).
#     - The `setup()` function in `ai_cog.py` receives the `bot` instance and a `config` dictionary.
#     - This `config` dictionary is populated in `bot.py`'s `on_ready` with various constants and references:
#       - `GEMINI_API_KEY`.
#       - Discord IDs: `OWNER_USER_ID`, `CATERCORD_GUILD_ID`, etc.
#       - Channel collections/IDs: `ALWAYS_ON_AI_CHANNELS`, `STAFF_CHANNELS`, etc.
#       - Bot utilities: `COMMAND_PREFIX`, `NERDY_YELLOW`.
#       - Shared data/paths: `ingame_name_cache_ref`, `MOBS_FOLDER_PATH_config`.
#       - Core services: Supabase client (`bot.supabase_client`), logging functions
#         (`bot.log_info_global`, `bot.log_error_global`), `bot.run_supabase_sync_global`.
# 7.  **Data Reload (`/refresh` command in `bot.py`):**
#     - The `/refresh` command in `bot.py` calls `AICog.load_keyword_data()` to refresh the
#       keyword rules from Supabase.
#
# When making changes in `bot.py` that relate to these AI features (e.g., how prompts are
# constructed, how AI cog methods are called, or data passed to the cog), consider if
# `ai_cog.py` also needs adjustment and mention this in your reasoning.
# --- END LLM INSTRUCTION ---

import discord # Keep your original discord import
import os      # <--- Ensure this import is present
import threading
import asyncio
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, button
from flask import Flask
from supabase import create_client, Client
from postgrest import APIError
import traceback
import math
from typing import Optional, Tuple, List, Dict, Any, Set, Union
from dotenv import load_dotenv
import datetime
import pytz
from dateutil.parser import parse as date_parse
from discord.ext import tasks
import re
import asyncio
import discord.utils
import io
from PIL import Image
import aiohttp
import contextlib
import difflib


# --- Configuration ---
load_dotenv()  # harmless in production; only loads if a .env file exists
MAIN_TOKEN = os.getenv("MAIN_DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ADMIN_KEY = os.getenv("SUPABASE_ADMIN_KEY")
NEWBEE_ROLE_ID = 1360176495947022447 # "Unverified" role
FLORRIST_ROLE_ID = 1248708073019805717 # "Verified" role
HC1_ROLE_ID = 1230235110415274004 # "HC" role
BOT_COMMANDS_ALLOWED_CHANNEL_IDS = {1330664430148780102, 1248710731407560835} # Channels for /hcmembers
HC_MEMBER_LIST_CHANNEL_ID = 1354431395140731165 # Channel for static list
HC_LIST_EMBED_TITLE = r"**\[HC1\] Guild Members**"
ALLOWED_WITHERER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692} # User IDs for /wither
OWNER_USER_ID = 1230848174218940416 # Protected from /wither
BOT_USER_ID: Optional[int] = None # Bot's own User ID (set in on_ready)
MAX_WITHER_SECONDS = 600 # Max duration for /wither (10 minutes)
ORDINARY_LOGS_CHANNEL_ID = 1317943895606165579 # Info log channel
EXTRAORDINARY_LOGS_CHANNEL_ID = 1362988767367135453 # Error log channel
MEMBERS_PER_PAGE = 50 # Members per page in lists
NERDY_YELLOW = discord.Color.gold() # Embed color
EX_MEMBER_ROLE_ID = 1267882075390873681 # Role to add on HC leave, remove on HC verify
VIEW_MODE_DISCORD = "discord_view"
VIEW_MODE_ACTIVITY_ALL = "activity_all_view" # Renamed for clarity
VIEW_MODE_ACTIVITY_DAILY = "activity_daily_view"
VIEW_MODE_ACTIVITY_WEEKLY = "activity_weekly_view"
VIEW_MODE_ACTIVITY_MONTHLY = "activity_monthly_view" # Using 30 days for simplicity
SORT_MODE_IGN = "sort_ign"
SORT_MODE_ACTIVITY = "sort_activity"
ACTIVITY_COLUMN_WIDTH = 18 # Increase width for "Count (Last Seen)"
COMMAND_PREFIX = "." # Define the prefix
AUTODELETE_DELAY_SECONDS = 5.0
CATERCORD_GUILD_ID = 1200476681803137024 # Catercord server ID
RANDOM_SERVER_ID = 1318657897550577776 # New server ID for special wither logic
WITHERED_ROLE_ID_RANDOM_SERVER = 1370374993287975024 # Special role for wither in RANDOM_SERVER_ID
active_static_list_views: Dict[int, Dict[str, Any]] = {} # channel_id -> {'view': StaticHCPagesView, 'message_id': int, 'task': tasks.Loop}
STATIC_LIST_RESET_TIMEOUT_MINUTES = 5
SORT_MODE_DISCORD_NAME = "sort_discord_name"
PRIVATE_SERVER_ID = 1332980983003349012
STAFF_CHANNELS = set() # Initialize as empty set, will be populated in on_ready
UNRESTRICTED_AI_CHANNEL_ID = 1330664430148780102 # Channel for unrestricted AI use in Catercord
ingame_name_cache: List[str] = [] # Cache for In-Game Names from hc_members
SCREENSHOTS_DROPBOX_CHANNEL_ID = 1359782718426316840 # Channel for image processing
BOT_INSTANCE_TYPE = os.getenv("BOT_INSTANCE_TYPE", "PRODUCTION").upper()
PETALS_FOLDER_NAME = "Petals"
MOBS_FOLDER_NAME = "Mobs"
available_profile_pics_cache: List[Tuple[str, str, str]] = []
PROFILE_PIC_BASE_PATH = "" # Will be set in on_ready to the script's directory
ALWAYS_ON_AI_CHANNELS = {1330664430148780102, 1364657218175107162} # Channels for AI to respond to every message
RARITY_PREFIXES = ["common", "uncommon", "rare", "epic", "legendary", "mythic", "ultra", "super", "unique"]
DISABLE_STATIC_LIST_FOR_TESTING_INSTANCE = (BOT_INSTANCE_TYPE == "TESTING")
PETAL_ABBREVIATIONS = {"ygg": "yggdrasil", "begg": "beetle egg", "beggs": "beetle egg", "pinger": "stinger", "binger": "blood stinger", "minger": "magic stinger"}
SUPER_ATTEMPT_CHANNEL_ID = 1303267777284673566 # Channel for super attempt logging
ZORR_PRO_DESIGNATED_CHANNEL_ID = 1236340209239724115
ZORR_PRO_AUTOMOD_KEYWORD_REGEX = r"(?:(?:z\s*[o0]\s*r(?:\s*r)*)|(?:z\s*[o0]\s*r(?:\s*r)*\s*\.\s*p\s*r\s*[o0])|(?:z\s*[o0]\s*r(?:\s*r)*\s*p\s*r\s*[o0])|(?:r(?:\s*r)*\s*[o0]\s*z)|(?:[o0]\s*r\s*p\s*\.\s*r(?:\s*r)*\s*[o0]\s*z)|(?:[o0]\s*r\s*p\s*r(?:\s*r)*\s*[o0]\s*z))"
AUTOMOD_ALERT_CHANNEL_ID = 1236340209239724115
DISABLE_SUPER_ATTEMPT_LOGGING_FOR_TESTING_INSTANCE = (BOT_INSTANCE_TYPE == "TESTING")
MANUAL_OVERRIDE_SUPER_ATTEMPT_LOGGING_IN_TESTING = False # Set to True to test listener in "TESTING" instance type
guild_sync_sessions: Dict[int, Dict[str, Any]] = {} # User ID -> {'screenshot_igns_collected': Set[str], 'bot_reply_message_id': int, 'last_update_time': datetime.datetime}
GUILD_SYNC_SESSION_TIMEOUT_SECONDS = 1800 # 30 minutes for a session to be considered stale
DEPRECATION_MESSAGE_ACTIVITY = (
    "ℹ️ The 'Activate Myself' feature is being phased out soon.\n\n"
    "The screenshot system in <#{channel_id}> is a more efficient way to track activity for everyone!\n\n"
    "**Quick Screenshot Guide:**\n"
    "1. Press `Ctrl + Shift + S` to capture your Florr.io screen.\n"
    "2. In Discord (in the <#{channel_id}> channel), press `Ctrl + V` to paste and send.\n\n"
    "This method is quick and helps keep activity records accurate. Thanks for your understanding!"
).format(channel_id=SCREENSHOTS_DROPBOX_CHANNEL_ID)



# --- Supabase Client ---
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_ADMIN_KEY:
    try: supabase = create_client(SUPABASE_URL, SUPABASE_ADMIN_KEY); print("Supabase client created successfully.")
    except Exception as e: print(f"CRITICAL: Failed Supabase client creation: {e}"); supabase = None
else: print("CRITICAL: Supabase credentials missing."); supabase = None

# --- Discord Setup ---
intents = discord.Intents.default()
intents.members = True       # You already have this for member events/fetching
intents.message_content = True # <<<--- ADD THIS LINE
intents.auto_moderation_execution = True
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

class GuildSyncInProgressView(discord.ui.View):
    def __init__(self, original_author_id: int, session_id: int): # session_id is user_id
        super().__init__(timeout=GUILD_SYNC_SESSION_TIMEOUT_SECONDS)
        self.original_author_id = original_author_id
        self.session_id = session_id # This is the user's ID, used to find the session
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.original_author_id:
            await interaction.response.send_message("❌ This is not your sync session.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Add 10 More Screenshots", style=discord.ButtonStyle.primary, custom_id="guild_sync_add_more")
    async def add_more_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        session_data = guild_sync_sessions.get(self.session_id)
        if not session_data:
            await interaction.response.send_message("❌ Your sync session seems to have expired or was not found. Please start over by sending 10 screenshots.", ephemeral=True)
            self.stop_view_and_session()
            return

        session_data['last_update_time'] = discord.utils.utcnow()
        await interaction.response.send_message(
            "✅ Okay, I'm ready for your next batch! Please send another message containing exactly 10 more screenshots.",
            ephemeral=True
        )
        # The view on the original message remains, waiting for the next `on_message` trigger.

    @discord.ui.button(label="Finalize & Generate Report", style=discord.ButtonStyle.success, custom_id="guild_sync_finalize")
    async def finalize_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer the interaction publicly, this will show "Bot is thinking..."
        await interaction.response.defer(thinking=True, ephemeral=False) 

        session_data = guild_sync_sessions.get(self.session_id)
        if not session_data or not self.message: # self.message is the bot's message with the buttons
            error_content = "❌ Your sync session was not found or the original message context is missing. Please start over."
            try:
                # This edits the deferred "thinking..." state
                await interaction.edit_original_response(content=error_content, embed=None, view=None)
            except discord.HTTPException: 
                # Fallback if edit_original_response fails (e.g., token expired too fast)
                try: await interaction.followup.send(error_content, ephemeral=True)
                except discord.HTTPException: pass 
            self.stop_view_and_session()
            return

        # Update the message that had the buttons to indicate processing
        for item_comp in self.children: # Renamed 'item' to 'item_comp' to avoid conflict if generate_final_sync_report_embed_only has 'item'
            if isinstance(item_comp, discord.ui.Button): item_comp.disabled = True
        
        status_update_content = f"{interaction.user.mention} ⏳ Finalizing report based on {len(session_data.get('screenshot_igns_collected', []))} collected IGNs..."
        try:
            # Edit the message that had the buttons
            await self.message.edit(content=status_update_content, view=self, embed=None)
        except discord.HTTPException:
            # If this specific edit fails, it's not critical; the main report will still be attempted.
            await log_info(interaction.guild, f"GuildSync: Minor error updating button message to '{status_update_content.split('⏳')[1][:50]}...' for user {self.original_author_id}")


        # Generate the report embed (this function now just returns the embed)
        report_embed = await generate_final_sync_report_embed_only(interaction.guild, interaction.user, self.session_id)

        if report_embed:
            try:
                # Edit the deferred interaction response (which shows "Bot is thinking...") with the final report
                await interaction.edit_original_response(content=f"{interaction.user.mention} Guild Sync Analysis FINAL REPORT:", embed=report_embed, view=None)
                
                # Optionally, update the original button message to confirm report is above/below or remove it
                try:
                    # Delete the message that had the buttons, as the report is now the interaction's response.
                    await self.message.delete(delay=3) 
                    await log_info(interaction.guild, f"GuildSync: Deleted old status message {self.message.id} after final report for user {self.original_author_id}.")
                except discord.HTTPException as e_del_status:
                    await log_info(interaction.guild, f"GuildSync: Could not delete old status message {self.message.id}. Error: {e_del_status}")


            except discord.HTTPException as e_final_send:
                await log_error(interaction.guild, "GuildSync: Failed to send final report via interaction.edit_original_response", error=e_final_send, interaction=interaction)
                # Fallback: try sending report as a new message to the channel if interaction response fails
                try:
                    if self.message and self.message.channel: # self.message is the message that had the buttons
                         await self.message.channel.send(content=f"{interaction.user.mention} Guild Sync Analysis FINAL REPORT (Fallback):", embed=report_embed)
                         # Try to clean up the original status message if possible
                         await self.message.edit(content=f"{interaction.user.mention} Report generated in a new message above/below.", embed=None, view=None)
                except Exception as e_channel_fallback:
                     await log_error(interaction.guild, "GuildSync: Failed to send final report as channel message fallback", error=e_channel_fallback, interaction=interaction)
        else: # Report generation failed or returned None
            error_content_report_fail = "❌ An error occurred while generating the final report. Please check logs or try again."
            try:
                await interaction.edit_original_response(content=error_content_report_fail, embed=None, view=None)
            except discord.HTTPException: pass # If edit fails, not much more can be done here

        self.stop_view_and_session(clear_from_global=True)

    def stop_view_and_session(self, clear_from_global: bool = True):
        self.stop()
        if clear_from_global and self.session_id in guild_sync_sessions:
            del guild_sync_sessions[self.session_id]
            print(f"GuildSync: Cleared session for user {self.session_id}")
        if self.message: # Try to clear buttons from the message if view is stopped
            asyncio.create_task(self.message.edit(view=None))


    async def on_timeout(self):
        session_data = guild_sync_sessions.get(self.session_id)
        user_mention = f"<@{self.original_author_id}>"
        
        timeout_message_content = f"{user_mention} Your guild sync session has timed out due to inactivity."
        
        if session_data and self.message:
            timeout_message_content += f" {len(session_data.get('screenshot_igns_collected', []))} IGNs were collected."
            try:
                # Update the original message to indicate timeout and remove buttons
                for item in self.children:
                    item.disabled = True
                await self.message.edit(content=self.message.content + "\n\n*(Session timed out, buttons disabled.)*", embed=self.message.embeds[0] if self.message.embeds else None, view=self)
            except discord.HTTPException:
                pass # Ignore if message edit fails
        
        # Attempt to send a new message in the channel if the original interaction message is gone or cannot be edited.
        elif self.message and self.message.channel:
            try:
                await self.message.channel.send(timeout_message_content)
            except discord.HTTPException:
                pass
        
        self.stop_view_and_session(clear_from_global=True)
        print(f"GuildSync: Session for user {self.original_author_id} timed out.")


async def process_guild_sync_batch(
    message: discord.Message, # The user's message with screenshots
    valid_image_attachments: List[discord.Attachment],
    is_new_session: bool
) -> Optional[discord.Message]: # Returns the bot's reply message if a new one is sent
    """Processes a batch of screenshots for guild sync, updating or creating a session."""
    guild = message.guild
    user = message.author
    user_id = user.id
    
    ai_cog = bot.get_cog('AICog')
    if not ai_cog:
        await log_error(guild, "GuildSync: AICog not found during batch processing.", message_context=message)
        # If it's a new session, we need to inform the user via a new reply
        if is_new_session:
            try:
                return await message.reply(f"{user.mention} ❌ AI Module error. Sync aborted.")
            except discord.HTTPException: pass
        # If it's an existing session, the view interaction might handle user feedback
        return None

    extracted_from_this_batch: Set[str] = set()
    failed_ai_this_batch = 0
    
    # Use the NEW AI prompt key
    known_igns_list_for_ai = "\n".join(ai_cog.ingame_name_cache_ref) if ai_cog.ingame_name_cache_ref else "No known names provided."

    for image_att in valid_image_attachments:
        try:
            image_bytes = await image_att.read()
            ai_extracted_text = await ai_cog.get_ai_response_with_image(
                prompt_key="FLORR_GUILD_LIST_FULL_EXTRACTION", # Use new prompt
                image_bytes=image_bytes,
                prompt_kwargs={'known_igns_list_str': known_igns_list_for_ai}
            )
            if ai_extracted_text and ai_extracted_text.strip().upper() != "NO_NAMES_FOUND":
                extracted_this_image = {name.strip() for name in ai_extracted_text.split('\n') if name.strip()}
                extracted_from_this_batch.update(extracted_this_image)
            elif not ai_extracted_text:
                failed_ai_this_batch +=1
        except Exception as e_img_proc:
            failed_ai_this_batch +=1
            await log_error(guild, f"GuildSync: Error processing image {image_att.filename} in batch.", error=e_img_proc, message_context=message)

    if is_new_session:
        if not extracted_from_this_batch and failed_ai_this_batch == len(valid_image_attachments):
            return await message.reply(f"{user.mention} ❌ AI failed to extract names from all initial images. Sync aborted.")
        if not extracted_from_this_batch:
            return await message.reply(f"{user.mention} ℹ️ AI did not identify any player names from the initial screenshots. Sync aborted.")

        guild_sync_sessions[user_id] = {
            'screenshot_igns_collected': extracted_from_this_batch,
            'bot_reply_message_id': 0, # Will be set after sending
            'last_update_time': discord.utils.utcnow()
        }
        session_data = guild_sync_sessions[user_id]
        
        reply_content = f"{user.mention} ✅ Initial batch of {len(valid_image_attachments)} images processed. **{len(extracted_from_this_batch)}** unique IGNs collected so far."
        view = GuildSyncInProgressView(user_id, user_id)
        bot_reply_msg = await message.reply(content=reply_content, view=view)
        session_data['bot_reply_message_id'] = bot_reply_msg.id
        view.message = bot_reply_msg # Link message to view for timeout edits
        await log_info(guild, f"GuildSync: New session started for {user.name}. Collected {len(extracted_from_this_batch)} IGNs from first batch.")
        return bot_reply_msg
    else: # Adding to existing session
        session_data = guild_sync_sessions.get(user_id)
        if not session_data: # Should not happen if called correctly
            await log_error(guild, f"GuildSync: Tried to add to non-existent session for user {user_id}.")
            return None 
        
        newly_added_count = len(extracted_from_this_batch - session_data['screenshot_igns_collected'])
        session_data['screenshot_igns_collected'].update(extracted_from_this_batch)
        session_data['last_update_time'] = discord.utils.utcnow()
        
        bot_reply_msg_obj: Optional[discord.Message] = None
        if session_data['bot_reply_message_id']:
            try:
                bot_reply_msg_obj = await message.channel.fetch_message(session_data['bot_reply_message_id'])
            except (discord.NotFound, discord.HTTPException):
                await log_error(guild, f"GuildSync: Could not fetch previous bot reply {session_data['bot_reply_message_id']} to update.")

        update_msg_content = f"{user.mention} ✅ Batch processed. Added **{newly_added_count}** new unique IGNs. **Total collected: {len(session_data['screenshot_igns_collected'])}**."
        if failed_ai_this_batch > 0:
            update_msg_content += f" (Failed to extract from {failed_ai_this_batch} image(s) in this batch)."

        if bot_reply_msg_obj:
            try:
                # Ensure the view is fresh if it's being re-sent or message is edited
                current_view = GuildSyncInProgressView(user_id, user_id)
                current_view.message = bot_reply_msg_obj
                await bot_reply_msg_obj.edit(content=update_msg_content, view=current_view)
                # Update the view instance in GuildSyncInProgressView if necessary, or re-instantiate
                if isinstance(bot_reply_msg_obj.view, GuildSyncInProgressView):
                     bot_reply_msg_obj.view.message = bot_reply_msg_obj # Ensure it's linked
                
            except discord.HTTPException as e_edit:
                await log_error(guild, "GuildSync: Failed to edit bot reply for additional batch.", error=e_edit)
                # Fallback to sending a new message if edit fails, though this can clutter.
                # For now, log and user might have to finalize if edit fails.
        else: # No previous message to edit, this implies an issue. User might need to re-initiate or finalize.
             await message.reply(f"{user.mention} Processed batch, but couldn't update previous status message. Total collected so far: {len(session_data['screenshot_igns_collected'])}.")


        await log_info(guild, f"GuildSync: Added {newly_added_count} IGNs to session for {user.name}. Total: {len(session_data['screenshot_igns_collected'])}. Failures this batch: {failed_ai_this_batch}")
        return bot_reply_msg_obj # Or None if not fetched/edited


async def generate_final_sync_report_embed_only(guild: Optional[discord.Guild], user: discord.User, user_id_session_key: int) -> Optional[discord.Embed]:
    """Generates the final guild sync report embed. Returns Embed or None on failure or if no data."""
    # user_id_session_key is the key for guild_sync_sessions

    session_data = guild_sync_sessions.get(user_id_session_key)
    if not session_data:
        if guild: await log_error(guild, f"GuildSync Report Gen: Session data not found for user ID {user_id_session_key}.")
        else: print(f"GuildSync Report Gen: Session data not found for user ID {user_id_session_key} (No guild context).")
        return None # Cannot generate report

    collected_screenshot_igns = session_data.get('screenshot_igns_collected', set()) # Default to empty set
    
    if not collected_screenshot_igns:
        log_ctx = f"user {user.display_name} ({user_id_session_key})"
        if guild: await log_info(guild, f"GuildSync Report Gen: No IGNs collected for {log_ctx}.")
        else: print(f"GuildSync Report Gen: No IGNs collected for {log_ctx} (No guild context).")
        return discord.Embed(title="Guild Sync Report", description="No IGNs were collected from screenshots. Cannot generate a comparison.", color=discord.Color.orange())

    log_ctx_start = f"{user.display_name} ({user_id_session_key})"
    if guild: await log_info(guild, f"GuildSync Report Gen: Starting for {log_ctx_start}. {len(collected_screenshot_igns)} IGNs from screenshots.")
    else: print(f"GuildSync Report Gen: Starting for {log_ctx_start}. {len(collected_screenshot_igns)} IGNs from screenshots (No guild context).")


    db_members_with_status = await fetch_all_db_hc_members_with_status(guild)
    
    # --- Detailed Comparison Logic ---
    ss_igns_lower = {ign.lower() for ign in collected_screenshot_igns}
    db_map_lower_to_original: Dict[str, Dict[str, Any]] = {entry['ingame_name'].lower(): entry for entry in db_members_with_status}

    in_ss_not_in_db_at_all: List[str] = []
    in_ss_and_db_not_hc: List[str] = [] 
    in_db_hc_not_in_ss: List[str] = [] 

    for s_ign in collected_screenshot_igns:
        s_ign_l = s_ign.lower()
        db_entry = db_map_lower_to_original.get(s_ign_l)
        if not db_entry:
            in_ss_not_in_db_at_all.append(s_ign)
        elif db_entry.get('is_in_hc') is False: # Explicitly check for False
            in_ss_and_db_not_hc.append(s_ign)
        # If in SS and in DB with is_in_hc=True or is_in_hc=None (treat None as not actively in HC for this report)
        # it's a match or handled by other categories.

    for db_ign_l, db_entry_data in db_map_lower_to_original.items():
        if db_entry_data.get('is_in_hc') is True: # Only consider those marked as IN HC in DB
            if db_ign_l not in ss_igns_lower: # Check if this DB HC member is NOT in the screenshot list
                in_db_hc_not_in_ss.append(db_entry_data['ingame_name']) # Add original casing

    # Pass the original list of dicts to find_potential_ign_typos
    potential_typos = find_potential_ign_typos(collected_screenshot_igns, db_members_with_status)
    # --- End Detailed Comparison Logic ---

    # --- Build Report Embed ---
    report_embed = discord.Embed(
        title=f"Guild Member Sync Report (Finalized by {user.display_name})",
        description=(
            f"Processed screenshots from your session, collecting **{len(collected_screenshot_igns)}** unique IGNs.\n"
            f"Compared against **{len(db_members_with_status)}** total entries in the member database."
        ),
        color=NERDY_YELLOW
    )
    report_embed.timestamp = discord.utils.utcnow()

    def format_field_value(items: List[str], max_items_display=15) -> str:
        if not items: return "None found."
        display_count = len(items)
        items_sorted = sorted(items, key=str.lower) # Sort for consistent display
        lines = [f"- `{discord.utils.escape_markdown(ign)}`" for ign in items_sorted[:max_items_display]]
        value = "\n".join(lines)
        if display_count > max_items_display:
            value += f"\n- ...and {display_count - max_items_display} more."
        return value

    if in_ss_not_in_db_at_all:
        report_embed.add_field(
            name=f"️⚠️ In Screenshots, NOT IN DB ({len(in_ss_not_in_db_at_all)})",
            value=format_field_value(in_ss_not_in_db_at_all), inline=False
        )
    if in_ss_and_db_not_hc:
        report_embed.add_field(
            name=f"🟡 In Screenshots, IN DB but Marked NOT HC ({len(in_ss_and_db_not_hc)})",
            value=format_field_value(in_ss_and_db_not_hc), inline=False
        )
    if in_db_hc_not_in_ss: # This now correctly lists DB members marked 'is_in_hc: True' not found in screenshots
        report_embed.add_field(
            name=f"❓ IN DB (Active HC), NOT IN SCREENSHOTS ({len(in_db_hc_not_in_ss)})",
            value=format_field_value(in_db_hc_not_in_ss), inline=False
        )
    
    if potential_typos:
        typo_lines = []
        for s_ign, d_ign, db_is_hc, score in potential_typos[:10]: # Show top 10 typos
            hc_status_indicator = "(HC)" if db_is_hc else "(Not HC)"
            typo_lines.append(f"- SS: `{discord.utils.escape_markdown(s_ign)}` vs DB: `{discord.utils.escape_markdown(d_ign)}` {hc_status_indicator} ({score*100:.1f}%)")
        
        typo_field_val = "\n".join(typo_lines)
        if not typo_field_val: typo_field_val = "None significant found." # Message if list empty
        if len(potential_typos) > 10:
            typo_field_val += f"\n- ...and {len(potential_typos) - 10} more potential typos."
        report_embed.add_field(name=f"🤔 Potential Typos/Capitalization ({len(potential_typos)})", value=typo_field_val, inline=False)

    if not report_embed.fields and (not in_ss_not_in_db_at_all and not in_ss_and_db_not_hc and not in_db_hc_not_in_ss and not potential_typos):
        # Only add "All Clear" if all lists are empty
        report_embed.description += "\n\n✅ **All Clear!** No major discrepancies identified between screenshot names and active HC database members based on these categories."

    report_embed.set_footer(text="Use /hcverify, /hcleave, /hconly to correct DB. AI extracts all names from guild list screenshots for this mode.")
    # --- End Build Report Embed ---
    
    # Logging moved to the caller after it successfully sends the report
    # This function now just returns the embed
    return report_embed

async def fetch_all_db_hc_members_with_status(guild: Optional[discord.Guild]) -> List[Dict[str, Any]]:
    """
    Fetches all HC members from Supabase, including their ingame_name, discord_id, and is_in_hc status.
    Returns a list of dicts, e.g., {'ingame_name': 'Player1', 'discord_id': '123...', 'is_in_hc': True}
    """
    if not supabase:
        if guild: await log_error(guild, "GuildSync: Supabase unavailable for fetching DB HC members with status.")
        return []
    
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("ingame_name, discord_id, is_in_hc")
                           # .eq("is_in_hc", True) # Fetch ALL members to check their status, not just active ones
                           .not_.is_("ingame_name", "null")
                           .execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            return [
                {
                    'ingame_name': entry['ingame_name'],
                    'discord_id': str(entry['discord_id']) if entry.get('discord_id') else None,
                    'is_in_hc': entry.get('is_in_hc')
                }
                for entry in resp.data if entry.get('ingame_name')
            ]
        return []
    except Exception as e:
        if guild: await log_error(guild, "GuildSync: Error fetching all HC members with status from DB", error=e)
        return []

async def fetch_all_db_hc_members_for_sync(guild: Optional[discord.Guild]) -> List[str]:
    """Fetches all In-Game Names from hc_members where is_in_hc is TRUE."""
    if not supabase:
        if guild: await log_error(guild, "GuildSync: Supabase unavailable for fetching DB HC members.")
        return []
    
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("ingame_name")
                           .eq("is_in_hc", True)
                           .not_.is_("ingame_name", "null") # Ensure IGN is not null
                           .execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            return [entry['ingame_name'] for entry in resp.data if entry.get('ingame_name')]
        return []
    except Exception as e:
        if guild: await log_error(guild, "GuildSync: Error fetching all HC members from DB", error=e)
        return []

def find_potential_ign_typos(screenshot_igns: Set[str], db_igns_with_status: List[Dict[str, Any]], threshold: float = 0.85) -> List[Tuple[str, str, bool, float]]:
    """
    Compares screenshot IGNs to DB IGNs, finds potential typos.
    Returns: List of (screenshot_ign, db_ign, db_ign_is_in_hc, score)
    """
    potential_typos = []
    
    db_ign_names_only_set = {entry['ingame_name'] for entry in db_igns_with_status}
    unique_screenshot_igns = screenshot_igns - db_ign_names_only_set # Focus on SS IGNs not exact in DB

    for s_ign in unique_screenshot_igns:
        # Create a list of (db_ign_name, db_ign_is_in_hc) for matching
        db_ign_tuples_for_matching = [(entry['ingame_name'], entry.get('is_in_hc', False)) for entry in db_igns_with_status]
        
        # Use process.extractBests from fuzzywuzzy or similar if available and more performant for large lists
        # For now, using difflib's get_close_matches on names and then looking up status
        
        best_db_name_matches = difflib.get_close_matches(s_ign, [t[0] for t in db_ign_tuples_for_matching], n=1, cutoff=threshold)
        
        if best_db_name_matches:
            best_db_name_match_str = best_db_name_matches[0]
            # Find the full entry for this matched DB name to get its 'is_in_hc' status
            matched_db_entry = next((entry for entry in db_igns_with_status if entry['ingame_name'] == best_db_name_match_str), None)
            if matched_db_entry:
                db_ign_is_in_hc = matched_db_entry.get('is_in_hc', False)
                ratio = difflib.SequenceMatcher(None, s_ign, best_db_name_match_str).ratio()
                if ratio >= threshold : # Double check
                    potential_typos.append((s_ign, best_db_name_match_str, db_ign_is_in_hc, round(ratio, 3)))
    
    potential_typos.sort(key=lambda x: x[3], reverse=True) # Sort by score desc
    return potential_typos


class GuildSyncDoneView(discord.ui.View):
    def __init__(self, original_author_id: int):
        super().__init__(timeout=300.0) # 5 minutes timeout
        self.original_author_id = original_author_id
        self.message: Optional[discord.Message] = None # To store the message this view is attached to

    @discord.ui.button(label="Done ✓", style=discord.ButtonStyle.success, custom_id="guild_sync_done")
    async def done_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_author_id:
            await interaction.response.send_message("❌ You are not the one who initiated this sync.", ephemeral=True)
            return

        button.disabled = True
        button.label = "Report Acknowledged"
        await interaction.response.edit_message(view=self)
        # Optionally, send an ephemeral confirmation
        await interaction.followup.send("Report interaction closed.", ephemeral=True)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                item.label = "Report Timed Out"
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
        self.stop()


async def handle_guild_sync_from_screenshots(
    message: discord.Message,
    valid_image_attachments: List[discord.Attachment]
):
    """Handles the new guild member update mode."""
    guild = message.guild
    user = message.author
    processing_reply_content = f"{user.mention} ⏳ Starting Guild Member Sync Analysis for {len(valid_image_attachments)} image(s)..."
    processing_reply: Optional[discord.Message] = None
    try:
        processing_reply = await message.reply(processing_reply_content, allowed_mentions=discord.AllowedMentions(users=[user]))
    except discord.HTTPException as e_initial_reply:
        await log_error(guild, "GuildSync: Failed to send initial processing reply", error=e_initial_reply, message_context=message)
        return

    ai_cog = bot.get_cog('AICog')
    if not ai_cog:
        if processing_reply: await processing_reply.edit(content=f"{user.mention} ❌ Error: AI module is not available for image processing.")
        else: await message.channel.send(f"{user.mention} ❌ Error: AI module is not available for image processing.")
        await log_error(guild, "GuildSync: AICog not found.", message_context=message)
        return

    screenshot_igns_set: Set[str] = set()
    failed_ai_extractions = 0

    # 1. Extract IGNs from screenshots (using existing online player extraction)
    if processing_reply: # Check if processing_reply was successfully created
      await processing_reply.edit(content=f"{user.mention} 🧠 Extracting names from screenshots with AI... (this may take a moment)")
    
    known_igns_list_for_ai = "\n".join(ai_cog.ingame_name_cache_ref) if ai_cog.ingame_name_cache_ref else "No known names provided."
    
    for idx, image_att in enumerate(valid_image_attachments):
        try:
            image_bytes = await image_att.read()
            # Using FLORR_IMAGE_NAME_EXTRACTION (extracts *online* IGNs based on current prompt)
            ai_extracted_text = await ai_cog.get_ai_response_with_image(
                prompt_key="FLORR_IMAGE_NAME_EXTRACTION", 
                image_bytes=image_bytes,
                prompt_kwargs={'known_igns_list_str': known_igns_list_for_ai}
            )
            if ai_extracted_text and ai_extracted_text.strip().upper() != "NO_NAMES_FOUND":
                extracted_this_image = {name.strip() for name in ai_extracted_text.split('\n') if name.strip()}
                screenshot_igns_set.update(extracted_this_image)
            elif not ai_extracted_text: # AI returned None or empty string
                failed_ai_extractions +=1
                await log_info(guild, f"GuildSync: AI returned no text for image {image_att.filename}.")
            # If "NO_NAMES_FOUND", it's not an error, just no names.
        except Exception as e_img_proc:
            failed_ai_extractions +=1
            await log_error(guild, f"GuildSync: Error processing image {image_att.filename}", error=e_img_proc, message_context=message)
    
    if failed_ai_extractions == len(valid_image_attachments) and not screenshot_igns_set:
        if processing_reply: await processing_reply.edit(content=f"{user.mention} ❌ AI failed to extract names from all images, or no names were found. Cannot proceed with sync.")
        return
    if not screenshot_igns_set:
        if processing_reply: await processing_reply.edit(content=f"{user.mention} ℹ️ AI did not identify any known player names from the screenshots. Sync aborted.")
        return
    
    if processing_reply: # Check if processing_reply exists before editing
        await processing_reply.edit(content=f"{user.mention} 📊 Comparing {len(screenshot_igns_set)} unique names from screenshots with the database...")

    # 2. Fetch all current HC members from DB
    db_hc_igns_list = await fetch_all_db_hc_members_for_sync(guild)
    db_hc_igns_set = set(db_hc_igns_list) # For efficient lookup

    # 3. Perform Comparisons
    in_screenshot_not_active_in_db: List[str] = []
    for s_ign in screenshot_igns_set:
        s_ign_lower = s_ign.lower()
        is_active_in_db_set = any(db_s_ign.lower() == s_ign_lower for db_s_ign in db_hc_igns_set)
        if not is_active_in_db_set:
            member_db_status_resp = await run_supabase_sync(
                lambda: supabase.table("hc_members")
                               .select("is_in_hc")
                               .ilike("ingame_name", s_ign) 
                               .maybe_single()
                               .execute()
            )
            if member_db_status_resp and hasattr(member_db_status_resp, 'data') and member_db_status_resp.data:
                if member_db_status_resp.data.get("is_in_hc") is False:
                    in_screenshot_not_active_in_db.append(f"{s_ign} (DB: Not in HC)")
                elif member_db_status_resp.data.get("is_in_hc") is True:
                     await log_info(guild, f"GuildSync Discrepancy: {s_ign} found in DB with is_in_hc=TRUE but wasn't in initial active fetch. Possible data sync issue or case mismatch not caught by `any()`.")
                # else: is_in_hc is null, treat as not in DB for this check
            else: 
                in_screenshot_not_active_in_db.append(f"{s_ign} (Not in DB at all)")

    in_db_active_not_in_screenshot = list(db_hc_igns_set - {ign.lower() for ign in screenshot_igns_set})
    # Refine in_db_active_not_in_screenshot to use original casing from db_hc_igns_list
    temp_in_db_active_not_in_screenshot_lower = {ign.lower() for ign in in_db_active_not_in_screenshot}
    in_db_active_not_in_screenshot = [ign for ign in db_hc_igns_list if ign.lower() in temp_in_db_active_not_in_screenshot_lower]


    potential_typos = find_potential_ign_typos(screenshot_igns_set, db_hc_igns_set)

    # 4. Format Report
    report_embed = discord.Embed(
        title=f"Guild Member Sync Analysis Report ({user.display_name})",
        description=f"Analyzed {len(valid_image_attachments)} images. Found {len(screenshot_igns_set)} unique player names in screenshots (AI-identified as 'online'). Compared with {len(db_hc_igns_set)} active HC members in database.",
        color=NERDY_YELLOW
    )
    report_embed.timestamp = discord.utils.utcnow()

    if in_screenshot_not_active_in_db:
        field_value = "\n".join([f"- `{discord.utils.escape_markdown(ign)}`" for ign in sorted(in_screenshot_not_active_in_db)])
        if len(field_value) > 1020: field_value = field_value[:1017] + "..."
        report_embed.add_field(name=f"⚠️ In Screenshots, Not Active in DB ({len(in_screenshot_not_active_in_db)})", value=field_value or "None", inline=False)

    if in_db_active_not_in_screenshot:
        field_value = "\n".join([f"- `{discord.utils.escape_markdown(ign)}`" for ign in sorted(in_db_active_not_in_screenshot)])
        if len(field_value) > 1020: field_value = field_value[:1017] + "..."
        report_embed.add_field(name=f"❓ In DB (Active), Not in Screenshots ({len(in_db_active_not_in_screenshot)})", value=field_value or "None", inline=False)

    if potential_typos:
        typo_lines = [f"- SS: `{discord.utils.escape_markdown(s_ign)}` vs DB: `{discord.utils.escape_markdown(d_ign)}` (Score: {score*100:.1f}%)" for s_ign, d_ign, score in potential_typos]
        field_value = "\n".join(typo_lines)
        if len(field_value) > 1020: field_value = field_value[:1017] + "..."
        report_embed.add_field(name=f"🤔 Potential Typos/Capitalization ({len(potential_typos)})", value=field_value or "None", inline=False)

    if not in_screenshot_not_active_in_db and not in_db_active_not_in_screenshot and not potential_typos:
        report_embed.add_field(name="✅ All Clear!", value="No major discrepancies found based on this analysis.", inline=False)

    report_embed.set_footer(text="This report is based on names AI identified as 'online' in screenshots vs. DB's 'is_in_hc=true' list.")

    # 5. Send Report
    sync_view = GuildSyncDoneView(user.id)
    final_report_message_content = f"{user.mention} Guild Sync Analysis Complete:"
    if processing_reply:
        final_message = await processing_reply.edit(content=final_report_message_content, embed=report_embed, view=sync_view)
    else: 
        final_message = await message.channel.send(content=final_report_message_content, embed=report_embed, view=sync_view)
    
    sync_view.message = final_message # Link message to view for timeout handling

    await log_info(guild, f"GuildSync report generated for {user.name}. SS IGNs: {len(screenshot_igns_set)}, DB HC IGNs: {len(db_hc_igns_set)}. Inconsistencies: Screenshot/NotDB: {len(in_screenshot_not_active_in_db)}, DB/NotSS: {len(in_db_active_not_in_screenshot)}, Typos: {len(potential_typos)}")

async def get_user_super_attempt_stats(guild: Optional[discord.Guild], ign: str) -> Dict[str, Any]:
    """
    Fetches various super attempt statistics for a given IGN.
    Returns a dict with keys: 
        'total_attempts', 'total_petals_lost', 
        'favorite_petal_name', 'favorite_petal_attempts',
        'top_petals' (list of dicts: {'petal_name', 'attempts', 'total_petals_lost_for_petal'}),
        'average_petals_lost_per_attempt'.
    Returns empty/default values if no data or error.
    """
    if not supabase or not ign:
        return {
            'total_attempts': 0, 'total_petals_lost': 0.0,
            'favorite_petal_name': "N/A", 'favorite_petal_attempts': 0,
            'top_petals': [], 'average_petals_lost_per_attempt': 0.0
        }

    stats_result = {
        'total_attempts': 0, 'total_petals_lost': 0.0,
        'favorite_petal_name': "N/A", 'favorite_petal_attempts': 0,
        'top_petals': [], 'average_petals_lost_per_attempt': 0.0
    }

    try:
        # 1. Get all attempts for the user
        all_attempts_resp = await run_supabase_sync(
            lambda: supabase.table("super_attempts")
                           .select("chosen_petal_name, petals_lost")
                           .eq("ingame_name", ign)
                           .execute()
        )

        if not (all_attempts_resp and hasattr(all_attempts_resp, 'data') and all_attempts_resp.data):
            return stats_result # No attempts found

        all_attempts_data = all_attempts_resp.data
        stats_result['total_attempts'] = len(all_attempts_data)
        
        current_total_petals_lost = 0.0
        for attempt in all_attempts_data:
            # Ensure petals_lost is treated as float
            try:
                current_total_petals_lost += float(attempt.get("petals_lost", 0.0))
            except (ValueError, TypeError):
                pass # Ignore if not a valid number, or log if strictness needed
        stats_result['total_petals_lost'] = current_total_petals_lost


        if stats_result['total_attempts'] > 0:
            stats_result['average_petals_lost_per_attempt'] = round(stats_result['total_petals_lost'] / stats_result['total_attempts'], 2)
        
        # 2. Calculate favorite and top petals (excluding "Unknown Ultra Petal" for favorite/top display)
        petal_counts: Dict[str, Dict[str, Any]] = {} # petal_name -> {'attempts': int, 'total_petals_lost': float}
        
        for attempt in all_attempts_data:
            # Ensure petal_name is always a string, defaulting to "Unknown Ultra Petal" if None or missing
            petal_name_raw = attempt.get("chosen_petal_name")
            petal_name = petal_name_raw if petal_name_raw is not None else "Unknown Ultra Petal"
            
            petals_lost_in_attempt = 0.0
            try:
                petals_lost_in_attempt = float(attempt.get("petals_lost", 0.0))
            except (ValueError, TypeError):
                pass

            if petal_name not in petal_counts:
                petal_counts[petal_name] = {'attempts': 0, 'total_petals_lost': 0.0}
            petal_counts[petal_name]['attempts'] += 1
            petal_counts[petal_name]['total_petals_lost'] += petals_lost_in_attempt

        # Filter out "Unknown Ultra Petal" for favorite and top display lists
        displayable_petals = {
            name: data for name, data in petal_counts.items()
            if name and name.lower() != "unknown ultra petal" # MODIFIED: Add check for name being non-None
        }

        if displayable_petals:
            # Sort by attempts (desc), then by name (asc) for tie-breaking
            sorted_petals = sorted(
                displayable_petals.items(),
                key=lambda item: (-item[1]['attempts'], item[0]) 
            )
            
            stats_result['favorite_petal_name'] = _get_display_friendly_petal_name(sorted_petals[0][0])
            stats_result['favorite_petal_attempts'] = sorted_petals[0][1]['attempts']
            
            stats_result['top_petals'] = [
                {
                    'petal_name': _get_display_friendly_petal_name(name), 
                    'attempts': data['attempts'],
                    'total_petals_lost_for_petal': data['total_petals_lost']
                }
                for name, data in sorted_petals[:3] # Get top 3
            ]
            
    except Exception as e:
        if guild:
            await log_error(guild, f"Error fetching super attempt stats for {ign}", error=e)
        else:
            print(f"Error fetching super attempt stats for {ign} (no guild context): {e}")
        # Return default/empty stats on error
        return {
            'total_attempts': 0, 'total_petals_lost': 0.0,
            'favorite_petal_name': "N/A", 'favorite_petal_attempts': 0,
            'top_petals': [], 'average_petals_lost_per_attempt': 0.0
        }
            
    return stats_result

async def get_super_attempt_log_entries(
    guild: Optional[discord.Guild], 
    ign: str, 
    page: int, # 0-indexed
    per_page: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fetches paginated super attempt log entries for an IGN.
    Returns a list of log entries and the total count of all entries for that IGN.
    Each entry: {'id', 'attempt_date', 'chosen_petal_name', 'petals_lost'}
    """
    if not supabase or not ign:
        return [], 0

    offset = page * per_page
    log_entries: List[Dict[str, Any]] = []
    total_count = 0

    try:
        # First, get the total count of attempts for this IGN
        count_resp = await run_supabase_sync(
            lambda: supabase.table("super_attempts")
                           .select("id", count='exact')
                           .eq("ingame_name", ign)
                           .execute()
        )
        if count_resp and hasattr(count_resp, 'count') and count_resp.count is not None:
            total_count = count_resp.count
        
        if total_count == 0:
            return [], 0

        # Then, fetch the paginated entries
        # Order by recorded_at DESC (most recent first) for display, then by attempt_date if needed.
        # For simplicity, let's order by recorded_at DESC then id DESC to ensure stable pagination.
        data_resp = await run_supabase_sync(
            lambda: supabase.table("super_attempts")
                           .select("id, attempt_date, chosen_petal_name, petals_lost")
                           .eq("ingame_name", ign)
                           .order("recorded_at", desc=True) # Most recent logs first
                           .order("id", desc=True) # Secondary sort for stability
                           .range(offset, offset + per_page - 1)
                           .execute()
        )

        if data_resp and hasattr(data_resp, 'data') and data_resp.data:
            for entry_data in data_resp.data:
                # Parse date string to date object
                attempt_date_obj = None
                if entry_data.get('attempt_date'):
                    try:
                        attempt_date_obj = datetime.datetime.strptime(entry_data['attempt_date'], '%Y-%m-%d').date()
                    except ValueError:
                        pass # Keep as None if parsing fails
                
                log_entries.append({
                    'id': entry_data.get('id'),
                    'attempt_date': attempt_date_obj,
                    'chosen_petal_name': entry_data.get('chosen_petal_name', "Unknown"),
                    'petals_lost': float(entry_data.get('petals_lost', 0.0)) # Ensure float
                })
        
    except Exception as e:
        if guild:
            await log_error(guild, f"Error fetching super attempt log for {ign}, page {page}", error=e)
        else:
            print(f"Error fetching super attempt log for {ign}, page {page} (no guild context): {e}")
        return [], 0 # Return empty on error, total_count might be 0 or stale

    return log_entries, total_count

async def add_unknown_super_attempts(
    guild: discord.Guild, 
    ign: str, 
    num_attempts_to_add: int, 
    author_discord_id: int
) -> Tuple[bool, str]:
    """Adds N 'Unknown Ultra Petal' attempts with 2.5 petals lost each."""
    if not supabase or not ign or num_attempts_to_add <= 0:
        return False, "Invalid parameters for adding unknown attempts."

    today_date_iso = datetime.datetime.now(pytz.utc).date().isoformat()
    default_petal_name = "Unknown Ultra Petal"
    default_petals_lost = 2.5

    records_to_insert = []
    for _ in range(num_attempts_to_add):
        records_to_insert.append({
            "ingame_name": ign,
            "discord_user_id": str(author_discord_id),
            "attempt_date": today_date_iso,
            "petals_lost": default_petals_lost,
            "chosen_petal_name": default_petal_name,
            "message_id": None, # No original message for these
            "channel_id": None
        })
    
    try:
        insert_resp = await run_supabase_sync(
            lambda: supabase.table("super_attempts").insert(records_to_insert).execute()
        )
        if insert_resp.data and len(insert_resp.data) == num_attempts_to_add:
            return True, f"Successfully added {num_attempts_to_add} unknown super attempt(s)."
        else:
            # Partial success or failure to get response data
            failed_count = num_attempts_to_add - (len(insert_resp.data) if insert_resp.data else 0)
            return False, f"Added {len(insert_resp.data) if insert_resp.data else 0}/{num_attempts_to_add} attempt(s). Some may have failed."
    except Exception as e:
        await log_error(guild, f"Error adding {num_attempts_to_add} unknown attempts for {ign}", error=e)
        return False, "Database error while adding unknown attempts."

async def remove_super_attempt_by_id(guild: discord.Guild, attempt_db_id: int) -> Tuple[bool, str]:
    """Removes a super attempt log entry by its database ID."""
    if not supabase or not attempt_db_id:
        return False, "Invalid parameters for removing attempt."
    try:
        delete_resp = await run_supabase_sync(
            lambda: supabase.table("super_attempts").delete().eq("id", attempt_db_id).execute()
        )
        if delete_resp.data and len(delete_resp.data) > 0:
            return True, f"Successfully removed super attempt log (ID: {attempt_db_id})."
        else:
            return False, f"Could not find super attempt log (ID: {attempt_db_id}) to remove, or it was already gone."
    except Exception as e:
        await log_error(guild, f"Error removing super attempt log ID {attempt_db_id}", error=e)
        return False, "Database error while removing super attempt log."

class AddUnknownAttemptsModal(discord.ui.Modal, title="Add Unknown Super Attempts"):
    num_attempts_input = discord.ui.TextInput(
        label="Number of unknown attempts to add (1-100)",
        placeholder="e.g., 5",
        min_length=1,
        max_length=3, # Allows up to 999, but we'll cap at 100
        style=discord.TextStyle.short,
        required=True
    )

    def __init__(self, view_ref: 'ProfilePagesView'): # Forward reference
        super().__init__(timeout=120.0)
        self.view_ref = view_ref

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            num_to_add = int(self.num_attempts_input.value)
            if not (1 <= num_to_add <= 100): # Sensible limit
                await interaction.followup.send("❌ Please enter a number between 1 and 100.", ephemeral=True)
                return
        except ValueError:
            await interaction.followup.send("❌ Invalid number entered.", ephemeral=True)
            return

        if not self.view_ref.hc_profile_data or not self.view_ref.hc_profile_data.get("ingame_name"):
            await interaction.followup.send("❌ Cannot add attempts: IGN not found for this profile.", ephemeral=True)
            return
        
        ign = self.view_ref.hc_profile_data.get("ingame_name")
        author_id = int(self.view_ref.target_user_display_data.get("_discord_id_for_sa_management")) # Relies on this being set

        success, msg = await add_unknown_super_attempts(interaction.guild, ign, num_to_add, author_id)
        
        feedback_color = discord.Color.green() if success else discord.Color.orange()
        feedback_embed = discord.Embed(title="Add Unknown Attempts Result", description=msg, color=feedback_color)
        await interaction.followup.send(embed=feedback_embed, ephemeral=True)

        if success:
            # Refresh the log page if currently on it
            if self.view_ref.current_page_mode == ProfilePagesView.SUPER_ATTEMPT_LOG_PAGE:
                # Refetch current page data for the log
                await self.view_ref._fetch_s_attempt_log_page_data(self.view_ref.s_attempt_log_current_page) 
            # Also, refetch overall stats as they have changed
            await self.view_ref._fetch_super_attempt_stats_data()
            # Trigger a view update (this should handle being on stats or log page)
            await self.view_ref._update_message(interaction) # Use the modal's interaction for the update context

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await log_error(interaction.guild, "Error in AddUnknownAttemptsModal", error=error, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred with the modal.", ephemeral=True)


class RemoveAttemptModal(discord.ui.Modal, title="Remove Super Attempt Log Entry"):
    entry_number_input = discord.ui.TextInput(
        label="Number of the log entry on THIS PAGE to remove",
        placeholder="e.g., 3 (for the 3rd item listed on the current page)",
        min_length=1,
        max_length=2,
        style=discord.TextStyle.short,
        required=True
    )

    def __init__(self, view_ref: 'ProfilePagesView'):
        super().__init__(timeout=120.0)
        self.view_ref = view_ref

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            entry_num_on_page = int(self.entry_number_input.value)
            # Validate against number of entries on current page (1-indexed for user)
            if not (1 <= entry_num_on_page <= len(self.view_ref.current_s_attempt_log_entries)):
                await interaction.followup.send(
                    f"❌ Invalid entry number. Please enter a number between 1 and {len(self.view_ref.current_s_attempt_log_entries)} "
                    f"for the current page.", 
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.followup.send("❌ Invalid number entered.", ephemeral=True)
            return

        # Get the DB ID of the selected entry
        # current_s_attempt_log_entries is 0-indexed internally
        entry_to_remove_data = self.view_ref.current_s_attempt_log_entries[entry_num_on_page - 1]
        attempt_db_id_to_remove = entry_to_remove_data.get('id')

        if not attempt_db_id_to_remove:
            await interaction.followup.send("❌ Error: Could not find database ID for the selected entry.", ephemeral=True)
            return

        success, msg = await remove_super_attempt_by_id(interaction.guild, attempt_db_id_to_remove)
        
        feedback_color = discord.Color.green() if success else discord.Color.orange()
        feedback_embed = discord.Embed(title="Remove Attempt Result", description=msg, color=feedback_color)
        await interaction.followup.send(embed=feedback_embed, ephemeral=True)

        if success:
            # Refresh the log page
            await self.view_ref._fetch_s_attempt_log_page_data(self.view_ref.s_attempt_log_current_page)
            # Also, refetch overall stats
            await self.view_ref._fetch_super_attempt_stats_data()
            # Trigger a view update
            await self.view_ref._update_message(interaction)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await log_error(interaction.guild, "Error in RemoveAttemptModal", error=error, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred with the modal.", ephemeral=True)

async def get_all_time_super_attempt_count(guild: Optional[discord.Guild], author_ign: str) -> int:
    """Fetches the total number of super attempts logged for a given IGN."""
    if not supabase or not author_ign:
        return 0
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("super_attempts")
                           .select("id", count='exact')
                           .eq("ingame_name", author_ign) # Match the IGN
                           # No date filter, so it counts all-time
                           .execute()
        )
        return resp.count if resp and hasattr(resp, 'count') and resp.count is not None else 0
    except Exception as e:
        if guild:
            await log_error(guild, f"Error fetching all-time super attempt count for {author_ign}", error=e)
        else:
            print(f"Error fetching all-time super attempt count for {author_ign} (no guild context): {e}")
        return 0

async def update_custom_nickname_on_attempt(
    guild: discord.Guild,
    user: discord.Member,
    author_ign: str, # IGN of the user
    all_time_attempt_count: Optional[int] = None # Can be pre-fetched
):
    """
    Updates a user's nickname if they have bot management enabled.
    Uses custom template if provided, otherwise a default HC format.
    Uses the provided all_time_attempt_count or fetches it if None.
    """
    if not supabase or not guild or not user or not author_ign: # Added author_ign check
        return

    try:
        settings_resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("manage_nickname_by_bot, custom_nickname_template, is_in_hc") # Fetch is_in_hc
                           .eq("discord_id", str(user.id))
                           .eq("ingame_name", author_ign) # Ensure we're updating for the correct IGN if user has multiple (though not typical)
                           .maybe_single()
                           .execute()
        )

        if not (settings_resp and hasattr(settings_resp, 'data') and settings_resp.data):
            return

        settings = settings_resp.data
        manage_by_bot = settings.get("manage_nickname_by_bot", False)
        is_in_hc = settings.get("is_in_hc", False) # Check if user is actually in HC
        custom_template = settings.get("custom_nickname_template")

        if not manage_by_bot:
            # If management is off, but they are IN HC, we might want to revert their nick to just IGN
            # This ensures if they turn management off, the SATT part is removed.
            if is_in_hc and user.nick != author_ign:
                 # Check bot permissions before trying to revert
                bot_member = guild.me
                if bot_member.top_role > user.top_role and bot_member.guild_permissions.manage_nicknames:
                    try:
                        await user.edit(nick=author_ign[:32], reason="Nickname management disabled, reverting to IGN")
                        await log_info(guild, f"Reverted nickname for {user.mention} to '{author_ign[:32]}' as management was disabled.")
                    except Exception as e_revert:
                        await log_error(guild, f"Error reverting nickname for {user.mention} after disabling management", error=e_revert)
            return # Nickname management not enabled by user choice

        # Fetch all-time attempt count if not provided
        if all_time_attempt_count is None:
            current_all_time_count = await get_all_time_super_attempt_count(guild, author_ign)
        else:
            current_all_time_count = all_time_attempt_count
            
        new_nickname_unprocessed: str
        if custom_template: # User has a specific template
            new_nickname_unprocessed = custom_template.replace("{satt}", str(current_all_time_count))
        elif is_in_hc: # User is in HC, management is ON, but NO custom template -> Apply default HC format
            if current_all_time_count > 0:
                new_nickname_unprocessed = f"{author_ign} ({current_all_time_count} satt)"
            else:
                new_nickname_unprocessed = author_ign # Just IGN if 0 SATT
        else: # Not in HC, but management somehow ON without template (should be rare) -> Just IGN
            new_nickname_unprocessed = author_ign

        new_nickname = new_nickname_unprocessed[:32]
        
        if user.nick == new_nickname:
            return

        bot_member = guild.me
        if bot_member.top_role <= user.top_role:
            await log_info(guild, f"Nickname update skipped for {user.mention}: Bot hierarchy too low.")
            return
        if not bot_member.guild_permissions.manage_nicknames:
            await log_info(guild, f"Nickname update skipped for {user.mention}: Bot lacks Manage Nicknames permission.")
            return

        await user.edit(nick=new_nickname, reason=f"Automatic nickname update (S.Attempts: {current_all_time_count})")
        log_reason_nick_type = "custom template" if custom_template else ("default HC format" if is_in_hc else "IGN default")
        await log_info(guild, f"Updated nickname for {user.mention} to '{new_nickname}' ({log_reason_nick_type}).")

    except Exception as e:
        await log_error(guild, f"Error updating nickname for {user.mention}", error=e)

class SuperAttemptButton(discord.ui.Button):
    """Base class for super attempt related buttons for easier type hinting."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class ChosenPetalButton(SuperAttemptButton):
    def __init__(self, chosen_petal_data: Dict[str, Any], petals_lost: int, original_user_message: discord.Message, author_ign: str, attempt_date_obj: datetime.date, row: int):
        self.chosen_petal_data = chosen_petal_data # {'original_full_name': str, 'display_friendly_name': str}
        self.petals_lost = petals_lost
        self.original_user_message = original_user_message
        self.author_ign = author_ign
        self.attempt_date_obj = attempt_date_obj
        
        # Truncate label if too long
        label = chosen_petal_data['display_friendly_name']
        if len(label) > 78: # Max 80, leave room for "✔ "
            label = label[:77] + "…"

        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=f"sa_choice_{original_user_message.id}_{chosen_petal_data['original_full_name'][:30]}", row=row)

    async def callback(self, interaction: discord.Interaction):
        if not self.view or interaction.user.id != self.view.target_user_id:
            await interaction.response.send_message("You cannot interact with this.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await self.view.handle_disambiguation_choice(interaction, self)

class CancelButton(SuperAttemptButton):
    def __init__(self, row: int, original_user_message_id: int):
        super().__init__(label="Cancel", style=discord.ButtonStyle.secondary, custom_id=f"sa_cancel_{original_user_message_id}", row=row)

    async def callback(self, interaction: discord.Interaction):
        if not self.view or interaction.user.id != self.view.target_user_id:
            await interaction.response.send_message("You cannot interact with this.", ephemeral=True)
            return
        await interaction.response.defer()
        await self.view.handle_cancel(interaction)

class UndoSuperAttemptButton(SuperAttemptButton):
    def __init__(self, attempt_db_id: int, original_user_message: discord.Message, row: int):
        self.attempt_db_id = attempt_db_id
        self.original_user_message = original_user_message
        super().__init__(label="Undo Log", emoji="↩️", style=discord.ButtonStyle.danger, custom_id=f"sa_undo_{attempt_db_id}", row=row)

    async def callback(self, interaction: discord.Interaction):
        if not self.view or interaction.user.id != self.view.target_user_id:
            await interaction.response.send_message("You cannot interact with this.", ephemeral=True)
            return
        
        await interaction.response.defer()
        # The view (SuperAttemptConfirmView) will handle the undo logic
        if isinstance(self.view, SuperAttemptConfirmView):
            await self.view.handle_undo(interaction, self.attempt_db_id, self.original_user_message)
        else: # Should not happen if correctly instanced
             await interaction.followup.send("Error: Undo context is incorrect.", ephemeral=True)


class SuperAttemptDisambiguationView(discord.ui.View):
    def __init__(self, target_user_id: int, candidate_petals: List[Dict[str, Any]], 
                 petals_lost: int, original_user_message: discord.Message, 
                 author_ign: str, attempt_date_obj: datetime.date, timeout=120.0):
        super().__init__(timeout=timeout)
        self.target_user_id = target_user_id
        self.candidate_petals = candidate_petals
        self.petals_lost = petals_lost
        self.original_user_message = original_user_message
        self.author_ign = author_ign
        self.attempt_date_obj = attempt_date_obj
        self.message: Optional[discord.Message] = None 

        current_row = 0
        for i, petal_data in enumerate(candidate_petals):
            if i > 0 and i % 4 == 0: 
                current_row +=1
            if current_row >= 4 :
                print(f"SuperAttemptDisambiguationView: Too many candidates ({len(candidate_petals)}), only showing first few.")
                break 
            self.add_item(ChosenPetalButton(petal_data, petals_lost, original_user_message, author_ign, attempt_date_obj, row=current_row))
        
        if len(self.children) > 0 : 
            last_button_row = self.children[-1].row if self.children[-1].row is not None else 0
            cancel_row = last_button_row + 1 if len(self.children) % 4 == 0 and current_row < 4 else current_row
            if cancel_row >= 5 : cancel_row = 4 
        else: 
            cancel_row = 0

        self.add_item(CancelButton(row=cancel_row, original_user_message_id=original_user_message.id))

    async def handle_disambiguation_choice(self, interaction: discord.Interaction, button: ChosenPetalButton):
        # // --- UNCHANGED SECTION (handle_disambiguation_choice) --- //
        guild = interaction.guild
        if not guild: 
            await interaction.followup.send("Error: Guild context lost.", ephemeral=True)
            return
            
        try:
            insert_resp = await run_supabase_sync(
                lambda: supabase.table("super_attempts").insert({
                    "ingame_name": self.author_ign,
                    "discord_user_id": str(self.target_user_id),
                    "attempt_date": self.attempt_date_obj.isoformat(),
                    "petals_lost": self.petals_lost,
                    "message_id": str(self.original_user_message.id),
                    "channel_id": str(self.original_user_message.channel.id),
                    "chosen_petal_name": button.chosen_petal_data['original_full_name'] 
                }).execute()
            )
            
            new_attempt_db_id = None
            if insert_resp.data and len(insert_resp.data) > 0 and 'id' in insert_resp.data[0]:
                new_attempt_db_id = insert_resp.data[0]['id']
            else: 
                fetch_id_resp = await run_supabase_sync(
                    lambda: supabase.table("super_attempts")
                                .select("id")
                                .eq("message_id", str(self.original_user_message.id))
                                .eq("ingame_name", self.author_ign)
                                .eq("chosen_petal_name", button.chosen_petal_data['original_full_name'])
                                .order("recorded_at", desc=True)
                                .limit(1).maybe_single().execute()
                )
                if fetch_id_resp.data: new_attempt_db_id = fetch_id_resp.data['id']

            if not new_attempt_db_id:
                await interaction.followup.send("Error: Could not confirm database ID for the logged attempt. Undo might not work.", ephemeral=True)
                await log_error(guild, f"Super Attempt Disambiguation: Failed to get DB ID after insert for {self.author_ign}, chosen {button.chosen_petal_data['display_friendly_name']}", message_context=self.original_user_message)
                confirm_embed = discord.Embed(
                    description=f"Logged: Lost {self.petals_lost}x {button.chosen_petal_data['display_friendly_name']}.",
                    color=discord.Color.green()
                )
                if self.message: 
                     await self.message.edit(content=f"{interaction.user.mention}", embed=confirm_embed, view=None)
                await _update_reactions(self.original_user_message, "success")
                if isinstance(interaction.user, discord.Member):
                    all_time_count_after_log = await get_all_time_super_attempt_count(guild, self.author_ign)
                    await update_custom_nickname_on_attempt(guild, interaction.user, self.author_ign, all_time_count_after_log)
                return

            all_time_attempts_count = await get_all_time_super_attempt_count(guild, self.author_ign)

            confirm_view_after_choice = SuperAttemptConfirmView(
                target_user_id=self.target_user_id,
                attempt_db_id=new_attempt_db_id,
                petals_lost=self.petals_lost,
                petal_display_name=button.chosen_petal_data['display_friendly_name'],
                author_ign=self.author_ign,
                all_time_attempt_count=all_time_attempts_count, 
                original_user_message=self.original_user_message
            )
            success_embed = confirm_view_after_choice.create_embed()
            if self.message: 
                await self.message.edit(content=f"{interaction.user.mention}", embed=success_embed, view=confirm_view_after_choice)
                confirm_view_after_choice.message = self.message 
            else: 
                await interaction.edit_original_response(content=f"{interaction.user.mention}", embed=success_embed, view=confirm_view_after_choice)

            # DB operation was successful. Now try to send confirmation and update reactions.
            try:
                if self.message: 
                    await self.message.edit(content=f"{interaction.user.mention}", embed=success_embed, view=confirm_view_after_choice)
                    confirm_view_after_choice.message = self.message 
                else: # Should not happen if self.message was set by the calling on_message
                    await interaction.edit_original_response(content=f"{interaction.user.mention}", embed=success_embed, view=confirm_view_after_choice)
                await _update_reactions(self.original_user_message, "success")
            except discord.HTTPException as http_err_reply:
                await log_error(guild, f"Super Attempt (Disambiguation Choice): DB log OK, but Discord API error sending confirm view or success reaction for {self.author_ign}, choice {button.chosen_petal_data['display_friendly_name']}.", error=http_err_reply, message_context=self.original_user_message)
                # Try to add success reaction one last time if the main reply failed
                try: await _update_reactions(self.original_user_message, "success")
                except discord.HTTPException as http_err_reaction_retry:
                    await log_error(guild, f"Super Attempt (Disambiguation Choice): Failed again to add success reaction for {self.author_ign} after confirm view send failed.", error=http_err_reaction_retry, message_context=self.original_user_message)

            await log_info(guild, f"Super attempt (disambiguated choice: {button.chosen_petal_data['display_friendly_name']}) by `{self.author_ign}`: Lost {self.petals_lost}. All-time attempts: {all_time_attempts_count}.")
            
            if isinstance(interaction.user, discord.Member): 
                await update_custom_nickname_on_attempt(guild, interaction.user, self.author_ign, all_time_attempts_count)

        except Exception as e: # This catches errors from the DB logging primarily
            await log_error(guild, f"Error handling disambiguation choice for {self.author_ign}", error=e, message_context=self.original_user_message)
            try: 
                if not interaction.response.is_done():
                    await interaction.response.send_message("An error occurred while processing your choice.", ephemeral=True)
                else:
                    await interaction.followup.send("An error occurred while processing your choice.", ephemeral=True)
            except discord.HTTPException: pass

            if self.message: await self.message.edit(content=f"{interaction.user.mention} An error occurred. Please try again or ask an admin.", embed=None, view=None)
            await _update_reactions(self.original_user_message, "error") # DB error or other critical failure before DB op.
        # // --- END UNCHANGED SECTION (handle_disambiguation_choice) --- //

    async def handle_cancel(self, interaction: discord.Interaction):
        if self.message:
            await self.message.edit(content=f"{interaction.user.mention} Super attempt logging cancelled.", embed=None, view=None)
        await _update_reactions(self.original_user_message, "cancelled")
        self.stop()
        if self.message: 
            await asyncio.sleep(AUTODELETE_DELAY_SECONDS) # Use your global constant here
            try: await self.message.delete()
            except discord.HTTPException: pass # Ignore if already deleted or forbidden

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(content=f"Timed out choosing petal for super attempt. Original message by <@{self.target_user_id}>.", embed=None, view=None)
                await _update_reactions(self.original_user_message, "timeout_or_neutral")
                await asyncio.sleep(AUTODELETE_DELAY_SECONDS) # Use your global constant here
                await self.message.delete() # MODIFIED: Delete the message on timeout
            except discord.HTTPException:
                pass # Message might already be gone or bot lacks permissions
        self.stop()

class SuperAttemptConfirmView(discord.ui.View):
    def __init__(self, target_user_id: int, attempt_db_id: int, petals_lost: int, 
                 petal_display_name: str, author_ign: str, all_time_attempt_count: int, 
                 original_user_message: discord.Message, timeout=180.0): 
        super().__init__(timeout=timeout)
        self.target_user_id = target_user_id
        self.attempt_db_id = attempt_db_id
        self.petals_lost = petals_lost
        self.petal_display_name = petal_display_name
        self.author_ign = author_ign
        self.all_time_attempt_count = all_time_attempt_count 
        self.original_user_message = original_user_message
        self.message: Optional[discord.Message] = None 
        self.is_undone = False

        self.add_item(UndoSuperAttemptButton(attempt_db_id, original_user_message, row=0))

    def create_embed(self) -> discord.Embed:
        # // --- UNCHANGED SECTION (create_embed) --- //
        if self.is_undone:
            return discord.Embed(
                description=f"↩️ Super attempt log for {self.petals_lost}x Ultra {self.petal_display_name} (by {self.author_ign}) has been **undone**.",
                color=discord.Color.orange()
            )
        else:
            return discord.Embed(
                description=(
                    f"Logged! That's super attempt **#{self.all_time_attempt_count}** for you overall, {self.author_ign} "
                    f"(lost {self.petals_lost}x Ultra {self.petal_display_name})."
                ),
                color=discord.Color.green()
            )
        # // --- END UNCHANGED SECTION (create_embed) --- //

    async def handle_undo(self, interaction: discord.Interaction, attempt_db_id_from_button: int, original_user_msg_obj: discord.Message):
        # // --- UNCHANGED SECTION (handle_undo) --- //
        guild = interaction.guild
        if self.is_undone: 
            await interaction.followup.send("This attempt has already been undone.", ephemeral=True)
            return

        if attempt_db_id_from_button != self.attempt_db_id: 
            await interaction.followup.send("Error: Undo ID mismatch.", ephemeral=True)
            return

        try:
            delete_resp = await run_supabase_sync(
                lambda: supabase.table("super_attempts").delete().eq("id", self.attempt_db_id).execute()
            )
            if delete_resp.data: 
                self.is_undone = True
                for item in self.children: 
                    if isinstance(item, discord.ui.Button): item.disabled = True
                
                embed = self.create_embed()
                if self.message: 
                    await self.message.edit(embed=embed, view=self)
                else: 
                    await interaction.edit_original_response(embed=embed, view=self)

                await _update_reactions(original_user_msg_obj, "undone")
                await log_info(guild, f"Super attempt ID {self.attempt_db_id} (Petal: {self.petal_display_name}, User: {self.author_ign}) undone by {interaction.user.name}.")
                if guild and isinstance(interaction.user, discord.Member): 
                    new_all_time_count = await get_all_time_super_attempt_count(guild, self.author_ign)
                    await update_custom_nickname_on_attempt(guild, interaction.user, self.author_ign, new_all_time_count)

            else:
                await interaction.followup.send("Could not find the attempt in the database to undo. It might have already been removed.", ephemeral=True)
                self.is_undone = True 
                for item in self.children:
                    if isinstance(item, discord.ui.Button): item.disabled = True
                if self.message: await self.message.edit(view=self)
                elif interaction.message: await interaction.edit_original_response(view=self)

        except Exception as e:
            await log_error(guild, f"Error undoing super attempt ID {self.attempt_db_id}", error=e, message_context=self.original_user_message)
            await interaction.followup.send("An error occurred while trying to undo the attempt.", ephemeral=True)
            await _update_reactions(original_user_msg_obj, "error") 
        # // --- END UNCHANGED SECTION (handle_undo) --- //

    async def on_timeout(self):
        if self.message:
            try:
                # Disable buttons
                for item in self.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = True
                await self.message.edit(view=self) 
                await _update_reactions(self.original_user_message, "timeout_or_neutral")

                # MODIFIED: Delete the message after a delay
                await asyncio.sleep(AUTODELETE_DELAY_SECONDS) # Use your global constant here
                await self.message.delete()
            except discord.HTTPException:
                pass 
        self.stop()

async def _update_reactions(user_message: discord.Message, state: str):
    """Manages reactions on the user's original super attempt message."""
    if not user_message or not user_message.guild: return # Need guild for bot member

    bot_member = user_message.guild.me
    if not bot_member: return

    try:
        # Clear previous bot reactions first to avoid clutter for states that replace others.
        # For "timeout_or_neutral" when it's a successful log, we want to AVOID clearing ✅.
        
        current_reactions = []
        if bot_member.guild_permissions.read_message_history: # Check if we can see existing reactions
            try:
                # Re-fetch the message to get current reactions to be absolutely sure
                refetched_message = await user_message.channel.fetch_message(user_message.id)
                current_reactions = [str(r.emoji) for r in refetched_message.reactions if r.me]
            except discord.HTTPException: # Message might be gone, or other issues
                pass # Proceed with adding if possible, removal might fail

        # Special handling for timeout of a successfully logged attempt:
        # If state is "timeout_or_neutral" AND "✅" is already present, do nothing.
        if state == "timeout_or_neutral" and "✅" in current_reactions:
            # This means a SuperAttemptConfirmView (which placed ✅) timed out,
            # and it wasn't undone. We want to keep the ✅.
            print(f"Reaction Info: Timeout for successful log (message {user_message.id}), keeping ✅ reaction.")
            return # Explicitly do nothing further with reactions for this case

        # For other states, or if the special timeout case above wasn't met, proceed with normal reaction management.
        common_bot_reactions = ["✅", "❓", "❌", "⌛", "📝", "❔", "⚠️"] # Added new ones
        for r_emoji in common_bot_reactions:
            if r_emoji in current_reactions: # Only try to remove if present
                with contextlib.suppress(discord.HTTPException, discord.Forbidden, discord.NotFound):
                    await user_message.remove_reaction(r_emoji, bot_member)
        
        await asyncio.sleep(0.1) # Brief pause

        if state == "success":
            await user_message.add_reaction("✅")
        elif state == "disambiguation":
            await user_message.add_reaction("❓")
        elif state == "undone":
            await user_message.add_reaction("❌")
        elif state == "cancelled": 
            await user_message.add_reaction("❔") 
        elif state == "error": 
            await user_message.add_reaction("⚠️")
        elif state == "timeout_or_neutral": # Generic timeout or neutral state not covered by specific success case
            # This state is now for when a disambiguation view times out, or confirm view times out *after* being undone.
            # Or if we explicitly want to mark it as "interaction over, but not necessarily error/success/undone".
            # Adding 📝 for a timed-out successful log (if not undone) was removed, handled by the explicit return above.
            # So, if it reaches here for "timeout_or_neutral", it means it wasn't a successful non-undone log.
            # We might clear all reactions, or add a generic "timeout" one if desired.
            # For now, after clearing, let's not add a new one unless a specific state implies it.
            pass # No specific reaction added for this generic timeout state now, relies on prior clear.

    except discord.Forbidden:
        print(f"Reaction Error: Bot lacks 'Add Reactions' or 'Read Message History' permission in {user_message.channel.mention}.")
    except discord.HTTPException as e:
        print(f"Reaction Error: HTTP error managing reactions: {e}")
    except Exception as e:
        print(f"Reaction Error: Unexpected error: {e}")

async def find_ultra_petal_candidates_for_query(petal_query_str: str, guild_for_log: Optional[discord.Guild]) -> List[Dict[str, str]]:
    """
    Finds all "Ultra" petal candidates from the cache that could match a user's query.
    1. Uses fuzzy_match_petal_name to get a primary base name match.
    2. Searches cache for all Ultra petals whose own base name matches this primary base name.

    Returns:
        List of dicts, each: {'original_full_name': "Ultra...", 
                               'display_friendly_name': "Ultra Display Name...",
                               'base_name_for_db': "processed_base_name_of_the_ultra_petal"}
    """
    candidates = []
    if not available_profile_pics_cache:
        if guild_for_log: await log_error(guild_for_log, "find_ultra_petal_candidates: Cache not ready.")
        return candidates

    # Step 1: Get the best fuzzy match for the user's query to determine the target base name.
    # The current fuzzy_match_petal_name is designed to return ONE best base name.
    # If it returns 'ambiguous' at this stage, we might need to handle that differently,
    # but for now, let's assume it gives one primary target.
    primary_match_result = await fuzzy_match_petal_name(petal_query_str)
    
    if primary_match_result.get("status") != "success":
        # print(f"[FIND ULTRA CANDIDATES] Fuzzy match for query '{petal_query_str}' was not 'success': {primary_match_result.get('status')}")
        return candidates # No base name to work with

    target_base_name = primary_match_result.get("base_name_matched") # e.g., "egg", "lotus"
    if not target_base_name:
        # print(f"[FIND ULTRA CANDIDATES] Fuzzy match success, but no 'base_name_matched' for query '{petal_query_str}'.")
        return candidates

    # print(f"[FIND ULTRA CANDIDATES] Target base name from fuzzy match: '{target_base_name}' for query '{petal_query_str}'")

    # Step 2: Iterate through the full cache to find all Ultra petals whose base name matches target_base_name.
    for original_full_name_cache, folder_id, _ in available_profile_pics_cache:
        if folder_id == PETALS_FOLDER_NAME and original_full_name_cache.lower().startswith("ultra "):
            base_name_of_this_ultra = _preprocess_petal_name_for_search(original_full_name_cache)
            if base_name_of_this_ultra == target_base_name:
                display_friendly_version = _get_display_friendly_petal_name(original_full_name_cache)
                candidates.append({
                    'original_full_name': original_full_name_cache,
                    'display_friendly_name': display_friendly_version,
                    'base_name_for_db': base_name_of_this_ultra # Store the consistent base name
                })
    
    # print(f"[FIND ULTRA CANDIDATES] Found {len(candidates)} Ultra candidates for base '{target_base_name}'.")
    return candidates

async def check_ultra_petal_exists(base_petal_name_to_find: str) -> Optional[str]:
    """
    Checks if an 'Ultra' rarity version of a given base petal name exists in the cache.

    Args:
        base_petal_name_to_find: The base name of the petal, e.g., "lotus", "egg".
                                 This should be pre-processed (lowercase, no 'petal' suffix, etc.).

    Returns:
        The original_full_name (e.g., "Ultra Lotus Petal") from the cache if an Ultra version
        of the base_petal_name_to_find is found, otherwise None.
    """
    if not available_profile_pics_cache:
        print("[CHECK ULTRA] Cache not ready for check_ultra_petal_exists.")
        return None

    normalized_base_to_find = base_petal_name_to_find.lower().strip()

    for original_full_name, folder_id, _ in available_profile_pics_cache:
        if folder_id == PETALS_FOLDER_NAME: # Only consider petals
            # Check if this cached item is an Ultra rarity
            if original_full_name.lower().startswith("ultra "):
                # Now, get the base name of this Ultra petal from the cache
                base_name_of_this_cached_ultra = _preprocess_petal_name_for_search(original_full_name)
                # Compare it with the base name we are looking for
                if base_name_of_this_cached_ultra == normalized_base_to_find:
                    print(f"[CHECK ULTRA] Found Ultra for base '{normalized_base_to_find}': '{original_full_name}'")
                    return original_full_name # Return the full name from cache, e.g., "Ultra Lotus Petal"
    
    print(f"[CHECK ULTRA] No Ultra version found in cache for base name: '{normalized_base_to_find}'")
    return None

def _preprocess_petal_name_for_search(name: str) -> str:
    """Lowercase, strip, remove rarity prefix, remove 'petal' suffix."""
    clean_name = name.lower().strip()
    for prefix in RARITY_PREFIXES:
        if clean_name.startswith(prefix + " "):
            clean_name = clean_name[len(prefix) + 1:].strip()
            break
    if clean_name.endswith(" petal"):
        clean_name = clean_name[:-len(" petal")].strip()
    elif clean_name.endswith("petal"):
        clean_name = clean_name[:-len("petal")].strip()
    return clean_name

def _preprocess_query_for_search(query: str) -> str:
    """Lowercase, strip, remove rarity, drop 'u', remove 'petal' suffix, expand abbreviations."""
    processed_query = query.lower().strip()
    for prefix in RARITY_PREFIXES:
        if processed_query.startswith(prefix + " "):
            processed_query = processed_query[len(prefix) + 1:].strip()
            break
    
    if len(processed_query) > 1 and processed_query.startswith('u'):
        if processed_query.startswith('u '):
            processed_query = processed_query[2:].strip()
        elif len(processed_query) > 1:
            processed_query = processed_query[1:].strip()

    if processed_query.endswith(" petal"):
        processed_query = processed_query[:-len(" petal")].strip()
    elif processed_query.endswith("petal"):
        processed_query = processed_query[:-len("petal")].strip()
    
    # Abbreviation expansion (after other cleaning)
    return PETAL_ABBREVIATIONS.get(processed_query, processed_query)

def _get_display_friendly_petal_name(original_name: str) -> str:
    """Remove rarity prefix from original cased name, preserving case of the rest."""
    display_friendly_name = original_name
    for prefix in RARITY_PREFIXES:
        if display_friendly_name.lower().startswith(prefix + " "):
            idx = display_friendly_name.lower().find(prefix + " ")
            if idx == 0:
                display_friendly_name = display_friendly_name[len(prefix) + 1:].strip()
            break
    return display_friendly_name

async def fuzzy_match_petal_name(query_string: str, cutoff: float = 0.6) -> Dict[str, Any]:
    """
    Fuzzy matches a query string against base petal names from the cache.
    Handles preprocessing and abbreviations.

    Returns a dictionary with status and match data.
    'success' status includes:
        'base_name_matched': The common base name found (e.g., 'lotus').
        'display_friendly_name': A display-friendly version (e.g., 'Lotus Petal').
        'original_query', 'processed_query'.
    """
    if not available_profile_pics_cache:
        return {'status': 'cache_not_ready'}

    # Map: base_search_name -> {'display_friendly_name': str, 'count': int}
    # We store the first encountered display_friendly_name for a base_search_name.
    unique_base_petal_data_map: Dict[str, Dict[str, Any]] = {}

    for display_name_orig, folder_id, _ in available_profile_pics_cache:
        if folder_id == PETALS_FOLDER_NAME: # Only consider petals
            # This gets the name like "lotus", "dandelion", "egg"
            base_search_name = _preprocess_petal_name_for_search(display_name_orig)
            if base_search_name:
                if base_search_name not in unique_base_petal_data_map:
                    # This gets the name like "Lotus Petal", "Dandelion", "Egg"
                    display_friendly = _get_display_friendly_petal_name(display_name_orig)
                    unique_base_petal_data_map[base_search_name] = {
                        'display_friendly_name': display_friendly,
                        # 'original_full_name_representative': display_name_orig # We don't need this for this func's output
                    }
    
    if not unique_base_petal_data_map:
        return {'status': 'no_searchable_petals'}

    processed_query_for_match = _preprocess_query_for_search(query_string)

    if not processed_query_for_match:
        return {'status': 'empty_query_after_processing', 'original_query': query_string}

    searchable_base_names_pool = list(unique_base_petal_data_map.keys())
    
    matches_from_difflib = difflib.get_close_matches(
        processed_query_for_match, searchable_base_names_pool, n=3, cutoff=cutoff
    )

    if not matches_from_difflib:
        return {
            'status': 'not_found', 
            'original_query': query_string, 
            'processed_query': processed_query_for_match
        }

    # Score the matches against the *base names*
    scored_matches: List[Dict[str, Any]] = []
    for matched_base_name_str in matches_from_difflib:
        score = difflib.SequenceMatcher(None, processed_query_for_match, matched_base_name_str).ratio()
        base_petal_entry_data = unique_base_petal_data_map.get(matched_base_name_str)
        if base_petal_entry_data:
            scored_matches.append({
                'base_name_matched': matched_base_name_str, # e.g., 'lotus'
                'display_friendly_name': base_petal_entry_data['display_friendly_name'], # e.g., 'Lotus Petal'
                'score': score
            })
    
    if not scored_matches: # Should not happen if matches_from_difflib was populated
         return {
            'status': 'not_found', 
            'original_query': query_string, 
            'processed_query': processed_query_for_match
        }

    scored_matches.sort(key=lambda x: x['score'], reverse=True)
    best_match = scored_matches[0] # This contains 'base_name_matched' and 'display_friendly_name'
    
    # Ambiguity Check (remains similar, but now based on base name matches)
    if len(scored_matches) > 1:
        second_match = scored_matches[1]
        is_ambiguous = (
            best_match['score'] > 0.70 and 
            second_match['score'] > 0.65 and
            (best_match['score'] - second_match['score']) < 0.1 
        )
        if len(processed_query_for_match) <= 3 and best_match['score'] < 0.85 :
            if (best_match['score'] - second_match['score']) < 0.15 and second_match['score'] > 0.60:
                 is_ambiguous = True

        if is_ambiguous:
            ambiguous_display_names_set = set()
            for m in scored_matches[:min(3, len(scored_matches))]:
                if m['score'] > 0.60:
                    ambiguous_display_names_set.add(m['display_friendly_name']) # Show display friendly for ambiguity
            
            unique_ambiguous_options = list(ambiguous_display_names_set)
            if len(unique_ambiguous_options) > 1:
                return {
                    'status': 'ambiguous',
                    'original_query': query_string,
                    'processed_query': processed_query_for_match,
                    'ambiguous_display_names': unique_ambiguous_options 
                }

    return {
        'status': 'success',
        'original_query': query_string,
        'processed_query': processed_query_for_match,
        'base_name_matched': best_match['base_name_matched'],
        'display_friendly_name': best_match['display_friendly_name']
        # Removed 'match_details' as the direct items are now returned
    }

def _generate_activity_week_display(
    relevant_active_dates: Set[datetime.date],
    week_start_calendar_date: datetime.date, 
    num_days_in_row: int, 
    today_date: datetime.date,
    current_month_for_padding_check: Optional[int] = None
) -> Tuple[List[str], List[str], List[str]]:
    """
    Generates lists of raw strings for day names, day numbers, and activity status characters.
    Day names: "Mon", "Tue", etc.
    Day numbers: " 1", "12" (2 chars, right-aligned)
    Status chars: "Y", "X", "o", ".", " " (1 char) - Using your specified chars
    """
    raw_day_names = []
    raw_day_numbers = [] 
    raw_activity_status_chars = []

    day_abbreviations = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    # Using your specified characters
    CHAR_ACTIVE = "Y"
    CHAR_PAST_INACTIVE = "x"
    CHAR_TODAY = "." # Using dot for Today and Future as per your example
    CHAR_FUTURE = "."
    CHAR_PADDING = " " 

    for i in range(num_days_in_row):
        current_date_in_loop = week_start_calendar_date + datetime.timedelta(days=i)
        raw_day_names.append(day_abbreviations[current_date_in_loop.weekday()])

        is_padding_day = current_month_for_padding_check and current_date_in_loop.month != current_month_for_padding_check
        
        if is_padding_day:
            raw_day_numbers.append("  ") 
            raw_activity_status_chars.append(CHAR_PADDING)
        else:
            raw_day_numbers.append(f"{current_date_in_loop.day:>2}") 

            status_char = CHAR_FUTURE # Default for future days
            if current_date_in_loop == today_date:
                status_char = CHAR_TODAY 
            elif current_date_in_loop in relevant_active_dates:
                status_char = CHAR_ACTIVE
            elif current_date_in_loop < today_date: # Past, and not in relevant_active_dates
                status_char = CHAR_PAST_INACTIVE
            
            raw_activity_status_chars.append(status_char)
    
    return raw_day_names, raw_day_numbers, raw_activity_status_chars

def _create_activity_legend_string() -> str:
    # Using your specified characters for the legend
    return "`Y` = Active, `x` = Inactive (Past), `.` = Today/Future/No Data"

def generate_monthly_activity_string_v2(
    all_active_dates_for_target_month: Set[datetime.date], 
    target_month: int, 
    target_year: int,
    today_date_actual: datetime.date
) -> str:
    if not today_date_actual: return "`N/A (Date Error)`"

    try:
        first_day_of_target_month = datetime.date(target_year, target_month, 1)
        if target_month == 12:
            first_day_of_next_month = datetime.date(target_year + 1, 1, 1)
        else:
            first_day_of_next_month = datetime.date(target_year, target_month + 1, 1)
        last_day_of_target_month = first_day_of_next_month - datetime.timedelta(days=1)
    except ValueError:
        return "`N/A (Invalid Month/Year for Calendar)`"

    output_lines = []
    month_year_header = first_day_of_target_month.strftime("%B %Y")
    output_lines.append(month_year_header)
    
    day_names_header_list_raw, _, _ = _generate_activity_week_display(set(), first_day_of_target_month, 7, today_date_actual)
    day_names_line_joined = " ".join(f"{name:<3}" for name in day_names_header_list_raw)
    
    output_lines.append("```") 
    output_lines.append(day_names_line_joined)
    output_lines.append("-" * len(day_names_line_joined))

    calendar_grid_start_date = first_day_of_target_month - datetime.timedelta(days=first_day_of_target_month.weekday())
    current_date_for_grid_row = calendar_grid_start_date
    
    while current_date_for_grid_row <= last_day_of_target_month:
        _, week_day_numbers_raw, week_status_chars_raw = _generate_activity_week_display(
            all_active_dates_for_target_month,
            current_date_for_grid_row, 
            7, 
            today_date_actual,
            target_month 
        )
        
        line_nums_cells = [f"{n_str:^3}" for n_str in week_day_numbers_raw]
        line_nums_joined = " ".join(line_nums_cells)
        output_lines.append(line_nums_joined)

        line_status_cells = [f"{s_char:^3}" for s_char in week_status_chars_raw]
        line_status_joined = " ".join(line_status_cells)
        output_lines.append(line_status_joined)
        
        # Add a blank line after the status characters for visual separation within the month view
        if current_date_for_grid_row + datetime.timedelta(days=6) < last_day_of_target_month : # Avoid extra blank line after last week
             output_lines.append("") # This creates the 1-line gap

        current_date_for_grid_row += datetime.timedelta(days=7)
        
    output_lines.append("```") # End of code block
    
    legend = _create_activity_legend_string()
    output_lines.append(legend) # Add legend after the code block
    
    activity_in_target_month = any(d.month == target_month and d.year == target_year for d in all_active_dates_for_target_month)
    if not activity_in_target_month:
         # This note should appear *before* the legend if possible, or make legend part of footer for embed.
         # For now, adding it before the legend string is appended.
         output_lines.insert(-1, f"\n*No activity logged in {first_day_of_target_month.strftime('%B %Y')}.*")


    return "\n".join(output_lines)

# Replace the ProfilePagesView class with this new version

class ProfileMonthSelect(discord.ui.Select):
    def __init__(self, current_real_year: int, current_real_month: int, 
                 currently_selected_year: int, currently_selected_month: int, # NEW PARAMETERS
                 num_months_to_show: int = 12):
        options = []
        for i in range(num_months_to_show):
            # Generate options based on current_real_year/month to go backwards
            year, month = current_real_year, current_real_month - i 
            while month <= 0:
                month += 12
                year -= 1
            
            month_date_obj = datetime.date(year, month, 1)
            option_label = month_date_obj.strftime("%B %Y")
            option_value = f"{year}-{month:02d}"
            
            # Determine if this option should be the default
            is_default = (year == currently_selected_year and month == currently_selected_month)
            
            options.append(discord.SelectOption(label=option_label, value=option_value, default=is_default))

        super().__init__(
            placeholder="Select Month...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="profile_month_select" 
        )

    async def callback(self, interaction: discord.Interaction):
        # // --- UNCHANGED SECTION (ProfileMonthSelect.callback) --- //
        view: ProfilePagesView = self.view 
        if view:
            await view.handle_month_selection(interaction, self.values[0])
        # // --- END UNCHANGED SECTION (ProfileMonthSelect.callback) --- //


class ProfilePagesView(discord.ui.View):
    MAIN_PAGE = "main"
    MONTHLY_PAGE = "monthly"
    SUPER_ATTEMPT_STATS_PAGE = "sa_stats" # New
    SUPER_ATTEMPT_LOG_PAGE = "sa_log"     # New
    SA_LOG_ENTRIES_PER_PAGE = 10          # New

    def __init__(self, interaction: discord.Interaction,
                 target_user_display_data: Dict[str, Any], # Must contain '_member_object_ref' and '_discord_id_for_sa_management'
                 hc_profile_data: Optional[Dict[str, Any]],
                 activity_summary_data: Optional[Dict[str, Any]],
                 initial_monthly_active_dates: Optional[Set[datetime.date]],
                 super_attempt_stats_data: Optional[Dict[str, Any]], # New
                 today_date_obj: datetime.date,
                 timeout=300.0): # Increased timeout slightly
        super().__init__(timeout=timeout)
        self.original_command_interaction = interaction
        self.target_user_display_data = target_user_display_data
        self.hc_profile_data = hc_profile_data
        self.activity_summary_data = activity_summary_data
        self.super_attempt_stats_data = super_attempt_stats_data # Store pre-fetched stats

        self.profile_target_member: Optional[discord.Member] = None
        if isinstance(target_user_display_data.get('_member_object_ref'), discord.Member):
            self.profile_target_member = target_user_display_data['_member_object_ref']
        
        # State for monthly activity view
        self.current_display_month = today_date_obj.month
        self.current_display_year = today_date_obj.year
        self.monthly_active_dates_for_current_view = initial_monthly_active_dates or set()
        
        self.today_date_obj = today_date_obj
        
        self.current_page_mode = self.MAIN_PAGE
        self.message: Optional[discord.Message] = None

        # Super Attempt Log State
        self.s_attempt_log_current_page = 0
        self.s_attempt_log_total_pages = 0
        self.s_attempt_log_total_entries = 0 # Total entries for THIS user
        self.current_s_attempt_log_entries: List[Dict[str, Any]] = []
        self.is_fetching_sa_log = False # Lock for Satt log fetching

        self._update_ui_elements()

    def _update_ui_elements(self):
        self.clear_items()
        
        # Common: Back to Main Profile (if not on main)
        if self.current_page_mode != self.MAIN_PAGE:
            back_to_main_btn = discord.ui.Button(label="⬅️ Back to Main Profile", style=discord.ButtonStyle.primary, custom_id=f"profile_nav_{self.MAIN_PAGE}", row=0)
            back_to_main_btn.callback = self.navigation_button_callback
            self.add_item(back_to_main_btn)

        if self.current_page_mode == self.MAIN_PAGE:
            if self.hc_profile_data and self.hc_profile_data.get("ingame_name"):
                monthly_btn = discord.ui.Button(label="🗓️ View Monthly Activity", style=discord.ButtonStyle.secondary, custom_id=f"profile_nav_{self.MONTHLY_PAGE}", row=0)
                monthly_btn.callback = self.navigation_button_callback
                self.add_item(monthly_btn)

                s_attempt_btn = discord.ui.Button(label="💥 Super Attempt Details", style=discord.ButtonStyle.secondary, custom_id=f"profile_nav_{self.SUPER_ATTEMPT_STATS_PAGE}", row=0)
                s_attempt_btn.callback = self.navigation_button_callback
                self.add_item(s_attempt_btn)

        elif self.current_page_mode == self.MONTHLY_PAGE:
            # Back to main already added
            self.add_item(ProfileMonthSelect(
                current_real_year=self.today_date_obj.year, 
                current_real_month=self.today_date_obj.month,
                currently_selected_year=self.current_display_year,
                currently_selected_month=self.current_display_month,
                num_months_to_show=12
            ))
        
        elif self.current_page_mode == self.SUPER_ATTEMPT_STATS_PAGE:
            # Back to main already added
            view_log_btn = discord.ui.Button(label="📜 View Full Log", style=discord.ButtonStyle.secondary, custom_id=f"profile_nav_{self.SUPER_ATTEMPT_LOG_PAGE}", row=1)
            view_log_btn.callback = self.navigation_button_callback
            self.add_item(view_log_btn)

        elif self.current_page_mode == self.SUPER_ATTEMPT_LOG_PAGE:
            # Back to main already added (row 0)
            # Back to Satt Stats (row 1, next to log nav)
            back_to_sa_stats_btn = discord.ui.Button(label="📊 Back to Satt Stats", style=discord.ButtonStyle.primary, custom_id=f"profile_nav_{self.SUPER_ATTEMPT_STATS_PAGE}", row=1)
            back_to_sa_stats_btn.callback = self.navigation_button_callback
            self.add_item(back_to_sa_stats_btn)

            # Log Navigation (row 1)
            log_prev_btn = discord.ui.Button(label="⬅️ Prev Log Page", style=discord.ButtonStyle.blurple, custom_id="profile_sa_log_prev", row=1, disabled=(self.s_attempt_log_current_page == 0 or self.is_fetching_sa_log))
            log_prev_btn.callback = self.handle_s_attempt_log_prev
            self.add_item(log_prev_btn)
            
            log_next_btn = discord.ui.Button(label="Next Log Page ➡️", style=discord.ButtonStyle.blurple, custom_id="profile_sa_log_next", row=1, disabled=(self.s_attempt_log_current_page >= self.s_attempt_log_total_pages - 1 or self.is_fetching_sa_log))
            log_next_btn.callback = self.handle_s_attempt_log_next
            self.add_item(log_next_btn)

            # Management Buttons (row 2, if owner)
            profile_owner_discord_id = self.target_user_display_data.get("_discord_id_for_sa_management")
            if profile_owner_discord_id and str(self.original_command_interaction.user.id) == str(profile_owner_discord_id):
                add_sa_btn = discord.ui.Button(label="➕ Add Unknown Attempt(s)", style=discord.ButtonStyle.success, custom_id="profile_sa_add_unknown", row=2)
                add_sa_btn.callback = self.handle_add_s_attempt
                self.add_item(add_sa_btn)

                remove_sa_btn = discord.ui.Button(label="➖ Remove Log Entry", style=discord.ButtonStyle.danger, custom_id="profile_sa_remove_entry", row=2, disabled=(not self.current_s_attempt_log_entries or self.is_fetching_sa_log))
                remove_sa_btn.callback = self.handle_remove_s_attempt
                self.add_item(remove_sa_btn)

    def _create_main_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🌟 [HC1] Profile: {discord.utils.escape_markdown(self.target_user_display_data['name'])}",
            color=NERDY_YELLOW
        )
        if self.target_user_display_data['avatar_url']:
            embed.set_thumbnail(url=self.target_user_display_data['avatar_url'])

        ign_display = "`Not Linked / Not Found`"
        hc_status_display = "❔ `Status Unknown (Not in DB)`"
        if self.hc_profile_data:
            ign = self.hc_profile_data.get("ingame_name")
            is_in_hc = self.hc_profile_data.get("is_in_hc")
            ign_display = f"`{discord.utils.escape_markdown(ign)}`" if ign else "`Not Set in DB`"
            if ign is not None: # Check ign exists before status
                if is_in_hc is True: 
                    hc_status_display = "✅ `In Guild (HC1)`"
                elif is_in_hc is False:
                    # Check for EX_MEMBER_ROLE_ID
                    has_ex_role = False
                    if self.profile_target_member and EX_MEMBER_ROLE_ID:
                        if any(role.id == EX_MEMBER_ROLE_ID for role in self.profile_target_member.roles):
                            has_ex_role = True
                    
                    if has_ex_role:
                        hc_status_display = "⏳ `Formerly in Guild (HC1)`"
                    else:
                        hc_status_display = "❌ `Not in Guild (HC1)`" # Generic "not in guild"
                else: # is_in_hc is None or other unexpected value
                    hc_status_display = "❔ `HC Status Unknown (DB)`" 
        
        general_info_value = (
            f"**Discord:** {self.target_user_display_data['mention_or_status']}\n"
            f"**In-Game Name (IGN):** {ign_display}\n"
            f"**[HC1] Guild Status:** {hc_status_display}"
        )
        embed.add_field(name="📋 General", value=general_info_value, inline=False)

        if self.activity_summary_data:
            activity_overview_value = (
                f"**Active Today:** {self.activity_summary_data['active_today_display']}\n"
                f"**Total Days Logged:** `{self.activity_summary_data['total_days_logged']}`\n"
                f"**Last Seen Active:** {self.activity_summary_data['last_seen_display']}"
            )
            embed.add_field(name="📈 Activity Overview", value=activity_overview_value, inline=False)
        elif self.hc_profile_data and self.hc_profile_data.get("ingame_name"):
            embed.add_field(name="📈 Activity Overview", value="`No activity data found.`", inline=False)
        else:
            embed.add_field(name="📈 Activity Overview", value="`Activity data N/A (No IGN Linked).`", inline=False)
        
        # Super Attempt Stats on Main Profile
        if self.super_attempt_stats_data and self.hc_profile_data and self.hc_profile_data.get("ingame_name"):
            sa_stats = self.super_attempt_stats_data
            sa_value = (
                f"**Total Super Attempts:** `{sa_stats.get('total_attempts', 0)}`\n"
                f"**Favorite Petal:** `{sa_stats.get('favorite_petal_name', 'N/A')}` ({sa_stats.get('favorite_petal_attempts', 0)} attempts)"
            )
            embed.add_field(name="💥 Super Attempts Overview", value=sa_value, inline=False)
        elif self.hc_profile_data and self.hc_profile_data.get("ingame_name"):
             embed.add_field(name="💥 Super Attempts Overview", value="`No super attempt data found.`", inline=False)
        else: # No IGN, no Satt stats
            embed.add_field(name="💥 Super Attempts Overview", value="`Super attempt data N/A (No IGN Linked).`", inline=False)

        embed.set_footer(text=f"Profile data generated: {get_formatted_utc_now()} | Use /activatemyself to mark active!")
        return embed

    def _create_monthly_embed(self) -> discord.Embed:
        # // --- UNCHANGED SECTION (ProfilePagesView._create_monthly_embed from previous state) --- //
        ign = self.hc_profile_data.get("ingame_name") if self.hc_profile_data else "N/A"
        embed = discord.Embed(
            title=f"🗓️ Monthly Activity - {discord.utils.escape_markdown(ign)}",
            color=NERDY_YELLOW
        )
            
        monthly_string = generate_monthly_activity_string_v2(
            self.monthly_active_dates_for_current_view,
            self.current_display_month,
            self.current_display_year,
            self.today_date_obj
        )
        embed.description = monthly_string
        display_month_obj = datetime.date(self.current_display_year, self.current_display_month, 1)
        embed.set_footer(text=f"Calendar for {display_month_obj.strftime('%B %Y')}")
        return embed
        # // --- END UNCHANGED SECTION (ProfilePagesView._create_monthly_embed from previous state) --- //

    def _create_super_attempt_stats_embed(self) -> discord.Embed:
        ign = self.hc_profile_data.get("ingame_name") if self.hc_profile_data else "N/A"
        embed = discord.Embed(
            title=f"💥 Super Attempt Statistics - {discord.utils.escape_markdown(ign)}",
            color=NERDY_YELLOW
        )
        if not self.super_attempt_stats_data or self.super_attempt_stats_data.get('total_attempts', 0) == 0:
            embed.description = "No super attempt data recorded for this user."
            return embed

        stats = self.super_attempt_stats_data
        
        top_petals_str_parts = []
        if stats['top_petals']:
            for i, petal_data in enumerate(stats['top_petals']):
                # Optional: include petals lost per attempt for these top 3
                # avg_lost_this_petal = round(petal_data['total_petals_lost_for_petal'] / petal_data['attempts'], 1) if petal_data['attempts'] > 0 else 0
                # top_petals_str_parts.append(f"{i+1}. `{petal_data['petal_name']}`: {petal_data['attempts']} attempts (avg {avg_lost_this_petal} lost)")
                top_petals_str_parts.append(f"{i+1}. `{petal_data['petal_name']}`: {petal_data['attempts']} attempts")
        else:
            top_petals_str_parts.append("`No specific petals recorded (or only 'Unknown').`")

        embed.add_field(name="🏆 Top 3 Attempted petals", value="\n".join(top_petals_str_parts) or "`N/A`", inline=False)
        
        overall_stats_value = (
            f"**Total Super Attempts (All):** `{stats.get('total_attempts', 0)}`\n"
            f"**Total Petals Lost (All):** `{stats.get('total_petals_lost', 0.0):.1f}`\n" # Display with 1 decimal for 2.5
            f"**Average Petals Lost per Attempt:** `{stats.get('average_petals_lost_per_attempt', 0.0):.2f}`"
        )
        embed.add_field(name="📊 Overall", value=overall_stats_value, inline=False)
        embed.set_footer(text=f"Stats as of: {get_formatted_utc_now()}")
        return embed

    def _create_super_attempt_log_embed(self) -> discord.Embed:
        ign = self.hc_profile_data.get("ingame_name") if self.hc_profile_data else "N/A"
        embed = discord.Embed(
            title=f"📜 Super Attempt Log - {discord.utils.escape_markdown(ign)}",
            color=NERDY_YELLOW
        )

        if self.is_fetching_sa_log:
            embed.description = "⏳ Fetching log entries..."
            return embed

        log_lines = []
        
        # Define column widths
        ID_WIDTH = 6
        DATE_WIDTH = 8 # DD/MM/YY
        PETAL_NAME_WIDTH = 22 # Max width for petal name
        LOST_WIDTH = 5 # e.g., "10.0"

        # Header
        header = (
            f"{'ID':<{ID_WIDTH}} | {'Date':<{DATE_WIDTH}} | "
            f"{'Petal Name':<{PETAL_NAME_WIDTH}} | {'Lost':>{LOST_WIDTH}}"
        )
        separator = (
            f"{'-'*ID_WIDTH}-|-{'-'*DATE_WIDTH}-|-"
            f"{'-'*PETAL_NAME_WIDTH}-|-{'-'*LOST_WIDTH}"
        )

        log_lines.append(header)
        log_lines.append(separator)

        if not self.current_s_attempt_log_entries:
            log_lines.append("No super attempt log entries found.")
        else:
            for entry in self.current_s_attempt_log_entries:
                db_id_str = str(entry.get('id', 'N/A'))
                
                date_val = entry.get('attempt_date') # This is a datetime.date object or None
                date_str = format_date_dmy(date_val) if date_val else "N/A"
                # format_date_dmy returns DD/MM/YYYY, we need DD/MM/YY
                if len(date_str) == 10 and date_str != "N/A": # DD/MM/YYYY
                    date_str = date_str[:6] + date_str[8:] # Convert to DD/MM/YY

                petal_original_name = entry.get('chosen_petal_name', "Unknown")
                petal_display_name = _get_display_friendly_petal_name(petal_original_name)
                
                if len(petal_display_name) > PETAL_NAME_WIDTH:
                    petal_display_name = petal_display_name[:PETAL_NAME_WIDTH-3] + "..."
                
                petals_lost_val = entry.get('petals_lost', 0.0)
                try:
                    petals_lost_str = f"{float(petals_lost_val):.1f}"
                except (ValueError, TypeError):
                    petals_lost_str = "N/A"

                log_lines.append(
                    f"{db_id_str:<{ID_WIDTH}} | {date_str:<{DATE_WIDTH}} | "
                    f"{petal_display_name:<{PETAL_NAME_WIDTH}} | {petals_lost_str:>{LOST_WIDTH}}"
                )
        
        embed.description = "```markdown\n" + "\n".join(log_lines) + "\n```"

        footer_text = f"Page {self.s_attempt_log_current_page + 1}/{self.s_attempt_log_total_pages} ({self.s_attempt_log_total_entries} total entries)"
        if self.is_fetching_sa_log: footer_text += " | Fetching..."
        embed.set_footer(text=footer_text)
        return embed

    async def _update_message(self, interaction_to_respond_to: discord.Interaction):
        self._update_ui_elements() 
        embed_to_send: discord.Embed
        if self.current_page_mode == self.MONTHLY_PAGE:
            embed_to_send = self._create_monthly_embed()
        elif self.current_page_mode == self.SUPER_ATTEMPT_STATS_PAGE:
            embed_to_send = self._create_super_attempt_stats_embed()
        elif self.current_page_mode == self.SUPER_ATTEMPT_LOG_PAGE:
            embed_to_send = self._create_super_attempt_log_embed()
        else: 
            embed_to_send = self._create_main_embed()
        
        try:
            # Use edit_original_response if interaction is not done
            if not interaction_to_respond_to.response.is_done():
                 await interaction_to_respond_to.response.edit_message(embed=embed_to_send, view=self)
            elif self.message: # If interaction is done, try to edit the view's message object
                 await self.message.edit(embed=embed_to_send, view=self)
            else: # Fallback if no message object and interaction is done (should be rare)
                 await interaction_to_respond_to.followup.send(embed=embed_to_send, view=self, ephemeral=False) # Send new if all else fails
        except discord.HTTPException as e:
            print(f"Error updating profile page view: {e}")
            guild_for_log = interaction_to_respond_to.guild 
            if bot and hasattr(bot, 'log_error_global'):
                 await bot.log_error_global(guild_for_log, "Failed to update profile page message", error=e)
            elif guild_for_log:
                 await log_error(guild_for_log, "Failed to update profile page message (fallback log)", error=e)
            # No deferral needed here as it's assumed interaction was already responded to or deferred
    
    async def _fetch_super_attempt_stats_data(self):
        """Fetches/Refreshes super_attempt_stats_data for the view."""
        if self.hc_profile_data and self.hc_profile_data.get("ingame_name"):
            ign = self.hc_profile_data.get("ingame_name")
            self.super_attempt_stats_data = await get_user_super_attempt_stats(self.original_command_interaction.guild, ign)
        else:
            self.super_attempt_stats_data = None # Clear if no IGN

    async def _fetch_s_attempt_log_page_data(self, page_num: int):
        """Fetches data for a specific page of the Satt log."""
        if not self.hc_profile_data or not self.hc_profile_data.get("ingame_name"):
            self.current_s_attempt_log_entries = []
            self.s_attempt_log_total_pages = 0
            self.s_attempt_log_total_entries = 0
            return

        ign = self.hc_profile_data.get("ingame_name")
        self.is_fetching_sa_log = True
        # Update UI to show loading state on buttons if needed, then call _update_message
        # For now, the embed itself will show "Fetching..."
        
        entries, total_entries = await get_super_attempt_log_entries(
            self.original_command_interaction.guild, ign, page_num, self.SA_LOG_ENTRIES_PER_PAGE
        )
        self.current_s_attempt_log_entries = entries
        self.s_attempt_log_total_entries = total_entries
        self.s_attempt_log_total_pages = math.ceil(total_entries / self.SA_LOG_ENTRIES_PER_PAGE) if total_entries > 0 else 1
        self.s_attempt_log_current_page = page_num # Ensure current page is set correctly
        self.is_fetching_sa_log = False


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True 

    async def navigation_button_callback(self, interaction: discord.Interaction):
        button_custom_id = interaction.data.get('custom_id')
        if not button_custom_id or not button_custom_id.startswith("profile_nav_"):
            if not interaction.response.is_done(): await interaction.response.defer()
            return

        new_mode = button_custom_id.split("profile_nav_")[1]
        
        valid_modes = [self.MAIN_PAGE, self.MONTHLY_PAGE, self.SUPER_ATTEMPT_STATS_PAGE, self.SUPER_ATTEMPT_LOG_PAGE]
        if new_mode not in valid_modes:
            if not interaction.response.is_done(): await interaction.response.defer()
            return

        if self.current_page_mode == new_mode: 
            if not interaction.response.is_done(): await interaction.response.defer()
            return

        self.current_page_mode = new_mode
        
        # Data fetching logic for new modes
        if new_mode == self.SUPER_ATTEMPT_STATS_PAGE:
            # Stats are usually pre-fetched or fetched on demand once
            if not self.super_attempt_stats_data and self.hc_profile_data and self.hc_profile_data.get("ingame_name"):
                await self._fetch_super_attempt_stats_data()
        elif new_mode == self.SUPER_ATTEMPT_LOG_PAGE:
            await self._fetch_s_attempt_log_page_data(0) # Fetch first page of log
            self.s_attempt_log_current_page = 0 # Reset to first page

        elif new_mode == self.MONTHLY_PAGE and \
           (self.current_display_month != self.today_date_obj.month or self.current_display_year != self.today_date_obj.year):
            if self.hc_profile_data and self.hc_profile_data.get("ingame_name"):
                ign_lower = self.hc_profile_data.get("ingame_name").lower()
                first_day_current_month = self.today_date_obj.replace(day=1)
                if self.today_date_obj.month == 12:
                    first_day_next_month = first_day_current_month.replace(year=self.today_date_obj.year + 1, month=1)
                else:
                    first_day_next_month = first_day_current_month.replace(month=self.today_date_obj.month + 1)
                last_day_current_month = first_day_next_month - datetime.timedelta(days=1)

                self.monthly_active_dates_for_current_view = await fetch_activity_dates_in_range(
                    self.original_command_interaction.guild, ign_lower, 
                    first_day_current_month, last_day_current_month
                )
                self.current_display_month = self.today_date_obj.month
                self.current_display_year = self.today_date_obj.year
            else: self.monthly_active_dates_for_current_view = set()

        await self._update_message(interaction)

    async def handle_month_selection(self, interaction: discord.Interaction, selected_value: str):
        # // --- UNCHANGED SECTION (ProfilePagesView.handle_month_selection from previous state) --- //
        try:
            year_str, month_str = selected_value.split('-')
            selected_year = int(year_str)
            selected_month = int(month_str)
        except ValueError:
            await interaction.response.send_message("Invalid month selection format.", ephemeral=True)
            return
        if not self.hc_profile_data or not self.hc_profile_data.get("ingame_name"):
            await interaction.response.send_message("Cannot fetch monthly data: No In-Game Name linked.", ephemeral=True)
            return
        ign_lower = self.hc_profile_data.get("ingame_name").lower()
        try:
            first_day_selected_month = datetime.date(selected_year, selected_month, 1)
            if selected_month == 12:
                first_day_next_selected_month = datetime.date(selected_year + 1, 1, 1)
            else:
                first_day_next_selected_month = datetime.date(selected_year, selected_month + 1, 1)
            last_day_selected_month = first_day_next_selected_month - datetime.timedelta(days=1)
        except ValueError:
            await interaction.response.send_message("Invalid date for selected month/year.", ephemeral=True)
            return
        self.monthly_active_dates_for_current_view = await fetch_activity_dates_in_range(
            self.original_command_interaction.guild, 
            ign_lower, 
            first_day_selected_month, 
            last_day_selected_month
        )
        self.current_display_month = selected_month
        self.current_display_year = selected_year
        self.current_page_mode = self.MONTHLY_PAGE 
        await self._update_message(interaction)
        # // --- END UNCHANGED SECTION (ProfilePagesView.handle_month_selection from previous state) --- //

    async def handle_s_attempt_log_prev(self, interaction: discord.Interaction):
        if self.s_attempt_log_current_page > 0 and not self.is_fetching_sa_log:
            self.s_attempt_log_current_page -= 1
            await self._fetch_s_attempt_log_page_data(self.s_attempt_log_current_page)
            await self._update_message(interaction)
        elif not interaction.response.is_done(): # Ack if no action
            await interaction.response.defer()


    async def handle_s_attempt_log_next(self, interaction: discord.Interaction):
        if self.s_attempt_log_current_page < self.s_attempt_log_total_pages - 1 and not self.is_fetching_sa_log:
            self.s_attempt_log_current_page += 1
            await self._fetch_s_attempt_log_page_data(self.s_attempt_log_current_page)
            await self._update_message(interaction)
        elif not interaction.response.is_done():
            await interaction.response.defer()
            
    async def handle_add_s_attempt(self, interaction: discord.Interaction):
        modal = AddUnknownAttemptsModal(view_ref=self)
        await interaction.response.send_modal(modal)
        # Refresh logic is handled in modal's on_submit

    async def handle_remove_s_attempt(self, interaction: discord.Interaction):
        modal = RemoveAttemptModal(view_ref=self)
        await interaction.response.send_modal(modal)
        # Refresh logic is handled in modal's on_submit

    async def on_timeout(self):
        # // --- UNCHANGED SECTION (ProfilePagesView.on_timeout from previous state) --- //
        if self.message: 
            try:
                timeout_embed: discord.Embed
                if self.current_page_mode == self.MONTHLY_PAGE: timeout_embed = self._create_monthly_embed()
                elif self.current_page_mode == self.SUPER_ATTEMPT_STATS_PAGE: timeout_embed = self._create_super_attempt_stats_embed()
                elif self.current_page_mode == self.SUPER_ATTEMPT_LOG_PAGE: timeout_embed = self._create_super_attempt_log_embed()
                else: timeout_embed = self._create_main_embed()
                
                if timeout_embed.footer.text:
                    timeout_embed.set_footer(text=f"{timeout_embed.footer.text} (Interaction timed out)")
                else:
                    timeout_embed.set_footer(text="Interaction timed out")

                self.clear_items() 
                await self.message.edit(embed=timeout_embed, view=self) 
            except discord.HTTPException:
                pass 
        self.stop()
        # // --- END UNCHANGED SECTION (ProfilePagesView.on_timeout from previous state) --- //

async def fetch_profile_details_by_ign(guild: Optional[discord.Guild], input_ign: str) -> Optional[Dict[str, Any]]:
    """
    Fetches core profile data for a given In-Game Name from hc_members.
    Performs a case-insensitive search for the IGN.
    Returns a dict {'ingame_name': str (actual case from DB), 
                    'discord_id': str | None, 
                    'is_in_hc': bool, 
                    'discord_name': str | None} 
    or None if not found.
    """
    if not supabase:
        if guild: await log_error(guild, f"Profile: Supabase unavailable fetching data for IGN '{input_ign}'.")
        return None
    try:
        # Perform a case-insensitive query for the ingame_name
        # Note: Supabase ilike is good for patterns. For exact case-insensitive match,
        # you might need to query without ilike and handle case in Python if your DB collation is case-sensitive
        # OR rely on a GIN/GIST index with pg_trgm for faster ilike if this becomes slow.
        # For now, a simple .eq() and then checking a lowercase version (if needed) or direct .ilike()
        # Let's try .ilike() as it's simpler for case-insensitivity directly in query
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("ingame_name, discord_id, is_in_hc, discord_name")
                           .ilike("ingame_name", input_ign) # Case-insensitive match
                           .maybe_single() # Expecting at most one due to unique constraint on ingame_name
                           .execute()
        )
        
        # PostgREST `ilike` with an exact string (no wildcards) effectively becomes a case-insensitive equality check.
        # If multiple results were possible due to no unique constraint, you'd need to loop or pick one.
        # With a unique constraint on ingame_name, ilike should return 0 or 1.

        if resp and hasattr(resp, 'data') and resp.data:
            # Ensure we return the ingame_name exactly as it is in the database for correct casing
            return {
                "ingame_name": resp.data.get("ingame_name"), # Actual case from DB
                "discord_id": str(resp.data.get("discord_id")) if resp.data.get("discord_id") else None,
                "is_in_hc": resp.data.get("is_in_hc"),
                "discord_name": resp.data.get("discord_name")
            }
        return None
    except (ConnectionError, APIError) as e:
        if guild: await log_error(guild, f"Profile: DB error fetching profile data for IGN '{input_ign}'", error=e)
    except Exception as e_gen:
        if guild: await log_error(guild, f"Profile: Unexpected error fetching profile data for IGN '{input_ign}'", error=e_gen)
    return None

async def fetch_hc_member_profile_data(guild: Optional[discord.Guild], discord_id_str: str) -> Optional[Dict[str, Any]]:
    """
    Fetches core profile data (IGN, is_in_hc) for a given Discord ID from hc_members.
    Returns a dict {'ingame_name': str, 'is_in_hc': bool, 'discord_name': str | None} or None if not found.
    """
    if not supabase:
        if guild: await log_error(guild, f"Profile: Supabase unavailable fetching data for user {discord_id_str}.")
        return None
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("ingame_name, is_in_hc, discord_name")
                           .eq("discord_id", discord_id_str)
                           .maybe_single()
                           .execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            return {
                "ingame_name": resp.data.get("ingame_name"),
                "is_in_hc": resp.data.get("is_in_hc"),
                "discord_name": resp.data.get("discord_name") # Store this for users not in guild
            }
        return None
    except (ConnectionError, APIError) as e:
        if guild: await log_error(guild, f"Profile: DB error fetching profile data for user {discord_id_str}", error=e)
    except Exception as e_gen:
        if guild: await log_error(guild, f"Profile: Unexpected error fetching profile data for user {discord_id_str}", error=e_gen)
    return None

async def fetch_activity_dates_in_range(guild: Optional[discord.Guild], ign_lower: str, start_date: datetime.date, end_date: datetime.date) -> Set[datetime.date]:
    """Fetches all distinct activity dates for a given lowercase IGN within a date range."""
    if not supabase or not ign_lower:
        return set()
    active_dates: Set[datetime.date] = set()
    try:
        # Fetch all activity_date entries for the member_identifier within the date range
        query = supabase.table("activity_log").select("activity_date").eq("member_identifier", ign_lower)
        query = query.gte("activity_date", start_date.isoformat())
        query = query.lte("activity_date", end_date.isoformat())
        
        # Potentially many dates, but for 30 days it's fine. Consider pagination for much larger ranges if ever needed.
        resp = await run_supabase_sync(lambda: query.execute())

        if resp and hasattr(resp, 'data') and resp.data:
            for log_entry in resp.data:
                activity_date_str = log_entry.get('activity_date')
                if activity_date_str:
                    try:
                        # Parse YYYY-MM-DD string to date object
                        parsed_date = datetime.datetime.strptime(activity_date_str, '%Y-%m-%d').date()
                        active_dates.add(parsed_date)
                    except ValueError:
                        # Log if parsing fails, but continue
                        if guild: 
                            await log_info(guild, f"Profile: Invalid date format '{activity_date_str}' in activity log for {ign_lower} during range fetch.")
    except (ConnectionError, APIError) as e:
        if guild: 
            await log_error(guild, f"Profile: Error fetching activity dates for {ign_lower}", error=e)
    except Exception as e_gen:
        if guild:
            await log_error(guild, f"Profile: Unexpected error fetching activity dates for {ign_lower}", error=e_gen)
    return active_dates

def generate_weekly_activity_string(active_dates_in_period: Set[datetime.date], today: datetime.date) -> str:
    """Generates an emoji string for the last 7 days of activity."""
    if not active_dates_in_period and not today : return "`N/A`" # Guard against empty input if it happens
    
    days_of_week_initials = ["M", "Tu", "W", "Th", "F", "Sa", "Su"] # Using Tu and Th for clarity
    # Ensure today is a date object
    if isinstance(today, datetime.datetime):
        today = today.date()

    header_parts = []
    activity_parts = []
    
    for i in range(6, -1, -1): # From 6 days ago up to today
        current_date = today - datetime.timedelta(days=i)
        day_initial = days_of_week_initials[current_date.weekday()]
        header_parts.append(f"{day_initial:<{len(day_initial)+ (1 if len(day_initial) == 1 else 0)}}") # Pad single char more

        if current_date == today:
            activity_emoji = "🗓️" if current_date in active_dates_in_period else "🗓️" # Today's emoji (could be different if not active)
        elif current_date in active_dates_in_period:
            activity_emoji = "✅"
        else:
            activity_emoji = "➖"
        activity_parts.append(f"{activity_emoji:<{len(day_initial)+ (1 if len(day_initial) == 1 else 0)}}")

    # Join with a slightly wider space for better visual separation
    # Using three spaces between emojis/headers. Adjust if needed.
    header_str = "   ".join(header_parts)
    activity_str = "   ".join(activity_parts)
    
    return f"```{header_str}\n{activity_str}```*(Past → Today)*"


def generate_monthly_activity_string(active_dates_in_period: Set[datetime.date], today: datetime.date) -> str:
    """Generates a multi-line emoji string for the last 30 days of activity."""
    if not active_dates_in_period and not today: return "`N/A`"
    
    # Ensure today is a date object
    if isinstance(today, datetime.datetime):
        today = today.date()

    activity_lines = []
    num_days_to_show = 30
    
    # Iterate through the 30-day period, grouping into weeks
    # Day 0 is `today - 29 days`, Day 29 is `today`
    all_period_dates = [(today - datetime.timedelta(days=(num_days_to_show - 1 - i))) for i in range(num_days_to_show)]

    week_count = 0
    for i in range(0, num_days_to_show, 7):
        week_count += 1
        week_dates = all_period_dates[i : min(i + 7, num_days_to_show)]
        if not week_dates: continue

        week_emojis = []
        for day_date in week_dates:
            if day_date == today:
                week_emojis.append("🗓️" if day_date in active_dates_in_period else "🗓️")
            elif day_date in active_dates_in_period:
                week_emojis.append("✅")
            else:
                week_emojis.append("➖")
        
        # Format week start/end dates carefully
        start_of_week_fmt = week_dates[0].strftime('%d') # Day only
        end_of_week_fmt = week_dates[-1].strftime('%d %b') # Day and Month (e.g., 23 Jul)
        if week_dates[0].month != week_dates[-1].month: # If week spans months, show month for start too
            start_of_week_fmt = week_dates[0].strftime('%d %b')

        week_header = f"W{week_count} ({start_of_week_fmt} - {end_of_week_fmt}):"
        activity_lines.append(f"{week_header.ljust(20)} {' '.join(week_emojis)}")

    if not activity_lines: return "`No activity data to display for the last 30 days.`"
    return "```\n" + "\n".join(activity_lines) + "\n```"

class HelpPagesView(discord.ui.View):
    def __init__(self, bot_user: discord.User, is_staff_view_allowed: bool, timeout=180.0):
        super().__init__(timeout=timeout)
        self.bot_user = bot_user
        self.current_page = "general" 
        self.is_staff_view_allowed = is_staff_view_allowed
        self.message: Optional[discord.Message] = None
        pass

    def _update_decorated_button_appearance(self, button_to_update: discord.ui.Button):
        if self.current_page == "general":
            button_to_update.label = "View Staff Commands"
            button_to_update.emoji = "🛡️"
            button_to_update.style = discord.ButtonStyle.secondary
        else: 
            button_to_update.label = "Back to General"
            button_to_update.emoji = "⬅️"
            button_to_update.style = discord.ButtonStyle.primary

    def _create_general_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🤓 Pingslave Bot - General Commands", color=NERDY_YELLOW)
        if self.bot_user and self.bot_user.display_avatar:
            embed.set_thumbnail(url=self.bot_user.display_avatar.url)
        embed.description = "Here are commands generally available to users:\n\u200B"
        
        embed.add_field(name="📊 [HC1] Guild & Activity", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('hcmembers')}  · Show interactive HC member list.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('activatemyself')} · Mark *yourself* as active for today.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('profile')} · View your [HC1] profile, activity, and S.Attempt stats.", value="\u200B", inline=False) # MODIFIED description
        
        embed.add_field(name="\u200B\n🕵️ Secret Phrase Discovery", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('discoveries')} · Show secret phrase discovery progress.", value="\u200B", inline=False)
        
        embed.add_field(name="\u200B\n💬 Messaging & Nicknames", value="\u200B", inline=False) # MODIFIED section title
        embed.add_field(name=f"{get_cmd_mention('message')} · Send a message as the bot (opt. AI).", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('florr')} · Send msg with custom name & Florr pic.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('setnickname')} · Manage your S.Attempt nickname template.", value="\u200B", inline=False) # ADDED command
        
        embed.add_field(name="\u200B\n⚙️ Other", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('ping')} · Check bot's latency to Discord.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('nerdhelp')}  · Shows this help message.", value="\u200B", inline=False)
        
        embed.set_footer(text="Bot by TheNerd | sweet_honey")
        return embed

    def _create_staff_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🛡️ Pingslave Bot - Staff Commands", color=NERDY_YELLOW)
        if self.bot_user and self.bot_user.display_avatar:
            embed.set_thumbnail(url=self.bot_user.display_avatar.url)
        embed.description = "These commands typically require server management permissions:\n\u200B"
        
        embed.add_field(name="🔑 Verification & HC Management", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('verify')}  · Verify user. `[Manage Roles]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('unverify')}  · Unverify user. `[Manage Roles]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('hcverify')}  · Verify into HC. `[Manage Roles]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('hconly')} · Register IGN only. `[Manage Roles]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('hcleave')} · Remove from HC. `[Manage Roles]`", value="\u200B", inline=False)
        
        embed.add_field(name="\u200B\n⏱️ Activity Tracking (Staff)", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('active')}  · Mark member active. `[Manage Server]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('inactive')}  · Remove activity. `[Manage Server]`", value="\u200B", inline=False)
        
        embed.add_field(name="\u200B\n⚙️ Utilities (Staff & Owner)", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('imitate')} · Send as another user. `[Manage Server]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('refresh')}  · Refresh list & data. `[Manage Roles]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('syncnicknames')}  · Sync HC nicks for S.Attempts. `[Manage Nicks]`", value="\u200B", inline=False) # MODIFIED description
        embed.add_field(name=f"{get_cmd_mention('wither')}  · Temp role removal. `[Special]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('addkeyword')} · Add keyword rule. `[Owner Only]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('aiping')} · Check AI model latencies. `[Owner Only]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('cleanup_bot_messages')} · Delete N bot messages. `[Owner Only]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('test_petal_match')} · Test petal name fuzzy matching. `[Owner Only]`", value="\u200B", inline=False) # ADDED (if test command is still relevant)

        embed.set_footer(text="Bot by TheNerd | sweet_honey")
        return embed

    def get_current_embed(self) -> discord.Embed:
        if self.current_page == "staff":
            return self._create_staff_embed()
        return self._create_general_embed()

    @discord.ui.button(label="View Staff Commands", emoji="🛡️", style=discord.ButtonStyle.secondary, custom_id="help_toggle_page_decorator_final")
    async def toggle_page_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_staff_view_allowed:
            await interaction.response.send_message("This action is not available.", ephemeral=True, delete_after=5)
            return

        if self.current_page == "general":
            self.current_page = "staff"
        else:
            self.current_page = "general"
        
        self._update_decorated_button_appearance(button) 
        current_embed = self.get_current_embed()
        
        await interaction.response.edit_message(embed=current_embed, view=self)

    async def on_timeout(self):
        if self.message and self.is_staff_view_allowed: 
            try:
                current_embed_on_timeout = self.get_current_embed()
                if current_embed_on_timeout.footer and current_embed_on_timeout.footer.text: # Check footer exists
                    current_embed_on_timeout.set_footer(text=f"{current_embed_on_timeout.footer.text} (Interaction timed out)")
                else: # Fallback if no footer
                    current_embed_on_timeout.set_footer(text="Interaction timed out")
                
                for item in self.children:
                    if isinstance(item, discord.ui.Button) and item.custom_id == "help_toggle_page_decorator_final":
                        item.disabled = True
                        break
                await self.message.edit(embed=current_embed_on_timeout, view=self) 
            except discord.HTTPException:
                pass
        self.stop()

async def profile_pic_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    choices = []
    current_lower = current.lower()
    
    if not available_profile_pics_cache:
        return [app_commands.Choice(name="Error: No images loaded, try later or /refresh", value="error_no_images_loaded")]

    for display_name, folder_id, filename_with_ext in available_profile_pics_cache:
        if not current_lower or current_lower in display_name.lower(): # Show all if current is empty
            # Value format: "FolderName:filename_with_ext.png"
            choice_value = f"{folder_id}:{filename_with_ext}"
            
            # Ensure choice name and value are within Discord's limits (100 chars)
            safe_display_name = (display_name[:97] + "...") if len(display_name) > 100 else display_name
            safe_choice_value = (choice_value[:97] + "...") if len(choice_value) > 100 else choice_value
            
            choices.append(app_commands.Choice(name=safe_display_name, value=safe_choice_value))
        
        if len(choices) >= 25: # Discord's limit for autocomplete suggestions
            break
            
    if not choices and current: # If user typed something but no matches
        return [app_commands.Choice(name=f"No matches for '{current}'", value="error_no_matches_found")]
        
    return choices

async def load_profile_picture_choices(guild_for_log: Optional[discord.Guild]):
    global available_profile_pics_cache, PROFILE_PIC_BASE_PATH
    available_profile_pics_cache.clear()
    
    # Determine the base path relative to this script file
    # This ensures it works correctly on Render
    PROFILE_PIC_BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    
    folders_to_scan = {
        PETALS_FOLDER_NAME: os.path.join(PROFILE_PIC_BASE_PATH, PETALS_FOLDER_NAME),
        MOBS_FOLDER_NAME: os.path.join(PROFILE_PIC_BASE_PATH, MOBS_FOLDER_NAME)
    }
    
    loaded_count = 0
    for folder_id, folder_path in folders_to_scan.items():
        if not os.path.isdir(folder_path):
            print(f"Warning: Profile picture folder not found: {folder_path}")
            if guild_for_log:
                 await log_info(guild_for_log, f"Profile picture folder '{folder_id}' not found at '{folder_path}'. Choices from this folder will be unavailable.")
            continue
            
        try:
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(".png"):
                    # Display name: filename without .png, spaces for underscores, title case
                    display_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
                    available_profile_pics_cache.append((display_name, folder_id, filename))
                    loaded_count += 1
        except OSError as e:
            print(f"Error scanning folder {folder_path}: {e}")
            if guild_for_log:
                 await log_error(guild_for_log, f"Error scanning profile picture folder {folder_path}", error=e)

    if available_profile_pics_cache:
        # Sort by display name for consistent autocomplete
        available_profile_pics_cache.sort(key=lambda x: x[0])
        print(f"Loaded {loaded_count} profile picture choices from folders: {', '.join(folders_to_scan.keys())}.")
        if guild_for_log:
            await log_info(guild_for_log, f"Successfully loaded {loaded_count} profile picture choices.")
    else:
        print("No profile picture choices loaded. Folders might be empty or missing.")
        if guild_for_log:
             await log_info(guild_for_log, "No profile picture choices were loaded (folders empty or not found).")

# Helper function (fetch_avatar_bytes - remains the same)
async def fetch_avatar_bytes(session: aiohttp.ClientSession, url: str) -> Optional[bytes]:
    """Fetches image bytes from a URL."""
    if not url:
        return None
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            else:
                print(f"Failed to fetch avatar from {url}, status: {response.status}")
                return None
    except Exception as e:
        print(f"Error fetching avatar from {url}: {e}")
        return None

async def can_manage_guild_or_is_bypass_user(interaction: discord.Interaction) -> bool:
    if interaction.user.id == OWNER_USER_ID:
        return True  # Bypass user, allow command
    return interaction.permissions.manage_guild

# --- Utility Functions (Helper for static timestamp) ---
def get_formatted_utc_now() -> str:
    """Returns the current UTC date and time in DD/MM/YYYY HH:MM UTC format."""
    return discord.utils.utcnow().strftime("%d/%m/%Y %H:%M UTC")

# --- Screenshot Activity Confirmation View & Buttons ---

class ScreenshotActionButton(discord.ui.Button):
    def __init__(self, ign: str, is_undo: bool, row: int, original_uploader_id: int, activity_date: datetime.date):
        self.ign = ign
        self.is_undo_action = is_undo # True if this button performs an "Undo", False if "Re-activate"
        self.original_uploader_id = original_uploader_id
        self.activity_date = activity_date

        label_prefix = "Undo" if self.is_undo_action else "Re-Activate"
        style = discord.ButtonStyle.danger if self.is_undo_action else discord.ButtonStyle.success
        emoji = "↩️" if self.is_undo_action else "✅"
        
        # Ensure custom_id is unique enough if many buttons
        # Truncate IGN if too long for custom_id (max 100 chars for custom_id)
        safe_ign_for_id = self.ign.replace(" ", "_")[:50] # Basic sanitization
        custom_id_action = "undo" if self.is_undo_action else "reactivate"
        custom_id = f"ss_act_{custom_id_action}_{safe_ign_for_id}_{original_uploader_id}"


        super().__init__(label=f"{label_prefix}: {self.ign}", style=style, emoji=emoji, custom_id=custom_id, row=row)

    async def callback(self, interaction: discord.Interaction):
        view: ScreenshotConfirmView = self.view # Type hint for clarity
        if not view:
            await interaction.response.send_message("Error: View context lost.", ephemeral=True)
            return

        # Security Check: Only the original uploader can use these buttons
        if interaction.user.id != self.original_uploader_id:
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return

        await interaction.response.defer() # Acknowledge the interaction

        guild = interaction.guild
        if not guild: # Should not happen if command is guild-only
            await interaction.followup.send("Error: Guild context lost.", ephemeral=True)
            return

        action_performed_successfully = False
        action_message = ""
        log_action_description = ""

        if self.is_undo_action:
            # --- Perform UNDO Action ---
            # This implies the user was marked active by THIS batch.
            # We need to ensure `remove_activity_log` is safe if the record somehow vanished.
            success, msg = await remove_activity_log(guild, self.ign, self.activity_date, interaction.user.id)
            if success:
                action_performed_successfully = True
                view.update_ign_status(self.ign, 'undone_by_view')
                action_message = f"↩️ Activity UNDONE for `{self.ign}` for {format_date_dmy(self.activity_date)}."
                log_action_description = f"undid activity for IGN {self.ign}"
            elif "No activity record found" in msg: # Successfully "undone" as it was already gone or never properly added
                action_performed_successfully = True # Treat as success for UI update
                view.update_ign_status(self.ign, 'undone_by_view')
                action_message = f"↩️ Activity for `{self.ign}` was already not present for {format_date_dmy(self.activity_date)}. Marked as undone."
                log_action_description = f"attempted to undo activity for IGN {self.ign}, but no record was found"
            else:
                action_message = f"⚠️ Failed to undo activity for `{self.ign}`: {msg}"
                log_action_description = f"failed to undo activity for IGN {self.ign} ({msg})"

        else:
            # --- Perform RE-ACTIVATE Action ---
            success, msg = await upsert_activity_log(guild, self.ign, self.activity_date, interaction.user.id)
            if success:
                action_performed_successfully = True
                view.update_ign_status(self.ign, 'active_by_view') # Mark as active by this view's action
                action_message = f"✅ Activity RE-ACTIVATED for `{self.ign}` for {format_date_dmy(self.activity_date)}."
                log_action_description = f"re-activated activity for IGN {self.ign}"
            else:
                action_message = f"⚠️ Failed to re-activate activity for `{self.ign}`: {msg}"
                log_action_description = f"failed to re-activate activity for IGN {self.ign} ({msg})"

        # Log the button action
        await log_info(guild, f"Screenshot Action: User `{interaction.user}` {log_action_description} via button (Original uploader: {self.original_uploader_id}).")

        # Update the original confirmation message with new embed and buttons
        if action_performed_successfully:
            await view.refresh_message(interaction.message) # Pass the message to edit
            # Trigger static list update if an activity status actually changed
            asyncio.create_task(update_static_list_message(guild))

        # Send an ephemeral follow-up to the user who clicked the button
        await interaction.followup.send(action_message, ephemeral=True)


class ScreenshotConfirmView(View):
    # Max 5 buttons per row. Max 5 rows. Total 25 components.
    # If newly_added_igns_details has more than ~23 items, we can't show all buttons.
    MAX_BUTTONS_DISPLAY = 23 

    def __init__(self, original_author_id: int, activity_date: datetime.date,
                 newly_added_igns_details: List[Dict[str, Any]], # [{'ign': str, 'status': 'active_by_view' | 'undone_by_view'}]
                 already_active_igns: List[str],
                 failed_to_add_igns: List[str], # IGNs that AI found but failed DB ops
                 guild_for_log: discord.Guild,
                 original_message_id: int,
                 timeout: float = 900.0): # 15 minutes timeout
        super().__init__(timeout=timeout)
        self.original_author_id = original_author_id
        self.activity_date = activity_date
        self.newly_added_igns_details = newly_added_igns_details # This list will be modified by buttons
        self.already_active_igns = already_active_igns
        self.failed_to_add_igns = failed_to_add_igns
        self.guild_for_log = guild_for_log # For logging within the view if needed
        self.message_id_to_reply_to = original_message_id # ID of the message we replied to (the one with screenshot)
        
        self._update_ui_elements()

    def _update_ui_elements(self):
        self.clear_items() # Remove previous buttons

        current_row = 0
        buttons_in_row = 0
        buttons_added_count = 0

        for ign_detail in self.newly_added_igns_details:
            if buttons_added_count >= self.MAX_BUTTONS_DISPLAY:
                # Add a placeholder if we exceed max buttons
                # For simplicity, we'll just stop adding more buttons.
                # A "more actions..." button could lead to a modal if needed.
                print(f"Warning: Max buttons ({self.MAX_BUTTONS_DISPLAY}) reached for ScreenshotConfirmView. Not all actions displayed.")
                break

            ign = ign_detail['ign']
            status = ign_detail['status'] # 'active_by_view' or 'undone_by_view'

            is_undo_button = (status == 'active_by_view')
            
            button = ScreenshotActionButton(
                ign=ign,
                is_undo=is_undo_button,
                row=current_row,
                original_uploader_id=self.original_author_id,
                activity_date=self.activity_date
            )
            self.add_item(button)
            buttons_added_count += 1
            buttons_in_row += 1
            if buttons_in_row >= 5: # Max 5 components per row
                buttons_in_row = 0
                current_row += 1
                if current_row >= 5: # Max 5 rows
                    print(f"Warning: Max rows reached for ScreenshotConfirmView buttons.")
                    break
        
    def update_ign_status(self, ign_to_update: str, new_status: str):
        """Updates the status of an IGN in newly_added_igns_details."""
        for detail in self.newly_added_igns_details:
            if detail['ign'] == ign_to_update:
                detail['status'] = new_status
                break
        self._update_ui_elements() # Re-render buttons based on new state

    def create_embed(self) -> discord.Embed:
        title = "📸 Screenshot Activity Update"
        embed_color = NERDY_YELLOW
        description_parts = [f"Activity for **{format_date_dmy(self.activity_date)}** based on your screenshot:"]

        if not self.newly_added_igns_details and not self.already_active_igns and not self.failed_to_add_igns:
            description_parts.append("\nNo players were processed from the screenshot.")
            embed_color = discord.Color.orange()
        else:
            if self.newly_added_igns_details:
                description_parts.append("\n**Newly Marked Active (or status changed via buttons):**")
                for detail in self.newly_added_igns_details:
                    ign = detail['ign']
                    status_icon = "✅" if detail['status'] == 'active_by_view' else "↩️"
                    status_text = "(Active)" if detail['status'] == 'active_by_view' else "(Undo Applied)"
                    description_parts.append(f"- {status_icon} `{discord.utils.escape_markdown(ign)}` {status_text}")
                if len(self.newly_added_igns_details) > self.MAX_BUTTONS_DISPLAY:
                    description_parts.append(f"*(...and {len(self.newly_added_igns_details) - self.MAX_BUTTONS_DISPLAY} more not shown with buttons)*")


            if self.already_active_igns:
                description_parts.append("\n**Already Marked Active Today:**")
                description_parts.extend([f"- 👍 `{discord.utils.escape_markdown(ign)}`" for ign in self.already_active_igns])
            
            if self.failed_to_add_igns:
                description_parts.append("\n**Failed to Process (e.g. DB Error):**")
                description_parts.extend([f"- ❌ `{discord.utils.escape_markdown(ign)}`" for ign in self.failed_to_add_igns])

        embed = discord.Embed(title=title, description="\n".join(description_parts), color=embed_color)
        embed.set_footer(text="Click buttons below to undo/re-activate new entries. (View active for 15 mins)")
        embed.timestamp = discord.utils.utcnow()
        return embed

    async def refresh_message(self, message_obj_to_edit: discord.Message):
        """Edits the message with the current view state."""
        embed = self.create_embed()
        try:
            await message_obj_to_edit.edit(embed=embed, view=self)
        except discord.HTTPException as e:
            await log_error(self.guild_for_log, "Failed to refresh ScreenshotConfirmView message", error=e)

    async def on_timeout(self):
        # Try to edit the message to remove/disable buttons
        # Fetch the message object it's attached to first.
        # This assumes the view was attached to a message sent by the bot.
        if self.message: # self.message should be set when the view is sent
            try:
                self.clear_items() # Remove all buttons
                timeout_embed = self.create_embed() # Get current data
                timeout_embed.description += "\n\n**Button interaction period has ended.**"
                timeout_embed.color = discord.Color.light_grey()
                await self.message.edit(embed=timeout_embed, view=self) # Send view with no items
            except discord.NotFound:
                await log_info(self.guild_for_log, f"ScreenshotConfirmView: Original message {self.message.id} not found on timeout.")
            except discord.HTTPException as e:
                await log_error(self.guild_for_log, f"ScreenshotConfirmView: Failed to edit message on timeout for {self.message.id}", error=e)
        await log_info(self.guild_for_log, f"ScreenshotConfirmView for message {self.message_id_to_reply_to} by user {self.original_author_id} timed out.")
        self.stop()

async def load_ign_cache(guild_for_log: Optional[discord.Guild]):
    """Loads all In-Game Names where is_in_hc is TRUE from Supabase into an in-memory cache."""
    global ingame_name_cache
    if not supabase:
        await log_error(guild_for_log, "IGN Cache loading failed: Supabase unavailable.", ping_owner=True)
        ingame_name_cache = [] # Ensure it's empty on failure
        return

    print("Loading IGN cache from Supabase (only members with is_in_hc = TRUE)...")
    try:
        # Fetch ingame_name for entries where is_in_hc is TRUE and ingame_name is not null
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("ingame_name")
                           .eq("is_in_hc", True)  # <-- ADDED THIS FILTER
                           .not_.is_("ingame_name", "null")
                           .execute()
        )

        if not resp or not hasattr(resp, 'data') or not resp.data:
            await log_info(guild_for_log, "No IGN data found (where is_in_hc=TRUE) or failed to fetch for cache. IGN cache will be empty.")
            ingame_name_cache = []
            return

        # Extract unique IGNs from the response
        temp_igns = set()
        for entry in resp.data:
            ign = entry.get("ingame_name")
            if ign: # Check if ign is not None and not an empty string
                temp_igns.add(str(ign)) # Convert to string just in case

        ingame_name_cache = sorted(list(temp_igns), key=str.lower) # Store as a sorted list (case-insensitive sort)

        print(f"Loaded {len(ingame_name_cache)} unique In-Game Names (is_in_hc=TRUE) into cache.")
        await log_info(guild_for_log, f"Successfully loaded {len(ingame_name_cache)} IGNs (is_in_hc=TRUE) into local cache.")

    except (APIError, ConnectionError, Exception) as e:
        await log_error(guild_for_log, "Failed to load IGN cache (is_in_hc=TRUE) from Supabase", error=e, ping_owner=True)
        ingame_name_cache = [] # Clear cache on error




    







class SelfActivateButton(discord.ui.Button):
    """Button for users to mark themselves active for today."""
    def __init__(self, row: int):
        super().__init__(label="Activate Myself Today", style=discord.ButtonStyle.success, emoji="✅", custom_id="static_activate_self", row=row)

    async def callback(self, interaction: discord.Interaction):
        view: StaticHCPagesView = self.view # type: ignore
        guild = interaction.guild 

        if not view or not guild:
            await interaction.response.send_message("❌ Cannot perform action: View or Guild context lost.", ephemeral=True)
            return

        # Send deprecation message
        await interaction.response.send_message(DEPRECATION_MESSAGE_ACTIVITY, ephemeral=True)
        
        # Log the attempt
        await log_info(guild, f"`{interaction.user.name}` (`{interaction.user.id}`) clicked the deprecated 'Activate Myself Today' button on the static list.")
        # IMPORTANT: Do NOT update view.last_interaction_time here to prevent view reset timer from being affected by this deprecated feature.

# --- Buttons and Views for the NEW Static List ---

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

# --- Static List View (REVISED Class) ---
# Inherits directly from View, copies logic as needed.
class StaticHCPagesView(View):

    # --- Data Update Method (Unchanged) ---
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
                message_to_edit: Optional[discord.Message] = None
                try:
                    message_to_edit = await channel.fetch_message(self.message_id)
                    # Directly edit the message object, not an interaction
                    await self.edit_message_object(message=message_to_edit)
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


    # --- __init__ (Unchanged except removing decorators) ---
    def __init__(self, original_data: List[Dict[str, Any]], initial_display_data: List[Dict[str, Any]], total_members: int, guild: discord.Guild, message: Optional[discord.Message] = None, timeout=None): # Pass message object
        super().__init__(timeout=timeout)
        self.original_data = original_data
        self.current_data = initial_display_data
        self.total_members = total_members
        self.current_page = 0
        # Store the message object directly
        self.message: Optional[discord.Message] = message
        # Keep message_id for convenience/logging if needed
        self.message_id: Optional[int] = message.id if message else None
        self.guild = guild
        self.is_target_guild = True
        self.bot_owner_id = OWNER_USER_ID

        # --- State (Unchanged) ---
        self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY
        self.sort_mode = SORT_MODE_ACTIVITY
        self.info_mode_active = False
        self.is_fetching_activity = False
        self.last_interaction_time = discord.utils.utcnow()

        # --- Initial Sort (Unchanged) ---
        self.sort_data()

        # --- Recalculate total pages (Unchanged) ---
        self.total_pages = math.ceil(len(self.current_data) / MEMBERS_PER_PAGE) if self.current_data else 1

        # --- Add UI Elements (Calls the refactored method) ---
        self.update_ui_elements()

    # --- Methods copied/adapted from HCPagesView (Unchanged: fetch_and_set_data, sort_data) ---
    async def fetch_and_set_data_for_mode(self, mode: str, start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None):
        """Fetches activity if needed and sets self.current_data. Now ASYNC."""
        print(f"[Static View] Async setting data for mode: {mode}")
        # ... (rest of method unchanged) ...

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
        # ... (rest of method unchanged) ...
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


    # --- REFACTORED update_ui_elements ---
    def update_ui_elements(self):
        """Clears and explicitly re-adds UI elements based on the current state."""
        self.clear_items() # Remove all existing items

        if self.info_mode_active:
            # Only show the "Back" button in info mode
            back_button = InfoButton(is_info_active=True, row=0)
            # Assign callback directly
            back_button.callback = self.toggle_info_mode
            self.add_item(back_button)
        else:
            # --- Row 0: Navigation ---
            prev_button = discord.ui.Button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="static_prev", row=0, disabled=self.current_page == 0 or self.is_fetching_activity)
            prev_button.callback = self.previous_button_callback
            self.add_item(prev_button)

            next_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.blurple, custom_id="static_next", row=0, disabled=self.current_page >= self.total_pages - 1 or self.is_fetching_activity)
            next_button.callback = self.next_button_callback
            self.add_item(next_button)

            # --- Row 1: Sorting & Info ---
            sort_button_disabled = self.is_fetching_activity
            if self.view_mode == VIEW_MODE_DISCORD:
                sort_label = "Sort by IGN" if self.sort_mode == SORT_MODE_DISCORD_NAME else "Sort by Discord Name"
            else:
                sort_label = "Sort by IGN" if self.sort_mode == SORT_MODE_ACTIVITY else "Sort by Activity"

            sort_button = discord.ui.Button(label=sort_label, style=discord.ButtonStyle.success, custom_id="static_toggle_sort", row=1, disabled=sort_button_disabled)
            sort_button.callback = self.sort_button_callback
            self.add_item(sort_button)

            info_button = InfoButton(is_info_active=False, row=1)
            info_button.callback = self.toggle_info_mode # Use the same callback method
            self.add_item(info_button)

            # --- Row 2: Actions (Self Activate & My Profile) ---
            activate_button = SelfActivateButton(row=2)
            # This button has its own callback defined in its class, no need to assign here
            self.add_item(activate_button)

            profile_button = MyProfileButton(row=2)
            profile_button.callback = self.show_my_profile
            self.add_item(profile_button)

            # --- Row 3: View Mode Select ---
            options = [
               discord.SelectOption(label="View Discord Names + IGN", value=VIEW_MODE_DISCORD, description="Show Discord usernames and IGNs.", emoji="👤"),
               discord.SelectOption(label="View Activity (Today)", value=VIEW_MODE_ACTIVITY_DAILY, description="Show IGNs active today.", emoji="📅"),
               discord.SelectOption(label="View Activity (Last 7 Days)", value=VIEW_MODE_ACTIVITY_WEEKLY, description="Show IGNs active in the last week.", emoji="📅"),
               discord.SelectOption(label="View Activity (Last 30 Days)", value=VIEW_MODE_ACTIVITY_MONTHLY, description="Show IGNs active in the last 30 days.", emoji="📅"),
               discord.SelectOption(label="View Activity (All-Time)", value=VIEW_MODE_ACTIVITY_ALL, description="Show IGNs and total activity count.", emoji="📊"),
            ]
            for option in options: option.default = option.value == self.view_mode

            view_select = discord.ui.Select(
                placeholder="Select View Mode...",
                min_values=1,
                max_values=1,
                options=options,
                custom_id="static_view_select",
                row=3,
                disabled=self.is_fetching_activity
            )
            view_select.callback = self.view_select_callback
            self.add_item(view_select)

    # --- REVISED create_page_embed (v3 - Handles Mentions Outside Code Block) ---
    def create_page_embed(self) -> discord.Embed:
        """Creates embed based on current view_mode, sort_mode, and context."""
        # --- Info Mode Embed (Specific to StaticHCPagesView - remains the same) ---
        if hasattr(self, 'info_mode_active') and self.info_mode_active: # Check if it's the static view
             # ... (Keep the existing info mode embed logic as is) ...
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
             embed.set_footer(text=f"Info Mode | Updated: {get_formatted_utc_now()}")
             return embed

        # --- Standard Page Embed Logic ---
        start = self.current_page * MEMBERS_PER_PAGE
        page_data = self.current_data[start : start + MEMBERS_PER_PAGE]
        idx = start + 1
        desc_lines = []

        if not page_data:
            desc_lines = ["No members found matching criteria."]
        elif self.view_mode == VIEW_MODE_DISCORD:
            # Format: #. `IGN` DiscordMention (Mention is OUTSIDE code block)
            IDX_WIDTH = 3
            # Define a visual width for the IGN part within backticks
            # Let's try 18 characters for the IGN display area.
            IGN_DISPLAY_WIDTH = 18

            for item_dict in page_data:
                ign = item_dict.get('ign', 'Unknown')
                index_str = f"{str(idx)+'.':<{IDX_WIDTH}} " # Index with padding and space

                # Get User ID for mention
                user_id_str: Optional[str] = None
                member = item_dict.get('member') # discord.Member object or None
                if member:
                    user_id_str = str(member.id)
                else:
                    user_id_str = item_dict.get("discord_id")

                # Construct mention or fallback text
                if user_id_str:
                    mention_display = f"<@!{user_id_str}>"
                else:
                    mention_display = "`[No Discord]`" # Use backticks for placeholder

                # Truncate IGN
                ign_display = ign
                if len(ign_display) > IGN_DISPLAY_WIDTH:
                     ign_display = ign_display[:IGN_DISPLAY_WIDTH-1] + "…"

                # Format line: Index<space> `IGN (padded)`<space>Mention
                # Note: Alignment might not be perfect due to variable mention width vs fixed IGN block width
                line = f"{index_str}`{ign_display:<{IGN_DISPLAY_WIDTH}}` {mention_display}"
                desc_lines.append(line)
                idx += 1

        elif self.view_mode in [VIEW_MODE_ACTIVITY_ALL, VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
            # Format: ``` #. IGN Activity ``` (Uses fixed-width code block)
            IDX_WIDTH = 3
            SPACE_WIDTH = 1
            IDX_PLUS_SPACE_WIDTH = IDX_WIDTH + SPACE_WIDTH # 4
            CONTENT_WIDTH = 34 # 38 - 4
            ACT_WIDTH = 18
            IGN_WIDTH = 16 # CONTENT_WIDTH - ACT_WIDTH = 34 - 18 = 16
            TOTAL_WIDTH = IDX_PLUS_SPACE_WIDTH + CONTENT_WIDTH # Should be 38

            header = (f"{'#':<{IDX_WIDTH}} {'IGN':<{IGN_WIDTH}}{'Activity':<{ACT_WIDTH}}")
            # Correct separator width
            separator = "-" * TOTAL_WIDTH

            desc_lines.append("```")
            desc_lines.append(header)
            desc_lines.append(separator)

            for item_dict in page_data:
                ign = item_dict.get('ign', 'Unknown')
                activity_count = item_dict.get('activity_count', 0)
                last_seen_date = item_dict.get('last_seen') # date object or None
                activity_display = f"{activity_count} ({format_date_dmy(last_seen_date)})"

                # Add space after index number
                index_str = f"{str(idx)+'.':<{IDX_WIDTH}} " # Pad index and add space

                # Truncate IGN and Activity
                ign_display = ign
                if len(ign_display) > IGN_WIDTH: ign_display = ign_display[:IGN_WIDTH-1] + "…"
                if len(activity_display) > ACT_WIDTH: activity_display = activity_display[:ACT_WIDTH-1] + "…"

                # Format Line: #<space>IGN<padding>Activity<padding>
                line = (f"{index_str}{ign_display:<{IGN_WIDTH}}{activity_display:<{ACT_WIDTH}}")
                desc_lines.append(line)
                idx += 1
            desc_lines.append("```")

        else: # Fallback
            desc_lines = ["Error: Invalid View Mode"]

        # --- Title (Handles context for HCPagesView) ---
        title = HC_LIST_EMBED_TITLE
        if hasattr(self, 'is_catercord_context') and not self.is_catercord_context:
            title = "HC Database Members (All)"

        embed = discord.Embed(
            title=title,
            description="\n".join(desc_lines), # Join the constructed lines
            color=NERDY_YELLOW
        )

        # --- Footer Update (Remains the same logic) ---
        sort_text = "IGN" if self.sort_mode == SORT_MODE_IGN else "Activity"
        view_text_map = {
            VIEW_MODE_DISCORD: "IGN+Discord", # Keep updated text
            VIEW_MODE_ACTIVITY_ALL: "Activity (All)",
            VIEW_MODE_ACTIVITY_DAILY: "Activity (Today)",
            VIEW_MODE_ACTIVITY_WEEKLY: "Activity (7d)",
            VIEW_MODE_ACTIVITY_MONTHLY: "Activity (30d)",
        }
        view_text = view_text_map.get(self.view_mode, "Unknown View")
        footer_text = (
            f"Page {self.current_page + 1}/{self.total_pages} | Total: {self.total_members} | "
            f"View: {view_text} | Sort: {sort_text}"
        )
        if hasattr(self, 'is_fetching_activity') and self.is_fetching_activity:
             footer_text += " | Fetching data..."
        footer_text += f" | Updated: {get_formatted_utc_now()}"
        embed.set_footer(text=footer_text)
        return embed

    # --- NEW: Helper to edit the Message Object ---
    async def edit_message_object(self, message: Optional[discord.Message] = None):
        """Edits the view's underlying message object."""
        message_to_edit = message or self.message
        if not message_to_edit:
            print(f"[Static View {self.message_id}] Error: edit_message_object called without a message.")
            return

        self.update_ui_elements() # Update button states etc. *before* creating embed
        embed = self.create_page_embed()

        try:
            await message_to_edit.edit(embed=embed, view=self)
        except discord.NotFound:
            print(f"[Static View] Message edit fail: Message {message_to_edit.id} not found.")
            self.stop()
            if self.guild and self.message_id:
                 if self.guild.id in active_static_list_views and active_static_list_views[self.guild.id]['message_id'] == self.message_id:
                      del active_static_list_views[self.guild.id]
                      print(f"[Static View] Removed view tracking for message {self.message_id} as it was not found.")
        except discord.HTTPException as e:
            # Log non-404 errors
            if e.status != 404:
                await log_error(self.guild, f"Static list Message edit fail (HTTP {e.status})", error=e)
        except Exception as e:
            await log_error(self.guild, f"Static list Message edit fail (General) for {message_to_edit.id}", error=e)

    # --- NEW: Helper to respond to Interaction (Initial Edit) ---
    async def respond_to_interaction(self, interaction: discord.Interaction):
        """Handles the initial edit response for an interaction."""
        if interaction.response.is_done():
            print(f"[Static View] Warning: respond_to_interaction called for already responded interaction {interaction.id}")
            # Attempt to edit the original response if possible, otherwise log
            try:
                await self.edit_message_object(await interaction.original_response())
            except Exception as e_edit_orig:
                print(f"[Static View] Failed to edit original response after double-response warning: {e_edit_orig}")
            return

        self.update_ui_elements() # Prepare UI elements
        embed = self.create_page_embed() # Prepare embed

        try:
            await interaction.response.edit_message(embed=embed, view=self)
            # Try to link the message object if not already linked
            if not self.message:
                 try:
                     self.message = await interaction.original_response()
                     self.message_id = self.message.id
                 except (discord.NotFound, discord.HTTPException):
                      print(f"[Static View] Failed to fetch original response for interaction {interaction.id} after edit.")

        except discord.NotFound:
            print(f"[Static View] Interaction edit fail: Interaction {interaction.id} not found.")
            self.stop()
        except discord.HTTPException as e:
            # Avoid logging interaction cancelled errors if user was quick
            if e.code != 10062: # Unknown Interaction
                 await log_error(self.guild, "Interaction edit fail (HTTP)", error=e, interaction=interaction)
        except Exception as e:
             await log_error(self.guild, "Interaction edit fail (General)", error=e, interaction=interaction)

    # --- REMOVED update_view ---

    # --- Interaction Callbacks (Modified to use respond_to_interaction) ---
    # These methods are now assigned directly to button.callback in update_ui_elements

    async def previous_button_callback(self, interaction: discord.Interaction):
        """Callback for the Previous button."""
        if self.current_page > 0 and not self.is_fetching_activity:
            self.current_page -= 1
            self.last_interaction_time = discord.utils.utcnow() # Update timestamp
            await self.respond_to_interaction(interaction) # Initial response/edit
        else:
            await interaction.response.defer() # Ack the interaction if no action taken

    async def next_button_callback(self, interaction: discord.Interaction):
        """Callback for the Next button."""
        if self.current_page < self.total_pages - 1 and not self.is_fetching_activity:
            self.current_page += 1
            self.last_interaction_time = discord.utils.utcnow() # Update timestamp
            await self.respond_to_interaction(interaction) # Initial response/edit
        else:
            await interaction.response.defer() # Ack

    async def sort_button_callback(self, interaction: discord.Interaction):
        """Callback for the Sort button."""
        if self.is_fetching_activity:
            await interaction.response.defer()
            return # Don't update last interaction time if fetching

        self.last_interaction_time = discord.utils.utcnow() # Update timestamp

        if self.view_mode == VIEW_MODE_DISCORD:
            self.sort_mode = SORT_MODE_IGN if self.sort_mode == SORT_MODE_DISCORD_NAME else SORT_MODE_DISCORD_NAME
        else:
             if self.sort_mode == SORT_MODE_IGN:
                 self.sort_mode = SORT_MODE_ACTIVITY
             else:
                 self.sort_mode = SORT_MODE_IGN

        self.sort_data() # Re-sort the current data
        await self.respond_to_interaction(interaction) # Initial response/edit

    async def view_select_callback(self, interaction: discord.Interaction):
        """Callback for the View Mode Select dropdown."""
        # The select object is implicitly available via interaction.data in newer d.py?
        # Or access via interaction.to_dict() maybe? Let's assume we get the values.
        # It's safer to find the component in the view if needed, but values are often passed directly.
        try:
            # In dpy 2.0+, interaction.data['values'] should contain the selected option(s).
            new_mode = interaction.data['values'][0]
        except (KeyError, IndexError):
            print("[Static View] Error: Could not get selected value from interaction data for view_select.")
            await interaction.response.defer() # Defer to prevent "Interaction Failed"
            return

        if self.view_mode == new_mode or self.is_fetching_activity:
            await interaction.response.defer()
            return

        self.last_interaction_time = discord.utils.utcnow()
        self.is_fetching_activity = True
        self.view_mode = new_mode

        # --- Initial Response: Show Loading State ---
        await self.respond_to_interaction(interaction) # Edit interaction to show loading

        # --- Ensure self.message is available for the final edit ---
        if not self.message:
             try:
                 self.message = await interaction.original_response()
                 self.message_id = self.message.id
             except (discord.NotFound, discord.HTTPException) as e_fetch_orig:
                  print(f"[Static View] Error fetching original response in view_select: {e_fetch_orig}. Cannot perform final update.")
                  self.is_fetching_activity = False # Release lock
                  # Optionally try to send an ephemeral error to user
                  try: await interaction.followup.send("❌ Error preparing view update.", ephemeral=True)
                  except Exception: pass
                  return # Stop processing

        # --- Fetch Data and Final Update ---
        try:
            await self.fetch_and_set_data_for_mode(new_mode)
            self.sort_mode = SORT_MODE_IGN if new_mode == VIEW_MODE_DISCORD else SORT_MODE_ACTIVITY
            self.sort_data()

        except Exception as e:
            await log_error(self.guild, f"Error changing static list view mode to {new_mode}", error=e, interaction=interaction)
            # Reset to a safe state
            self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY
            await self.fetch_and_set_data_for_mode(self.view_mode) # Await the async method here too for reset
            self.sort_mode = SORT_MODE_ACTIVITY
            self.sort_data()
            try: await interaction.followup.send("❌ Error fetching data for view.", ephemeral=True)
            except Exception: pass # Ignore if followup fails
        finally:
            self.is_fetching_activity = False
            # --- Final Edit: Use self.edit_message_object ---
            # This edits the message directly, not the interaction again.
            await self.edit_message_object()

    # --- NEW Callbacks for Info and My Profile (Unchanged structure, but now assigned in update_ui_elements) ---

    async def toggle_info_mode(self, interaction: discord.Interaction):
        """Callback for the InfoButton."""
        self.last_interaction_time = discord.utils.utcnow() # Update timestamp
        self.info_mode_active = not self.info_mode_active
        await self.respond_to_interaction(interaction) # Use initial response method

    async def show_my_profile(self, interaction: discord.Interaction):
        """Callback for the MyProfileButton. Shows the user's profile ephemerally."""
        guild = interaction.guild # Should be the static list's guild
        if not guild: # Should not happen if view is guild-bound
            await interaction.response.send_message("Error: Guild context lost for profile.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        if not await check_supabase_available(interaction):
            # check_supabase_available sends its own ephemeral message if DB is down
            # We might need to edit the deferred response if check_supabase_available already responded.
            # For now, assuming check_supabase_available handles the response logic.
            # If it doesn't send a message itself, we'd use interaction.followup.send here.
            # Let's ensure the deferred state is handled:
            try:
                await interaction.edit_original_response(content="❌ Database connection unavailable. Cannot fetch profile data.", view=None)
            except (discord.NotFound, discord.HTTPException):
                pass # If already responded or interaction gone.
            return

        # --- Fetch data for interaction.user (self-profile) ---
        target_user_for_display = interaction.user
        target_discord_id_str = str(interaction.user.id)
        
        hc_profile_db_data = await fetch_hc_member_profile_data(guild, target_discord_id_str)
        target_ign_from_db: Optional[str] = None
        if hc_profile_db_data:
            target_ign_from_db = hc_profile_db_data.get("ingame_name")
        
        if not target_ign_from_db:
            await interaction.followup.send(
                f"❌ {interaction.user.mention}, I couldn't find a linked In-Game Name (IGN) for you in the database. "
                f"Use {get_cmd_mention('hcverify')} or {get_cmd_mention('verify')} to link your IGN.",
                ephemeral=True
            )
            return

        # Prepare display data for the ProfilePagesView
        display_name_for_view: str = target_user_for_display.display_name
        avatar_url_for_view: Optional[str] = target_user_for_display.display_avatar.url if target_user_for_display.display_avatar else target_user_for_display.default_avatar.url
        mention_or_status_for_view: str = target_user_for_display.mention
        actual_member_object_ref: Optional[discord.Member] = None
        if isinstance(target_user_for_display, discord.Member):
            actual_member_object_ref = target_user_for_display

        target_user_display_data_for_view = {
            "name": display_name_for_view,
            "avatar_url": avatar_url_for_view,
            "mention_or_status": mention_or_status_for_view,
            "_member_object_ref": actual_member_object_ref,
            "_discord_id_for_sa_management": target_discord_id_str
        }

        # Fetch Activity and Super Attempt Data
        activity_summary_for_view: Optional[Dict[str, Any]] = None
        initial_monthly_dates_for_view: Set[datetime.date] = set()
        super_attempt_stats_data_for_view: Optional[Dict[str, Any]] = None
        today_utc_obj, _ = get_utc_date()

        if target_ign_from_db and today_utc_obj:
            ign_lower = target_ign_from_db.lower()
            
            is_active_today = await check_activity_exists(guild, ign_lower, today_utc_obj)
            active_today_disp = "❔ `N/A (DB Error)`"
            if is_active_today is True: active_today_disp = "✅ `Yes`"
            elif is_active_today is False: active_today_disp = "❌ `No`"
            
            all_time_summary = await fetch_activity_data(guild, [ign_lower])
            ign_all_time_data = all_time_summary.get(ign_lower, {'count': 0, 'last_seen': None})
            
            activity_summary_for_view = {
                "active_today_display": active_today_disp,
                "total_days_logged": ign_all_time_data['count'],
                "last_seen_display": f"`{format_date_dmy(ign_all_time_data['last_seen'])}`" if ign_all_time_data['last_seen'] else "`Never Logged`"
            }
            
            first_day_current_month = today_utc_obj.replace(day=1)
            if today_utc_obj.month == 12:
                first_day_next_month = first_day_current_month.replace(year=today_utc_obj.year + 1, month=1)
            else:
                first_day_next_month = first_day_current_month.replace(month=today_utc_obj.month + 1)
            last_day_current_month = first_day_next_month - datetime.timedelta(days=1)
            
            initial_monthly_dates_for_view = await fetch_activity_dates_in_range(
                guild, ign_lower, first_day_current_month, last_day_current_month
            )
            super_attempt_stats_data_for_view = await get_user_super_attempt_stats(guild, target_ign_from_db)
        
        if not today_utc_obj: # Should not happen if get_utc_date is robust
            await log_error(guild, "Static List Profile: Failed to get today's date object.", interaction=interaction)

        # Create and Send ProfilePagesView
        profile_view_instance = ProfilePagesView(
            interaction=interaction, # Pass the interaction that triggered this profile view
            target_user_display_data=target_user_display_data_for_view,
            hc_profile_data=hc_profile_db_data,
            activity_summary_data=activity_summary_for_view,
            initial_monthly_active_dates=initial_monthly_dates_for_view,
            super_attempt_stats_data=super_attempt_stats_data_for_view,
            today_date_obj=today_utc_obj if today_utc_obj else datetime.date.today() # Fallback for today_date_obj
        )
        
        initial_profile_embed = profile_view_instance._create_main_embed()
        
        try:
            # Send the profile as an ephemeral followup
            profile_message = await interaction.followup.send(embed=initial_profile_embed, view=profile_view_instance, ephemeral=True)
            profile_view_instance.message = profile_message # Link message to view for its own timeout handling
        except discord.HTTPException as e_send_profile:
            await log_error(guild, "Failed to send ephemeral profile from static list button", error=e_send_profile, interaction=interaction)
            try: # Try to edit the original deferred response with a simpler error
                await interaction.edit_original_response(content="❌ Error displaying your profile. Please try again later.", view=None)
            except (discord.NotFound, discord.HTTPException):
                pass # Original interaction might be gone


    # --- Timeout and Reset (Modify reset_view to use edit_message_object) ---
    async def on_timeout(self):
        print(f"[Static View] Default on_timeout triggered for view on message {self.message_id}. Disabling items.")
        # Update UI elements to get disabled state
        self.update_ui_elements()
        # Stop listening FIRST
        self.stop()
        # Try to edit the message one last time using the message object
        await self.edit_message_object()


    async def reset_view(self):
        """Resets the view state to default (called by background task)."""
        print(f"[Static View] Resetting view state for message {self.message_id} due to inactivity.")
        self.current_page = 0
        self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY
        self.sort_mode = SORT_MODE_ACTIVITY
        self.info_mode_active = False
        self.is_fetching_activity = True # Prevent interactions during reset fetch

        if not self.guild:
             print("[Static View] Reset Error: Guild object is None.")
             self.is_fetching_activity = False
             return
        channel = self.guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
             print(f"[Static View] Reset Error: Channel {HC_MEMBER_LIST_CHANNEL_ID} not found or not TextChannel.")
             self.is_fetching_activity = False
             return

        message_to_edit: Optional[discord.Message] = None
        try:
            # Fetch the message object first
            if self.message_id:
                message_to_edit = await channel.fetch_message(self.message_id)
                self.message = message_to_edit # Update internal reference

            # Fetch data for the default mode
            await self.fetch_and_set_data_for_mode(self.view_mode)
            self.sort_data()

        except discord.NotFound:
             print(f"[Static View] Reset Error: Message {self.message_id} not found. Stopping tracking.")
             if self.guild.id in active_static_list_views:
                 # Check if key exists before deleting
                 if channel.id in active_static_list_views:
                     del active_static_list_views[channel.id]
             self.stop()
             return
        except Exception as e:
             print(f"[Static View] Reset Error during data fetch or message fetch: {e}")
             await log_error(self.guild, "[Static View] Reset Error during data/message fetch", error=e)
             self.is_fetching_activity = False
             return
        finally:
             self.is_fetching_activity = False

        # --- Edit the Message using the object ---
        if message_to_edit:
            try:
                await self.edit_message_object(message=message_to_edit) # Use the specific edit method
                print(f"[Static View] Successfully reset and edited message {self.message_id}.")
                self.last_interaction_time = discord.utils.utcnow() # Update timestamp
            except Exception as e_edit:
                 # edit_message_object already handles logging NotFound etc.
                 print(f"[Static View] Reset Error: Failed to edit message {self.message_id} after reset (Error handled in edit_message_object): {e_edit}")
        else:
             print(f"[Static View] Reset Warning: message_to_edit object was None, could not finalize reset edit.")

async def fetch_all_supabase_hc_data(guild_for_log: Optional[discord.Guild]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fetches HC member data (where is_in_hc = TRUE) directly from Supabase (IGN, Discord ID/Name)
    and correlates with ALL activity data. Used when Discord context is unavailable/irrelevant.
    Returns a list of dicts: [{'discord_id': str | None, 'discord_name': str | None, 'ign': str, 'activity_count': int, 'last_seen': date | None, 'is_in_hc': bool}]
    and the total count. Sorted by IGN case-insensitive.
    """
    print("Fetch All Supabase Data (is_in_hc=TRUE): Starting fetch...")
    if not supabase:
        await log_error(guild_for_log, "fetch_all_supabase_hc_data failed: Supabase client unavailable.", ping_owner=True)
        return [], 0

    # 1. Fetch members from hc_members table where is_in_hc is TRUE
    active_hc_members_data = []
    try:
        print("Fetch All Supabase Data: Fetching from hc_members where is_in_hc = TRUE...")
        resp_members = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("discord_id, discord_name, ingame_name, is_in_hc") # Added is_in_hc
                           .eq("is_in_hc", True)  # <-- ADDED THIS FILTER
                           .execute()
        )
        if resp_members and hasattr(resp_members, 'data') and resp_members.data:
            active_hc_members_data = resp_members.data
            print(f"Fetch All Supabase Data: Found {len(active_hc_members_data)} entries in hc_members with is_in_hc = TRUE.")
        else:
            print("Fetch All Supabase Data: No data returned from hc_members (is_in_hc=TRUE).")
            return [], 0

    except (ConnectionError, APIError, Exception) as e:
        await log_error(guild_for_log, "Failed to fetch data from Supabase hc_members (is_in_hc=TRUE)", error=e, ping_owner=True)
        return [], 0

    # 2. Fetch all activity data (for the IGNs found)
    activity_summary: Dict[str, Dict[str, Any]] = {} # ign_lower -> {'count': int, 'last_seen': date}
    all_igns_in_db = [entry['ingame_name'] for entry in active_hc_members_data if entry.get('ingame_name')]

    if not all_igns_in_db:
         print("Fetch All Supabase Data: No IGNs found in fetched member data (is_in_hc=TRUE). Skipping activity fetch.")
    else:
        print(f"Fetch All Supabase Data: Fetching all-time activity for {len(all_igns_in_db)} IGNs (is_in_hc=TRUE)...")
        try:
            activity_summary = await fetch_activity_data(guild_for_log, all_igns_in_db)
            print(f"Fetch All Supabase Data: Fetched activity summary for {len(activity_summary)} IGNs.")
        except Exception as e_act:
             await log_error(guild_for_log, "Failed during all-time activity fetch in fetch_all_supabase_hc_data", error=e_act, ping_owner=True)

    # 3. Combine Member and Activity Data
    final_data: List[Dict[str, Any]] = []
    for member_entry in active_hc_members_data:
        ign = member_entry.get("ingame_name")
        if not ign: continue

        ign_lower = ign.lower()
        activity = activity_summary.get(ign_lower, {'count': 0, 'last_seen': None})

        final_data.append({
            "discord_id": member_entry.get("discord_id"),
            "discord_name": member_entry.get("discord_name"),
            "ign": ign,
            "activity_count": activity.get('count', 0),
            "last_seen": activity.get('last_seen'),
            "is_in_hc": member_entry.get("is_in_hc", True) # Should always be true due to query
        })

    # 4. Sort by IGN (case-insensitive) as default
    final_data.sort(key=lambda item: item['ign'].lower())

    total_members = len(final_data)
    print(f"Fetch All Supabase Data (is_in_hc=TRUE): Finished. Total entries prepared: {total_members}.")
    return final_data, total_members

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
                
async def ign_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes In-Game Names from the local cache or hc_members table."""
    choices = []
    limit = 25 # Max choices Discord allows for autocomplete

    current_lower = current.lower() # For case-insensitive matching

    # --- Use local cache if available and populated ---
    if ingame_name_cache:
        # print(f"IGN Autocomplete: Using cache with {len(ingame_name_cache)} items for '{current}'.") # Optional: for debugging
        
        matched_igns = [
            ign for ign in ingame_name_cache
            if current_lower in ign.lower() # Case-insensitive search within the cache
        ]
        
        for ign_str in matched_igns[:limit]: # Apply limit after filtering
            # Ensure name and value are strings
            # Truncate suggestion name if too long for Discord UI
            display_name = (ign_str[:97] + '...') if len(ign_str) > 100 else ign_str
            choices.append(app_commands.Choice(name=display_name, value=ign_str))
        
        # print(f"IGN Autocomplete (Cache): Found {len(choices)} choices for '{current}'") # Optional: for debugging
        return choices

    # --- Fallback to Supabase if cache is empty or not loaded ---
    print("IGN Autocomplete: Cache empty or not loaded, falling back to Supabase query.")
    if not supabase:
        print("IGN Autocomplete (Fallback): Supabase unavailable.")
        return [] # Return empty list if DB is down and cache is empty

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
        # print(f"IGN Autocomplete (Supabase Fallback): Found {len(choices)} choices for '{current}'") # Optional: for debugging
        return choices

    except (ConnectionError, APIError) as e:
        print(f"IGN Autocomplete Error (Supabase Fallback): Failed to fetch IGNs matching '{current}'. Error: {e}")
    except Exception as e:
         print(f"IGN Autocomplete Unexpected Error (Supabase Fallback): {e}")

    return [] # Return empty list on error during fallback

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

# --- REVISED log_info ---
async def log_info(guild: Optional[discord.Guild], message: str, embed: Optional[discord.Embed] = None):
    """Logs an info message. Sends to Discord channel only if in the target guild, otherwise prints to console."""
    is_target = guild and guild.id == CATERCORD_GUILD_ID

    log_prefix = f"[{guild.name if guild else 'No Guild'}] INFO:"
    if not is_target:
        log_prefix = f"[Console Log Only - Non-Target Guild] INFO:"

    # Print to console regardless
    print(f"{log_prefix} {message}")
    if embed:
        # Basic console representation of embed title/desc if printing only
        embed_title = getattr(embed, 'title', None)
        embed_desc = getattr(embed, 'description', None)
        if embed_title: print(f"{log_prefix} Embed Title: {embed_title}")
        if embed_desc: print(f"{log_prefix} Embed Desc: {embed_desc[:200]}{'...' if len(embed_desc) > 200 else ''}")

    # Only attempt Discord channel logging if in the target guild
    if is_target and guild: # Ensure guild object exists for log_to_channel
        if not embed:
            embed = discord.Embed(description=message, color=NERDY_YELLOW)
            embed.timestamp = discord.utils.utcnow()
        # Use log_to_channel but target INFO channel and no ping
        await log_to_channel(ORDINARY_LOGS_CHANNEL_ID, guild, embed=embed, ping_mention=None)
    # else:
    #     print(f"[Skipping Discord log - Non-Target Guild or No Guild] INFO: {message}") # Optional extra console print

# --- REVISED log_error ---
async def log_error(
    guild: Optional[discord.Guild], 
    message: str, 
    error: Optional[Exception] = None, 
    interaction: Optional[discord.Interaction] = None, 
    embed: Optional[discord.Embed] = None, 
    ping_owner: bool = False,
    message_context: Optional[discord.Message] = None # <<< ADD THIS PARAMETER
):
    is_target = guild and guild.id == CATERCORD_GUILD_ID
    log_prefix = f"[{guild.name if guild else 'No Guild'}] ERROR:"
    discord_ping_content: Optional[str] = None

    if not embed:
        title_prefix = f"🚨 Bot {'Critical ' if ping_owner else ''}Error" if is_target else "⚠️ Bot Error / Warning"
        embed = discord.Embed(title=title_prefix, description=message, color=discord.Color.red())
        embed.timestamp = discord.utils.utcnow()
        
        context_info_parts = []
        if interaction:
            cmd_name = interaction.command.name if interaction.command else 'N/A'
            cmd_link = f"`/{cmd_name}`" if cmd_name != 'N/A' else 'N/A'
            chan_mention = interaction.channel.mention if isinstance(interaction.channel, discord.TextChannel) else f"Ch:{interaction.channel_id}" if interaction.channel_id else "N/A"
            user_mention = f"{interaction.user.mention} (`{interaction.user.id}`)" if interaction.user else "N/A"
            context_info_parts.append(f"**Interaction:** Cmd: {cmd_link} in {chan_mention}\nUser: {user_mention}")
        
        # --- Use message_context here ---
        if message_context:
            channel_mention_msg = message_context.channel.mention if isinstance(message_context.channel, discord.TextChannel) else f"Ch:{message_context.channel.id}"
            user_mention_msg = f"{message_context.author.mention} (`{message_context.author.id}`)"
            msg_link = f"[Jump to Message]({message_context.jump_url})"
            content_preview = discord.utils.escape_markdown(message_context.content[:100] + "..." if len(message_context.content) > 100 else message_context.content)
            context_info_parts.append(
                f"**Message Context:** User: {user_mention_msg} in {channel_mention_msg}\n"
                f"Content: `{content_preview}`\n{msg_link}"
            )
        
        if context_info_parts:
            embed.add_field(name="Context", value="\n\n".join(context_info_parts), inline=False)
        # --- End use message_context ---

        if error:
            etype, emsg = type(error).__name__, str(error)
            tb = "".join(traceback.format_exception(type(error), error, error.__traceback__, limit=6))
            tb_short = (tb[:900] + "\n... (Truncated)") if len(tb) > 900 else tb
            details = f"**Type:** `{etype}`\n" + (f"**Msg:** `{emsg}`\n" if emsg else "") + f"**Traceback:**\n```py\n{tb_short}\n```"
            if len(details) > 1024: details = details[:1000] + "...```"
            embed.add_field(name="Error Details", value=details, inline=False)
            full_tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            print(f"---\n{log_prefix} Details:\nGuild: {guild.id if guild else 'N/A'}\nCtx: {message}\nErr: {etype}: {emsg}\n{full_tb}---")
        else:
            print(f"---\n{log_prefix} Context:\nGuild: {guild.id if guild else 'N/A'}\nMsg: {message}\n---")

    if is_target and guild: 
        if ping_owner:
            discord_ping_content = f"<@{OWNER_USER_ID}>"
            print(f"{log_prefix} (Owner Ping Queued for Discord)")
        await log_to_channel(EXTRAORDINARY_LOGS_CHANNEL_ID, guild, embed=embed, ping_mention=discord_ping_content)
    else:
        print(f"[Skipping Discord log - Non-Target Guild or No Guild] ERROR: {message}")

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
        desc_lines = []
        idx = start + 1

        # Define a shared IGN display width
        IGN_DISPLAY_WIDTH = 18 # Consistent with static list
        IDX_WIDTH = 3 # Consistent with static list

        if not page_data:
            # Keep code block for "No members" for all views to maintain similar look for empty state
            desc_lines = ["```\nNo members found matching criteria.\n```"]
        elif self.view_mode == VIEW_MODE_DISCORD:
            # Format: #. `IGN` DiscordMention (Mention is OUTSIDE code block)
            # No header, no overall code block for this view mode's content lines
            for item_dict in page_data:
                ign = item_dict.get('ign', 'Unknown IGN')
                index_str = f"{str(idx)+'.':<{IDX_WIDTH}} "

                member_obj = item_dict.get('member') # discord.Member object or None
                user_id_for_mention: Optional[str] = None
                display_name_for_fallback: Optional[str] = None

                if member_obj:
                    user_id_for_mention = str(member_obj.id)
                elif item_dict.get('discord_id'):
                    user_id_for_mention = str(item_dict['discord_id'])
                    display_name_for_fallback = item_dict.get('discord_name') # Stored name if user not in server

                # Construct mention or fallback text
                if user_id_for_mention:
                    mention_display = f"<@!{user_id_for_mention}>"
                elif display_name_for_fallback: # User ID was linked, but member object not found
                    mention_display = f"`{discord.utils.escape_markdown(display_name_for_fallback)} (Not in server)`"
                else: # No Discord ID linked at all (e.g., hconly entry)
                    mention_display = "`[No Discord Link]`"

                # Truncate IGN
                ign_display = ign
                if len(ign_display) > IGN_DISPLAY_WIDTH:
                     ign_display = ign_display[:IGN_DISPLAY_WIDTH-1] + "…"

                line = f"{index_str}`{ign_display:<{IGN_DISPLAY_WIDTH}}` {mention_display}"
                desc_lines.append(line)
                idx += 1

        # All activity views use the same layout now (within a code block)
        elif self.view_mode in [VIEW_MODE_ACTIVITY_ALL, VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
             # Format: ``` #. IGN Activity ``` (Uses fixed-width code block)
             # Re-use widths from static list for consistency if desired, or keep HCPagesView specific
             # Static list uses: IGN_WIDTH = 16, ACT_WIDTH = 18 (ACTIVITY_COLUMN_WIDTH)
             # HCPagesView currently uses: IGN_WIDTH = 20, ACT_WIDTH = ACTIVITY_COLUMN_WIDTH
             # Let's align them for better consistency if possible. Static list's total width is tighter.
             # Sticking to HCPagesView's current widths for activity for now unless specified.
             IGN_WIDTH_ACTIVITY = 20 # Keep as is for HCPagesView
             ACT_WIDTH = ACTIVITY_COLUMN_WIDTH
             TOTAL_WIDTH = IDX_WIDTH + 1 + IGN_WIDTH_ACTIVITY + ACT_WIDTH # +1 for space after index
             header = (f"{'#':<{IDX_WIDTH}} {'IGN':<{IGN_WIDTH_ACTIVITY}}{'Activity':<{ACT_WIDTH}}")
             separator = "-" * (TOTAL_WIDTH -1) # Adjust separator to match content width

             desc_lines.append("```")
             desc_lines.append(header)
             desc_lines.append(separator)

             for item_dict in page_data:
                ign = item_dict.get('ign', 'Unknown')
                activity_count = item_dict.get('activity_count', 0)
                last_seen_date = item_dict.get('last_seen') # date object or None
                activity_display = f"{activity_count} ({format_date_dmy(last_seen_date)})"

                index_str_activity = f"{str(idx)+'.':<{IDX_WIDTH}} " # Pad index and add space

                ign_display_activity = ign
                if len(ign_display_activity) > IGN_WIDTH_ACTIVITY: ign_display_activity = ign_display_activity[:IGN_WIDTH_ACTIVITY-1] + "…"
                if len(activity_display) > ACT_WIDTH: activity_display = activity_display[:ACT_WIDTH-1] + "…"

                line = (f"{index_str_activity}{ign_display_activity:<{IGN_WIDTH_ACTIVITY}}{activity_display:<{ACT_WIDTH}}")
                desc_lines.append(line)
                idx += 1
             desc_lines.append("```")
        else: # Fallback
             desc_lines = ["```Error: Invalid View Mode```"]


        title = HC_LIST_EMBED_TITLE if self.is_catercord_context else "HC Database Members (All)"
        embed = discord.Embed(
            title=title,
            description="\n".join(desc_lines), # Join the constructed lines
            color=NERDY_YELLOW
        )

        # Footer Update (Remains the same logic)
        sort_text = "IGN" if self.sort_mode == SORT_MODE_IGN else "Activity"
        # For Discord View, sort button is disabled, so text doesn't matter as much
        # but if it were enabled, sort_mode could be 'discord_name' vs 'ign'
        if self.view_mode == VIEW_MODE_DISCORD:
            # If you implement sorting for Discord view later, this text might change
            sort_text = "IGN" # Default assumption for this view if sort button was active

        view_text_map = {
            VIEW_MODE_DISCORD: "Discord+IGN",
            VIEW_MODE_ACTIVITY_ALL: "Activity (All)",
            VIEW_MODE_ACTIVITY_DAILY: "Activity (Today)",
            VIEW_MODE_ACTIVITY_WEEKLY: "Activity (7d)",
            VIEW_MODE_ACTIVITY_MONTHLY: "Activity (30d)",
        }
        view_text = view_text_map.get(self.view_mode, "Unknown View")
        footer_text = (
            f"Page {self.current_page + 1}/{self.total_pages} | Total: {self.total_members} | "
            f"View: {view_text} | Sort: {sort_text}"
        )
        if self.is_fetching_activity:
             footer_text += " | Fetching data..."
        footer_text += f" | {get_formatted_utc_now()}"
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
    Fetches HC members (is_in_hc=TRUE) from Discord and Supabase, including all-time activity counts.
    Logs warnings for mismatches (Role w/o DB, DB w/o Role/Member or not is_in_hc).
    Returns a list of dicts: [{'member': discord.Member | None, 'discord_id': str | None, 'discord_name': str | None, 'ign': str, 'activity_count': int, 'last_seen': date | None, 'is_in_hc': bool}]
    and the total count.
    Data is sorted by Discord name (if available), then IGN (case-insensitive).
    """
    print(f"Fetch HC Data ({guild.name}, is_in_hc=TRUE): Starting fetch...")
    hc_role = guild.get_role(HC1_ROLE_ID)
    if not hc_role:
        await log_error(guild, f"HC Role {HC1_ROLE_ID} not found during fetch.", ping_owner=True)
        return [], 0

    all_db_entries_raw: List[Dict] = []
    try:
        if not supabase: raise ConnectionError("Supabase client unavailable.")
        print(f"Fetch HC Data ({guild.name}): Fetching all entries from Supabase hc_members table for correlation...")
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members").select("discord_id, ingame_name, discord_name, is_in_hc").execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            all_db_entries_raw = resp.data
            print(f"Fetch HC Data ({guild.name}): Fetched {len(all_db_entries_raw)} total entries from Supabase.")
        else:
            print(f"Fetch HC Data ({guild.name}): No data returned from Supabase hc_members for correlation.")
    except ConnectionError as e:
        await log_error(guild, "Failed to fetch data from Supabase hc_members for correlation: Connection Error.", error=e, ping_owner=True)
        return [], 0
    except APIError as e:
         await log_error(guild, "Failed to fetch data from Supabase hc_members for correlation: API Error.", error=e, ping_owner=True)
         return [], 0
    except Exception as e:
        await log_error(guild, "Failed to fetch data from Supabase hc_members for correlation: Unexpected Error.", error=e, ping_owner=True)
        return [], 0

    # Create lookup maps from the raw DB data, ensuring shared payload objects
    db_payloads_by_discord_id: Dict[str, Dict] = {}
    db_payloads_by_ign_lower: Dict[str, Dict] = {}
    all_igns_for_activity_fetch: Set[str] = set()

    for entry in all_db_entries_raw:
        ign = entry.get("ingame_name")
        if not ign: continue
        
        all_igns_for_activity_fetch.add(ign)
        d_id_str = str(entry["discord_id"]) if entry.get("discord_id") else None
        is_in_hc_status = entry.get("is_in_hc", False)

        # Construct the payload once
        payload = {
            "ign_original": ign, # Keep original case for consistent reference
            "discord_id": d_id_str,
            "discord_name": entry.get("discord_name"),
            "is_in_hc": is_in_hc_status,
            "processed": False # This flag will be set on this shared payload object
        }
        
        if d_id_str:
            db_payloads_by_discord_id[d_id_str] = payload
        
        # If an entry with this IGN (case-insensitive) already exists in ign_map,
        # prefer the one with a discord_id if this one also has one, or if the existing one doesn't.
        # This handles potential duplicate IGNs if one is linked and other isn't (should be rare).
        # For simplicity, last one wins or prioritize linked ones.
        # A robust solution for duplicate IGNs might need more complex logic based on your data integrity rules.
        # For now, if d_id_str is present, it's likely the more "authoritative" entry for that IGN.
        # Or, if no d_id_str, it's an IGN-only entry.
        existing_ign_payload = db_payloads_by_ign_lower.get(ign.lower())
        if not existing_ign_payload or (d_id_str and not existing_ign_payload.get("discord_id")):
            db_payloads_by_ign_lower[ign.lower()] = payload
        elif not d_id_str and existing_ign_payload.get("discord_id"):
            pass # Keep the existing one that has a discord_id
        else: # Both have/don't have d_id, last one wins (or add more specific tie-breaking)
            db_payloads_by_ign_lower[ign.lower()] = payload


    print(f"Fetch HC Data ({guild.name}): Processed into {len(db_payloads_by_discord_id)} Discord ID payloads, {len(db_payloads_by_ign_lower)} IGN payloads.")

    activity_counts: Dict[str, Dict[str, Any]] = {}
    if all_igns_for_activity_fetch:
        print(f"Fetch HC Data ({guild.name}): Fetching all-time activity for {len(all_igns_for_activity_fetch)} IGNs...")
        activity_counts = await fetch_activity_data(guild, list(all_igns_for_activity_fetch))
        print(f"Fetch HC Data ({guild.name}): Fetched activity data for {len(activity_counts)} IGNs.")

    discord_hc_members: List[discord.Member] = []
    try:
        if not guild.chunked and guild.member_count is not None and guild.member_count > 1000:
             try: print(f"Fetch HC Data ({guild.name}): Chunking guild..."); await guild.chunk(cache=True)
             except Exception as chunk_e: print(f"WARN: Chunking failed: {chunk_e}")
        discord_hc_members = [m for m in guild.members if hc_role in m.roles and not m.bot]
        print(f"Fetch HC Data ({guild.name}): Found {len(discord_hc_members)} Discord members with HC role.")
    except Exception as e:
        await log_error(guild, "Guild chunking/member fetch failed during data fetch. List might be incomplete.", error=e)

    final_data: List[Dict[str, Any]] = []

    # Process Discord members WITH HC role
    for member in discord_hc_members:
        member_id_str = str(member.id)
        # Use the payload from db_payloads_by_discord_id
        db_payload = db_payloads_by_discord_id.get(member_id_str)
        current_discord_name = f"{member.name}#{member.discriminator}" if member.discriminator != '0' else member.name

        if db_payload:
            db_payload["processed"] = True # Mark this shared payload as processed
            if db_payload["is_in_hc"]:
                ign = db_payload["ign_original"]
                activity = activity_counts.get(ign.lower(), {'count': 0, 'last_seen': None})
                final_data.append({
                    "member": member, "discord_id": member_id_str, "discord_name": current_discord_name,
                    "ign": ign, "activity_count": activity['count'], "last_seen": activity['last_seen'],
                    "is_in_hc": True
                })
            else: # Has HC role, but DB says is_in_hc=FALSE
                await log_info(guild, f"Fetch HC Data Warning: Member {member.mention} (`{member_id_str}`) has HC role, but DB entry (IGN: `{db_payload['ign_original']}`) is_in_hc=FALSE.")
        else: # Has HC role, but no DB entry AT ALL
            await log_info(guild, f"Fetch HC Data Warning: Member {member.mention} (`{member_id_str}`) has HC role but no matching DB entry found.")

    # Process remaining DB entries that are is_in_hc=TRUE and were NOT processed above
    # (These are IGN-only entries, or users who have DB record with is_in_hc=TRUE but no HC role on Discord)
    for ign_l, db_payload in db_payloads_by_ign_lower.items():
        if db_payload["processed"] or not db_payload["is_in_hc"]:
            continue

        # This payload was not processed via a Discord ID match above, or it's an IGN-only entry.
        # And its is_in_hc flag is TRUE.
        
        ign = db_payload["ign_original"]
        activity = activity_counts.get(ign_l, {'count': 0, 'last_seen': None})
        d_id_str = db_payload.get("discord_id") # This is already a string or None from payload creation
        stored_discord_name = db_payload.get("discord_name")

        if d_id_str: # DB entry has a Discord ID, is_in_hc=TRUE, but user wasn't in discord_hc_members
            member_in_guild = guild.get_member(int(d_id_str))
            if member_in_guild:
                 # This is the case: DB says user is IN HC, member IS in guild, but DOES NOT have the role.
                 await log_info(guild, f"Fetch HC Data Info: DB entry (IGN: `{ign}`, is_in_hc=TRUE) for user {member_in_guild.mention} (`{d_id_str}`), but they do not have the HC role currently.")
            else: # DB says user is IN HC, but member NOT in guild.
                 name_to_log = stored_discord_name or f"ID {d_id_str}"
                 await log_info(guild, f"Fetch HC Data Info: DB entry (IGN: `{ign}`, is_in_hc=TRUE) for user `{name_to_log}` (`{d_id_str}`), but they are not currently in this server.")
            # Such entries (is_in_hc=TRUE in DB but no Discord role match) are NOT added to final_data for the list
        else: # IGN-only entry, is_in_hc=TRUE. Add to the list.
            final_data.append({
                "member": None, "discord_id": None, "discord_name": stored_discord_name,
                "ign": ign, "activity_count": activity['count'], "last_seen": activity['last_seen'],
                "is_in_hc": True
            })
        
        db_payload["processed"] = True # Mark as handled in this pass

    final_data.sort(key=lambda item: (
        item['member'].name.lower() if item.get('member') else (item.get('discord_name', 'zzz') or 'zzz').lower(),
        item['member'].discriminator if item.get('member') else 'zzz',
        item['ign'].lower()
    ))

    total_members = len(final_data)
    print(f"Fetch HC Data ({guild.name}, is_in_hc=TRUE): Finished. Total members for list: {total_members}.")
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

# --- Ensure task is stopped on cleanup (optional but good practice) ---
@bot.event
async def on_close():
     print("Closing bot connection. Stopping tasks...")
     if check_static_view_timeout.is_running():
          check_static_view_timeout.cancel()
          print(" Static view timeout checker task stopped.")

# --- REVISED update_static_list_message Function ---

async def update_static_list_message(guild: discord.Guild):
    """ Creates or updates the SINGLE interactive HC list message, cleaning up old ones."""
    # --- ADDED: Check for disabling static list in TESTING instance ---
    if DISABLE_STATIC_LIST_FOR_TESTING_INSTANCE:
        await log_info(guild, f"Static list update skipped: Bot instance type is '{BOT_INSTANCE_TYPE}' and updates are disabled for testing instances.")
        print(f"[Static Update] Skipped in {guild.name} due to BOT_INSTANCE_TYPE='{BOT_INSTANCE_TYPE}'.")
        return
    # --- END ADDED CHECK ---

    list_channel_id = HC_MEMBER_LIST_CHANNEL_ID
    chan = guild.get_channel(list_channel_id)

    # // --- UNCHANGED SECTION (update_static_list_message B - Initial Checks, Data Fetching) --- //
    # --- Initial Checks (Permissions, Bot Ready) ---
    if not isinstance(chan, discord.TextChannel):
        await log_error(guild, f"Static list update failed: Channel {list_channel_id} invalid.")
        return
    if not bot or not bot.user: # Added check for bot.user
        await log_error(guild, "Static list update failed: Bot not ready or bot.user not available.")
        return
    bot_perms = chan.permissions_for(guild.me)
    if not bot_perms.send_messages or not bot_perms.embed_links or not bot_perms.read_message_history or not bot_perms.manage_messages: # Added manage_messages for cleanup
        await log_error(guild, f"Static list update failed: Bot missing Send/Embed/History/ManageMessages permissions in {chan.mention}.")
        return

    await log_info(guild, f"Updating interactive static list in {chan.mention} and refreshing IGN cache...")

    # --- Fetch Fresh Base Data and Initial Display Data (Unchanged logic) ---
    member_data, total_count = [], 0
    try:
        member_data, total_count = await fetch_hc_member_data(guild)
    except Exception as e_fetch_base:
        await log_error(guild, "Static list update failed: Error fetching base member data.", error=e_fetch_base)
        return

    try:
        await log_info(guild, "Refreshing in-game name cache as part of static list update...")
        await load_ign_cache(guild) # Pass guild for logging context
        await log_info(guild, f"In-game name cache refreshed. Current size: {len(ingame_name_cache)}.")
    except Exception as e_ign_cache:
        # load_ign_cache logs its own critical errors, but we can log a general failure here too.
        await log_error(guild, "Static list update proceeding, but IGN cache refresh failed during the process.", error=e_ign_cache)

    initial_display_data = list(member_data) # Default to base data
    try:
        today_utc = datetime.datetime.now(pytz.utc).date()
        end_date_monthly = today_utc
        start_date_monthly = today_utc - datetime.timedelta(days=29)
        all_igns = [item['ign'] for item in member_data if item.get('ign')]
        if all_igns:
            monthly_activity_data = await fetch_activity_data(guild, all_igns, start_date_monthly, end_date_monthly)
            temp_data = []
            for item in member_data:
                ign_lower = item.get('ign', '').lower()
                activity_info = monthly_activity_data.get(ign_lower, {'count': 0, 'last_seen': None})
                updated_item = item.copy(); updated_item['activity_count'] = activity_info['count']; updated_item['last_seen'] = activity_info['last_seen']
                temp_data.append(updated_item)
            initial_display_data = temp_data
    except Exception as fetch_err:
         await log_error(guild, "[Static Update] Failed to fetch initial monthly activity", error=fetch_err)
    # --- End Data Fetching ---
    # // --- END UNCHANGED SECTION (update_static_list_message B - Initial Checks, Data Fetching) --- //

    # --- Message and View Management ---
    active_view_data = active_static_list_views.get(list_channel_id)
    tracked_message_obj: Optional[discord.Message] = None
    tracked_view_instance: Optional[StaticHCPagesView] = None

    if active_view_data:
        msg_id = active_view_data.get('message_id')
        view_instance = active_view_data.get('view')
        if msg_id and isinstance(view_instance, StaticHCPagesView) and not view_instance.is_finished():
            try:
                fetched_msg = await chan.fetch_message(msg_id)
                if fetched_msg.components: # Check if message still has view components
                    tracked_message_obj = fetched_msg
                    tracked_view_instance = view_instance
                    if not tracked_view_instance.message: # Link if missing
                        tracked_view_instance.message = fetched_msg
                    print(f"[Static Update] Valid tracked message {msg_id} and view instance found.")
                else:
                    print(f"[Static Update] Tracked message {msg_id} found but has no components. Invalidating.")
                    if not view_instance.is_finished(): view_instance.stop() # Stop the orphaned view
            except discord.NotFound:
                print(f"[Static Update] Tracked message {msg_id} not found. Invalidating.")
                if not view_instance.is_finished(): view_instance.stop()
            except Exception as e_fetch_tracked:
                print(f"[Static Update] Error validating tracked message {msg_id}: {e_fetch_tracked}. Invalidating.")
                if not view_instance.is_finished(): view_instance.stop()
        if not tracked_message_obj: # If validation failed
            if list_channel_id in active_static_list_views: # Check before deleting
                del active_static_list_views[list_channel_id] # Clear invalid entry

    # Scan history for the most recent list message if no valid tracked one
    message_from_history: Optional[discord.Message] = None
    if not tracked_message_obj:
        print("[Static Update] No valid tracked message. Scanning history for a reusable list...")
        async for historical_msg in chan.history(limit=20): # Check last 20 messages
            if historical_msg.author.id == bot.user.id and \
               historical_msg.embeds and historical_msg.embeds[0].title == HC_LIST_EMBED_TITLE and \
               historical_msg.components:
                message_from_history = historical_msg
                print(f"[Static Update] Found potential list message in history: {message_from_history.id}")
                break # Found the newest one

    # --- Determine Action: Update, Edit-with-New-View, or Send-New ---
    final_updated_message: Optional[discord.Message] = None

    try:
        if tracked_message_obj and tracked_view_instance:
            # Scenario 1: Valid tracked message and view instance exist. Update it.
            print(f"[Static Update] Action: Updating existing tracked view for message {tracked_message_obj.id}")
            await tracked_view_instance.update_data_and_refresh(
                new_original_data=member_data,
                new_initial_display_data=initial_display_data,
                new_total_members=total_count
            )
            final_updated_message = tracked_message_obj
            await log_info(guild, f"Interactive static list updated (reused active view) in {chan.mention}.")

        elif message_from_history:
            # Scenario 2: No valid tracked view, but found a reusable message in history.
            # Edit this message with a brand new view.
            print(f"[Static Update] Action: Reusing message {message_from_history.id} from history with a new view.")
            new_view = StaticHCPagesView(
                original_data=member_data, initial_display_data=initial_display_data,
                total_members=total_count, guild=guild, message=message_from_history # Link message now
            )
            initial_embed = new_view.create_page_embed()
            await message_from_history.edit(embed=initial_embed, view=new_view)
            # Update tracker
            active_static_list_views[list_channel_id] = {'view': new_view, 'message_id': message_from_history.id}
            final_updated_message = message_from_history
            await log_info(guild, f"Interactive static list updated (reused historical message, new view) in {chan.mention}.")

        else:
            # Scenario 3: No message to reuse. Send a new one.
            print("[Static Update] Action: Sending a new list message.")
            new_view = StaticHCPagesView(
                original_data=member_data, initial_display_data=initial_display_data,
                total_members=total_count, guild=guild, message=None # Message linked after send
            )
            initial_embed = new_view.create_page_embed()
            sent_message = await chan.send(embed=initial_embed, view=new_view)
            new_view.message = sent_message # Link the sent message object
            new_view.message_id = sent_message.id
            # Update tracker
            active_static_list_views[list_channel_id] = {'view': new_view, 'message_id': sent_message.id}
            final_updated_message = sent_message
            await log_info(guild, f"Interactive static list created (new message) in {chan.mention}.")

        # --- Cleanup Phase: Delete other old list messages by the bot ---
        if final_updated_message:
            print(f"[Static Update] Starting cleanup phase, protecting message {final_updated_message.id}.")
            cleaned_count = 0
            async for old_msg in chan.history(limit=30): # Check a bit more history for cleanup
                if old_msg.author.id == bot.user.id and \
                   old_msg.id != final_updated_message.id and \
                   old_msg.embeds and old_msg.embeds[0].title == HC_LIST_EMBED_TITLE:
                    try:
                        await old_msg.delete()
                        cleaned_count += 1
                        print(f"[Static Update Cleanup] Deleted old list message {old_msg.id}")
                        # If this deleted message was previously tracked, stop its view (if any)
                        # This is more complex to manage safely without iterating active_static_list_views.
                        # For now, relying on the primary logic to manage the single active view.
                    except discord.Forbidden:
                        await log_error(guild, f"Static list cleanup failed: Bot lacks delete permissions in {chan.mention}.")
                        break # Stop trying if permissions are missing
                    except discord.HTTPException as e_del:
                        await log_error(guild, f"Static list cleanup failed: HTTP error deleting message {old_msg.id}.", error=e_del)
            if cleaned_count > 0:
                await log_info(guild, f"Static list cleanup: Deleted {cleaned_count} old/duplicate list message(s) from {chan.mention}.")
        else:
            print("[Static Update] Cleanup skipped as no final message was established.")

    except discord.Forbidden as e:
        await log_error(guild, f"Static list update failed: Bot lacks permissions in {chan.mention}.", error=e)
    except discord.HTTPException as e:
        await log_error(guild, "Static list update failed: Discord API error.", error=e)
    except Exception as e:
        await log_error(guild, "Static list update failed: Unexpected error during send/edit/update.", error=e)

    # Ensure background task is running
    if not check_static_view_timeout.is_running():
        print("[Static Update] Background task for view timeout wasn't running. Starting it.")
        try: check_static_view_timeout.start()
        except RuntimeError: print("[Static Update] Background task already started (RuntimeError).")

# --- Discord Events ---
@bot.event
async def on_ready():
    print("--- on_ready event started ---")
    global BOT_USER_ID, command_ids, STAFF_CHANNELS

    if bot.user:
        BOT_USER_ID = bot.user.id
        print(f"Logged in as {bot.user} (ID: {BOT_USER_ID})")
        print(f"Discord.py v{discord.__version__}")
        print(f"Bot Instance Type: {BOT_INSTANCE_TYPE}") 
    else:
        print("CRITICAL ERROR: Bot user object not found on ready.")
        return

    activity = discord.Activity(type=discord.ActivityType.watching, name="out for Pings | /nerdhelp")
    await bot.change_presence(status=discord.Status.online, activity=activity)

    print(f"Bot is ready and connected to {len(bot.guilds)} guild(s).")
    log_guild_for_ready_msg = bot.get_guild(CATERCORD_GUILD_ID) or (bot.guilds[0] if bot.guilds else None)
    
    print("--- Loading initial non-AI data ---")
    log_guild_for_data_load = bot.get_guild(CATERCORD_GUILD_ID) # Define this before it's used in cog loading error log
    if not log_guild_for_data_load and bot.guilds: log_guild_for_data_load = bot.guilds[0]


    await load_ign_cache(log_guild_for_data_load)
    print("Loading profile picture choices...")
    await load_profile_picture_choices(log_guild_for_data_load)

    print("Identifying staff channels in target guild...")
    STAFF_CHANNELS.clear() 
    target_guild_for_staff_channels = bot.get_guild(CATERCORD_GUILD_ID)
    if target_guild_for_staff_channels:
        florrist_role = target_guild_for_staff_channels.get_role(FLORRIST_ROLE_ID)
        hc1_role = target_guild_for_staff_channels.get_role(HC1_ROLE_ID)
        everyone_role = target_guild_for_staff_channels.default_role
        if florrist_role and hc1_role: 
            potentially_staff_channels = 0; actually_staff_channels = 0
            for channel in target_guild_for_staff_channels.text_channels:
                everyone_perms = channel.permissions_for(everyone_role)
                if not everyone_perms.view_channel:
                    potentially_staff_channels += 1
                    florrist_ow = channel.overwrites_for(florrist_role); hc1_ow = channel.overwrites_for(hc1_role)
                    florrist_can_view = florrist_ow.view_channel is True; hc1_can_view = hc1_ow.view_channel is True
                    if not florrist_can_view and not hc1_can_view:
                        STAFF_CHANNELS.add(channel.id); actually_staff_channels += 1
            print(f"Staff Channel Identification Complete: Found {actually_staff_channels} staff channel(s) out of {potentially_staff_channels} potentially restricted channels.")
        else:
            missing_role_names = []
            if not florrist_role: missing_role_names.append(f"Florrist Role (ID: {FLORRIST_ROLE_ID})")
            if not hc1_role: missing_role_names.append(f"HC1 Role (ID: {HC1_ROLE_ID})")
            print(f"WARN: Could not find required roles for staff channel ID: {', '.join(missing_role_names)}.")
            if log_guild_for_data_load:
                await log_error(target_guild_for_staff_channels, f"Failed to identify staff channels: Roles not found: {', '.join(missing_role_names)}.", ping_owner=True)
    else: print(f"WARN: Target guild (ID: {CATERCORD_GUILD_ID}) not found. Cannot identify staff channels.")
    
    print("Setting up bot attributes for cogs...")
    bot.supabase_client = supabase 
    bot.log_info_global = log_info; bot.log_error_global = log_error
    bot.run_supabase_sync_global = run_supabase_sync
    bot.OWNER_USER_ID_config = OWNER_USER_ID 
    bot.CATERCORD_GUILD_ID_config = CATERCORD_GUILD_ID
    bot.PRIVATE_SERVER_ID_config = PRIVATE_SERVER_ID
    bot.RANDOM_SERVER_ID_config = RANDOM_SERVER_ID
    bot.STAFF_CHANNELS_config = STAFF_CHANNELS 
    bot.BOT_COMMANDS_ALLOWED_CHANNEL_IDS_config = BOT_COMMANDS_ALLOWED_CHANNEL_IDS
    bot.COMMAND_PREFIX_config = COMMAND_PREFIX
    bot.ALWAYS_ON_AI_CHANNELS_config = ALWAYS_ON_AI_CHANNELS
    bot.UNRESTRICTED_AI_CHANNEL_ID_config = UNRESTRICTED_AI_CHANNEL_ID
    bot.ingame_name_cache_ref_config = ingame_name_cache 
    bot.NERDY_YELLOW_config = NERDY_YELLOW 
    bot.PROFILE_PIC_BASE_PATH_config = PROFILE_PIC_BASE_PATH 
    bot.MOBS_FOLDER_PATH_config = os.path.join(PROFILE_PIC_BASE_PATH, MOBS_FOLDER_NAME)
    print("Bot attributes set.")

    print("Loading cogs...")
    synced_commands = [] # Define before use in ready log message
    try:
        await bot.load_extension('ai_cog') 
        print("AICog load_extension call completed.") # More precise wording
    except commands.ExtensionAlreadyLoaded:
        print("AICog was already loaded (ExtensionAlreadyLoaded).")
    except commands.ExtensionFailed as e_failed: # Catch ExtensionFailed specifically
        print(f"CRITICAL: AICog failed to load (ExtensionFailed): {e_failed.name} - {e_failed.original if e_failed.original else 'No original exception info'}")
        print(traceback.format_exc())
        if log_guild_for_data_load:
            await log_error(log_guild_for_data_load, f"CRITICAL: AICog failed to load (ExtensionFailed: {e_failed.name}). AI features disabled.", error=e_failed.original, ping_owner=True)
    except Exception as e_cog: # Catch other load_extension errors
        print(f"CRITICAL: Failed to load AICog (General Exception): {e_cog}\n{traceback.format_exc()}")
        if log_guild_for_data_load:
            await log_error(log_guild_for_data_load, "CRITICAL: Failed to load AICog (General Exception). AI features disabled.", error=e_cog, ping_owner=True)
    
    # --- ADDED: Explicit Verification of AICog ---
    if bot.get_cog('AICog') is None:
        print("CRITICAL VERIFICATION: AICog is None after load_extension attempt. AI features WILL BE UNAVAILABLE.")
        if log_guild_for_data_load:
             await log_error(log_guild_for_data_load, "CRITICAL POST-LOAD CHECK: AICog FAILED TO REGISTER. AI features WILL BE UNAVAILABLE.", ping_owner=True)
    else:
        print("AICog loading verified successfully (cog instance found via bot.get_cog).")
    # --- END ADDED VERIFICATION ---

    print("Syncing application commands...")
    try:
        synced_commands = await tree.sync()
        print(f"Synced {len(synced_commands)} application commands.")
        command_ids.clear()
        for cmd in synced_commands:
            if hasattr(cmd, 'name') and hasattr(cmd, 'id'):
                command_ids[cmd.name] = cmd.id
                if isinstance(cmd, app_commands.Group):
                    for sub_cmd in cmd.commands:
                        if isinstance(sub_cmd, app_commands.Command):
                             full_name = f"{cmd.name} {sub_cmd.name}"
                             command_ids[full_name] = sub_cmd.id
            else: print(f"  Skipped storing ID during sync for an item (type: {type(cmd)}, name: {getattr(cmd, 'name', 'N/A')})")
        if not command_ids: print("Warning: command_ids dictionary is empty after sync.") # Moved this check inside
    except discord.HTTPException as e: print(f"Command Sync failed (HTTPException): {e.status} - {e.text}")
    except Exception as e: print(f"Command Sync failed (Unexpected Error): {e}\n{traceback.format_exc()}")

    if log_guild_for_ready_msg:
        try:
             instance_info = f" ({BOT_INSTANCE_TYPE} instance)" if BOT_INSTANCE_TYPE != "PRODUCTION" else ""
             await log_info(log_guild_for_ready_msg, f"Bot ready and online{instance_info}. Synced {len(synced_commands)} commands.")
        except Exception as log_e: print(f"Failed to send initial ready log message: {log_e}")

    print("Starting background tasks...")
    if not check_static_view_timeout.is_running():
        try: check_static_view_timeout.start(); print(" Static view timeout checker task started.")
        except RuntimeError: print(" Static view timeout checker task was already running (RuntimeError).")
        except Exception as e_task_start:
            print(f"Failed to start static view timeout task: {e_task_start}")
            if log_guild_for_data_load: await log_error(log_guild_for_data_load, "Failed to start static view timeout task", error=e_task_start)

    async def delayed_update(delay_seconds: int):
        await asyncio.sleep(delay_seconds)
        if DISABLE_STATIC_LIST_FOR_TESTING_INSTANCE:
            print(f"--- Skipped delayed static list update (BOT_INSTANCE_TYPE='{BOT_INSTANCE_TYPE}') ---")
            if bot.get_guild(CATERCORD_GUILD_ID):
                 await log_info(bot.get_guild(CATERCORD_GUILD_ID), f"Delayed static list update skipped: Bot instance type is '{BOT_INSTANCE_TYPE}'.")
            return
        print(f"--- Running delayed static list update after {delay_seconds}s ---")
        guild_for_delayed_update = bot.get_guild(CATERCORD_GUILD_ID)
        if not guild_for_delayed_update:
            print(f"ERROR: Could not find target guild {CATERCORD_GUILD_ID} for delayed static list update."); return
        if not supabase:
            print("ERROR: Supabase client not available for delayed static list update.")
            await log_error(guild_for_delayed_update, "Delayed static list update failed: Supabase client not available."); return
        try: await update_static_list_message(guild_for_delayed_update)
        except Exception as e:
            print(f"ERROR during delayed initial static list update: {e}\n{traceback.format_exc()}")
            await log_error(guild_for_delayed_update, "Error during delayed initial static list update", error=e)
        print(f"--- Delayed static list update finished ---")

    if bot.is_ready() and any(g.id == CATERCORD_GUILD_ID for g in bot.guilds):
        print("Scheduling delayed static list update for target guild (Catercord)...")
        asyncio.create_task(delayed_update(delay_seconds=60)) 
    else: print("Skipping delayed static list update (Bot not fully ready or not in target guild).")

    print("--- on_ready event finished ---")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Ignore updates for bots or if roles haven't changed
    if after.bot or before.roles == after.roles:
        return

    guild = after.guild # Define guild here
    # If HC role isn't configured or found, no need to proceed
    hc_role = guild.get_role(HC1_ROLE_ID) # Define hc_role here
    if not hc_role:
        print(f"on_member_update ({guild.name}): HC Role {HC1_ROLE_ID} not found, cannot check role change.")
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
            # --- ADDED: Check for disabling static list in TESTING instance ---
            if DISABLE_STATIC_LIST_FOR_TESTING_INSTANCE:
                await log_info(guild, f"Static list update skipped after role change for {after.mention}: Bot instance type is '{BOT_INSTANCE_TYPE}'.")
                print(f"[on_member_update] Skipped static list update for {after.name} in {guild.name} due to BOT_INSTANCE_TYPE='{BOT_INSTANCE_TYPE}'.")
            else:
            # --- END ADDED CHECK ---
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
    global command_ids # Ensure command_ids is accessible
    cmd_id = command_ids.get(name)
    if cmd_id:
        return f"</{name}:{cmd_id}>"
    else:
        print(f"Warn: No ID found for cmd '/{name}' in get_cmd_mention.")
        return f"`/{name}`"

# --- Slash Commands ---

# --- Verify Command ---
@tree.command(name="verify", description="Verify a standard user or update your own IGN if already verified.")
@app_commands.describe(
    user="The user to verify (or yourself to update IGN).",
    ingame_name="[Optional] User's Florr IGN to link/update. Required if updating your own IGN."
)
# @app_commands.checks.has_permissions(manage_roles=True) # <-- We'll handle this conditionally
@app_commands.checks.bot_has_permissions(manage_roles=True) # Bot always needs this for role operations
async def verify(interaction: discord.Interaction, user: discord.Member, ingame_name: Optional[str] = None):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=False)
        return

    # Conditional Permission Check
    is_self_target = interaction.user.id == user.id
    role_verified_obj = guild.get_role(FLORRIST_ROLE_ID) # Used for self-check and main logic
    
    if not is_self_target: # If targeting OTHERS, original permission check applies
        if not interaction.permissions.manage_roles:
            await interaction.response.send_message(
                "❌ You need 'Manage Roles' permission to verify other users.", ephemeral=True
            )
            return
    elif is_self_target and (not role_verified_obj or role_verified_obj not in interaction.user.roles):
        # Targeting self, but NOT verified -> staff still needs to verify them
        await interaction.response.send_message(
            f"❌ You cannot use this command to verify yourself initially. Please ask a staff member with 'Manage Roles' permission to verify you.",
            ephemeral=True
        )
        return
    elif is_self_target and role_verified_obj and role_verified_obj in interaction.user.roles and not ingame_name:
        # Targeting self, IS verified, but no IGN provided for update
        await interaction.response.send_message(
            "ℹ️ You are already verified. To update your In-Game Name, please provide it in the `ingame_name` option.",
            ephemeral=True
        )
        return

    # Defer after permission checks
    await interaction.response.defer(thinking=True, ephemeral=False)

    if not await check_supabase_available(interaction):
        await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        return

    role_to_remove = guild.get_role(NEWBEE_ROLE_ID)
    # role_verified_obj is already defined above
    bot_member = guild.me

    # Role existence checks (still important if staff is running it for role changes)
    missing_roles = []
    if NEWBEE_ROLE_ID and not role_to_remove: missing_roles.append(f"Unverified Role (ID: {NEWBEE_ROLE_ID})")
    if FLORRIST_ROLE_ID and not role_verified_obj: missing_roles.append(f"Verified Role (ID: {FLORRIST_ROLE_ID})")
    
    if missing_roles and not (is_self_target and role_verified_obj and role_verified_obj in user.roles):
        # If roles are missing AND it's not a self-IGN update case (where roles don't matter)
        msg = f"❌ Setup Error: Roles not found: {', '.join(missing_roles)}. Please configure the bot."
        await interaction.edit_original_response(content=msg, embed=None, view=None)
        await log_error(guild, f"Verify failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return
    
    # Hierarchy check (only relevant if roles are being changed, i.e., not self-IGN update)
    if not (is_self_target and role_verified_obj and role_verified_obj in user.roles):
        hierarchy_fail = False
        hierarchy_reason = ""
        if role_verified_obj and bot_member.top_role.position <= role_verified_obj.position: # Check role_verified_obj exists
            hierarchy_fail=True
            hierarchy_reason=f"Cannot assign the '{role_verified_obj.name}' role."
        elif role_to_remove and bot_member.top_role.position <= role_to_remove.position:
            hierarchy_fail=True
            hierarchy_reason=f"Cannot remove the '{role_to_remove.name}' role."
        
        if hierarchy_fail:
            msg = f"❌ Hierarchy Error: {hierarchy_reason} My highest role ('{bot_member.top_role.name}') is not high enough."
            await interaction.edit_original_response(content=msg, embed=None, view=None)
            await log_error(guild, f"Verify failed: Bot hierarchy issue. Reason: {hierarchy_reason}", interaction=interaction)
            return

    actions_taken = []
    db_messages = [] 
    reason_prefix = "Self-updated IGN" if is_self_target else "Verified"
    reason = f"{reason_prefix} by {interaction.user} (ID: {interaction.user.id})"
    modified_roles = False
    db_changed_is_in_hc_status = False 
    ign_for_final_nick_update: Optional[str] = None

    try:
        # --- Role Management ---
        # Skip role changes if user is self-targeting AND already verified
        if is_self_target and role_verified_obj and role_verified_obj in user.roles:
            actions_taken.append("ℹ️ You are already verified. Proceeding with IGN update only.")
        else: # Standard role verification logic by staff
            has_verified_role = role_verified_obj and role_verified_obj in user.roles
            has_unverified_role = bool(role_to_remove and role_to_remove in user.roles)

            roles_to_add_list = []
            roles_to_remove_list = []

            if has_unverified_role and role_to_remove:
                 roles_to_remove_list.append(role_to_remove)
            if not has_verified_role and role_verified_obj: # Check role_verified_obj exists
                 roles_to_add_list.append(role_verified_obj)

            if roles_to_add_list or roles_to_remove_list:
                current_roles = user.roles
                final_role_set = [r for r in current_roles if r not in roles_to_remove_list] + roles_to_add_list
                final_role_set = [r for r in final_role_set if r.id != guild.default_role.id] 
                await user.edit(roles=final_role_set, reason=reason)
                modified_roles = True
                if roles_to_remove_list and role_to_remove: actions_taken.append(f"➖ Removed `{role_to_remove.name}`")
                if roles_to_add_list and role_verified_obj: actions_taken.append(f"➕ Added `{role_verified_obj.name}`")
            else:
                actions_taken.append(f"ℹ️ Roles already correct for standard verification.")
            
        # --- IGN Linking/Updating Logic ---
        cleaned_ign: Optional[str] = None
        if ingame_name: # This condition is now also true for self-update case
            cleaned_ign = ingame_name.strip()
            ign_for_final_nick_update = cleaned_ign
            user_id_str = str(user.id)
            user_discord_name_tag = f"{user.name}#{user.discriminator}" if user.discriminator != '0' else user.name

            if not cleaned_ign:
                db_messages.append("⚠️ IGN provided was empty. No IGN update attempted.")
                # If self-targeting and IGN was empty, this is an error for their intent.
                if is_self_target:
                     await interaction.edit_original_response(content="❌ You must provide a valid In-Game Name to update.", embed=None, view=None)
                     return
            else:
                try:
                    conflict_resp = await run_supabase_sync(
                        lambda: supabase.table("hc_members")
                                       .select("discord_id")
                                       .ilike("ingame_name", cleaned_ign) 
                                       .not_.eq("discord_id", user_id_str) 
                                       .not_.is_("discord_id", "null") 
                                       .maybe_single()
                                       .execute()
                    )
                    if conflict_resp and hasattr(conflict_resp, 'data') and conflict_resp.data and conflict_resp.data.get("discord_id"):
                        other_user_id = conflict_resp.data.get("discord_id")
                        db_messages.append(f"⚠️ **IGN Conflict:** `{discord.utils.escape_markdown(cleaned_ign)}` is already linked to another user (<@{other_user_id}>). IGN not updated.")
                        await log_info(guild, f"/verify IGN conflict: User `{interaction.user}` tried to link `{cleaned_ign}` to `{user.name}`, but it's linked to ID {other_user_id}.")
                    else:
                        # For /verify (even self-verify for IGN), is_in_hc should be FALSE unless /hcverify is used.
                        # If they are already in DB with is_in_hc=TRUE, this command should NOT change that unless they are also being HCVerified (which this command doesn't do).
                        # So, we need to fetch current is_in_hc if user exists, and preserve it if True, otherwise set to False.
                        
                        current_db_status = await run_supabase_sync(
                            lambda: supabase.table("hc_members")
                                           .select("is_in_hc")
                                           .eq("discord_id", user_id_str)
                                           .maybe_single()
                                           .execute()
                        )
                        
                        final_is_in_hc_value = False # Default for new /verify entries
                        if current_db_status and hasattr(current_db_status, 'data') and current_db_status.data:
                            if current_db_status.data.get("is_in_hc") is True:
                                final_is_in_hc_value = True # Preserve if they are already marked in HC

                        data_to_upsert = {
                            "discord_id": user_id_str,
                            "discord_name": user_discord_name_tag,
                            "ingame_name": cleaned_ign,
                            "is_in_hc": final_is_in_hc_value 
                        }
                        await run_supabase_sync(
                            lambda: supabase.table("hc_members")
                                           .upsert(data_to_upsert, on_conflict="discord_id")
                                           .execute()
                        )
                        db_messages.append(f"💾 IGN `{discord.utils.escape_markdown(cleaned_ign)}` linked/updated for {user.mention}.")
                        log_msg_hc_status = " (is_in_hc preserved as TRUE)" if final_is_in_hc_value else " (is_in_hc set/kept as FALSE)"
                        await log_info(guild, f"/verify: IGN `{cleaned_ign}` linked/updated for {user.mention} by `{interaction.user}`{log_msg_hc_status}.")
                        
                        # Only set db_changed_is_in_hc_status if the 'final_is_in_hc_value' is different from what it might have been.
                        # This is tricky without knowing the "before" state precisely without another query.
                        # For simplicity, let's assume if we touch the DB record, nickname might need an update if managed.
                        # Or more accurately, if 'final_is_in_hc_value' is now FALSE and it might have been TRUE.
                        if not final_is_in_hc_value and (not current_db_status or not current_db_status.data or current_db_status.data.get("is_in_hc") is not False):
                            db_changed_is_in_hc_status = True

                except APIError as e_db:
                    # ... (same error handling as before for unique constraint and other API errors) ...
                    if "unique constraint" in str(e_db.message).lower() and "hc_members_ingame_name_key" in str(e_db.message).lower():
                        db_messages.append(f"⚠️ **IGN Not Linked:** `{discord.utils.escape_markdown(cleaned_ign)}` already exists (possibly unlinked). Use `/hcverify` or contact staff if this IGN should be linked for HC.")
                        await log_info(guild, f"/verify DB Error: IGN `{cleaned_ign}` unique constraint hit for user {user.mention}. User: `{interaction.user}`. Error: {e_db.message}")
                    else:
                        db_messages.append(f"⚠️ Database error during IGN update: {e_db.message}")
                        await log_error(guild, f"Verify DB Error for IGN `{cleaned_ign}` (user: {user.mention})", error=e_db, interaction=interaction)
                except Exception as e_db_other:
                    db_messages.append(f"⚠️ An unexpected database error occurred during IGN update.")
                    await log_error(guild, f"Verify Unexpected DB Error for IGN `{cleaned_ign}` (user: {user.mention})", error=e_db_other, interaction=interaction)
        
        elif not ingame_name and not is_self_target: 
            # IGN not provided by staff, and not a self-update case
            ign_for_final_nick_update = await get_ign_from_user(guild, user.id)
            try:
                user_db_resp = await run_supabase_sync(
                    lambda: supabase.table("hc_members")
                                   .select("is_in_hc, ingame_name")
                                   .eq("discord_id", str(user.id))
                                   .maybe_single()
                                   .execute()
                )
                if user_db_resp and hasattr(user_db_resp, 'data') and user_db_resp.data:
                    if not ign_for_final_nick_update:
                        ign_for_final_nick_update = user_db_resp.data.get("ingame_name")
                    if user_db_resp.data.get("is_in_hc") is True: # If they were in HC
                        await run_supabase_sync(
                            lambda: supabase.table("hc_members")
                                           .update({"is_in_hc": False}) # Mark them as not in HC via /verify
                                           .eq("discord_id", str(user.id))
                                           .execute()
                        )
                        db_messages.append(f"ℹ️ {user.mention} (already in DB) now correctly marked as standard verified (not in HC guild).")
                        await log_info(guild, f"/verify: User {user.mention} (no IGN param by staff) found in DB with is_in_hc=TRUE, updated to FALSE.")
                        db_changed_is_in_hc_status = True
            except Exception as e_db_check:
                 await log_error(guild, f"Verify DB check/update (no IGN param by staff) error for {user.mention}", error=e_db_check, interaction=interaction)
        
        # Nickname update logic
        if ign_for_final_nick_update and (is_self_target or db_changed_is_in_hc_status):
            # If self-target, always try to update nick with the new/existing IGN.
            # If staff target, only update if is_in_hc status potentially changed that would affect default nick.
            current_satt_for_nick_update = await get_all_time_super_attempt_count(guild, ign_for_final_nick_update)
            await update_custom_nickname_on_attempt(guild, user, ign_for_final_nick_update, current_satt_for_nick_update)

        # --- Construct Final Message ---
        final_response_parts = []
        if actions_taken: final_response_parts.extend(actions_taken)
        if db_messages: final_response_parts.extend(db_messages)
        
        if not final_response_parts: 
            final_response_parts.append("ℹ️ No changes made.") # Generic if nothing happened

        await log_info(guild, f"`{interaction.user}` ran /verify for {user.mention}. Actions: {'; '.join(final_response_parts)}.")
        
        final_embed_desc = "\n".join(final_response_parts)
        title_action = "IGN Update" if is_self_target else "Verification"
        final_embed_title = f"✅ {title_action} Processed: {user.display_name}"
        final_color = discord.Color.green()
        if any("⚠️" in msg for msg in final_response_parts):
            final_embed_title = f"⚠️ {title_action} Processed with Issues: {user.display_name}"
            final_color = discord.Color.orange()
        
        final_embed = create_embed(title=final_embed_title, description=final_embed_desc, color=final_color)
        await interaction.edit_original_response(embed=final_embed, view=None)

        # Public notification only if roles were changed by staff
        if modified_roles and not is_self_target:
            public_notif_desc = f"✅ **{user.display_name}** has been verified!"
            role_actions_for_public = [line for line in actions_taken if "Role" not in line and ("Added" in line or "Removed" in line)]
            if role_actions_for_public:
                public_notif_desc += "\n" + "\n".join(role_actions_for_public)
            public_embed = create_embed(public_notif_desc, discord.Color.green())
            try:
                if isinstance(interaction.channel, discord.TextChannel):
                    if interaction.channel.permissions_for(bot_member).send_messages and \
                       interaction.channel.permissions_for(bot_member).embed_links:
                        await interaction.channel.send(embed=public_embed)
                    else:
                        await log_info(guild, f"Skipped public /verify notification for {user.mention}: Missing Send/Embed perms in {interaction.channel.mention}")
            except Exception as e_public:
                 await log_error(guild,"Failed to send public verify notification", error=e_public, interaction=interaction)

    except discord.Forbidden:
        # ... (same error handling as before) ...
        await log_error(guild, "Verify failed: Bot lacks permissions (Forbidden).", interaction=interaction)
        await interaction.edit_original_response(content="❌ Failed: I don't have the necessary permissions to manage roles for this user.", embed=None, view=None)
    except discord.HTTPException as e:
        # ... (same error handling as before) ...
        await log_error(guild, "Verify failed: Discord API error.", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Failed: A Discord API error occurred. Please try again later.", embed=None, view=None)
    except Exception as e:
        # ... (same error handling as before) ...
        await log_error(guild, "Unexpected error during /verify.", error=e, interaction=interaction, ping_owner=True)
        await interaction.edit_original_response(content="❌ An unexpected error occurred.", embed=None, view=None)


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

    role_to_add = guild.get_role(NEWBEE_ROLE_ID) # Role to ADD is 'Unverified'
    role_to_remove = guild.get_role(FLORRIST_ROLE_ID) # Role to REMOVE is 'Verified'

    # Role existence checks
    missing_roles = []
    if NEWBEE_ROLE_ID and not role_to_add: missing_roles.append(f"Unverified Role (ID: {NEWBEE_ROLE_ID})")
    if FLORRIST_ROLE_ID and not role_to_remove: missing_roles.append(f"Verified Role (ID: {FLORRIST_ROLE_ID})")
    if missing_roles:
        msg = f"❌ Setup Error: Roles not found: {', '.join(missing_roles)}. Please configure the bot."
        await interaction.response.send_message(msg, ephemeral=False)
        await log_error(guild, f"Unverify failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return
    # We definitely need the 'Unverified' role to add it
    if not role_to_add:
         msg = f"❌ Setup Error: Unverified Role (ID: {NEWBEE_ROLE_ID}) not configured correctly."
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


# --- REFINED HC Verify Command (Handles existing IGN-only entries, EX_MEMBER_ROLE_ID removal) ---
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
    role_unverified = guild.get_role(NEWBEE_ROLE_ID)
    role_verified = guild.get_role(FLORRIST_ROLE_ID)
    role_hc = guild.get_role(HC1_ROLE_ID)
    role_maybe_exhc = guild.get_role(EX_MEMBER_ROLE_ID)
    bot_member = guild.me

    missing_roles = []
    critical_roles_found = True
    if FLORRIST_ROLE_ID and not role_verified:
        missing_roles.append(f"Verified (ID: {FLORRIST_ROLE_ID})")
        critical_roles_found = False
    if HC1_ROLE_ID and not role_hc:
        missing_roles.append(f"HC (ID: {HC1_ROLE_ID})")
        critical_roles_found = False
    if NEWBEE_ROLE_ID and not role_unverified: print(f"HCVerify Warning ({guild.name}): Unverified Role (ID: {NEWBEE_ROLE_ID}) not found.")
    if EX_MEMBER_ROLE_ID and not role_maybe_exhc: print(f"HCVerify Warning ({guild.name}): Maybe-ExHC Role (ID: {EX_MEMBER_ROLE_ID}) not found.")

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
            print(f"HCVerify: Checking DB for IGN '{ign_to_process}' before upsert/update.")
            existing_entry_resp = await run_supabase_sync(
                lambda: supabase.table("hc_members")
                               .select("discord_id, ingame_name, is_in_hc") # Select is_in_hc
                               .eq("ingame_name", ign_to_process)
                               .maybe_single()
                               .execute()
            )
            existing_entry = existing_entry_resp.data if existing_entry_resp and hasattr(existing_entry_resp, 'data') else None
            operation_type = "store/update" # Default operation type

            current_user_data = {
                "discord_id": str(user.id),
                "discord_name": f"{user.name}#{user.discriminator}" if user.discriminator != '0' else user.name,
                "ingame_name": ign_to_process,
                "is_in_hc": True # Explicitly setting to True for verification
            }

            if existing_entry:
                existing_discord_id = existing_entry.get("discord_id")
                existing_is_in_hc = existing_entry.get("is_in_hc")

                if existing_discord_id is None:
                    # Case 1: IGN exists, discord_id is NULL. Update this entry to link it and set is_in_hc = TRUE.
                    operation_type = "link_and_activate"
                    print(f"HCVerify: IGN '{ign_to_process}' found unlinked. Linking and activating...")
                    await run_supabase_sync(
                        lambda: supabase.table("hc_members")
                                       .update(current_user_data) # Update all fields including is_in_hc
                                       .eq("ingame_name", ign_to_process)
                                       .is_("discord_id", "null") # Safety condition
                                       .execute()
                    )
                    result_summary.append(f"🔗 IGN Linked & Activated: `{discord.utils.escape_markdown(ign_to_process)}` linked to {user.mention}.")
                    log_summary.append("Supabase update OK (linked existing IGN, set is_in_hc=TRUE)")
                    db_success = True
                elif str(existing_discord_id) == str(user.id):
                    # Case 2: IGN exists and linked to THIS user. Upsert to update IGN case, name, and ensure is_in_hc=TRUE.
                    operation_type = "update_and_activate"
                    print(f"HCVerify: IGN '{ign_to_process}' already linked to this user. Updating and ensuring active...")
                    await run_supabase_sync(
                        lambda: supabase.table("hc_members")
                                       .upsert(current_user_data, on_conflict="discord_id") # Upsert on discord_id
                                       .execute()
                    )
                    status_change_msg = " (marked as in HC)" if not existing_is_in_hc else ""
                    result_summary.append(f"💾 IGN Updated: `{discord.utils.escape_markdown(ign_to_process)}`{status_change_msg}.")
                    log_summary.append(f"Supabase upsert OK (updated existing user link, ensured is_in_hc=TRUE {status_change_msg})")
                    db_success = True
                else:
                    # Case 3: IGN exists and linked to ANOTHER user. Error.
                    errors_occurred=True
                    err_detail=f"IGN Conflict: '{ign_to_process}' is already linked to another Discord account (<@{existing_discord_id}>)."
                    result_summary.append(f"⚠️ DB Error: {err_detail}")
                    log_summary.append(f"DB fail: IGN Unique Conflict for {ign_to_process} (linked to {existing_discord_id})")
                    await log_info(guild, f"HCVerify DB Error: IGN '{ign_to_process}' conflict for user {user.mention}. Already linked to ID {existing_discord_id}.", interaction=interaction)
            else:
                # Case 4: IGN does not exist. Upsert to create new entry with is_in_hc=TRUE.
                operation_type = "create_and_activate"
                print(f"HCVerify: IGN '{ign_to_process}' not found. Creating new active entry...")
                # Attempt to upsert on discord_id first to handle cases where user changes IGN
                # If user has an old IGN linked, this will update it.
                # If user has no entry, it will create one.
                await run_supabase_sync(
                    lambda: supabase.table("hc_members")
                                   .upsert(current_user_data, on_conflict="discord_id")
                                   .execute()
                )
                result_summary.append(f"💾 IGN Stored & Activated: `{discord.utils.escape_markdown(ign_to_process)}`.")
                log_summary.append("Supabase upsert OK (new/updated user link, set is_in_hc=TRUE)")
                db_success = True
        
        except APIError as e:
            errors_occurred=True
            # Check for unique constraint violation specifically on ingame_name if discord_id upsert strategy changes
            # For now, general API error handling is fine.
            if "unique constraint" in str(e.message).lower() and "hc_members_ingame_name_key" in str(e.message).lower() and operation_type == "create_and_activate":
                 # This might happen if user existed with different discord_id but same IGN
                 err_detail=f"IGN Conflict: '{ign_to_process}' might already exist under a different Discord ID."
                 result_summary.append(f"⚠️ DB Error: {err_detail}")
                 log_summary.append(f"DB upsert fail: Potential IGN Unique Conflict on create for {ign_to_process}")
            else:
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
        if db_success: # And manage_nickname_by_bot is true for the user
            # Fetch current SATT count
            current_satt_for_nick_update = await get_all_time_super_attempt_count(guild, ign_to_process)
            # This will apply custom template or default HC format
            await update_custom_nickname_on_attempt(guild, user, ign_to_process, current_satt_for_nick_update)
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

# --- New HCLeave Command (MODIFIED: Sets is_in_hc=FALSE, includes Role Changes) ---
@tree.command(name="hcleave", description="Mark member as not in HC (sets is_in_hc=false) & update roles.") # MODIFIED Description
@app_commands.describe(
    ingame_name="The IGN to mark as not in HC."
)
@app_commands.autocomplete(ingame_name=ign_autocomplete)
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def hcleave(interaction: discord.Interaction, ingame_name: str):
    """Marks a member as not in HC in the database and handles linked user roles."""
    guild = interaction.guild
    if not await check_supabase_available(interaction):
        try:
            if interaction.response.is_done(): await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        except (discord.NotFound, discord.HTTPException): pass
        return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return
    if not supabase: # Should be caught by check_supabase_available
        await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=False)
        await log_error(guild, "hcleave failed: Supabase unavailable.", interaction=interaction)
        return

    await interaction.response.defer(thinking=True, ephemeral=False)

    role_hc = guild.get_role(HC1_ROLE_ID)
    role_maybe_exhc = guild.get_role(EX_MEMBER_ROLE_ID)
    bot_member = guild.me

    if not role_hc:
        msg = f"❌ Setup Error: HC Role (ID: {HC1_ROLE_ID}) not found. Cannot perform role actions."
        await interaction.followup.send(msg, ephemeral=False)
        await log_error(guild, f"hcleave failed: Missing critical HC role {HC1_ROLE_ID}", interaction=interaction)
        return
    if not role_maybe_exhc:
        print(f"hcleave Warning ({guild.name}): Maybe-ExHC Role {EX_MEMBER_ROLE_ID} not found. Will skip adding it.")

    log_summary = []
    result_summary = []
    errors_occurred = False
    db_updated_to_not_in_hc = False
    # ... (role change flags remain the same) ...
    hc_role_removed_flag = False
    exhc_role_added_flag = False
    reason = f"HC Leave processed by {interaction.user} (ID: {interaction.user.id})"
    cleaned_ign = ingame_name.strip()
    target_identifier_log = f"IGN: `{discord.utils.escape_markdown(cleaned_ign)}`" if cleaned_ign else "Invalid Target (Empty IGN)"
    found_discord_id: Optional[str] = None
    member_to_modify: Optional[discord.Member] = None

    if not cleaned_ign:
        await interaction.followup.send("❌ In-game name cannot be empty.", ephemeral=False)
        return

    # --- Step 1: Check Database for IGN, its discord_id, and is_in_hc status ---
    try:
        print(f"hcleave: Checking DB for entry matching IGN '{cleaned_ign}'...")
        fetch_resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("discord_id, ingame_name, is_in_hc") # Fetch discord_id and is_in_hc
                           .eq("ingame_name", cleaned_ign)
                           .maybe_single()
                           .execute()
        )

        db_entry = fetch_resp.data if fetch_resp and hasattr(fetch_resp, 'data') else None

        if not db_entry:
            result_summary.append(f"ℹ️ No database entry found matching {target_identifier_log}.")
            log_summary.append(f"DB check: No match found for {cleaned_ign}")
            await interaction.followup.send(embed=create_embed(title="ℹ️ HC Leave: No Action Needed", description="\n".join(result_summary), color=discord.Color.blue()))
            return
        
        current_is_in_hc = db_entry.get("is_in_hc")
        found_discord_id = db_entry.get("discord_id")
        
        if current_is_in_hc is False: # Explicitly check for False
            result_summary.append(f"ℹ️ {target_identifier_log} is already marked as not in HC.")
            log_summary.append(f"DB check: {cleaned_ign} already is_in_hc=FALSE.")
            # Optionally, still check roles if a discord_id is linked? For now, exit if already marked.
            await interaction.followup.send(embed=create_embed(title="ℹ️ HC Leave: No DB Change Needed", description="\n".join(result_summary), color=discord.Color.blue()))
            return

        print(f"hcleave: Found DB entry for '{cleaned_ign}'. Linked Discord ID: {found_discord_id or 'None'}, is_in_hc: {current_is_in_hc}.")
        if found_discord_id:
             try:
                  member_to_modify = guild.get_member(int(found_discord_id))
                  if member_to_modify:
                       print(f"hcleave: Found Discord member {member_to_modify} ({found_discord_id}) linked to IGN '{cleaned_ign}'.")
                  else:
                       result_summary.append(f"ℹ️ DB entry indicates user ID `{found_discord_id}` for `{cleaned_ign}`, but user is not in this server. Will only update DB status.")
                       log_summary.append(f"DB fetch OK for {cleaned_ign}, linked user {found_discord_id} not found in guild.")
             except ValueError:
                  result_summary.append(f"⚠️ DB data issue: Invalid Discord ID '{found_discord_id}' found for IGN `{cleaned_ign}`. Will only update DB status based on IGN.")
                  log_summary.append(f"DB fetch OK for {cleaned_ign}, but invalid Discord ID '{found_discord_id}' found.")
                  errors_occurred = True # Log as an error but proceed with DB update on IGN
                  found_discord_id = None # Treat as unlinked if ID is invalid for role changes

    except (APIError, ConnectionError, Exception) as e:
        errors_occurred = True
        result_summary.append(f"⚠️ DB Error checking for {target_identifier_log}: Could not proceed.")
        log_summary.append(f"DB check fail: {type(e).__name__}")
        await log_error(guild, f"hcleave DB check error for {cleaned_ign}", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed(title="❌ HC Leave Failed", description="\n".join(result_summary), color=discord.Color.red()))
        return

    # --- Step 2: Update Database: Set is_in_hc = FALSE ---
    try:
        print(f"hcleave: Attempting to set is_in_hc=FALSE for IGN '{cleaned_ign}'...")
        update_result = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .update({"is_in_hc": False})
                           .eq("ingame_name", cleaned_ign) # Match by IGN
                           .eq("is_in_hc", True) # Ensure we only update if currently true (safety)
                           .execute()
        )
        if update_result and hasattr(update_result, 'data') and update_result.data:
             db_updated_to_not_in_hc = True
             result_summary.append(f"💾 Database: {target_identifier_log} marked as no longer in HC.")
             log_summary.append(f"DB update OK: {cleaned_ign} set to is_in_hc=FALSE")
        else:
             # This might happen if the is_in_hc was already false (should be caught above) or another issue.
             result_summary.append(f"ℹ️ Database: No update made for {target_identifier_log} (possibly already marked, or no match).")
             log_summary.append(f"DB update: No rows affected for {cleaned_ign} (is_in_hc=FALSE).")
             # If this happens unexpectedly, it might be an error.
             # For now, treat as info, but consider if it should be an error.
    except (APIError, ConnectionError, Exception) as e:
        errors_occurred = True
        result_summary.append(f"⚠️ DB Error updating {target_identifier_log} to not in HC: {getattr(e, 'message', type(e).__name__)}")
        log_summary.append(f"DB update fail (is_in_hc=FALSE): {type(e).__name__}")
        await log_error(guild, f"hcleave DB update error for {cleaned_ign}", error=e, interaction=interaction)
        # Continue to attempt role changes if member_to_modify exists, as roles might still need fixing.

    # --- Step 3: Attempt Role Changes (if member found and HC role exists) ---
    if member_to_modify and role_hc: # role_hc existence already checked
        # ... (Keep existing role change logic exactly as is from previous version) ...
        # ... This includes hierarchy checks, adding/removing roles, appending to result_summary and log_summary ...
        can_manage_member = bot_member.top_role.position > member_to_modify.top_role.position
        can_remove_hc = bot_member.top_role.position > role_hc.position
        can_add_exhc = role_maybe_exhc and (bot_member.top_role.position > role_maybe_exhc.position)

        if not can_manage_member:
            errors_occurred = True
            result_summary.append(f"⚠️ Role Skipped: Bot hierarchy too low to manage {member_to_modify.mention}.")
            log_summary.append(f"Role change skipped (Bot hierarchy vs member {member_to_modify.id})")
        elif not (role_hc in member_to_modify.roles):
            result_summary.append(f"ℹ️ Role Info: {member_to_modify.mention} did not have the `{role_hc.name}` role to remove.")
            log_summary.append(f"Role removal skipped ({member_to_modify.id} didn't have HC role)")
            # Still attempt to add ExHC role if applicable
            if role_maybe_exhc and can_add_exhc and role_maybe_exhc not in member_to_modify.roles:
                try:
                    await member_to_modify.add_roles(role_maybe_exhc, reason=reason + " (Ex-HC role addition)")
                    exhc_role_added_flag = True
                    result_summary.append(f"➕ Role Added: `{role_maybe_exhc.name}` to {member_to_modify.mention}.")
                    log_summary.append(f"Ex-HC role added for {member_to_modify.id} as they lacked HC role.")
                except Exception as e_exhc:
                    errors_occurred = True; result_summary.append(f"⚠️ Role Error: Failed to add `{role_maybe_exhc.name}` to {member_to_modify.mention}."); log_summary.append(f"Ex-HC role add fail: {type(e_exhc).__name__}"); await log_error(guild, f"hcleave Ex-HC role add failed for {member_to_modify.id}", error=e_exhc)
        else: # Has HC role and bot can manage member
            roles_to_remove_list = []
            roles_to_add_list = []

            if can_remove_hc:
                roles_to_remove_list.append(role_hc)
            else: # Should not happen if can_manage_member is true and role_hc is below member top_role, but defensive
                errors_occurred = True
                result_summary.append(f"⚠️ Role Skipped: Bot hierarchy too low to remove `{role_hc.name}` from {member_to_modify.mention}.")
                log_summary.append(f"Role removal skipped (Bot hierarchy vs HC role for {member_to_modify.id})")

            if role_maybe_exhc:
                if can_add_exhc:
                    if role_maybe_exhc not in member_to_modify.roles:
                         roles_to_add_list.append(role_maybe_exhc)
                else:
                    result_summary.append(f"ℹ️ Role Info: Bot hierarchy too low to add `{role_maybe_exhc.name}` to {member_to_modify.mention}.")
                    log_summary.append(f"Role add skipped (Bot hierarchy vs Maybe-ExHC role for {member_to_modify.id})")

            if roles_to_remove_list or roles_to_add_list:
                try:
                    # Use user.edit for atomicity if possible (requires fetching current roles and constructing new set)
                    current_roles = list(member_to_modify.roles)
                    final_role_set = [r for r in current_roles if r not in roles_to_remove_list] + roles_to_add_list
                    final_role_set = [r for r in final_role_set if r.id != guild.default_role.id]

                    await member_to_modify.edit(roles=final_role_set, reason=reason)
                    # role_changes_succeeded = True # Not used directly for now
                    if role_hc in roles_to_remove_list:
                         hc_role_removed_flag = True
                         result_summary.append(f"➖ Role Removed: `{role_hc.name}` from {member_to_modify.mention}.")
                    if role_maybe_exhc in roles_to_add_list:
                         exhc_role_added_flag = True
                         result_summary.append(f"➕ Role Added: `{role_maybe_exhc.name}` to {member_to_modify.mention}.")
                    log_summary.append(f"Role update successful for {member_to_modify.id}. Removed HC: {hc_role_removed_flag}, Added ExHC: {exhc_role_added_flag}")
                except discord.Forbidden: errors_occurred = True; result_summary.append(f"⚠️ Role Error: Permissions error updating {member_to_modify.mention}."); log_summary.append(f"Role update fail: Forbidden for {member_to_modify.id}"); await log_error(guild, f"hcleave role update Forbidden for {member_to_modify.id}", interaction=interaction)
                except discord.HTTPException as e: errors_occurred = True; result_summary.append(f"⚠️ Role Error: Discord API Error updating {member_to_modify.mention}."); log_summary.append(f"Role update fail: HTTP {e.status} for {member_to_modify.id}"); await log_error(guild, f"hcleave role update HTTP for {member_to_modify.id}", error=e, interaction=interaction)
                except Exception as e: errors_occurred = True; result_summary.append(f"⚠️ Role Error: Unknown error updating {member_to_modify.mention}."); log_summary.append(f"Role update fail: {type(e).__name__} for {member_to_modify.id}"); await log_error(guild, f"hcleave role update unexpected error for {member_to_modify.id}", error=e, interaction=interaction)

    # --- Final Response & Logging ---
    final_color = discord.Color.green() if not errors_occurred and db_updated_to_not_in_hc else discord.Color.orange()
    final_title = f"{'✅' if not errors_occurred and db_updated_to_not_in_hc else '⚠️'} HC Leave Processed: {target_identifier_log}"
    if errors_occurred: final_title += " (with issues/skips)"
    if not result_summary: result_summary.append("ℹ️ No specific actions were performed or needed (check logs).")

    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    try:
        await interaction.followup.send(embed=final_embed, ephemeral=False)
    except (discord.NotFound, discord.HTTPException) as e:
        await log_error(guild, "hcleave failed final followup send", error=e, interaction=interaction)

    await log_info(guild, f"`{interaction.user}` processed /hcleave for {target_identifier_log}. Summary: {'; '.join(log_summary)}.")

    # Trigger list update if DB status was successfully changed from TRUE to FALSE
    if db_updated_to_not_in_hc:
        print(f"hcleave: Triggering list update for {target_identifier_log} (DB updated is_in_hc=FALSE).")
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
        # Prepare data for insertion, explicitly setting discord_id and discord_name to None, and is_in_hc to TRUE
        data_to_insert = {
            "ingame_name": cleaned_ign,
            "discord_id": None,
            "discord_name": None,
            "is_in_hc": True # Explicitly set to TRUE
        }

        # Attempt to insert the new record.
        # If an IGN already exists (unique constraint on ingame_name), this will fail.
        # We want to ensure that if it exists but is_in_hc=FALSE, we update it.
        # So, we'll try an upsert strategy.
        # The DB default for is_in_hc is TRUE, so insert alone would work for new entries.
        # But to handle re-activating an IGN-only entry, upsert is better.
        
        # Check if IGN already exists
        existing_entry_resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("ingame_name, is_in_hc")
                           .eq("ingame_name", cleaned_ign)
                           .maybe_single()
                           .execute()
        )
        existing_entry = existing_entry_resp.data if existing_entry_resp and hasattr(existing_entry_resp, 'data') else None

        if existing_entry:
            if existing_entry.get("is_in_hc") is True:
                # Already exists and is in HC
                success_msg = f"ℹ️ **{discord.utils.escape_markdown(cleaned_ign)}** (IGN only) is already registered and marked as in HC."
                await interaction.followup.send(success_msg, ephemeral=False)
                await log_info(guild, f"`{interaction.user}` used /hconly for IGN: `{cleaned_ign}` (already exists and active).")
                # No list update needed if no change
                return # Exit command
            else:
                # Exists but is_in_hc is False, so update it
                print(f"HCOnly: IGN '{cleaned_ign}' found with is_in_hc=FALSE. Updating to TRUE.")
                await run_supabase_sync(
                    lambda: supabase.table("hc_members")
                                   .update({"is_in_hc": True, "discord_id": None, "discord_name": None}) # Ensure discord parts are Null
                                   .eq("ingame_name", cleaned_ign)
                                   .execute()
                )
                success_msg = f"✅ Reactivated **{discord.utils.escape_markdown(cleaned_ign)}** (IGN only) in the database."
                log_action = "reactivated IGN (was is_in_hc=FALSE)"
        else:
            # Does not exist, insert new
            print(f"HCOnly: IGN '{cleaned_ign}' not found. Inserting new entry.")
            await run_supabase_sync(
                lambda: supabase.table("hc_members")
                               .insert(data_to_insert)
                               .execute()
            )
            success_msg = f"✅ Successfully registered **{discord.utils.escape_markdown(cleaned_ign)}** (IGN only) in the database."
            log_action = "registered new IGN"

        await interaction.followup.send(success_msg, ephemeral=False)
        await log_info(guild, f"`{interaction.user}` used /hconly to {log_action}: `{cleaned_ign}`.")

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
async def activatemyself(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild: # Should already be caught by tree if guild_only, but for safety
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    # Send deprecation message
    await interaction.response.send_message(DEPRECATION_MESSAGE_ACTIVITY, ephemeral=True)
    
    # Log the attempt
    await log_info(guild, f"`{interaction.user.name}` (`{interaction.user.id}`) used the deprecated /activatemyself command.")

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

# --- Inactive Command (CORRECTED DECORATOR and Date Handling, ADDED PERMISSION CHECK) ---
@tree.command(name="inactive", description="Remove an activity record for an IGN on a specific date.")
@app_commands.describe(
    ingame_name="The In-Game Name (IGN) to mark inactive.",
    date="Date of activity to remove (Select from list)."
)
@app_commands.autocomplete(ingame_name=ign_autocomplete, date=activity_date_autocomplete)
@app_commands.checks.has_permissions(manage_guild=True) # <<<--- ADDED PERMISSION CHECK
async def inactive(interaction: discord.Interaction, ingame_name: str, date: str):
    guild = interaction.guild
    if not await check_supabase_available(interaction): return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    # Check if bot has manage_guild permission (optional but good practice if the check might fail often)
    # bot_member = guild.me
    # if not bot_member.guild_permissions.manage_guild:
    #     await interaction.response.send_message("Bot configuration error: I need 'Manage Server' permission for internal checks.", ephemeral=True)
    #     await log_error(guild, "/inactive command cannot run: Bot missing Manage Server permission.", interaction=interaction)
    #     return

    await interaction.response.defer(thinking=True, ephemeral=False)

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
    # Errors are logged within remove_activity_log if needed

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

    is_target_guild = current_guild_id == CATERCORD_GUILD_ID

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
         if interaction.channel_id not in BOT_COMMANDS_ALLOWED_CHANNEL_IDS and interaction.user.id != OWNER_USER_ID:
             allowed_mentions = [f"<#{ch_id}>" for ch_id in BOT_COMMANDS_ALLOWED_CHANNEL_IDS if guild.get_channel(ch_id)]
             msg = f"❌ In this server, the command only works in: {', '.join(allowed_mentions) or 'configured channels'}"
             await log_info(guild, f"User `{interaction.user}` attempted /hcmembers in disallowed channel {interaction.channel.mention if interaction.channel else interaction.channel_id} within target guild.")
             # Edit the deferred response
             await interaction.edit_original_response(content=msg, embed=None, view=None)
             return
         else:
             # Log successful use in allowed channel/by owner
             log_detail = ""
             if interaction.user.id == OWNER_USER_ID and interaction.channel_id not in BOT_COMMANDS_ALLOWED_CHANNEL_IDS:
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

# Replace the /profile command with this new version

@tree.command(name="profile", description="View Florr.io [HC1] profile, activity stats, and recent activity patterns.")
@app_commands.describe(
    user="[Optional] Select a Discord user to view their profile.",
    ingame_name="[Optional] Or, type an In-Game Name to view its profile."
)
@app_commands.autocomplete(ingame_name=ign_autocomplete)
async def profile(interaction: discord.Interaction, 
                  user: Optional[discord.Member] = None, 
                  ingame_name: Optional[str] = None):
    guild = interaction.guild
    
    await interaction.response.defer(thinking=True, ephemeral=False)

    if not await check_supabase_available(interaction):
        await interaction.edit_original_response(content="❌ Database connection unavailable. Cannot fetch profile data.", embed=None, view=None)
        return

    target_user_for_display: Union[discord.Member, discord.User, None] = None # More precise type
    hc_profile_db_data: Optional[Dict[str, Any]] = None 
    target_discord_id_str: Optional[str] = None
    target_ign_from_db: Optional[str] = None 
    target_is_self_profile = False
    error_message_for_user: Optional[str] = None

    if user: 
        target_user_for_display = user
        target_discord_id_str = str(user.id)
        hc_profile_db_data = await fetch_hc_member_profile_data(guild, target_discord_id_str)
        if hc_profile_db_data:
            target_ign_from_db = hc_profile_db_data.get("ingame_name")
        if user.id == interaction.user.id:
            target_is_self_profile = True
    elif ingame_name: 
        cleaned_ign_param = ingame_name.strip()
        if not cleaned_ign_param:
            error_message_for_user = "❌ Provided In-Game Name was empty."
        else:
            hc_profile_db_data = await fetch_profile_details_by_ign(guild, cleaned_ign_param)
            if hc_profile_db_data:
                target_ign_from_db = hc_profile_db_data["ingame_name"] 
                target_discord_id_str = hc_profile_db_data.get("discord_id")
                if target_discord_id_str and guild:
                    try:
                        # Try to fetch member for avatar/name, fallback to bot user if not found
                        target_user_for_display = await guild.fetch_member(int(target_discord_id_str))
                    except (discord.NotFound, ValueError, AttributeError):
                        target_user_for_display = bot.user # Fallback display
                elif target_discord_id_str: # User ID exists but no guild context (e.g., DM)
                     try: target_user_for_display = await bot.fetch_user(int(target_discord_id_str))
                     except (discord.NotFound, ValueError): target_user_for_display = bot.user
                else: # No Discord ID linked to IGN
                    target_user_for_display = bot.user # Use bot for avatar if no user linked
                
                # Check if the found Discord ID (if any) matches the interactor
                if target_discord_id_str and target_discord_id_str == str(interaction.user.id):
                    target_is_self_profile = True
                    # If it's a self profile via IGN, ensure target_user_for_display is the interactor
                    if isinstance(interaction.user, (discord.Member, discord.User)):
                         target_user_for_display = interaction.user
            else:
                error_message_for_user = f"❌ No profile data found for IGN `{discord.utils.escape_markdown(cleaned_ign_param)}`."
    else: # Neither user nor IGN provided, default to self
        target_is_self_profile = True
        target_user_for_display = interaction.user 
        target_discord_id_str = str(interaction.user.id)
        hc_profile_db_data = await fetch_hc_member_profile_data(guild, target_discord_id_str)
        if hc_profile_db_data:
            target_ign_from_db = hc_profile_db_data.get("ingame_name")

    if error_message_for_user:
        await interaction.edit_original_response(content=error_message_for_user, embed=None, view=None)
        return

    # Permission check for viewing others' profiles
    if not target_is_self_profile:
        invoker_is_staff_or_owner = False
        if guild and isinstance(interaction.user, discord.Member): # Must be in a guild to have perms
            invoker_is_staff_or_owner = await can_manage_guild_or_is_bypass_user(interaction)
        
        if not invoker_is_staff_or_owner:
            await interaction.edit_original_response(content="❌ You can only view your own profile or require staff permissions to view others'.", embed=None, view=None)
            return

    # Prepare display data for the view
    display_name_for_view: str
    avatar_url_for_view: Optional[str] = None
    mention_or_status_for_view: str
    actual_member_object_ref: Optional[discord.Member] = None # For role checks in view
    discord_id_for_sa_management: Optional[str] = target_discord_id_str # Store the target's ID

    if isinstance(target_user_for_display, (discord.Member, discord.User)):
        display_name_for_view = target_user_for_display.display_name
        avatar_url_for_view = target_user_for_display.display_avatar.url if target_user_for_display.display_avatar else target_user_for_display.default_avatar.url
        mention_or_status_for_view = target_user_for_display.mention
        if isinstance(target_user_for_display, discord.Member):
             actual_member_object_ref = target_user_for_display
    elif hc_profile_db_data and hc_profile_db_data.get("ingame_name"): # IGN-only case, or user not in server
        display_name_for_view = hc_profile_db_data.get("ingame_name") 
        if bot.user and bot.user.display_avatar : avatar_url_for_view = bot.user.display_avatar.url 
        db_disc_name = hc_profile_db_data.get("discord_name")
        db_disc_id = hc_profile_db_data.get("discord_id") # This is already stored in target_discord_id_str
        if target_discord_id_str:
            mention_or_status_for_view = f"`{discord.utils.escape_markdown(db_disc_name or f'ID: {target_discord_id_str}')}` (Info from DB / User not in server)"
        else:
            mention_or_status_for_view = "`Not Linked to Discord`"
    else: 
        await interaction.edit_original_response(content="❌ Critical error: Could not determine target for profile display.", embed=None, view=None)
        await log_error(guild, "Profile: Failed to determine target for display", interaction=interaction)
        return

    target_user_display_data_for_view = {
        "name": display_name_for_view,
        "avatar_url": avatar_url_for_view,
        "mention_or_status": mention_or_status_for_view,
        "_member_object_ref": actual_member_object_ref, # For EX_MEMBER_ROLE_ID check
        "_discord_id_for_sa_management": discord_id_for_sa_management # For Satt management buttons
    }

    # --- Fetch Activity and Super Attempt Data ---
    activity_summary_for_view: Optional[Dict[str, Any]] = None
    initial_monthly_dates_for_view: Set[datetime.date] = set()
    super_attempt_stats_data_for_view: Optional[Dict[str, Any]] = None # New
    today_utc_obj, _ = get_utc_date()

    if target_ign_from_db and today_utc_obj:
        ign_lower = target_ign_from_db.lower()
        
        # Activity Summary
        is_active_today = await check_activity_exists(guild, ign_lower, today_utc_obj)
        active_today_disp = "❔ `N/A (DB Error)`"
        if is_active_today is True: active_today_disp = "✅ `Yes`"
        elif is_active_today is False: active_today_disp = "❌ `No`"
        
        all_time_summary = await fetch_activity_data(guild, [ign_lower])
        ign_all_time_data = all_time_summary.get(ign_lower, {'count': 0, 'last_seen': None})
        
        activity_summary_for_view = {
            "active_today_display": active_today_disp,
            "total_days_logged": ign_all_time_data['count'],
            "last_seen_display": f"`{format_date_dmy(ign_all_time_data['last_seen'])}`" if ign_all_time_data['last_seen'] else "`Never Logged`"
        }
        
        # Initial Monthly Dates
        first_day_of_current_month = today_utc_obj.replace(day=1)
        if today_utc_obj.month == 12:
            first_day_of_next_month = first_day_of_current_month.replace(year=today_utc_obj.year + 1, month=1)
        else:
            first_day_of_next_month = first_day_of_current_month.replace(month=today_utc_obj.month + 1)
        last_day_of_current_month = first_day_of_next_month - datetime.timedelta(days=1)
        
        initial_monthly_dates_for_view = await fetch_activity_dates_in_range(
            guild, ign_lower, first_day_of_current_month, last_day_of_current_month
        )

        # Super Attempt Stats (New)
        super_attempt_stats_data_for_view = await get_user_super_attempt_stats(guild, target_ign_from_db)
    
    if not today_utc_obj:
        await log_error(guild, "Profile command: Failed to get today's date object.", interaction=interaction)

    # --- Create and Send View ---
    profile_view = ProfilePagesView(
        interaction=interaction,
        target_user_display_data=target_user_display_data_for_view,
        hc_profile_data=hc_profile_db_data,
        activity_summary_data=activity_summary_for_view,
        initial_monthly_active_dates=initial_monthly_dates_for_view,
        super_attempt_stats_data=super_attempt_stats_data_for_view, # Pass new data
        today_date_obj=today_utc_obj if today_utc_obj else datetime.date.today() 
    )
    
    initial_embed = profile_view._create_main_embed() # Main embed will now include Satt overview
    
    try:
        await interaction.edit_original_response(embed=initial_embed, view=profile_view)
        profile_view.message = await interaction.original_response() # Link message to view
    except discord.HTTPException as e_edit_final:
        if guild: await log_error(guild, "Failed to send initial profile embed with view", error=e_edit_final, interaction=interaction)
        else: print(f"Failed to send initial profile embed (DM/No Guild): {e_edit_final}")
        try:
            await interaction.edit_original_response(content="❌ Error displaying profile. Please try again.", embed=None, view=None)
        except: pass

@tree.command(name="refresh", description="Manually refresh the interactive [HC1] list message AND reload keyword data.")
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return
    if not await check_supabase_available(interaction):
        return
    if guild.id != CATERCORD_GUILD_ID:
        await interaction.response.send_message("List refresh commands can only be used in the target server.", ephemeral=True)
        return
    
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(list_channel, discord.TextChannel):
        await interaction.response.send_message(f"❌ Configuration Error: Static list channel (ID: {HC_MEMBER_LIST_CHANNEL_ID}) not found or invalid.", ephemeral=True)
        await log_error(guild, f"/refresh failed: Static list channel invalid.", interaction=interaction)
        return

    await interaction.response.defer(thinking=True, ephemeral=False)
    feedback_msg = (
        f"⏳ Starting refresh...\n"
        f"- Reloading keyword data from Supabase.\n"
        f"- Reloading profile picture choices from local files.\n" # <--- ADDED THIS LINE
        f"- Updating interactive list in {list_channel.mention}."
    )
    
    try:
        await interaction.followup.send(feedback_msg, ephemeral=False)
    except Exception as e_followup:
        await log_error(guild, "Failed initial /refresh followup send", error=e_followup, interaction=interaction)
        try: await interaction.edit_original_response(content="⏳ Starting refresh...", embed=None, view=None)
        except Exception: pass

    keyword_load_success = False
    profile_pics_load_success = False # <--- ADDED THIS
    list_update_success = False
    error_details = ""
    ai_cog = bot.get_cog('AICog') 

    try:
        # 1. Reload Keyword Data (via AI Cog)
        if ai_cog:
            await log_info(guild, f"Manual keyword data reload initiated by `{interaction.user}` via /refresh.")
            await ai_cog.load_keyword_data(guild) 
            keyword_load_success = True
            print(f"Keyword reload complete (via cog). Cache size in cog: {len(ai_cog.keyword_data_cache)}")
        else:
            await log_info(guild, "AI Cog not found during /refresh. Keyword data not reloaded.") # Changed to log_info
            error_details += " AI module not loaded, keyword data not reloaded."

        # 2. Reload Profile Picture Choices <--- NEW SECTION
        await log_info(guild, f"Manual profile picture choices reload initiated by `{interaction.user}` via /refresh.")
        await load_profile_picture_choices(guild) # Pass guild for logging
        profile_pics_load_success = True
        print(f"Profile picture choices reloaded. Cache size: {len(available_profile_pics_cache)}.")
        # load_profile_picture_choices logs its own errors if any.

        # 3. Update Static List Message
        await log_info(guild, f"Manual interactive static list refresh initiated by `{interaction.user}` via /refresh.")
        await update_static_list_message(guild)
        list_update_success = True
        print(f"Static list update triggered.")

        completion_msg = f"✅ Refresh complete!\n"
        if ai_cog and keyword_load_success:
            completion_msg += f"- Keyword data reloaded ({len(ai_cog.keyword_data_cache)} rules).\n"
        elif not ai_cog:
            completion_msg += f"- Keyword data skipped (AI module not loaded).\n"
        
        if profile_pics_load_success: # <--- ADDED THIS
            completion_msg += f"- Profile picture choices reloaded ({len(available_profile_pics_cache)} available).\n"
        else: # Should not happen if load_profile_picture_choices is robust, but for completeness
            completion_msg += f"- Profile picture choices reload failed or skipped.\n"

        completion_msg += f"- Interactive list update triggered in {list_channel.mention}."
        
        await interaction.edit_original_response(content=completion_msg, embed=None, view=None)
        await log_info(guild, f"/refresh command confirmed complete for user {interaction.user}.")

    except Exception as e:
        action = "processing refresh" # General action
        if not keyword_load_success and ai_cog : action = "keyword loading (via cog)"
        elif not profile_pics_load_success and not list_update_success: action = "profile pic loading"
        elif not list_update_success: action = "list updating"
        
        error_details += f" An error occurred during {action}."
        await log_error(guild, f"Error during /refresh process execution ({action})", error=e, interaction=interaction)
        try:
            await interaction.edit_original_response(content=f"❌ Refresh failed.{error_details}", embed=None, view=None)
        except Exception: pass



# --- Sync Nicknames Command (Optimized DB Query) ---
@tree.command(name="syncnicknames", description="Sync nicknames for users with bot-managed nickname templates.") # MODIFIED DESCRIPTION
@app_commands.checks.has_permissions(manage_nicknames=True) 
@app_commands.checks.bot_has_permissions(manage_nicknames=True) 
async def syncnicknames(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=False)

    if not supabase:
        await interaction.edit_original_response(content="❌ Database connection unavailable.")
        await log_error(guild, "/syncnicknames failed: Supabase unavailable.", interaction=interaction)
        return

    start_time = discord.utils.utcnow()
    await log_info(guild, f"Custom Nickname Sync initiated by `{interaction.user}`.")
    loading_emoji = "🔄" 
    await interaction.edit_original_response(content=f"{loading_emoji} Fetching users with managed nicknames...")

    users_to_update: List[Dict[str, Any]] = []
    try:
        # Fetch users who have manage_nickname_by_bot = TRUE and a non-null template
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("discord_id, ingame_name, custom_nickname_template")
                           .eq("manage_nickname_by_bot", True)
                           .not_.is_("custom_nickname_template", "null")
                           .execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            users_to_update = resp.data
        
        total_users_to_process = len(users_to_update)
        print(f"SyncNickCustom ({guild.name}): Found {total_users_to_process} users with bot-managed nicknames.")

    except Exception as e:
        await log_error(guild, "SyncNickCustom: Database fetch failed for managed users", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Database fetch for managed users failed. Cannot proceed.")
        return

    if total_users_to_process == 0:
        await interaction.edit_original_response(content=f"ℹ️ No users found with bot-managed nickname templates. Nothing to sync.")
        return

    await interaction.edit_original_response(content=f"{loading_emoji} Syncing {total_users_to_process} custom nicknames...")
    
    counts = {'proc': 0, 'upd_ok': 0, 'upd_fail_perm': 0, 'upd_fail_hier': 0, 'upd_fail_other': 0, 'no_member': 0, 'no_ign': 0}
    bot_member = guild.me
    bot_pos = bot_member.top_role.position
    bot_can_manage_nicks_globally = bot_member.guild_permissions.manage_nicknames

    last_prog_update_time = asyncio.get_event_loop().time()
    update_interval = 5.0

    for user_data in users_to_update:
        counts['proc'] += 1
        discord_id_str = user_data.get("discord_id")
        author_ign = user_data.get("ingame_name")
        template = user_data.get("custom_nickname_template")

        if not discord_id_str or not author_ign or not template:
            counts['no_ign'] +=1 # Or some other specific count for bad data
            continue

        member = guild.get_member(int(discord_id_str))
        if not member:
            counts['no_member'] += 1
            continue
        
        if not bot_can_manage_nicks_globally: # Global check, stop if bot loses perm mid-sync
            counts['upd_fail_perm'] += (total_users_to_process - counts['proc'] + 1) # Mark rest as failed
            await log_error(guild, "SyncNickCustom: Bot lost Manage Nicknames permission mid-sync.", interaction=interaction)
            break 
        
        if bot_pos <= member.top_role.position:
            counts['upd_fail_hier'] += 1
            continue
        
        try:
            all_time_count = await get_all_time_super_attempt_count(guild, author_ign)
            new_nickname_unprocessed = template.replace("{satt}", str(all_time_count))
            new_nickname = new_nickname_unprocessed[:32]

            if member.nick == new_nickname:
                # counts['upd_ok'] += 1 # Optionally count "already correct" as success
                continue 

            await member.edit(nick=new_nickname, reason=f"Custom Nickname Sync ({interaction.user.id})")
            counts['upd_ok'] += 1
            await asyncio.sleep(0.2) # Be gentle with API
        except discord.Forbidden:
            counts['upd_fail_perm'] += 1
        except discord.HTTPException as e_http:
            counts['upd_fail_other'] += 1 # Group HTTP with other for this summary
            if e_http.status == 429: print(f"SyncNickCustom ({guild.name}): Rate limit hit!")
        except Exception as e_other_nick:
            counts['upd_fail_other'] += 1
            await log_error(guild, f"SyncNickCustom: Unexpected error updating nick for {member.mention}", error=e_other_nick, interaction=interaction)

        now = asyncio.get_event_loop().time()
        if (now - last_prog_update_time > update_interval) or (counts['proc'] == total_users_to_process):
             if interaction.is_expired():
                  print(f"SyncNickCustom ({guild.name}): Interaction expired, cannot update progress.")
                  last_prog_update_time = now + 999 
                  continue
             try:
                await interaction.edit_original_response(content=f"{loading_emoji} Syncing custom nicknames... ({counts['proc']}/{total_users_to_process})")
                last_prog_update_time = now
             except (discord.NotFound, discord.HTTPException):
                print(f"SyncNickCustom ({guild.name}): Progress update failed. Continuing sync...")
                last_prog_update_time = now + 999


    end_time = discord.utils.utcnow()
    duration = (end_time - start_time).total_seconds()

    summary_embed = discord.Embed(title="✅ Custom Nickname Sync Complete!", color=NERDY_YELLOW)
    
    summary_lines = [
        f"⏱️ **Duration:** {duration:.2f} seconds",
        f"👥 **Users with Managed Nicknames Found:** {total_users_to_process}",
        f"📊 **Users Processed:** {counts['proc']}",
        f"✅ **Nicknames Updated/Correct:** {counts['upd_ok']}",
        f"ℹ️ **Skipped (No Member/IGN):** {counts['no_member'] + counts['no_ign']}",
        f"❌ **Failed Updates:** {counts['upd_fail_perm'] + counts['upd_fail_hier'] + counts['upd_fail_other']}",
        f"   - Permissions Error: {counts['upd_fail_perm']}",
        f"   - Bot Hierarchy Too Low: {counts['upd_fail_hier']}",
        f"   - Other Errors: {counts['upd_fail_other']}"
    ]
    summary_embed.description = "\n".join(summary_lines)
    summary_embed.set_footer(text=f"Completed: {get_formatted_utc_now()}")

    try:
        if not interaction.is_expired():
            await interaction.edit_original_response(content=None, embed=summary_embed)
        else:
            await interaction.followup.send(embed=summary_embed, ephemeral=False)
    except Exception as e_final_send:
        await log_error(guild, "SyncNickCustom: Could not send final summary.", error=e_final_send, embed=summary_embed, interaction=interaction)

    log_embed = discord.Embed(title="Custom Nickname Sync Finished", description="\n".join(summary_lines), color=NERDY_YELLOW)
    log_embed.set_footer(text=f"Initiated by {interaction.user} | Completed: {get_formatted_utc_now()}")
    await log_info(guild, "", embed=log_embed)


# --- Wither Command ---
# --- Wither Command (MODIFIED - Invoker Hierarchy Check Removed) ---
@tree.command(name="wither", description="Temporarily remove roles from a user.")
@app_commands.describe(
    user="User to wither.",
    time="Duration in minutes (0.1 to 10, default 2)."
)
async def wither(interaction: discord.Interaction, user: discord.Member, time: app_commands.Range[float, 0.1, 10.0] = 2.0):
    guild = interaction.guild
    invoker = interaction.user # Member object of the user running the command

    # Pre-checks
    if not guild:
        await interaction.response.send_message("This command cannot be used outside a server.", ephemeral=False)
        return

    bot_member = guild.me # Bot's member object in the guild

    async def fail_check(log_reason: str, user_message: str):
        """Helper to send failure message and log error."""
        send_method = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        try:
            await send_method(embed=create_embed(user_message, discord.Color.red()), ephemeral=False)
        except (discord.NotFound, discord.InteractionResponded, discord.HTTPException) as e:
            print(f"Wither Check Fail Send Error: {type(e).__name__} - {e}")
        except Exception as e:
            print(f"Wither Check Fail Send Error (Unknown): {e}")
        await log_error(guild, f"Wither check fail ({invoker.name} -> {user.name}): {log_reason}", interaction=interaction)

    # 1. Permission Check (Invoker)
    invoker_can_wither = False
    permission_denied_message = "❌ You do not have permission to use this command." # Default

    if guild.id == CATERCORD_GUILD_ID:
        if invoker.id in ALLOWED_WITHERER_IDS:
            invoker_can_wither = True
    elif guild.id == RANDOM_SERVER_ID:
        if invoker.id in ALLOWED_WITHERER_IDS or (isinstance(invoker, discord.Member) and invoker.guild_permissions.administrator):
            invoker_can_wither = True
        else:
            permission_denied_message = "❌ In this server, only whitelisted users or Administrators can use this command."
    else: # Any other server
        if isinstance(invoker, discord.Member) and invoker.guild_permissions.administrator:
            invoker_can_wither = True
        else:
            permission_denied_message = "❌ In this server, only Administrators can use this command."

    if not invoker_can_wither:
        if not interaction.response.is_done():
            try: await interaction.response.defer(ephemeral=False)
            except discord.InteractionResponded: pass
        await fail_check("Invoker permission denied.", permission_denied_message)
        return

    # 2. Defer Publicly (thinking state visible)
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(thinking=True, ephemeral=False)
        except discord.InteractionResponded:
            print(f"Warning: Interaction {interaction.id} was already responded to before public defer in wither.")
            pass

    # 3. Target Checks (Self, Protected, Bot, Bot Hierarchy)
    if user.id == invoker.id: await fail_check("Target self.", "🤨 You cannot wither yourself."); return
    if user.id == OWNER_USER_ID and invoker.id != OWNER_USER_ID: await fail_check("Target protected.", f"😨 Cannot wither the protected user (<@{OWNER_USER_ID}>)."); return
    if user.id == BOT_USER_ID: await fail_check("Target bot.", "😭 You cannot wither me!"); return
    if user.bot: await fail_check("Target other bot.", "🤖 You cannot wither other bots."); return
    if guild.owner_id and user.id == guild.owner_id and invoker.id != guild.owner_id: await fail_check("Target guild owner.", f"👑 You cannot wither the server owner (<@{guild.owner_id}>)."); return
    # Bot hierarchy check (Bot must be able to manage target's roles)
    if bot_member.top_role.position <= user.top_role.position: await fail_check("Bot hierarchy low.", f"❌ My highest role ('{bot_member.top_role.name}') is not high enough to manage {user.mention}'s roles."); return
    # --- Invoker hierarchy check REMOVED ---
    # if invoker.id != guild.owner_id and isinstance(invoker, discord.Member) and invoker.top_role.position <= user.top_role.position: await fail_check("Invoker hierarchy low.", f"❌ Your highest role ('{invoker.top_role.name}') is not high enough to wither {user.mention}."); return
    
    # Bot permissions check
    if not bot_member.guild_permissions.manage_roles: await fail_check("Bot missing manage_roles perm.", "❌ I lack the `Manage Roles` permission needed for this command."); return


    # 4. Get Original Roles (excluding @everyone)
    original_roles = [r for r in user.roles if r.id != guild.default_role.id]
    if not original_roles and guild.id != RANDOM_SERVER_ID: # If no roles AND not random server (where we might just add the special role)
        await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} has no roles (other than @everyone) to remove.", discord.Color.orange()), ephemeral=False)
        return

    # --- Start of Main Wither Logic (Outer Try Block) ---
    try:
        wither_seconds = min(max(1, int(time * 60)), int(MAX_WITHER_SECONDS or 600))
        actual_minutes = wither_seconds / 60.0
        reason_wither = f"Withered by {invoker.name} ({invoker.id}) for {actual_minutes:.1f}m."

        # --- Role Removal ---
        roles_to_remove_actually = [r for r in original_roles if bot_member.top_role.position > r.position]
        skipped_roles_remove = [r for r in original_roles if r not in roles_to_remove_actually]

        if not roles_to_remove_actually and guild.id != RANDOM_SERVER_ID: # If no manageable roles AND not random server
             await interaction.followup.send(embed=create_embed(f"ℹ️ Cannot wither {user.display_name}: None of their roles are below my highest role.", color=discord.Color.orange()), ephemeral=False)
             await log_info(guild, f"Wither attempt on {user.name} by {invoker.name} failed: No manageable roles.")
             return

        everyone_role = guild.default_role
        roles_to_set_during_wither = [everyone_role]
        special_wither_role_added_msg_part = ""

        if guild.id == RANDOM_SERVER_ID:
            withered_role_random_obj = guild.get_role(WITHERED_ROLE_ID_RANDOM_SERVER)
            if withered_role_random_obj:
                if bot_member.top_role.position > withered_role_random_obj.position:
                    roles_to_set_during_wither.append(withered_role_random_obj)
                    special_wither_role_added_msg_part = f"\n**Special Role Added:** `{withered_role_random_obj.name}`"
                else:
                    special_wither_role_added_msg_part = f"\n*(Note: Could not add special withered role '{withered_role_random_obj.name}' due to hierarchy.)*"
            else:
                special_wither_role_added_msg_part = f"\n*(Note: Special withered role (ID: {WITHERED_ROLE_ID_RANDOM_SERVER}) for this server not found/configured.)*"
                await log_error(guild, f"Wither: Special role {WITHERED_ROLE_ID_RANDOM_SERVER} not found in guild {guild.id} ({RANDOM_SERVER_ID})")

        await user.edit(roles=roles_to_set_during_wither, reason=reason_wither)

        # --- Send Confirmation ---
        roles_removed_names = (', '.join(f"`{r.name}`" for r in roles_to_remove_actually) or ('None' if not roles_to_remove_actually and guild.id != RANDOM_SERVER_ID else 'All existing manageable roles'))
        if len(roles_removed_names) > 850: roles_removed_names = roles_removed_names[:847] + "..."

        wither_desc = f"{user.mention} has been withered by {invoker.mention} for **{actual_minutes:.1f} minutes**!\n\n**Roles Removed:** {roles_removed_names}"
        wither_desc += special_wither_role_added_msg_part # Add info about the special role if applicable
        if skipped_roles_remove:
            skipped_names = (', '.join(f"`{r.name}`" for r in skipped_roles_remove))
            if len(skipped_names) > 100: skipped_names = skipped_names[:97] + "..."
            wither_desc += f"\n*(Skipped removing {len(skipped_roles_remove)} role(s) due to hierarchy: {skipped_names})*"

        await interaction.followup.send(embed=create_embed(title="🌪️ Wither Cast! 🌪️", description=wither_desc, color=discord.Color.dark_purple()), ephemeral=False)

        log_msg = f"`{user.name}` ({user.id}) withered by `{invoker.name}` ({invoker.id}) for {actual_minutes:.1f}m. Roles removed: {', '.join(r.name for r in roles_to_remove_actually) or 'N/A'}."
        if guild.id == RANDOM_SERVER_ID and any(role.id == WITHERED_ROLE_ID_RANDOM_SERVER for role in roles_to_set_during_wither):
            log_msg += f" Special role {WITHERED_ROLE_ID_RANDOM_SERVER} added."
        if skipped_roles_remove: log_msg += f" Skipped (hierarchy): {', '.join(r.name for r in skipped_roles_remove)}."
        await log_info(guild, log_msg)

        # --- Wait Period ---
        await asyncio.sleep(wither_seconds)

        # --- Role Restore (Inner Try Block) ---
        try:
            member_after = await guild.fetch_member(user.id)
            bot_member_after = await guild.fetch_member(bot.user.id) if bot.user else await guild.fetch_me()
            reason_restore = f"Wither expired after {actual_minutes:.1f}m. Restoring roles."

            if not bot_member_after.guild_permissions.manage_roles:
                await log_error(guild, f"Wither restore fail for {member_after.mention}: Bot lost `Manage Roles` permission.")
                if interaction.channel: await interaction.channel.send(f"⚠️ Failed to restore roles for {member_after.mention}: Bot permissions missing.")
                return
            if bot_member_after.top_role.position <= member_after.top_role.position:
                await log_error(guild, f"Wither restore fail: Bot hierarchy now too low for {member_after.mention}.")
                if interaction.channel: await interaction.channel.send(f"⚠️ Failed to restore roles for {member_after.mention}: Hierarchy issue.")
                return

            valid_restore_roles = []
            skipped_deleted_names = []
            skipped_hierarchy_names = []
            original_role_ids = {r.id for r in original_roles}
            current_valid_roles = {r.id: r for r in guild.roles}

            for role_id in original_role_ids:
                role_obj = current_valid_roles.get(role_id)
                if not role_obj:
                    original_name = next((r.name for r in original_roles if r.id == role_id), f"ID {role_id}")
                    skipped_deleted_names.append(original_name)
                elif bot_member_after.top_role.position > role_obj.position:
                    valid_restore_roles.append(role_obj)
                else:
                    skipped_hierarchy_names.append(role_obj.name)

            if skipped_deleted_names: await log_info(guild, f"Wither restore notice for {member_after.name}: Roles seem deleted: {', '.join(skipped_deleted_names)}.")
            if skipped_hierarchy_names: await log_info(guild, f"Wither restore notice for {member_after.name}: Roles skipped (hierarchy): {', '.join(skipped_hierarchy_names)}.")

            if not valid_restore_roles and guild.id != RANDOM_SERVER_ID: # If no roles to restore AND not random server (where we only need to remove the special role)
                await log_info(guild, f"Wither restore: No valid roles left to restore for {member_after.name}.")
                if interaction.channel: await interaction.channel.send(f"ℹ️ Wither ended for {member_after.mention}, but no valid roles could be restored (deleted or hierarchy issues).")
                # Still proceed to remove special role if in RANDOM_SERVER_ID
                if guild.id != RANDOM_SERVER_ID: return

            final_roles_to_set = valid_restore_roles + [guild.default_role]
            special_wither_role_removed_msg_part = ""

            if guild.id == RANDOM_SERVER_ID:
                withered_role_random_obj = guild.get_role(WITHERED_ROLE_ID_RANDOM_SERVER)
                if withered_role_random_obj and withered_role_random_obj in member_after.roles:
                    if bot_member_after.top_role.position > withered_role_random_obj.position:
                         special_wither_role_removed_msg_part = f"\n*(Special withered role `{withered_role_random_obj.name}` removed.)*"
                         await log_info(guild, f"Wither Restore: Removing special role {withered_role_random_obj.name} from {member_after.name} in {RANDOM_SERVER_ID}.")
                    else:
                         special_wither_role_removed_msg_part = f"\n*(Could not remove special withered role `{withered_role_random_obj.name}` due to hierarchy.)*"
                         await log_error(guild, f"Wither Restore: Could not remove special role {withered_role_random_obj.name} from {member_after.name} in {RANDOM_SERVER_ID} due to hierarchy.")


            await member_after.edit(roles=final_roles_to_set, reason=reason_restore)

            restored_names = (', '.join(f"`{r.name}`" for r in valid_restore_roles) or 'None')
            restore_msg = f"✨ {member_after.mention}'s roles have been restored!"
            restore_msg += special_wither_role_removed_msg_part # Add info about special role removal
            if skipped_deleted_names or skipped_hierarchy_names:
                restore_msg += "\n*(Some original roles were not restored due to being deleted or hierarchy issues.)*"

            try:
                 await interaction.followup.send(embed=create_embed(restore_msg, color=NERDY_YELLOW), ephemeral=False)
            except (discord.NotFound, discord.HTTPException) as e_followup:
                print(f"Wither restore followup failed ({e_followup}), attempting to send to channel.")
                if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                    try: await interaction.channel.send(embed=create_embed(restore_msg, color=NERDY_YELLOW))
                    except Exception as e_chan_send: await log_error(guild, "Wither failed channel send after followup fail", error=e_chan_send)
                else: await log_info(guild, f"Wither restore OK for {member_after.mention}, but couldn't send followup or channel message.")

            log_restore_details = f"Restored roles for `{member_after.name}` ({member_after.id}). Roles: {', '.join(r.name for r in valid_restore_roles)}"
            if guild.id == RANDOM_SERVER_ID and "removed" in special_wither_role_removed_msg_part.lower():
                log_restore_details += f". Special role {WITHERED_ROLE_ID_RANDOM_SERVER} also handled."
            await log_info(guild, log_restore_details)

        except discord.NotFound:
            await log_info(guild, f"Wither restore skipped: User `{user.name}` ({user.id}) left the server.")
            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                try: await interaction.channel.send(f"ℹ️ Wither ended for {user.display_name}, but they have left the server.")
                except Exception: pass
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
            await log_error(guild, f"Wither restore failed: Unexpected error for {user.name} ({user.id}).", error=e)
            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                try: await interaction.channel.send(f"⚠️ An unexpected error occurred trying to restore roles for {user.display_name}.")
                except Exception: pass

    except discord.Forbidden:
        await log_error(guild, f"Wither initial remove failed: Forbidden for {user.name} ({user.id}).", interaction=interaction)
        try: await interaction.edit_original_response(content=f"❌ Failed to remove roles for {user.display_name}: Permissions error.", embed=None, view=None)
        except Exception: pass
    except discord.HTTPException as e:
        await log_error(guild, f"Wither initial remove failed: API error for {user.name} ({user.id}).", error=e, interaction=interaction)
        try: await interaction.edit_original_response(content=f"❌ Failed to remove roles for {user.display_name}: Discord API error.", embed=None, view=None)
        except Exception: pass
    except Exception as e:
        await log_error(guild, f"Wither initial remove failed: Unexpected error for {user.name} ({user.id}).", error=e, interaction=interaction)
        try: await interaction.edit_original_response(content=f"❌ An unexpected error occurred trying to wither {user.display_name}.", embed=None, view=None)
        except Exception: pass



@bot.event
async def on_message(message: discord.Message):
    # --- Initial Checks: Ignore self, or messages without basic properties ---
    if not message.guild or not bot.is_ready() or not bot.user or \
       message.author.id == bot.user.id: # Ignore messages from the bot itself
        return

    if message.author.bot: # If the message is from any other bot (not ours), generally ignore.
        return

    if not message.content and not message.attachments and not message.embeds:
        if not (message.channel.id == AUTOMOD_ALERT_CHANNEL_ID and message.type == discord.MessageType.auto_moderation_action):
            return

    guild = message.guild
    channel = message.channel
    user_id = message.author.id # For session checking

    # --- AutoMod Alert Message Parsing for Zorr.pro ---
    # (This section remains unchanged from your previous correct version)
    if message.channel.id == AUTOMOD_ALERT_CHANNEL_ID and \
       message.type == discord.MessageType.auto_moderation_action and \
       message.embeds:
        # ... (full Zorr.pro handling logic as previously provided) ...
        embed = message.embeds[0]
        original_message_content = embed.description
        original_author_member: discord.Member = message.author
        original_channel_id_from_fields: Optional[int] = None
        rule_name_from_fields: Optional[str] = None
        for field in embed.fields:
            if field.name == "channel_id":
                try: original_channel_id_from_fields = int(field.value)
                except (ValueError, TypeError):
                    await log_error(guild, f"ZorrRedirect: Could not parse channel_id '{field.value}' from embed field.", ping_owner=True); return
            elif field.name == "rule_name":
                rule_name_from_fields = str(field.value).strip()
        is_zorr_pro_trigger = False
        if rule_name_from_fields and "zorr.pro blocker" in rule_name_from_fields.lower(): is_zorr_pro_trigger = True
        if not original_message_content: original_message_content = "(Blocked message content was not found in the alert embed.)"
        if original_author_member and original_channel_id_from_fields and original_message_content and is_zorr_pro_trigger:
            if original_channel_id_from_fields == ZORR_PRO_DESIGNATED_CHANNEL_ID: return
            original_channel_obj = guild.get_channel(original_channel_id_from_fields)
            original_channel_name_for_log = f"#{original_channel_obj.name}" if original_channel_obj else f"ID {original_channel_id_from_fields}"
            await log_info(guild, f"ZorrRedirect: Matched AutoMod. User: {original_author_member.name}, OrigChan: {original_channel_name_for_log}")
            designated_channel = guild.get_channel(ZORR_PRO_DESIGNATED_CHANNEL_ID)
            if not isinstance(designated_channel, discord.TextChannel): await log_error(guild, f"ZorrRedirect: Designated channel {ZORR_PRO_DESIGNATED_CHANNEL_ID} invalid.", ping_owner=True); return
            bot_member = guild.me
            if not bot_member: return
            perms_in_designated = designated_channel.permissions_for(bot_member)
            if not perms_in_designated.send_messages or not perms_in_designated.manage_webhooks: await log_error(guild, f"ZorrRedirect: Bot lacks Send/ManageWebhooks in {designated_channel.mention}.", ping_owner=True); return
            info_message_content = (f"{original_author_member.mention}, your message related to zorr.pro was blocked in {original_channel_name_for_log}. Please discuss here in {designated_channel.mention}. I'll re-post your message:")
            try: await designated_channel.send(info_message_content)
            except discord.HTTPException as e: await log_error(guild, f"ZorrRedirect: Failed to send info message to {designated_channel.mention}", error=e); return
            temp_webhook: Optional[discord.Webhook] = None
            try:
                avatar_bytes: Optional[bytes] = None; webhook_display_name = original_author_member.display_name[:80]
                avatar_url_to_fetch = original_author_member.display_avatar.url if original_author_member.display_avatar else original_author_member.default_avatar.url
                async with aiohttp.ClientSession() as session: avatar_bytes = await fetch_avatar_bytes(session, avatar_url_to_fetch)
                disallowed_webhook_chars = ["@", "#", ":", "```", "discord"]
                if any(d_char in webhook_display_name.lower() for d_char in disallowed_webhook_chars) or webhook_display_name.lower() == "clyde": webhook_display_name = "Relayed Message"
                temp_webhook = await designated_channel.create_webhook(name=webhook_display_name, avatar=avatar_bytes, reason="Zorr.pro AutoMod relay")
                content_to_relay = original_message_content[:2000]
                await temp_webhook.send(content=content_to_relay, wait=True)
            except Exception as e_imitate: await log_error(guild, f"ZorrRedirect: Error during imitation.", error=e_imitate, ping_owner=True)
            finally:
                if temp_webhook:
                    try: await temp_webhook.delete(reason="Zorr.pro AutoMod relay cleanup")
                    except Exception: pass
            return
        return

    # --- Screenshot processing block ---
    if message.channel.id == SCREENSHOTS_DROPBOX_CHANNEL_ID and message.attachments:
        valid_image_attachments = [att for att in message.attachments if att.content_type and att.content_type.startswith("image/")]
        
        if valid_image_attachments:
            # --- Guild Sync Mode Logic ---
            active_session_data = guild_sync_sessions.get(user_id)
            
            # Clean up stale sessions implicitly if a new 10-image message arrives from a user with an old session
            if active_session_data and (discord.utils.utcnow() - active_session_data['last_update_time']).total_seconds() > GUILD_SYNC_SESSION_TIMEOUT_SECONDS:
                await log_info(guild, f"GuildSync: Stale session found for user {user_id} and cleaned up upon new message.")
                del guild_sync_sessions[user_id]
                active_session_data = None

            if len(valid_image_attachments) == 10:
                if active_session_data:
                    # User sent 10 images while a session is active - assume it's an "add more" batch
                    await log_info(guild, f"GuildSync Mode: Adding new batch of 10 images from {message.author.name} to existing session.")
                    asyncio.create_task(process_guild_sync_batch(message, valid_image_attachments, is_new_session=False))
                else:
                    # User sent 10 images and no session active - start new session
                    await log_info(guild, f"GuildSync Mode: Starting new session for {message.author.name} with 10 images.")
                    asyncio.create_task(process_guild_sync_batch(message, valid_image_attachments, is_new_session=True))
                return # Guild sync mode handles its own replies/updates
            elif active_session_data:
                # User sent a message with <10 images while a session is active.
                # Inform them they need to send exactly 10 for "add more" or use buttons.
                try:
                    await message.reply(
                        f"{message.author.mention} You have an active guild sync session. "
                        f"To add more screenshots, please send a message with exactly 10 images. "
                        f"Alternatively, use the buttons on my previous reply to finalize the report.",
                        delete_after=30.0 # Make it self-deleting
                    )
                except discord.HTTPException: pass
                return
            else: # 1-9 images and no active sync session - proceed with normal activity logging
                # (This is the start of your existing single-batch activity screenshot processing logic)
                # ... (Full existing logic for 1-9 images for activity logging) ...
                num_images = len(valid_image_attachments)
                processing_reply_content = f"{message.author.mention} ⏳ Analyzing {num_images} image(s) for online player names and activity updates..."
                processing_reply: Optional[discord.Message] = None
                try: processing_reply = await message.reply(processing_reply_content, allowed_mentions=discord.AllowedMentions(users=[message.author]))
                except discord.HTTPException as e_initial_reply: await log_error(guild, "Screenshot processing: Failed to send initial processing reply", error=e_initial_reply, message_context=message); return
                all_matched_igns_from_all_images: List[str] = []; all_ai_suggested_raw_names_global: Set[str] = set()
                ai_reported_no_names_at_least_once = False; ai_extracted_some_text_globally = False
                activity_date, date_error = get_utc_date()
                if date_error or not activity_date:
                    if processing_reply: await processing_reply.edit(content=f"{message.author.mention} ❌ Error: Could not determine today's date for activity logging.")
                    else: await message.channel.send(f"{message.author.mention} ❌ Error: Could not determine today's date for activity logging.")
                    await log_error(guild, f"Screenshot activity error: Failed to get today's date ({date_error})", message_context=message); return
                try:
                    ai_cog = bot.get_cog('AICog')
                    if not ai_cog:
                        if processing_reply: await processing_reply.edit(content=f"{message.author.mention} ❌ Error: AI module is not available.")
                        else: await message.channel.send(f"{message.author.mention} ❌ Error: AI module is not available.")
                        await log_error(guild, "Screenshot activity error: AICog not found.", message_context=message); return
                    known_igns_str = "\n".join(ai_cog.ingame_name_cache_ref) if ai_cog.ingame_name_cache_ref else "No known names."
                    for idx, image_att in enumerate(valid_image_attachments):
                        try:
                            image_data = await image_att.read()
                            ai_extracted_text_for_this_image = await ai_cog.get_ai_response_with_image(prompt_key="FLORR_IMAGE_NAME_EXTRACTION", image_bytes=image_data, prompt_kwargs={'known_igns_list_str': known_igns_str})
                            if ai_extracted_text_for_this_image:
                                stripped_ai_text = ai_extracted_text_for_this_image.strip()
                                if stripped_ai_text.upper() == "NO_NAMES_FOUND": ai_reported_no_names_at_least_once = True
                                else:
                                    ai_extracted_some_text_globally = True
                                    potential_names_from_ai_this_image = [name.strip() for name in stripped_ai_text.split('\n') if name.strip()]
                                    for raw_name in potential_names_from_ai_this_image: all_ai_suggested_raw_names_global.add(raw_name)
                                    if ai_cog.ingame_name_cache_ref and potential_names_from_ai_this_image:
                                        for ai_name in potential_names_from_ai_this_image:
                                            ai_name_lower = ai_name.lower()
                                            for cached_ign in ai_cog.ingame_name_cache_ref:
                                                if cached_ign.lower() == ai_name_lower:
                                                    if cached_ign not in all_matched_igns_from_all_images: all_matched_igns_from_all_images.append(cached_ign)
                                                    break
                        except Exception as e_single_img_proc: await log_error(guild, f"Error during single image processing (msg {message.id}, att {image_att.filename})", error=e_single_img_proc)
                    discarded_by_cache_check: List[str] = []
                    if ai_extracted_some_text_globally:
                        matched_igns_lower = {ign.lower() for ign in all_matched_igns_from_all_images}
                        for raw_ai_name in all_ai_suggested_raw_names_global:
                            if raw_ai_name.lower() not in matched_igns_lower: discarded_by_cache_check.append(raw_ai_name)
                    if discarded_by_cache_check: # Logging for discarded names logic remains
                        discarded_names_str = "\n- ".join(discord.utils.escape_markdown(d_name)[:100] for d_name in discarded_by_cache_check[:20]); log_parts = [f"AI suggested names for msg by {message.author.mention} in {message.channel.mention}", f"(Img(s): {', '.join([a.filename for a in valid_image_attachments])})", "discarded after cache check:", f"```\n- {discarded_names_str}\n```", "Raw Suggestions:", f"```\n- {chr(10).join(discord.utils.escape_markdown(s)[:100] for s in sorted(list(all_ai_suggested_raw_names_global))[:20])}\n```", f"Matched: {all_matched_igns_from_all_images or 'None'}"]; log_msg_discarded = "\n".join(log_parts); err_embed = discord.Embed(title="📝 AI Img: Discarded", description=log_msg_discarded[:4000], color=discord.Color.orange()); err_embed.timestamp = discord.utils.utcnow(); err_embed.set_footer(text=f"Msg ID: {message.id} | User: {message.author.name}"); await log_to_channel(EXTRAORDINARY_LOGS_CHANNEL_ID, guild, embed=err_embed)
                    newly_added_details: List[Dict[str, Any]] = []; already_active: List[str] = []; failed_to_add: List[str] = []
                    activity_changed = False; final_msg_obj: Optional[discord.Message] = processing_reply
                    if not all_matched_igns_from_all_images:
                        content = f"{message.author.mention} AI analysis of {num_images} image(s) complete: "; content += "No online player names (from known list with green dots) clearly identified." if ai_reported_no_names_at_least_once and not ai_extracted_some_text_globally else ("AI issue or no usable data from images." if not ai_extracted_some_text_globally and not ai_reported_no_names_at_least_once else "Some text identified, but didn't match known online IGNs or criteria.")
                        if final_msg_obj:
                            try: await final_msg_obj.edit(content=content, allowed_mentions=discord.AllowedMentions(users=[message.author]), embed=None, view=None)
                            except discord.HTTPException: final_msg_obj = await message.reply(content, allowed_mentions=discord.AllowedMentions(users=[message.author]))
                        else: final_msg_obj = await message.reply(content, allowed_mentions=discord.AllowedMentions(users=[message.author]))
                    else:
                        for ign in all_matched_igns_from_all_images:
                            exists = await check_activity_exists(guild, ign.lower(), activity_date)
                            if exists: already_active.append(ign)
                            elif exists is False:
                                success, upsert_msg = await upsert_activity_log(guild, ign, activity_date, message.author.id)
                                if success: newly_added_details.append({'ign': ign, 'status': 'active_by_view'}); activity_changed = True
                                else: failed_to_add.append(ign); await log_error(guild, f"SS Upsert Fail: IGN '{ign}', User {message.author.name}. DB: {upsert_msg}")
                            else: failed_to_add.append(ign); await log_error(guild, f"SS DB Check Fail: IGN '{ign}', User {message.author.name}")
                        ss_view = ScreenshotConfirmView(message.author.id, activity_date, newly_added_details, already_active, failed_to_add, guild, message.id); final_embed = ss_view.create_embed(); reply_content = f"{message.author.mention}"
                        if final_msg_obj:
                            try: final_msg_obj = await final_msg_obj.edit(content=reply_content, embed=final_embed, view=ss_view, allowed_mentions=discord.AllowedMentions(users=[message.author]))
                            except discord.HTTPException: final_msg_obj = await message.reply(content=reply_content, embed=final_embed, view=ss_view, allowed_mentions=discord.AllowedMentions(users=[message.author]))
                        else: final_msg_obj = await message.reply(content=reply_content, embed=final_embed, view=ss_view, allowed_mentions=discord.AllowedMentions(users=[message.author]))
                        if final_msg_obj: ss_view.message = final_msg_obj
                        if activity_changed: await log_info(guild, f"SS by {message.author.name}: New: {len(newly_added_details)}, Already: {len(already_active)}. List update."); asyncio.create_task(update_static_list_message(guild))
                        else: await log_info(guild, f"SS by {message.author.name}: No new activity. Already: {len(already_active)}.")
                except Exception as e_pipeline:
                    traceback.print_exc(); await log_error(guild, "Critical SS error", error=e_pipeline, ping_owner=True, message_context=message)
                    err_content = f"{message.author.mention} Sorry, critical error processing {num_images} image(s). Admins notified."
                    if processing_reply:
                        try: await processing_reply.edit(content=err_content, allowed_mentions=discord.AllowedMentions(users=[message.author]), embed=None, view=None)
                        except discord.HTTPException: await message.reply(err_content, allowed_mentions=discord.AllowedMentions(users=[message.author]))
                    else: await message.reply(err_content, allowed_mentions=discord.AllowedMentions(users=[message.author]))
            return # Handled screenshot processing (either sync or activity)

    # --- Super Attempt Logging ---
    # (This section remains unchanged from your previous correct version)
    if message.channel.id == SUPER_ATTEMPT_CHANNEL_ID:
        # ... (full super attempt logging logic as previously provided) ...
        if DISABLE_SUPER_ATTEMPT_LOGGING_FOR_TESTING_INSTANCE and not MANUAL_OVERRIDE_SUPER_ATTEMPT_LOGGING_IN_TESTING:
            if BOT_INSTANCE_TYPE == "TESTING": print(f"Super attempt logging skipped for message {message.id} due to TESTING instance type."); return
        msg_content = message.content.strip(); attempt_match = re.fullmatch(r"-(?P<petals>[1-4])\s*(?P<petal_query>.+)", msg_content, re.IGNORECASE)
        if attempt_match:
            petals_lost_str = attempt_match.group("petals"); petal_query_str = attempt_match.group("petal_query").strip()
            try: petals_lost = int(petals_lost_str)
            except ValueError: return
            if not petal_query_str: return
            author_ign = await get_ign_from_user(guild, message.author.id)
            if not author_ign:
                try:
                    await message.reply(f"{message.author.mention}, your IGN isn't linked. Use `/hcverify` or `/verify`.");
                except discord.HTTPException: pass; return
            attempt_date_obj, date_error_msg = get_utc_date()
            if date_error_msg or not attempt_date_obj:
                try: await message.reply(f"Sorry, error determining date.");
                except discord.HTTPException: pass; await log_error(guild, f"Super Attempt Log: Failed to get UTC date. Error: {date_error_msg}", message_context=message); return
            if not await check_supabase_available(message.channel): await log_info(guild, f"Super Attempt Log for '{petal_query_str}': Supabase unavailable."); return
            ultra_candidates = await find_ultra_petal_candidates_for_query(petal_query_str, guild); bot_reply_msg: Optional[discord.Message] = None
            if len(ultra_candidates) == 1: # Single match logic
                chosen_petal_data = ultra_candidates[0]; chosen_petal_name_for_db = chosen_petal_data['original_full_name']; display_friendly_name_for_reply = chosen_petal_data['display_friendly_name']
                try:
                    insert_resp = await run_supabase_sync(lambda: supabase.table("super_attempts").insert({"ingame_name": author_ign, "discord_user_id": str(message.author.id),"attempt_date": attempt_date_obj.isoformat(), "petals_lost": petals_lost,"message_id": str(message.id), "channel_id": str(message.channel.id),"chosen_petal_name": chosen_petal_name_for_db}).execute()); attempt_db_id = None
                    if insert_resp.data and len(insert_resp.data) > 0 and 'id' in insert_resp.data[0]: attempt_db_id = insert_resp.data[0]['id']
                    if not attempt_db_id: fetch_id_resp = await run_supabase_sync(lambda: supabase.table("super_attempts").select("id").eq("message_id", str(message.id)).eq("ingame_name", author_ign).eq("chosen_petal_name", chosen_petal_name_for_db).order("recorded_at", desc=True).limit(1).maybe_single().execute()); attempt_db_id = fetch_id_resp.data['id'] if fetch_id_resp.data else None
                    if not attempt_db_id: await log_error(guild, f"Super Attempt (single): Failed to get DB ID for {author_ign}", message_context=message);
                    try: await message.reply(f"Error saving (no DB ID). Admin notified.");
                    except discord.HTTPException: pass; await _update_reactions(message, "error"); return
                    all_time_attempts_count = await get_all_time_super_attempt_count(guild, author_ign)
                    sa_view = SuperAttemptConfirmView(message.author.id, attempt_db_id, petals_lost, display_friendly_name_for_reply, author_ign, all_time_attempts_count, message); embed = sa_view.create_embed()
                    # DB operation was successful. Now try to send confirmation and update reactions.
                    try:
                        bot_reply_msg = await message.reply(content=f"{message.author.mention}", embed=embed, view=sa_view); sa_view.message = bot_reply_msg
                        await _update_reactions(message, "success")
                    except discord.HTTPException as http_err_reply:
                        await log_error(guild, f"Super Attempt (Single Match): DB log OK, but Discord API error sending confirm view or success reaction for {author_ign}.", error=http_err_reply, message_context=message)
                        # Try to add success reaction one last time if the main reply failed, but don't switch to error icon for this.
                        try: await _update_reactions(message, "success") # Try adding success reaction again
                        except discord.HTTPException as http_err_reaction_retry:
                            await log_error(guild, f"Super Attempt (Single Match): Failed again to add success reaction for {author_ign} after confirm view send failed.", error=http_err_reaction_retry, message_context=message)
                    
                    await log_info(guild, f"Super attempt by `{author_ign}`: Lost {petals_lost}x {display_friendly_name_for_reply}. All-time: {all_time_attempts_count}.")
                    if isinstance(message.author, discord.Member): await update_custom_nickname_on_attempt(guild, message.author, author_ign, all_time_attempts_count)
                
                except Exception as e: # This catches errors from the DB logging primarily
                    await log_error(guild, f"Error logging single super attempt for {author_ign}", error=e, message_context=message, ping_owner=True);
                    try: await message.reply(f"Error logging attempt. Admin notified.");
                    except discord.HTTPException: pass
                    await _update_reactions(message, "error") # DB error, so use error reaction

            elif len(ultra_candidates) > 1: # Disambiguation logic
                disamb_embed = discord.Embed(title="❓ Which Ultra Petal Was It?", description=f"{message.author.mention}, \"{discord.utils.escape_markdown(petal_query_str)}\" could be multiple. Choose one:", color=discord.Color.blue())
                sa_disamb_view = SuperAttemptDisambiguationView(message.author.id, ultra_candidates, petals_lost, message, author_ign, attempt_date_obj); bot_reply_msg = await message.reply(embed=disamb_embed, view=sa_disamb_view); sa_disamb_view.message = bot_reply_msg
                await _update_reactions(message, "disambiguation")
            else: # No candidates, log as Unknown
                chosen_petal_name_for_db = "Unknown Ultra Petal"; display_friendly_name_for_reply = "Unknown Ultra"
                await log_info(guild, f"Super Attempt: No Ultra match for '{petal_query_str}' by {author_ign}. Logging as Unknown.")
                try: # Duplicate of single match logic, for Unknown
                    insert_resp = await run_supabase_sync(lambda: supabase.table("super_attempts").insert({"ingame_name": author_ign, "discord_user_id": str(message.author.id),"attempt_date": attempt_date_obj.isoformat(), "petals_lost": petals_lost,"message_id": str(message.id), "channel_id": str(message.channel.id),"chosen_petal_name": chosen_petal_name_for_db}).execute()); attempt_db_id = None
                    if insert_resp.data and len(insert_resp.data) > 0 and 'id' in insert_resp.data[0]: attempt_db_id = insert_resp.data[0]['id']
                    if not attempt_db_id: fetch_id_resp = await run_supabase_sync(lambda: supabase.table("super_attempts").select("id").eq("message_id", str(message.id)).order("recorded_at", desc=True).limit(1).maybe_single().execute()); attempt_db_id = fetch_id_resp.data['id'] if fetch_id_resp.data else None
                    if not attempt_db_id: await log_error(guild, f"Super Attempt (Unknown): Failed to get DB ID for {author_ign}", message_context=message);
                    try: await message.reply(f"Error saving (no DB ID for unknown). Admin notified.");
                    except discord.HTTPException: pass
                    await _update_reactions(message, "error"); return # DB error, so use error reaction
                    
                    all_time_attempts_count = await get_all_time_super_attempt_count(guild, author_ign)
                    sa_view = SuperAttemptConfirmView(message.author.id, attempt_db_id, petals_lost, display_friendly_name_for_reply, author_ign, all_time_attempts_count, message); embed = sa_view.create_embed()
                    # DB operation was successful. Now try to send confirmation and update reactions.
                    try:
                        bot_reply_msg = await message.reply(content=f"{message.author.mention}", embed=embed, view=sa_view); sa_view.message = bot_reply_msg
                        await _update_reactions(message, "success")
                    except discord.HTTPException as http_err_reply_unknown:
                        await log_error(guild, f"Super Attempt (Unknown Match): DB log OK, but Discord API error sending confirm view or success reaction for {author_ign}.", error=http_err_reply_unknown, message_context=message)
                        try: await _update_reactions(message, "success")
                        except discord.HTTPException as http_err_reaction_retry_unknown:
                             await log_error(guild, f"Super Attempt (Unknown Match): Failed again to add success reaction for {author_ign} after confirm view send failed.", error=http_err_reaction_retry_unknown, message_context=message)

                    await log_info(guild, f"Super attempt by `{author_ign}`: Lost {petals_lost}x {display_friendly_name_for_reply}. All-time: {all_time_attempts_count}.")
                    if isinstance(message.author, discord.Member): await update_custom_nickname_on_attempt(guild, message.author, author_ign, all_time_attempts_count)

                except Exception as e: # This catches errors from the DB logging primarily
                    await log_error(guild, f"Error logging 'Unknown Ultra Petal' for {author_ign}", error=e, message_context=message, ping_owner=True);
                    try: await message.reply(f"Error logging unknown petal. Admin notified.");
                    except discord.HTTPException: pass
                    await _update_reactions(message, "error") # DB error, so use error reaction
            return # Handled super attempt

    # --- HC List Auto-Delete ---
    # (This section remains unchanged from your previous correct version)
    if channel.id == HC_MEMBER_LIST_CHANNEL_ID:
        # ... (full HC list auto-delete logic as previously provided) ...
        is_main_list_message = False; active_view_data = active_static_list_views.get(HC_MEMBER_LIST_CHANNEL_ID)
        if active_view_data and active_view_data.get('message_id') == message.id: is_main_list_message = True
        if not is_main_list_message and message.author.id != bot.user.id:
            try: await message.delete(delay=AUTODELETE_DELAY_SECONDS)
            except (discord.Forbidden, discord.NotFound): pass 
            except Exception as e_del_user: await log_error(guild, f"Error auto-deleting user message {message.id} in HC list", error=e_del_user)
        elif not is_main_list_message and message.author.id == bot.user.id and not message.interaction:
            try: await message.delete(delay=AUTODELETE_DELAY_SECONDS)
            except (discord.Forbidden, discord.NotFound): pass
            except Exception as e_del_bot_misc: await log_error(guild, f"Error auto-deleting misc bot message {message.id} in HC list", error=e_del_bot_misc)
        return

    # --- Pass message to AI Cog for its processing ---
    # This call should be at the end of bot.py's on_message if no other handlers returned.
    ai_cog = bot.get_cog('AICog')
    if ai_cog and hasattr(ai_cog, 'process_message_for_ai'):
        if not message.webhook_id: # Don't let AI process messages sent by webhooks
            await ai_cog.process_message_for_ai(message)

@tree.command(name="message", description="Send a message as the bot, optionally using AI.")
@app_commands.describe(
    message_content="The message content. If AI is used, this becomes the prompt.",
    ai="[Optional] Have AI generate the message content? (Defaults to No)"
)
@app_commands.choices(ai=[
    app_commands.Choice(name="No", value="no"),
    app_commands.Choice(name="Yes", value="yes"),
])
async def message_command( # Renamed function to avoid conflict if you had 'message' before
    interaction: discord.Interaction,
    message_content: str,
    ai: Optional[str] = "no"
):
    if not interaction.channel:
        await interaction.response.send_message("This command needs a channel context.", ephemeral=True)
        return

    target_channel: discord.abc.Messageable = interaction.channel
    guild = interaction.guild # Can be None if in DMs
    use_ai_generation = ai.lower() == "yes" if ai else False
    final_content_to_send = message_content.strip() # Strip initial input
    ai_response_raw = None # To track if AI was successful

    bot_is_true_guild_member = guild and interaction.guild.me and interaction.guild.me.joined_at

    # Deferral Logic - Important to defer based on where the message will be sent
    # If bot is not a "true member" (e.g., app only), the command response itself is the message.
    # Otherwise, the command response is ephemeral, and bot sends a separate message.
    is_ephemeral_response = True
    if guild and not bot_is_true_guild_member:
        is_ephemeral_response = False # Bot will edit the interaction response directly

    await interaction.response.defer(thinking=True, ephemeral=is_ephemeral_response)

    # --- AI Generation Block ---
    if use_ai_generation:
        ai_cog = bot.get_cog('AICog')
        if not ai_cog:
            await log_info(guild, "/message command: AI cog not loaded. Sending original content.")
            feedback_msg = "⚠️ AI module is not available. Sending your original content."
            if is_ephemeral_response: await interaction.followup.send(feedback_msg, ephemeral=True)
            else: await interaction.edit_original_response(content=feedback_msg)
            # Fall through to send original content
        elif not ai_cog.get_all_available_models_details(): # Check if any models are actually configured in the cog
            await log_info(guild, "/message command: No AI models available in AICog. Sending original content.")
            feedback_msg = "⚠️ AI models are currently unavailable. Sending your original content."
            if is_ephemeral_response: await interaction.followup.send(feedback_msg, ephemeral=True)
            else: await interaction.edit_original_response(content=feedback_msg)
            # Fall through to send original content
        else:
            await log_info(guild, f"User `{interaction.user}` attempting AI message generation with prompt: \"{message_content[:100]}...\"")
            try:
                preferred_model_for_message_cmd = 'gemini_2_5_flash' # Or 'gemini_2_0_flash'

                prompt_data_for_ai = {
                    'current_message_content': message_content, # This is the user's prompt for the AI
                    'server_name': guild.name if guild else "DM",
                    'channel_name': target_channel.name if hasattr(target_channel, 'name') else "DM Channel"
                }
                # The HUMAN_SYSTEM_INSTRUCTION_V3 prompt gets server_name, channel_name etc. from prompt_data
                # if not explicitly overridden in system_instruction_details.kwargs.
                system_instruction_details_for_ai = {
                    'key': "HUMAN_SYSTEM_INSTRUCTION_V3",
                    'kwargs': {} # No specific overrides needed here for /message
                }

                # If the message needs to be sent in a text channel, provide typing context
                typing_ctx = target_channel.typing() if isinstance(target_channel, discord.TextChannel) and is_ephemeral_response else contextlib.nullcontext()
                async with typing_ctx:
                    ai_response_raw = await ai_cog.get_ai_response(
                        prompt_data=prompt_data_for_ai,
                        history=None, # No history for this command currently
                        system_instruction_details=system_instruction_details_for_ai,
                        preferred_model_id=preferred_model_for_message_cmd
                    )

                if ai_response_raw:
                    # Process the AI response (stripping, etc.)
                    processed_response = ai_response_raw.strip()
                    pingslave_prefix_pattern = re.compile(r"^(?:\[.*?UTC\]\s*)?(?:.*?\(You \(Pingslave\)\):\s*)", re.IGNORECASE)
                    match = pingslave_prefix_pattern.match(processed_response)
                    if match:
                        processed_response = processed_response[match.end():]
                    
                    if bot.user and bot.user.name:
                        display_name_prefix_lower = f"{bot.user.display_name.lower()}:"
                        name_prefix_lower = f"{bot.user.name.lower()}:"
                        if processed_response.lower().startswith(display_name_prefix_lower):
                            processed_response = processed_response[len(display_name_prefix_lower):].lstrip()
                        elif processed_response.lower().startswith(name_prefix_lower):
                            processed_response = processed_response[len(name_prefix_lower):].lstrip()
                    
                    processed_response = processed_response.strip()
                    if processed_response.endswith(('.', '!', '?')) and not any(processed_response.endswith(x) for x in ['...', '?!', '!!']):
                        processed_response = processed_response[:-1]
                    if len(processed_response) > 1980: processed_response = processed_response[:1977] + "..."
                    
                    if processed_response:
                        final_content_to_send = processed_response
                        await log_info(guild, f"User `{interaction.user}` used /message with AI. Generated: '{final_content_to_send[:100].strip()}...'")
                    else:
                        ai_response_raw = None # Treat empty processed response as no response
                        feedback_msg = "⚠️ AI generated an empty response. Sending your original content."
                        await log_info(guild, "/message command: AI generated an empty response.")
                        if is_ephemeral_response: await interaction.followup.send(feedback_msg, ephemeral=True)
                        else: await interaction.edit_original_response(content=feedback_msg)
                else:
                    feedback_msg = "⚠️ AI generated no response. Sending your original content."
                    await log_info(guild, "/message command: AI generated no response (None/empty raw).")
                    if is_ephemeral_response: await interaction.followup.send(feedback_msg, ephemeral=True)
                    else: await interaction.edit_original_response(content=feedback_msg)

            except Exception as ai_err:
                await log_error(guild, f"AI generation error for /message command", error=ai_err, interaction=interaction)
                feedback_msg = "⚠️ An error occurred during AI generation. Sending your original content."
                if is_ephemeral_response: await interaction.followup.send(feedback_msg, ephemeral=True)
                else: await interaction.edit_original_response(content=feedback_msg)
                ai_response_raw = None # Ensure it's None on error

    # --- Send Message Block ---
    try:
        if not final_content_to_send: # Should not happen if AI fails as it defaults to original
            final_content_to_send = "*(Original message was empty or AI failed to generate content.)*"

        if len(final_content_to_send) > 2000:
            final_content_to_send = final_content_to_send[:1997] + "..."

        if not is_ephemeral_response: # Bot is not a "true member", edit the interaction response
            response_text_for_edit = final_content_to_send
            if use_ai_generation and ai_response_raw : response_text_for_edit += "\n*(AI Generated)*"
            if len(response_text_for_edit) > 2000 : response_text_for_edit = response_text_for_edit[:1997] + "..."
            await interaction.edit_original_response(content=response_text_for_edit, view=None, embed=None)
            await log_info(guild, f"User `{interaction.user}` used /message (App-Only Mode) in {target_channel.mention if isinstance(target_channel, discord.TextChannel) else 'UnknownChannel'}. AI Used: {use_ai_generation}, AI Success: {bool(ai_response_raw)}.")
        else: # Bot is a "true member", send a new message and confirm ephemerally
            if isinstance(target_channel, discord.TextChannel) and guild and interaction.guild.me:
                if not target_channel.permissions_for(interaction.guild.me).send_messages:
                    await interaction.edit_original_response(content=f"❌ I don't have 'Send Messages' permission in {target_channel.mention}.", view=None, embed=None)
                    return
            
            await target_channel.send(final_content_to_send)
            confirmation_msg = "✅ Message sent."
            if use_ai_generation and ai_response_raw: confirmation_msg += " (AI Generated)"
            await interaction.edit_original_response(content=confirmation_msg, view=None, embed=None) # Confirm ephemerally
            await log_info(guild, f"User `{interaction.user}` used /message (Full Member/DM) in {target_channel.mention if isinstance(target_channel, discord.TextChannel) else 'DM/Group'}. AI Used: {use_ai_generation}, AI Success: {bool(ai_response_raw)}.")

    except discord.Forbidden:
        await log_error(guild, "/message failed sending: Forbidden", interaction=interaction)
        try:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Failed to send message: I lack permissions in this channel/context.", ephemeral=True)
            else: # Should have been deferred
                await interaction.edit_original_response(content=f"❌ Failed to send message: I lack permissions in this channel/context.", view=None, embed=None)
        except Exception: pass
    except discord.HTTPException as e:
        await log_error(guild, "/message failed sending: HTTP Exception", error=e, interaction=interaction)
        try:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Failed to send message: Discord API error. {e.text}", ephemeral=True)
            else:
                await interaction.edit_original_response(content=f"❌ Failed to send message: Discord API error. {e.text}", view=None, embed=None)
        except Exception: pass
    except Exception as e:
        await log_error(guild, "/message failed sending: Unexpected error", error=e, interaction=interaction, ping_owner=True)
        try:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ An unexpected error occurred while sending the message.", ephemeral=True)
            else:
                 await interaction.edit_original_response(content=f"❌ An unexpected error occurred while sending the message.", view=None, embed=None)
        except Exception: pass

@tree.command(name="imitate", description="[Staff Only] Send a message appearing as another user.")
@app_commands.describe(
    user="The user to imitate (name and avatar).",
    message_content="The content of the message to send."
)
@app_commands.check(can_manage_guild_or_is_bypass_user)
async def imitate(
    interaction: discord.Interaction,
    user: discord.Member,
    message_content: str
):
    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("This command can only be used in server text channels.", ephemeral=True)
        return

    target_channel: discord.TextChannel = interaction.channel
    guild = interaction.guild # Should always exist due to TextChannel check

    # Defer ephemerally as the command result is just a confirmation
    await interaction.response.defer(thinking=True, ephemeral=True)

    # Bot permissions check (implicitly needed for webhook creation)
    if guild and interaction.guild.me:
        bot_perms = target_channel.permissions_for(interaction.guild.me)
        if not bot_perms.manage_webhooks:
            await interaction.followup.send(f"❌ I lack the 'Manage Webhooks' permission in {target_channel.mention} to imitate {user.display_name}.", ephemeral=True)
            await log_error(guild, f"/imitate failed: Bot missing manage_webhooks permission for user {user.display_name}.", interaction=interaction)
            return

    avatar_bytes: Optional[bytes] = None
    async with aiohttp.ClientSession() as session:
        avatar_url_to_fetch = user.display_avatar.url if user.display_avatar else user.default_avatar.url
        avatar_bytes = await fetch_avatar_bytes(session, avatar_url_to_fetch)
        if not avatar_bytes:
            # This is less critical for imitate, Discord might use a default if avatar fetch fails for webhook
            await log_info(guild, f"/imitate warning: Failed to fetch avatar for {user.display_name}. Webhook might use default.")

    temp_webhook: Optional[discord.Webhook] = None
    try:
        webhook_name = user.display_name[:80] # Max 80 chars for webhook name
         # Basic check for Discord disallowed characters/strings in webhook names
        disallowed_in_names = ["@", "#", ":", "```", "discord"]
        if any(disallowed in webhook_name.lower() for disallowed in disallowed_in_names) or webhook_name.lower() == "clyde":
             webhook_name = "Imitated User" # Fallback if display name is problematic
             await log_info(guild, f"/imitate: User '{user.display_name}' display name problematic for webhook, using fallback '{webhook_name}'.")


        temp_webhook = await target_channel.create_webhook(
            name=webhook_name,
            avatar=avatar_bytes,
            reason=f"Temp webhook for /imitate by {interaction.user} (imitating {user.id})"
        )
        await temp_webhook.send(content=message_content, wait=True)
        await interaction.edit_original_response(content=f"✅ Message sent, imitating {user.mention}.")
        await log_info(guild, f"User `{interaction.user}` used /imitate as {user.mention} in {target_channel.mention}. Content: '{message_content[:50].strip()}...'")

    except discord.Forbidden:
        await interaction.edit_original_response(content=f"❌ I lack permissions (likely 'Manage Webhooks' or 'Send Messages' via webhook) in {target_channel.mention} to imitate {user.display_name}.")
        await log_error(guild, f"/imitate failed: Forbidden.", interaction=interaction)
    except discord.HTTPException as e:
        await interaction.edit_original_response(content=f"❌ Discord API Error: Failed to send message imitating {user.display_name}. {e.text}")
        await log_error(guild, f"/imitate failed: HTTP Exception.", error=e, interaction=interaction)
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ An unexpected error occurred.")
        await log_error(guild, f"/imitate failed: Unexpected error.", error=e, interaction=interaction, ping_owner=True)
    finally:
        if temp_webhook:
            try: await temp_webhook.delete(reason="Temp webhook cleanup for /imitate")
            except Exception as e_del: await log_error(guild, f"Failed to delete temp webhook for /imitate. Webhook ID: {temp_webhook.id}", error=e_del)

# Helper function to handle sending public errors for /florr
async def send_public_florr_error(interaction: discord.Interaction, public_message_content: str, log_message_content: str, log_level: str = "info", ping_owner_on_log: bool = False):
    """Sends a public error message for /florr and updates the ephemeral interaction response."""
    guild = interaction.guild # Can be None if in DMs (though /florr is TextChannel only)
    
    try:
        if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
             await interaction.channel.send(f"{interaction.user.mention} {public_message_content}")
             await interaction.edit_original_response(content=f"⚠️ Problem with your input. See message above in channel.", view=None)
        else: # Fallback if channel context is lost or not TextChannel (should not happen for /florr)
             await interaction.edit_original_response(content=f"{interaction.user.mention} {public_message_content}", view=None)
    except discord.Forbidden:
        await interaction.edit_original_response(content="❌ Error: I lack permissions to send the full error message or update this response.", view=None)
    except discord.HTTPException:
        await interaction.edit_original_response(content="❌ Error: Discord API error while reporting the problem.", view=None)
    except Exception as e:
        await interaction.edit_original_response(content="❌ Error: An unexpected error occurred while reporting the problem.", view=None)
        if guild: await log_error(guild, f"Failed to send public florr error itself: {e}", interaction=interaction, ping_owner=True)

    # Log the original intended error
    if guild:
        if log_level == "error":
            await log_error(guild, log_message_content, interaction=interaction, ping_owner=ping_owner_on_log)
        else: # 'info' or other
            await log_info(guild, log_message_content) # log_info doesn't take interaction or ping_owner
    elif log_level == "error": # Log to console if no guild
        print(f"ERROR (No Guild Context for /florr error): {log_message_content}")


@tree.command(name="florr", description="Send a message with a custom name and a chosen Florr-themed profile picture.")
@app_commands.describe(
    name="The name to display for the message (1-80 characters).",
    profile="Choose a profile picture from the Petals/Mobs list.",
    message_content="The content of the message to send."
)
@app_commands.autocomplete(profile=profile_pic_autocomplete)
async def florr(
    interaction: discord.Interaction,
    name: str,
    profile: str,
    message_content: str
):
    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
        # This initial check can be ephemeral as it's a command context issue
        await interaction.response.send_message("This command can only be used in text channels.", ephemeral=True)
        return

    target_channel: discord.TextChannel = interaction.channel
    guild = interaction.guild # Should always exist due to TextChannel check

    # Defer ephemerally. We will send public messages for specific errors if needed.
    await interaction.response.defer(thinking=True, ephemeral=True)

    # Validate custom name
    cleaned_name = name.strip()
    if not (1 <= len(cleaned_name) <= 80):
        # This error is about the 'name' param, not 'profile', so ephemeral is fine.
        await interaction.edit_original_response(content="❌ Custom name must be 1-80 characters long.", view=None)
        return
    disallowed_in_names = ["@", "#", ":", "```", "discord"]
    if any(disallowed in cleaned_name.lower() for disallowed in disallowed_in_names) or cleaned_name.lower() == "clyde":
        # This error is about the 'name' param, ephemeral is fine.
        await interaction.edit_original_response(content=f"❌ The custom name '{discord.utils.escape_markdown(cleaned_name)}' contains disallowed characters or is a reserved name.", view=None)
        return

    # --- Stricter Profile Validation ---
    if not available_profile_pics_cache:
        # This is a bot-side issue (cache not loaded), ephemeral is fine
        await interaction.edit_original_response(content="❌ Profile picture choices are currently unavailable. Please try again later or use `/refresh`.", view=None)
        await log_error(guild, "/florr: available_profile_pics_cache is empty.", interaction=interaction, ping_owner=True)
        return

    # Check if `profile` is one of the special error values from autocomplete
    if profile == "error_no_images_loaded":
        await send_public_florr_error(
            interaction,
            "Profile picture choices could not be loaded by the bot. Please try `/refresh` or ask an admin to check the bot's setup.",
            "/florr: User selected 'error_no_images_loaded'. Cache might be empty or uninitialized.",
            log_level="error", ping_owner_on_log=True
        )
        return
    if profile == "error_no_matches_found":
         await send_public_florr_error(
            interaction,
            "No profile picture matches your search term. Please try a different term or select from the broader list.",
            f"/florr: User selected 'error_no_matches_found'. User may have typed non-matching string for autocomplete.",
            log_level="info"
        )
         return

    # Generate the set of valid choice values from the cache
    valid_choice_values = {f"{folder_id_cache}:{filename_cache}" for _, folder_id_cache, filename_cache in available_profile_pics_cache}

    if profile not in valid_choice_values:
        # User typed something not in the list or manipulated the value
        public_err_msg = f"Invalid profile picture selection: `{discord.utils.escape_markdown(profile)}`.\nPlease select a valid option from the autocomplete list that appears as you type."
        log_err_msg = f"/florr: User {interaction.user.name} provided invalid profile selection '{profile}'. It was not in the {len(valid_choice_values)} valid choice values."
        await send_public_florr_error(interaction, public_err_msg, log_err_msg, log_level="info")
        return

    # --- Profile Parsing and File Handling (Errors here are also made public) ---
    try:
        folder_id, filename_with_ext = profile.split(":", 1)
    except ValueError: # Should be caught by `profile not in valid_choice_values`, but defensive.
        public_err_msg = "Internal error processing profile selection format. This should not happen if you selected from the list."
        log_err_msg = f"/florr: Invalid profile value format AFTER cache validation: '{profile}'"
        await send_public_florr_error(interaction, public_err_msg, log_err_msg, log_level="error", ping_owner_on_log=True)
        return

    # Folder ID check (PETALS_FOLDER_NAME, MOBS_FOLDER_NAME) - defensive
    if folder_id not in [PETALS_FOLDER_NAME, MOBS_FOLDER_NAME]:
        public_err_msg = "Invalid folder specified in profile picture selection. Please select from the list."
        log_err_msg = f"/florr: Unknown folder_id in profile value AFTER cache validation: '{folder_id}'"
        await send_public_florr_error(interaction, public_err_msg, log_err_msg, log_level="error", ping_owner_on_log=True)
        return

    # PROFILE_PIC_BASE_PATH check - bot config error, ephemeral is fine for this one.
    if not PROFILE_PIC_BASE_PATH:
        await interaction.edit_original_response(content="⚠️ Configuration error: Profile picture base path not set. Contact bot owner.", view=None)
        await log_error(guild, "/florr command failed: PROFILE_PIC_BASE_PATH is not set.", interaction=interaction, ping_owner=True)
        return
        
    image_path = os.path.join(PROFILE_PIC_BASE_PATH, folder_id, filename_with_ext)

    if not os.path.exists(image_path):
        public_err_msg = f"The image file for `{discord.utils.escape_markdown(filename_with_ext)}` seems to be missing on the server. The list might be outdated. Try `/refresh` or contact an admin."
        log_err_msg = f"/florr: Image file not found at '{image_path}'. Cache might be stale or file actually missing."
        await send_public_florr_error(interaction, public_err_msg, log_err_msg, log_level="error", ping_owner_on_log=True)
        return

    chosen_avatar_bytes: Optional[bytes] = None
    try:
        with open(image_path, "rb") as f:
            chosen_avatar_bytes = f.read()
    except Exception as e:
        public_err_msg = f"Error reading image file for `{discord.utils.escape_markdown(filename_with_ext)}`. Please try another selection or contact an admin."
        log_err_msg = f"Error reading image file {image_path} for /florr"
        await send_public_florr_error(interaction, public_err_msg, log_err_msg, log_level="error", ping_owner_on_log=True)
        # Note: send_public_florr_error handles logging the exception passed via `e` if guild context exists.
        # To ensure it's logged, we can call log_error directly here too.
        if guild: await log_error(guild, f"Error reading image file {image_path} for /florr", error=e, interaction=interaction)
        return

    if not chosen_avatar_bytes: # Should be caught by `open` error, but defensive
        public_err_msg = f"Failed to load image data for `{discord.utils.escape_markdown(filename_with_ext)}`. Please try another selection."
        log_err_msg = f"/florr: chosen_avatar_bytes was None after attempting to read {image_path}."
        await send_public_florr_error(interaction, public_err_msg, log_err_msg, log_level="error", ping_owner_on_log=True)
        return

    # --- Webhook Logic ---
    # Errors in this section (Forbidden, HTTP) are typically bot permissions or Discord API issues,
    # so their ephemeral error messages are generally fine.
    temp_webhook: Optional[discord.Webhook] = None
    try:
        if guild and interaction.guild.me: # Should always be true due to earlier checks
            bot_perms = target_channel.permissions_for(interaction.guild.me)
            if not bot_perms.manage_webhooks:
                # This is a bot permission issue, ephemeral error is fine.
                await interaction.edit_original_response(content=f"❌ I lack the 'Manage Webhooks' permission in {target_channel.mention} to send this message.", view=None)
                await log_error(guild, f"/florr failed: Bot missing manage_webhooks permission.", interaction=interaction)
                return

        temp_webhook = await target_channel.create_webhook(
            name=cleaned_name,
            avatar=chosen_avatar_bytes,
            reason=f"Temp webhook for /florr by {interaction.user}"
        )
        await temp_webhook.send(content=message_content, wait=True)
        # Success message is ephemeral, updating the deferred response.
        await interaction.edit_original_response(content=f"✅ Message sent as '{cleaned_name}' with picture '{folder_id}/{filename_with_ext}'.", view=None)
        await log_info(guild, f"User `{interaction.user}` used /florr as '{cleaned_name}' (Pic: {folder_id}/{filename_with_ext}) in {target_channel.mention}. Msg: '{message_content[:50].strip()}...'")

    except discord.Forbidden:
        await interaction.edit_original_response(content=f"❌ I lack permissions (likely 'Manage Webhooks') in {target_channel.mention}.", view=None)
        await log_error(guild, f"/florr failed: Forbidden.", interaction=interaction)
    except discord.HTTPException as e:
        error_text = f"Discord API Error: Failed to send. Code: {e.code}, Text: {e.text}"
        await interaction.edit_original_response(content=error_text[:1900], view=None)
        await log_error(guild, f"/florr failed: HTTP Exception", error=e, interaction=interaction)
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ An unexpected error occurred.", view=None)
        await log_error(guild, f"/florr failed: Unexpected error.", error=e, interaction=interaction, ping_owner=True)
    finally:
        if temp_webhook:
            try: await temp_webhook.delete(reason="Temp webhook cleanup for /florr")
            except Exception as e_del: await log_error(guild, f"Failed to delete temp webhook for /florr. ID: {temp_webhook.id}", error=e_del)
   
@tree.command(name="nerdhelp", description="Show the list of available bot commands.")
async def nerdhelp(interaction: discord.Interaction):
    # // --- UNCHANGED SECTION (nerdhelp beginning - guild check, bot ready, command_ids check) --- //
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    if not bot or not bot.user:
        await interaction.response.send_message("Bot is not fully ready, cannot generate help.", ephemeral=False)
        return
    if not command_ids:
        print("Warning: command_ids dictionary is empty during nerdhelp execution! Links may not be clickable.")
    # // --- END UNCHANGED SECTION (nerdhelp beginning - guild check, bot ready, command_ids check) --- //

    can_see_staff_commands = False
    if isinstance(interaction.user, discord.Member): # Ensure user is a Member for permission checks
        can_see_staff_commands = await can_manage_guild_or_is_bypass_user(interaction)

    view_instance = HelpPagesView(bot_user=bot.user, is_staff_view_allowed=can_see_staff_commands)
    
    if not can_see_staff_commands:
        view_instance.clear_items() 

    initial_embed = view_instance.get_current_embed()

    # // --- UNCHANGED SECTION (nerdhelp end - sending message and error handling) --- //
    try:
        await interaction.response.send_message(embed=initial_embed, view=view_instance, ephemeral=False)
        view_instance.message = await interaction.original_response()
            
    except Exception as e:
        print(f"Error sending nerdhelp response: {e}")
        if isinstance(e, discord.HTTPException) and e.code == 50035:
            print("--- TRACEBACK FOR NERDHELP 50035 ---")
            print(traceback.format_exc())
            print("--- END TRACEBACK ---")
        await log_error(interaction.guild, "Failed to send nerdhelp response", error=e, interaction=interaction)
        try:
            if interaction.response.is_done():
                await interaction.followup.send("Failed to generate help embed.", ephemeral=False)
            else: # Should have been responded to by send_message above
                await interaction.edit_original_response(content="Failed to generate help embed.", embed=None, view=None)
        except Exception: pass
    # // --- END UNCHANGED SECTION (nerdhelp end - sending message and error handling) --- //

@tree.command(name="cleanup_bot_messages", description="[Owner Only] Deletes the bot's previous N messages in this channel.")
@app_commands.describe(
    count="Number of bot's own messages to delete (1-100)."
)
async def cleanup_bot_messages(interaction: discord.Interaction, count: app_commands.Range[int, 1, 100]):
    # 1. Owner check
    if interaction.user.id != OWNER_USER_ID:
        await interaction.response.send_message("❌ Unauthorized. This command is for the bot owner only.", ephemeral=True)
        return

    # 2. Guild and TextChannel check
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ This command can only be used in a text channel.", ephemeral=True)
        return
    
    target_channel: discord.TextChannel = interaction.channel

    # 3. Defer ephemerally
    await interaction.response.defer(thinking=True, ephemeral=True)

    # 4. Bot permissions check (Read Message History)
    bot_member = guild.me
    if not bot_member: # Should not happen
        await interaction.followup.send("❌ Internal error: Bot member object not found.", ephemeral=True)
        return
        
    if not target_channel.permissions_for(bot_member).read_message_history:
        await interaction.followup.send(f"❌ I lack the `Read Message History` permission in {target_channel.mention}.", ephemeral=True)
        return

    # 5. Collect bot's messages
    messages_to_delete: List[discord.Message] = []
    # Determine scan limit: scan up to count * 5 messages, with a max overall scan of 500
    # This helps find 'count' bot messages even if they are interspersed with other users' messages.
    scan_limit = min(count * 7, 700) # Increased multiplier slightly and overall scan limit
    
    await log_info(guild, f"/cleanup_bot_messages: User {interaction.user.name} trying to delete {count} bot messages in #{target_channel.name}. Scan limit: {scan_limit}.")
    
    initial_feedback_message = f"⏳ Scanning up to {scan_limit} messages in {target_channel.mention} to find {count} of my own messages to delete..."
    if scan_limit < count * 2 and count > 10: # Heuristic for when scan limit might be too tight
        initial_feedback_message += "\n*(Note: Scan limit might be tight if my messages are sparse.)*"
    try:
        await interaction.edit_original_response(content=initial_feedback_message)
    except discord.HTTPException:
        pass # If interaction already expired, proceed silently

    try:
        async for message in target_channel.history(limit=scan_limit):
            if message.author.id == bot.user.id: # Check if bot.user is not None
                # Do not delete the interaction response message itself if it's from the bot (unlikely for this command path, but good check)
                if interaction.id and message.interaction and message.interaction.id == interaction.id:
                    continue
                messages_to_delete.append(message)
                if len(messages_to_delete) >= count:
                    break
        
        if not messages_to_delete:
            await interaction.edit_original_response(content=f"ℹ️ No messages of mine found to delete within the last {scan_limit} messages checked in {target_channel.mention}.", view=None)
            await log_info(guild, f"/cleanup_bot_messages: Found 0 bot messages to delete in #{target_channel.name} within scan limit {scan_limit}.")
            return

        # 6. Delete messages
        deleted_count = 0
        failed_count = 0
        
        await interaction.edit_original_response(content=f"🗑️ Found {len(messages_to_delete)} of my messages. Starting deletion (this may take a moment)...", view=None)

        # Delete messages one by one (more reliable for older messages than purge)
        # Delete from oldest to newest in the found list to avoid issues with changing history during iteration if it were newest first.
        # However, discord.HistoryIterator already gives messages from newest to oldest.
        # So, messages_to_delete is currently newest first. Reversing it for deletion is slightly more intuitive if there are issues.
        # messages_to_delete.reverse() # Optional: delete oldest found messages first. For now, let's stick to newest found.

        for msg_to_del in messages_to_delete:
            try:
                await msg_to_del.delete()
                deleted_count += 1
                await asyncio.sleep(0.3) # Small delay to avoid hitting rate limits quickly
            except discord.Forbidden:
                failed_count += 1
            except discord.NotFound:
                # Message was already deleted, perhaps by another process or user
                pass # Or count as success if desired: deleted_count +=1
            except discord.HTTPException as e_del_http:
                failed_count += 1
                await log_error(guild, f"/cleanup_bot_messages: HTTP error deleting message {msg_to_del.id}.", error=e_del_http, interaction=interaction)
                if e_del_http.status == 429: # Rate limited
                    await interaction.edit_original_response(content=f" Rate limited by Discord while deleting. {deleted_count} deleted so far. Please try again later for the rest.", view=None)
                    return # Stop processing on rate limit
            except Exception as e_del_unknown:
                failed_count += 1
                await log_error(guild, f"/cleanup_bot_messages: Unknown error deleting message {msg_to_del.id}.", error=e_del_unknown, interaction=interaction)

        # 7. Report results
        result_message = f"✅ Cleanup complete in {target_channel.mention}!\n"
        result_message += f"- Messages targeted for deletion: {len(messages_to_delete)}\n"
        result_message += f"- Successfully deleted: {deleted_count}\n"
        if failed_count > 0:
            result_message += f"- Failed to delete: {failed_count} (see logs for details)"
        
        await interaction.edit_original_response(content=result_message, view=None)
        await log_info(guild, f"/cleanup_bot_messages: User {interaction.user.name} finished. Deleted: {deleted_count}, Failed: {failed_count} in #{target_channel.name}.")

    except discord.Forbidden: # This would be for history() failing
        await interaction.edit_original_response(content=f"❌ Forbidden: I lack `Read Message History` permission in {target_channel.mention} to find messages.", view=None)
        await log_error(guild, f"/cleanup_bot_messages: Forbidden on channel.history() for {target_channel.mention}.", interaction=interaction)
    except discord.HTTPException as e_hist_http:
        await interaction.edit_original_response(content=f"❌ Discord API Error while fetching history from {target_channel.mention}: {e_hist_http.text}", view=None)
        await log_error(guild, f"/cleanup_bot_messages: HTTP error on channel.history() for {target_channel.mention}.", error=e_hist_http, interaction=interaction)
    except Exception as e_unknown_outer:
        await interaction.edit_original_response(content=f"❌ An unexpected error occurred: {type(e_unknown_outer).__name__}", view=None)
        await log_error(guild, f"/cleanup_bot_messages: Unexpected outer error.", error=e_unknown_outer, interaction=interaction, ping_owner=True)

@tree.command(name="ping", description="Check the bot's latency to Discord.")
async def ping(interaction: discord.Interaction):
    # Defer the response to acknowledge the command immediately
    # Use ephemeral=False so the "Pinging..." message is visible
    await interaction.response.defer(thinking=True, ephemeral=False)

    # 1. WebSocket Latency
    ws_latency_ms = round(bot.latency * 1000)

    # 2. API Latency (Message Send/Edit)
    # Send an initial message
    start_time = discord.utils.utcnow()
    # We use followup.send() because we deferred with thinking=True
    # If we used defer(ephemeral=False, thinking=False), we could use edit_original_response
    # But followup.send() after defer(thinking=True) is also a common pattern for this.
    # For this specific case, editing the original deferred response is cleaner.
    
    # Send a placeholder message to measure edit time
    message_to_edit = await interaction.edit_original_response(content="Pinging API...")
    end_time = discord.utils.utcnow()

    api_latency_ms = round((end_time - start_time).total_seconds() * 1000)
    
    # Create embed for results
    embed = discord.Embed(
        title="🏓 Pong!",
        color=NERDY_YELLOW # Use your defined color
    )
    embed.add_field(name="🤖 Bot Latency (WebSocket)", value=f"`{ws_latency_ms} ms`", inline=False)
    embed.add_field(name="↔️ API Latency (Message Edit)", value=f"`{api_latency_ms} ms`", inline=False)
    
    current_time_formatted = get_formatted_utc_now()
    embed.set_footer(text=f"Measured at: {current_time_formatted}")

    # Edit the original (deferred) response with the results
    await interaction.edit_original_response(content=None, embed=embed)
    
    # Optional: Log the ping
    guild = interaction.guild
    if guild:
        await log_info(guild, f"/ping by {interaction.user}: WS Latency={ws_latency_ms}ms, API Latency={api_latency_ms}ms")
    else:
        print(f"/ping by {interaction.user} (DM): WS Latency={ws_latency_ms}ms, API Latency={api_latency_ms}ms")

@tree.command(name="test", description="Test fuzzy matching for petal names with spelling correction.")
@app_commands.describe(petal_query="The petal name (or part of it) you're searching for.")
async def test_petal_match(interaction: discord.Interaction, petal_query: str):
    await interaction.response.defer(ephemeral=True)

    match_result = await fuzzy_match_petal_name(petal_query) # Uses MODIFIED fuzzy_match_petal_name

    status = match_result.get('status')
    original_q = match_result.get('original_query', petal_query) 
    processed_q = match_result.get('processed_query', "N/A")

    if status == 'cache_not_ready':
        await interaction.followup.send("Petal names cache is not loaded yet. Please try again or use `/refresh`.")
    elif status == 'no_searchable_petals':
        await interaction.followup.send("No processable petal names found in the cache. The Petals image folder might be empty or misconfigured.")
    elif status == 'empty_query_after_processing':
        await interaction.followup.send(f"Your query (`{original_q}`) became empty after processing. Please try a more specific name part.")
    elif status == 'not_found':
        await interaction.followup.send(
            f"No close match found for input `{original_q}` (processed for matching as: `{processed_q}`).\n"
            f"Try a different spelling or a more distinct part of the name."
        )
    elif status == 'ambiguous':
        ambiguous_names = match_result.get('ambiguous_display_names', [])
        names_str = ", ".join([f"`{name}`" for name in ambiguous_names])
        await interaction.followup.send(
            f"Input Query: `{original_q}` (processed as: `{processed_q}`)\n\n"
            f"⚠️ **Ambiguous Match:** Could be one of: {names_str}.\nPlease be more specific."
        )
    elif status == 'success':
        base_name = match_result.get('base_name_matched', "Error: No base name")
        display_friendly = match_result.get('display_friendly_name', "Error: No display name")
        
        response_message = (
            f"Input Query: `{original_q}`\n"
            f"(Processed for matching as: `{processed_q}`)\n\n"
            f"Matched Base Name: **{base_name}**\n"
            f"Display-Friendly Name: **{display_friendly}**"
        )
        # Check if an Ultra version of this base_name exists, just for info in /test
        ultra_version_full_name = await check_ultra_petal_exists(base_name)
        if ultra_version_full_name:
            # Get the display-friendly version of the *Ultra* petal name
            ultra_display_friendly = _get_display_friendly_petal_name(ultra_version_full_name)
            response_message += f"\n(Ultra version found: `{ultra_display_friendly}` from cache name `{ultra_version_full_name}`)"
        else:
            response_message += "\n(No Ultra version of this base petal was found in cache)"
            
        await interaction.followup.send(response_message)
    else:
        await interaction.followup.send("An unexpected result occurred during matching.")

@tree.command(name="setnickname", description="Manage your custom nickname template for super attempts.")
@app_commands.describe(
    template="Nickname template (e.g., \"IGN | {satt} satt\"). Uses {satt} for super attempt count. Omit to toggle bot management.",
    user="[Optional] Target another user (requires Manage Nicknames permission)."
)
async def setnickname(interaction: discord.Interaction, template: Optional[str] = None, user: Optional[discord.Member] = None):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    if not await check_supabase_available(interaction):
        return

    target_user = user or interaction.user
    if not isinstance(target_user, discord.Member):
        await interaction.response.send_message("Invalid user provided.", ephemeral=True)
        return
        
    if user and user.id != interaction.user.id:
        if not interaction.permissions.manage_nicknames:
            await interaction.response.send_message(f"❌ You need 'Manage Nicknames' permission to set templates for others.", ephemeral=True)
            return

    await interaction.response.defer(ephemeral=True)

    author_ign = await get_ign_from_user(guild, target_user.id)
    if not author_ign:
        await interaction.followup.send(f"❌ {target_user.mention} does not have an In-Game Name linked in the database. Cannot manage nickname.", ephemeral=True)
        return

    manage_by_bot_new_value: bool
    template_to_store: Optional[str] = None
    response_message_parts = []

    # Fetch current settings to toggle manage_nickname_by_bot if template is omitted
    current_settings_resp = await run_supabase_sync(
        lambda: supabase.table("hc_members")
                       .select("manage_nickname_by_bot, custom_nickname_template, is_in_hc")
                       .eq("discord_id", str(target_user.id))
                       .maybe_single()
                       .execute()
    )
    
    current_manage_by_bot = False
    current_is_in_hc = False
    if current_settings_resp and hasattr(current_settings_resp, 'data') and current_settings_resp.data:
        current_manage_by_bot = current_settings_resp.data.get("manage_nickname_by_bot", False)
        current_is_in_hc = current_settings_resp.data.get("is_in_hc", False)
        # If template is not provided, current_custom_template is not directly used for setting, but for info.
        # current_custom_template = current_settings_resp.data.get("custom_nickname_template")


    if template is not None: # Template parameter was explicitly provided (even if empty string)
        cleaned_template = template.strip()
        if not cleaned_template: # User provided blank string explicitly to clear template
            manage_by_bot_new_value = True # Keep management ON but use default format
            template_to_store = None # Store NULL for custom_template
            response_message_parts.append(f"⚙️ Custom nickname template **cleared** for {target_user.mention}.")
            if current_is_in_hc:
                 response_message_parts.append(f"🤖 Bot will now use the default HC nickname format: `IGN (SATT satt)` or `IGN`.")
            else:
                 response_message_parts.append(f"🤖 Bot will now set nickname to IGN as user is not in HC.")
            response_message_parts.append(f"🤖 Bot nickname management remains **enabled** (or enabled if it was off).")

        elif len(cleaned_template) > 200:
            await interaction.followup.send(f"❌ Nickname template is too long (max 200 characters).", ephemeral=True)
            return
        else: # Valid custom template provided
            manage_by_bot_new_value = True
            template_to_store = cleaned_template
            response_message_parts.append(f"⚙️ Custom nickname template for {target_user.mention} set to: `{discord.utils.escape_markdown(template_to_store)}`.")
            response_message_parts.append(f"🤖 Bot nickname management **enabled** (or enabled if it was off).")
            if "{satt}" not in template_to_store:
                response_message_parts.append(f"⚠️ Your template does not include `{{satt}}`. The super attempt count will not be shown.")
    else: # Template parameter was omitted entirely (is None) -> Toggle management
        manage_by_bot_new_value = not current_manage_by_bot # Toggle the current state
        if manage_by_bot_new_value:
            template_to_store = None # When turning ON by toggle, ensure custom template is NULL for default format
            response_message_parts.append(f"🤖 Bot nickname management **enabled** for {target_user.mention}.")
            if current_is_in_hc:
                 response_message_parts.append(f"🤖 Bot will now use the default HC nickname format.")
            else:
                 response_message_parts.append(f"🤖 Bot will now set nickname to IGN as user is not in HC (if different).")

        else: # Turning OFF
            template_to_store = None # Clear template when turning off management too, for consistency
            response_message_parts.append(f"🤖 Bot nickname management **disabled** for {target_user.mention}.")
            response_message_parts.append(f"🏷️ Nickname will revert to IGN (if different and user is in HC) or be unmanaged.")


    try:
        await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .update({
                               "manage_nickname_by_bot": manage_by_bot_new_value,
                               "custom_nickname_template": template_to_store
                           })
                           .eq("discord_id", str(target_user.id))
                           # Ensure it's for the correct IGN if user has multiple accounts (rare)
                           # This also implicitly checks if the user is in hc_members for this IGN
                           .eq("ingame_name", author_ign) 
                           .execute()
        )
        response_message_parts.append(f"💾 Settings saved.")

        # Immediately update nickname based on new settings
        all_time_count = await get_all_time_super_attempt_count(guild, author_ign)
        # Call update_custom_nickname_on_attempt. It will now handle:
        # 1. Custom template if manage_by_bot_new_value is True and template_to_store is not None.
        # 2. Default HC format if manage_by_bot_new_value is True, template_to_store is None, and is_in_hc is True.
        # 3. Reverting to IGN if manage_by_bot_new_value is False and is_in_hc is True.
        await update_custom_nickname_on_attempt(guild, target_user, author_ign, all_time_count)
        
        current_nick = target_user.nick # Get nick after potential update
        # This confirmation is a bit trickier now due to multiple nickname outcomes.
        # update_custom_nickname_on_attempt logs the actual change.
        response_message_parts.append(f"ℹ️ Nickname update based on new settings has been processed. Check server for changes.")


    except Exception as e:
        await log_error(guild, f"Error saving nickname settings for {target_user.mention}", error=e, interaction=interaction)
        await interaction.followup.send("❌ An error occurred while saving your nickname settings.", ephemeral=True)
        return

    await interaction.followup.send("\n".join(response_message_parts), ephemeral=True)
    await log_info(guild, f"`{interaction.user}` used /setnickname for {target_user.mention}. Manage: {manage_by_bot_new_value}, Template: '{template_to_store}'.")

# --- Bot Startup ---
if __name__ == "__main__":
    print("--- Initializing Pingslave Bot ---")
    # Essential checks before starting
    if not MAIN_TOKEN:
        print("CRITICAL: DISCORD_BOT_MAIN_TOKEN environment variable not found. Bot cannot start.")
    elif not supabase:
        print("CRITICAL: Supabase client initialization failed. Check URL/Key and connection. Bot may have limited functionality.")
        # Decide if you want the bot to run without Supabase or exit
        # exit(1) # Example: exit if Supabase fails
    else:
        print("Discord MAIN_TOKEN and Supabase Client OK.")
        print("Starting Keep Alive Flask server...")
        keep_alive() # Starts Flask in a separate thread

        try:
            print("Attempting to start Discord Bot...")
            # --- IMPORTANT: REMOVED log_handler=None ---
            # This allows default discord.py logging to show connection/sync status
            bot.run(MAIN_TOKEN)
        except discord.LoginFailure:
            # MAIN_TOKEN is invalid
            print("CRITICAL: Discord Login Failed. The provided DISCORD_BOT_MAIN_TOKEN is invalid or expired.")
        except discord.PrivilegedIntentsRequired:
            # Member intent is likely missing in Discord Dev Portal settings
            print("CRITICAL: Privileged Intents (Server Members Intent) required but not enabled in the Discord Developer Portal.")
        except Exception as e:
            # Catch any other unexpected errors during startup
            print(f"CRITICAL: Unexpected error during bot execution: {e}")
            print(traceback.format_exc()) # Print full traceback for debugging

    print("--- Bot process has potentially ended (check logs for specific errors) ---")
