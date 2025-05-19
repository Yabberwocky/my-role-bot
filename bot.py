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
from typing import Optional, Tuple, List, Dict, Any, Set # Keep this one, it's used more broadly
from dotenv import load_dotenv
import datetime
import pytz
from dateutil.parser import parse as date_parse
from discord.ext import tasks
import re
import asyncio
import discord.utils
import io # <--- ADD THIS IMPORT
from PIL import Image
import aiohttp
import contextlib

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
    # WEEKLY_PAGE = "weekly" # REMOVED
    MONTHLY_PAGE = "monthly"

    def __init__(self, interaction: discord.Interaction,
                 target_user_display_data: Dict[str, Any],
                 hc_profile_data: Optional[Dict[str, Any]],
                 activity_summary_data: Optional[Dict[str, Any]],
                 # weekly_active_dates: Optional[Set[datetime.date]], # REMOVED
                 initial_monthly_active_dates: Optional[Set[datetime.date]], # For current month display
                 today_date_obj: datetime.date,
                 timeout=180.0):
        super().__init__(timeout=timeout)
        self.original_command_interaction = interaction
        self.target_user_display_data = target_user_display_data
        self.hc_profile_data = hc_profile_data # Contains IGN needed for fetching later
        self.activity_summary_data = activity_summary_data
        
        # State for currently displayed monthly data
        self.current_display_month = today_date_obj.month
        self.current_display_year = today_date_obj.year
        self.monthly_active_dates_for_current_view = initial_monthly_active_dates or set()
        
        self.today_date_obj = today_date_obj # Actual current date
        
        self.current_page_mode = self.MAIN_PAGE
        self.message: Optional[discord.Message] = None 

        self._update_ui_elements() # Changed from _update_buttons

    def _update_ui_elements(self): # Renamed for clarity
        self.clear_items()
        
        if self.current_page_mode == self.MAIN_PAGE:
            if self.hc_profile_data and self.hc_profile_data.get("ingame_name"):
                monthly_btn = discord.ui.Button(label="🗓️ View Monthly Activity", style=discord.ButtonStyle.secondary, custom_id=f"profile_nav_{self.MONTHLY_PAGE}", row=0)
                monthly_btn.callback = self.navigation_button_callback
                self.add_item(monthly_btn)
        else: # On MONTHLY_PAGE
            back_to_main_btn = discord.ui.Button(label="⬅️ Back to Main Profile", style=discord.ButtonStyle.primary, custom_id=f"profile_nav_{self.MAIN_PAGE}", row=0)
            back_to_main_btn.callback = self.navigation_button_callback
            self.add_item(back_to_main_btn)
            
            if self.current_page_mode == self.MONTHLY_PAGE:
                # Pass the view's currently displayed month/year to the select
                self.add_item(ProfileMonthSelect(
                    current_real_year=self.today_date_obj.year, 
                    current_real_month=self.today_date_obj.month,
                    currently_selected_year=self.current_display_year, # Pass current view's year
                    currently_selected_month=self.current_display_month, # Pass current view's month
                    num_months_to_show=12
                ))

    # _create_main_embed remains the same as your last working version
    def _create_main_embed(self) -> discord.Embed:
        # // --- UNCHANGED SECTION (FROM PREVIOUS WORKING VERSION) --- //
        # This function should be exactly as it was when the main profile page looked correct.
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
            if ign is not None:
                if is_in_hc is True: hc_status_display = "✅ `In Guild (HC1)`"
                elif is_in_hc is False: hc_status_display = "⏳ `Formerly in Guild (HC1)`"
                else: hc_status_display = "❔ `HC Status Unknown (DB)`"
        
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
        
        embed.set_footer(text=f"Profile data generated: {get_formatted_utc_now()} | Use /activatemyself to mark active!")
        return embed
        # // --- END UNCHANGED SECTION --- //


    # _create_weekly_embed is REMOVED

    def _create_monthly_embed(self) -> discord.Embed:
        ign = self.hc_profile_data.get("ingame_name") if self.hc_profile_data else "N/A"
        embed = discord.Embed(
            title=f"🗓️ Monthly Activity - {discord.utils.escape_markdown(ign)}",
            color=NERDY_YELLOW
        )
        # REMOVED: Do not set thumbnail for the monthly view to maximize text space
        # if self.target_user_display_data['avatar_url']:
        #     embed.set_thumbnail(url=self.target_user_display_data['avatar_url'])
            
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

    async def _update_message(self, interaction_to_respond_to: discord.Interaction):
        self._update_ui_elements() 
        embed_to_send: discord.Embed
        if self.current_page_mode == self.MONTHLY_PAGE:
            embed_to_send = self._create_monthly_embed()
        else: 
            embed_to_send = self._create_main_embed()
        
        try:
            await interaction_to_respond_to.response.edit_message(embed=embed_to_send, view=self)
        except discord.HTTPException as e:
            print(f"Error updating profile page view: {e}")
            guild_for_log = interaction_to_respond_to.guild 
            if bot and hasattr(bot, 'log_error_global'):
                 await bot.log_error_global(guild_for_log, "Failed to update profile page message", error=e)
            elif guild_for_log:
                 await log_error(guild_for_log, "Failed to update profile page message (fallback log)", error=e)
            if not interaction_to_respond_to.response.is_done():
                try: await interaction_to_respond_to.response.defer()
                except discord.HTTPException: pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True # Allow anyone to interact

    async def navigation_button_callback(self, interaction: discord.Interaction):
        button_custom_id = interaction.data.get('custom_id')
        if not button_custom_id or not button_custom_id.startswith("profile_nav_"):
            if not interaction.response.is_done(): await interaction.response.defer()
            return

        new_mode = button_custom_id.split("profile_nav_")[1]
        
        if new_mode not in [self.MAIN_PAGE, self.MONTHLY_PAGE]: # WEEKLY_PAGE removed
            if not interaction.response.is_done(): await interaction.response.defer()
            return

        if self.current_page_mode == new_mode: 
            if not interaction.response.is_done(): await interaction.response.defer()
            return

        self.current_page_mode = new_mode
        # If switching to monthly, ensure data is for current real month initially
        if new_mode == self.MONTHLY_PAGE and \
           (self.current_display_month != self.today_date_obj.month or self.current_display_year != self.today_date_obj.year):
            
            # Fetch data for the actual current month before displaying
            # This is if user goes Main -> Monthly, ensure monthly isn't showing an old selected month
            if self.hc_profile_data and self.hc_profile_data.get("ingame_name"):
                ign_lower = self.hc_profile_data.get("ingame_name").lower()
                first_day_current_month = self.today_date_obj.replace(day=1)
                if self.today_date_obj.month == 12:
                    first_day_next_month = first_day_current_month.replace(year=self.today_date_obj.year + 1, month=1)
                else:
                    first_day_next_month = first_day_current_month.replace(month=self.today_date_obj.month + 1)
                last_day_current_month = first_day_next_month - datetime.timedelta(days=1)

                self.monthly_active_dates_for_current_view = await fetch_activity_dates_in_range(
                    self.original_command_interaction.guild, # Use guild from original interaction
                    ign_lower, 
                    first_day_current_month, 
                    last_day_current_month
                )
                self.current_display_month = self.today_date_obj.month
                self.current_display_year = self.today_date_obj.year
            else: # No IGN, cannot fetch monthly data
                self.monthly_active_dates_for_current_view = set()


        await self._update_message(interaction)

    async def handle_month_selection(self, interaction: discord.Interaction, selected_value: str):
        """Callback for the month select dropdown."""
        # selected_value is "YYYY-MM"
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
        
        # Defer the select interaction while fetching
        # await interaction.response.defer() # Already handled by _update_message if it's called
                                        # But if fetch is long, defer early here is good.
                                        # For now, _update_message will handle the response edit.

        # Fetch data for the selected month
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
            self.original_command_interaction.guild, # Use guild from original interaction
            ign_lower, 
            first_day_selected_month, 
            last_day_selected_month
        )
        self.current_display_month = selected_month
        self.current_display_year = selected_year
        
        # Update the message with new monthly data
        # Ensure current_page_mode is MONTHLY_PAGE before calling _update_message
        self.current_page_mode = self.MONTHLY_PAGE 
        await self._update_message(interaction) # Pass the select's interaction

    async def on_timeout(self):
        if self.message: 
            try:
                timeout_embed: discord.Embed
                if self.current_page_mode == self.MONTHLY_PAGE: timeout_embed = self._create_monthly_embed()
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
        self.current_page = "general" # "general" or "staff"
        self.is_staff_view_allowed = is_staff_view_allowed
        self.message: Optional[discord.Message] = None

        # --- We will let the @discord.ui.button decorator handle the button ---
        # --- So, NO self.toggle_button = ... or self.add_item(...) here for it ---
        
        # Update the appearance of the decorated button if it's going to be active.
        # The button itself is only "active" (visible/added to children) if is_staff_view_allowed.
        # We need to find the button instance created by the decorator to modify it.
        # The children are populated after __init__ completes based on decorators.
        # So, we can't modify it here directly in __init__ before it's added.
        # Instead, the button's initial appearance can be set in its callback logic or before sending.
        
        # If not staff view allowed, we will remove the button before sending the view.
        # This is done in the /nerdhelp command now.
        pass


    def _update_decorated_button_appearance(self, button_to_update: discord.ui.Button):
        """Updates the label, emoji, and style of the button passed to it."""
        if self.current_page == "general":
            button_to_update.label = "View Staff Commands"
            button_to_update.emoji = "🛡️"
            button_to_update.style = discord.ButtonStyle.secondary
        else: # current_page == "staff"
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
        embed.add_field(name=f"{get_cmd_mention('profile')} · View your [HC1] profile and activity.", value="\u200B", inline=False)
        embed.add_field(name="\u200B\n🕵️ Secret Phrase Discovery", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('discoveries')} · Show secret phrase discovery progress.", value="\u200B", inline=False)
        embed.add_field(name="\u200B\n💬 Messaging", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('message')} · Send a message as the bot (opt. AI).", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('florr')} · Send msg with custom name & Florr pic.", value="\u200B", inline=False)
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
        embed.add_field(name=f"{get_cmd_mention('syncnicknames')}  · Sync all HC nicks. `[Manage Nicks]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('wither')}  · Temp role removal. `[Special]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('addkeyword')} · Add keyword rule. `[Owner Only]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('aiping')} · Check AI model latencies. `[Owner Only]`", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('cleanup_bot_messages')} · Delete N bot messages. `[Owner Only]`", value="\u200B", inline=False)
        embed.set_footer(text="Bot by TheNerd | sweet_honey")
        return embed

    def get_current_embed(self) -> discord.Embed:
        if self.current_page == "staff":
            return self._create_staff_embed()
        return self._create_general_embed()

    # The button defined by the decorator is the one and only toggle button.
    # Its initial label/style will be as defined in the decorator. We update it before sending the view.
    @discord.ui.button(label="View Staff Commands", emoji="🛡️", style=discord.ButtonStyle.secondary, custom_id="help_toggle_page_decorator_final")
    async def toggle_page_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_staff_view_allowed:
            await interaction.response.send_message("This action is not available.", ephemeral=True, delete_after=5)
            return

        if self.current_page == "general":
            self.current_page = "staff"
        else:
            self.current_page = "general"
        
        self._update_decorated_button_appearance(button) # Pass the button instance from the callback
        current_embed = self.get_current_embed()
        
        await interaction.response.edit_message(embed=current_embed, view=self)

    async def on_timeout(self):
        if self.message and self.is_staff_view_allowed: # Only if there was an interactive element
            try:
                current_embed_on_timeout = self.get_current_embed()
                current_embed_on_timeout.set_footer(text=f"{current_embed_on_timeout.footer.text} (Interaction timed out)")
                
                # Find the button and disable it
                for item in self.children:
                    if isinstance(item, discord.ui.Button) and item.custom_id == "help_toggle_page_decorator_final":
                        item.disabled = True
                        break
                await self.message.edit(embed=current_embed_on_timeout, view=self) # Send view with disabled button
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
        """Callback for the MyProfileButton."""
        # This sends a *new* ephemeral message, so it doesn't conflict with view edits
        wip_message = (
             f"👋 Hey {interaction.user.mention}!\n\n"
             "The **My Profile** feature is still under construction 🚧.\n\n"
             "It will eventually show your personal stats like activity history, verification date, etc.\n\n"
             "Thanks for your interest! Click the button below if you'd like to let the developer know you're waiting eagerly for this feature."
        )
        wip_embed = discord.Embed(description=wip_message, color=NERDY_YELLOW)
        wip_view = MyProfileWIPView(requesting_user=interaction.user, bot_owner_id=self.bot_owner_id)
        # Ensure this is the first response for this specific interaction
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=wip_embed, view=wip_view, ephemeral=True)
        else:
            # If somehow already responded (e.g., view timed out concurrently?), use followup
            try:
                await interaction.followup.send(embed=wip_embed, view=wip_view, ephemeral=True)
            except Exception as e_followup:
                 print(f"[Static View] Error sending MyProfile followup: {e_followup}")


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
async def log_error(guild: Optional[discord.Guild], message: str, error: Optional[Exception] = None, interaction: Optional[discord.Interaction] = None, embed: Optional[discord.Embed] = None, ping_owner: bool = False):
    """
    Logs an error. Always prints to console.
    Sends to Discord error channel ONLY if in the target guild.
    Pings owner ONLY if in the target guild AND ping_owner is True.
    """
    is_target = guild and guild.id == CATERCORD_GUILD_ID
    log_prefix = f"[{guild.name if guild else 'No Guild'}] ERROR:"
    discord_ping_content: Optional[str] = None

    # --- Prepare Embed Details (Done Regardless of Target Guild) ---
    if not embed:
        title_prefix = f"🚨 Bot {'Critical ' if ping_owner else ''}Error" if is_target else "⚠️ Bot Error / Warning"
        embed = discord.Embed(title=title_prefix, description=message, color=discord.Color.red())
        embed.timestamp = discord.utils.utcnow()
        if interaction:
            cmd_name = interaction.command.name if interaction.command else 'N/A'
            cmd = f"`/{cmd_name}`" if cmd_name != 'N/A' else 'N/A'
            chan_mention = interaction.channel.mention if isinstance(interaction.channel, discord.TextChannel) else f"Ch:{interaction.channel_id}" if interaction.channel_id else "N/A"
            user = f"{interaction.user.mention} (`{interaction.user.id}`)" if interaction.user else "N/A"
            embed.add_field(name="Context", value=f"Cmd: {cmd} in {chan_mention}\nUser: {user}", inline=False)
        if error:
            etype, emsg = type(error).__name__, str(error)
            tb = "".join(traceback.format_exception(type(error), error, error.__traceback__, limit=6))
            tb_short = (tb[:900] + "\n... (Truncated)") if len(tb) > 900 else tb
            details = f"**Type:** `{etype}`\n" + (f"**Msg:** `{emsg}`\n" if emsg else "") + f"**Traceback:**\n```py\n{tb_short}\n```"
            if len(details) > 1024: details = details[:1000] + "...```"
            embed.add_field(name="Error Details", value=details, inline=False)
            full_tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
             # Print full traceback to console immediately
            print(f"---\n{log_prefix} Details:\nGuild: {guild.id if guild else 'N/A'}\nCtx: {message}\nErr: {etype}: {emsg}\n{full_tb}---")
        else:
            # Print basic error context to console if no exception object
            print(f"---\n{log_prefix} Context:\nGuild: {guild.id if guild else 'N/A'}\nMsg: {message}\n---")

    # --- Console Logging (Always Happens) ---
    # Console logging of the error context/traceback is handled above

    # --- Discord Channel Logging (Conditional) ---
    if is_target and guild: # Check if target guild and guild object exists
        # Determine if owner ping is needed *for Discord*
        if ping_owner:
            discord_ping_content = f"<@{OWNER_USER_ID}>"
            print(f"{log_prefix} (Owner Ping Queued for Discord)")

        # Call log_to_channel, targeting the ERROR channel
        await log_to_channel(EXTRAORDINARY_LOGS_CHANNEL_ID, guild, embed=embed, ping_mention=discord_ping_content)
    else:
        # Optionally print a note that Discord logging was skipped
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

# --- Start the task in on_ready ---
@bot.event
async def on_ready():
    # ... (your existing on_ready code) ...


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
    """ Creates or updates the SINGLE interactive HC list message, cleaning up old ones."""
    list_channel_id = HC_MEMBER_LIST_CHANNEL_ID
    chan = guild.get_channel(list_channel_id)

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
    if log_guild_for_ready_msg:
        try:
             instance_info = f" ({BOT_INSTANCE_TYPE} instance)" if BOT_INSTANCE_TYPE != "PRODUCTION" else ""
             await log_info(log_guild_for_ready_msg, f"Bot ready and online{instance_info}. Synced {len(synced_commands)} commands.")
        except Exception as log_e:
             print(f"Failed to send initial ready log message: {log_e}")

    print("--- Loading initial non-AI data ---")
    log_guild_for_data_load = bot.get_guild(CATERCORD_GUILD_ID)
    if not log_guild_for_data_load and bot.guilds: log_guild_for_data_load = bot.guilds[0]

    await load_ign_cache(log_guild_for_data_load)
    print("Loading profile picture choices...")
    await load_profile_picture_choices(log_guild_for_data_load)

    # --- START: Staff Channel Identification ---
    print("Identifying staff channels in target guild...")
    STAFF_CHANNELS.clear() # Clear previous findings
    target_guild_for_staff_channels = bot.get_guild(CATERCORD_GUILD_ID)
    if target_guild_for_staff_channels:
        florrist_role = target_guild_for_staff_channels.get_role(FLORRIST_ROLE_ID)
        hc1_role = target_guild_for_staff_channels.get_role(HC1_ROLE_ID)
        everyone_role = target_guild_for_staff_channels.default_role

        if florrist_role and hc1_role: # everyone_role always exists
            print(f"Checking channel visibility against roles: '{florrist_role.name}', '{hc1_role.name}' in guild '{target_guild_for_staff_channels.name}'")
            potentially_staff_channels = 0
            actually_staff_channels = 0
            for channel in target_guild_for_staff_channels.text_channels:
                everyone_perms = channel.permissions_for(everyone_role)
                if not everyone_perms.view_channel:
                    potentially_staff_channels += 1
                    florrist_ow = channel.overwrites_for(florrist_role)
                    hc1_ow = channel.overwrites_for(hc1_role)
                    florrist_can_view = florrist_ow.view_channel is True
                    hc1_can_view = hc1_ow.view_channel is True
                    if not florrist_can_view and not hc1_can_view:
                        STAFF_CHANNELS.add(channel.id)
                        actually_staff_channels += 1
                        # print(f"  -> Identified Staff Channel: #{channel.name} ({channel.id})")
            print(f"Staff Channel Identification Complete: Found {actually_staff_channels} staff channel(s) out of {potentially_staff_channels} potentially restricted channels.")
        else:
            missing_role_names = []
            if not florrist_role: missing_role_names.append(f"Florrist Role (ID: {FLORRIST_ROLE_ID})")
            if not hc1_role: missing_role_names.append(f"HC1 Role (ID: {HC1_ROLE_ID})")
            print(f"WARN: Could not find required roles in target guild for staff channel identification: {', '.join(missing_role_names)}.")
            if log_guild_for_data_load: # Log error if guild context available
                await log_error(target_guild_for_staff_channels, f"Failed to identify staff channels: Roles not found: {', '.join(missing_role_names)}.", ping_owner=True)
    else:
        print(f"WARN: Target guild (ID: {CATERCORD_GUILD_ID}) not found. Cannot identify staff channels.")
    # --- END: Staff Channel Identification ---

    # --- Set bot attributes for cogs (BEFORE loading them) ---
    print("Setting up bot attributes for cogs...")
    bot.supabase_client = supabase # Pass the actual Supabase client instance
    bot.log_info_global = log_info
    bot.log_error_global = log_error
    bot.run_supabase_sync_global = run_supabase_sync
    
    # Constants that the AI cog's setup function expects in its config dict
    bot.OWNER_USER_ID_config = OWNER_USER_ID 
    bot.CATERCORD_GUILD_ID_config = CATERCORD_GUILD_ID
    bot.PRIVATE_SERVER_ID_config = PRIVATE_SERVER_ID
    bot.RANDOM_SERVER_ID_config = RANDOM_SERVER_ID
    bot.STAFF_CHANNELS_config = STAFF_CHANNELS # Will be the set populated above
    bot.BOT_COMMANDS_ALLOWED_CHANNEL_IDS_config = BOT_COMMANDS_ALLOWED_CHANNEL_IDS
    bot.COMMAND_PREFIX_config = COMMAND_PREFIX
    bot.ALWAYS_ON_AI_CHANNELS_config = ALWAYS_ON_AI_CHANNELS
    bot.UNRESTRICTED_AI_CHANNEL_ID_config = UNRESTRICTED_AI_CHANNEL_ID
    # Pass the live ingame_name_cache list reference
    bot.ingame_name_cache_ref_config = ingame_name_cache 
    bot.NERDY_YELLOW_config = NERDY_YELLOW # If AI cog needs this color
    # Add any other constants AI cog might need from bot.py's global scope
    print("Bot attributes set.")

    # --- Load Cogs ---
    print("Loading cogs...")
    try:
        await bot.load_extension('ai_cog') # Ensure ai_cog.py is in the same directory
        print("AICog loaded successfully.")
    except commands.ExtensionAlreadyLoaded:
        print("AICog was already loaded.")
    except Exception as e_cog:
        print(f"CRITICAL: Failed to load AICog: {e_cog}\n{traceback.format_exc()}")
        if log_guild_for_data_load:
            await log_error(log_guild_for_data_load, "CRITICAL: Failed to load AICog.", error=e_cog, ping_owner=True)
    # --- End Load Cogs ---

# --- Command Syncing (Keep as is) ---
    print("Syncing application commands...")
    synced_commands = []
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
            else:
                print(f"  Skipped storing ID during sync for an item (type: {type(cmd)}, name: {getattr(cmd, 'name', 'N/A')})")
        if command_ids: print(f"Stored command IDs: {command_ids}")
        else: print("Warning: command_ids dictionary is empty after sync.")
    except discord.HTTPException as e:
        print(f"Command Sync failed (HTTPException): {e.status} - {e.text}")
    except Exception as e:
        print(f"Command Sync failed (Unexpected Error): {e}\n{traceback.format_exc()}")

    # --- Start Background Tasks ---
    print("Starting background tasks...")
    if not check_static_view_timeout.is_running():
        try:
            check_static_view_timeout.start()
            print(" Static view timeout checker task started.")
        except RuntimeError: # Already running
            print(" Static view timeout checker task was already running (RuntimeError).")
        except Exception as e_task_start:
            print(f"Failed to start static view timeout task: {e_task_start}")
            if log_guild_for_data_load:
                await log_error(log_guild_for_data_load, "Failed to start static view timeout task", error=e_task_start)


    # --- Schedule Delayed Static List Update ---
    async def delayed_update(delay_seconds: int):
        await asyncio.sleep(delay_seconds) # Wait for the specified delay
        print(f"--- Running delayed static list update after {delay_seconds}s ---")
        
        guild_for_delayed_update = bot.get_guild(CATERCORD_GUILD_ID)
        if not guild_for_delayed_update:
            print(f"ERROR: Could not find target guild {CATERCORD_GUILD_ID} for delayed static list update.")
            # Log this if possible. Guild context is None here.
            # await log_error(None, f"Delayed static list update failed: Target guild {CATERCORD_GUILD_ID} not found.")
            return
            
        if not supabase:
            print("ERROR: Supabase client not available for delayed static list update.")
            await log_error(guild_for_delayed_update, "Delayed static list update failed: Supabase client not available.")
            return
            
        try:
            await update_static_list_message(guild_for_delayed_update)
        except Exception as e:
            print(f"ERROR during delayed initial static list update: {e}\n{traceback.format_exc()}")
            await log_error(guild_for_delayed_update, "Error during delayed initial static list update", error=e)
        print(f"--- Delayed static list update finished ---")

    # Check if bot is fully ready and in the target guild before scheduling
    if bot.is_ready() and any(g.id == CATERCORD_GUILD_ID for g in bot.guilds):
        print("Scheduling delayed static list update for target guild (Catercord)...")
        # Use bot.loop.create_task for asyncio tasks from sync context if not already in async
        asyncio.create_task(delayed_update(delay_seconds=60)) # Using asyncio.create_task directly is fine in async func
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
    global command_ids # Ensure command_ids is accessible
    cmd_id = command_ids.get(name)
    if cmd_id:
        return f"</{name}:{cmd_id}>"
    else:
        print(f"Warn: No ID found for cmd '/{name}' in get_cmd_mention.")
        return f"`/{name}`"

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

    role_to_remove = guild.get_role(NEWBEE_ROLE_ID)
    role_to_add = guild.get_role(FLORRIST_ROLE_ID)

    # Role existence checks
    missing_roles = []
    if NEWBEE_ROLE_ID and not role_to_remove: missing_roles.append(f"Unverified Role (ID: {NEWBEE_ROLE_ID})")
    if FLORRIST_ROLE_ID and not role_to_add: missing_roles.append(f"Verified Role (ID: {FLORRIST_ROLE_ID})")
    if missing_roles:
        msg = f"❌ Setup Error: Roles not found: {', '.join(missing_roles)}. Please configure the bot."
        await interaction.response.send_message(msg, ephemeral=False)
        await log_error(guild, f"Verify failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return
    # We definitely need the role to add
    if not role_to_add:
         msg = f"❌ Setup Error: Verified Role (ID: {FLORRIST_ROLE_ID}) not configured correctly."
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

    # --- Determine Target and Fetch Base HC Profile Data ---
    # ... (This large block of target determination logic remains UNCHANGED from your last working version) ...
    # // --- UNCHANGED SECTION (Profile Target Determination) --- //
    target_user_for_display: discord.User 
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
                        target_user_for_display = await guild.fetch_member(int(target_discord_id_str))
                    except (discord.NotFound, ValueError, AttributeError):
                        target_user_for_display = bot.user 
                elif target_discord_id_str: 
                    target_user_for_display = bot.user 
                else: 
                    target_user_for_display = bot.user 
                if target_discord_id_str and target_discord_id_str == str(interaction.user.id):
                    target_is_self_profile = True
                    if isinstance(interaction.user, (discord.Member, discord.User)):
                         target_user_for_display = interaction.user 
            else:
                error_message_for_user = f"❌ No profile data found for IGN `{discord.utils.escape_markdown(cleaned_ign_param)}`."
    else: 
        target_is_self_profile = True
        target_user_for_display = interaction.user 
        target_discord_id_str = str(interaction.user.id)
        hc_profile_db_data = await fetch_hc_member_profile_data(guild, target_discord_id_str)
        if hc_profile_db_data:
            target_ign_from_db = hc_profile_db_data.get("ingame_name")
    if error_message_for_user:
        await interaction.edit_original_response(content=error_message_for_user, embed=None, view=None)
        return
    if not target_is_self_profile:
        invoker_is_staff_or_owner = False
        if guild and isinstance(interaction.user, discord.Member):
            invoker_is_staff_or_owner = await can_manage_guild_or_is_bypass_user(interaction)
        if not invoker_is_staff_or_owner:
            await interaction.edit_original_response(content="❌ You can only view your own profile or require staff permissions to view others'.", embed=None, view=None)
            return
    display_name_for_view: str
    avatar_url_for_view: Optional[str] = None
    mention_or_status_for_view: str
    if isinstance(target_user_for_display, (discord.Member, discord.User)):
        display_name_for_view = target_user_for_display.display_name
        avatar_url_for_view = target_user_for_display.display_avatar.url if target_user_for_display.display_avatar else target_user_for_display.default_avatar.url
        mention_or_status_for_view = target_user_for_display.mention
    elif hc_profile_db_data and hc_profile_db_data.get("ingame_name"): 
        display_name_for_view = hc_profile_db_data.get("ingame_name") 
        if bot.user and bot.user.display_avatar : avatar_url_for_view = bot.user.display_avatar.url 
        db_disc_name = hc_profile_db_data.get("discord_name")
        db_disc_id = hc_profile_db_data.get("discord_id")
        if db_disc_id:
            mention_or_status_for_view = f"`{discord.utils.escape_markdown(db_disc_name or f'ID: {db_disc_id}')}` (Info from DB)"
        else:
            mention_or_status_for_view = "`Not Linked to Discord`"
    else: 
        await interaction.edit_original_response(content="❌ Critical error: Could not determine target for profile display.", embed=None, view=None)
        return
    target_user_display_data_for_view = {
        "name": display_name_for_view,
        "avatar_url": avatar_url_for_view,
        "mention_or_status": mention_or_status_for_view
    }
    # // --- END UNCHANGED SECTION (Profile Target Determination) --- //

    activity_summary_for_view: Optional[Dict[str, Any]] = None
    # REMOVED weekly_active_dates_for_view
    initial_monthly_dates_for_view: Set[datetime.date] = set()
    today_utc_obj, _ = get_utc_date()

    if target_ign_from_db and today_utc_obj:
        ign_lower = target_ign_from_db.lower()
        
        is_active_today = await check_activity_exists(guild, ign_lower, today_utc_obj)
        active_today_disp = "❔ `N/A (DB Error)`"
        if is_active_today is True: active_today_disp = "✅ `Yes`" # Using standard emoji here
        elif is_active_today is False: active_today_disp = "❌ `No`" # Using standard emoji here
        
        all_time_summary = await fetch_activity_data(guild, [ign_lower])
        ign_all_time_data = all_time_summary.get(ign_lower, {'count': 0, 'last_seen': None})
        
        activity_summary_for_view = {
            "active_today_display": active_today_disp,
            "total_days_logged": ign_all_time_data['count'],
            "last_seen_display": f"`{format_date_dmy(ign_all_time_data['last_seen'])}`" if ign_all_time_data['last_seen'] else "`Never Logged`"
        }
        
        # Fetch active dates for the *current calendar month* for initial display
        first_day_of_current_month = today_utc_obj.replace(day=1)
        if today_utc_obj.month == 12:
            first_day_of_next_month = first_day_of_current_month.replace(year=today_utc_obj.year + 1, month=1)
        else:
            first_day_of_next_month = first_day_of_current_month.replace(month=today_utc_obj.month + 1)
        last_day_of_current_month = first_day_of_next_month - datetime.timedelta(days=1)
        
        initial_monthly_dates_for_view = await fetch_activity_dates_in_range(
            guild, ign_lower, first_day_of_current_month, last_day_of_current_month
        )
    
    if not today_utc_obj:
        await log_error(guild, "Profile command: Failed to get today's date object.", interaction=interaction)

    profile_view = ProfilePagesView(
        interaction=interaction,
        target_user_display_data=target_user_display_data_for_view,
        hc_profile_data=hc_profile_db_data,
        activity_summary_data=activity_summary_for_view,
        initial_monthly_active_dates=initial_monthly_dates_for_view, 
        today_date_obj=today_utc_obj if today_utc_obj else datetime.date.today() 
    )
    
    initial_embed = profile_view._create_main_embed()
    
    try:
        await interaction.edit_original_response(embed=initial_embed, view=profile_view)
        profile_view.message = await interaction.original_response()
    except discord.HTTPException as e_edit_final:
        # // --- UNCHANGED SECTION (Final Error Handling) --- //
        if guild: await log_error(guild, "Failed to send initial profile embed with view", error=e_edit_final, interaction=interaction)
        else: print(f"Failed to send initial profile embed (DM/No Guild): {e_edit_final}")
        try:
            await interaction.edit_original_response(content="❌ Error displaying profile. Please try again.", embed=None, view=None)
        except: pass
        # // --- END UNCHANGED SECTION (Final Error Handling) --- //

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

    hc_role = guild.get_role(HC1_ROLE_ID)
    if not hc_role:
        await interaction.edit_original_response(content=f"❌ Configuration Error: HC Role (ID: {HC1_ROLE_ID}) not found.")
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
    summary_embed.set_footer(text=f"Completed: {get_formatted_utc_now()}")
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
    if not message.guild or not bot.is_ready() or not bot.user or \
       message.author.id == bot.user.id or message.author.bot:
        return
    if not message.content and not message.attachments:
        return

    guild = message.guild
    channel = message.channel
    author = message.author

    # --- 1. Image Processing for Name Extraction & Activity Update ---
    if message.channel.id == SCREENSHOTS_DROPBOX_CHANNEL_ID and message.attachments:
        valid_image_attachments = [att for att in message.attachments if att.content_type and att.content_type.startswith("image/")]
        if valid_image_attachments:
            num_images = len(valid_image_attachments)
            print(f"{num_images} image(s) received in #{channel.name} from {author.name}. Processing for activity...")
            
            processing_reply_content = f"{author.mention} ⏳ Analyzing {num_images} image(s) for online player names and activity updates..."
            processing_reply = await message.reply(processing_reply_content, allowed_mentions=discord.AllowedMentions(users=[author]))

            all_matched_igns_from_all_images: List[str] = []
            all_ai_suggested_raw_names_global: Set[str] = set()
            ai_reported_no_names_at_least_once = False
            ai_extracted_some_text_globally = False

            activity_date, date_error = get_utc_date()
            if date_error or not activity_date:
                await processing_reply.edit(content=f"{author.mention} ❌ Error: Could not determine today's date for activity logging.")
                await log_error(guild, f"Screenshot activity error: Failed to get today's date ({date_error})", message_context=message) # Pass message_context
                return

            try:
                # --- MODIFICATION: Get AI Cog instance ---
                ai_cog = bot.get_cog('AICog')
                if not ai_cog:
                    await processing_reply.edit(content=f"{author.mention} ❌ Error: AI module is not available for image processing.")
                    await log_error(guild, "Screenshot activity error: AICog not found.", message_context=message)
                    return
                # --- END MODIFICATION ---

                known_igns_str = "\n".join(ai_cog.ingame_name_cache_ref) if ai_cog.ingame_name_cache_ref else "No known names provided." # Use cog's cache ref
                
                for idx, image_att in enumerate(valid_image_attachments):
                    print(f"Processing image {idx + 1}/{num_images} (Filename: {image_att.filename}, ID: {image_att.id})...")
                    try:
                        image_data = await image_att.read()
                        # --- MODIFICATION: Call cog's method ---
                        ai_extracted_text_for_this_image = await ai_cog.get_ai_response_with_image(
                            prompt_key="FLORR_IMAGE_NAME_EXTRACTION",
                            image_bytes=image_data,
                            prompt_kwargs={'known_igns_list_str': known_igns_str}
                        )
                        # --- END MODIFICATION ---
                        if ai_extracted_text_for_this_image:
                            stripped_ai_text = ai_extracted_text_for_this_image.strip()
                            if stripped_ai_text.upper() == "NO_NAMES_FOUND":
                                print(f"[Image {idx+1}] AI explicitly reported NO_NAMES_FOUND.")
                                ai_reported_no_names_at_least_once = True
                            else:
                                ai_extracted_some_text_globally = True
                                potential_names_from_ai_this_image = [name.strip() for name in stripped_ai_text.split('\n') if name.strip()]
                                print(f"[Image {idx+1}] AI extracted potential names: {potential_names_from_ai_this_image}")
                                for raw_name in potential_names_from_ai_this_image:
                                    all_ai_suggested_raw_names_global.add(raw_name)
                                # Use cog's ingame_name_cache_ref
                                if ai_cog.ingame_name_cache_ref and potential_names_from_ai_this_image:
                                    for ai_name in potential_names_from_ai_this_image:
                                        ai_name_lower = ai_name.lower()
                                        for cached_ign in ai_cog.ingame_name_cache_ref: # Use cog's reference
                                            if cached_ign.lower() == ai_name_lower:
                                                if cached_ign not in all_matched_igns_from_all_images:
                                                    all_matched_igns_from_all_images.append(cached_ign)
                                                break
                        else:
                            print(f"[Image {idx+1}] AI returned no usable text for this image.")
                    except Exception as e_single_img_proc:
                        print(f"Error processing image {idx + 1} (Filename: {image_att.filename}, ID: {image_att.id}): {e_single_img_proc}")
                        await log_error(guild, f"Error during single image processing (message {message.id}, attachment {image_att.filename})", error=e_single_img_proc)
                
                discarded_by_cache_check: List[str] = []
                if ai_extracted_some_text_globally:
                    matched_igns_lower = {ign.lower() for ign in all_matched_igns_from_all_images}
                    for raw_ai_name in all_ai_suggested_raw_names_global:
                        if raw_ai_name.lower() not in matched_igns_lower:
                            discarded_by_cache_check.append(raw_ai_name)
                if discarded_by_cache_check:
                    discarded_names_str = "\n- ".join(discord.utils.escape_markdown(d_name) for d_name in discarded_by_cache_check)
                    log_message_discarded = (
                        f"AI suggested names for message by {message.author.mention} (`{message.author.id}`) in {message.channel.mention} "
                        f"(Image(s): {', '.join([att.filename for att in valid_image_attachments]) or 'N/A'}) "
                        f"that were discarded after cache check (not in known IGN list or did not meet criteria):\n"
                        f"```\n- {discarded_names_str}\n```"
                        f"\n**AI's Raw Unique Suggestions (before any filtering):**\n"
                        f"```\n- {chr(10).join(discord.utils.escape_markdown(s_name) for s_name in sorted(list(all_ai_suggested_raw_names_global))) or 'None'}\n```"
                        f"\n**Final Matched Names:** {all_matched_igns_from_all_images if all_matched_igns_from_all_images else 'None'}"
                    )
                    if len(log_message_discarded) > 4000:
                        log_message_discarded = log_message_discarded[:4000] + "\n... (log truncated)"
                    error_embed_discarded = discord.Embed(
                        title="📝 AI Image Processing: Discarded Name Suggestions",
                        description=log_message_discarded,
                        color=discord.Color.orange() 
                    )
                    error_embed_discarded.timestamp = discord.utils.utcnow()
                    error_embed_discarded.set_footer(text=f"Message ID: {message.id} | User: {message.author.name}")
                    await log_to_channel(EXTRAORDINARY_LOGS_CHANNEL_ID, guild, embed=error_embed_discarded)
                    print(f"Logged discarded AI names to extraordinary logs: {discarded_by_cache_check}")

                # --- Process Activity Updates ---
                newly_added_details_for_view: List[Dict[str, Any]] = [] 
                already_active_today_for_view: List[str] = []
                failed_to_add_for_view: List[str] = []
                activity_changed = False

                if not all_matched_igns_from_all_images:
                    # Handle no names matched from AI
                    if ai_reported_no_names_at_least_once and not ai_extracted_some_text_globally:
                        final_user_message = f"{author.mention} AI analysis of {num_images} image(s) complete: No online player names (from our known list, with green dots) were clearly identified in any of the images."
                    elif not ai_extracted_some_text_globally and not ai_reported_no_names_at_least_once:
                        final_user_message = f"{author.mention} AI analysis ran into an issue or returned no usable data from any of the {num_images} image(s)."
                    else: 
                        final_user_message = f"{author.mention} AI analysis of {num_images} image(s) complete. Some text may have been identified, but it didn't match our known online In-Game Names list or meet all specified criteria (e.g., green dot for online status)."
                    
                    try:
                        await processing_reply.edit(content=final_user_message, allowed_mentions=discord.AllowedMentions(users=[author]), embed=None, view=None)
                    except discord.NotFound: 
                        print(f"Screenshot processing: 'processing_reply' (ID: {processing_reply.id}) not found for edit. Sending new followup to original message.")
                        await message.reply(final_user_message, allowed_mentions=discord.AllowedMentions(users=[author]))
                    except discord.HTTPException as e_edit_http:
                        await log_error(guild, f"Screenshot processing: HTTP error editing 'processing_reply' for no matched names.", error=e_edit_http, interaction=message)
                        await message.reply(final_user_message, allowed_mentions=discord.AllowedMentions(users=[author]))

                else:
                    # Iterate through matched IGNs to update activity
                    for ign_str in all_matched_igns_from_all_images:
                        ign_lower = ign_str.lower()
                        exists = await check_activity_exists(guild, ign_lower, activity_date)

                        if exists is True:
                            already_active_today_for_view.append(ign_str)
                        elif exists is False:
                            # Not active yet today, so try to upsert
                            success, upsert_msg = await upsert_activity_log(guild, ign_str, activity_date, author.id)
                            if success:
                                newly_added_details_for_view.append({'ign': ign_str, 'status': 'active_by_view'})
                                activity_changed = True
                            else:
                                failed_to_add_for_view.append(ign_str)
                                await log_error(guild, f"Screenshot activity: Failed to upsert activity for IGN '{ign_str}' from screenshot by {author.name}. DB Msg: {upsert_msg}")
                        else: # exists is None (DB check failed)
                            failed_to_add_for_view.append(ign_str)
                            await log_error(guild, f"Screenshot activity: DB check failed for IGN '{ign_str}' from screenshot by {author.name}.")
                    
                    # --- Create View and Final Embed ---
                    confirm_view = ScreenshotConfirmView(
                        original_author_id=author.id,
                        activity_date=activity_date,
                        newly_added_igns_details=newly_added_details_for_view,
                        already_active_igns=already_active_today_for_view,
                        failed_to_add_igns=failed_to_add_for_view,
                        guild_for_log=guild,
                        original_message_id=message.id
                    )
                    final_embed = confirm_view.create_embed()
                    
                    edited_message: Optional[discord.Message] = None
                    try:
                        edited_message = await processing_reply.edit(content=f"{author.mention}", embed=final_embed, view=confirm_view, allowed_mentions=discord.AllowedMentions(users=[author]))
                    except discord.NotFound: 
                        print(f"Screenshot processing: 'processing_reply' (ID: {processing_reply.id}) not found for edit. Sending new followup to original message.")
                        edited_message = await message.reply(content=f"{author.mention}", embed=final_embed, view=confirm_view, allowed_mentions=discord.AllowedMentions(users=[author]))
                    except discord.HTTPException as e_edit_http:
                        await log_error(guild, f"Screenshot processing: HTTP error editing 'processing_reply' with results.", error=e_edit_http, interaction=message)
                        edited_message = await message.reply(content=f"{author.mention}", embed=final_embed, view=confirm_view, allowed_mentions=discord.AllowedMentions(users=[author]))
                    
                    if edited_message: 
                        confirm_view.message = edited_message 

                    if activity_changed:
                        await log_info(guild, f"Screenshot by {author.name} processed. Newly active: {len(newly_added_details_for_view)}, Already active: {len(already_active_today_for_view)}. Triggering list update.")
                        asyncio.create_task(update_static_list_message(guild))
                    else:
                        await log_info(guild, f"Screenshot by {author.name} processed. No new activity recorded. Already active: {len(already_active_today_for_view)}.")

            except Exception as e_img_pipeline:
                print(f"Critical error during screenshot activity processing pipeline for message {message.id}: {e_img_pipeline}")
                traceback.print_exc() 
                await log_error(guild, "Critical error during screenshot activity processing", error=e_img_pipeline, ping_owner=True)
                critical_error_message_content = f"{author.mention} Sorry, a critical unexpected error occurred while processing the {num_images} image(s). Admins have been notified."
                try:
                    await processing_reply.edit(content=critical_error_message_content, allowed_mentions=discord.AllowedMentions(users=[author]), embed=None, view=None)
                except discord.NotFound:
                    print(f"Screenshot processing: 'processing_reply' (ID: {processing_reply.id}) not found for critical error edit. Sending new followup.")
                    await message.reply(critical_error_message_content, allowed_mentions=discord.AllowedMentions(users=[author]))
                except discord.HTTPException as e_edit_crit_http:
                    await log_error(guild, f"Screenshot processing: HTTP error editing 'processing_reply' for critical error.", error=e_edit_crit_http, interaction=message)
                    await message.reply(critical_error_message_content, allowed_mentions=discord.AllowedMentions(users=[author]))
                except Exception as e_final_send_crit:
                     print(f"Failed to send critical error message to user after pipeline failure: {e_final_send_crit}")
            return # Image processing handled.







    # --- 5. Auto-Delete Logic for HC_MEMBER_LIST_CHANNEL_ID ---
    if channel.id == HC_MEMBER_LIST_CHANNEL_ID:
        if message.interaction is not None and author.id == bot.user.id: # Message is an interaction response from the bot itself
            try:
                await message.delete(delay=AUTODELETE_DELAY_SECONDS)
            except discord.Forbidden:
                print(f"Failed to auto-delete message {message.id} in HC list channel: Missing Permissions.")
            except discord.NotFound:
                pass # Message was already deleted
            except Exception as e_del:
                print(f"Error auto-deleting message {message.id} in HC list channel: {e_del}")
            finally:
                return # Stop further processing for these auto-deleted messages



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
   
# --- Nerd Help Command (MODIFIED) ---
@tree.command(name="nerdhelp", description="Show the list of available bot commands.")
# REMOVED @app_commands.check(test_bot_owner_only_check)
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    if not bot or not bot.user:
        await interaction.response.send_message("Bot is not fully ready, cannot generate help.", ephemeral=False)
        return
    if not command_ids:
        print("Warning: command_ids dictionary is empty during nerdhelp execution! Links may not be clickable.")

    can_see_staff_commands = False
    if isinstance(interaction.user, discord.Member):
        can_see_staff_commands = await can_manage_guild_or_is_bypass_user(interaction)

    # Create the view instance
    view_instance = HelpPagesView(bot_user=bot.user, is_staff_view_allowed=can_see_staff_commands)
    
    # If the user cannot see staff commands, we effectively want no buttons.
    # We achieve this by clearing items from the view instance if it's not allowed.
    # The HelpPagesView's button is defined by a decorator, so it's always part of its potential children.
    if not can_see_staff_commands:
        view_instance.clear_items() # Remove the decorated button if not allowed to use it

    # The button's initial appearance is set by the decorator (View Staff Commands)
    # This is correct as the initial page is 'general'.
    initial_embed = view_instance.get_current_embed()


    try:
        # Send the view. If view_instance.children is empty, Discord handles it as no components.
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
        except Exception: pass

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
