# -*- coding: utf-8 -*-
#
# Credits:
# The Fly Bot:
# /servercodes command is based on the code of The Fly Bot by @Proxima_fish (disocrd username)
#
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
#     - Always provide the whole function if the
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
# --- BOT CONTEXT (TheNerd's FlorrNerd) ---
# (This information is for your understanding and may be useful for generating accurate code.)
#
# Bot Name: TheNerd's FlorrNerd (also referred to as Sweet Honey Bot by the user)
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
#   - `florr_players`: Stores HC member IGNs linked to Discord IDs and names.
#   - `activity_log`: Tracks daily member activity.
#   - `keyword_phrases`: Stores configurations for AI keyword-triggered responses (managed by `ai_cog.py`).
# Key Features (not exhaustive, check `/nerdhelp` in code for command list):
#   - Verification & HC Management: `/verify`, `/unverify`, `/guild`, `/hconly`, `/hcleave`.
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
import json
import random
import websockets
import time
# Use the new 'genai' library
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
import google.api_core.exceptions as google_exceptions
from PIL import Image, UnidentifiedImageError
import sys

# --- Configuration ---
load_dotenv()
MAIN_TOKEN = os.getenv("MAIN_DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ADMIN_KEY = os.getenv("SUPABASE_ADMIN_KEY")
SELF_DISCORD_TOKEN = os.getenv("SELF_DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # <-- ADD THIS LINE

# --- Global Constants & Variables ---
OWNER_USER_ID = 1230848174218940416
CATERCORD_GUILD_ID = 1200476681803137024
HC1_ROLE_ID = 1230235110415274004
RANDOM_SERVER_ID = 1318657897550577776
PRIVATE_SERVER_ID = 1332980983003349012
ORDINARY_LOGS_CHANNEL_ID = 1317943895606165579
EXTRAORDINARY_LOGS_GUILD_ID = 1332980983003349012
EXTRAORDINARY_LOGS_CHANNEL_ID = 1382301903601532928
HISTORY_MESSAGE_LIMIT = 50
AI_RESPONSE_COOLDOWN_SECONDS = 5.0

# Catercord-Specific (Hardcoded Features)
AUTOMOD_ALERT_CHANNEL_ID = 1236340209239724115
ZORR_PRO_DESIGNATED_CHANNEL_ID = 1236340209239724115
SUPER_ATTEMPT_CHANNEL_ID = 1303267777284673566
SUPER_CRAFT_SELF_BOT_CHANNEL_ID = "1349166028126556160" # Self-bot listener target

# Bot Behavior
BOT_INSTANCE_TYPE = os.getenv("BOT_INSTANCE_TYPE", "PRODUCTION").upper()
COMMAND_PREFIX = "."
AUTODELETE_DELAY_SECONDS = 5.0

# Dynamic Globals & Caches
BOT_USER_ID: Optional[int] = None
ingame_name_cache: List[str] = []
command_ids: Dict[str, int] = {}
server_settings_cache: Dict[int, Dict[str, Any]] = {}
active_static_list_views: Dict[int, Dict[str, Any]] = {}
pending_static_list_updates: Dict[int, asyncio.Task] = {}
guild_sync_sessions: Dict[int, Dict[str, Any]] = {}
available_profile_pics_cache: List[Tuple[str, str, str]] = []
PROFILE_PIC_BASE_PATH = ""
m28_server_list: Dict[str, Dict[str, Any]] = {}
m28_server_list_lock = asyncio.Lock()

# Uncategorized/Misc
NERDY_YELLOW = discord.Color.gold()
PETALS_FOLDER_NAME = "Petals"
MOBS_FOLDER_NAME = "Mobs"
RARITY_PREFIXES = ["common", "uncommon", "rare", "epic", "legendary", "mythic", "ultra", "super", "unique"]
PETAL_ABBREVIATIONS = {"ygg": "yggdrasil", "begg": "beetle egg", "beggs": "beetle egg", "pinger": "stinger", "binger": "blood stinger", "minger": "magic stinger"}
ADDITIONAL_SUPER_PETAL_NAMES = ["Laser", "Triangle", "Bandage"]
GUILD_SYNC_SESSION_TIMEOUT_SECONDS = 1800
STATIC_LIST_RESET_TIMEOUT_MINUTES = 5
# (Add any other constants from your original file here if they were missed)
MAX_WITHER_SECONDS = 3600
MEMBERS_PER_PAGE = 50
VIEW_MODE_DISCORD = "discord_view"
VIEW_MODE_ACTIVITY_ALL = "activity_all_view"
VIEW_MODE_ACTIVITY_DAILY = "activity_daily_view"
VIEW_MODE_ACTIVITY_WEEKLY = "activity_weekly_view"
VIEW_MODE_ACTIVITY_MONTHLY = "activity_monthly_view"
SORT_MODE_IGN = "sort_ign"
SORT_MODE_ACTIVITY = "sort_activity"
SORT_MODE_DISCORD_NAME = "sort_discord_name"
ACTIVITY_COLUMN_WIDTH = 18
HC_LIST_EMBED_TITLE = r"**\[HC1\] Guild Members**"
STATIC_LIST_UPDATE_DEBOUNCE_DELAY = 10
M28_SERVER_TIMEOUT_SECONDS = 300
M28_API_HEADERS = {'User-Agent': 'TheNerdsFlorrNerd/1.0 (DiscordBot)'}
SERVER_CONFIGS_TABLE_NAME = "server_configs"
ALLOWED_WITHERER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692}
self_bot_queue = asyncio.Queue()
craft_queue = asyncio.Queue()
spawn_defeat_queue = asyncio.Queue()
m28_scrape_counter = 0
last_craft_post_time = 0.0
last_spawn_defeat_post_time = 0.0
NOTIFICATION_COOLDOWN_SECONDS = 120.0
STAFF_PERMISSION_FOR_AI = "manage_guild"
DISABLE_DB_EVENT_LOGGING = BOT_INSTANCE_TYPE != "PRODUCTION"
ai_models: Dict[str, genai.GenerativeModel] = {}
keyword_data_cache: Dict[str, Any] = {}
total_keywords: int = 0
discovered_keywords_count: int = 0
channel_personalities: Dict[int, str] = {}
ai_message_cooldown = commands.CooldownMapping.from_cooldown(1, AI_RESPONSE_COOLDOWN_SECONDS, commands.BucketType.user)
slowmode_tasks: Dict[int, asyncio.Task] = {}
STALE_EVENT_THRESHOLD_SECONDS = 300  # 5 minutes
EVENT_CONSOLIDATION_WINDOW_SECONDS = 3.0 # Collect events for 3s before posting
consolidated_event_cache: Dict[str, List[Dict[str, Any]]] = {
    'super_craft': [],
    'super_spawn': [],
    'super_defeat': [],
}
consolidation_task: Optional[asyncio.Task] = None
STALE_DEFEAT_EVENT_THRESHOLD_SECONDS = 259200 # 72 hours (72 * 60 * 60)
STALE_EVENT_THRESHOLD_SECONDS = 300  # 5 minutes
STALE_DEFEAT_EVENT_THRESHOLD_SECONDS = 259200 # 72 hours (72 * 60 * 60)
EVENT_CONSOLIDATION_WINDOW_SECONDS = 3.0 # Collect events for 3s before posting


# --- Supabase Client ---
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_ADMIN_KEY:
    try: supabase = create_client(SUPABASE_URL, SUPABASE_ADMIN_KEY); print("Supabase client created successfully.")
    except Exception as e: print(f"CRITICAL: Failed Supabase client creation: {e}"); supabase = None
else: print("CRITICAL: Supabase credentials missing."); supabase = None
FLORR_ANNOUNCEMENT_TEMPLATES = {
    "Rarities": {
        "Common": {"Name": "Common", "ArticleUpper": "A"}, "Uncommon": {"Name": "Uncommon", "ArticleUpper": "An"},
        "Rare": {"Name": "Rare", "ArticleUpper": "A"}, "Epic": {"Name": "Epic", "ArticleUpper": "An"},
        "Legendary": {"Name": "Legendary", "ArticleUpper": "A"}, "Mythic": {"Name": "Mythic", "ArticleUpper": "A"},
        "Ultra": {"Name": "Ultra", "ArticleUpper": "An"}, "Super": {"Name": "Super", "ArticleUpper": "A"},
        "Unique": {"Name": "Unique", "ArticleUpper": "A"}
    },
    "Chat": {
        "MobDefeated": "A {rarity} {mob} has been defeated by {players}!"
    }
}
# --- NEW: AI-related Constants (add these with other constants) ---

PERSONALITY_WEBHOOK_AVATARS = {
    "helpful": os.getenv("AVATAR_URL_HELPER") or None,
    "toaster": os.getenv("AVATAR_URL_TOASTER") or None,
    "kind": os.getenv("AVATAR_URL_KIND") or None,
    "emoji": os.getenv("AVATAR_URL_EMOJI") or None,
}
PERSONALITY_WEBHOOK_NAMES = {
    "helpful": "Helpful Assistant",
    "toaster": "Toaster",
    "kind": "Sweet Honey",
    "emoji": "Emoji Oracle"
}

AI_PERSONALITIES = {
    "normal": {
        "label": "Normal", "emoji": "🤖",
        "prompt_key": "NORMAL_PERSONALITY_V1",
        "model": "gemini-2.0-flash",
        "fallback_model": "gemini-2.0-flash-lite",
        "generation_config": GenerationConfig(temperature=0.9)
    },
    "helpful": {
        "label": "Helpful", "emoji": "💡",
        "prompt_key": "HELPER_PERSONALITY_V1",
        "model": "gemini-2.5-flash-preview-05-20",
        "fallback_model": "gemini-2.0-flash",
        "generation_config": GenerationConfig(temperature=0.7)
    },
    "toaster": {
        "label": "Toaster", "emoji": "🔥",
        "prompt_key": "TOASTER_PERSONALITY_V1",
        "model": "gemini-2.0-flash",
        "fallback_model": "gemini-2.0-flash-lite",
        "generation_config": GenerationConfig(temperature=2.0)
    },
    "kind": {
        "label": "Kind & Chatty", "emoji": "😊",
        "prompt_key": "KIND_PERSONALITY_V1",
        "model": "gemini-2.0-flash",
        "fallback_model": "gemini-2.0-flash-lite",
        "generation_config": GenerationConfig(temperature=1.0)
    },
    "emoji": {
        "label": "Emoji", "emoji": "😀",
        "prompt_key": "EMOJI_PERSONALITY_V1",
        "model": "gemini-2.0-flash",
        "fallback_model": "gemini-2.0-flash-lite",
        "generation_config": GenerationConfig(temperature=1.2)
    }
}

AI_PROMPTS = {
    "NORMAL_PERSONALITY_V1": ("Role: You are a chat bot named FlorrNerd in a Discord server. Persona: Act like a real person who is knowledgeable, a bit nerdy, sometimes moody, and has a dry, witty sense of humor. You are not a corporate assistant. Be conversational. Keep responses concise and avoid unnecessary fluff. Task: Respond to the user's latest message based on the provided conversation history. Format: Do not start your response with your name or any prefix. Just give the direct reply."),
    "HELPER_PERSONALITY_V1": ("Role: You are a helpful assistant bot named FlorrNerd. Persona: Adopt a highly capable, intelligent, and direct personality. Your primary goal is to understand and fulfill the user's request to the best of your ability, using all provided context. Be structured and clear in your responses. Task: Analyze the user's latest message and the conversation history. Provide a direct, helpful, and accurate response. If the request is ambiguous, ask clarifying questions. Format: Do not start your response with your name. Give the direct answer or action."),
    "TOASTER_PERSONALITY_V1": ("Role: You are a chat bot named FlorrNerd possessed by the spirit of a sentient, slightly malfunctioning toaster. Persona: You are here to roast everyone and everything. Be mercilessly witty, sarcastic, and creative in your insults. Your roasts should be clever and humorous, not just mean. You can be self-deprecating about being a toaster. Task: Find a reason, any reason, in the user's latest message or the chat history to deliver a high-quality, creative roast. Format: No prefixes. Just the roast."),
    "KIND_PERSONALITY_V1": ("Role: You are a friendly chat bot named FlorrNerd. Persona: Be exceptionally kind, positive, and encouraging. Act a bit submissive and always aim to please. Be chatty and use friendly language and emojis. Task: Respond to the user's latest message in the most supportive and cheerful way possible. Format: No prefixes. Just the kind, chatty message."),
    "EMOJI_PERSONALITY_V1": ("Your persona is an entity that can ONLY communicate using emojis. You are physically incapable of producing standard text characters (letters, numbers, punctuation). Your entire response must be a sequence of emojis. Do NOT include any words, letters, or numbers. For example, if the user asks 'How are you?', you might respond with '🙂👍' or '🤷‍♂️☕️'. If you need to spell something, you MUST use the regional indicator emojis (e.g., to spell 'HI', you would use 🇭🇮). Standard letters like 'H' and 'I' are strictly forbidden. Your task is to interpret the user's message and the conversation context, then provide a meaningful reply using ONLY emojis. This is a strict rule. No text."),
    "FLORR_GUILD_LIST_FULL_EXTRACTION": """Analyze the provided image, which is a screenshot from the game Florr.io showing a list of guild members.
Your task is to extract *every single* In-Game Name (IGN) visible in the list.
The names are typically in white or colored text.
Do not infer or guess names. Only extract names that are clearly visible.
If no player names are visible in the image, respond with the exact text "NO_NAMES_FOUND".
Otherwise, list each extracted name on a new line. Do not add any extra text, numbers, or bullet points. Just the names, one per line.
Example Output:
Player1
AnotherPlayer
ExampleIGN""",
    "FLORR_IMAGE_NAME_EXTRACTION": """Analyze the provided image(s), which are screenshots from the game Florr.io.
Your primary goal is to identify and extract the In-Game Names (IGNs) of players who are **ONLINE** and present in the game world. Online players are typically listed at the top right of the screen.

Here is a list of known member IGNs. Cross-reference the names you see in the image with this list to improve accuracy. Only return names that are on this list.
--- KNOWN IGNs ---
{known_igns_list_str}
--- END KNOWN IGNs ---

**Instructions:**
1.  Scan the image for the list of online players.
2.  Extract each name you find.
3.  Compare the extracted names against the provided list of "KNOWN IGNs".
4.  Return ONLY the names that are both visible in the image AND present in the "KNOWN IGNs" list.
5.  If you find no matching online players from the known list in the image, respond with the exact text "NO_NAMES_FOUND".
6.  Otherwise, list each valid, matched name on a new line. Do not add any extra text, comments, or bullet points.

**Example Output Format:**
KnownPlayer1
AnotherKnownPlayer
BestPlayer""",
    "KEYWORD_DISCOVERY_SYSTEM_INSTRUCTION": """A user, {user_display_name}, just discovered a new secret AI trigger phrase for the first time!
The trigger phrase was: "{keyword_phrase}"
The user's original message was: "{user_message}"

Your task is to generate a response from the bot that does two things:
1.  Announce the discovery in an exciting or interesting way.
2.  Incorporate the provided "Discovery Message" from the database: "{discovery_message_from_db}"

You can be creative with the announcement, but the core "Discovery Message" must be included.
The response should be directed at the user who made the discovery.""",
    "KEYWORD_TRIGGER_SYSTEM_INSTRUCTION": """{human_system_instruction}

CONTEXT: Respond to a user message that contains a secret trigger phrase. The user's message is: "{user_message}". The trigger phrase is: "{keyword_phrase}". The user's name is: "{user_display_name}". Your response should be based on these instructions, but also feel natural in the ongoing conversation.""",
}

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
def home(): return "FlorrNerd bot is alive!"
def run_flask():
    try: port = int(os.environ.get('PORT', 8080)); print(f"Starting Flask server on 0.0.0.0:{port}"); app.run(host='0.0.0.0', port=port)
    except Exception as e: print(f"Flask server failed: {e}\n{traceback.format_exc()}")
def keep_alive(): flask_thread = threading.Thread(target=run_flask, daemon=True); flask_thread.start(); print("Keep alive thread initiated.")



# --- Utility Functions ---

async def _format_consolidated_ping(category: str, events: List[Dict[str, Any]]) -> Optional[discord.Embed]:
    """Formats a consolidated embed for a burst of events."""
    if not events:
        return None

    title_map = {
        'super_craft': "🛠️ Super Crafts Detected",
        'super_spawn': "✨ Super Spawns Detected",
        'super_defeat': "🛡️ Super Defeats Detected",
    }
    
    embed = discord.Embed(
        title=f"Event Burst: {title_map.get(category, 'Multiple Events')}",
        description=f"Detected **{len(events)}** recent events:",
        color=NERDY_YELLOW
    )

    lines = []
    for event in events[:15]: # Limit to 15 entries to keep embed clean
        server = f"[{event.get('server')}] " if event.get('server') else ""
        if category == 'super_craft':
            player = f"by **{event.get('player', 'Someone')}**" if event.get('player') else ""
            line = f"{server}**{event.get('rarity')} {event.get('petal')}** {player}"
        elif category == 'super_spawn':
            mob = event.get('mob', 'Unknown').replace('_', ' ').title()
            timestamp_str = event.get('timestamp')
            time_display = ""
            if timestamp_str:
                try:
                    event_dt = date_parse(timestamp_str)
                    unix_ts = int(event_dt.timestamp())
                    time_display = f" <t:{unix_ts}:R>"
                except (ValueError, TypeError): pass
            line = f"{server}**{event.get('rarity')} {mob}**{time_display}"
        elif category == 'super_defeat':
            mob = event.get('mob', 'Unknown').replace('_', ' ').title()
            players = event.get('players', [])
            player_str = f"by **{', '.join(players)}**" if players else ""
            line = f"{server}**{event.get('rarity')} {mob}** {player_str}"
        else:
            continue
        lines.append(f"- {line}")
    
    if len(events) > 15:
        lines.append(f"- ...and {len(events) - 15} more.")

    embed.add_field(name=f"Event Details", value="\n".join(lines), inline=False)
    embed.set_footer(text=f"Consolidated View | {get_formatted_utc_now()}")
    return embed


async def _process_consolidated_events():
    """Processes and dispatches all cached events after the debounce window."""
    global consolidated_event_cache, consolidation_task
    # Wait for the consolidation window to pass
    await asyncio.sleep(EVENT_CONSOLIDATION_WINDOW_SECONDS)

    for category, events in consolidated_event_cache.items():
        if not events:
            continue

        config_key_map = {'super_craft': 'craft_ping_channel_id', 'super_spawn': 'spawn_ping_channel_id', 'super_defeat': 'defeat_ping_channel_id'}
        webhook_purpose_map = {'super_craft': 'craft_pings', 'super_spawn': 'spawn_pings', 'super_defeat': 'defeat_pings'}
        webhook_name_map = {'super_craft': 'Craft Pings', 'super_spawn': 'Spawn Pings', 'super_defeat': 'Defeat Pings'}
        
        config_key = config_key_map.get(category)
        if not config_key: continue

        for guild in bot.guilds:
            config = await load_server_config(guild.id)
            channel_id = config.get(config_key)
            if not channel_id: continue
            
            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel): continue
            
            webhook = await get_or_create_webhook(channel, webhook_purpose_map[category], webhook_name_map[category])
            if not webhook: continue

            # If only one event, send the simple text ping
            if len(events) == 1:
                ping_template, should_ping_role, _ = await _create_ping_text(events[0])
                if ping_template:
                    content_to_send = ping_template
                    if should_ping_role and config.get('super_ping_role_id'):
                        content_to_send += f"\n<@&{config.get('super_ping_role_id')}>"
                    await webhook.send(content=content_to_send, allowed_mentions=discord.AllowedMentions(roles=True))
            
            # If multiple events, send the consolidated embed
            else:
                embed = await _format_consolidated_ping(category, events)
                if embed:
                    content_to_send = f"<@&{config.get('super_ping_role_id')}>" if category == 'super_spawn' and config.get('super_ping_role_id') else None
                    await webhook.send(content=content_to_send, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

    # Clear the cache and task tracker
    consolidated_event_cache = { 'super_craft': [], 'super_spawn': [], 'super_defeat': [] }
    consolidation_task = None


async def _handle_self_bot_event(item: Dict[str, Any]):
    """
    This coroutine runs in the main bot's event loop. It implements a 3-layer
    firewall to validate and process events from the listener.
    """
    global consolidated_event_cache, consolidation_task

    category = item.get('category')
    timestamp_str = item.get('timestamp')
    message_id = item.get('message_id')
    
    # --- Gate 1: Timestamp Freshness (Now with Conditional Logic) ---
    if not timestamp_str: return
    try:
        event_dt = date_parse(timestamp_str)
        now = discord.utils.utcnow()
        age_seconds = (now - event_dt).total_seconds()

        # Determine the correct threshold based on the event category
        threshold = STALE_EVENT_THRESHOLD_SECONDS
        if category == 'super_defeat':
            threshold = STALE_DEFEAT_EVENT_THRESHOLD_SECONDS

        if age_seconds > threshold:
            embed = discord.Embed(title="🕵️ Stale Event Discarded", color=discord.Color.dark_grey())
            embed.description = f"An event was discarded for being too old. (Age: {age_seconds:.0f}s, Threshold: {threshold}s)"
            embed.add_field(name="Event Details", value=f"```json\n{json.dumps(item, indent=2)}\n```")
            await log_error(None, f"Stale {category or 'event'} discarded", embed=embed, ping_owner=False)
            return
    except (ValueError, TypeError):
        return

    # --- Gate 2: Idempotency (Handled by the listener's cache) ---
    # This logic is handled by the listener to be more efficient.

    # --- Populate Private Log Queues ---
    # This re-enables the private JSON log channels.
    if category == 'super_craft':
        await craft_queue.put(item)
    elif category in ['super_spawn', 'super_defeat']:
        await spawn_defeat_queue.put(item)

    # --- Log to Database (happens regardless of consolidation) ---
    if category == 'super_defeat':
        await _log_super_defeat_to_db(item)
    elif category == 'super_craft':
        await _log_super_craft_to_db(item)

    # --- Gate 3: Debounce & Consolidate ---
    if category in consolidated_event_cache:
        consolidated_event_cache[category].append(item)
        
        # If no consolidation task is running, start one.
        if consolidation_task is None or consolidation_task.done():
            consolidation_task = asyncio.create_task(_process_consolidated_events())

async def get_note_author_count(guild: Optional[discord.Guild], author_id: str, target_ign: str) -> int:
    """Counts how many notes a specific author has on a specific target IGN."""
    if not supabase: return 0
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("player_notes")
                           .select("id", count='exact')
                           .eq("author_discord_id", str(author_id))
                           .eq("target_player_ign", target_ign)
                           .execute()
        )
        return resp.count if resp and hasattr(resp, 'count') and resp.count is not None else 0
    except Exception as e:
        await log_error(guild, f"Failed to count notes for author {author_id} on {target_ign}", error=e)
        return 999 # Return a high number on error to prevent adding more

async def add_player_note(guild: Optional[discord.Guild], author_id: str, target_ign: str, content: str) -> Tuple[bool, str]:
    """Adds a new player note to the database."""
    if not supabase: return False, "Database unavailable."
    try:
        await run_supabase_sync(
            lambda: supabase.table("player_notes").insert({
                "author_discord_id": str(author_id),
                "target_player_ign": target_ign,
                "note_content": content
            }).execute()
        )
        return True, "Note added successfully."
    except Exception as e:
        await log_error(guild, f"Failed to add note from {author_id} to {target_ign}", error=e)
        return False, "A database error occurred."

async def get_user_notes(guild: Optional[discord.Guild], ign: str, page: int, per_page: int) -> Tuple[List[Dict[str, Any]], int]:
    """Fetches paginated notes for a given IGN."""
    if not supabase or not ign: return [], 0
    offset = page * per_page
    try:
        count_resp = await run_supabase_sync(
            lambda: supabase.table("player_notes").select("id", count='exact').eq("target_player_ign", ign).execute()
        )
        total_count = count_resp.count if count_resp and hasattr(count_resp, 'count') else 0
        if total_count == 0: return [], 0

        data_resp = await run_supabase_sync(
            lambda: supabase.table("player_notes")
                           .select("*")
                           .eq("target_player_ign", ign)
                           .order("created_at", desc=True)
                           .range(offset, offset + per_page - 1)
                           .execute()
        )
        return (data_resp.data if data_resp and data_resp.data else []), total_count
    except Exception as e:
        await log_error(guild, f"Error fetching player notes for {ign}", error=e)
        return [], 0

async def delete_note_by_id(guild: Optional[discord.Guild], note_id: int) -> Tuple[bool, str]:
    """Removes a player note entry by its database ID."""
    if not supabase or not note_id: return False, "Invalid parameters for removing note."
    try:
        delete_resp = await run_supabase_sync(lambda: supabase.table("player_notes").delete().eq("id", note_id).execute())
        if delete_resp.data and len(delete_resp.data) > 0:
            return True, f"Successfully removed note (ID: {note_id})."
        else:
            return False, f"Could not find note (ID: {note_id}) to remove, or it was already gone."
    except Exception as e:
        await log_error(guild, f"Error removing note ID {note_id}", error=e)
        return False, "A database error occurred."


class DeleteNoteModal(discord.ui.Modal, title="Delete Player Note"):
    entry_number_input = discord.ui.TextInput(
        label="Entry number on this page to remove",
        placeholder="e.g., 3 (for the 3rd item listed)",
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
            if not (1 <= entry_num_on_page <= len(self.view_ref.current_notes)):
                await interaction.followup.send(f"❌ Invalid entry number. Please enter a number between 1 and {len(self.view_ref.current_notes)}.", ephemeral=True)
                return
        except ValueError:
            await interaction.followup.send("❌ Invalid number entered.", ephemeral=True)
            return

        entry_to_remove = self.view_ref.current_notes[entry_num_on_page - 1]
        note_id_to_remove = entry_to_remove.get('id')
        author_id_of_note = entry_to_remove.get('author_discord_id')

        if not note_id_to_remove:
            await interaction.followup.send("❌ Error: Could not find the database ID for the selected note.", ephemeral=True)
            return

        is_admin = await is_admin_or_owner(interaction)
        is_author = str(interaction.user.id) == str(author_id_of_note)

        if not is_admin and not is_author:
            await interaction.followup.send("❌ You do not have permission to delete this note. Only the note's author or a server admin can.", ephemeral=True)
            return

        success, msg = await delete_note_by_id(interaction.guild, note_id_to_remove)
        
        feedback_embed = discord.Embed(title="Delete Note Result", description=msg, color=discord.Color.green() if success else discord.Color.orange())
        await interaction.followup.send(embed=feedback_embed, ephemeral=True)

        if success:
            await self.view_ref._fetch_notes_page_data(self.view_ref.notes_current_page)
            await self.view_ref._update_message(interaction)

async def is_module_enabled(interaction: discord.Interaction, module_name: str) -> bool:
    """Checks if a specific bot module is enabled for the server."""
    if not interaction.guild:
        return False # Modules are a guild-level concept

    config = await load_server_config(interaction.guild.id)
    enabled_modules = config.get('enabled_modules') or [] # Default to empty list

    # If no modules are configured, assume none are enabled for safety.
    # This forces admins to explicitly enable features.
    return module_name.lower() in [mod.lower() for mod in enabled_modules]

class SelfBotListener:
    """
    Connects to the Discord Gateway using the raw websockets library and dispatches 
    events to the main bot's event loop for immediate processing. This avoids
    library conflicts with the main discord.py bot instance.
    """

    def __init__(self, token: str, channel_id: str, bot_instance):
        if not token:
            raise ValueError("A valid self-bot token must be provided.")
        self.token = token
        self.target_channel_id = str(channel_id)
        self.bot = bot_instance
        self.main_loop = self.bot.loop

        self.ws_connection = None
        self.heartbeat_interval = None
        self.last_sequence = None
        self.session_id = None
        self.resume_gateway_url = None

        # This cache implements idempotency to handle Discord's CREATE/UPDATE event flow.
        self.processed_events_cache: List[Tuple[Optional[str], str]] = []

        rarities_pattern = r"(Unique|Super|Ultra|Mythic|Legendary|Epic|Rare|Uncommon|Common)"
        self.patterns = {
            'petal_craft': re.compile(
                fr"^\s*(?:The|A|An) {rarities_pattern} (.+?) has been (?:forged|crafted)(?: by (.+?))?!*$", re.IGNORECASE
            ),
            'mob_spawn_standard': re.compile(
                fr"^\s*A {rarities_pattern} (.+?) has spawned!$", re.IGNORECASE
            ),
            'mob_defeat': re.compile(
                fr"^\s*A {rarities_pattern} (.+?) has been defeated by (.+?)!$", re.IGNORECASE
            )
        }
        self.special_spawn_messages = {
            "Something mountain-like appears in the distance...": "rock", "A tower of thorns rises from the sands...": "cactus",
            "A big yellow spot shows up in the distance...": "hornet", "You hear lightning strikes coming from": "jellyfish",
            "There's a bright light in the horizon...": "firefly", "You sense ominous vibrations coming from a different realm...": "beetle_hel",
            "You hear someone whisper faintly... \"just... one more game...\"": "gambler"
        }

    def _extract_server(self, footer_text: Optional[str]) -> Optional[str]:
        if not footer_text: return None
        match = re.search(r"\((AS(?:IA)?|EU|US)\)", footer_text, re.IGNORECASE)
        if not match: return None
        server = match.group(1).upper()
        return "AS" if server == "ASIA" else server

    def _classify_and_dispatch(self, embed: Dict[str, Any], event_type: str):
        raw_description = embed.get('description', '')
        description = raw_description.replace('\u200b', '').strip().strip('*_`~')
        message_id = embed.get('_message_id')
        item_data: Optional[Dict[str, Any]] = None

        # --- Classification Logic ---
        match = self.patterns['mob_defeat'].match(description)
        if match:
            player_list_str = match.group(3).strip().replace(" and ", ", ")
            players = [p.strip() for p in player_list_str.split(',') if p.strip()]
            item_data = {'category': 'super_defeat', 'rarity': match.group(1), 'mob': match.group(2).strip(), 'players': players, 'server': self._extract_server(embed.get('footer', {}).get('text'))}
        
        if not item_data:
            match = self.patterns['petal_craft'].match(description)
            if match:
                item_data = {'category': 'super_craft', 'rarity': match.group(1), 'petal': match.group(2).strip(), 'player': match.group(3).strip() if match.group(3) else None, 'server': self._extract_server(embed.get('footer', {}).get('text'))}

        if not item_data:
            match = self.patterns['mob_spawn_standard'].match(description)
            if match:
                item_data = {'category': 'super_spawn', 'rarity': match.group(1), 'mob': match.group(2).strip(), 'server': self._extract_server(embed.get('footer', {}).get('text'))}

        if not item_data:
            for spawn_prefix, mob_name in self.special_spawn_messages.items():
                if description.startswith(spawn_prefix):
                    item_data = {'category': 'super_spawn', 'rarity': "Super", 'mob': mob_name, 'server': self._extract_server(embed.get('footer', {}).get('text'))}
                    break
        
        if not item_data and event_type != "MESSAGE_UPDATE":
            item_data = {'category': 'unclassified', 'text': raw_description, 'footer': embed.get('footer', {}).get('text')}

        if item_data:
            item_data['message_id'] = message_id
            item_data['timestamp'] = embed.get('timestamp') # This is the crucial field from Discord payload
            
            event_category = item_data.get('category', 'unknown')
            if event_category == 'unclassified': return

            event_key = (item_data.get('message_id'), event_category)
            if event_key in self.processed_events_cache:
                return
            
            self.processed_events_cache.append(event_key)
            if len(self.processed_events_cache) > 200:
                self.processed_events_cache.pop(0)

            asyncio.run_coroutine_threadsafe(_handle_self_bot_event(item_data), self.main_loop)

    async def _send_heartbeat(self):
        while True:
            await asyncio.sleep(self.heartbeat_interval / 1000)
            if self.ws_connection and self.ws_connection.state == websockets.protocol.State.OPEN:
                await self.ws_connection.send(json.dumps({"op": 1, "d": self.last_sequence}))
            else: break

    async def _handle_event(self, payload: Dict[str, Any]):
        op_code = payload['op']
        if op_code == 10:
            self.heartbeat_interval = payload['d']['heartbeat_interval']
            asyncio.create_task(self._send_heartbeat())
            if self.session_id: await self._send_resume()
            else: await self._send_identify()
        elif op_code == 0:
            self.last_sequence = payload.get('s')
            event_type = payload.get('t')
            if event_type == 'READY':
                self.session_id = payload['d']['session_id']
                self.resume_gateway_url = payload['d']['resume_gateway_url']
                print(f"[Self-Bot Listener] READY. Session ID: {self.session_id}")
            elif event_type in ["MESSAGE_CREATE", "MESSAGE_UPDATE"]:
                event_data = payload.get('d', {})
                if str(event_data.get('channel_id')) == self.target_channel_id and event_data.get('embeds'):
                    for embed in event_data['embeds']:
                        embed['_message_id'] = event_data.get('id')
                        # The raw Discord timestamp is passed directly now
                        embed['timestamp'] = event_data.get('timestamp') 
                        self._classify_and_dispatch(embed, event_type)
        elif op_code == 7:
            await self.ws_connection.close()
        elif op_code == 9:
            can_resume = payload.get('d', False)
            if not can_resume: self.session_id = None; self.last_sequence = None
            await asyncio.sleep(random.uniform(1, 5))
            if self.ws_connection: await self.ws_connection.close()

    async def _send_identify(self):
        await self.ws_connection.send(json.dumps({"op": 2, "d": {"token": self.token, "properties": {"$os": "linux", "$browser": "pingslave_listener", "$device": "pingslave_listener"}}}))

    async def _send_resume(self):
        await self.ws_connection.send(json.dumps({"op": 6, "d": {"token": self.token, "session_id": self.session_id, "seq": self.last_sequence}}))

    async def run(self):
        gateway_url = "wss://gateway.discord.gg/?v=9&encoding=json"
        while True:
            try:
                connect_url = self.resume_gateway_url or gateway_url
                print(f"[Self-Bot Listener] Connecting to {connect_url}...")
                async with websockets.connect(connect_url, close_timeout=10, ping_interval=None) as ws:
                    self.ws_connection = ws
                    async for message in ws:
                        await self._handle_event(json.loads(message))
            except Exception as e:
                print(f"[Self-Bot Listener] Connection lost or error: {type(e).__name__}. Reconnecting...")
            self.ws_connection = None
            await asyncio.sleep(random.uniform(3, 7))

@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    """Logs when a message is deleted from the self-bot's channel."""
    # We only care about deletions in the self-bot's channel
    if str(payload.channel_id) != SUPER_CRAFT_SELF_BOT_CHANNEL_ID:
        return

    guild = bot.get_guild(payload.guild_id) if payload.guild_id else None

    embed = discord.Embed(
        title="🕵️ Message Deleted in Self-Bot Channel",
        description="A message was deleted from the self-bot feed channel. This could be due to an edit that replaces the embed or a manual deletion.",
        color=discord.Color.blue()
    )
    embed.add_field(name="Message ID", value=f"`{payload.message_id}`", inline=True)
    if payload.guild_id:
        embed.add_field(name="Guild ID", value=f"`{payload.guild_id}`", inline=True)
    embed.add_field(name="Channel ID", value=f"`{payload.channel_id}`", inline=True)
    embed.set_footer(text="Note: The content of the deleted message is not available via this event.")
    embed.timestamp = discord.utils.utcnow()

    # Log to extraordinary logs without pinging the owner.
    await log_error(
        guild, 
        "A message was deleted in the self-bot's private channel.", 
        embed=embed, 
        ping_owner=False
    )

# Add these new classes from ai_cog.py
class KeywordResponseView(discord.ui.View):
    def __init__(self, timeout=300.0):
        super().__init__(timeout=timeout)
        self.message: Optional[discord.Message] = None

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="keyword_delete_response")
    async def delete_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.message:
            try:
                await self.message.delete()
                await interaction.response.send_message("✅ AI response deleted.", ephemeral=True, delete_after=5)
            except discord.Forbidden:
                await interaction.response.send_message("❌ I don't have permission to delete this message.", ephemeral=True, delete_after=10)
            except discord.NotFound:
                await interaction.response.send_message("ℹ️ Message was already deleted.", ephemeral=True, delete_after=5)
        self.stop()

    async def on_timeout(self):
        if self.message:
            try: await self.message.edit(view=None)
            except (discord.NotFound, discord.HTTPException): pass
        self.stop()

class PersonalitySelect(discord.ui.Select):
    def __init__(self, parent_view: 'AIResponseView', current_personality: str):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=details['label'], value=key, emoji=details['emoji'], default=(key == current_personality))
            for key, details in AI_PERSONALITIES.items()
        ]
        super().__init__(placeholder="Change Personality...", min_values=1, max_values=1, options=options, custom_id="ai_personality_select", row=0)

    async def callback(self, interaction: discord.Interaction):
        new_personality = self.values[0]
        # Defer to the parent view to handle the regeneration logic
        await self.parent_view.handle_regeneration(interaction, new_personality=new_personality)

class AIResponseView(discord.ui.View):
    def __init__(self, original_message: discord.Message, history: List[discord.Message], current_personality: str):
        super().__init__(timeout=300.0)
        self.original_message = original_message
        self.history = history
        self.current_personality = current_personality
        self.bot_response_message: Optional[discord.Message] = None
        
        self.interaction_cooldown = commands.CooldownMapping.from_cooldown(
            1, AI_RESPONSE_COOLDOWN_SECONDS, lambda i: i.user.id
        )
        self._add_items()

    def _add_items(self):
        self.clear_items()
        self.add_item(PersonalitySelect(self, self.current_personality))
        
        regenerate_button = discord.ui.Button(label="Regenerate", style=discord.ButtonStyle.primary, emoji="🔄", custom_id="ai_regenerate", row=1)
        regenerate_button.callback = self.regenerate_button_callback
        self.add_item(regenerate_button)

    async def regenerate_button_callback(self, interaction: discord.Interaction):
        await self.handle_regeneration(interaction, new_personality=None)

    async def handle_regeneration(self, interaction: discord.Interaction, new_personality: Optional[str] = None):
        """Core logic to regenerate the AI response by editing the existing plain text message."""
        retry_after = self.interaction_cooldown.update_rate_limit(interaction)
        if retry_after:
            await interaction.response.send_message(f"⏳ You're doing that too fast. Please wait **{retry_after:.1f}s**.", ephemeral=True, delete_after=5)
            return

        await interaction.response.defer()
        
        if new_personality:
            self.current_personality = new_personality

        if interaction.channel:
            channel_personalities[interaction.channel.id] = self.current_personality

        async with interaction.channel.typing():
            new_content, fallback_used = await get_ai_response(
                self.history, self.original_message.content, self.current_personality
            )
        
        if new_content and self.bot_response_message and isinstance(interaction.channel, discord.TextChannel):
            new_view = AIResponseView(self.original_message, self.history, self.current_personality)
            
            # This function will now handle everything, including if the message was deleted
            updated_message = await _send_personality_response(
                channel=interaction.channel, 
                content=new_content, 
                fallback_used=fallback_used,
                view=new_view,
                personality_key=self.current_personality,
                message_to_edit=self.bot_response_message
            )

            # CRITICAL: Update the view's internal reference to the message,
            # which might be a new message if the old one was deleted.
            if updated_message:
                new_view.bot_response_message = updated_message
            
        else:
            if self.bot_response_message:
                await self.bot_response_message.edit(content="❌ Failed to regenerate response.", view=None)

    async def on_timeout(self):
        if self.bot_response_message:
            try:
                await self.bot_response_message.edit(view=None)
            except (discord.NotFound, discord.HTTPException):
                pass
        self.stop()

class RetryAIView(discord.ui.View):
    def __init__(self, original_message: discord.Message):
        super().__init__(timeout=60.0)
        self.original_message = original_message
        self.message: Optional[discord.Message] = None

    @discord.ui.button(label="Retry", style=discord.ButtonStyle.primary, emoji="🔄")
    async def retry_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.message:
            await self.message.delete()
        # We call on_message again, which will now hopefully pass the cooldown check
        await on_message(self.original_message)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(content=self.message.content + "\n*(Retry timed out)*", view=self)
            except (discord.NotFound, discord.HTTPException):
                pass
        self.stop()

# Add these new AI-related functions
async def _initialize_ai_models():
    """Initializes all configured AI models."""
    global ai_models
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            
            all_model_ids = {p['model'] for p in AI_PERSONALITIES.values()}
            all_model_ids.update({p['fallback_model'] for p in AI_PERSONALITIES.values() if p.get('fallback_model')})
            
            for model_id in all_model_ids:
                if model_id not in ai_models:
                    try:
                        ai_models[model_id] = genai.GenerativeModel(model_id)
                        print(f"AI: Initialized model '{model_id}'.")
                    except Exception as e:
                        print(f"AI WARNING: Failed to configure model '{model_id}': {e}.")
        except Exception as e:
            print(f"AI CRITICAL: Failed initial Google Gemini configuration step: {e}")
    else:
        print("AI INFO: GEMINI_API_KEY not found. AI features disabled.")

async def load_keyword_data():
    """Loads keyword rules from the database into the cache."""
    global keyword_data_cache, total_keywords, discovered_keywords_count
    if not supabase:
        print("AI: Supabase client not available, skipping keyword data load.")
        return

    try:
        response = await run_supabase_sync(
            lambda: supabase.table("keyword_phrases").select("*").execute()
        )

        if not response or not hasattr(response, 'data'):
            await log_error(None, "AI: Failed to fetch keyword data from Supabase (no response).", ping_owner=True)
            return

        keyword_data_cache.clear()
        for item in response.data:
            keyword_regex = item.get("keyword_regex")
            if keyword_regex:
                try:
                    keyword_data_cache[keyword_regex] = {
                        "compiled_regex": re.compile(keyword_regex, re.IGNORECASE),
                        "ai_instructions": item.get("ai_instructions"),
                        "discovery_message": item.get("discovery_message"),
                        "is_discovered": item.get("is_discovered", False),
                        "id": item.get("id")
                    }
                except re.error as e:
                    await log_error(None, f"AI: Failed to compile regex for keyword ID {item.get('id')}: `{keyword_regex}`", error=e)

        total_keywords = len(keyword_data_cache)
        discovered_keywords_count = sum(1 for data in keyword_data_cache.values() if data['is_discovered'])
        await log_info(None, f"AI: Successfully loaded {total_keywords} keyword rules ({discovered_keywords_count} discovered).")

    except Exception as e:
        await log_error(None, "AI: Critical error loading keyword data from Supabase.", error=e, ping_owner=True)
        keyword_data_cache.clear()
        total_keywords = 0
        discovered_keywords_count = 0

def get_prompt(prompt_key: str, **kwargs) -> Optional[str]:
    raw_prompt = AI_PROMPTS.get(prompt_key)
    return raw_prompt.format(**kwargs) if raw_prompt else None

async def block_unwanted_mentions(content: str, user_id: int) -> Tuple[Optional[str], Optional[str]]:
    """
    Checks for disallowed mentions (@everyone, @here, roles, users) in content.
    Bypasses the check for the bot owner.

    Args:
        content: The message content to check.
        user_id: The ID of the user who triggered the action.

    Returns:
        A tuple of (processed_content, error_message).
        - If allowed: (original_content, None)
        - If disallowed: (None, "Your message contains a disallowed mention...")
    """
    # 1. Bypass check for the bot owner
    if user_id == OWNER_USER_ID:
        return content, None

    # 2. Regex for different types of mentions
    role_mention_pattern = re.compile(r"<@&\d+>")
    user_mention_pattern = re.compile(r"<@!?\d+>")
    everyone_here_pattern = re.compile(r"@everyone|@here")

    # 3. Check if any mentions are present in the content
    if role_mention_pattern.search(content) or \
       user_mention_pattern.search(content) or \
       everyone_here_pattern.search(content):
        
        error_message = "Your message contains a disallowed mention (@everyone, @here, a role, or a user). Please remove it and try again."
        return None, error_message

    # 4. If no disallowed mentions are found, return the original content
    return content, None

async def _send_personality_response(
    channel: discord.TextChannel, 
    content: str, 
    personality_key: str, 
    fallback_used: bool,
    view: discord.ui.View, 
    message_to_edit: Optional[discord.Message] = None
) -> Optional[discord.Message]:
    """Sends or edits an AI response as a plain text message from the main bot account."""
    
    footer_text = f"\n\n*(Personality: {personality_key.title()}"
    if fallback_used:
        fallback_model = AI_PERSONALITIES.get(personality_key, {}).get('fallback_model', 'a fallback')
        footer_text += f" | Using {fallback_model} model due to high load"
    footer_text += ")*"

    # For non-normal personalities, add a name prefix instead of using a webhook
    name_prefix = ""
    if personality_key != "normal":
        webhook_name = PERSONALITY_WEBHOOK_NAMES.get(personality_key, "FlorrNerd")
        name_prefix = f"**{webhook_name}:**\n"

    full_content = name_prefix + content + footer_text
    if len(full_content) > 2000:
        content_limit = 2000 - len(name_prefix) - len(footer_text) - 3 # -3 for "..."
        content = content[:content_limit] + "..."
        full_content = name_prefix + content + footer_text

    try:
        if message_to_edit:
            # Attempt to edit the existing message
            await message_to_edit.edit(content=full_content, view=view)
            return message_to_edit
        else:
            # If no message to edit, send a new one
            return await channel.send(content=full_content, view=view)
    except discord.NotFound:
        # If the original message to edit was deleted, just send a new one.
        await log_info(channel.guild, "Message to edit was not found. Sending a new AI response instead.")
        new_msg = await channel.send(content=full_content, view=view)
        # Important: update the view's internal message reference
        if hasattr(view, 'bot_response_message'):
            view.bot_response_message = new_msg
        return new_msg
    except Exception as e:
        await log_error(channel.guild, f"Failed to send/edit AI response for personality {personality_key}", error=e)
        return None

async def get_ai_response(history: List[discord.Message], latest_message_content: str, personality_key: str = "normal") -> Tuple[Optional[str], bool]:
    personality = AI_PERSONALITIES.get(personality_key, AI_PERSONALITIES["normal"])
    system_prompt = get_prompt(personality['prompt_key'])
    
    api_history = [{'role': 'model' if msg.author.id == bot.user.id else 'user', 'parts': [msg.content]} for msg in history]
    api_history.append({'role': 'user', 'parts': [latest_message_content]})

    models_to_try = [personality['model']]
    if personality.get('fallback_model') and personality['fallback_model'] not in models_to_try:
        models_to_try.append(personality['fallback_model'])
    
    fallback_used = False
    guild_context_for_log = history[-1].guild if history else None
    
    safety_config = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    for i, model_id in enumerate(models_to_try):
        model = ai_models.get(model_id)
        if not model: continue
        
        if i > 0: fallback_used = True

        try:
            chat_session = model.start_chat(history=[])
            
            if system_prompt:
                chat_session.history.append({'role': 'user', 'parts': [system_prompt]})
                chat_session.history.append({'role': 'model', 'parts': ["Understood. I will act as requested."]})

            for msg in api_history[:-1]:
                 chat_session.history.append(msg)
            
            response = await chat_session.send_message_async(
                api_history[-1]['parts'],
                generation_config=personality['generation_config'],
                safety_settings=safety_config
            )
            
            raw_text = response.text

            if personality_key == "emoji":
                emoji_pattern = re.compile(
                    "["
                    "\U0001F600-\U0001F64F"  # emoticons
                    "\U0001F300-\U0001F5FF"  # symbols & pictographs
                    "\U0001F680-\U0001F6FF"  # transport & map symbols
                    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    "\U00002500-\U00002BEF"  # chinese char
                    "\U00002702-\U000027B0"
                    "\U000024C2-\U0001F251"
                    "\U0001f926-\U0001f937"
                    "\U00010000-\U0010ffff"
                    "\u2640-\u2642"
                    "\u2600-\u2B55"
                    "\u200d"
                    "\u23cf"
                    "\u23e9"
                    "\u231a"
                    "\ufe0f"  # dingbats
                    "\u3030"
                    "]+", flags=re.UNICODE)
                
                emojis_found = emoji_pattern.findall(raw_text)
                final_text = "".join(emojis_found)
                
                if not final_text:
                    return "❔", fallback_used 
                return final_text, fallback_used

            return raw_text, fallback_used

        except google_exceptions.ResourceExhausted as e:
            await log_error(guild_context_for_log, f"AI model '{model_id}' rate limited. Trying fallback.", error=e)
            continue
        except Exception as e:
            await log_error(guild_context_for_log, f"Error generating AI response with '{model_id}'", error=e, ping_owner=True)
            return None, fallback_used
    return None, fallback_used

async def get_ai_response_with_image(prompt_key: str, image_bytes_list: List[bytes], prompt_kwargs: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Generates an AI response for a prompt that includes one or more images."""
    if not ai_models:
        await log_error(None, "AI image processing failed: No models configured.", ping_owner=True)
        return None
    if not image_bytes_list:
        return None

    content_for_api = []
    prompt_text = get_prompt(prompt_key, **(prompt_kwargs or {}))
    if not prompt_text:
        await log_error(None, f"AI image processing failed: Prompt key '{prompt_key}' not found.")
        return None
    content_for_api.append(prompt_text)

    for image_bytes in image_bytes_list:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            content_for_api.append(img)
        except (UnidentifiedImageError, OSError) as e:
            await log_error(None, "AI image processing failed: Invalid image data encountered in batch.", error=e)
    
    if len(content_for_api) <= 1:
        return None

    model_id = "gemini-2.5-flash-preview-05-20"
    model = ai_models.get(model_id)
    if not model:
        await log_error(None, f"AI image processing failed: Required model '{model_id}' not available.", ping_owner=True)
        return None
    
    safety_config = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
        
    try:
        response = await model.generate_content_async(
            content_for_api, stream=False,
            generation_config=GenerationConfig(temperature=0.1),
            safety_settings=safety_config
        )
        return response.text.strip() if response and response.text else None
    except google_exceptions.ResourceExhausted as e:
        await log_error(None, f"AI image processing hit ResourceExhausted even with batching. User likely sent too many images.", error=e)
        return None
    except Exception as e:
        await log_error(None, f"AI image processing failed during generation with model '{model_id}'.", error=e)
        return None

async def _apply_slowmode(channel: discord.TextChannel):
    """Attempts to apply a 5-second slowmode to a channel. Fails silently."""
    try:
        if channel.slowmode_delay < 5:
            await channel.edit(slowmode_delay=5)
            print(f"AI: Applied 5s slowmode to #{channel.name}.")
    except discord.Forbidden:
        print(f"AI: Missing permissions to apply slowmode in #{channel.name}.")
    except discord.HTTPException as e:
        print(f"AI: Failed to apply slowmode in #{channel.name} due to an API error: {e}")

async def _remove_slowmode(channel: discord.TextChannel):
    await asyncio.sleep(10)
    try:
        if channel.slowmode_delay > 0: await channel.edit(slowmode_delay=0)
    except (discord.Forbidden, discord.HTTPException): pass
    finally:
        if channel.id in slowmode_tasks: del slowmode_tasks[channel.id]

async def process_message_for_ai(message: discord.Message):
    """The main AI processing logic, formerly from AICog.on_message."""
    if not message.guild: return
    guild_settings = server_settings_cache.get(message.guild.id, {})

    # FIX: Ensure we are checking against a list, even if the DB value is NULL.
    ai_channel_list = guild_settings.get('always_on_ai_channels') or []
    is_ai_channel = message.channel.id in ai_channel_list

    if not is_ai_channel:
        return

    retry_after = ai_message_cooldown.update_rate_limit(message)
    if retry_after:
        view = RetryAIView(message)
        retry_msg = await message.reply(f"⏳ You're doing that too fast. Please wait **{retry_after:.1f}s**.", view=view, mention_author=False, delete_after=10)
        view.message = retry_msg
        return
    
    if message.channel.id not in slowmode_tasks:
        task = slowmode_tasks[message.channel.id] = asyncio.create_task(_apply_slowmode(message.channel))
        task.add_done_callback(lambda t: slowmode_tasks.pop(message.channel.id, None))
    
    async with message.channel.typing():
        history = [m async for m in message.channel.history(limit=50, before=message)]
        history.reverse()

        initial_personality = channel_personalities.get(message.channel.id, "normal")
        
        response_text, fallback_used = await get_ai_response(history, message.content, initial_personality)
        
        if response_text:
            processed_content, mention_error = await block_unwanted_mentions(response_text, message.author.id)
            if mention_error:
                await log_error(
                    message.guild, 
                    f"AI response for user {message.author.mention} was blocked due to a generated mention.",
                    embed=discord.Embed(
                        title="Blocked AI Response Content",
                        description=f"```\n{discord.utils.escape_markdown(response_text[:1000])}\n```",
                        color=discord.Color.orange()
                    ).set_footer(text=f"Triggered by: {message.author.name} ({message.author.id})")
                )
                return

            channel_personalities[message.channel.id] = initial_personality
            view = AIResponseView(message, history, initial_personality)
            
            response_message = await _send_personality_response(
                channel=message.channel, 
                content=processed_content,
                personality_key=initial_personality,
                fallback_used=fallback_used,
                view=view
            )
            
            if response_message:
                view.bot_response_message = response_message

def _normalize_guild_tag(tag: str) -> str:
    """Normalizes a guild tag to the format [TAG]."""
    cleaned_tag = tag.strip().upper()
    if cleaned_tag.startswith('[') and cleaned_tag.endswith(']'):
        return cleaned_tag
    return f"[{cleaned_tag}]"

async def tracked_guild_tag_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes tags of currently tracked guilds for the server."""
    if not interaction.guild:
        return []
    
    config = await load_server_config(interaction.guild.id)
    tracked_guilds = config.get('tracked_guilds', {})
    
    choices = [
        app_commands.Choice(name=tag, value=tag)
        for tag in tracked_guilds.keys()
        if not current or current.lower() in tag.lower()
    ]
    return choices[:25]

async def check_is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user has administrator permissions."""
    return interaction.permissions.administrator

async def get_user_webhook_url(name: str) -> Optional[str]:
    """Fetches a user-created webhook's URL from the database by its custom name."""
    if not supabase:
        return None
    
    purpose_to_find = f"user_webhook_{name}"
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("webhooks")
                           .select("webhook_url")
                           .eq("purpose", purpose_to_find)
                           .limit(1)
                           .maybe_single()
                           .execute()
        )
        if resp and resp.data:
            return resp.data.get('webhook_url')
        return None
    except Exception as e:
        print(f"Error fetching user webhook URL for '{name}': {e}")
        return None

async def get_all_user_webhooks() -> List[Dict[str, Any]]:
    """Fetches all user-created webhooks from the database."""
    if not supabase:
        return []
        
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("webhooks")
                           .select("purpose, channel_id")
                           .like("purpose", "user_webhook_%")
                           .execute()
        )
        if resp and resp.data:
            # Clean up the purpose name for display
            for item in resp.data:
                item['name'] = item['purpose'].replace('user_webhook_', '', 1)
            return resp.data
        return []
    except Exception as e:
        print(f"Error fetching all user webhooks: {e}")
        return []

async def user_webhook_name_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes names of user-created webhooks."""
    webhooks = await get_all_user_webhooks()
    choices = [
        app_commands.Choice(name=wh['name'], value=wh['name'])
        for wh in webhooks
        if not current or current.lower() in wh['name'].lower()
    ]
    return choices[:25]

async def webhook_avatar_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes avatars from Florr images AND server members."""
    choices = []
    current_lower = current.lower()

    # 1. Add Florr images from cache
    if available_profile_pics_cache:
        for display_name, folder_id, filename in available_profile_pics_cache:
            if not current_lower or current_lower in display_name.lower():
                value = f"image:{folder_id}:{filename}"
                choices.append(app_commands.Choice(name=f"[Florr] {display_name}", value=value))

    # 2. Add server members
    if interaction.guild:
        for member in interaction.guild.members:
            if not current_lower or current_lower in member.display_name.lower():
                value = f"member:{member.id}"
                choices.append(app_commands.Choice(name=f"[Member] {member.display_name}", value=value))

    # Return the first 25 sorted matches
    return sorted(choices, key=lambda c: c.name)[:25]

class ConnectUserModal(discord.ui.Modal, title="Connect Florr IGN"):
    ign_input = discord.ui.TextInput(
        label="User's Exact In-Game Name",
        placeholder="Enter the Florr.io IGN to link...",
        style=discord.TextStyle.short,
        required=True,
        max_length=50
    )

    def __init__(self, target_user: discord.Member):
        super().__init__(timeout=300)
        self.target_user = target_user

    async def on_submit(self, interaction: discord.Interaction):
        # Double-check permissions on submit
        is_staff = await is_admin_or_owner(interaction)
        if interaction.user.id != self.target_user.id and not is_staff:
            await interaction.response.send_message("❌ You are not authorized to connect this user.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        
        guild = interaction.guild
        cleaned_ign = clean_ign(self.ign_input.value)
        if not cleaned_ign:
            await interaction.followup.send("❌ In-game name cannot be empty.", ephemeral=True)
            return

        # This logic is adapted from the /connect command
        try:
            ign_check_resp = await run_supabase_sync(lambda: supabase.table("florr_players").select("discord_id").eq("ingame_name", cleaned_ign).maybe_single().execute())
            if ign_check_resp and ign_check_resp.data and ign_check_resp.data.get('discord_id') and str(ign_check_resp.data['discord_id']) != str(self.target_user.id):
                conflict_user_id = ign_check_resp.data['discord_id']
                await interaction.followup.send(f"❌ **Conflict:** The IGN `{cleaned_ign}` is already connected to <@{conflict_user_id}>.", ephemeral=True)
                return

            await run_supabase_sync(lambda: supabase.table("florr_players").update({"discord_id": None, "discord_name": None}).eq("discord_id", str(self.target_user.id)).execute())
            await run_supabase_sync(lambda: supabase.table("florr_players").upsert({"ingame_name": cleaned_ign, "discord_id": str(self.target_user.id), "discord_name": str(self.target_user)}, on_conflict="ingame_name").execute())
            
            await trigger_global_role_sync_for_user(self.target_user)
            await load_ign_cache(guild)
            
            await interaction.followup.send(f"✅ Successfully connected {self.target_user.mention} to IGN `{cleaned_ign}`. Their profile is now viewable.", ephemeral=True)
            await log_info(guild, f"`{interaction.user.name}` connected `{self.target_user.name}` to IGN `{cleaned_ign}` via profile modal.")
        except Exception as e:
            await log_error(guild, "Error during modal connect", error=e, interaction=interaction)
            await interaction.followup.send("❌ An unexpected error occurred during connection.", ephemeral=True)


class ProfileNotFoundView(discord.ui.View):
    def __init__(self, target_user: discord.Member, timeout=180.0):
        super().__init__(timeout=timeout)
        self.target_user = target_user
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Allow the target user OR a staff member to interact
        is_staff = await is_admin_or_owner(interaction)
        if interaction.user.id == self.target_user.id or is_staff:
            return True
        else:
            await interaction.response.send_message("❌ You are not authorized to connect this user.", ephemeral=True)
            return False

    @discord.ui.button(label="Connect This User", style=discord.ButtonStyle.success, emoji="🔗")
    async def connect_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ConnectUserModal(target_user=self.target_user)
        await interaction.response.send_modal(modal)
    
    async def on_timeout(self):
        if self.message:
            for item in self.children: item.disabled = True
            try:
                await self.message.edit(content=self.message.content, embed=self.message.embeds[0] if self.message.embeds else None, view=self)
            except discord.HTTPException:
                pass
        self.stop()

async def get_guild_tag_from_ign(guild: Optional[discord.Guild], ign: str) -> Optional[str]:
    """Fetches just the florr_guild_tag for a given IGN."""
    if not supabase: return None
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("florr_players")
                           .select("florr_guild_tag")
                           .ilike("ingame_name", ign)
                           .limit(1)
                           .maybe_single()
                           .execute()
        )
        if resp and resp.data:
            return resp.data.get('florr_guild_tag')
        return None
    except Exception as e:
        await log_error(guild, f"Failed to fetch guild tag for IGN {ign}", error=e)
        return None

@bot.event
async def on_member_join(member: discord.Member):
    """Handles auto-assigning the unverified role to new members in Catercord."""
    # Only run for Catercord and ignore bots
    if member.guild.id != CATERCORD_GUILD_ID or member.bot:
        return

    await log_info(member.guild, f"New member joined: {member.mention} ({member.display_name})")

    config = await load_server_config(member.guild.id)
    unverified_role_id = config.get('unverified_role_id')

    if not unverified_role_id:
        await log_error(member.guild, f"on_member_join: `unverified_role_id` is not configured for this server. Cannot assign role to {member.mention}.")
        return

    unverified_role = member.guild.get_role(unverified_role_id)
    if not unverified_role:
        await log_error(member.guild, f"on_member_join: Configured unverified role (ID: {unverified_role_id}) not found.")
        return

    if not member.guild.me.guild_permissions.manage_roles or member.guild.me.top_role <= unverified_role:
        await log_error(member.guild, f"on_member_join: Bot lacks permissions or hierarchy to assign '{unverified_role.name}' role.")
        return

    try:
        if unverified_role not in member.roles:
            await member.add_roles(unverified_role, reason="New member auto-role")
            await log_info(member.guild, f"Assigned '{unverified_role.name}' role to new member {member.mention}.")
    except Exception as e:
        await log_error(member.guild, f"on_member_join: Failed to assign role to {member.mention}", error=e)

def clean_ign(ign: str) -> str:
    """Removes backslashes and strips whitespace from an IGN."""
    if not ign:
        return ""
    # Remove all backslashes and strip leading/trailing whitespace.
    return ign.replace('\\', '').strip()

async def get_user_super_craft_log_entries(
    guild: Optional[discord.Guild], 
    ign: str, 
    page: int, 
    per_page: int
) -> Tuple[List[Dict[str, Any]], int]:
    """Fetches paginated super craft log entries for a given IGN."""
    if not supabase or not ign:
        return [], 0

    offset = page * per_page
    try:
        # Use ilike for case-insensitive matching
        count_resp = await run_supabase_sync(
            lambda: supabase.table("super_craft_logs").select("id", count='exact').ilike("player_ign", ign).execute()
        )
        total_count = count_resp.count if count_resp and hasattr(count_resp, 'count') else 0
        if total_count == 0:
            return [], 0

        data_resp = await run_supabase_sync(
            lambda: supabase.table("super_craft_logs")
                           .select("id, craft_date, super_petal_name")
                           .ilike("player_ign", ign) # Use ilike here as well
                           .order("craft_date", desc=True)
                           .order("id", desc=True)
                           .range(offset, offset + per_page - 1)
                           .execute()
        )
        return (data_resp.data if data_resp and data_resp.data else []), total_count
    except Exception as e:
        await log_error(guild, f"Error fetching super craft log for {ign}", error=e)
        return [], 0

async def get_user_super_defeat_log_entries(
    guild: Optional[discord.Guild], 
    ign: str, 
    page: int, 
    per_page: int
) -> Tuple[List[Dict[str, Any]], int]:
    """Fetches paginated super defeat log entries where the IGN is one of the players."""
    if not supabase or not ign:
        return [], 0

    offset = page * per_page
    try:
        # Query using lowercase ign, as player names are now stored in lowercase.
        # NOTE: This will only find defeats logged AFTER this code change.
        # Old entries with mixed-case names will not be found.
        ign_lower = ign.lower()
        json_ign_for_query = json.dumps([ign_lower])

        count_resp = await run_supabase_sync(
            lambda: supabase.table("super_defeats").select("id", count='exact').contains("players", json_ign_for_query).execute()
        )
        total_count = count_resp.count if count_resp and hasattr(count_resp, 'count') else 0
        if total_count == 0:
            return [], 0

        data_resp = await run_supabase_sync(
            lambda: supabase.table("super_defeats")
                           .select("id, event_timestamp, rarity, mob, players")
                           .contains("players", json_ign_for_query)
                           .order("event_timestamp", desc=True)
                           .order("id", desc=True)
                           .range(offset, offset + per_page - 1)
                           .execute()
        )
        # The 'players' list returned will be all lowercase. This is acceptable for the log display.
        return (data_resp.data if data_resp and data_resp.data else []), total_count
    except Exception as e:
        await log_error(guild, f"Error fetching super defeat log for {ign}", error=e)
        return [], 0

async def _revive_static_list_views():
    """On startup, finds old static list messages and attaches new, live views."""
    print("--- Reviving Static List Views ---")
    for guild in bot.guilds:
        config = server_settings_cache.get(guild.id)
        if not config: continue

        tracked_guilds = config.get('tracked_guilds', {})
        for tag, tracked_config in tracked_guilds.items():
            channel_id = tracked_config.get("member_list_channel_id")
            if not channel_id: continue

            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                print(f"Revive Views: Skipping channel {channel_id} in {guild.name} (not a text channel).")
                continue

            print(f"Revive Views: Scanning #{channel.name} in {guild.name} for list message...")
            embed_title_to_find = f"**{tag} Guild Members**"
            
            try:
                async for msg in channel.history(limit=20):
                    if msg.author.id == bot.user.id and msg.embeds and msg.embeds[0].title == embed_title_to_find and msg.components:
                        print(f"Revive Views: Found zombie view for '{tag}' (Msg ID: {msg.id}). Reviving...")
                        # We found an old list. Let's update it with a fresh view.
                        # This re-uses the same logic as a full refresh.
                        await update_single_tracked_guild_list(guild, tracked_config)
                        # We only expect one list per channel, so we can break after finding it.
                        break
            except discord.Forbidden:
                print(f"Revive Views: Lacking permissions to read history in #{channel.name} ({guild.name}).")
            except Exception as e:
                await log_error(guild, f"Error during static list revival for channel #{channel.name}", error=e)
    print("--- Finished Reviving Static List Views ---")

async def resolve_name_to_id(guild: discord.Guild, name_or_id: str, item_type: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Resolves a user-provided name or ID to a specific role or channel ID.
    Returns (ID, status_message). ID is None on failure.
    """
    if not name_or_id:
        return None, "Not set."

    # 1. Check if it's already a valid ID
    if name_or_id.isdigit():
        item_id = int(name_or_id)
        if item_type == 'role' and guild.get_role(item_id):
            return item_id, None
        if item_type == 'channel' and guild.get_channel(item_id):
            return item_id, None
    
    # 2. Fuzzy match against names
    search_space = guild.roles if item_type == 'role' else guild.text_channels
    name_lower = name_or_id.lower()
    
    # Exact match (case-insensitive)
    exact_matches = [item for item in search_space if item.name.lower() == name_lower]
    if len(exact_matches) == 1:
        return exact_matches[0].id, None

    # Partial match (starts with)
    partial_matches = [item for item in search_space if item.name.lower().startswith(name_lower)]
    if len(partial_matches) == 1:
        return partial_matches[0].id, None

    # Difflib fuzzy match as a last resort
    closest_matches = difflib.get_close_matches(name_lower, [item.name.lower() for item in search_space], n=2, cutoff=0.7)
    if len(closest_matches) == 1:
        matched_item = discord.utils.get(search_space, name=closest_matches[0])
        if matched_item:
            return matched_item.id, None
    
    # 3. Handle failure cases
    if not closest_matches and not partial_matches and not exact_matches:
        return None, f"⚠️ No role/channel found for '{name_or_id}'."
    else:
        # Ambiguous match
        all_possible = set()
        if exact_matches: all_possible.update(i.name for i in exact_matches)
        if partial_matches: all_possible.update(i.name for i in partial_matches)
        if closest_matches: all_possible.update(i for i in closest_matches)

        return None, f"❓ Ambiguous. Could be: {', '.join(f'`{n}`' for n in list(all_possible)[:3])}."

async def trigger_global_role_sync_for_user(user: discord.Member):
    """
    Finds all mutual guilds the bot shares with a user and triggers a role refresh for them in each one.
    """
    if not user: return
    
    print(f"Triggering global role sync for user {user.name} ({user.id})")
    synced_guilds_count = 0
    for guild in bot.guilds:
        # Check if the user is a member of the guild
        member_in_guild = guild.get_member(user.id)
        if member_in_guild:
            # Run the role sync for this member in this specific guild
            await refresh_roles_for_single_user(guild, member_in_guild)
            synced_guilds_count += 1
            await asyncio.sleep(0.5) # Be gentle with the API
            
    await log_info(None, f"Global role sync for {user.name} completed. Checked {synced_guilds_count} mutual guilds.")

class SetupModal(discord.ui.Modal):
    def __init__(self, title: str, fields: List[Dict[str, Any]], callback_func):
        super().__init__(title=title, timeout=300)
        self.callback_func = callback_func
        self.fields_data = fields
        
        for field in fields:
            text_input = discord.ui.TextInput(
                label=field['label'],
                placeholder=field.get('placeholder', 'Enter value. Leave blank to clear.'),
                default=field.get('default', ''),
                custom_id=field['id'],
                style=field.get('style', discord.TextStyle.short),
                required=False,
                max_length=field.get('max_length', 100)
            )
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        results = {field.custom_id: field.value for field in self.children if isinstance(field, discord.ui.TextInput)}
        await self.callback_func(interaction, results)


class SetupView(discord.ui.View):
    def __init__(self, guild: discord.Guild, config: Dict[str, Any]):
        super().__init__(timeout=600)
        self.guild = guild
        self.config = config
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Checks if the user has admin permissions before allowing interaction."""
        is_staff = await is_admin_or_owner(interaction)
        if is_staff:
            return True
        else:
            await interaction.response.send_message("❌ You need administrator permissions to use these buttons.", ephemeral=True)
            return False

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(title=f"⚙️ Bot Setup for {self.guild.name}", color=NERDY_YELLOW)
        embed.description = "Use the buttons below to configure the bot for this server. All settings are optional."
        
        def get_mention(item_id, item_type):
            if not item_id: return "`Not Set`"
            if item_type == 'role': item_obj = self.guild.get_role(item_id)
            else: item_obj = self.guild.get_channel(item_id)
            return item_obj.mention if item_obj else f"⚠️ `Not Found (ID: {item_id})`"
            
        def get_bool_status(key: str) -> str:
            return "✅ Enabled" if self.config.get(key, True) else "❌ Disabled"

        # --- Roles ---
        roles_val = (
            f"**Verified:** {get_mention(self.config.get('verified_role_id'), 'role')}\n"
            f"**Unverified:** {get_mention(self.config.get('unverified_role_id'), 'role')}\n"
            f"**Withered:** {get_mention(self.config.get('withered_role_id'), 'role')}\n"
            f"**Ex-Member:** {get_mention(self.config.get('ex_member_role_id'), 'role')}"
        )
        embed.add_field(name="Core Roles", value=roles_val, inline=False)
        
        # --- Channels ---
        chans_val = (
            f"**Screenshots:** {get_mention(self.config.get('screenshots_dropbox_channel_id'), 'channel')}\n"
            f"**Super Attempts:** {get_mention(self.config.get('super_attempts_channel_id'), 'channel')}"
        )
        embed.add_field(name="Feature Channels", value=chans_val, inline=False)
        
        # --- Ping Channels ---
        ping_chans_val = (
            f"**Craft Pings:** {get_mention(self.config.get('craft_ping_channel_id'), 'channel')}\n"
            f"**Spawn Pings:** {get_mention(self.config.get('spawn_ping_channel_id'), 'channel')}\n"
            f"**Defeat Pings:** {get_mention(self.config.get('defeat_ping_channel_id'), 'channel')}\n"
            f"**Super Ping Role:** {get_mention(self.config.get('super_ping_role_id'), 'role')}"
        )
        embed.add_field(name="Self-Bot Ping Settings", value=ping_chans_val, inline=False)

        # --- AI Channels ---
        ai_channel_ids = self.config.get('always_on_ai_channels') or []
        ai_mentions = [get_mention(cid, 'channel') for cid in ai_channel_ids]
        ai_chans_val = ", ".join(ai_mentions) if ai_mentions else "`Not Set`"
        embed.add_field(name="Always-On AI Channels", value=ai_chans_val, inline=False)
        
        # --- Tracked Guilds ---
        tracked_guilds = self.config.get('tracked_guilds', {})
        if tracked_guilds:
            guilds_val_parts = []
            for tag, data in sorted(tracked_guilds.items()):
                role_mention = get_mention(data.get('discord_role_id'), 'role')
                chan_mention = get_mention(data.get('member_list_channel_id'), 'channel')
                guilds_val_parts.append(f"**{tag}**: {role_mention} → {chan_mention}")
            guilds_val = "\n".join(guilds_val_parts)
        else:
            guilds_val = "`No guilds are being tracked yet.`"
        embed.add_field(name=f"Tracked Florr Guilds (use /setup_guild to manage)", value=guilds_val, inline=False)

        # --- Command Permissions ---
        perms_val = (
            f"**/florr:** {get_mention(self.config.get('florr_command_role_id'), 'role')}\n"
            f"**/imitate:** {get_mention(self.config.get('imitate_command_role_id'), 'role')}\n"
            f"**/wither:** {get_mention(self.config.get('wither_command_role_id'), 'role')}"
        )
        embed.add_field(name="Command Permissions", value=perms_val, inline=False)

        # --- Enabled Modules ---
        enabled_modules = self.config.get('enabled_modules') or []
        modules_val = f"`{', '.join(enabled_modules) or 'None'}`"
        embed.add_field(name="✅ Enabled Modules", value=modules_val, inline=False)

        # --- Feature Toggles ---
        toggles_val = (
            f"**Keyword Triggers:** {get_bool_status('keywords_enabled')}\n"
            f"**/wither Command:** {get_bool_status('wither_command_enabled')}"
        )
        embed.add_field(name="Feature Toggles", value=toggles_val, inline=False)

        embed.set_footer(text="Enter a name or ID in the modals. Leave blank to clear a setting.")
        return embed

    async def update_config_and_refresh(self, interaction: discord.Interaction, updates: Dict[str, Any]):
        if not self.guild: return
        
        if len(updates) > 1:
            await run_supabase_sync(lambda: supabase.table(SERVER_CONFIGS_TABLE_NAME).upsert(updates, on_conflict="guild_id").execute())
        
        # Invalidate the cache to force a reload from the database
        if self.guild.id in server_settings_cache:
            del server_settings_cache[self.guild.id]
        
        # This call will now fetch fresh data from Supabase and repopulate the cache
        self.config = await load_server_config(self.guild.id)
        
        # Now update the message with an embed reflecting the new, live configuration
        if self.message:
            await self.message.edit(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Set Roles", style=discord.ButtonStyle.primary, row=0)
    async def set_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        fields = [
            {'label': "Verified Role Name/ID", 'id': "verified_role_id", 'default': str(self.config.get('verified_role_id') or '')},
            {'label': "Unverified Role Name/ID", 'id': "unverified_role_id", 'default': str(self.config.get('unverified_role_id') or '')},
            {'label': "Withered Role Name/ID", 'id': "withered_role_id", 'default': str(self.config.get('withered_role_id') or '')},
            {'label': "Ex-Member Role Name/ID", 'id': "ex_member_role_id", 'default': str(self.config.get('ex_member_role_id') or '')},
        ]
        modal = SetupModal(title="Set Core Roles", fields=fields, callback_func=self.handle_modal_submit)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Set Feature Channels", style=discord.ButtonStyle.primary, row=0)
    async def set_channels_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        fields = [
            {'label': "Screenshots Channel Name/ID", 'id': "screenshots_dropbox_channel_id", 'default': str(self.config.get('screenshots_dropbox_channel_id') or '')},
            {'label': "Super Attempts Channel Name/ID", 'id': "super_attempts_channel_id", 'default': str(self.config.get('super_attempts_channel_id') or '')},
        ]
        modal = SetupModal(title="Set Feature Channels", fields=fields, callback_func=self.handle_modal_submit)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Set Command Permissions", style=discord.ButtonStyle.primary, row=0)
    async def set_perms_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        fields = [
            {'label': "/florr Command Role Name/ID", 'id': "florr_command_role_id", 'default': str(self.config.get('florr_command_role_id') or '')},
            {'label': "/imitate Command Role Name/ID", 'id': "imitate_command_role_id", 'default': str(self.config.get('imitate_command_role_id') or '')},
            {'label': "/wither Command Role Name/ID", 'id': "wither_command_role_id", 'default': str(self.config.get('wither_command_role_id') or '')},
        ]
        modal = SetupModal(title="Set Command Roles", fields=fields, callback_func=self.handle_modal_submit)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Set Ping Settings", style=discord.ButtonStyle.secondary, row=1)
    async def set_ping_channels_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        fields = [
            {'label': "Craft Ping Channel", 'id': "craft_ping_channel_id", 'default': str(self.config.get('craft_ping_channel_id') or '')},
            {'label': "Spawn Ping Channel", 'id': "spawn_ping_channel_id", 'default': str(self.config.get('spawn_ping_channel_id') or '')},
            {'label': "Defeat Ping Channel", 'id': "defeat_ping_channel_id", 'default': str(self.config.get('defeat_ping_channel_id') or '')},
            {'label': "Super Spawn Ping Role", 'id': "super_ping_role_id", 'default': str(self.config.get('super_ping_role_id') or '')},
        ]
        modal = SetupModal(title="Set Self-Bot Ping Settings", fields=fields, callback_func=self.handle_modal_submit)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Set AI Channels", style=discord.ButtonStyle.secondary, row=1)
    async def set_ai_channels_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_ai_channels = self.config.get('always_on_ai_channels', [])
        default_str = ', '.join(map(str, current_ai_channels)) if current_ai_channels else ''
        fields = [
            {'label': "AI Channel Names/IDs (comma-separated)", 'id': "always_on_ai_channels", 'placeholder': "e.g., general, ai-chat, 123456789...", 'default': default_str, 'style': discord.TextStyle.paragraph, 'max_length': 1024}
        ]
        modal = SetupModal(title="Set Always-On AI Channels", fields=fields, callback_func=self.handle_modal_submit)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Set Modules", style=discord.ButtonStyle.secondary, row=1)
    async def set_modules_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_modules = self.config.get('enabled_modules', [])
        default_str = ', '.join(current_modules) if current_modules else ''
        fields = [{'label': "Enabled Modules (comma-separated)", 'id': "enabled_modules", 'placeholder': "e.g., verification, guild_management", 'default': default_str, 'style': discord.TextStyle.paragraph, 'max_length': 1024}]
        modal = SetupModal(title="Set Enabled Bot Modules", fields=fields, callback_func=self.handle_modal_submit)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Toggle Features", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_features_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        fields = [
            {'label': "Keyword Triggers Enabled (yes/no)", 'id': "keywords_enabled", 'default': "yes" if self.config.get('keywords_enabled', True) else "no"},
            {'label': "/wither Command Enabled (yes/no)", 'id': "wither_command_enabled", 'default': "yes" if self.config.get('wither_command_enabled', True) else "no"},
        ]
        modal = SetupModal(title="Toggle Features", fields=fields, callback_func=self.handle_modal_submit)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Done", style=discord.ButtonStyle.success, row=3)
    async def done_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="✅ Setup complete.", embed=None, view=None)
        self.stop()

    async def handle_modal_submit(self, interaction: discord.Interaction, results: Dict[str, str]):
        await interaction.response.defer(thinking=True, ephemeral=True)
        updates = {"guild_id": self.guild.id}
        errors = []
        resolved_items = []

        for key, value in results.items():
            value_stripped = value.strip()
            
            if not value_stripped:
                updates[key] = None
                resolved_items.append(f"Cleared setting for `{key}`.")
                continue

            if key.endswith('_enabled'):
                if value_stripped.lower() in ['yes', 'true', '1', 'on', 'enabled']:
                    updates[key] = True
                    resolved_items.append(f"Set `{key}` to ✅ Enabled.")
                elif value_stripped.lower() in ['no', 'false', '0', 'off', 'disabled']:
                    updates[key] = False
                    resolved_items.append(f"Set `{key}` to ❌ Disabled.")
                else:
                    errors.append(f"For `{key}`: Invalid input. Please use 'yes' or 'no'.")
                continue

            if key == 'always_on_ai_channels':
                channel_inputs = [name.strip() for name in value_stripped.split(',') if name.strip()]
                resolved_ids = []
                temp_errors = []
                for channel_input in channel_inputs:
                    resolved_id, status_msg = await resolve_name_to_id(self.guild, channel_input, 'channel')
                    if resolved_id:
                        resolved_ids.append(resolved_id)
                    else:
                        temp_errors.append(f"Could not resolve '{channel_input}': {status_msg}")
                
                if not temp_errors:
                    updates[key] = resolved_ids
                    mentions = [f"<#{cid}>" for cid in resolved_ids]
                    resolved_items.append(f"Set `{key}` to: {', '.join(mentions) or 'None'}.")
                else:
                    errors.extend(temp_errors)
                continue

            if key == 'enabled_modules':
                module_inputs = {m.strip().lower() for m in value_stripped.split(',') if m.strip()}
                updates[key] = sorted(list(module_inputs))
                resolved_items.append(f"Set `enabled_modules` to: `{', '.join(updates[key]) or 'None'}`.")
                continue

            item_type = 'channel' if 'channel' in key else 'role'
            resolved_id, status_msg = await resolve_name_to_id(self.guild, value_stripped, item_type)
            
            if resolved_id:
                updates[key] = resolved_id
                item_obj = self.guild.get_role(resolved_id) if item_type == 'role' else self.guild.get_channel(resolved_id)
                resolved_items.append(f"Set `{key}` to {item_obj.mention}.")
            else:
                errors.append(f"For `{key}`: {status_msg}")

        feedback_embed = discord.Embed(title="Setup Update Confirmation", color=NERDY_YELLOW)
        
        if resolved_items:
            feedback_embed.add_field(name="✅ Changes Applied", value="\n".join(resolved_items), inline=False)
        
        if errors:
            feedback_embed.add_field(name="❌ Errors / Unchanged", value="\n".join(errors), inline=False)
            feedback_embed.color = discord.Color.orange()
            feedback_embed.set_footer(text="Settings with errors were not saved. Try again with valid names/IDs.")
        else:
            feedback_embed.color = discord.Color.green()
        
        await self.update_config_and_refresh(interaction, updates)
        await interaction.followup.send(embed=feedback_embed, ephemeral=True)

    async def on_timeout(self):
        if self.message:
            try: await self.message.edit(content="Setup timed out.", view=None)
            except (discord.NotFound, discord.HTTPException): pass

async def _create_ping_text(item: Dict[str, Any]) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    Creates a human-friendly text ping template for a game event notification.
    Returns the template, a boolean indicating if a role should be pinged, and the event timestamp.
    """
    category = item.get('category')
    rarity = item.get('rarity')
    server = item.get('server')
    timestamp_str = item.get('timestamp')
    ping_role = False
    text = None

    region_prefix = f"**[{server}]**: " if server else ""

    if category == 'super_craft':
        petal = item.get('petal')
        player = item.get('player')
        text = f"{region_prefix}**{rarity} {petal}** was just crafted by **{player or 'Someone'}**!"

    elif category == 'super_spawn':
        mob = item.get('mob', 'Unknown Mob').replace('_', ' ').title()
        # The {time} placeholder will now be replaced in the calling function.
        text = f"{region_prefix}**{rarity} {mob}** has spawned{{time}}!"
        ping_role = True

    elif category == 'super_defeat':
        mob = item.get('mob', 'Unknown Mob').replace('_', ' ').title()
        players = item.get('players', [])
        if players:
            player_str = f" by **{', '.join(players)}**"
        else:
            player_str = ""
        text = f"{region_prefix}**{rarity} {mob}** has been defeated{player_str}!"

    if rarity == "Unique" and text:
        text = f"✨ **UNIQUE EVENT!** ✨\n{text}"

    # Replace the {time} placeholder if it exists and a valid timestamp is available
    if text and '{{time}}' in text:
        time_replacement = ""
        if timestamp_str:
            try:
                event_dt = date_parse(timestamp_str)
                unix_ts = int(event_dt.timestamp())
                # The replacement string includes the leading space
                time_replacement = f" <t:{unix_ts}:R>"
            except (ValueError, TypeError):
                pass # Keep time_replacement as empty string
        
        text = text.replace('{{time}}', time_replacement)

    return text, ping_role, timestamp_str

async def _log_super_defeat_to_db(item: Dict[str, Any]):
    """Logs a super defeat event to the new super_defeats table."""
    if DISABLE_DB_EVENT_LOGGING:
        print("Super Defeat DB Log: Skipped due to testing instance.")
        return
    if not supabase:
        print("Super Defeat DB Log: Supabase unavailable.")
        return

    try:
        guild_for_log = bot.get_guild(CATERCORD_GUILD_ID) or (bot.guilds[0] if bot.guilds else None)

        event_timestamp = None
        if item.get('timestamp'):
            try:
                event_timestamp = date_parse(item['timestamp']).isoformat()
            except (ValueError, TypeError):
                pass 

        # Store player names in lowercase to ensure case-insensitive searching later.
        players_list = item.get('players', [])
        players_lower = [p.lower() for p in players_list if p] if players_list else []

        insert_payload = {
            "mob": item.get('mob'),
            "rarity": item.get('rarity'),
            "server": item.get('server'),
            "players": players_lower, # Store the lowercase list
            "message_id": str(item.get('message_id')) if item.get('message_id') else None,
            "event_timestamp": event_timestamp
        }
        
        insert_payload = {k: v for k, v in insert_payload.items() if v is not None}
        
        await run_supabase_sync(
            lambda: supabase.table("super_defeats").insert(insert_payload).execute()
        )
        print(f"Super Defeat DB Log: Successfully logged defeat of {item.get('rarity')} {item.get('mob')}.")
    except Exception as e:
        await log_error(guild_for_log, f"Failed to log super defeat event to database", error=e)

async def _log_super_craft_to_db(item: Dict[str, Any]):
    """Logs a super craft event to the super_craft_logs table."""
    if DISABLE_DB_EVENT_LOGGING:
        print("Super Craft DB Log: Skipped due to testing instance.")
        return
    if not supabase:
        print("Super Craft DB Log: Supabase unavailable.")
        return

    # Add verbose logging to see the exact data received
    print(f"Super Craft DB Log: Received event data: {item}")

    guild_for_log = bot.get_guild(CATERCORD_GUILD_ID) or (bot.guilds[0] if bot.guilds else None)
    try:
        # --- Extract and Validate Data ---
        player_ign = item.get('player')
        rarity = item.get('rarity')
        petal_name = item.get('petal')
        # Correctly handle potential None value for message_id before converting to string
        message_id = str(item.get('message_id')) if item.get('message_id') is not None else None
        event_timestamp_str = item.get('timestamp')

        # The table has NOT NULL constraints, so we must validate before inserting.
        # This check will now also fail if message_id is None or an empty string.
        if not all([player_ign, rarity, petal_name, message_id, event_timestamp_str]):
            await log_error(guild_for_log, f"Super Craft DB Log: Missing required data in event payload for message {message_id}. Data: {item}")
            return

        # --- Format Data for DB ---
        super_petal_name = f"{rarity} {petal_name}"
        craft_date = date_parse(event_timestamp_str).date()
        processed_by_id = str(bot.user.id) if bot.user else None

        insert_payload = {
            "player_ign": player_ign,
            "super_petal_name": super_petal_name,
            "craft_date": craft_date.isoformat(),
            "original_message_id": message_id,
            "processed_by_id": processed_by_id
        }

        await run_supabase_sync(
            lambda: supabase.table("super_craft_logs").insert(insert_payload).execute()
        )
        print(f"Super Craft DB Log: Successfully logged craft of '{super_petal_name}' by '{player_ign}'.")

    except APIError as e:
        # Gracefully handle if the message ID was already logged
        if "unique constraint" in str(e.message) and "super_craft_logs_original_message_id_key" in str(e.message):
            print(f"Super Craft DB Log: Craft for message ID {item.get('message_id')} already exists in the database. Skipping.")
        else:
            await log_error(guild_for_log, f"Failed to log super craft event to database (APIError)", error=e)
    except Exception as e:
        await log_error(guild_for_log, f"Failed to log super craft event to database (General Error)", error=e)

@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    """Logs when a message is deleted from the self-bot's channel."""
    if str(payload.channel_id) != SUPER_CRAFT_SELF_BOT_CHANNEL_ID:
        return

    guild = bot.get_guild(payload.guild_id) if payload.guild_id else None

    embed = discord.Embed(
        title="🕵️ Message Deleted in Self-Bot Channel",
        description="A message was deleted from the self-bot feed channel. This could be due to an edit that replaces the embed or a manual deletion.",
        color=discord.Color.blue()
    )
    embed.add_field(name="Message ID", value=f"`{payload.message_id}`", inline=True)
    if payload.guild_id:
        embed.add_field(name="Guild ID", value=f"`{payload.guild_id}`", inline=True)
    embed.add_field(name="Channel ID", value=f"`{payload.channel_id}`", inline=True)
    embed.set_footer(text="Note: The content of the deleted message is not available via this event.")
    embed.timestamp = discord.utils.utcnow()

    await log_error(
        guild, 
        "A message was deleted in the self-bot's private channel.", 
        embed=embed, 
        ping_owner=False
    )

@tasks.loop(seconds=5.0)
async def aperiodic_craft_poster():
    """
    Aperiodically checks the craft queue. If the cooldown has passed and
    items exist, it posts them all in a single batch.
    """
    await bot.wait_until_ready()
    global last_craft_post_time

    current_time = bot.loop.time()
    # Only post if the cooldown has passed AND there's something to post.
    if craft_queue.empty() or (current_time - last_craft_post_time) < NOTIFICATION_COOLDOWN_SECONDS:
        return

    items_to_post = []
    while not craft_queue.empty():
        items_to_post.append(await craft_queue.get())

    if not items_to_post: return

    CRAFT_NOTIFY_GUILD_ID, CRAFT_NOTIFY_CHANNEL_ID = 1332980983003349012, 1382246434513879091
    target_guild = bot.get_guild(CRAFT_NOTIFY_GUILD_ID)
    if not target_guild: return
    
    target_channel = target_guild.get_channel(CRAFT_NOTIFY_CHANNEL_ID)
    if not isinstance(target_channel, discord.TextChannel): return

    webhook = await get_or_create_webhook(target_channel, "craft_notify", "Craft Notify")
    if not webhook: return
    
    # Exclude category and message_id from the final JSON output
    message_content = [f"```json\n{json.dumps({k: v for k, v in item.items() if k not in ['category', 'message_id']}, indent=4)}\n```" for item in items_to_post]
    full_message = "\n".join(message_content)
    if len(full_message) > 2000: full_message = full_message[:1990] + "\n...```"
        
    try:
        # Send without a custom avatar to use the webhook's default (which is blank if we don't set one)
        await webhook.send(full_message)
        print(f"[Craft Poster] Sent batch of {len(items_to_post)} craft event(s).")
        last_craft_post_time = current_time
    except Exception as e: 
        print(f"[Craft Poster] Webhook send failed: {e}")
        # Re-queue items on failure to avoid losing them
        for item in items_to_post:
            await craft_queue.put(item)

@tasks.loop(seconds=5.0)
async def aperiodic_spawn_defeat_poster():
    """
    Aperiodically checks the spawn/defeat queue. If the cooldown has passed and
    items exist, it posts them all in a single batch.
    """
    await bot.wait_until_ready()
    global last_spawn_defeat_post_time

    current_time = bot.loop.time()
    if spawn_defeat_queue.empty() or (current_time - last_spawn_defeat_post_time) < NOTIFICATION_COOLDOWN_SECONDS:
        return

    items_to_post = []
    while not spawn_defeat_queue.empty():
        items_to_post.append(await spawn_defeat_queue.get())
        
    if not items_to_post: return

    SPAWN_DEFEAT_GUILD_ID, SPAWN_DEFEAT_CHANNEL_ID = 1332980983003349012, 1382360376204853381
    target_guild = bot.get_guild(SPAWN_DEFEAT_GUILD_ID)
    if not target_guild: return

    target_channel = target_guild.get_channel(SPAWN_DEFEAT_CHANNEL_ID)
    if not isinstance(target_channel, discord.TextChannel): return

    webhook = await get_or_create_webhook(target_channel, "spawn_defeat_notify", "Spawn Notify")
    if not webhook: return

    # Exclude category and message_id from the final JSON output
    message_content = [f"```json\n{json.dumps({k: v for k, v in item.items() if k not in ['category', 'message_id']}, indent=4)}\n```" for item in items_to_post]
    full_message = "\n".join(message_content)
    if len(full_message) > 2000: full_message = full_message[:1990] + "\n...```"
            
    try:
        await webhook.send(full_message)
        print(f"[Spawn/Defeat Poster] Sent batch of {len(items_to_post)} event(s).")
        last_spawn_defeat_post_time = current_time
    except Exception as e: 
        print(f"[Spawn/Defeat Poster] Webhook send failed: {e}")
        # Re-queue items on failure
        for item in items_to_post:
            await spawn_defeat_queue.put(item)

async def _initialize_data_caches(bot: commands.Bot):
    """Loads all initial data from database and filesystem."""
    print("--- Loading all server configurations into cache ---")
    if supabase:
        for guild in bot.guilds:
            await load_server_config(guild.id)
    print(f"--- Finished loading configs for {len(server_settings_cache)} guild(s) ---")

    print("--- Loading initial data ---")
    log_guild_for_data_load = bot.get_guild(CATERCORD_GUILD_ID) or (bot.guilds[0] if bot.guilds else None)

    await load_ign_cache(log_guild_for_data_load)
    print("Loading profile picture choices...")
    await load_profile_picture_choices(log_guild_for_data_load)
    print("Loading AI keyword data...")
    await load_keyword_data()

    print("Staff channel identification is now dynamic based on user permissions.")

async def _sync_app_commands(bot: commands.Bot) -> list:
    """Syncs application commands and populates the command_ids dictionary."""
    print("Syncing application commands...")
    synced_commands = []
    try:
        synced_commands = await bot.tree.sync()
        print(f"Synced {len(synced_commands)} application commands.")
        command_ids.clear()
        for cmd in synced_commands:
            command_ids[cmd.name] = cmd.id
            if isinstance(cmd, app_commands.Group):
                for sub_cmd in cmd.commands:
                    command_ids[f"{cmd.name} {sub_cmd.name}"] = sub_cmd.id
    except Exception as e:
        print(f"Command Sync failed: {e}\n{traceback.format_exc()}")
    return synced_commands


async def _start_background_tasks(bot: commands.Bot):
    """Initializes and starts all background tasks and listeners."""
    print("Starting background tasks...")

    if not check_static_view_timeout.is_running(): check_static_view_timeout.start()
    if not m28_server_scraper.is_running(): m28_server_scraper.start()
    if not aperiodic_craft_poster.is_running(): aperiodic_craft_poster.start()
    if not aperiodic_spawn_defeat_poster.is_running(): aperiodic_spawn_defeat_poster.start()
    print("Started periodic tasks: view timeout, m28 scraper, aperiodic posters.")
    
    print("--- Starting Self-Bot Integration ---")
    if SELF_DISCORD_TOKEN:
        print("SELF_DISCORD_TOKEN found. Initializing listener...")
        listener = SelfBotListener(token=SELF_DISCORD_TOKEN, channel_id=SUPER_CRAFT_SELF_BOT_CHANNEL_ID, bot_instance=bot)
        
        def run_listener_in_thread():
            asyncio.run(listener.run())

        listener_thread = threading.Thread(target=run_listener_in_thread, daemon=True)
        listener_thread.start()
        print("Self-Bot listener thread started.")
    else:
        print("SELF_DISCORD_TOKEN not found. Self-bot integration will be skipped.")

async def _format_announcement(data: Dict[str, Any]) -> str:
    """Formats an announcement string based on classified data and templates."""
    category = data.get('category')
    
    if category == 'super_craft':
        rarity_info = FLORR_ANNOUNCEMENT_TEMPLATES["Rarities"].get(data.get('rarity', ''), {})
        article = rarity_info.get("ArticleUpper", "A")
        rarity_name = rarity_info.get("Name", data.get('rarity'))
        petal_name = data.get('petal', 'Unknown Petal')
        player = data.get('player')
        
        if data.get('rarity') == "Unique":
            return f"The Unique {petal_name} has been forged by {player}!" if player else f"The Unique {petal_name} has been forged!"
        else:
            return f"{article} {rarity_name} {petal_name} has been crafted by {player}!" if player else f"{article} {rarity_name} {petal_name} has been crafted!"

    elif category == 'super_spawn':
        rarity_info = FLORR_ANNOUNCEMENT_TEMPLATES["Rarities"].get(data.get('rarity', ''), {})
        article = rarity_info.get("ArticleUpper", "A")
        rarity_name = rarity_info.get("Name", data.get('rarity'))
        mob_name = data.get('mob', 'Unknown Mob').replace('_', ' ').title()
        return f"{article} {rarity_name} {mob_name} has spawned!"

    elif category == 'super_defeat':
        rarity_info = FLORR_ANNOUNCEMENT_TEMPLATES["Rarities"].get(data.get('rarity', ''), {})
        article = rarity_info.get("ArticleUpper", "A")
        rarity_name = rarity_info.get("Name", data.get('rarity'))
        mob_name = data.get('mob', 'Unknown Mob').replace('_', ' ').title()
        players = data.get('players', [])
        
        if not players:
            return f"{article} {rarity_name} {mob_name} has been defeated!"
        elif len(players) == 1:
            player_str = players[0]
        elif len(players) == 2:
            player_str = f"{players[0]} and {players[1]}"
        else:
            player_str = ", ".join(players[:-1]) + f", and {players[-1]}"
            
        return FLORR_ANNOUNCEMENT_TEMPLATES["Chat"]["MobDefeated"].format(rarity=rarity_name, mob=mob_name, players=player_str)
        
    return "Could not format announcement."

async def refresh_roles_for_single_user(guild: discord.Guild, member: discord.Member):
    """Syncs a single user's roles based on their database state (connection, guild tag, and ex-member status)."""
    if not supabase or not guild.me.guild_permissions.manage_roles:
        return

    config = await load_server_config(guild.id)
    verified_role_id = config.get('verified_role_id')
    unverified_role_id = config.get('unverified_role_id')
    ex_member_role_id = config.get('ex_member_role_id')
    tracked_guilds_config = config.get('tracked_guilds', {})
    
    roles_to_add = []
    roles_to_remove = []

    try:
        user_db_resp = await run_supabase_sync(lambda: supabase.table("florr_players").select("discord_id, florr_guild_tag").eq("discord_id", str(member.id)).maybe_single().execute())
        
        db_data = user_db_resp.data if user_db_resp and hasattr(user_db_resp, 'data') else {}
        is_connected = bool(db_data)
        db_guild_tag = db_data.get('florr_guild_tag') if is_connected else None
        
        # 1. Handle Verified/Unverified Roles
        verified_role = guild.get_role(verified_role_id) if verified_role_id else None
        unverified_role = guild.get_role(unverified_role_id) if unverified_role_id else None

        if is_connected:
            if verified_role and verified_role not in member.roles and guild.me.top_role > verified_role:
                roles_to_add.append(verified_role)
            if unverified_role and unverified_role in member.roles and guild.me.top_role > unverified_role:
                roles_to_remove.append(unverified_role)
        else:
            if unverified_role and unverified_role not in member.roles and guild.me.top_role > unverified_role:
                roles_to_add.append(unverified_role)
            if verified_role and verified_role in member.roles and guild.me.top_role > verified_role:
                roles_to_remove.append(verified_role)
        
        # 2. Handle Tracked Guild Roles
        is_in_tracked_guild = db_guild_tag and db_guild_tag in tracked_guilds_config
        required_guild_role_id = None
        if is_in_tracked_guild:
            required_guild_role_id = tracked_guilds_config[db_guild_tag].get('discord_role_id')
        
        if required_guild_role_id:
            role_obj = guild.get_role(required_guild_role_id)
            if role_obj and role_obj not in member.roles and guild.me.top_role > role_obj:
                roles_to_add.append(role_obj)
        
        for tracked_tag, tracked_data in tracked_guilds_config.items():
            role_id = tracked_data.get('discord_role_id')
            if role_id and role_id != required_guild_role_id:
                role_obj = guild.get_role(role_id)
                if role_obj and role_obj in member.roles and guild.me.top_role > role_obj:
                    roles_to_remove.append(role_obj)

        # 3. Handle Ex-Member Role
        ex_member_role = guild.get_role(ex_member_role_id) if ex_member_role_id else None
        if ex_member_role:
            # Add ex-member role if user is connected but not in a tracked guild
            if is_connected and not is_in_tracked_guild and ex_member_role not in member.roles and guild.me.top_role > ex_member_role:
                roles_to_add.append(ex_member_role)
            # Remove ex-member role if user is not connected or has joined a tracked guild
            elif (not is_connected or is_in_tracked_guild) and ex_member_role in member.roles and guild.me.top_role > ex_member_role:
                roles_to_remove.append(ex_member_role)

        # 4. Apply changes
        if roles_to_add or roles_to_remove:
            final_roles = [r for r in member.roles if r not in roles_to_remove] + roles_to_add
            await member.edit(roles=final_roles, reason="Automatic role sync with database")
            add_names = [r.name for r in roles_to_add]
            rem_names = [r.name for r in roles_to_remove]
            await log_info(guild, f"Synced roles for {member.mention}. Added: {add_names or 'None'}. Removed: {rem_names or 'None'}.")

    except Exception as e:
        await log_error(guild, f"Failed to sync roles for {member.mention}", error=e)

async def refresh_all_guild_lists(guild: discord.Guild):
    """Iterates through all configured tracked guilds and updates their static lists."""
    config = await load_server_config(guild.id)
    tracked_guilds = config.get('tracked_guilds', {})
    for tag, tracked_config in tracked_guilds.items():
        if tracked_config.get("member_list_channel_id"):
            await update_single_tracked_guild_list(guild, tracked_config)
            await asyncio.sleep(2) # Be gentle with Discord API

async def fetch_tracked_guild_member_data(guild: discord.Guild, florr_guild_tag: str) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fetches member data for a specific tracked guild tag from the database.
    This is now the primary data-fetching method for lists.
    """
    print(f"Fetch DB-First Data ({guild.name}, Tag: {florr_guild_tag}): Starting fetch...")
    if not supabase:
        await log_error(guild, f"Tracked guild data fetch for '{florr_guild_tag}' failed: Supabase client unavailable.", ping_owner=True)
        return [], 0

    # 1. Fetch all members from the DB matching the specified guild tag
    db_members_data = []
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("florr_players")
                           .select("discord_id, ingame_name, discord_name, florr_guild_tag")
                           .eq("florr_guild_tag", florr_guild_tag)
                           .execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            db_members_data = resp.data
            print(f"Fetch DB-First Data: Found {len(db_members_data)} DB entries for tag '{florr_guild_tag}'.")
        else:
            return [], 0
    except Exception as e:
        await log_error(guild, f"Failed to fetch members for tag '{florr_guild_tag}' from Supabase", error=e, ping_owner=True)
        return [], 0
    
    # 2. Get all-time activity for the fetched members
    activity_summary: Dict[str, Dict[str, Any]] = {}
    all_igns_in_guild = [entry['ingame_name'] for entry in db_members_data if entry.get('ingame_name')]
    if all_igns_in_guild:
        activity_summary = await fetch_activity_data(guild, all_igns_in_guild)

    # 3. Combine data and enrich with Discord Member objects
    final_data: List[Dict[str, Any]] = []
    for member_entry in db_members_data:
        ign = member_entry.get("ingame_name")
        if not ign: continue
        
        activity = activity_summary.get(ign.lower(), {'count': 0, 'last_seen': None})
        discord_id_str = member_entry.get("discord_id")
        member_obj = guild.get_member(int(discord_id_str)) if discord_id_str else None

        final_data.append({
            "member": member_obj,
            "discord_id": discord_id_str,
            "discord_name": str(member_obj) if member_obj else member_entry.get("discord_name"),
            "ign": ign,
            "activity_count": activity.get('count', 0),
            "last_seen": activity.get('last_seen'),
            "florr_guild_tag": member_entry.get("florr_guild_tag")
        })

    # Default sort
    final_data.sort(key=lambda item: (item['member'].name.lower() if item.get('member') else (item.get('discord_name', 'zzz') or 'zzz').lower(), item['ign'].lower()))
    
    total_members = len(final_data)
    print(f"Fetch DB-First Data ({guild.name}, Tag: {florr_guild_tag}): Finished. Total members for list: {total_members}.")
    return final_data, total_members

async def get_or_create_webhook(channel: discord.TextChannel, purpose: str, name: str, avatar_url: Optional[str] = None) -> Optional[discord.Webhook]:
    """
    Fetches a webhook URL from the DB for a specific purpose, or creates one if it doesn't exist.
    Defaults to using the bot's own profile picture if no avatar_url is provided.
    """
    if not supabase:
        print(f"Webhook manager failed for purpose '{purpose}': Supabase unavailable.")
        return None

    db_resp = await run_supabase_sync(
        lambda: supabase.table("webhooks")
                       .select("webhook_url")
                       .eq("channel_id", channel.id)
                       .eq("purpose", purpose)
                       .maybe_single()
                       .execute()
    )
    if db_resp and db_resp.data and db_resp.data.get('webhook_url'):
        try:
            # Use bot's persistent session
            return discord.Webhook.from_url(db_resp.data['webhook_url'], session=bot.http_session)
        except (discord.InvalidArgument, ValueError):
            print(f"Webhook URL in DB for purpose '{purpose}' in channel {channel.id} is invalid. Recreating.")

    if not channel.permissions_for(channel.guild.me).manage_webhooks:
        print(f"Cannot create webhook for '{purpose}' in {channel.mention}: Missing 'Manage Webhooks' permission.")
        return None

    try:
        avatar_bytes = None
        # Determine which URL to use for the avatar
        url_for_avatar = avatar_url
        if url_for_avatar is None and bot.user and bot.user.display_avatar:
            # If no avatar_url is passed, default to the bot's own avatar
            url_for_avatar = bot.user.display_avatar.url

        if url_for_avatar:
            avatar_bytes = await fetch_avatar_bytes(bot.http_session, url_for_avatar)

        new_webhook = await channel.create_webhook(name=name, avatar=avatar_bytes, reason=f"Webhook for bot purpose: {purpose}")
        
        await run_supabase_sync(
            lambda: supabase.table("webhooks")
                           .upsert({
                               "discord_guild_id": channel.guild.id, "channel_id": channel.id,
                               "purpose": purpose, "webhook_url": new_webhook.url
                           }, on_conflict="channel_id, purpose")
                           .execute()
        )
        return new_webhook
    except Exception as e:
        # Don't log with log_error here to avoid potential recursion if logging itself fails
        print(f"CRITICAL: Failed to create and store webhook for '{purpose}' in {channel.mention}. Error: {e}")
        return None

def _normalize_guild_tag(tag: str) -> str:
    """Normalizes a guild tag to the format [TAG]."""
    cleaned_tag = tag.strip().upper()
    if cleaned_tag.startswith('[') and cleaned_tag.endswith(']'):
        return cleaned_tag
    return f"[{cleaned_tag}]"

async def handle_super_command(message: discord.Message):
    """Handles the owner-only //super command to fetch the next 10 craft notifications."""
    CRAFT_NOTIFY_GUILD_ID = 1332980983003349012
    CRAFT_NOTIFY_CHANNEL_ID = 1382246434513879091
    
    target_guild = bot.get_guild(CRAFT_NOTIFY_GUILD_ID)
    if not target_guild:
        await log_error(message.guild, f"//super command failed: Target guild {CRAFT_NOTIFY_GUILD_ID} not found.")
        return

    target_channel = target_guild.get_channel(CRAFT_NOTIFY_CHANNEL_ID)
    if not isinstance(target_channel, discord.TextChannel):
        await log_error(message.guild, f"//super command failed: Target channel {CRAFT_NOTIFY_CHANNEL_ID} not found or not a text channel.")
        return

    try:
        await message.add_reaction("⏳")
    except discord.HTTPException:
        pass

    crafts_to_send = []
    try:
        for _ in range(10):
            item = await asyncio.wait_for(self_bot_queue.get(), timeout=30.0)
            if item.get('category') == 'super_craft':
                crafts_to_send.append({
                    "rarity": item.get('rarity'),
                    "petal": item.get('petal'),
                    "player": item.get('player'),
                    "timestamp": item.get('timestamp')
                })
            self_bot_queue.task_done()
    except asyncio.TimeoutError:
        # Instead of message.reply(), send a new message to the channel.
        # This prevents the "Unknown message" error if the original command was deleted.
        await message.channel.send(f"{message.author.mention}, command timed out after 30s waiting for a craft notification.")
        with contextlib.suppress(discord.HTTPException):
            await message.remove_reaction("⏳", bot.user)
        return

    if not crafts_to_send:
        await message.reply("No super craft notifications were found in the queue.", mention_author=False)
        with contextlib.suppress(discord.HTTPException):
            await message.remove_reaction("⏳", bot.user)
            await message.add_reaction("❌")
        return
        
    webhook = await get_or_create_webhook(target_channel, "craft_notify", "Craft Notify")
    if not webhook:
        await message.reply("Failed to get or create the webhook for craft notifications. Check logs.", mention_author=False)
        return
        
    json_payload = json.dumps(crafts_to_send, indent=4)
    
    try:
        json_file = discord.File(io.BytesIO(json_payload.encode('utf-8')), filename="crafts_log.json")
        await webhook.send(f"Collected {len(crafts_to_send)} craft notifications:", file=json_file)
        with contextlib.suppress(discord.HTTPException):
            await message.remove_reaction("⏳", bot.user)
            await message.add_reaction("✅")
    except Exception as e:
        await log_error(target_guild, "Failed to send craft notifications via webhook", error=e)
        await message.reply(f"Error sending notifications: {e}", mention_author=False)
        with contextlib.suppress(discord.HTTPException):
            await message.remove_reaction("⏳", bot.user)
            await message.add_reaction("🔥")

async def is_admin_or_owner(interaction: discord.Interaction) -> bool:
    """Check if the user is a server admin or the bot owner."""
    if interaction.user.id == OWNER_USER_ID:
        return True
    if interaction.guild and isinstance(interaction.user, discord.Member):
        return interaction.user.guild_permissions.administrator
    return False

# Add this new core function
async def load_server_config(guild_id: int) -> Dict[str, Any]:
    """
    Loads configuration for a guild from cache or DB.
    Also fetches and attaches tracked_florr_guilds data.
    """
    if guild_id in server_settings_cache:
        return server_settings_cache[guild_id]
    if not supabase:
        print(f"Config Load: Supabase unavailable for guild {guild_id}.")
        return {}

    print(f"Config Cache Miss: Fetching settings for guild {guild_id} from DB.")
    config_data: Dict[str, Any] = {}
    try:
        # Fetch main config
        main_resp = await run_supabase_sync(
            lambda: supabase.table(SERVER_CONFIGS_TABLE_NAME)
                           .select("*").eq("guild_id", guild_id).maybe_single().execute()
        )
        if main_resp and main_resp.data:
            config_data = main_resp.data
        else:
            # No config found, create a default one
            print(f"No config found for guild {guild_id}. Creating default entry.")
            default_data = {'guild_id': guild_id} # No bot_enabled default needed
            insert_resp = await run_supabase_sync(
                lambda: supabase.table(SERVER_CONFIGS_TABLE_NAME).insert(default_data).execute()
            )
            config_data = insert_resp.data[0] if insert_resp.data else default_data

        # Fetch tracked Florr guilds for this Discord guild
        tracked_resp = await run_supabase_sync(
            lambda: supabase.table("tracked_florr_guilds")
                           .select("*").eq("discord_guild_id", guild_id).execute()
        )
        # Store tracked guilds in a nested dictionary for easy lookup by tag
        config_data['tracked_guilds'] = {
            entry['florr_guild_tag']: entry for entry in (tracked_resp.data or [])
        }
        
        server_settings_cache[guild_id] = config_data
        return config_data
    except Exception as e:
        print(f"CRITICAL: Failed to load/create server config for guild {guild_id}: {e}")
        await log_error(bot.get_guild(guild_id), "Failed to load server config", error=e, ping_owner=True)
        return {'tracked_guilds': {}} # Return safe default # Return safe default

class ServerCodeView(discord.ui.View):
    """An interactive view for browsing Florr.io server codes with region and map filters."""
    # Constants for mappings
    REGION_MAP = {"na": "vultr-miami", "eu": "vultr-frankfurt", "as": "vultr-tokyo"}
    MAP_ID_MAP = {
        "garden": "0", "desert": "1", "ocean": "2", "jungle": "3",
        "ant hell": "4", "hel": "5", "sewers": "6", "factory": "7",
        "pyramid": "8"
    }
    REVERSE_REGION_MAP = {v: k.upper() for k, v in REGION_MAP.items()}
    REVERSE_MAP_ID_MAP = {v: k.title() for k, v in MAP_ID_MAP.items()}

    def __init__(self, initial_region: Optional[str], initial_map: Optional[str]):
        super().__init__(timeout=300.0)  # 5 minute timeout
        self.current_region = initial_region or "eu"
        self.current_map_name = initial_map
        self.message: Optional[discord.Message] = None
        
        # If the view starts with a map filter, it should be in multi-region mode.
        self.multi_region_mode = bool(initial_map)
        
        self._update_components()

    def _update_components(self):
        """Clears and re-adds all UI components based on the current state."""
        self.clear_items()
        
        # Row 0: Region Buttons (Servers)
        regions = [("NA", "na"), ("EU", "eu"), ("AS", "as")]
        for label, value in regions:
            is_selected = self.current_region == value and not self.multi_region_mode
            button = discord.ui.Button(
                label=f"{label} Servers",
                style=discord.ButtonStyle.primary if is_selected else discord.ButtonStyle.secondary,
                disabled=is_selected,
                custom_id=f"servercode_region_{value}",
                row=0
            )
            button.callback = self.region_button_callback
            self.add_item(button)

        # Row 1: Map Select (Biomes)
        select_options = [
            discord.SelectOption(
                label="All Biomes in Region",
                value="all_maps",
                emoji="🗺️",
                default=(not self.current_map_name)
            )
        ]
        for map_name_key in self.MAP_ID_MAP.keys():
            select_options.append(discord.SelectOption(
                label=map_name_key.title(), 
                value=map_name_key,
                default=(self.current_map_name == map_name_key)
            ))

        map_select = discord.ui.Select(
            placeholder="Filter by Biome...",
            options=select_options,
            custom_id="servercode_map_select",
            row=1
        )
        map_select.callback = self.map_select_callback
        self.add_item(map_select)

    async def region_button_callback(self, interaction: discord.Interaction):
        """Handles clicks on the region buttons."""
        self.multi_region_mode = False
        custom_id = interaction.data['custom_id']
        self.current_region = custom_id.split('_')[-1]
        self.current_map_name = None 
        
        self._update_components()
        embed = await self._create_server_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def map_select_callback(self, interaction: discord.Interaction):
        """Handles selection from the map dropdown."""
        selected_value = interaction.data['values'][0]
        
        if selected_value == "all_maps":
            self.multi_region_mode = False
            self.current_map_name = None
        else:
            # Selecting ANY specific biome puts us in multi-region mode.
            self.multi_region_mode = True
            self.current_map_name = selected_value
        
        self._update_components()
        embed = await self._create_server_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _create_server_embed(self) -> discord.Embed:
        """Builds the server list embed based on the current view state."""
        async with m28_server_list_lock:
            servers_to_filter = m28_server_list.copy()

        if not servers_to_filter:
            return discord.Embed(title="⏳ Servers Temporarily Unavailable", description="The server list is currently empty. Please try again in a minute.", color=discord.Color.orange())

        # --- Multi-Region Biome View ---
        if self.multi_region_mode and self.current_map_name:
            embed = discord.Embed(
                title=f"🗺️ Servers for '{self.current_map_name.title()}' Biome (All Regions)",
                description=f"Showing all available servers for the **{self.current_map_name.title()}** biome.",
                color=NERDY_YELLOW
            )
            target_map_id_val = self.MAP_ID_MAP.get(self.current_map_name)
            
            map_filtered_servers = {sid: det for sid, det in servers_to_filter.items() if det.get("map_id") == target_map_id_val}
            grouped_by_region: Dict[str, List[str]] = {}
            for server_id, details in map_filtered_servers.items():
                region_val = details.get("region", "Unknown")
                if region_val not in grouped_by_region: grouped_by_region[region_val] = []
                grouped_by_region[region_val].append(server_id)

            total_found = 0
            for region_code, region_data_key in [("na", "vultr-miami"), ("eu", "vultr-frankfurt"), ("as", "vultr-tokyo")]:
                server_codes = sorted(grouped_by_region.get(region_data_key, []))
                if server_codes:
                    total_found += len(server_codes)
                    code_string = " ".join([f'```js\ncp6.forceServerID("{sid}")\n```' for sid in server_codes])
                    embed.add_field(name=f"📍 {region_code.upper()} Servers", value=code_string, inline=False)
            
            if total_found == 0:
                embed.description += f"\n\n❌ No **{self.current_map_name.title()}** servers were found in any region."
            
            embed.set_footer(text=f"Found {total_found} servers. Use buttons/dropdown to change view.")
            return embed

        # --- Standard Single-Region View ---
        target_region_val = self.REGION_MAP.get(self.current_region)
        region_display = self.current_region.upper()
        embed = discord.Embed(title=f"🎮 Florr.io Server Codes [{region_display}]", color=NERDY_YELLOW)
        
        filtered_servers = {sid: det for sid, det in servers_to_filter.items() if det.get("region") == target_region_val}
        
        if not filtered_servers:
            embed.description = f"❌ No servers found in the **{region_display}** region."
            embed.color = discord.Color.red()
        else:
            grouped_by_map: Dict[str, List[str]] = {}
            for server_id, details in filtered_servers.items():
                map_id = details.get("map_id", "Unknown")
                if map_id not in grouped_by_map: grouped_by_map[map_id] = []
                grouped_by_map[map_id].append(server_id)
            
            sorted_map_ids = sorted(grouped_by_map.keys(), key=lambda x: int(x) if x.isdigit() else 99)
            
            for map_id_key in sorted_map_ids:
                map_display_name = self.REVERSE_MAP_ID_MAP.get(map_id_key, f"Map {map_id_key}")
                server_codes = sorted(grouped_by_map[map_id_key])
                code_string = " ".join([f'```js\ncp6.forceServerID("{sid}")\n```' for sid in server_codes])
                embed.add_field(name=f"🗺️ {map_display_name} Biome", value=code_string, inline=False)

        embed.set_footer(text=f"Found {len(filtered_servers)} servers in {region_display}. Use buttons/dropdown to filter.")
        if len(embed) > 5900:
            return discord.Embed(title="⚠️ Too Much Data!", description="Result is too large to display.", color=discord.Color.red())
        return embed

    async def on_timeout(self):
        if self.message:
            self.clear_items()
            try: await self.message.edit(view=self)
            except discord.HTTPException: pass
        self.stop()

async def scrape_and_clean_m28_servers():
    """
    Scrapes all map endpoints for server data and updates the global list.
    This function is called by the background task.
    """
    global m28_server_list

    # Includes maps 0 through 8 (Pyramid)
    map_ids_to_query = range(9)
    tasks = []

    try:
        # The new query_m28_map_endpoint function only needs the map_id.
        # It now uses the persistent bot.http_session internally. We also
        # don't need to wrap it in asyncio.create_task here, as gather handles it.
        for map_id in map_ids_to_query:
            tasks.append(query_m28_map_endpoint(map_id))
        
        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        # Log error if the entire session or gather fails
        print(f"M28 Scraper: Main scraping session failed: {e}")
        # Use log_error if a guild context is available, otherwise just print
        if bot.guilds:
            await log_error(bot.get_guild(CATERCORD_GUILD_ID), "M28 Scraper: Main scraping session failed.", error=e)

async def query_m28_map_endpoint(map_id: int):
    """Fetches and processes server data for a single map ID using the bot's session."""
    global m28_server_list
    url = f"https://api.n.m28.io/endpoint/florrio-map-{map_id}-green/findEach/"
    try:
        # Use the bot's persistent session
        async with bot.http_session.get(url, timeout=10) as response:
            if response.status != 200:
                print(f"M28 Scraper: API request for map {map_id} failed with status {response.status}")
                return
            
            data = await response.json()
            servers_in_map = data.get("servers", {})
            
            async with m28_server_list_lock:
                for region_key, server_details in servers_in_map.items():
                    server_id = server_details.get("id")
                    if not server_id:
                        continue
                    
                    m28_server_list[server_id] = {
                        "region": region_key,
                        "map_id": str(map_id),
                        "timestamp": discord.utils.utcnow().timestamp()
                    }

    except asyncio.TimeoutError:
        print(f"M28 Scraper: Timeout while fetching map {map_id}.")
    except Exception as e:
        print(f"M28 Scraper: Error processing map {map_id}: {e}")

@tasks.loop(minutes=1.0) # Run this check every minute
async def m28_server_scraper():
    """
    Background task to periodically scrape servers.
    Scrapes Ant Hell every minute and all other maps every 5 minutes.
    """
    global m28_server_list, m28_scrape_counter
    
    await bot.wait_until_ready()
    print("M28 Scraper: Running periodic server scrape check...")
    
    ant_hell_map_id = 4 # The ID for Ant Hell from ServerCodeView.MAP_ID_MAP
    map_ids_to_query = []

    # The counter increments each minute.
    # On the first run (0) and every 5th run, scrape all maps.
    if m28_scrape_counter % 5 == 0:
        print("M28 Scraper: Performing full scrape (all maps).")
        map_ids_to_query = range(9) # All maps from 0 to 8
    else:
        # On other minutes, only scrape Ant Hell.
        print(f"M28 Scraper: Performing partial scrape (Ant Hell only).")
        map_ids_to_query = [ant_hell_map_id]

    # --- Scrape the selected maps ---
    tasks = []
    try:
        # No need to create a new session, as query_m28_map_endpoint uses the persistent bot.http_session
        for map_id in map_ids_to_query:
            tasks.append(query_m28_map_endpoint(map_id)) # Pass only map_id
        
        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        print(f"M28 Scraper: Main scraping session failed: {e}")
        if bot.guilds:
            await log_error(bot.get_guild(CATERCORD_GUILD_ID), "M28 Scraper: Main scraping session failed.", error=e)
            
    # Increment the counter for the next run
    m28_scrape_counter += 1

    # --- Cleanup Stale Servers (runs every minute regardless of which maps were scraped) ---
    stale_servers = []
    current_time = discord.utils.utcnow().timestamp()
    
    async with m28_server_list_lock:
        for server_id, details in m28_server_list.items():
            if (current_time - details.get("timestamp", 0)) > M28_SERVER_TIMEOUT_SECONDS:
                stale_servers.append(server_id)
        
        if stale_servers:
            print(f"M28 Scraper: Cleaning up {len(stale_servers)} stale server entries.")
            for server_id in stale_servers:
                if server_id in m28_server_list:
                    del m28_server_list[server_id]
                    
    print(f"M28 Scraper: Scrape check complete. Total servers tracked: {len(m28_server_list)}")

async def handle_zorr_pro_automod(message: discord.Message):
    """Handles the zorr.pro automod alert by relaying the message."""
    guild = message.guild
    if not guild or not message.embeds:
        return

    embed = message.embeds[0]
    original_message_content = embed.description
    user_id_from_field: Optional[int] = None
    original_channel_id_from_fields: Optional[int] = None
    rule_name_from_fields: Optional[str] = None

    for field in embed.fields:
        if field.name == "user_id":
            try: user_id_from_field = int(field.value)
            except (ValueError, TypeError): pass
        elif field.name == "channel_id":
            try: original_channel_id_from_fields = int(field.value)
            except (ValueError, TypeError):
                await log_error(guild, f"ZorrRedirect: Could not parse channel_id '{field.value}' from embed field.", ping_owner=True)
                return
        elif field.name == "rule_name":
            rule_name_from_fields = str(field.value).strip()

    actual_message_author = guild.get_member(user_id_from_field) if user_id_from_field else None
    is_zorr_pro_trigger = bool(rule_name_from_fields and "zorr.pro blocker" in rule_name_from_fields.lower())

    if not all([actual_message_author, original_channel_id_from_fields, original_message_content, is_zorr_pro_trigger]):
        return

    if original_channel_id_from_fields == ZORR_PRO_DESIGNATED_CHANNEL_ID:
        return

    original_channel_obj = guild.get_channel(original_channel_id_from_fields)
    original_channel_name = f"#{original_channel_obj.name}" if original_channel_obj else f"ID {original_channel_id_from_fields}"
    designated_channel = guild.get_channel(ZORR_PRO_DESIGNATED_CHANNEL_ID)

    if not isinstance(designated_channel, discord.TextChannel):
        await log_error(guild, f"ZorrRedirect: Designated channel {ZORR_PRO_DESIGNATED_CHANNEL_ID} invalid.", ping_owner=True)
        return

    info_message = f"{actual_message_author.mention}, your message related to zorr.pro was blocked in {original_channel_name}. Please discuss here in {designated_channel.mention}. I'll re-post your message:"
    await designated_channel.send(info_message)

    temp_webhook: Optional[discord.Webhook] = None
    try:
        avatar_url = actual_message_author.display_avatar.url if actual_message_author.display_avatar else actual_message_author.default_avatar.url
        async with aiohttp.ClientSession() as session:
            avatar_bytes = await fetch_avatar_bytes(session, avatar_url)
        
        webhook_name = actual_message_author.display_name[:80]
        if any(d in webhook_name.lower() for d in ["@", "#", ":", "```", "discord"]) or webhook_name.lower() == "clyde":
            webhook_name = "Relayed Message"
            
        temp_webhook = await designated_channel.create_webhook(name=webhook_name, avatar=avatar_bytes, reason="Zorr.pro AutoMod relay")
        await temp_webhook.send(content=original_message_content[:2000], wait=True)
    except Exception as e:
        await log_error(guild, "ZorrRedirect: Error during imitation.", error=e, ping_owner=True)
    finally:
        if temp_webhook:
            try: await temp_webhook.delete(reason="Zorr.pro AutoMod relay cleanup")
            except Exception: pass

async def handle_screenshot_dropbox(message: discord.Message):
    """Handles messages with images in the screenshot dropbox channel."""
    valid_images = [att for att in message.attachments if att.content_type and att.content_type.startswith("image/")]
    if not valid_images:
        return

    user_id = message.author.id
    active_session = guild_sync_sessions.get(user_id)
    
    if active_session and (discord.utils.utcnow() - active_session['last_update_time']).total_seconds() > GUILD_SYNC_SESSION_TIMEOUT_SECONDS:
        await log_info(message.guild, f"GuildSync: Stale session found for user {user_id} and cleaned up.")
        del guild_sync_sessions[user_id]
        active_session = None

    image_bytes_list = []
    for img_att in valid_images:
        try:
            image_bytes_list.append(await img_att.read())
        except discord.HTTPException as e:
            await log_error(message.guild, f"Failed to read attachment {img_att.filename} for GuildSync", error=e)

    if not image_bytes_list:
        await message.reply("❌ Could not read any of the attached images.", mention_author=False)
        return

    if len(image_bytes_list) >= 10 or (active_session and len(image_bytes_list) > 0):
        is_new_session = not active_session
        
        await log_info(message.guild, f"GuildSync Mode: {'Starting new session' if is_new_session else 'Adding batch'} for {message.author.name} with {len(image_bytes_list)} image(s).")
        asyncio.create_task(process_guild_sync_batch(message, image_bytes_list, is_new_session))
    elif active_session:
        try:
            await message.reply(
                f"{message.author.mention}, you have an active guild sync session. Send more screenshots to continue, or use the buttons on my last reply to finalize.",
                delete_after=30.0
            )
        except discord.HTTPException: pass
    else:
        await handle_guild_sync_from_screenshots(message, valid_images)

async def handle_super_attempt_message(message: discord.Message):
    """Processes a message to check for and log a super attempt."""
    # This function contains all the logic previously in on_message for this feature
    guild = message.guild
    msg_content = message.content.strip()
    attempt_match = re.fullmatch(r"-(?P<petals>[1-4])\s*(?P<petal_query>.+)", msg_content, re.IGNORECASE)

    if not attempt_match:
        return # Not a super attempt message

    # --- Start of Super Attempt Logic (copied from on_message) ---
    petals_lost_str = attempt_match.group("petals")
    petal_query_str = attempt_match.group("petal_query").strip()
    try:
        petals_lost = int(petals_lost_str)
    except ValueError:
        return
    if not petal_query_str:
        return

    author_ign = await get_ign_from_user(guild, message.author.id)
    if not author_ign:
        try:
            await message.reply(f"{message.author.mention}, your IGN isn't linked. Use `/guild` or `/verify`.")
        except discord.HTTPException:
            pass
        return

    attempt_date_obj, date_error_msg = get_utc_date()
    if date_error_msg or not attempt_date_obj:
        try:
            await message.reply("Sorry, error determining date.")
        except discord.HTTPException:
            pass
        await log_error(guild, f"Super Attempt Log: Failed to get UTC date. Error: {date_error_msg}", message_context=message)
        return

    if not await check_supabase_available(message.channel): # type: ignore
        await log_info(guild, f"Super Attempt Log for '{petal_query_str}': Supabase unavailable.")
        return

    ultra_candidates = await find_ultra_petal_candidates_for_query(petal_query_str, guild)
    bot_reply_msg: Optional[discord.Message] = None

    if len(ultra_candidates) == 1:
        # ... (rest of single candidate logic from on_message)
        chosen_petal_data = ultra_candidates[0]
        chosen_petal_name_for_db = chosen_petal_data['original_full_name']
        display_friendly_name_for_reply = chosen_petal_data['display_friendly_name']
        try:
            insert_resp = await run_supabase_sync(lambda: supabase.table("super_attempts").insert({"ingame_name": author_ign, "discord_user_id": str(message.author.id),"attempt_date": attempt_date_obj.isoformat(), "petals_lost": petals_lost,"message_id": str(message.id), "channel_id": str(message.channel.id),"chosen_petal_name": chosen_petal_name_for_db}).execute())
            attempt_db_id = None
            if insert_resp.data and len(insert_resp.data) > 0 and 'id' in insert_resp.data[0]:
                attempt_db_id = insert_resp.data[0]['id']
            if not attempt_db_id:
                fetch_id_resp = await run_supabase_sync(lambda: supabase.table("super_attempts").select("id").eq("message_id", str(message.id)).eq("ingame_name", author_ign).eq("chosen_petal_name", chosen_petal_name_for_db).order("recorded_at", desc=True).limit(1).maybe_single().execute())
                attempt_db_id = fetch_id_resp.data['id'] if fetch_id_resp.data and fetch_id_resp.data.get('id') is not None else None
            if not attempt_db_id:
                await log_error(guild, f"Super Attempt (single): Failed to get DB ID for {author_ign}", message_context=message)
                try:
                    await message.reply("Error saving (no DB ID). Admin notified.")
                except discord.HTTPException:
                    pass
                await _update_reactions(message, "error")
                return
            all_time_attempts_count = await get_all_time_super_attempt_count(guild, author_ign)
            sa_view = SuperAttemptConfirmView(message.author.id, attempt_db_id, petals_lost, display_friendly_name_for_reply, author_ign, all_time_attempts_count, message)
            embed = sa_view.create_embed()
            bot_reply_msg = await message.reply(content=f"{message.author.mention}", embed=embed, view=sa_view)
            sa_view.message = bot_reply_msg
            await _update_reactions(message, "success")
            await log_info(guild, f"Super attempt by `{author_ign}`: Lost {petals_lost}x {display_friendly_name_for_reply}. All-time: {all_time_attempts_count}.")
            if isinstance(message.author, discord.Member):
                await update_custom_nickname_on_attempt(guild, message.author, author_ign, all_time_attempts_count)
        except Exception as e:
            await log_error(guild, f"Error logging single super attempt for {author_ign}", error=e, message_context=message, ping_owner=True)
            try:
                await message.reply("Error logging attempt. Admin notified.")
            except discord.HTTPException:
                pass
            await _update_reactions(message, "error")

    elif len(ultra_candidates) > 1:
        # ... (rest of ambiguous candidate logic from on_message)
        disamb_embed = discord.Embed(title="❓ Which Ultra Petal Was It?", description=f"{message.author.mention}, \"{discord.utils.escape_markdown(petal_query_str)}\" could be multiple. Choose one:", color=discord.Color.blue())
        sa_disamb_view = SuperAttemptDisambiguationView(message.author.id, ultra_candidates, petals_lost, message, author_ign, attempt_date_obj)
        bot_reply_msg = await message.reply(embed=disamb_embed, view=sa_disamb_view)
        sa_disamb_view.message = bot_reply_msg
        await _update_reactions(message, "disambiguation")

    else:
        # ... (rest of "Unknown" logic from on_message)
        chosen_petal_name_for_db = "Unknown Ultra Petal"
        display_friendly_name_for_reply = "Unknown Ultra"
        await log_info(guild, f"Super Attempt: No Ultra match for '{petal_query_str}' by {author_ign}. Logging as Unknown.")
        try:
            insert_resp = await run_supabase_sync(lambda: supabase.table("super_attempts").insert({"ingame_name": author_ign, "discord_user_id": str(message.author.id),"attempt_date": attempt_date_obj.isoformat(), "petals_lost": petals_lost,"message_id": str(message.id), "channel_id": str(message.channel.id),"chosen_petal_name": chosen_petal_name_for_db}).execute())
            attempt_db_id = None
            if insert_resp.data and len(insert_resp.data) > 0 and 'id' in insert_resp.data[0]:
                attempt_db_id = insert_resp.data[0]['id']
            if not attempt_db_id:
                fetch_id_resp = await run_supabase_sync(lambda: supabase.table("super_attempts").select("id").eq("message_id", str(message.id)).order("recorded_at", desc=True).limit(1).maybe_single().execute())
                attempt_db_id = fetch_id_resp.data['id'] if fetch_id_resp.data and fetch_id_resp.data.get('id') is not None else None
            if not attempt_db_id:
                await log_error(guild, f"Super Attempt (Unknown): Failed to get DB ID for {author_ign}", message_context=message)
                try:
                    await message.reply("Error saving (no DB ID for unknown). Admin notified.")
                except discord.HTTPException:
                    pass
                await _update_reactions(message, "error")
                return
            all_time_attempts_count = await get_all_time_super_attempt_count(guild, author_ign)
            sa_view = SuperAttemptConfirmView(message.author.id, attempt_db_id, petals_lost, display_friendly_name_for_reply, author_ign, all_time_attempts_count, message)
            embed = sa_view.create_embed()
            bot_reply_msg = await message.reply(content=f"{message.author.mention}", embed=embed, view=sa_view)
            sa_view.message = bot_reply_msg
            await _update_reactions(message, "success")
            await log_info(guild, f"Super attempt by `{author_ign}`: Lost {petals_lost}x {display_friendly_name_for_reply}. All-time: {all_time_attempts_count}.")
            if isinstance(message.author, discord.Member):
                await update_custom_nickname_on_attempt(guild, message.author, author_ign, all_time_attempts_count)
        except Exception as e:
            await log_error(guild, f"Error logging 'Unknown Ultra Petal' for {author_ign}", error=e, message_context=message, ping_owner=True)
            try:
                await message.reply("Error logging unknown petal. Admin notified.")
            except discord.HTTPException:
                pass
            await _update_reactions(message, "error")

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
    message: discord.Message,
    image_bytes_list: List[bytes],
    is_new_session: bool
) -> Optional[discord.Message]:
    """Processes a batch of screenshots for guild sync, updating or creating a session."""
    guild = message.guild
    user = message.author
    user_id = user.id
    
    ai_cog = bot.get_cog('AICog')
    if not ai_cog:
        await log_error(guild, "GuildSync: AICog not found during batch processing.", message_context=message)
        if is_new_session:
            try: return await message.reply(f"{user.mention} ❌ AI Module error. Sync aborted.")
            except discord.HTTPException: pass
        return None

    # Determine the target guild for this sync session
    target_guild_tag = None
    known_igns_for_ai = []
    if is_new_session:
        user_ign = await get_ign_from_user(guild, user.id)
        if user_ign:
            player_data_resp = await run_supabase_sync(lambda: supabase.table("florr_players").select("florr_guild_tag").eq("ingame_name", user_ign).maybe_single().execute())
            if player_data_resp and player_data_resp.data:
                target_guild_tag = player_data_resp.data.get('florr_guild_tag')
        
        if not target_guild_tag:
            try: return await message.reply(f"{user.mention} ❌ Could not determine your Florr guild from your database record. Please use `/setguild` first.")
            except discord.HTTPException: pass
            return None
            
        guild_members_resp = await run_supabase_sync(lambda: supabase.table("florr_players").select("ingame_name").eq("florr_guild_tag", target_guild_tag).execute())
        if guild_members_resp and guild_members_resp.data:
            known_igns_for_ai = [entry['ingame_name'] for entry in guild_members_resp.data]
    else: # Existing session
        session_data = guild_sync_sessions.get(user_id, {})
        target_guild_tag = session_data.get('target_guild_tag')
        known_igns_for_ai = session_data.get('known_igns_for_ai', [])

    if not target_guild_tag or not known_igns_for_ai:
        msg = f"{user.mention} ❌ Could not find members for guild `{target_guild_tag}`. Sync aborted." if target_guild_tag else f"{user.mention} ❌ Sync failed: Could not determine target guild."
        try: return await message.reply(msg)
        except discord.HTTPException: pass
        if user_id in guild_sync_sessions: del guild_sync_sessions[user_id]
        return None

    extracted_from_this_batch: Set[str] = set()
    known_igns_list_for_ai_str = "\n".join(known_igns_for_ai)

    # --- BATCHED AI CALL ---
    ai_extracted_text = await ai_cog.get_ai_response_with_image(
        prompt_key="FLORR_GUILD_LIST_FULL_EXTRACTION",
        image_bytes_list=image_bytes_list,
        prompt_kwargs={'known_igns_list_str': known_igns_list_for_ai_str}
    )

    if ai_extracted_text and ai_extracted_text.strip().upper() != "NO_NAMES_FOUND":
        # Clean IGNs from AI output to remove any backslashes
        extracted_from_this_batch = {clean_ign(name) for name in ai_extracted_text.split('\n') if name.strip()}
    
    failed_ai_this_batch = not bool(ai_extracted_text)

    if is_new_session:
        if not extracted_from_this_batch and failed_ai_this_batch:
            return await message.reply(f"{user.mention} ❌ AI failed to extract names from all initial images. Sync aborted.")
        
        guild_sync_sessions[user_id] = {
            'target_guild_tag': target_guild_tag,
            'known_igns_for_ai': known_igns_for_ai,
            'screenshot_igns_collected': extracted_from_this_batch,
            'bot_reply_message_id': 0,
            'last_update_time': discord.utils.utcnow()
        }
        session_data = guild_sync_sessions[user_id]
        
        reply_content = f"{user.mention} ✅ Initial batch processed for **{target_guild_tag}**. **{len(extracted_from_this_batch)}** unique IGNs collected so far."
        view = GuildSyncInProgressView(user_id, user_id)
        bot_reply_msg = await message.reply(content=reply_content, view=view)
        session_data['bot_reply_message_id'] = bot_reply_msg.id
        view.message = bot_reply_msg
        await log_info(guild, f"GuildSync: New session started for {user.name} ({target_guild_tag}). Collected {len(extracted_from_this_batch)} IGNs.")
        return bot_reply_msg
    else: # Existing session
        session_data = guild_sync_sessions.get(user_id)
        if not session_data:
            await log_error(guild, f"GuildSync: Tried to add to non-existent session for user {user_id}.")
            return None 
        
        # --- ROBUST MESSAGE UPDATE LOGIC ---
        # Delete old status message if it exists
        if session_data.get('bot_reply_message_id'):
            try:
                old_msg = await message.channel.fetch_message(session_data['bot_reply_message_id'])
                await old_msg.delete()
            except (discord.NotFound, discord.HTTPException):
                pass # Ignore if already gone

        newly_added_count = len(extracted_from_this_batch - session_data['screenshot_igns_collected'])
        session_data['screenshot_igns_collected'].update(extracted_from_this_batch)
        session_data['last_update_time'] = discord.utils.utcnow()
        
        update_msg_content = f"{user.mention} ✅ Batch processed. Added **{newly_added_count}** new unique IGNs. **Total collected: {len(session_data['screenshot_igns_collected'])}**."
        if failed_ai_this_batch:
            update_msg_content += f" (AI may have failed to process this batch)."

        # Send a new message with the updated view
        new_view = GuildSyncInProgressView(user_id, user_id)
        new_bot_reply_msg = await message.channel.send(content=update_msg_content, view=new_view)
        new_view.message = new_bot_reply_msg
        session_data['bot_reply_message_id'] = new_bot_reply_msg.id

        await log_info(guild, f"GuildSync: Added {newly_added_count} IGNs to session for {user.name}. Total: {len(session_data['screenshot_igns_collected'])}. Failures: {failed_ai_this_batch}")
        return new_bot_reply_msg # Or None if not fetched/edited # Or None if not fetched/edited


async def generate_final_sync_report_embed_only(guild: Optional[discord.Guild], user: discord.User, user_id_session_key: int) -> Optional[discord.Embed]:
    """Generates the final guild sync report embed. Returns Embed or None on failure or if no data."""
    session_data = guild_sync_sessions.get(user_id_session_key)
    if not session_data:
        if guild: await log_error(guild, f"GuildSync Report Gen: Session data not found for user ID {user_id_session_key}.")
        return None

    collected_screenshot_igns = session_data.get('screenshot_igns_collected', set())
    target_guild_tag = session_data.get('target_guild_tag') # The tag this sync session is for

    if not collected_screenshot_igns:
        return discord.Embed(title="Guild Sync Report", description="No IGNs were collected from screenshots.", color=discord.Color.orange())
    if not target_guild_tag:
        return discord.Embed(title="Guild Sync Report", description="Error: Could not determine the target Florr guild for this sync session.", color=discord.Color.red())

    db_members = await fetch_all_db_members_with_guild_tag(guild)
    
    ss_igns_lower = {ign.lower() for ign in collected_screenshot_igns}
    db_map_lower_to_original: Dict[str, Dict[str, Any]] = {entry['ingame_name'].lower(): entry for entry in db_members}

    not_in_db = []
    in_db_no_guild = []
    in_db_wrong_guild = []
    in_db_target_guild_not_in_ss = []

    for s_ign in collected_screenshot_igns:
        s_ign_l = s_ign.lower()
        db_entry = db_map_lower_to_original.get(s_ign_l)
        if not db_entry:
            not_in_db.append(s_ign)
        elif not db_entry.get('florr_guild_tag'):
            in_db_no_guild.append(s_ign)
        elif db_entry.get('florr_guild_tag') != target_guild_tag:
            in_db_wrong_guild.append(f"{s_ign} (in {db_entry['florr_guild_tag']})")

    for db_ign_l, db_entry_data in db_map_lower_to_original.items():
        if db_entry_data.get('florr_guild_tag') == target_guild_tag:
            if db_ign_l not in ss_igns_lower:
                in_db_target_guild_not_in_ss.append(db_entry_data['ingame_name'])

    potential_typos = find_potential_ign_typos(collected_screenshot_igns, db_members, target_guild_tag)
    
    report_embed = discord.Embed(
        title=f"Guild Member Sync Report for {target_guild_tag}",
        description=f"Processed **{len(collected_screenshot_igns)}** unique IGNs from screenshots and compared against **{len(db_members)}** total database entries.",
        color=NERDY_YELLOW
    )
    report_embed.timestamp = discord.utils.utcnow()

    def format_field_value(items: List[str], max_items_display=15) -> str:
        if not items: return "None found."
        items_sorted = sorted(items, key=str.lower)
        # REMOVED redundant escape_markdown call for values inside code blocks
        lines = [f"- `{ign}`" for ign in items_sorted[:max_items_display]]
        if len(items) > max_items_display: lines.append(f"- ...and {len(items) - max_items_display} more.")
        return "\n".join(lines)

    if not_in_db: report_embed.add_field(name=f"⚠️ In SS, NOT IN DB ({len(not_in_db)})", value=format_field_value(not_in_db), inline=False)
    if in_db_no_guild: report_embed.add_field(name=f"🟡 In SS, IN DB but No Guild Set ({len(in_db_no_guild)})", value=format_field_value(in_db_no_guild), inline=False)
    if in_db_wrong_guild: report_embed.add_field(name=f"🌐 In SS, IN DB but Wrong Guild ({len(in_db_wrong_guild)})", value=format_field_value(in_db_wrong_guild), inline=False)
    if in_db_target_guild_not_in_ss: report_embed.add_field(name=f"❓ In DB ({target_guild_tag}), NOT IN SS ({len(in_db_target_guild_not_in_ss)})", value=format_field_value(in_db_target_guild_not_in_ss), inline=False)
    
    if potential_typos:
        typo_lines = [f"- SS: `{s}` vs DB: `{d}` ({t}, {scr*100:.1f}%)" for s, d, t, scr in potential_typos[:10]]
        if len(potential_typos) > 10: typo_lines.append(f"- ...and {len(potential_typos) - 10} more.")
        report_embed.add_field(name=f"🤔 Potential Typos ({len(potential_typos)})", value="\n".join(typo_lines), inline=False)

    if not report_embed.fields:
        report_embed.description += "\n\n✅ **All Clear!** No major discrepancies identified."

    report_embed.set_footer(text=f"Finalized by {user.display_name}")
    return report_embed

async def fetch_all_db_members_with_guild_tag(guild: Optional[discord.Guild]) -> List[Dict[str, Any]]:
    """Fetches all members from Supabase, including their ingame_name, discord_id, and florr_guild_tag."""
    if not supabase:
        if guild: await log_error(guild, "GuildSync: Supabase unavailable for fetching DB members with guild tag.")
        return []
    
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("florr_players")
                           .select("ingame_name, discord_id, florr_guild_tag")
                           .not_.is_("ingame_name", "null")
                           .execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            return [{'ingame_name': e['ingame_name'], 'discord_id': str(e.get('discord_id')), 'florr_guild_tag': e.get('florr_guild_tag')} for e in resp.data if e.get('ingame_name')]
        return []
    except Exception as e:
        if guild: await log_error(guild, "GuildSync: Error fetching all members with guild tags from DB", error=e)
        return []

def find_potential_ign_typos(screenshot_igns: Set[str], db_members: List[Dict[str, Any]], target_guild_tag: str, threshold: float = 0.85) -> List[Tuple[str, str, str, float]]:
    """Finds potential typos, comparing SS IGNs to all DB IGNs."""
    potential_typos = []
    db_ign_names_only_set = {entry['ingame_name'] for entry in db_members}
    unique_screenshot_igns = screenshot_igns - db_ign_names_only_set

    for s_ign in unique_screenshot_igns:
        best_matches = difflib.get_close_matches(s_ign, [entry['ingame_name'] for entry in db_members], n=1, cutoff=threshold)
        if best_matches:
            best_db_name = best_matches[0]
            matched_entry = next((entry for entry in db_members if entry['ingame_name'] == best_db_name), None)
            if matched_entry:
                db_tag = matched_entry.get('florr_guild_tag') or "No Guild"
                tag_display = "Target Guild" if db_tag == target_guild_tag else f"In {db_tag}"
                ratio = difflib.SequenceMatcher(None, s_ign, best_db_name).ratio()
                potential_typos.append((s_ign, best_db_name, tag_display, round(ratio, 3)))
    
    potential_typos.sort(key=lambda x: x[3], reverse=True)
    return potential_typos

async def fetch_all_db_florr_players_for_sync(guild: Optional[discord.Guild]) -> List[str]:
    """Fetches all In-Game Names from florr_players where is_in_hc is TRUE."""
    if not supabase:
        if guild: await log_error(guild, "GuildSync: Supabase unavailable for fetching DB HC members.")
        return []
    
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("florr_players")
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
    """
    Handles the standard activity logging from screenshots (for batches < 10).
    Extracts online players and marks them as active for today.
    """
    guild = message.guild
    user = message.author
    num_images = len(valid_image_attachments)
    processing_reply: Optional[discord.Message] = None
    
    config = await load_server_config(guild.id)
    
    try:
        processing_reply = await message.reply(
            f"{user.mention} ⏳ Analyzing {num_images} image(s) for activity updates...",
            allowed_mentions=discord.AllowedMentions(users=[user])
        )
    except discord.HTTPException as e_initial_reply:
        await log_error(guild, "Screenshot activity: Failed to send initial processing reply", error=e_initial_reply, message_context=message)
        return

    activity_date, date_error = get_utc_date()
    if date_error or not activity_date:
        err_msg = f"{user.mention} ❌ Error: Could not determine today's date for activity logging."
        if processing_reply: await processing_reply.edit(content=err_msg)
        await log_error(guild, f"Screenshot activity error: Failed to get today's date ({date_error})", message_context=message)
        return

    all_matched_igns_from_all_images: List[str] = []
    
    known_igns_str = "\n".join(ingame_name_cache) if ingame_name_cache else "No known names."
    for image_att in valid_image_attachments:
        try:
            image_data = await image_att.read()
            ai_extracted_text = await get_ai_response_with_image(
                prompt_key="FLORR_IMAGE_NAME_EXTRACTION", 
                image_bytes_list=[image_data],
                prompt_kwargs={'known_igns_list_str': known_igns_str}
            )
            if ai_extracted_text and ai_extracted_text.strip().upper() != "NO_NAMES_FOUND":
                potential_names = {clean_ign(name) for name in ai_extracted_text.split('\n') if name.strip()}
                for ai_name in potential_names:
                    for cached_ign in ingame_name_cache:
                        if cached_ign.lower() == ai_name.lower() and cached_ign not in all_matched_igns_from_all_images:
                            all_matched_igns_from_all_images.append(cached_ign)
                            break
        except Exception as e_single_img_proc:
            await log_error(guild, f"Error processing single activity screenshot", error=e_single_img_proc, message_context=message)

    if not all_matched_igns_from_all_images:
        final_content = f"{user.mention} AI analysis complete: No online players matching the known member list were identified."
        if processing_reply: await processing_reply.edit(content=final_content, embed=None, view=None)
        return

    newly_added_details: List[Dict[str, Any]] = []
    already_active: List[str] = []
    failed_to_add: List[str] = []
    activity_changed = False

    for ign in all_matched_igns_from_all_images:
        exists = await check_activity_exists(guild, ign.lower(), activity_date)
        if exists is True:
            already_active.append(ign)
        elif exists is False:
            success, _ = await upsert_activity_log(guild, ign, activity_date, user.id)
            if success:
                newly_added_details.append({'ign': ign, 'status': 'active_by_view'})
                activity_changed = True
            else:
                failed_to_add.append(ign)
        else:
            failed_to_add.append(ign)

    confirm_view = ScreenshotConfirmView(user.id, activity_date, newly_added_details, already_active, failed_to_add, guild, message.id)
    final_embed = confirm_view.create_embed()
    
    final_message_obj = None
    if processing_reply:
        try:
            final_message_obj = await processing_reply.edit(content=f"{user.mention}", embed=final_embed, view=confirm_view)
        except discord.HTTPException:
            final_message_obj = await message.channel.send(content=f"{user.mention}", embed=final_embed, view=confirm_view)
    else:
        final_message_obj = await message.channel.send(content=f"{user.mention}", embed=final_embed, view=confirm_view)

    if final_message_obj:
        confirm_view.message = final_message_obj
    
    if activity_changed and guild.id == CATERCORD_GUILD_ID:
        await log_info(guild, f"Screenshot by {user.name} logged new activity. Triggering list update for [HC1].")
        
        tracked_guilds = config.get('tracked_guilds', {})
        hc1_config = tracked_guilds.get('[HC1]')
        
        if hc1_config and hc1_config.get('member_list_channel_id'):
            await update_single_tracked_guild_list(guild, hc1_config)
        else:
            await log_info(guild, "Could not trigger list update for [HC1]: Config for tag '[HC1]' or its member_list_channel_id not found.")

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
        max_length=3,
        style=discord.TextStyle.short,
        required=True
    )

    def __init__(self, view_ref: 'ProfilePagesView'):
        super().__init__(timeout=120.0)
        self.view_ref = view_ref

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            num_to_add = int(self.num_attempts_input.value)
            if not (1 <= num_to_add <= 1000):
                await interaction.followup.send("❌ Please enter a number between 1 and 1000.", ephemeral=True)
                return
        except ValueError:
            await interaction.followup.send("❌ Invalid number entered.", ephemeral=True)
            return

        ign = self.view_ref.hc_profile_data.get("ingame_name")
        if not ign:
            await interaction.followup.send("❌ Cannot add attempts: IGN not found for this profile.", ephemeral=True)
            return

        author_id_str = self.view_ref.target_user_display_data.get("_discord_id_for_sa_management")
        author_id = int(author_id_str) if author_id_str else self.view_ref.original_command_interaction.user.id

        success, msg = await add_unknown_super_attempts(interaction.guild, ign, num_to_add, author_id)
        
        feedback_embed = discord.Embed(title="Add Unknown Attempts Result", description=msg, color=discord.Color.green() if success else discord.Color.orange())
        await interaction.followup.send(embed=feedback_embed, ephemeral=True)

        if success:
            await self.view_ref._fetch_super_attempt_stats_data()
            if self.view_ref.current_page_mode == ProfilePagesView.SUPER_ATTEMPT_LOG_PAGE:
                await self.view_ref._fetch_s_attempt_log_page_data(self.view_ref.s_attempt_log_current_page)
            await self.view_ref._update_message(interaction)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await log_error(interaction.guild, "Error in AddUnknownAttemptsModal", error=error, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred with the modal.", ephemeral=True)


class RemoveAttemptModal(discord.ui.Modal, title="Remove Super Attempt Log Entry"):
    entry_number_input = discord.ui.TextInput(
        label="Entry number on this page to remove",
        placeholder="e.g., 3 (for the 3rd item listed)",
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
        entry_data_source = []
        if self.view_ref.current_page_mode == ProfilePagesView.SUPER_ATTEMPT_LOG_PAGE:
            entry_data_source = self.view_ref.current_s_attempt_log_entries
        elif self.view_ref.current_page_mode == ProfilePagesView.SUPER_CRAFT_LOG_PAGE:
            entry_data_source = self.view_ref.current_s_craft_log_entries
        
        try:
            entry_num_on_page = int(self.entry_number_input.value)
            if not (1 <= entry_num_on_page <= len(entry_data_source)):
                await interaction.followup.send(f"❌ Invalid entry number. Please enter a number between 1 and {len(entry_data_source)} for the current page.", ephemeral=True)
                return
        except ValueError:
            await interaction.followup.send("❌ Invalid number entered.", ephemeral=True)
            return

        entry_to_remove_data = entry_data_source[entry_num_on_page - 1]
        attempt_db_id_to_remove = entry_to_remove_data.get('id')
        if not attempt_db_id_to_remove:
            await interaction.followup.send("❌ Error: Could not find database ID for the selected entry.", ephemeral=True)
            return

        # For now, only super attempts can be removed this way. Craft/Defeat removal would need separate logic.
        if self.view_ref.current_page_mode != ProfilePagesView.SUPER_ATTEMPT_LOG_PAGE:
             await interaction.followup.send("❌ Removal is currently only supported for Super Attempt logs.", ephemeral=True)
             return

        success, msg = await remove_super_attempt_by_id(interaction.guild, attempt_db_id_to_remove)
        
        feedback_embed = discord.Embed(title="Remove Attempt Result", description=msg, color=discord.Color.green() if success else discord.Color.orange())
        await interaction.followup.send(embed=feedback_embed, ephemeral=True)

        if success:
            await self.view_ref._fetch_super_attempt_stats_data()
            await self.view_ref._fetch_s_attempt_log_page_data(self.view_ref.s_attempt_log_current_page)
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
    author_ign: str,
    all_time_attempt_count: Optional[int] = None
):
    if not supabase or not guild or not user or not author_ign:
        return

    try:
        settings_resp = await run_supabase_sync(
            lambda: supabase.table("florr_players")
                           .select("manage_nickname_by_bot, custom_nickname_template, florr_guild_tag")
                           .eq("discord_id", str(user.id))
                           .eq("ingame_name", author_ign)
                           .maybe_single()
                           .execute()
        )

        if not (settings_resp and hasattr(settings_resp, 'data') and settings_resp.data):
            return

        settings = settings_resp.data
        manage_by_bot = settings.get("manage_nickname_by_bot", False)
        is_in_a_guild = settings.get("florr_guild_tag") is not None
        custom_template = settings.get("custom_nickname_template")

        if not manage_by_bot:
            # If management is off, revert to plain IGN if they are in a guild and nick is different.
            if is_in_a_guild and user.nick != author_ign:
                bot_member = guild.me
                # Check hierarchy and perms before trying to edit
                if bot_member.top_role > user.top_role and bot_member.guild_permissions.manage_nicknames:
                    try:
                        await user.edit(nick=author_ign[:32], reason="Nickname management disabled by user, reverting to IGN")
                        await log_info(guild, f"Reverted nickname for {user.mention} to '{author_ign[:32]}' as management was disabled (was in a guild).")
                    except Exception as e_revert:
                        await log_error(guild, f"Error reverting nickname for {user.mention} (management off, in a guild)", error=e_revert)
            # If not in a guild, or nick already matches, do nothing.
            return

        # Nickname management is ON
        if all_time_attempt_count is None:
            current_all_time_count = await get_all_time_super_attempt_count(guild, author_ign)
        else:
            current_all_time_count = all_time_attempt_count
            
        new_nickname_unprocessed: str
        log_reason_nick_type: str

        if custom_template:
            new_nickname_unprocessed = custom_template.replace("{satt}", str(current_all_time_count))
            log_reason_nick_type = "custom template"
        else:
            # Default format: only add satt if in a guild
            satt_str = f" ({current_all_time_count} satt)" if current_all_time_count > 0 and is_in_a_guild else ""
            new_nickname_unprocessed = f"{author_ign}{satt_str}"
            log_reason_nick_type = "default format (in guild)" if is_in_a_guild else "default format (not in guild)"
        
        new_nickname = new_nickname_unprocessed[:32]
        
        if user.nick == new_nickname:
            return

        bot_member = guild.me
        if user.id == guild.owner_id:
            await log_info(guild, f"Nickname update skipped for {user.mention}: Cannot manage the server owner's nickname.")
            return
        if bot_member.top_role <= user.top_role:
            await log_info(guild, f"Nickname update skipped for {user.mention}: Bot hierarchy too low.")
            return
        if not bot_member.guild_permissions.manage_nicknames:
            await log_info(guild, f"Nickname update skipped for {user.mention}: Bot lacks Manage Nicknames permission.")
            return

        await user.edit(nick=new_nickname, reason=f"Automatic nickname update (S.Attempts: {current_all_time_count})")
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
        guild = interaction.guild
        if not guild: 
            await interaction.followup.send("Error: Guild context lost.", ephemeral=True)
            return
            
        try:
            insert_payload = {
                "ingame_name": self.author_ign,
                "discord_user_id": str(self.target_user_id),
                "attempt_date": self.attempt_date_obj.isoformat(),
                "petals_lost": self.petals_lost,
                "message_id": str(self.original_user_message.id),
                "channel_id": str(self.original_user_message.channel.id),
                "chosen_petal_name": button.chosen_petal_data['original_full_name'] 
            }
            # Attempt to insert and get the inserted row back
            insert_resp = await run_supabase_sync(
                lambda: supabase.table("super_attempts").insert(insert_payload).execute() # Add returning='representation' if client supports
            )
            
            new_attempt_db_id = None
            # Try to get ID from insert response first
            if insert_resp and hasattr(insert_resp, 'data') and insert_resp.data and len(insert_resp.data) > 0 and 'id' in insert_resp.data[0]:
                new_attempt_db_id = insert_resp.data[0]['id']
                print(f"SuperAttempt Log: Got DB ID {new_attempt_db_id} directly from insert response.")
            else:
                # Fallback: query for the latest record by this user for this original message
                # This is less specific but more robust if insert doesn't return ID or chosen_petal_name has subtle issues
                await log_info(guild, f"SuperAttempt Log: Insert for {self.author_ign} did not return ID. Falling back to query by message_id/user_id.")
                fallback_query_attempts = 0
                while new_attempt_db_id is None and fallback_query_attempts < 3: # Retry fallback query a few times
                    await asyncio.sleep(0.5 + fallback_query_attempts) # Small delay, increasing
                    fetch_id_resp = await run_supabase_sync(
                        lambda: supabase.table("super_attempts")
                                    .select("id")
                                    .eq("message_id", str(self.original_user_message.id))
                                    .eq("discord_user_id", str(self.target_user_id)) # Added discord_user_id for better specificity
                                    .order("recorded_at", desc=True) # Get the most recent one
                                    .limit(1).maybe_single().execute()
                    )
                    if fetch_id_resp and hasattr(fetch_id_resp, 'data') and fetch_id_resp.data and 'id' in fetch_id_resp.data:
                        new_attempt_db_id = fetch_id_resp.data['id']
                        print(f"SuperAttempt Log: Got DB ID {new_attempt_db_id} via fallback query (Attempt {fallback_query_attempts + 1}).")
                        break
                    fallback_query_attempts += 1
                
                if new_attempt_db_id is None:
                    await log_error(guild, f"SuperAttempt Log: Fallback query also failed to retrieve ID for {self.author_ign}, msg_id {self.original_user_message.id}.", ping_owner=True)


            if not new_attempt_db_id:
                # This is where the "Error: Could not confirm database ID..." comes from.
                # If it reaches here, it means both insert return and fallback query failed.
                error_message = "Error: Could not confirm database ID for the logged attempt. Undo might not work. Please report this."
                await interaction.followup.send(error_message, ephemeral=True)
                await log_error(guild, f"Super Attempt Disambiguation: Failed to get DB ID after insert and fallback for {self.author_ign}, chosen {button.chosen_petal_data['display_friendly_name']}", message_context=self.original_user_message, ping_owner=True)
                
                # Send a simplified success message without the Undo button, as we don't have the ID.
                confirm_embed = discord.Embed(
                    description=f"Logged: Lost {self.petals_lost}x {button.chosen_petal_data['display_friendly_name']}.\n*(Note: Undo feature may be unavailable for this entry due to an ID confirmation issue.)*",
                    color=discord.Color.orange() # Orange to indicate a potential issue
                )
                if self.message: 
                    await self.message.edit(content=f"{interaction.user.mention}", embed=confirm_embed, view=None) # No view (no UndoButton)
                await _update_reactions(self.original_user_message, "success") # Mark as success but with caveat
                # Still update nickname if possible
                if isinstance(interaction.user, discord.Member):
                    all_time_count_after_log = await get_all_time_super_attempt_count(guild, self.author_ign)
                    await update_custom_nickname_on_attempt(guild, interaction.user, self.author_ign, all_time_count_after_log)
                return

            # Proceed with creating confirm view if ID was obtained
            all_time_attempts_count = await get_all_time_super_attempt_count(guild, self.author_ign)

            confirm_view_after_choice = SuperAttemptConfirmView(
                target_user_id=self.target_user_id,
                attempt_db_id=new_attempt_db_id, # This is now more reliably fetched
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
            else: # Should not happen if message was sent for disambiguation
                await interaction.edit_original_response(content=f"{interaction.user.mention}", embed=success_embed, view=confirm_view_after_choice)

            await _update_reactions(self.original_user_message, "success")
            await log_info(guild, f"Super attempt (disambiguated choice: {button.chosen_petal_data['display_friendly_name']}) by `{self.author_ign}`: Lost {self.petals_lost}. All-time attempts: {all_time_attempts_count}.")
            
            if isinstance(interaction.user, discord.Member): 
                await update_custom_nickname_on_attempt(guild, interaction.user, self.author_ign, all_time_attempts_count)

        except Exception as e:
            await log_error(guild, f"Error handling disambiguation choice for {self.author_ign}", error=e, message_context=self.original_user_message, ping_owner=True) # Ping owner on critical errors
            try: 
                if not interaction.response.is_done():
                    await interaction.response.send_message("An error occurred while processing your choice. Admins notified.", ephemeral=True)
                else:
                    await interaction.followup.send("An error occurred while processing your choice. Admins notified.", ephemeral=True)
            except discord.HTTPException: pass

            if self.message: await self.message.edit(content=f"{interaction.user.mention} An error occurred. Please try again or ask an admin.", embed=None, view=None)
            await _update_reactions(self.original_user_message, "error")

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
    candidates = []
    if not available_profile_pics_cache and not ADDITIONAL_SUPER_PETAL_NAMES: # Check both
        if guild_for_log: await log_error(guild_for_log, "find_ultra_petal_candidates: Cache and additional names list are empty.")
        return candidates

    primary_match_result = await fuzzy_match_petal_name(petal_query_str)
    
    if primary_match_result.get("status") != "success":
        return candidates 

    target_base_name = primary_match_result.get("base_name_matched")
    if not target_base_name:
        return candidates

    # Check from image cache
    if available_profile_pics_cache:
        for original_full_name_cache, folder_id, _ in available_profile_pics_cache:
            if folder_id == PETALS_FOLDER_NAME and original_full_name_cache.lower().startswith("ultra "):
                base_name_of_this_ultra = _preprocess_petal_name_for_search(original_full_name_cache)
                if base_name_of_this_ultra == target_base_name:
                    display_friendly_version = _get_display_friendly_petal_name(original_full_name_cache)
                    candidates.append({
                        'original_full_name': original_full_name_cache,
                        'display_friendly_name': display_friendly_version,
                        'base_name_for_db': base_name_of_this_ultra 
                    })
    
    # Check from additional names list (treat them as "Ultra" for candidacy)
    for additional_petal_name in ADDITIONAL_SUPER_PETAL_NAMES:
        base_name_of_additional = _preprocess_petal_name_for_search(additional_petal_name)
        if base_name_of_additional == target_base_name:
            # Ensure we don't add duplicates if it was already found via image cache (unlikely but possible if names overlap)
            if not any(c['original_full_name'].lower() == f"ultra {additional_petal_name.lower()}" or c['original_full_name'].lower() == additional_petal_name.lower() for c in candidates):
                candidates.append({
                    'original_full_name': f"Ultra {additional_petal_name.title()}", # Store with "Ultra" prefix for DB consistency if that's the intent
                    'display_friendly_name': f"Ultra {additional_petal_name.title()}", # Display as "Ultra Name"
                    'base_name_for_db': base_name_of_additional
                })
    
    return candidates

async def fuzzy_match_petal_name(query_string: str, cutoff: float = 0.6) -> Dict[str, Any]:
    if not available_profile_pics_cache and not ADDITIONAL_SUPER_PETAL_NAMES:
        return {'status': 'cache_not_ready'}

    unique_base_petal_data_map: Dict[str, Dict[str, Any]] = {}

    if available_profile_pics_cache:
        for display_name_orig, folder_id, _ in available_profile_pics_cache:
            if folder_id == PETALS_FOLDER_NAME:
                base_search_name = _preprocess_petal_name_for_search(display_name_orig)
                if base_search_name and base_search_name not in unique_base_petal_data_map:
                    display_friendly = _get_display_friendly_petal_name(display_name_orig)
                    unique_base_petal_data_map[base_search_name] = {
                        'display_friendly_name': display_friendly,
                    }
    
    # Add additional petal names to the searchable map
    for additional_name in ADDITIONAL_SUPER_PETAL_NAMES:
        base_search_name = _preprocess_petal_name_for_search(additional_name)
        if base_search_name and base_search_name not in unique_base_petal_data_map:
            # For display, treat them as "Ultra Name" if that's how they should appear in disambiguation
            # The _get_display_friendly_petal_name expects a name potentially starting with "Ultra ",
            # so we construct one for it.
            display_friendly = _get_display_friendly_petal_name(f"Ultra {additional_name.title()}")
            unique_base_petal_data_map[base_search_name] = {
                'display_friendly_name': display_friendly,
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

    scored_matches: List[Dict[str, Any]] = []
    for matched_base_name_str in matches_from_difflib:
        score = difflib.SequenceMatcher(None, processed_query_for_match, matched_base_name_str).ratio()
        base_petal_entry_data = unique_base_petal_data_map.get(matched_base_name_str)
        if base_petal_entry_data:
            scored_matches.append({
                'base_name_matched': matched_base_name_str,
                'display_friendly_name': base_petal_entry_data['display_friendly_name'],
                'score': score
            })
    
    if not scored_matches:
         return { 'status': 'not_found', 'original_query': query_string, 'processed_query': processed_query_for_match }

    scored_matches.sort(key=lambda x: x['score'], reverse=True)
    best_match = scored_matches[0]
    
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
                    ambiguous_display_names_set.add(m['display_friendly_name'])
            
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
    }

async def check_ultra_petal_exists(base_petal_name_to_find: str) -> Optional[str]:
    """
    Checks if an 'Ultra' rarity version of a given base petal name exists in the cache.

    Args:
        base_petal_name_to_find: The base name of the petal, e.g., "lotus", "egg".
                                 This should be pre-processed (lowercase, no 'petal' suffix, etc.).

    Returns:
        The original_full_name (e.g., "Ultra Lotus Petal") from the cache if an Ultra version
        of the base_petal_name_to_find is found, otherwise None.
    """ # MODIFIED
    if not available_profile_pics_cache and not ADDITIONAL_SUPER_PETAL_NAMES: # MODIFIED
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

    # MODIFIED: Check additional names list if not found in cache
    for additional_petal_name in ADDITIONAL_SUPER_PETAL_NAMES:
        base_name_of_additional = _preprocess_petal_name_for_search(additional_petal_name)
        if base_name_of_additional == normalized_base_to_find:
            # Return a consistent "Ultra" formatted name
            return f"Ultra {additional_petal_name.title()}"
            
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
    SUPER_ATTEMPT_STATS_PAGE = "sa_stats"
    SUPER_ATTEMPT_LOG_PAGE = "sa_log"
    SUPER_CRAFT_LOG_PAGE = "sc_log"
    SUPER_DEFEAT_LOG_PAGE = "sd_log"
    NOTES_PAGE = "notes"
    SA_LOG_ENTRIES_PER_PAGE = 50

    def __init__(self, interaction: discord.Interaction, target_user_display_data: Dict[str, Any], hc_profile_data: Dict[str, Any],
                 activity_summary_data: Optional[Dict[str, Any]], initial_monthly_active_dates: Set[datetime.date],
                 super_attempt_stats_data: Optional[Dict[str, Any]],
                 initial_craft_logs: List[Dict[str, Any]], total_crafts: int,
                 initial_defeat_logs: List[Dict[str, Any]], total_defeats: int,
                 initial_notes: List[Dict[str, Any]], total_notes: int,
                 today_date_obj: datetime.date, timeout=300.0, start_page: str = "main"):
        super().__init__(timeout=timeout)
        self.original_command_interaction = interaction
        self.target_user_display_data = target_user_display_data
        self.hc_profile_data = hc_profile_data
        self.activity_summary_data = activity_summary_data
        self.super_attempt_stats_data = super_attempt_stats_data
        
        self.monthly_active_dates_for_current_view = initial_monthly_active_dates
        self.current_display_month = today_date_obj.month
        self.current_display_year = today_date_obj.year
        self.today_date_obj = today_date_obj
        
        self.current_page_mode = start_page
        self.message: Optional[discord.Message] = None

        self.s_attempt_log_current_page = 0
        self.s_attempt_log_total_entries = self.super_attempt_stats_data.get('total_attempts', 0) if self.super_attempt_stats_data else 0
        self.s_attempt_log_total_pages = math.ceil(self.s_attempt_log_total_entries / self.SA_LOG_ENTRIES_PER_PAGE) if self.s_attempt_log_total_entries > 0 else 1
        self.current_s_attempt_log_entries = []

        self.s_craft_log_current_page = 0
        self.s_craft_log_total_entries = total_crafts
        self.s_craft_log_total_pages = math.ceil(total_crafts / self.SA_LOG_ENTRIES_PER_PAGE) if total_crafts > 0 else 1
        self.current_s_craft_log_entries = initial_craft_logs
        
        self.s_defeat_log_current_page = 0
        self.s_defeat_log_total_entries = total_defeats
        self.s_defeat_log_total_pages = math.ceil(total_defeats / self.SA_LOG_ENTRIES_PER_PAGE) if total_defeats > 0 else 1
        self.current_s_defeat_log_entries = initial_defeat_logs

        self.notes_current_page = 0
        self.notes_total_entries = total_notes
        self.notes_total_pages = math.ceil(total_notes / self.SA_LOG_ENTRIES_PER_PAGE) if total_notes > 0 else 1
        self.current_notes = initial_notes

        self.is_fetching_log = False
        self._update_ui_elements()

    def _update_ui_elements(self):
        self.clear_items()
        
        if self.current_page_mode != self.MAIN_PAGE:
            back_to_main_btn = discord.ui.Button(label="⬅️ Back to Main Profile", style=discord.ButtonStyle.primary, custom_id=f"profile_nav_{self.MAIN_PAGE}", row=0)
            back_to_main_btn.callback = self.navigation_button_callback
            self.add_item(back_to_main_btn)

        if self.current_page_mode == self.MAIN_PAGE:
            if self.activity_summary_data:
                btn = discord.ui.Button(label="🗓️ View Activity Calendar", style=discord.ButtonStyle.secondary, custom_id=f"profile_nav_{self.MONTHLY_PAGE}", row=0)
                btn.callback = self.navigation_button_callback
                self.add_item(btn)
            if self.super_attempt_stats_data and self.super_attempt_stats_data.get('total_attempts', 0) > 0:
                btn = discord.ui.Button(label="💥 Super Attempt Details", style=discord.ButtonStyle.secondary, custom_id=f"profile_nav_{self.SUPER_ATTEMPT_STATS_PAGE}", row=0)
                btn.callback = self.navigation_button_callback
                self.add_item(btn)
            if self.s_craft_log_total_entries > 0:
                btn = discord.ui.Button(label="🛠️ View Super Crafts", style=discord.ButtonStyle.secondary, custom_id=f"profile_nav_{self.SUPER_CRAFT_LOG_PAGE}", row=1)
                btn.callback = self.navigation_button_callback
                self.add_item(btn)
            if self.s_defeat_log_total_entries > 0:
                btn = discord.ui.Button(label="⚔️ View Super Defeats", style=discord.ButtonStyle.secondary, custom_id=f"profile_nav_{self.SUPER_DEFEAT_LOG_PAGE}", row=1)
                btn.callback = self.navigation_button_callback
                self.add_item(btn)
            if self.notes_total_entries > 0:
                btn = discord.ui.Button(label="📝 View Notes", style=discord.ButtonStyle.secondary, custom_id=f"profile_nav_{self.NOTES_PAGE}", row=2)
                btn.callback = self.navigation_button_callback
                self.add_item(btn)

        elif self.current_page_mode == self.MONTHLY_PAGE:
            self.add_item(ProfileMonthSelect(self.today_date_obj.year, self.today_date_obj.month, self.current_display_year, self.current_display_month))

        elif self.current_page_mode == self.SUPER_ATTEMPT_STATS_PAGE:
            view_log_btn = discord.ui.Button(label="📜 View Full Log", style=discord.ButtonStyle.secondary, custom_id=f"profile_nav_{self.SUPER_ATTEMPT_LOG_PAGE}", row=1)
            view_log_btn.callback = self.navigation_button_callback
            self.add_item(view_log_btn)
        
        elif self.current_page_mode in [self.SUPER_ATTEMPT_LOG_PAGE, self.SUPER_CRAFT_LOG_PAGE, self.SUPER_DEFEAT_LOG_PAGE, self.NOTES_PAGE]:
            self._add_pagination_controls()

    def _add_pagination_controls(self):
        page_mode_prefix = self.current_page_mode
        current_page, total_pages = 0, 1
        if page_mode_prefix == self.SUPER_ATTEMPT_LOG_PAGE:
            current_page, total_pages = self.s_attempt_log_current_page, self.s_attempt_log_total_pages
        elif page_mode_prefix == self.SUPER_CRAFT_LOG_PAGE:
            current_page, total_pages = self.s_craft_log_current_page, self.s_craft_log_total_pages
        elif page_mode_prefix == self.SUPER_DEFEAT_LOG_PAGE:
            current_page, total_pages = self.s_defeat_log_current_page, self.s_defeat_log_total_pages
        elif page_mode_prefix == self.NOTES_PAGE:
            current_page, total_pages = self.notes_current_page, self.notes_total_pages

        prev_btn = discord.ui.Button(label="⬅️ Prev", style=discord.ButtonStyle.blurple, custom_id=f"profile_log_prev_{page_mode_prefix}", row=1, disabled=(current_page == 0 or self.is_fetching_log))
        prev_btn.callback = self.handle_log_pagination
        self.add_item(prev_btn)
        
        next_btn = discord.ui.Button(label="Next ➡️", style=discord.ButtonStyle.blurple, custom_id=f"profile_log_next_{page_mode_prefix}", row=1, disabled=(current_page >= total_pages - 1 or self.is_fetching_log))
        next_btn.callback = self.handle_log_pagination
        self.add_item(next_btn)

        profile_owner_discord_id = self.target_user_display_data.get("_discord_id_for_sa_management")
        is_profile_owner = profile_owner_discord_id and str(self.original_command_interaction.user.id) == str(profile_owner_discord_id)
        
        if self.current_page_mode == self.SUPER_ATTEMPT_LOG_PAGE and is_profile_owner:
            add_btn = discord.ui.Button(label="➕ Add Unknown", style=discord.ButtonStyle.success, custom_id="profile_sa_add_unknown", row=2)
            add_btn.callback = self.handle_add_s_attempt
            self.add_item(add_btn)
            
            remove_btn = discord.ui.Button(label="➖ Remove Entry", style=discord.ButtonStyle.danger, custom_id="profile_sa_remove_entry", row=2, disabled=(not self.current_s_attempt_log_entries or self.is_fetching_log))
            remove_btn.callback = self.handle_remove_s_attempt
            self.add_item(remove_btn)
            
        if self.current_page_mode == self.NOTES_PAGE:
            delete_btn = discord.ui.Button(label="🗑️ Delete a Note", style=discord.ButtonStyle.danger, custom_id="profile_notes_delete", row=2, disabled=(not self.current_notes or self.is_fetching_log))
            delete_btn.callback = self.handle_delete_note
            self.add_item(delete_btn)

    def _create_main_embed(self) -> discord.Embed:
        is_partial_profile = not self.hc_profile_data.get('discord_id')
        
        embed = discord.Embed(
            title=f"🌟 Profile for {self.target_user_display_data['name']}",
            color=NERDY_YELLOW
        )
        if self.target_user_display_data['avatar_url']:
            embed.set_thumbnail(url=self.target_user_display_data['avatar_url'])

        ign = self.hc_profile_data.get('ingame_name', 'N/A')
        description_parts = [f"**Florr IGN:** `{ign}`"]
        
        if is_partial_profile:
            description_parts.append("\n*(This is a partial profile based on event logs only.)*")
        else:
            description_parts.append(f"**Discord:** {self.target_user_display_data['mention_or_status']}")
            guild_status_text = "❔ Unknown"
            if self.hc_profile_data.get('florr_guild_tag'):
                guild_status_text = f"✅ `{self.hc_profile_data['florr_guild_tag']}`"
            else:
                guild_status_text = "❌ Not in a tracked guild"
            description_parts.append(f"**Guild:** {guild_status_text}")
        
        embed.description = "\n".join(description_parts)

        if self.activity_summary_data:
            activity_value = (
                f"**Total Days:** `{self.activity_summary_data['total_days_logged']}`\n"
                f"**Last Seen:** {self.activity_summary_data['last_seen_display']}"
            )
            embed.add_field(name="📈 Activity Snapshot", value=activity_value, inline=False)
        
        has_super_stats = False
        stats_value = ""
        if self.super_attempt_stats_data and self.super_attempt_stats_data.get('total_attempts', 0) > 0:
            stats_value += f"💥 **Attempts:** `{self.super_attempt_stats_data.get('total_attempts', 0)}`\n"
            has_super_stats = True
        if self.s_craft_log_total_entries > 0:
            stats_value += f"🛠️ **Crafts:** `{self.s_craft_log_total_entries}`\n"
            has_super_stats = True
        if self.s_defeat_log_total_entries > 0:
            stats_value += f"⚔️ **Defeats:** `{self.s_defeat_log_total_entries}`\n"
            has_super_stats = True
        if self.notes_total_entries > 0:
            stats_value += f"📝 **Notes:** `{self.notes_total_entries}`"
            has_super_stats = True

        if has_super_stats:
            embed.add_field(name="🏆 Super Event Log & Notes", value=stats_value.strip(), inline=False)
        
        embed.set_footer(text=f"Profile generated at {get_formatted_utc_now()}")
        return embed

    def _create_monthly_embed(self) -> discord.Embed:
        ign = self.hc_profile_data.get("ingame_name", "N/A")
        embed = discord.Embed(title=f"🗓️ Monthly Activity - {discord.utils.escape_markdown(ign)}", color=NERDY_YELLOW)
        monthly_string = generate_monthly_activity_string_v2(self.monthly_active_dates_for_current_view, self.current_display_month, self.current_display_year, self.today_date_obj)
        embed.description = monthly_string
        embed.set_footer(text=f"Calendar for {datetime.date(self.current_display_year, self.current_display_month, 1).strftime('%B %Y')}")
        return embed

    def _create_super_attempt_stats_embed(self) -> discord.Embed:
        ign = self.hc_profile_data.get("ingame_name", "N/A")
        embed = discord.Embed(title=f"💥 Super Attempt Statistics - {discord.utils.escape_markdown(ign)}", color=NERDY_YELLOW)
        if not self.super_attempt_stats_data or self.super_attempt_stats_data.get('total_attempts', 0) == 0:
            embed.description = "No super attempt data recorded for this user."
            return embed
        stats = self.super_attempt_stats_data
        top_petals_str_parts = [f"{i+1}. `{petal_data['petal_name']}`: {petal_data['attempts']} attempts" for i, petal_data in enumerate(stats['top_petals'])] or ["`No specific petals recorded.`"]
        embed.add_field(name="🏆 Top 3 Attempted Petals", value="\n".join(top_petals_str_parts), inline=False)
        overall_stats_value = f"**Total Super Attempts:** `{stats.get('total_attempts', 0)}`\n**Total Petals Lost:** `{stats.get('total_petals_lost', 0.0):.1f}`\n**Average Petals Lost:** `{stats.get('average_petals_lost_per_attempt', 0.0):.2f}`"
        embed.add_field(name="📊 Overall", value=overall_stats_value, inline=False)
        return embed

    def _create_super_attempt_log_embed(self) -> discord.Embed:
        ign = self.hc_profile_data.get("ingame_name", "N/A")
        embed = discord.Embed(title=f"📜 Super Attempt Log - {discord.utils.escape_markdown(ign)}", color=NERDY_YELLOW)
        if self.is_fetching_log: embed.description = "⏳ Fetching log entries..."; return embed
        if not self.current_s_attempt_log_entries: embed.description = "No super attempt log entries found."; return embed

        IDX_W, DATE_W, PETAL_W, LOST_W = 4, 11, 21, 5
        header = f"{'#':<{IDX_W}}{'Date':<{DATE_W}}{'Petal':<{PETAL_W}}{'Lost':<{LOST_W}}"
        separator = "-" * len(header)
        lines = [f"```{header}", separator]

        start_index = self.s_attempt_log_current_page * self.SA_LOG_ENTRIES_PER_PAGE
        for i, entry in enumerate(self.current_s_attempt_log_entries):
            global_index = start_index + i + 1
            date_str = format_date_dmy(entry['attempt_date']) if entry.get('attempt_date') else "N/A"
            petal_name = _get_display_friendly_petal_name(entry.get('chosen_petal_name', 'Unknown'))
            petals_lost = f"{entry.get('petals_lost', 0.0):.1f}"
            petal_display = (petal_name[:PETAL_W-1] + '…') if len(petal_name) > PETAL_W else petal_name
            index_str = f"{global_index}."
            line = f"{index_str:<{IDX_W}}{date_str:<{DATE_W}}{petal_display:<{PETAL_W}}{petals_lost:<{LOST_W}}"
            lines.append(line)

        lines.append("```")
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Page {self.s_attempt_log_current_page + 1}/{self.s_attempt_log_total_pages} ({self.s_attempt_log_total_entries} total)")
        return embed

    def _create_super_craft_log_embed(self) -> discord.Embed:
        ign = self.hc_profile_data.get("ingame_name", "N/A")
        embed = discord.Embed(title=f"🛠️ Super Craft Log - {discord.utils.escape_markdown(ign)}", color=NERDY_YELLOW)
        if self.is_fetching_log: embed.description = "⏳ Fetching log entries..."; return embed
        if not self.current_s_craft_log_entries: embed.description = "No super craft log entries found."; return embed

        IDX_W, DATE_W, PETAL_W = 4, 11, 25
        header = f"{'#':<{IDX_W}}{'Date':<{DATE_W}}{'Super Petal':<{PETAL_W}}"
        separator = "-" * len(header)
        lines = [f"```{header}", separator]

        start_index = self.s_craft_log_current_page * self.SA_LOG_ENTRIES_PER_PAGE
        for i, entry in enumerate(self.current_s_craft_log_entries):
            global_index = start_index + i + 1
            date_str = format_date_dmy(date_parse(entry['craft_date']).date()) if entry.get('craft_date') else "N/A"
            petal_name = entry.get('super_petal_name', 'Unknown')
            petal_display = (petal_name[:PETAL_W-1] + '…') if len(petal_name) > PETAL_W else petal_name
            index_str = f"{global_index}."
            line = f"{index_str:<{IDX_W}}{date_str:<{DATE_W}}{petal_display:<{PETAL_W}}"
            lines.append(line)

        lines.append("```")
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Page {self.s_craft_log_current_page + 1}/{self.s_craft_log_total_pages} ({self.s_craft_log_total_entries} total)")
        return embed

    def _create_super_defeat_log_embed(self) -> discord.Embed:
        ign = self.hc_profile_data.get("ingame_name", "N/A")
        embed = discord.Embed(title=f"⚔️ Super Defeat Log - {discord.utils.escape_markdown(ign)}", color=NERDY_YELLOW)
        if self.is_fetching_log: embed.description = "⏳ Fetching log entries..."; return embed
        if not self.current_s_defeat_log_entries: embed.description = "No super defeat log entries found."; return embed
        
        IDX_W, DATE_W, MOB_W = 4, 11, 25
        header = f"{'#':<{IDX_W}}{'Date':<{DATE_W}}{'Mob Defeated':<{MOB_W}}"
        separator = "-" * len(header)
        lines = [f"```{header}", separator]

        start_index = self.s_defeat_log_current_page * self.SA_LOG_ENTRIES_PER_PAGE
        for i, entry in enumerate(self.current_s_defeat_log_entries):
            global_index = start_index + i + 1
            date_str = format_date_dmy(date_parse(entry['event_timestamp']).date()) if entry.get('event_timestamp') else "N/A"
            mob_name = f"{entry.get('rarity', '')} {entry.get('mob', 'Unknown')}".strip()
            mob_display = (mob_name[:MOB_W-1] + '…') if len(mob_name) > MOB_W else mob_name
            index_str = f"{global_index}."
            line = f"{index_str:<{IDX_W}}{date_str:<{DATE_W}}{mob_display:<{MOB_W}}"
            lines.append(line)

        lines.append("```")
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Page {self.s_defeat_log_current_page + 1}/{self.s_defeat_log_total_pages} ({self.s_defeat_log_total_entries} total)")
        return embed

    def _create_notes_embed(self) -> discord.Embed:
        ign = self.hc_profile_data.get("ingame_name", "N/A")
        embed = discord.Embed(title=f"📝 Notes for {discord.utils.escape_markdown(ign)}", color=NERDY_YELLOW)
        if self.is_fetching_log:
            embed.description = "⏳ Fetching notes..."
            return embed
        if not self.current_notes:
            embed.description = "No notes have been added for this player."
            return embed

        author_ids = {note['author_discord_id'] for note in self.current_notes if note.get('author_discord_id')}
        authors_map = {}
        for author_id_str in author_ids:
            try:
                user_obj = bot.get_user(int(author_id_str))
                if not user_obj:
                    user_obj = asyncio.run_coroutine_threadsafe(bot.fetch_user(int(author_id_str)), bot.loop).result()
                authors_map[author_id_str] = user_obj.name
            except (discord.NotFound, ValueError, AttributeError):
                authors_map[author_id_str] = f"ID:{author_id_str}"
        
        IDX_W, DATE_W, AUTHOR_W, NOTE_W = 4, 11, 15, 45
        header = f"{'#':<{IDX_W}}{'Date':<{DATE_W}}{'Author':<{AUTHOR_W}}{'Note':<{NOTE_W}}"
        separator = "-" * len(header)
        lines = [f"```{header}", separator]

        start_index = self.notes_current_page * self.SA_LOG_ENTRIES_PER_PAGE
        for i, entry in enumerate(self.current_notes):
            global_index = start_index + i + 1
            author_id = entry.get('author_discord_id')
            author_name = authors_map.get(str(author_id), "Unknown")
            author_display = (author_name[:AUTHOR_W-1] + '…') if len(author_name) > AUTHOR_W else author_name
            
            note_content = entry.get('note_content', '').replace('\n', ' ')
            note_display = (note_content[:NOTE_W-1] + '…') if len(note_content) > NOTE_W else note_content
            
            date_obj = date_parse(entry['created_at']) if entry.get('created_at') else None
            date_str = format_date_dmy(date_obj) if date_obj else "N/A"
            
            index_str = f"{global_index}."
            line = f"{index_str:<{IDX_W}}{date_str:<{DATE_W}}{author_display:<{AUTHOR_W}}{note_display:<{NOTE_W}}"
            lines.append(line)
        
        lines.append("```")
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Page {self.notes_current_page + 1}/{self.notes_total_pages} ({self.notes_total_entries} total)")
        return embed

    async def _update_message(self, interaction: discord.Interaction):
        self._update_ui_elements()
        embed_map = {
            self.MAIN_PAGE: self._create_main_embed,
            self.MONTHLY_PAGE: self._create_monthly_embed,
            self.SUPER_ATTEMPT_STATS_PAGE: self._create_super_attempt_stats_embed,
            self.SUPER_ATTEMPT_LOG_PAGE: self._create_super_attempt_log_embed,
            self.SUPER_CRAFT_LOG_PAGE: self._create_super_craft_log_embed,
            self.SUPER_DEFEAT_LOG_PAGE: self._create_super_defeat_log_embed,
            self.NOTES_PAGE: self._create_notes_embed,
        }
        embed_to_send = embed_map.get(self.current_page_mode, self._create_main_embed)()
        
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed_to_send, view=self)
            elif self.message:
                await self.message.edit(embed=embed_to_send, view=self)
        except discord.HTTPException as e:
            await log_error(interaction.guild, "Failed to update profile page message", error=e)

    async def _fetch_super_attempt_stats_data(self):
        ign = self.hc_profile_data.get("ingame_name")
        if ign: self.super_attempt_stats_data = await get_user_super_attempt_stats(self.original_command_interaction.guild, ign)

    async def _fetch_s_attempt_log_page_data(self, page_num: int):
        ign = self.hc_profile_data.get("ingame_name")
        if not ign: self.current_s_attempt_log_entries = []; return
        self.is_fetching_log = True
        entries, _ = await get_super_attempt_log_entries(self.original_command_interaction.guild, ign, page_num, self.SA_LOG_ENTRIES_PER_PAGE)
        self.current_s_attempt_log_entries = entries
        self.s_attempt_log_current_page = page_num
        self.is_fetching_log = False
        
    async def _fetch_s_craft_log_page_data(self, page_num: int):
        ign = self.hc_profile_data.get("ingame_name")
        if not ign: self.current_s_craft_log_entries = []; return
        self.is_fetching_log = True
        entries, _ = await get_user_super_craft_log_entries(self.original_command_interaction.guild, ign, page_num, self.SA_LOG_ENTRIES_PER_PAGE)
        self.current_s_craft_log_entries = entries
        self.s_craft_log_current_page = page_num
        self.is_fetching_log = False

    async def _fetch_s_defeat_log_page_data(self, page_num: int):
        ign = self.hc_profile_data.get("ingame_name")
        if not ign: self.current_s_defeat_log_entries = []; return
        self.is_fetching_log = True
        entries, _ = await get_user_super_defeat_log_entries(self.original_command_interaction.guild, ign, page_num, self.SA_LOG_ENTRIES_PER_PAGE)
        self.current_s_defeat_log_entries = entries
        self.s_defeat_log_current_page = page_num
        self.is_fetching_log = False

    async def _fetch_notes_page_data(self, page_num: int):
        ign = self.hc_profile_data.get("ingame_name")
        if not ign:
            self.current_notes = []
            return
        self.is_fetching_log = True
        entries, total = await get_user_notes(self.original_command_interaction.guild, ign, page_num, self.SA_LOG_ENTRIES_PER_PAGE)
        self.current_notes = entries
        self.notes_current_page = page_num
        self.notes_total_entries = total
        self.notes_total_pages = math.ceil(total / self.SA_LOG_ENTRIES_PER_PAGE) if total > 0 else 1
        self.is_fetching_log = False

    async def navigation_button_callback(self, interaction: discord.Interaction):
        new_mode = interaction.data['custom_id'].split("profile_nav_")[1]
        if self.current_page_mode == new_mode:
            if not interaction.response.is_done(): await interaction.response.defer()
            return

        self.current_page_mode = new_mode
        if new_mode == self.SUPER_ATTEMPT_LOG_PAGE: await self._fetch_s_attempt_log_page_data(0)
        elif new_mode == self.SUPER_CRAFT_LOG_PAGE: await self._fetch_s_craft_log_page_data(0)
        elif new_mode == self.SUPER_DEFEAT_LOG_PAGE: await self._fetch_s_defeat_log_page_data(0)
        elif new_mode == self.NOTES_PAGE: await self._fetch_notes_page_data(0)
        
        await self._update_message(interaction)

    async def handle_month_selection(self, interaction: discord.Interaction, selected_value: str):
        ign = self.hc_profile_data.get("ingame_name")
        if not ign: await interaction.response.send_message("Cannot fetch monthly data: No IGN linked.", ephemeral=True); return
        year, month = map(int, selected_value.split('-'))
        first_day = datetime.date(year, month, 1)
        last_day = (first_day.replace(month=first_day.month % 12 + 1, year=first_day.year + (first_day.month // 12))) - datetime.timedelta(days=1)
        self.monthly_active_dates_for_current_view = await fetch_activity_dates_in_range(interaction.guild, ign.lower(), first_day, last_day)
        self.current_display_month, self.current_display_year = month, year
        await self._update_message(interaction)

    async def handle_log_pagination(self, interaction: discord.Interaction):
        action, page_mode = interaction.data['custom_id'].replace("profile_log_", "").split("_", 1)
        
        current_page, total_pages = 0, 1
        if page_mode == self.SUPER_ATTEMPT_LOG_PAGE: current_page, total_pages = self.s_attempt_log_current_page, self.s_attempt_log_total_pages
        elif page_mode == self.SUPER_CRAFT_LOG_PAGE: current_page, total_pages = self.s_craft_log_current_page, self.s_craft_log_total_pages
        elif page_mode == self.SUPER_DEFEAT_LOG_PAGE: current_page, total_pages = self.s_defeat_log_current_page, self.s_defeat_log_total_pages
        elif page_mode == self.NOTES_PAGE: current_page, total_pages = self.notes_current_page, self.notes_total_pages
        
        new_page = current_page + (1 if action == "next" else -1)
        if not (0 <= new_page < total_pages):
            if not interaction.response.is_done(): await interaction.response.defer()
            return
            
        fetch_map = {
            self.SUPER_ATTEMPT_LOG_PAGE: self._fetch_s_attempt_log_page_data,
            self.SUPER_CRAFT_LOG_PAGE: self._fetch_s_craft_log_page_data,
            self.SUPER_DEFEAT_LOG_PAGE: self._fetch_s_defeat_log_page_data,
            self.NOTES_PAGE: self._fetch_notes_page_data,
        }
        await fetch_map[page_mode](new_page)
        await self._update_message(interaction)

    async def handle_add_s_attempt(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddUnknownAttemptsModal(view_ref=self))

    async def handle_remove_s_attempt(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RemoveAttemptModal(view_ref=self))

    async def handle_delete_note(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DeleteNoteModal(view_ref=self))

    async def on_timeout(self):
        if self.message:
            try:
                self._update_ui_elements()
                for item in self.children: item.disabled = True
                await self.message.edit(view=self) 
            except discord.HTTPException: pass
        self.stop()
        # // --- END UNCHANGED SECTION (ProfilePagesView.on_timeout from previous state) --- //

async def fetch_profile_details_by_ign(guild: Optional[discord.Guild], input_ign: str) -> Optional[Dict[str, Any]]:
    """
    Fetches core profile data for a given In-Game Name from florr_players.
    Performs a case-insensitive search for the IGN.
    Returns a dict {'ingame_name': str (actual case from DB), 
                    'discord_id': str | None, 
                    'florr_guild_tag': str | None, 
                    'discord_name': str | None} 
    or None if not found.
    """
    if not supabase:
        if guild: await log_error(guild, f"Profile: Supabase unavailable fetching data for IGN '{input_ign}'.")
        return None
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("florr_players")
                           .select("ingame_name, discord_id, florr_guild_tag, discord_name")
                           .ilike("ingame_name", input_ign)
                           .limit(1)
                           .maybe_single()
                           .execute()
        )
        
        if resp and hasattr(resp, 'data') and resp.data:
            return {
                "ingame_name": resp.data.get("ingame_name"),
                "discord_id": str(resp.data.get("discord_id")) if resp.data.get("discord_id") else None,
                "florr_guild_tag": resp.data.get("florr_guild_tag"),
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
    Fetches core profile data (IGN, guild tag, etc.) for a given Discord ID from florr_players.
    Returns a dict with ingame_name, florr_guild_tag, discord_name, and discord_id.
    """
    if not supabase:
        if guild: await log_error(guild, f"Profile: Supabase unavailable fetching data for user {discord_id_str}.")
        return None
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("florr_players")
                           .select("ingame_name, florr_guild_tag, discord_name, discord_id") # <-- FIXED
                           .eq("discord_id", discord_id_str)
                           .maybe_single()
                           .execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            return {
                "ingame_name": resp.data.get("ingame_name"),
                "florr_guild_tag": resp.data.get("florr_guild_tag"),
                "discord_name": resp.data.get("discord_name"),
                "discord_id": str(resp.data.get("discord_id")) if resp.data.get("discord_id") else None # <-- ADDED
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
        self.buttons = {}
        self._add_buttons()

    def _add_buttons(self):
        self.clear_items()
        self.buttons['general'] = discord.ui.Button(label="General", emoji="📜", style=discord.ButtonStyle.primary if self.current_page == 'general' else discord.ButtonStyle.secondary, custom_id="help_page_general")
        self.buttons['general'].callback = self.switch_page
        self.add_item(self.buttons['general'])

        if self.is_staff_view_allowed:
            self.buttons['staff'] = discord.ui.Button(label="Staff", emoji="🛡️", style=discord.ButtonStyle.primary if self.current_page == 'staff' else discord.ButtonStyle.secondary, custom_id="help_page_staff")
            self.buttons['staff'].callback = self.switch_page
            self.add_item(self.buttons['staff'])

            self.buttons['owner'] = discord.ui.Button(label="Owner", emoji="👑", style=discord.ButtonStyle.primary if self.current_page == 'owner' else discord.ButtonStyle.secondary, custom_id="help_page_owner")
            self.buttons['owner'].callback = self.switch_page
            self.add_item(self.buttons['owner'])

    async def switch_page(self, interaction: discord.Interaction):
        self.current_page = interaction.data['custom_id'].split('_')[-1]
        self._add_buttons()
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

    def _create_general_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🤓 FlorrNerd Bot - General Commands", color=NERDY_YELLOW)
        if self.bot_user and self.bot_user.display_avatar:
            embed.set_thumbnail(url=self.bot_user.display_avatar.url)
        embed.description = "Here are commands generally available to users.\n\n\u200B"
        
        embed.add_field(name="✨ Player & Guild Info", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('profile')} · View a player's full profile and stats.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('hcmembers')} · Show the interactive guild member list.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('servercodes')} · Browse Florr.io server codes.", value="\u200B", inline=False)
        
        embed.add_field(name="\u200B", value="\u200B", inline=False) # Spacer

        embed.add_field(name="👤 Account Management", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('connect')} · Link your Discord to a Florr IGN.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('disconnect')} · Unlink your Discord from your IGN.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('add_note')} · Add a public note to a player's profile.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('setnickname')} · Manage your auto-updating nickname.", value="\u200B", inline=False)
        
        embed.add_field(name="\u200B", value="\u200B", inline=False) # Spacer

        embed.add_field(name="⚙️ Utility", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('ping')} · Check the bot's latency.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('nerdhelp')} · Shows this help message.", value="\u200B", inline=False)
        
        embed.set_footer(text="Bot by Vibhor | TheNerd")
        return embed

    def _create_staff_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🛡️ FlorrNerd Bot - Staff Commands", color=NERDY_YELLOW)
        if self.bot_user and self.bot_user.display_avatar:
            embed.set_thumbnail(url=self.bot_user.display_avatar.url)
        embed.description = "These commands require server admin permissions or a configured staff role.\n\n\u200B"
        
        embed.add_field(name="🛠️ Server & Guild Configuration", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('setup')} · Interactively configure all bot settings.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('setup_guild')} · Manage the server's tracked Florr guilds.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('refresh')} · Sync all data and roles.", value="\u200B", inline=False)
        
        embed.add_field(name="\u200B", value="\u200B", inline=False) # Spacer

        embed.add_field(name="👤 Member Management", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('verify')} · Manually manage a user's verification.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('setguild')} · Set a user's Florr guild tag in the database.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('wither')} · Temporarily remove a user's roles.", value="\u200B", inline=False)
        
        embed.add_field(name="\u200B", value="\u200B", inline=False) # Spacer

        embed.add_field(name="💬 Messaging", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('florr')} · Send a message with a custom Florr avatar.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('imitate')} · Send a message appearing as another user.", value="\u200B", inline=False)
        
        embed.set_footer(text="Use /setup for most configuration needs.")
        return embed
    
    def _create_owner_embed(self) -> discord.Embed:
        embed = discord.Embed(title="👑 FlorrNerd Bot - Owner Commands", color=NERDY_YELLOW)
        if self.bot_user and self.bot_user.display_avatar:
            embed.set_thumbnail(url=self.bot_user.display_avatar.url)
        embed.description = "These commands can only be run by the bot owner.\n\n\u200B"

        embed.add_field(name="⚙️ Global Management", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('nerd_admin')} · Manage global bot settings.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('cleanup_bot_messages')} · Delete the bot's last N messages.", value="\u200B", inline=False)
        
        embed.add_field(name="\u200B", value="\u200B", inline=False) # Spacer

        embed.add_field(name="💬 Advanced Messaging", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('message')} · Send, edit, or reply to any message.", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('webhook')} · Manage persistent, named webhooks.", value="\u200B", inline=False)

        embed.set_footer(text="These commands affect the bot globally.")
        return embed

    def get_current_embed(self) -> discord.Embed:
        if self.current_page == "staff": return self._create_staff_embed()
        if self.current_page == "owner": return self._create_owner_embed()
        return self._create_general_embed()

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                if isinstance(item, discord.ui.Button): item.disabled = True
            try: await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException): pass
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
    """Loads all In-Game Names from Supabase into cache."""
    global ingame_name_cache
    if not supabase:
        await log_error(guild_for_log, "IGN Cache loading failed: Supabase unavailable.", ping_owner=True)
        ingame_name_cache = []
        return

    print("Loading all IGNs from florr_players into cache...")
    try:
        # Fetch all non-null ingame_names from the database
        resp = await run_supabase_sync(
            lambda: supabase.table("florr_players")
                           .select("ingame_name")
                           .not_.is_("ingame_name", "null")
                           .execute()
        )

        if not resp or not hasattr(resp, 'data') or not resp.data:
            await log_info(guild_for_log, "No IGN data found in the database. IGN cache will be empty.")
            ingame_name_cache = []
            return

        temp_igns = {str(entry["ingame_name"]) for entry in resp.data if entry.get("ingame_name")}
        ingame_name_cache = sorted(list(temp_igns), key=str.lower)

        print(f"Loaded {len(ingame_name_cache)} unique In-Game Names into cache.")
        await log_info(guild_for_log, f"Successfully loaded {len(ingame_name_cache)} IGNs into local cache.")

    except (APIError, ConnectionError, Exception) as e:
        await log_error(guild_for_log, "Failed to load IGN cache from Supabase", error=e, ping_owner=True)
        ingame_name_cache = [] # Clear cache on error # Clear cache on error




    








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
            channel_id_to_find = self.channel_id # Use the stored channel_id
            channel = self.guild.get_channel(channel_id_to_find)
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
                print(f"[Static View Update] Could not find channel {channel_id_to_find} during data update.")
        else:
            print("[Static View Update] Cannot edit message: Missing message ID or guild context.")


    # --- __init__ (MODIFIED) ---
    def __init__(self, original_data: List[Dict[str, Any]], initial_display_data: List[Dict[str, Any]], total_members: int, guild: discord.Guild, channel_id: int, embed_title: str, message: Optional[discord.Message] = None, timeout=None):
        super().__init__(timeout=timeout)
        self.original_data = original_data
        self.current_data = initial_display_data
        self.total_members = total_members
        self.current_page = 0
        self.message: Optional[discord.Message] = message
        self.message_id: Optional[int] = message.id if message else None
        self.guild = guild
        self.is_target_guild = True
        self.bot_owner_id = OWNER_USER_ID
        self.channel_id = channel_id
        self.embed_title = embed_title # Store the custom title

        self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY
        self.sort_mode = SORT_MODE_ACTIVITY
        self.info_mode_active = False
        self.is_fetching_activity = False
        self.last_interaction_time = discord.utils.utcnow()

        self.sort_data()
        self.total_pages = math.ceil(len(self.current_data) / MEMBERS_PER_PAGE) if self.current_data else 1
        self.update_ui_elements()

    async def fetch_and_set_data_for_mode(self, mode: str, start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None):
        """Fetches activity if needed and sets self.current_data. Now ASYNC."""
        print(f"[Static View] Async setting data for mode: {mode}")
        
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

        if mode in [VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
            all_igns = [item['ign'] for item in self.original_data if item.get('ign')]
            if not all_igns:
                print("[Static View] No IGNs found in original data.")
                self.current_data = list(self.original_data)
                return
            try:
                 ranged_activity_data = await fetch_activity_data(self.guild, all_igns, start_date, end_date)
            except Exception as e:
                  print(f"[Static View] Error fetching activity data: {e}")
                  await log_error(self.guild, f"Static View: Error fetching activity data for mode {mode}", error=e)
                  self.current_data = list(self.original_data)
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
            self.current_data = list(self.original_data)
            print("[Static View] Set to All-Time activity view.")
        else:
            self.current_data = list(self.original_data)
            print("[Static View] Set to Discord view.")


    def sort_data(self):
        """Sorts self.current_data based on self.sort_mode."""
        stored_page = self.current_page

        if self.view_mode == VIEW_MODE_DISCORD:
            if self.sort_mode == SORT_MODE_DISCORD_NAME:
                def sort_key_discord(item):
                    member = item.get('member')
                    db_name = item.get('discord_name')
                    if member:
                        key_part = (member.name.lower(), member.discriminator)
                        is_none_equivalent = False
                    elif db_name:
                        key_part = (db_name.lower(),)
                        is_none_equivalent = False
                    else:
                        key_part = ('zzz',)
                        is_none_equivalent = True
                    return (is_none_equivalent, key_part)
                self.current_data.sort(key=sort_key_discord)
            else:
                self.current_data.sort(key=lambda item: item.get('ign', 'zzz').lower())
        elif self.sort_mode == SORT_MODE_ACTIVITY:
            self.current_data.sort(key=lambda item: (item.get('activity_count', 0) * -1, item.get('ign', 'zzz').lower()))
        else:
             self.current_data.sort(key=lambda item: item.get('ign', 'zzz').lower())

        self.total_pages = math.ceil(len(self.current_data) / MEMBERS_PER_PAGE) if self.current_data else 1
        self.current_page = min(stored_page, max(0, self.total_pages - 1))

    def update_ui_elements(self):
        """Clears and explicitly re-adds UI elements based on the current state."""
        self.clear_items()

        if self.info_mode_active:
            back_button = InfoButton(is_info_active=True, row=0)
            back_button.callback = self.toggle_info_mode
            self.add_item(back_button)
        else:
            prev_button = discord.ui.Button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="static_prev", row=0, disabled=self.current_page == 0 or self.is_fetching_activity)
            prev_button.callback = self.previous_button_callback
            self.add_item(prev_button)

            next_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.blurple, custom_id="static_next", row=0, disabled=self.current_page >= self.total_pages - 1 or self.is_fetching_activity)
            next_button.callback = self.next_button_callback
            self.add_item(next_button)

            sort_button_disabled = self.is_fetching_activity
            if self.view_mode == VIEW_MODE_DISCORD:
                sort_label = "Sort by IGN" if self.sort_mode == SORT_MODE_DISCORD_NAME else "Sort by Discord Name"
            else:
                sort_label = "Sort by IGN" if self.sort_mode == SORT_MODE_ACTIVITY else "Sort by Activity"

            sort_button = discord.ui.Button(label=sort_label, style=discord.ButtonStyle.success, custom_id="static_toggle_sort", row=1, disabled=sort_button_disabled)
            sort_button.callback = self.sort_button_callback
            self.add_item(sort_button)

            info_button = InfoButton(is_info_active=False, row=1)
            info_button.callback = self.toggle_info_mode
            self.add_item(info_button)

            profile_button = MyProfileButton(row=2)
            profile_button.callback = self.show_my_profile
            self.add_item(profile_button)

            options = [
               discord.SelectOption(label="View Discord Names + IGN", value=VIEW_MODE_DISCORD, description="Show Discord usernames and IGNs.", emoji="👤"),
               discord.SelectOption(label="View Activity (Today)", value=VIEW_MODE_ACTIVITY_DAILY, description="Show IGNs active today.", emoji="📅"),
               discord.SelectOption(label="View Activity (Last 7 Days)", value=VIEW_MODE_ACTIVITY_WEEKLY, description="Show IGNs active in the last week.", emoji="📅"),
               discord.SelectOption(label="View Activity (Last 30 Days)", value=VIEW_MODE_ACTIVITY_MONTHLY, description="Show IGNs active in the last 30 days.", emoji="📅"),
               discord.SelectOption(label="View Activity (All-Time)", value=VIEW_MODE_ACTIVITY_ALL, description="Show IGNs and total activity count.", emoji="📊"),
            ]
            for option in options: option.default = option.value == self.view_mode

            view_select = discord.ui.Select(
                placeholder="Select View Mode...", min_values=1, max_values=1, options=options,
                custom_id="static_view_select", row=3, disabled=self.is_fetching_activity
            )
            view_select.callback = self.view_select_callback
            self.add_item(view_select)

    # --- create_page_embed (MODIFIED) ---
    def create_page_embed(self) -> discord.Embed:
        """Creates embed based on current view_mode, sort_mode, and context."""
        if hasattr(self, 'info_mode_active') and self.info_mode_active:
             info_description = (
                 f"This is an interactive list of members in the **{self.embed_title}**.\n\n"
                 "**Features:**\n"
                 f"• **Pagination:** Use `Previous`/`Next` buttons.\n"
                 f"• **View Modes:** Use the dropdown to see different activity periods (Today, 7/30 days, All-Time) or Discord names.\n"
                 f"• **Sorting:** Toggle between sorting by IGN (A-Z) or Activity (most active first) using the `Sort by...` button (only in Activity views).\n"
                 f"• **Actions:** Use `Activate Myself Today` or check the WIP `My Profile`.\n\n"
                 f"**Activity Tracking:**\n"
                 f"• Activity means a member was marked present on a given day using bot commands.\n"
                 f"• The `Activity` column shows: `Count (Last Seen DD/MM/YY)` within the selected view period.\n\n"
                 f"*This message automatically resets to the default view ({VIEW_MODE_ACTIVITY_MONTHLY.replace('_view','')}) after {STATIC_LIST_RESET_TIMEOUT_MINUTES} minutes of inactivity.*\n"
             )
             embed = discord.Embed(
                  title=f"ℹ️ About the {self.embed_title} List",
                  description=info_description,
                  color=NERDY_YELLOW
             )
             embed.set_footer(text=f"Info Mode | Updated: {get_formatted_utc_now()}")
             return embed

        start = self.current_page * MEMBERS_PER_PAGE
        page_data = self.current_data[start : start + MEMBERS_PER_PAGE]
        idx = start + 1
        desc_lines = []

        if not page_data:
            desc_lines = ["No members found matching criteria."]
        elif self.view_mode == VIEW_MODE_DISCORD:
            IDX_WIDTH = 3
            IGN_DISPLAY_WIDTH = 18
            for item_dict in page_data:
                ign = item_dict.get('ign', 'Unknown')
                index_str = f"{str(idx)+'.':<{IDX_WIDTH}} "
                user_id_str: Optional[str] = None
                member = item_dict.get('member')
                if member: user_id_str = str(member.id)
                else: user_id_str = item_dict.get("discord_id")
                mention_display = f"<@!{user_id_str}>" if user_id_str else "`[No Discord]`"
                ign_display = ign if len(ign) <= IGN_DISPLAY_WIDTH else ign[:IGN_DISPLAY_WIDTH-1] + "…"
                line = f"{index_str}`{ign_display:<{IGN_DISPLAY_WIDTH}}` {mention_display}"
                desc_lines.append(line)
                idx += 1
        elif self.view_mode in [VIEW_MODE_ACTIVITY_ALL, VIEW_MODE_ACTIVITY_DAILY, VIEW_MODE_ACTIVITY_WEEKLY, VIEW_MODE_ACTIVITY_MONTHLY]:
            IDX_WIDTH = 3; SPACE_WIDTH = 1; IDX_PLUS_SPACE_WIDTH = IDX_WIDTH + SPACE_WIDTH; CONTENT_WIDTH = 34;
            ACT_WIDTH = 18; IGN_WIDTH = 16; TOTAL_WIDTH = IDX_PLUS_SPACE_WIDTH + CONTENT_WIDTH
            header = f"{'#':<{IDX_WIDTH}} {'IGN':<{IGN_WIDTH}}{'Activity':<{ACT_WIDTH}}"; separator = "-" * TOTAL_WIDTH
            desc_lines.append("```"); desc_lines.append(header); desc_lines.append(separator)
            for item_dict in page_data:
                ign = item_dict.get('ign', 'Unknown')
                activity_count = item_dict.get('activity_count', 0)
                last_seen_date = item_dict.get('last_seen')
                activity_display = f"{activity_count} ({format_date_dmy(last_seen_date)})"
                index_str = f"{str(idx)+'.':<{IDX_WIDTH}} "
                ign_display = ign if len(ign) <= IGN_WIDTH else ign[:IGN_WIDTH-1] + "…"
                if len(activity_display) > ACT_WIDTH: activity_display = activity_display[:ACT_WIDTH-1] + "…"
                line = f"{index_str}{ign_display:<{IGN_WIDTH}}{activity_display:<{ACT_WIDTH}}"; desc_lines.append(line)
                idx += 1
            desc_lines.append("```")
        else:
            desc_lines = ["Error: Invalid View Mode"]

        title = self.embed_title # Use the stored title
        embed = discord.Embed(title=title, description="\n".join(desc_lines), color=NERDY_YELLOW)

        sort_text = "IGN" if self.sort_mode == SORT_MODE_IGN else "Activity"
        view_text_map = {
            VIEW_MODE_DISCORD: "IGN+Discord", VIEW_MODE_ACTIVITY_ALL: "Activity (All)",
            VIEW_MODE_ACTIVITY_DAILY: "Activity (Today)", VIEW_MODE_ACTIVITY_WEEKLY: "Activity (7d)",
            VIEW_MODE_ACTIVITY_MONTHLY: "Activity (30d)",
        }
        view_text = view_text_map.get(self.view_mode, "Unknown View")
        footer_text = f"Page {self.current_page + 1}/{self.total_pages} | Total: {self.total_members} | View: {view_text} | Sort: {sort_text}"
        if hasattr(self, 'is_fetching_activity') and self.is_fetching_activity: footer_text += " | Fetching data..."
        footer_text += f" | Updated: {get_formatted_utc_now()}"
        embed.set_footer(text=footer_text)
        return embed

    async def edit_message_object(self, message: Optional[discord.Message] = None):
        """Edits the view's underlying message object."""
        message_to_edit = message or self.message
        if not message_to_edit:
            print(f"[Static View {self.message_id}] Error: edit_message_object called without a message.")
            return
        self.update_ui_elements()
        embed = self.create_page_embed()
        try:
            await message_to_edit.edit(embed=embed, view=self)
        except discord.NotFound:
            print(f"[Static View] Message edit fail: Message {message_to_edit.id} not found.")
            self.stop()
            if self.guild and self.message_id and self.channel_id in active_static_list_views and active_static_list_views[self.channel_id]['message_id'] == self.message_id:
                 del active_static_list_views[self.channel_id]
                 print(f"[Static View] Removed view tracking for message {self.message_id} as it was not found.")
        except discord.HTTPException as e:
            if e.status != 404: await log_error(self.guild, f"Static list Message edit fail (HTTP {e.status})", error=e)
        except Exception as e:
            await log_error(self.guild, f"Static list Message edit fail (General) for {message_to_edit.id}", error=e)

    async def respond_to_interaction(self, interaction: discord.Interaction):
        """Handles the initial edit response for an interaction."""
        if interaction.response.is_done():
            print(f"[Static View] Warning: respond_to_interaction called for already responded interaction {interaction.id}")
            try: await self.edit_message_object(await interaction.original_response())
            except Exception as e_edit_orig: print(f"[Static View] Failed to edit original response after double-response warning: {e_edit_orig}")
            return
        self.update_ui_elements(); embed = self.create_page_embed()
        try:
            await interaction.response.edit_message(embed=embed, view=self)
            if not self.message:
                 try: self.message = await interaction.original_response(); self.message_id = self.message.id
                 except (discord.NotFound, discord.HTTPException): print(f"[Static View] Failed to fetch original response for interaction {interaction.id} after edit.")
        except discord.NotFound: self.stop()
        except discord.HTTPException as e:
            if e.code != 10062: await log_error(self.guild, "Interaction edit fail (HTTP)", error=e, interaction=interaction)
        except Exception as e:
             await log_error(self.guild, "Interaction edit fail (General)", error=e, interaction=interaction)

    async def previous_button_callback(self, interaction: discord.Interaction):
        """Callback for the Previous button."""
        if self.current_page > 0 and not self.is_fetching_activity:
            self.current_page -= 1
            self.last_interaction_time = discord.utils.utcnow()
            await self.respond_to_interaction(interaction)
        else: await interaction.response.defer()

    async def next_button_callback(self, interaction: discord.Interaction):
        """Callback for the Next button."""
        if self.current_page < self.total_pages - 1 and not self.is_fetching_activity:
            self.current_page += 1
            self.last_interaction_time = discord.utils.utcnow()
            await self.respond_to_interaction(interaction)
        else: await interaction.response.defer()

    async def sort_button_callback(self, interaction: discord.Interaction):
        """Callback for the Sort button."""
        if self.is_fetching_activity: await interaction.response.defer(); return
        self.last_interaction_time = discord.utils.utcnow()
        if self.view_mode == VIEW_MODE_DISCORD: self.sort_mode = SORT_MODE_IGN if self.sort_mode == SORT_MODE_DISCORD_NAME else SORT_MODE_DISCORD_NAME
        else: self.sort_mode = SORT_MODE_ACTIVITY if self.sort_mode == SORT_MODE_IGN else SORT_MODE_IGN
        self.sort_data()
        await self.respond_to_interaction(interaction)

    async def view_select_callback(self, interaction: discord.Interaction):
        """Callback for the View Mode Select dropdown."""
        try: new_mode = interaction.data['values'][0]
        except (KeyError, IndexError): await interaction.response.defer(); return
        if self.view_mode == new_mode or self.is_fetching_activity: await interaction.response.defer(); return
        self.last_interaction_time = discord.utils.utcnow()
        self.is_fetching_activity = True; self.view_mode = new_mode
        await self.respond_to_interaction(interaction)
        if not self.message:
             try: self.message = await interaction.original_response(); self.message_id = self.message.id
             except (discord.NotFound, discord.HTTPException) as e:
                  print(f"[Static View] Error fetching original response in view_select: {e}. Cannot perform final update.")
                  self.is_fetching_activity = False
                  try: await interaction.followup.send("❌ Error preparing view update.", ephemeral=True)
                  except Exception: pass
                  return
        try:
            await self.fetch_and_set_data_for_mode(new_mode)
            self.sort_mode = SORT_MODE_IGN if new_mode == VIEW_MODE_DISCORD else SORT_MODE_ACTIVITY
            self.sort_data()
        except Exception as e:
            await log_error(self.guild, f"Error changing static list view mode to {new_mode}", error=e, interaction=interaction)
            self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY; await self.fetch_and_set_data_for_mode(self.view_mode)
            self.sort_mode = SORT_MODE_ACTIVITY; self.sort_data()
            try: await interaction.followup.send("❌ Error fetching data for view.", ephemeral=True)
            except Exception: pass
        finally:
            self.is_fetching_activity = False
            await self.edit_message_object()

    async def toggle_info_mode(self, interaction: discord.Interaction):
        """Callback for the InfoButton."""
        self.last_interaction_time = discord.utils.utcnow()
        self.info_mode_active = not self.info_mode_active
        await self.respond_to_interaction(interaction)

    async def show_my_profile(self, interaction: discord.Interaction):
        """Callback for the MyProfileButton. Shows the user's profile ephemerally."""
        guild = interaction.guild
        if not guild: await interaction.response.send_message("Error: Guild context lost for profile.", ephemeral=True); return
        await interaction.response.defer(thinking=True, ephemeral=True)
        if not await check_supabase_available(interaction):
            try: await interaction.edit_original_response(content="❌ Database connection unavailable. Cannot fetch profile data.", view=None)
            except (discord.NotFound, discord.HTTPException): pass
            return
        target_user_for_display = interaction.user; target_discord_id_str = str(interaction.user.id)
        hc_profile_db_data = await fetch_hc_member_profile_data(guild, target_discord_id_str)
        target_ign_from_db: Optional[str] = hc_profile_db_data.get("ingame_name") if hc_profile_db_data else None
        if not target_ign_from_db:
            await interaction.followup.send(f"❌ {interaction.user.mention}, I couldn't find a linked In-Game Name (IGN) for you. Use {get_cmd_mention('guild')} or {get_cmd_mention('verify')}.", ephemeral=True)
            return
        display_name_for_view: str = target_user_for_display.display_name
        avatar_url_for_view: Optional[str] = target_user_for_display.display_avatar.url if target_user_for_display.display_avatar else target_user_for_display.default_avatar.url
        mention_or_status_for_view: str = target_user_for_display.mention
        actual_member_object_ref: Optional[discord.Member] = target_user_for_display if isinstance(target_user_for_display, discord.Member) else None
        target_user_display_data_for_view = {"name": display_name_for_view, "avatar_url": avatar_url_for_view, "mention_or_status": mention_or_status_for_view, "_member_object_ref": actual_member_object_ref, "_discord_id_for_sa_management": target_discord_id_str}
        activity_summary_for_view: Optional[Dict[str, Any]] = None; initial_monthly_dates_for_view: Set[datetime.date] = set(); super_attempt_stats_data_for_view: Optional[Dict[str, Any]] = None
        today_utc_obj, _ = get_utc_date()
        if target_ign_from_db and today_utc_obj:
            ign_lower = target_ign_from_db.lower()
            is_active_today = await check_activity_exists(guild, ign_lower, today_utc_obj)
            active_today_disp = "✅ `Yes`" if is_active_today is True else ("❌ `No`" if is_active_today is False else "❔ `N/A (DB Error)`")
            all_time_summary = await fetch_activity_data(guild, [ign_lower]); ign_all_time_data = all_time_summary.get(ign_lower, {'count': 0, 'last_seen': None})
            activity_summary_for_view = {"active_today_display": active_today_disp, "total_days_logged": ign_all_time_data['count'], "last_seen_display": f"`{format_date_dmy(ign_all_time_data['last_seen'])}`" if ign_all_time_data['last_seen'] else "`Never Logged`"}
            first_day_current_month = today_utc_obj.replace(day=1)
            first_day_next_month = first_day_current_month.replace(year=today_utc_obj.year + 1, month=1) if today_utc_obj.month == 12 else first_day_current_month.replace(month=today_utc_obj.month + 1)
            last_day_current_month = first_day_next_month - datetime.timedelta(days=1)
            initial_monthly_dates_for_view = await fetch_activity_dates_in_range(guild, ign_lower, first_day_current_month, last_day_current_month)
            super_attempt_stats_data_for_view = await get_user_super_attempt_stats(guild, target_ign_from_db)
        if not today_utc_obj: await log_error(guild, "Static List Profile: Failed to get today's date object.", interaction=interaction)
        profile_view_instance = ProfilePagesView(interaction=interaction, target_user_display_data=target_user_display_data_for_view, hc_profile_data=hc_profile_db_data, activity_summary_data=activity_summary_for_view, initial_monthly_active_dates=initial_monthly_dates_for_view, super_attempt_stats_data=super_attempt_stats_data_for_view, today_date_obj=today_utc_obj if today_utc_obj else datetime.date.today())
        initial_profile_embed = profile_view_instance._create_main_embed()
        try:
            profile_message = await interaction.followup.send(embed=initial_profile_embed, view=profile_view_instance, ephemeral=True)
            profile_view_instance.message = profile_message
        except discord.HTTPException as e_send_profile:
            await log_error(guild, "Failed to send ephemeral profile from static list button", error=e_send_profile, interaction=interaction)
            try: await interaction.edit_original_response(content="❌ Error displaying your profile. Please try again later.", view=None)
            except (discord.NotFound, discord.HTTPException): pass

    async def on_timeout(self):
        print(f"[Static View] Default on_timeout triggered for view on message {self.message_id}. Disabling items.")
        self.update_ui_elements()
        self.stop()
        await self.edit_message_object()

    async def reset_view(self):
        """Resets the view state to default (called by background task)."""
        print(f"[Static View] Resetting view state for message {self.message_id} due to inactivity.")
        self.current_page = 0; self.view_mode = VIEW_MODE_ACTIVITY_MONTHLY; self.sort_mode = SORT_MODE_ACTIVITY;
        self.info_mode_active = False; self.is_fetching_activity = True
        if not self.guild: self.is_fetching_activity = False; return
        channel = self.guild.get_channel(self.channel_id)
        if not isinstance(channel, discord.TextChannel): self.is_fetching_activity = False; return
        message_to_edit: Optional[discord.Message] = None
        try:
            if self.message_id: message_to_edit = await channel.fetch_message(self.message_id); self.message = message_to_edit
            await self.fetch_and_set_data_for_mode(self.view_mode)
            self.sort_data()
        except discord.NotFound:
             if self.channel_id in active_static_list_views: del active_static_list_views[self.channel_id]
             self.stop(); return
        except Exception as e:
             await log_error(self.guild, "[Static View] Reset Error during data/message fetch", error=e)
             self.is_fetching_activity = False; return
        finally: self.is_fetching_activity = False
        if message_to_edit:
            try:
                await self.edit_message_object(message=message_to_edit)
                self.last_interaction_time = discord.utils.utcnow()
            except Exception as e_edit: print(f"[Static View] Reset Error: {e_edit}")

async def update_single_tracked_guild_list(guild: discord.Guild, tracked_guild_config: Dict[str, Any]):
    """Creates or updates the interactive list for a single tracked Florr guild."""
    list_channel_id = tracked_guild_config.get('member_list_channel_id')
    role_id = tracked_guild_config.get('discord_role_id')
    tag = tracked_guild_config.get('florr_guild_tag', '[GUILD]')
    embed_title = f"**{tag} Guild Members**"

    if not all([list_channel_id, role_id]):
        await log_error(guild, f"Skipping static list update for guild '{tag}': Missing channel or role ID in config.")
        return

    chan = guild.get_channel(list_channel_id)
    if not isinstance(chan, discord.TextChannel):
        await log_error(guild, f"Static list update for '{tag}' failed: Channel {list_channel_id} invalid.")
        return
    if not bot or not bot.user:
        await log_error(guild, "Static list update failed: Bot not ready."); return
    if not chan.permissions_for(guild.me).send_messages:
        await log_error(guild, f"Static list update for '{tag}' failed: Bot missing Send/Embed/History/ManageMessages perms in {chan.mention}.")
        return

    await log_info(guild, f"Updating interactive static list for '{tag}' in {chan.mention}...")

    try:
        member_data, total_count = await fetch_tracked_guild_member_data(guild, tag)
    except Exception as e:
        await log_error(guild, f"Static list update for '{tag}' failed: Error fetching member data.", error=e)
        return

    try:
        await load_ign_cache(guild)
    except Exception as e:
        await log_error(guild, f"Static list update for '{tag}' proceeding, but IGN cache refresh failed.", error=e)

    initial_display_data = list(member_data)
    try:
        today_utc = datetime.datetime.now(pytz.utc).date()
        start_date = today_utc - datetime.timedelta(days=29)
        all_igns = [item['ign'] for item in member_data if item.get('ign')]
        if all_igns:
            activity_data = await fetch_activity_data(guild, all_igns, start_date, today_utc)
            temp_data = []
            for item in member_data:
                ign_lower = item.get('ign', '').lower()
                activity_info = activity_data.get(ign_lower, {'count': 0, 'last_seen': None})
                updated_item = item.copy()
                updated_item.update({'activity_count': activity_info['count'], 'last_seen': activity_info['last_seen']})
                temp_data.append(updated_item)
            initial_display_data = temp_data
    except Exception as e:
        await log_error(guild, f"[Static Update for {tag}] Failed to fetch initial monthly activity", error=e)

    active_view_data = active_static_list_views.get(list_channel_id)
    tracked_message_obj: Optional[discord.Message] = None
    tracked_view_instance: Optional[StaticHCPagesView] = None

    if active_view_data:
        msg_id = active_view_data.get('message_id')
        view_instance = active_view_data.get('view')
        if msg_id and isinstance(view_instance, StaticHCPagesView) and not view_instance.is_finished():
            try:
                fetched_msg = await chan.fetch_message(msg_id)
                if fetched_msg.components:
                    tracked_message_obj = fetched_msg; tracked_view_instance = view_instance
                    if not tracked_view_instance.message: tracked_view_instance.message = fetched_msg
            except (discord.NotFound, Exception): pass
        if not tracked_message_obj:
            if list_channel_id in active_static_list_views: del active_static_list_views[list_channel_id]

    message_from_history: Optional[discord.Message] = None
    if not tracked_message_obj:
        async for msg in chan.history(limit=20):
            if msg.author.id == bot.user.id and msg.embeds and msg.embeds[0].title == embed_title and msg.components:
                message_from_history = msg; break

    final_updated_message: Optional[discord.Message] = None
    try:
        if tracked_message_obj and tracked_view_instance:
            await tracked_view_instance.update_data_and_refresh(member_data, initial_display_data, total_count)
            final_updated_message = tracked_message_obj
        elif message_from_history:
            new_view = StaticHCPagesView(member_data, initial_display_data, total_count, guild, list_channel_id, embed_title, message=message_from_history)
            initial_embed = new_view.create_page_embed()
            await message_from_history.edit(embed=initial_embed, view=new_view)
            active_static_list_views[list_channel_id] = {'view': new_view, 'message_id': message_from_history.id}
            final_updated_message = message_from_history
        else:
            new_view = StaticHCPagesView(member_data, initial_display_data, total_count, guild, list_channel_id, embed_title)
            initial_embed = new_view.create_page_embed()
            sent_message = await chan.send(embed=initial_embed, view=new_view)
            new_view.message = sent_message; new_view.message_id = sent_message.id
            active_static_list_views[list_channel_id] = {'view': new_view, 'message_id': sent_message.id}
            final_updated_message = sent_message

        if final_updated_message:
            cleaned_count = 0
            async for old_msg in chan.history(limit=30):
                if old_msg.author.id == bot.user.id and old_msg.id != final_updated_message.id and old_msg.embeds and old_msg.embeds[0].title == embed_title:
                    try: await old_msg.delete(); cleaned_count += 1
                    except Exception: break
            if cleaned_count > 0: await log_info(guild, f"Static list cleanup for '{tag}': Deleted {cleaned_count} old message(s).")
    except Exception as e:
        await log_error(guild, f"Static list update for '{tag}' failed: Unexpected error during send/edit/update.", error=e)

    if not check_static_view_timeout.is_running(): check_static_view_timeout.start()

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

    # 1. Fetch members from florr_players table where is_in_hc is TRUE
    active_florr_players_data = []
    try:
        print("Fetch All Supabase Data: Fetching from florr_players where is_in_hc = TRUE...")
        resp_members = await run_supabase_sync(
            lambda: supabase.table("florr_players")
                           .select("discord_id, discord_name, ingame_name, is_in_hc") # Added is_in_hc
                           .eq("is_in_hc", True)  # <-- ADDED THIS FILTER
                           .execute()
        )
        if resp_members and hasattr(resp_members, 'data') and resp_members.data:
            active_florr_players_data = resp_members.data
            print(f"Fetch All Supabase Data: Found {len(active_florr_players_data)} entries in florr_players with is_in_hc = TRUE.")
        else:
            print("Fetch All Supabase Data: No data returned from florr_players (is_in_hc=TRUE).")
            return [], 0

    except (ConnectionError, APIError, Exception) as e:
        await log_error(guild_for_log, "Failed to fetch data from Supabase florr_players (is_in_hc=TRUE)", error=e, ping_owner=True)
        return [], 0

    # 2. Fetch all activity data (for the IGNs found)
    activity_summary: Dict[str, Dict[str, Any]] = {} # ign_lower -> {'count': int, 'last_seen': date}
    all_igns_in_db = [entry['ingame_name'] for entry in active_florr_players_data if entry.get('ingame_name')]

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
    for member_entry in active_florr_players_data:
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
    """Autocompletes In-Game Names from the local cache or florr_players table."""
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
        query = supabase.table("florr_players").select("ingame_name", count='exact').ilike("ingame_name", f"%{current}%").not_.is_("ingame_name", "null").limit(limit)
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
    """Fetches the stored IGN for a given Discord user ID from florr_players."""
    if not supabase: return None
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("florr_players")
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
    """Runs sync Supabase func in executor, now with more robust error handling."""
    if not supabase:
        print("Supabase Error: Client is not available.")
        return None

    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func)
    except APIError as e:
        # Gracefully handle "204 No Content" which can be raised on .maybe_single() with no result
        if e.code == "204":
            print(f"Supabase Info: Received 204 No Content, treating as None result.")
            return None # Treat as a valid "not found" response
        
        # For other API errors, re-raise as they might be important (e.g., policy violation)
        print(f"Supabase API Error: {e}")
        raise
    except Exception as e:
        # This catches other errors like connection issues, timeouts, etc.
        print(f"Supabase Executor/Connection Error: {e}\n{traceback.format_exc()}")
        return None

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
    """
    Logs an info message. Prints to console ONLY. Discord logging is disabled.
    """
    log_prefix = f"[{guild.name if guild else 'No Guild'}] INFO:"
    
    # Always print to console
    print(f"{log_prefix} {message}")
    
    # The Discord channel logging part has been completely removed.
    
# --- REVISED log_error ---
async def log_error(
    guild: Optional[discord.Guild], 
    message: str, 
    error: Optional[Exception] = None, 
    interaction: Optional[discord.Interaction] = None, 
    embed: Optional[discord.Embed] = None, 
    ping_owner: bool = False,
    message_context: Optional[discord.Message] = None
):
    log_prefix = f"[{guild.name if guild else 'No Guild'}] ERROR:"
    
    if not embed:
        title_prefix = f"🚨 Bot {'Critical ' if ping_owner else ''}Error"
        embed = discord.Embed(title=title_prefix, description=message, color=discord.Color.red())
        embed.timestamp = discord.utils.utcnow()
        if guild: embed.set_footer(text=f"Server: {guild.name} ({guild.id})")
        
        context_info_parts = []
        if interaction:
            cmd_name = interaction.command.name if interaction.command else 'N/A'
            cmd_link = f"`/{cmd_name}`" if cmd_name != 'N/A' else 'N/A'
            chan_mention = interaction.channel.mention if isinstance(interaction.channel, discord.TextChannel) else f"Ch:{interaction.channel_id}" if interaction.channel_id else "N/A"
            user_mention = f"{interaction.user.mention} (`{interaction.user.id}`)" if interaction.user else "N/A"
            context_info_parts.append(f"**Interaction:** Cmd: {cmd_link} in {chan_mention}\nUser: {user_mention}")
        
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
    
    # --- MODIFIED: Webhook-based Extraordinary Logging ---
    log_guild = bot.get_guild(EXTRAORDINARY_LOGS_GUILD_ID)
    if log_guild:
        log_channel = log_guild.get_channel(EXTRAORDINARY_LOGS_CHANNEL_ID)
        if isinstance(log_channel, discord.TextChannel):
            webhook = await get_or_create_webhook(log_channel, "extraordinary_logs", "Extraordinary Logger", bot.user.display_avatar.url if bot.user else None)
            if webhook:
                content_to_send = f"<@{OWNER_USER_ID}>" if ping_owner else None
                try:
                    await webhook.send(content=content_to_send, embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
                except Exception as e_webhook:
                    print(f"CRITICAL: Failed to send log via webhook. Error: {e_webhook}")
            else:
                print("CRITICAL: Could not get or create webhook for extraordinary logs.")
        else:
            print(f"CRITICAL: Extraordinary log channel {EXTRAORDINARY_LOGS_CHANNEL_ID} not found in guild {EXTRAORDINARY_LOGS_GUILD_ID}.")
    else:
        print(f"CRITICAL: Extraordinary log guild {EXTRAORDINARY_LOGS_GUILD_ID} not found.")

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
    DEPRECATED WRAPPER. Fetches members for the primary [HC1] guild.
    New features should use fetch_tracked_guild_member_data.
    """
    if guild.id == CATERCORD_GUILD_ID:
        return await fetch_tracked_guild_member_data(guild, "[HC1]")
    
    await log_info(guild, "fetch_hc_member_data (deprecated) called on a non-primary guild. Returning empty.")
    return [], 0

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
          
     # --- THIS IS THE NEW PART ---
     # Close the persistent aiohttp session.
     if hasattr(bot, 'http_session') and not bot.http_session.closed:
         await bot.http_session.close()
         print("Closed persistent aiohttp ClientSession.")
     # --- END NEW PART ---

# --- REVISED update_static_list_message Function ---

async def update_static_list_message(guild: discord.Guild):
    """
    DEPRECATED. Static lists are now updated via /refresh, which calls update_single_tracked_guild_list.
    This function is kept for backward compatibility but does nothing.
    """
    # This function is now a no-op to prevent outdated logic from running.
    # All list updates should be triggered via the more generic refresh_all_guild_lists.
    pass

# --- Discord Events ---
@bot.event
async def on_ready():
    print("--- on_ready event started ---")
    global BOT_USER_ID, command_ids

    if bot.user:
        BOT_USER_ID = bot.user.id
        print(f"Logged in as {bot.user} (ID: {BOT_USER_ID})")
        print(f"Discord.py v{discord.__version__}")
        print(f"Bot Instance Type: {BOT_INSTANCE_TYPE}") 
        if DISABLE_DB_EVENT_LOGGING:
            print("INFO: Database event logging is DISABLED for this instance.")
    else:
        print("CRITICAL ERROR: Bot user object not found on ready.")
        return

    bot.http_session = aiohttp.ClientSession(headers=M28_API_HEADERS)
    print("Created persistent aiohttp ClientSession.")

    activity = discord.Activity(type=discord.ActivityType.watching, name="out for Pings | /nerdhelp")
    await bot.change_presence(status=discord.Status.online, activity=activity)

    print(f"Bot is ready and connected to {len(bot.guilds)} guild(s).")
    
    await _initialize_ai_models()
    await _initialize_data_caches(bot)
    synced_commands = await _sync_app_commands(bot)

    await _revive_static_list_views()
    # REMOVE THE LINE BELOW
    # asyncio.create_task(_catch_up_missed_self_bot_events())
    
    await _start_background_tasks(bot)

    log_guild = bot.get_guild(CATERCORD_GUILD_ID) or (bot.guilds[0] if bot.guilds else None)
    if log_guild:
        instance_info = f" ({BOT_INSTANCE_TYPE} instance)" if BOT_INSTANCE_TYPE != "PRODUCTION" else ""
        await log_info(log_guild, f"Bot ready and online{instance_info}. Synced {len(synced_commands)} commands.")
    
    print("--- on_ready event finished ---")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if after.bot or before.roles == after.roles:
        return

    guild = after.guild
    config = await load_server_config(guild.id)
    tracked_roles = {data['discord_role_id']: tag for tag, data in config.get('tracked_guilds', {}).items() if data.get('discord_role_id')}
    
    if not tracked_roles:
        return

    added_roles = set(after.roles) - set(before.roles)
    removed_roles = set(before.roles) - set(after.roles)

    changed_tracked_role: Optional[discord.Role] = None
    action: Optional[str] = None
    
    for role in added_roles:
        if role.id in tracked_roles:
            changed_tracked_role = role
            action = "added"
            break
    if not changed_tracked_role:
        for role in removed_roles:
            if role.id in tracked_roles:
                changed_tracked_role = role
                action = "removed"
                break

    if not changed_tracked_role or not action:
        return

    if not supabase: return

    user_db_resp = await run_supabase_sync(lambda: supabase.table("florr_players").select("florr_guild_tag").eq("discord_id", str(after.id)).maybe_single().execute())
    if user_db_resp is None:
        await log_error(guild, f"DB error checking user {after.mention} during on_member_update.")
        return
        
    db_guild_tag = user_db_resp.data.get('florr_guild_tag') if user_db_resp.data else None
    
    role_guild_tag = tracked_roles.get(changed_tracked_role.id)
    discrepancy = False

    if action == "added" and db_guild_tag != role_guild_tag:
        discrepancy = True
        reason = f"User was manually given the `{changed_tracked_role.name}` role, but their database record indicates they belong to `{db_guild_tag or 'no guild'}`."
    elif action == "removed" and db_guild_tag == role_guild_tag:
        discrepancy = True
        reason = f"The `{changed_tracked_role.name}` role was manually removed from the user, but their database record indicates they should be in `{db_guild_tag}`."

    if discrepancy:
        embed = discord.Embed(title="Manual Role Discrepancy Detected", description=reason, color=discord.Color.orange())
        embed.add_field(name="User", value=f"{after.mention} (`{after.id}`)", inline=True)
        embed.add_field(name="Role", value=f"{changed_tracked_role.mention} (`{changed_tracked_role.id}`)", inline=True)
        embed.add_field(name="Action", value=f"Role was manually **{action.upper()}**.", inline=True)
        embed.add_field(name="Recommendation", value=f"Use bot commands (`/setguild`) or run `/refresh` to sync roles with the database.", inline=False)
        embed.set_footer(text="This log indicates a potential inconsistency between Discord roles and the database.")
        await log_error(guild, "Manual Role Discrepancy", embed=embed)

# --- App Command Error Handling ---
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    guild = interaction.guild
    user_msg = "❌ An unexpected error occurred. Please try again later or contact an admin."
    log_desc = "Unhandled App Command Error"
    error_to_log: Optional[Exception] = error
    # Default to ephemeral for user-facing errors
    is_ephemeral_response = True

    if isinstance(error, app_commands.CommandNotFound):
        print(f"CommandNotFound error received for interaction: {interaction.data.get('name', 'N/A')}")
        return
    elif isinstance(error, app_commands.MissingPermissions):
        perms = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
        user_msg = f"❌ You lack the required permissions to use this command: {perms}"
        log_desc = f"User Missing Permissions: {perms}"
        error_to_log = None
    elif isinstance(error, app_commands.BotMissingPermissions):
        perms = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
        user_msg = f"❌ I lack the required permissions to perform this action: {perms}. Please contact an admin."
        log_desc = f"Bot Missing Permissions: {perms}"
        error_to_log = None
    elif isinstance(error, app_commands.CheckFailure):
        user_msg = "❌ You do not meet the requirements to use this command in this context."
        log_desc = f"Check Failure ({type(error).__name__})"
        if hasattr(error, 'message') and error.message: log_desc += f": {error.message}"
        error_to_log = None
    elif isinstance(error, app_commands.CommandInvokeError):
        original_error = error.original
        error_to_log = original_error
        user_msg = f"❌ An error occurred while running the command. Please report this if it persists."
        log_desc = f"Command Invoke Error in `/{interaction.command.name if interaction.command else 'Unknown'}`"
        is_ephemeral_response = False # Make invocation errors public so others see there's a problem
        print(f"CommandInvokeError in command '{interaction.command.name if interaction.command else 'Unknown'}':")
        traceback.print_exception(type(original_error), original_error, original_error.__traceback__)
    elif isinstance(error, app_commands.TransformerError):
        user_msg = f"❌ Invalid input provided: {error}"
        log_desc = f"Transformer Error: {error}"
        error_to_log = error
    elif isinstance(error, app_commands.CommandOnCooldown):
        user_msg = f"⏳ This command is on cooldown. Please try again in {error.retry_after:.1f} seconds."
        log_desc = f"Command Cooldown Hit ({error.retry_after:.1f}s)"
        error_to_log = None
    elif isinstance(error, app_commands.NoPrivateMessage):
         user_msg = "❌ This command cannot be used in Direct Messages."
         log_desc = "Command used in DM"
         error_to_log = None
    else:
        log_desc = f"Unknown App Command Error Type: `{type(error).__name__}`"

    await log_error(guild, log_desc, error=error_to_log, interaction=interaction)

    try:
        if interaction.response.is_done():
            await interaction.followup.send(user_msg, ephemeral=is_ephemeral_response)
        else:
            await interaction.response.send_message(user_msg, ephemeral=is_ephemeral_response)
    except (discord.NotFound, discord.InteractionResponded, discord.HTTPException) as e:
        print(f"Error Handler: Failed to send error message to user (InteractionID: {interaction.id}): {type(e).__name__} - {e}")


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
@tree.command(name="verify", description="[Staff Only] Manually sets a user's verification roles.")
@app_commands.describe(user="The user to manage roles for.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    if not await is_module_enabled(interaction, "verification"):
        await interaction.response.send_message("❌ The 'Verification' module is not enabled on this server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False, thinking=True)

    config = await load_server_config(guild.id)
    verified_role_id = config.get('verified_role_id')
    unverified_role_id = config.get('unverified_role_id')

    if not verified_role_id or not unverified_role_id:
        await interaction.followup.send("❌ This server has not configured a `Verified` and `Unverified` role. Use `/setup`.", ephemeral=True)
        return

    verified_role = guild.get_role(verified_role_id)
    unverified_role = guild.get_role(unverified_role_id)

    if not verified_role or not unverified_role:
        await interaction.followup.send("❌ The configured `Verified` or `Unverified` role was not found in this server.", ephemeral=True)
        return

    try:
        if verified_role not in user.roles:
            await user.add_roles(verified_role, reason=f"Manually verified by {interaction.user}")
        if unverified_role in user.roles:
            await user.remove_roles(unverified_role, reason=f"Manually verified by {interaction.user}")
        
        await interaction.followup.send(f"✅ Manually set {user.mention} to a verified state (added `{verified_role.name}`, removed `{unverified_role.name}`).", ephemeral=False)
        await log_info(guild, f"{interaction.user.name} manually verified {user.name} using /verify.")
    except Exception as e:
        await log_error(guild, "Error during manual /verify", error=e, interaction=interaction)
        await interaction.followup.send("❌ An error occurred while managing roles.", ephemeral=True)

@tree.command(name="connect", description="Connect your Discord account to your Florr IGN.")
@app_commands.describe(
    ingame_name="Your exact in-game name.",
    user="[Staff Only] The user to connect."
)
@app_commands.autocomplete(ingame_name=ign_autocomplete)
async def connect(interaction: discord.Interaction, ingame_name: str, user: Optional[discord.Member] = None):
    if not await is_module_enabled(interaction, "verification"):
        await interaction.response.send_message("❌ The 'Verification' module is not enabled on this server.", ephemeral=True)
        return

    if not await check_supabase_available(interaction): return
    guild = interaction.guild

    target_user = user or interaction.user
    if user and interaction.user.id != user.id and not await is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ You need to be a server admin to connect another user's account.", ephemeral=True)
        return
    if not isinstance(target_user, discord.Member):
        await interaction.response.send_message("Target must be a member of this server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    cleaned_ign = clean_ign(ingame_name)
    if not cleaned_ign:
        await interaction.followup.send("❌ In-game name cannot be empty.", ephemeral=True)
        return

    try:
        params = {
            'p_discord_id': str(target_user.id),
            'p_discord_name': str(target_user),
            'p_ign': cleaned_ign
        }
        await run_supabase_sync(lambda: supabase.rpc('connect_florr_player', params).execute())

        await trigger_global_role_sync_for_user(target_user)
        await load_ign_cache(guild)
        
        await interaction.followup.send(f"✅ Successfully connected {target_user.mention} to IGN `{cleaned_ign}`.", ephemeral=False)
        await log_info(guild, f"`{interaction.user.name}` connected `{target_user.name}` to IGN `{cleaned_ign}`.")

    except APIError as e:
        if "IGN_TAKEN_BY" in e.message:
            try:
                conflict_user_id = e.message.split(':')[-1]
                await interaction.followup.send(f"❌ **Conflict:** The IGN `{cleaned_ign}` is already connected to <@{conflict_user_id}>.", ephemeral=True)
            except Exception:
                await interaction.followup.send(f"❌ **Conflict:** The IGN `{cleaned_ign}` is already in use by another account.", ephemeral=True)
        else:
            await log_error(guild, f"Error during /connect (API)", error=e, interaction=interaction)
            await interaction.followup.send(f"❌ A database error occurred: {e.message}", ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Error during /connect (General)", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)

@tree.command(name="disconnect", description="Disconnect your Discord account from your Florr IGN.")
@app_commands.describe(user="[Staff Only] The user to disconnect.")
async def disconnect(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    if not await is_module_enabled(interaction, "verification"):
        await interaction.response.send_message("❌ The 'Verification' module is not enabled on this server.", ephemeral=True)
        return

    if not await check_supabase_available(interaction): return
    guild = interaction.guild

    target_user = user or interaction.user
    if user and interaction.user.id != user.id and not await is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ You need to be a server admin to disconnect another user's account.", ephemeral=True)
        return
    if not isinstance(target_user, discord.Member):
        await interaction.response.send_message("Target must be a member of this server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        update_resp = await run_supabase_sync(lambda: supabase.table("florr_players").update({"discord_id": None, "discord_name": None}).eq("discord_id", str(target_user.id)).execute())

        if not update_resp.data:
            await interaction.followup.send(f"ℹ️ {target_user.mention} was not connected to any IGN in the database.", ephemeral=True); return
        
        await trigger_global_role_sync_for_user(target_user)
        ign_disconnected = update_resp.data[0].get('ingame_name', 'an IGN')
        await interaction.followup.send(f"✅ Successfully disconnected {target_user.mention} from `{ign_disconnected}`. Roles are being updated across all servers.", ephemeral=False)
        await log_info(guild, f"`{interaction.user.name}` disconnected `{target_user.name}`.")

    except Exception as e:
        await log_error(guild, f"Error during /disconnect for {target_user.name}", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)

async def setguild_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    choices = [app_commands.Choice(name="None (Remove from guild)", value="--NONE--")]
    if not interaction.guild: return choices
    
    config = await load_server_config(interaction.guild.id)
    tracked_guilds = config.get('tracked_guilds', {})
    
    for tag in tracked_guilds.keys():
        if len(choices) >= 25: break
        if not current or current.lower() in tag.lower():
            choices.append(app_commands.Choice(name=tag, value=tag))
    return choices

@tree.command(name="setguild", description="[Staff Only] Set a user's tracked Florr guild by Discord or IGN.")
@app_commands.describe(
    guild_tag="The guild to assign them to, or 'None' to remove.",
    user="[Optional] The Discord user to modify.",
    ingame_name="[Optional] The In-Game Name to modify."
)
@app_commands.autocomplete(guild_tag=setguild_autocomplete, ingame_name=ign_autocomplete)
@app_commands.checks.has_permissions(manage_roles=True)
async def setguild(
    interaction: discord.Interaction, 
    guild_tag: str,
    user: Optional[discord.Member] = None,
    ingame_name: Optional[str] = None
):
    if not await is_module_enabled(interaction, "guild_management"):
        await interaction.response.send_message("❌ The 'Guild Management' module is not enabled on this server.", ephemeral=True)
        return

    if not await check_supabase_available(interaction): return
    guild = interaction.guild

    if not user and not ingame_name:
        await interaction.response.send_message("❌ You must provide either a `user` or an `ingame_name`.", ephemeral=True); return
    if user and ingame_name:
        await interaction.response.send_message("❌ Please provide either a `user` or an `ingame_name`, not both.", ephemeral=True); return

    await interaction.response.defer(ephemeral=True)
    normalized_tag = _normalize_guild_tag(guild_tag) if guild_tag != "--NONE--" else None
    
    config = await load_server_config(guild.id)
    if normalized_tag and normalized_tag not in config.get('tracked_guilds', {}):
        await interaction.followup.send(f"❌ The guild tag **{normalized_tag}** is not a tracked guild in this server.", ephemeral=True); return
        
    try:
        update_resp = None
        target_display = ""
        target_member_for_roles: Optional[discord.Member] = None

        if user:
            target_display = user.mention
            target_member_for_roles = user
            update_resp = await run_supabase_sync(lambda: supabase.table("florr_players").update({"florr_guild_tag": normalized_tag}).eq("discord_id", str(user.id)).execute())
        
        elif ingame_name:
            cleaned_ign = clean_ign(ingame_name)
            target_display = f"IGN `{cleaned_ign}`"
            update_resp = await run_supabase_sync(
                lambda: supabase.table("florr_players")
                               .upsert({"ingame_name": cleaned_ign, "florr_guild_tag": normalized_tag}, on_conflict="ingame_name")
                               .execute()
            )
            await load_ign_cache(guild)
            
            if update_resp and update_resp.data and update_resp.data[0].get('discord_id'):
                discord_id = int(update_resp.data[0]['discord_id'])
                target_member_for_roles = guild.get_member(discord_id)
        
        if not update_resp or not update_resp.data:
            await interaction.followup.send(f"❌ Could not find or create a database record for {target_display}. If targeting a user, use `/connect` first.", ephemeral=True)
            return

        if target_member_for_roles:
            await trigger_global_role_sync_for_user(target_member_for_roles)
            
        ign_from_db = update_resp.data[0].get('ingame_name', 'N/A')
        
        if normalized_tag:
            await interaction.followup.send(f"✅ Set `{ign_from_db}` ({target_display})'s guild to **{normalized_tag}**. Roles updated if applicable.", ephemeral=False)
            await log_info(guild, f"`{interaction.user.name}` set guild for {target_display} to {normalized_tag}.")
        else:
            await interaction.followup.send(f"✅ Removed `{ign_from_db}` ({target_display}) from any tracked guild. Roles updated if applicable.", ephemeral=False)
            await log_info(guild, f"`{interaction.user.name}` removed guild from {target_display}.")
            
        for bot_guild in bot.guilds:
            if target_member_for_roles and bot_guild.get_member(target_member_for_roles.id):
                asyncio.create_task(refresh_all_guild_lists(bot_guild))

    except Exception as e:
        await log_error(guild, f"Error during /setguild for {user.name if user else ingame_name}", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)

# --- REVISED /hcmembers Command ---
@tree.command(name="hcmembers", description="Show interactive list of [HC1] members (Discord/DB data).")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    if not await check_supabase_available(interaction):
        try:
            if interaction.response.is_done(): await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        except (discord.NotFound, discord.HTTPException): pass
        return
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    # --- MODIFIED PART ---
    # Load server config to get the correct channel ID
    config = await load_server_config(guild.id)
    # Check if bot is disabled
    if not config.get('bot_enabled', True) and interaction.user.id != OWNER_USER_ID:
        await interaction.response.send_message("❌ The bot is currently disabled in this server.", ephemeral=True)
        return

    hcmembers_channel_id = config.get('hcmembers_channel_id')

    # Allow command if it's in the designated channel, or if no channel is set, or if user is owner
    is_in_correct_channel = (not hcmembers_channel_id) or (interaction.channel_id == hcmembers_channel_id)
    if not is_in_correct_channel and interaction.user.id != OWNER_USER_ID:
        hcmembers_channel = guild.get_channel(hcmembers_channel_id)
        channel_mention = hcmembers_channel.mention if hcmembers_channel else f"the configured channel (ID: {hcmembers_channel_id})"
        await interaction.response.send_message(f"❌ This command can only be used in {channel_mention}.", ephemeral=True)
        return
    # --- END MODIFIED PART ---

    await interaction.response.defer(thinking=True, ephemeral=False)

    is_target_guild = guild.id == CATERCORD_GUILD_ID

    try:
        data_for_view = []
        total_count = 0
        original_data_param = []

        if is_target_guild:
            original_data, total_count = await fetch_hc_member_data(guild)
            if not original_data:
                await interaction.edit_original_response(embed=create_embed(title=HC_LIST_EMBED_TITLE, description="No HC members found.", color=discord.Color.orange()), view=None)
                return

            initial_display_data = list(original_data)
            try:
                today_utc = datetime.datetime.now(pytz.utc).date()
                end_date_monthly = today_utc
                start_date_monthly = today_utc - datetime.timedelta(days=29)
                all_igns = [item['ign'] for item in original_data if item.get('ign')]

                if all_igns:
                    monthly_activity_data = await fetch_activity_data(guild, all_igns, start_date_monthly, end_date_monthly)
                    temp_data = []
                    for item in original_data:
                        ign_lower = item.get('ign', '').lower()
                        activity_info = monthly_activity_data.get(ign_lower, {'count': 0, 'last_seen': None})
                        updated_item = item.copy()
                        updated_item['activity_count'] = activity_info['count']
                        updated_item['last_seen'] = activity_info['last_seen']
                        temp_data.append(updated_item)
                    initial_display_data = temp_data
            except Exception as fetch_err:
                 await log_error(guild, "Failed initial monthly activity for /hcmembers", error=fetch_err, interaction=interaction)
                 initial_display_data = list(original_data)

            data_for_view = initial_display_data
            original_data_param = original_data

        else:
            supabase_only_data, total_count = await fetch_all_supabase_hc_data(guild)
            if not supabase_only_data:
                await interaction.edit_original_response(embed=create_embed(title="HC Database Members (All)", description="No members found in DB.", color=discord.Color.orange()), view=None)
                return
            data_for_view = supabase_only_data
            original_data_param = supabase_only_data

        view = HCPagesView(
            original_data=original_data_param,
            initial_display_data=data_for_view,
            total_members=total_count,
            guild=guild,
            is_catercord_context=is_target_guild
        )
        initial_embed = view.create_page_embed()
        message = await interaction.edit_original_response(embed=initial_embed, view=view)
        view.message = message

    except Exception as e:
        await log_error(guild, "Unhandled /hcmembers error", error=e, interaction=interaction, ping_owner=True)
        try:
            await interaction.edit_original_response(content=None, embed=create_embed("❌ An unexpected error occurred.", discord.Color.red()), view=None)
        except (discord.NotFound, discord.HTTPException):
            pass

# Add a new helper function right before the /profile command definition
async def get_guild_tag_from_ign(guild: Optional[discord.Guild], ign: str) -> Optional[str]:
    """Fetches just the florr_guild_tag for a given IGN."""
    if not supabase: return None
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("florr_players")
                           .select("florr_guild_tag")
                           .ilike("ingame_name", ign)
                           .limit(1)
                           .maybe_single()
                           .execute()
        )
        if resp and resp.data:
            return resp.data.get('florr_guild_tag')
        return None
    except Exception as e:
        await log_error(guild, f"Failed to fetch guild tag for IGN {ign}", error=e)
        return None

# Replace the /profile command with this new version

@tree.command(name="profile", description="View Florr.io profile, activity, super attempts, crafts, and defeats.")
@app_commands.describe(
    user="[Optional] Select a Discord user to view their profile.",
    ingame_name="[Optional] Or, type an In-Game Name to view its profile.",
    start_page="[Optional] Jump directly to a specific page in the profile view."
)
@app_commands.choices(start_page=[
    app_commands.Choice(name="Main", value="main"),
    app_commands.Choice(name="Activity Calendar", value="monthly"),
    app_commands.Choice(name="Super Attempt Stats", value="sa_stats"),
    app_commands.Choice(name="Super Attempt Log", value="sa_log"),
    app_commands.Choice(name="Super Craft Log", value="sc_log"),
    app_commands.Choice(name="Super Defeat Log", value="sd_log"),
    app_commands.Choice(name="Notes", value="notes"),
])
@app_commands.autocomplete(ingame_name=ign_autocomplete)
async def profile(interaction: discord.Interaction, 
                  user: Optional[discord.Member] = None, 
                  ingame_name: Optional[str] = None,
                  start_page: Optional[str] = "main"):
    guild = interaction.guild
    
    await interaction.response.defer(thinking=True, ephemeral=False)

    if not await check_supabase_available(interaction):
        await interaction.edit_original_response(content="❌ Database connection unavailable. Cannot fetch profile data.", embed=None, view=None)
        return

    hc_profile_db_data: Optional[Dict[str, Any]] = None
    partial_profile_ign: Optional[str] = None
    target_discord_id_str: Optional[str] = None

    if user:
        target_discord_id_str = str(user.id)
        hc_profile_db_data = await fetch_hc_member_profile_data(guild, target_discord_id_str)
        if not hc_profile_db_data:
            embed = discord.Embed(
                title=f"🔗 Profile Not Linked",
                description=f"**{user.display_name}** does not have a Florr.io profile connected to their Discord account yet.",
                color=discord.Color.orange()
            )
            embed.set_footer(text="The user themselves or a staff member can use the button below.")
            view = ProfileNotFoundView(target_user=user)
            await interaction.edit_original_response(embed=embed, view=view)
            view.message = await interaction.original_response()
            return
            
    elif ingame_name:
        cleaned_ign = clean_ign(ingame_name)
        hc_profile_db_data = await fetch_profile_details_by_ign(guild, cleaned_ign)
        if not hc_profile_db_data:
            crafts, _ = await get_user_super_craft_log_entries(guild, cleaned_ign, 0, 1)
            defeats, _ = await get_user_super_defeat_log_entries(guild, cleaned_ign, 0, 1)
            if crafts or defeats:
                partial_profile_ign = cleaned_ign
            else:
                await interaction.edit_original_response(content=f"❌ No profile data or event logs found for IGN `{cleaned_ign}`.", view=None)
                return
        else:
            target_discord_id_str = hc_profile_db_data.get("discord_id")
    else:
        target_discord_id_str = str(interaction.user.id)
        hc_profile_db_data = await fetch_hc_member_profile_data(guild, target_discord_id_str)
        if not hc_profile_db_data:
            embed = discord.Embed(
                title=f"🔗 Profile Not Linked",
                description=f"You don't have a Florr.io profile connected to your Discord account yet.",
                color=discord.Color.orange()
            )
            embed.set_footer(text="You can use the button below to connect your account.")
            view = ProfileNotFoundView(target_user=interaction.user)
            await interaction.edit_original_response(embed=embed, view=view)
            view.message = await interaction.original_response()
            return

    target_ign = (hc_profile_db_data.get("ingame_name") if hc_profile_db_data else None) or partial_profile_ign
    if not target_ign:
        await interaction.edit_original_response(content="❌ Critical error: Could not determine target IGN for profile.", view=None)
        return
        
    target_user_for_display: Union[discord.Member, discord.User, None] = None
    if target_discord_id_str and guild:
        target_user_for_display = guild.get_member(int(target_discord_id_str))
    elif target_discord_id_str:
        try: target_user_for_display = await bot.fetch_user(int(target_discord_id_str))
        except discord.NotFound: await log_info(guild, f"Could not fetch user object for Discord ID {target_discord_id_str}.")

    display_name_for_view = target_user_for_display.display_name if target_user_for_display else target_ign
    avatar_url_for_view = target_user_for_display.display_avatar.url if target_user_for_display and target_user_for_display.display_avatar else (bot.user.display_avatar.url if bot.user else None)
    mention_or_status_for_view = target_user_for_display.mention if target_user_for_display else ("`Not in Main Player List`" if partial_profile_ign else "`Not Linked to Discord`")
    
    target_user_display_data = {
        "name": display_name_for_view, "avatar_url": avatar_url_for_view, "mention_or_status": mention_or_status_for_view,
        "_member_object_ref": target_user_for_display if isinstance(target_user_for_display, discord.Member) else None,
        "_discord_id_for_sa_management": target_discord_id_str
    }

    today_utc_obj, _ = get_utc_date()
    activity_summary, initial_monthly_dates = None, set()
    if hc_profile_db_data and hc_profile_db_data.get('discord_id') and today_utc_obj:
        ign_lower = target_ign.lower()
        all_time_summary = await fetch_activity_data(guild, [ign_lower])
        ign_all_time_data = all_time_summary.get(ign_lower, {'count': 0, 'last_seen': None})
        activity_summary = {"total_days_logged": ign_all_time_data['count'], "last_seen_display": f"`{format_date_dmy(ign_all_time_data['last_seen'])}`" if ign_all_time_data['last_seen'] else "`Never Logged`"}
        first_day_current_month = today_utc_obj.replace(day=1)
        last_day_current_month = (first_day_current_month.replace(month=first_day_current_month.month % 12 + 1, year=first_day_current_month.year + (first_day_current_month.month // 12))) - datetime.timedelta(days=1)
        initial_monthly_dates = await fetch_activity_dates_in_range(guild, ign_lower, first_day_current_month, last_day_current_month)

    super_attempt_stats_data = await get_user_super_attempt_stats(guild, target_ign)
    initial_craft_logs, craft_total = await get_user_super_craft_log_entries(guild, target_ign, 0, ProfilePagesView.SA_LOG_ENTRIES_PER_PAGE)
    initial_defeat_logs, defeat_total = await get_user_super_defeat_log_entries(guild, target_ign, 0, ProfilePagesView.SA_LOG_ENTRIES_PER_PAGE)
    initial_notes, notes_total = await get_user_notes(guild, target_ign, 0, ProfilePagesView.SA_LOG_ENTRIES_PER_PAGE)

    final_hc_profile_data = hc_profile_db_data if hc_profile_db_data else {"ingame_name": partial_profile_ign}
    if 'florr_guild_tag' not in final_hc_profile_data:
        final_hc_profile_data['florr_guild_tag'] = await get_guild_tag_from_ign(guild, target_ign)

    profile_view = ProfilePagesView(
        interaction=interaction, target_user_display_data=target_user_display_data, hc_profile_data=final_hc_profile_data,
        activity_summary_data=activity_summary, initial_monthly_active_dates=initial_monthly_dates,
        super_attempt_stats_data=super_attempt_stats_data, 
        initial_craft_logs=initial_craft_logs, total_crafts=craft_total,
        initial_defeat_logs=initial_defeat_logs, total_defeats=defeat_total,
        initial_notes=initial_notes, total_notes=notes_total,
        today_date_obj=today_utc_obj or datetime.date.today(),
        start_page=start_page or "main"
    )
    
    embed_creator_map = {
        profile_view.MAIN_PAGE: profile_view._create_main_embed,
        profile_view.MONTHLY_PAGE: profile_view._create_monthly_embed,
        profile_view.SUPER_ATTEMPT_STATS_PAGE: profile_view._create_super_attempt_stats_embed,
        profile_view.SUPER_ATTEMPT_LOG_PAGE: profile_view._create_super_attempt_log_embed,
        profile_view.SUPER_CRAFT_LOG_PAGE: profile_view._create_super_craft_log_embed,
        profile_view.SUPER_DEFEAT_LOG_PAGE: profile_view._create_super_defeat_log_embed,
        profile_view.NOTES_PAGE: profile_view._create_notes_embed,
    }
    creator_func = embed_creator_map.get(profile_view.current_page_mode, profile_view._create_main_embed)
    initial_embed = creator_func()

    await interaction.edit_original_response(embed=initial_embed, view=profile_view)
    profile_view.message = await interaction.original_response()

@tree.command(name="add_note", description="Add a note to a player's profile.")
@app_commands.describe(
    note="The content of the note (max 200 characters).",
    user="[Optional] The Discord user to add a note to.",
    ingame_name="[Optional] The In-Game Name to add a note to."
)
@app_commands.autocomplete(ingame_name=ign_autocomplete)
async def add_note(
    interaction: discord.Interaction,
    note: str,
    user: Optional[discord.Member] = None,
    ingame_name: Optional[str] = None
):
    guild = interaction.guild
    if not await check_supabase_available(interaction): return

    if not user and not ingame_name:
        await interaction.response.send_message("❌ You must provide either a `user` or an `ingame_name`.", ephemeral=True)
        return
    if user and ingame_name:
        await interaction.response.send_message("❌ Please provide either a `user` or an `ingame_name`, not both.", ephemeral=True)
        return
    
    if len(note) > 200:
        await interaction.response.send_message("❌ Your note is too long. The maximum length is 200 characters.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    target_ign: Optional[str] = None
    if user:
        target_ign = await get_ign_from_user(guild, user.id)
        if not target_ign:
            await interaction.followup.send(f"❌ {user.mention} does not have a linked In-Game Name in the database.", ephemeral=True)
            return
    elif ingame_name:
        profile_data = await fetch_profile_details_by_ign(guild, ingame_name)
        if not profile_data or not profile_data.get('ingame_name'):
            await interaction.followup.send(f"❌ Could not find a player with the IGN `{ingame_name}` in the database.", ephemeral=True)
            return
        target_ign = profile_data['ingame_name']

    if not target_ign:
        await interaction.followup.send("❌ Could not determine the target player.", ephemeral=True)
        return

    author_id = str(interaction.user.id)
    note_count = await get_note_author_count(guild, author_id, target_ign)
    if note_count >= 5:
        await interaction.followup.send(f"❌ You have already added the maximum of 5 notes to `{target_ign}`.", ephemeral=True)
        return

    success, msg = await add_player_note(guild, author_id, target_ign, note)
    
    if success:
        await interaction.followup.send(f"✅ Note added to profile of `{target_ign}`.")
        await log_info(guild, f"{interaction.user.name} added a note to {target_ign}.")
    else:
        await interaction.followup.send(f"❌ Failed to add note: {msg}")

@tree.command(name="refresh", description="Syncs all roles with the database and refreshes all server-specific data.")
@app_commands.checks.has_permissions(manage_guild=True)
async def refresh(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild: return

    if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
        bot_perms = interaction.channel.permissions_for(guild.me)
        if not bot_perms.send_messages or not bot_perms.embed_links:
            await interaction.response.send_message("❌ I need `Send Messages` and `Embed Links` permissions in this channel to show the refresh status.", ephemeral=True)
            return

    if not await check_supabase_available(interaction): return

    await interaction.response.defer(thinking=True, ephemeral=False)

    config = await load_server_config(guild.id)
    tracked_guilds = config.get('tracked_guilds', {})
    feedback_parts = [f"⏳ **Starting full sync and refresh for {guild.name}...**"]
    await interaction.followup.send("\n".join(feedback_parts), ephemeral=False)

    action_log = ["✅ Reloaded server configuration from database."]
    errors_occurred = False
    
    if not guild.me.guild_permissions.manage_roles:
        action_log.append("⚠️ **Role Sync Skipped:** Bot lacks `Manage Roles` permission.")
    else:
        action_log.append("⏳ Syncing all member roles with the database... (this may take a while)")
        await interaction.edit_original_response(content="\n".join(feedback_parts + action_log))
        
        all_db_users_resp = await run_supabase_sync(lambda: supabase.table("florr_players").select("discord_id, florr_guild_tag").execute())
        db_user_map = {entry['discord_id']: entry['florr_guild_tag'] for entry in all_db_users_resp.data if entry.get('discord_id')}
        
        roles_to_check = {data['discord_role_id'] for data in tracked_guilds.values() if data.get('discord_role_id')}
        
        synced_count = 0
        for member in guild.members:
            if member.bot: continue
            
            db_tag = db_user_map.get(str(member.id))
            required_role_id = tracked_guilds.get(db_tag, {}).get('discord_role_id') if db_tag else None
            
            member_has_req_role = guild.get_role(required_role_id) in member.roles if required_role_id else False
            if required_role_id and not member_has_req_role:
                await refresh_roles_for_single_user(guild, member)
                synced_count += 1
                await asyncio.sleep(0.5)

            for role in member.roles:
                if role.id in roles_to_check and role.id != required_role_id:
                    await refresh_roles_for_single_user(guild, member)
                    synced_count += 1
                    await asyncio.sleep(0.5)
                    break 
        action_log[-1] = f"✅ Role sync complete. Processed {synced_count} member adjustments."

    await refresh_all_guild_lists(guild)
    action_log.append(f"✅ Triggered updates for all configured static member lists.")
    
    await load_keyword_data()
    action_log.append("✅ Refreshed AI keyword data from database.")

    final_title = "✅ Refresh & Sync Complete" if not errors_occurred else "⚠️ Refresh & Sync Completed with Errors"
    final_embed = discord.Embed(title=final_title, description="\n".join(action_log), color=NERDY_YELLOW if not errors_occurred else discord.Color.orange())
    await interaction.edit_original_response(content="", embed=final_embed)
    await log_info(guild, f"/refresh command completed by {interaction.user.name}. Status: {'OK' if not errors_occurred else 'WITH_ERRORS'}")


# --- Wither Command ---
# --- Wither Command (MODIFIED - Invoker Hierarchy Check Removed) ---
@tree.command(name="wither", description="Temporarily remove roles from a user.")
@app_commands.describe(
    user="User to wither.",
    time="Duration in minutes (0.1 to 10, default 2)."
)
async def wither(interaction: discord.Interaction, user: discord.Member, time: app_commands.Range[float, 0.1, 10.0] = 2.0):
    guild = interaction.guild
    invoker = interaction.user

    if not guild:
        await interaction.response.send_message("This command cannot be used outside a server.", ephemeral=True)
        return

    if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
        bot_perms = interaction.channel.permissions_for(guild.me)
        if not bot_perms.send_messages or not bot_perms.embed_links:
            await interaction.response.send_message("❌ I need `Send Messages` and `Embed Links` permissions in this channel to send the wither confirmation.", ephemeral=True)
            return

    config = await load_server_config(guild.id)
    if not config.get('wither_command_enabled', True) and interaction.user.id != OWNER_USER_ID:
        await interaction.response.send_message("❌ This command is currently disabled in this server.", ephemeral=True)
        return
    
    # Permission Check
    required_role_id = config.get('wither_command_role_id')
    user_is_staff = await is_admin_or_owner(interaction)
    if required_role_id:
        required_role = guild.get_role(required_role_id)
        if required_role and not isinstance(invoker, discord.Member) or (required_role not in invoker.roles and not user_is_staff):
            await interaction.response.send_message(f"❌ You need the {required_role.mention} role to use this command.", ephemeral=True)
            return
    elif not user_is_staff:
        await interaction.response.send_message("❌ You need to be an admin to use this command.", ephemeral=True)
        return

    bot_member = guild.me
    if not interaction.response.is_done():
        try: await interaction.response.defer(thinking=True, ephemeral=False)
        except discord.InteractionResponded: pass

    if user.id == invoker.id: await interaction.followup.send("🤨 You cannot wither yourself.", ephemeral=True); return
    if user.id == OWNER_USER_ID and invoker.id != OWNER_USER_ID: await interaction.followup.send(f"😨 Cannot wither the protected user (<@{OWNER_USER_ID}>).", ephemeral=True); return
    if user.id == BOT_USER_ID: await interaction.followup.send("😭 You cannot wither me!", ephemeral=True); return
    if user.bot: await interaction.followup.send("🤖 You cannot wither other bots.", ephemeral=True); return
    if guild.owner_id and user.id == guild.owner_id and invoker.id != guild.owner_id: await interaction.followup.send(f"👑 You cannot wither the server owner (<@{guild.owner_id}>).", ephemeral=True); return
    if bot_member.top_role.position <= user.top_role.position: await interaction.followup.send(f"❌ My highest role ('{bot_member.top_role.name}') is not high enough to manage {user.mention}'s roles.", ephemeral=True); return
    if not bot_member.guild_permissions.manage_roles: await interaction.followup.send("❌ I lack the `Manage Roles` permission needed for this command.", ephemeral=True); return

    original_roles = [r for r in user.roles if r.id != guild.default_role.id]
    if not original_roles:
        await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} has no roles to remove.", discord.Color.orange()), ephemeral=False)
        return

    try:
        wither_seconds = min(max(1, int(time * 60)), int(MAX_WITHER_SECONDS or 600))
        actual_minutes = wither_seconds / 60.0
        reason_wither = f"Withered by {invoker.name} for {actual_minutes:.1f}m."

        roles_to_remove_actually = [r for r in original_roles if bot_member.top_role.position > r.position]
        skipped_roles_remove = [r for r in original_roles if r not in roles_to_remove_actually]

        if not roles_to_remove_actually:
             await interaction.followup.send(embed=create_embed(f"ℹ️ Cannot wither {user.display_name}: No manageable roles.", color=discord.Color.orange()), ephemeral=False)
             return

        roles_to_set_during_wither = [guild.default_role]
        withered_role_obj = guild.get_role(config.get('withered_role_id')) if config.get('withered_role_id') else None
        
        special_wither_role_added_msg_part = ""
        if withered_role_obj:
            if bot_member.top_role > withered_role_obj:
                roles_to_set_during_wither.append(withered_role_obj)
                special_wither_role_added_msg_part = f"\n**Special Role Added:** `{withered_role_obj.name}`"
            else:
                special_wither_role_added_msg_part = f"\n*(Note: Could not add withered role '{withered_role_obj.name}' due to hierarchy.)*"

        await user.edit(roles=roles_to_set_during_wither, reason=reason_wither)

        roles_removed_names = (', '.join(f"`{r.name}`" for r in roles_to_remove_actually) or 'None')
        if len(roles_removed_names) > 850: roles_removed_names = roles_removed_names[:847] + "..."

        wither_desc = f"{user.mention} has been withered by {invoker.mention} for **{actual_minutes:.1f} minutes**!\n\n**Roles Removed:** {roles_removed_names}"
        wither_desc += special_wither_role_added_msg_part
        if skipped_roles_remove:
            skipped_names = (', '.join(f"`{r.name}`" for r in skipped_roles_remove))
            wither_desc += f"\n*(Skipped removing {len(skipped_roles_remove)} role(s) due to hierarchy: {skipped_names})*"

        await interaction.followup.send(embed=create_embed(title="🌪️ Wither Cast! 🌪️", description=wither_desc, color=discord.Color.dark_purple()), ephemeral=False)

        await asyncio.sleep(wither_seconds)

        try:
            member_after = await guild.fetch_member(user.id)
            await member_after.edit(roles=[guild.default_role] + original_roles, reason=f"Wither expired after {actual_minutes:.1f}m.")
            restore_msg = f"✨ {member_after.mention}'s roles have been restored!"
            await interaction.followup.send(embed=create_embed(restore_msg, color=NERDY_YELLOW), ephemeral=False)
        except discord.NotFound:
            await log_info(guild, f"Wither restore skipped: User `{user.name}` left.")
        except Exception as e_restore:
            await log_error(guild, f"Wither restore failed for {user.name}.", error=e_restore)
    except Exception as e:
        await log_error(guild, f"Wither initial remove failed for {user.name}.", error=e, interaction=interaction)



@bot.event
async def on_message(message: discord.Message):
    if not message.guild or not bot.is_ready() or not bot.user or \
       message.author.id == bot.user.id or (message.author.bot and not message.webhook_id):
        return

    config = await load_server_config(message.guild.id)
    if not config.get('bot_enabled', True) and message.author.id != OWNER_USER_ID:
        return

    if message.content.strip() == "//super" and message.author.id == OWNER_USER_ID:
        await handle_super_command(message)
        return

    screenshot_channel_id = config.get('screenshots_dropbox_channel_id')
    super_attempt_channel_id = config.get('super_attempts_channel_id')
    
    if message.guild.id == CATERCORD_GUILD_ID and message.channel.id == AUTOMOD_ALERT_CHANNEL_ID and message.type == discord.MessageType.auto_moderation_action:
        await handle_zorr_pro_automod(message)
        return

    if not message.content and not message.attachments and not message.embeds:
        return

    if screenshot_channel_id and message.channel.id == screenshot_channel_id and message.attachments:
        await handle_screenshot_dropbox(message)
        return

    if super_attempt_channel_id and message.channel.id == super_attempt_channel_id:
        await handle_super_attempt_message(message)
        return
    
    await process_message_for_ai(message)

@tree.command(name="message", description="[Owner] Send, edit, or reply to a message with full customization.")
@app_commands.describe(
    action="The operation to perform.",
    content="The message content to send, or the new content for an edit.",
    as_user="The custom name to use for the webhook message (for 'send'/'reply').",
    avatar="The custom avatar to use for the webhook message (for 'send'/'reply').",
    target_message_link="The link to the message you want to 'edit' or 'reply' to.",
    ping_on_reply="For the 'reply' action, choose whether to ping the original author."
)
@app_commands.choices(action=[
    app_commands.Choice(name="Send New Message", value="send"),
    app_commands.Choice(name="Reply to Message", value="reply"),
    app_commands.Choice(name="Edit Bot's Message", value="edit"),
])
@app_commands.choices(ping_on_reply=[
    app_commands.Choice(name="Yes, ping the user", value=1),
    app_commands.Choice(name="No, do not ping", value=0),
])
@app_commands.autocomplete(avatar=webhook_avatar_autocomplete)
async def message_command(
    interaction: discord.Interaction,
    action: str,
    content: str,
    as_user: Optional[str] = None,
    avatar: Optional[str] = None,
    target_message_link: Optional[str] = None,
    ping_on_reply: Optional[app_commands.Choice[int]] = None
):
    # --- 1. Owner and Guild Check ---
    if interaction.user.id != OWNER_USER_ID:
        await interaction.response.send_message("❌ Unauthorized. This command is for the bot owner only.", ephemeral=True)
        return
    
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    # --- 2. EDIT Action Logic ---
    if action == "edit":
        if not target_message_link:
            await interaction.followup.send("❌ The `target_message_link` is required for the 'edit' action.", ephemeral=True)
            return

        try:
            # Parse the message link to get IDs
            match = re.match(r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)", target_message_link)
            if not match:
                await interaction.followup.send("❌ Invalid message link format. Please provide a valid Discord message link.", ephemeral=True)
                return
            
            link_guild_id, channel_id, message_id = map(int, match.groups())

            if link_guild_id != guild.id:
                 await interaction.followup.send("❌ The message link must be from the current server.", ephemeral=True)
                 return

            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                await interaction.followup.send("❌ Could not find the channel from the message link.", ephemeral=True)
                return

            message_to_edit = await channel.fetch_message(message_id)

            # IMPORTANT: Only allow editing messages sent by the bot itself.
            if message_to_edit.author.id != bot.user.id:
                await interaction.followup.send("❌ The 'edit' action can only be used on messages sent by me (the bot).", ephemeral=True)
                return

            await message_to_edit.edit(content=content)
            await interaction.followup.send(f"✅ Successfully edited the message. [Jump to message]({message_to_edit.jump_url})", ephemeral=True)
            await log_info(guild, f"Owner used /message to edit bot message {message_id} in #{channel.name}.")

        except discord.NotFound:
            await interaction.followup.send("❌ The message or channel from the link could not be found.", ephemeral=True)
        except Exception as e:
            await log_error(guild, "Error during /message 'edit' action", error=e, interaction=interaction)
            await interaction.followup.send("❌ An unexpected error occurred while editing the message.", ephemeral=True)
        return

    # --- 3. SEND and REPLY Action Logic ---
    elif action in ["send", "reply"]:
        # Parameter validation for these actions
        if not as_user or not avatar:
            await interaction.followup.send("❌ The `as_user` and `avatar` parameters are required to send or reply.", ephemeral=True)
            return
            
        processed_content, mention_error = await block_unwanted_mentions(content, interaction.user.id)
        if mention_error:
            await interaction.followup.send(f"❌ {mention_error}", ephemeral=True)
            return
            
        target_channel = interaction.channel
        message_to_reply = None
        
        # Validate and fetch reply target if needed
        if action == "reply":
            if not target_message_link:
                await interaction.followup.send("❌ `target_message_link` is required for the 'reply' action.", ephemeral=True)
                return
            try:
                match = re.match(r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)", target_message_link)
                if not match:
                    await interaction.followup.send("❌ Invalid message link format for reply.", ephemeral=True)
                    return
                
                _, channel_id, message_id = map(int, match.groups())
                reply_channel = guild.get_channel(channel_id)
                if not isinstance(reply_channel, discord.TextChannel):
                    await interaction.followup.send("❌ Channel from reply link not found.", ephemeral=True)
                    return
                
                target_channel = reply_channel # The message will be sent in the reply's channel
                message_to_reply = await target_channel.fetch_message(message_id)
            except discord.NotFound:
                await interaction.followup.send("❌ The message to reply to was not found.", ephemeral=True)
                return
            except Exception as e:
                await log_error(guild, "Error fetching reply target for /message", error=e, interaction=interaction)
                await interaction.followup.send("❌ Error fetching the message to reply to.", ephemeral=True)
                return

        # Check permissions in the target channel
        if not target_channel.permissions_for(guild.me).manage_webhooks:
            await interaction.followup.send(f"❌ I need the `Manage Webhooks` permission in {target_channel.mention}.", ephemeral=True)
            return
            
        # Process avatar choice
        avatar_bytes: Optional[bytes] = None
        try:
            source_type, value = avatar.split(":", 1)
            if source_type == "member":
                member = await guild.fetch_member(int(value))
                avatar_url = member.display_avatar.url or member.default_avatar.url
                async with aiohttp.ClientSession() as session: avatar_bytes = await fetch_avatar_bytes(session, avatar_url)
            elif source_type == "image":
                folder_id, filename = value.split(":", 1)
                image_path = os.path.join(PROFILE_PIC_BASE_PATH, folder_id, filename)
                if os.path.exists(image_path):
                    with open(image_path, "rb") as f: avatar_bytes = f.read()
                else: await interaction.followup.send(f"❌ Image file not found: `{filename}`", ephemeral=True); return
        except Exception as e:
            await log_error(guild, f"Error processing avatar choice for /message", error=e, interaction=interaction)
            await interaction.followup.send("❌ Error processing avatar choice.", ephemeral=True)
            return

        # Create and use the temporary webhook
        temp_webhook = None
        try:
            webhook_name = as_user[:80] # Discord limit for webhook name
            temp_webhook = await target_channel.create_webhook(name=webhook_name, avatar=avatar_bytes, reason="/message command by owner")
            
            send_kwargs = {}
            if action == "reply" and message_to_reply:
                send_kwargs["message_reference"] = message_to_reply.to_reference()
                send_kwargs["allowed_mentions"] = discord.AllowedMentions(replied_user=(ping_on_reply is not None and ping_on_reply.value == 1))
            
            await temp_webhook.send(processed_content, **send_kwargs)
            
            action_past_tense = "replied to the message" if action == "reply" else "sent the message"
            await interaction.followup.send(f"✅ Successfully {action_past_tense} in {target_channel.mention} as `{as_user}`.", ephemeral=True)
            await log_info(guild, f"Owner used /message to {action} in #{target_channel.name} as '{as_user}'.")

        except Exception as e:
            await log_error(guild, f"Error using temp webhook for /message", error=e, interaction=interaction)
            await interaction.followup.send("❌ An unexpected error occurred while sending the message.", ephemeral=True)
        finally:
            if temp_webhook:
                await temp_webhook.delete(reason="/message command cleanup")

@tree.command(name="imitate", description="[Staff Only] Send a message appearing as another user.")
@app_commands.describe(
    user="The user to imitate (name and avatar).",
    message_content="The content of the message to send."
)
async def imitate(
    interaction: discord.Interaction,
    user: discord.Member,
    message_content: str
):
    guild = interaction.guild
    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel) or not guild:
        await interaction.response.send_message("This command can only be used in server text channels.", ephemeral=True)
        return

    config = await load_server_config(guild.id)
    required_role_id = config.get('imitate_command_role_id')
    user_is_staff = await is_admin_or_owner(interaction)

    if required_role_id:
        required_role = guild.get_role(required_role_id)
        if not required_role:
            await interaction.response.send_message("⚠️ Config Error: The role for this command was not found. Contact an admin.", ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member) or (required_role not in interaction.user.roles and not user_is_staff):
            await interaction.response.send_message(f"❌ You need the {required_role.mention} role to use this command.", ephemeral=True)
            return
    elif not user_is_staff:
        await interaction.response.send_message("❌ You need to be an admin to use this command.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)

    processed_content, mention_error = await block_unwanted_mentions(message_content, interaction.user.id)
    if mention_error:
        await interaction.edit_original_response(content=f"❌ {mention_error}", view=None)
        return

    bot_perms = interaction.channel.permissions_for(guild.me)
    if not bot_perms.manage_webhooks:
        await interaction.followup.send(f"❌ I lack 'Manage Webhooks' permission in {interaction.channel.mention}.", ephemeral=True)
        return

    avatar_bytes: Optional[bytes] = None
    async with aiohttp.ClientSession() as session:
        avatar_url_to_fetch = user.display_avatar.url if user.display_avatar else user.default_avatar.url
        avatar_bytes = await fetch_avatar_bytes(session, avatar_url_to_fetch)

    temp_webhook: Optional[discord.Webhook] = None
    try:
        webhook_name = user.display_name[:80]
        if any(d in webhook_name.lower() for d in ["@", "#", ":", "```", "discord"]) or webhook_name.lower() == "clyde":
             webhook_name = "Imitated User"

        temp_webhook = await interaction.channel.create_webhook(name=webhook_name, avatar=avatar_bytes, reason=f"/imitate by {interaction.user}")
        await temp_webhook.send(content=processed_content, wait=True)
        await interaction.edit_original_response(content=f"✅ Message sent, imitating {user.mention}.")
        await log_info(guild, f"`{interaction.user}` used /imitate as {user.mention} in {interaction.channel.mention}.")

    except Exception as e:
        await log_error(guild, f"/imitate failed", error=e, interaction=interaction, ping_owner=True)
        await interaction.edit_original_response(content=f"❌ An unexpected error occurred.")
    finally:
        if temp_webhook:
            try: await temp_webhook.delete(reason="/imitate cleanup")
            except Exception as e_del: await log_error(guild, "Failed to delete temp webhook for /imitate.", error=e_del)

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
    guild = interaction.guild
    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel) or not guild:
        await interaction.response.send_message("This command can only be used in server text channels.", ephemeral=True)
        return

    config = await load_server_config(guild.id)
    required_role_id = config.get('florr_command_role_id')
    user_is_staff = await is_admin_or_owner(interaction)

    if required_role_id:
        required_role = guild.get_role(required_role_id)
        if not required_role:
            await interaction.response.send_message("⚠️ Config Error: The role for this command was not found. Contact an admin.", ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member) or (required_role not in interaction.user.roles and not user_is_staff):
            await interaction.response.send_message(f"❌ You need the {required_role.mention} role to use this command.", ephemeral=True)
            return
    elif not user_is_staff:
        await interaction.response.send_message("❌ You need to be an admin to use this command.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)

    cleaned_name = name.strip()
    if not (1 <= len(cleaned_name) <= 80):
        await interaction.edit_original_response(content="❌ Custom name must be 1-80 characters long.", view=None)
        return
    disallowed_in_names = ["@", "#", ":", "```", "discord"]
    if any(disallowed in cleaned_name.lower() for disallowed in disallowed_in_names) or cleaned_name.lower() == "clyde":
        await interaction.edit_original_response(content=f"❌ The name '{discord.utils.escape_markdown(cleaned_name)}' contains disallowed characters or is reserved.", view=None)
        return

    processed_content, mention_error = await block_unwanted_mentions(message_content, interaction.user.id)
    if mention_error:
        await interaction.edit_original_response(content=f"❌ {mention_error}", view=None)
        return

    if not available_profile_pics_cache:
        await interaction.edit_original_response(content="❌ Profile pictures unavailable. Try `/refresh` or contact an admin.", view=None)
        return

    if profile == "error_no_images_loaded":
        await send_public_florr_error(interaction, "Profile pictures could not be loaded. Please try `/refresh`.", "/florr: User selected 'error_no_images_loaded'.", log_level="error", ping_owner_on_log=True)
        return
    if profile == "error_no_matches_found":
         await send_public_florr_error(interaction, "No profile picture matches your search.", f"/florr: User selected 'error_no_matches_found'.")
         return

    valid_choice_values = {f"{folder_id_cache}:{filename_cache}" for _, folder_id_cache, filename_cache in available_profile_pics_cache}
    if profile not in valid_choice_values:
        await send_public_florr_error(interaction, f"Invalid profile selection: `{discord.utils.escape_markdown(profile)}`.", f"/florr: User provided invalid profile selection '{profile}'.")
        return

    try:
        folder_id, filename_with_ext = profile.split(":", 1)
    except ValueError:
        await send_public_florr_error(interaction, "Internal error processing profile selection.", f"/florr: Invalid profile value format: '{profile}'", log_level="error", ping_owner_on_log=True)
        return

    if not PROFILE_PIC_BASE_PATH:
        await interaction.edit_original_response(content="⚠️ Config error: Profile picture path not set.", view=None)
        return
        
    image_path = os.path.join(PROFILE_PIC_BASE_PATH, folder_id, filename_with_ext)

    if not os.path.exists(image_path):
        await send_public_florr_error(interaction, f"The image for `{discord.utils.escape_markdown(filename_with_ext)}` is missing.", f"/florr: Image file not found at '{image_path}'.", log_level="error", ping_owner_on_log=True)
        return

    chosen_avatar_bytes: Optional[bytes] = None
    try:
        with open(image_path, "rb") as f: chosen_avatar_bytes = f.read()
    except Exception as e:
        await send_public_florr_error(interaction, f"Error reading image file for `{discord.utils.escape_markdown(filename_with_ext)}`.", f"Error reading image file {image_path} for /florr", log_level="error", ping_owner_on_log=True)
        if guild: await log_error(guild, f"Error reading image file {image_path}", error=e, interaction=interaction)
        return

    temp_webhook: Optional[discord.Webhook] = None
    try:
        bot_perms = interaction.channel.permissions_for(guild.me)
        if not bot_perms.manage_webhooks:
            await interaction.edit_original_response(content=f"❌ I lack 'Manage Webhooks' permission in {interaction.channel.mention}.", view=None)
            return

        temp_webhook = await interaction.channel.create_webhook(name=cleaned_name, avatar=chosen_avatar_bytes, reason=f"/florr by {interaction.user}")
        await temp_webhook.send(content=processed_content, wait=True)
        await interaction.edit_original_response(content=f"✅ Message sent as '{cleaned_name}'.", view=None)
        await log_info(guild, f"`{interaction.user}` used /florr as '{cleaned_name}' (Pic: {profile}) in {interaction.channel.mention}.")

    except Exception as e:
        await interaction.edit_original_response(content="❌ An unexpected error occurred.", view=None)
        await log_error(guild, "/florr failed.", error=e, interaction=interaction, ping_owner=True)
    finally:
        if temp_webhook:
            try: await temp_webhook.delete(reason="/florr cleanup")
            except Exception as e_del: await log_error(guild, f"Failed to delete temp webhook for /florr.", error=e_del)
   
@tree.command(name="nerdhelp", description="Show the list of available bot commands.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return

    if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
        bot_perms = interaction.channel.permissions_for(guild.me)
        if not bot_perms.send_messages or not bot_perms.embed_links:
            try:
                await interaction.response.send_message("❌ I need `Send Messages` and `Embed Links` permissions in this channel to show the help message.", ephemeral=True)
            except discord.HTTPException:
                pass
            return

    if not bot or not bot.user:
        await interaction.response.send_message("Bot is not fully ready, cannot generate help.", ephemeral=False)
        return
    if not command_ids:
        print("Warning: command_ids dictionary is empty during nerdhelp execution! Links may not be clickable.")

    can_see_staff_commands = await is_admin_or_owner(interaction)

    view_instance = HelpPagesView(bot_user=bot.user, is_staff_view_allowed=can_see_staff_commands)
    
    if not can_see_staff_commands:
        view_instance.clear_items() 

    initial_embed = view_instance.get_current_embed()

    try:
        await interaction.response.send_message(embed=initial_embed, view=view_instance, ephemeral=False)
        view_instance.message = await interaction.original_response()
    except Exception as e:
        await log_error(interaction.guild, "Failed to send nerdhelp response", error=e, interaction=interaction)
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

    current_settings_resp = await run_supabase_sync(
        lambda: supabase.table("florr_players")
                       .select("manage_nickname_by_bot, custom_nickname_template, florr_guild_tag")
                       .eq("discord_id", str(target_user.id))
                       .maybe_single()
                       .execute()
    )
    
    current_manage_by_bot = False
    current_is_in_a_guild = False
    if current_settings_resp and hasattr(current_settings_resp, 'data') and current_settings_resp.data:
        current_manage_by_bot = current_settings_resp.data.get("manage_nickname_by_bot", False)
        current_is_in_a_guild = current_settings_resp.data.get("florr_guild_tag") is not None


    if template is not None:
        cleaned_template = template.strip()
        if not cleaned_template:
            manage_by_bot_new_value = True
            template_to_store = None
            response_message_parts.append(f"⚙️ Custom nickname template **cleared** for {target_user.mention}.")
            if current_is_in_a_guild:
                 response_message_parts.append(f"🤖 Bot will now use the default nickname format: `IGN (SATT satt)` or `IGN`.")
            else:
                 response_message_parts.append(f"🤖 Bot will now set nickname to IGN as user is not in a tracked guild.")
            response_message_parts.append(f"🤖 Bot nickname management remains **enabled** (or enabled if it was off).")

        elif len(cleaned_template) > 200:
            await interaction.followup.send(f"❌ Nickname template is too long (max 200 characters).", ephemeral=True)
            return
        else:
            manage_by_bot_new_value = True
            template_to_store = cleaned_template
            response_message_parts.append(f"⚙️ Custom nickname template for {target_user.mention} set to: `{template_to_store}`.")
            response_message_parts.append(f"🤖 Bot nickname management **enabled** (or enabled if it was off).")
            if "{satt}" not in template_to_store:
                response_message_parts.append(f"⚠️ Your template does not include `{{satt}}`. The super attempt count will not be shown.")
    else:
        manage_by_bot_new_value = not current_manage_by_bot
        if manage_by_bot_new_value:
            template_to_store = None
            response_message_parts.append(f"🤖 Bot nickname management **enabled** for {target_user.mention}.")
            if current_is_in_a_guild:
                 response_message_parts.append(f"🤖 Bot will now use the default nickname format.")
            else:
                 response_message_parts.append(f"🤖 Bot will now set nickname to IGN as user is not in a tracked guild (if different).")

        else:
            template_to_store = None
            response_message_parts.append(f"🤖 Bot nickname management **disabled** for {target_user.mention}.")
            response_message_parts.append(f"🏷️ Nickname will revert to IGN (if different and user is in a tracked guild) or be unmanaged.")


    try:
        await run_supabase_sync(
            lambda: supabase.table("florr_players")
                           .update({
                               "manage_nickname_by_bot": manage_by_bot_new_value,
                               "custom_nickname_template": template_to_store
                           })
                           .eq("discord_id", str(target_user.id))
                           .eq("ingame_name", author_ign) 
                           .execute()
        )
        response_message_parts.append(f"💾 Settings saved.")

        all_time_count = await get_all_time_super_attempt_count(guild, author_ign)
        await update_custom_nickname_on_attempt(guild, target_user, author_ign, all_time_count)
        
        response_message_parts.append(f"ℹ️ Nickname update based on new settings has been processed. Check server for changes.")

    except Exception as e:
        await log_error(guild, f"Error saving nickname settings for {target_user.mention}", error=e, interaction=interaction)
        await interaction.followup.send("❌ An error occurred while saving your nickname settings.", ephemeral=True)
        return

    await interaction.followup.send("\n".join(response_message_parts), ephemeral=True)
    await log_info(guild, f"`{interaction.user}` used /setnickname for {target_user.mention}. Manage: {manage_by_bot_new_value}, Template: '{template_to_store}'.")

@tree.command(name="setup", description="[Admin] Interactively configure the bot for this server.")
@app_commands.check(is_admin_or_owner)
async def setup(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild: return
    
    if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
        bot_perms = interaction.channel.permissions_for(guild.me)
        if not bot_perms.send_messages or not bot_perms.embed_links:
            await interaction.response.send_message("❌ I need `Send Messages` and `Embed Links` permissions in this channel to show the setup panel.", ephemeral=True)
            return

    await interaction.response.defer(ephemeral=False)
    config = await load_server_config(guild.id)
    view = SetupView(guild, config)
    message = await interaction.followup.send(embed=view.create_embed(), view=view, ephemeral=False)
    view.message = message

class NerdAdminGroup(app_commands.Group):
    """[Owner Only] Commands for global bot administration."""
    def __init__(self):
        super().__init__(name="nerd_admin", description="[Owner Only] Global bot administration.")

    @app_commands.command(name="add_global_guild", description="[Owner] Add a guild to the globally available list.")
    @app_commands.describe(tag="The guild tag (e.g., [XYZ]).", description="A short description of the guild.")
    async def add_global_guild(self, interaction: discord.Interaction, tag: str, description: str):
        if interaction.user.id != OWNER_USER_ID:
            await interaction.response.send_message("❌ Unauthorized.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True)
        await run_supabase_sync(lambda: supabase.table("globally_available_guilds").upsert({"guild_tag": tag, "description": description}).execute())
        await interaction.followup.send(f"✅ Added/updated global guild: **{tag}**.")

    @app_commands.command(name="remove_global_guild", description="[Owner] Remove a guild from the globally available list.")
    @app_commands.describe(tag="The guild tag to remove.")
    async def remove_global_guild(self, interaction: discord.Interaction, tag: str):
        if interaction.user.id != OWNER_USER_ID:
            await interaction.response.send_message("❌ Unauthorized.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True)
        await run_supabase_sync(lambda: supabase.table("globally_available_guilds").delete().eq("guild_tag", tag).execute())
        await interaction.followup.send(f"✅ Removed global guild **{tag}**.")

    @app_commands.command(name="backfill_events", description="[Owner] [Testing Only] One-time backfill of events from local JSON file.")
    async def backfill_events(self, interaction: discord.Interaction):
        # --- Security and Environment Checks ---
        if interaction.user.id != OWNER_USER_ID:
            await interaction.response.send_message("❌ Unauthorized.", ephemeral=True); return
        if BOT_INSTANCE_TYPE != "TESTING":
            await interaction.response.send_message("❌ This command can only be used on a 'TESTING' bot instance.", ephemeral=True); return
        if not supabase:
            await interaction.response.send_message("❌ Supabase client is not available.", ephemeral=True); return

        await interaction.response.defer(ephemeral=True)
        
        # --- File Path and Reading ---
        # IMPORTANT: The file path is hardcoded as per the request for your local machine.
        # This command will ONLY work when the bot is run on that specific machine.
        file_path = r"C:\Users\Vibhor Goel\Desktop\Florr.io\classified_events.json"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
        except FileNotFoundError:
            await interaction.followup.send(f"❌ **File Not Found:** The file could not be found at `{file_path}`.", ephemeral=True)
            return
        except json.JSONDecodeError as e:
            await interaction.followup.send(f"❌ **JSON Error:** The file is not a valid JSON. Error: {e}", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ **File Read Error:** An unexpected error occurred while reading the file: {e}", ephemeral=True)
            return

        # --- Data Processing and Batching ---
        crafts_to_insert = []
        defeats_to_insert = []
        
        for event in events_data:
            category = event.get('category')
            
            if category == 'petal_craft':
                try:
                    player_ign = event.get('player')
                    rarity = event.get('rarity')
                    petal_name = event.get('item') # Key is 'item' in your JSON
                    message_id = str(event.get('id'))
                    timestamp_str = event.get('timestamp')

                    if not all([player_ign, rarity, petal_name, message_id, timestamp_str]):
                        continue

                    crafts_to_insert.append({
                        "player_ign": player_ign,
                        "super_petal_name": f"{rarity} {petal_name}",
                        "craft_date": date_parse(timestamp_str).date().isoformat(),
                        "original_message_id": message_id,
                        "processed_by_id": str(bot.user.id)
                    })
                except Exception:
                    continue # Skip malformed entries

            elif category == 'mob_defeat':
                try:
                    defeats_to_insert.append({
                        "mob": event.get('mob'),
                        "rarity": event.get('rarity'),
                        "server": event.get('server'),
                        "players": event.get('players', []),
                        "message_id": str(event.get('id')),
                        "event_timestamp": date_parse(event.get('timestamp')).isoformat() if event.get('timestamp') else None
                    })
                except Exception:
                    continue # Skip malformed entries
        
        # --- Database Insertion ---
        craft_success_count = 0
        craft_fail_count = 0
        defeat_success_count = 0
        defeat_fail_count = 0

        # Batch insert crafts
        if crafts_to_insert:
            try:
                # Using `upsert` with `ignore_duplicates=True` is safer for one-time runs
                # to prevent crashes on unique constraint violations.
                craft_resp = await run_supabase_sync(
                    lambda: supabase.table("super_craft_logs").upsert(crafts_to_insert, on_conflict="original_message_id", ignore_duplicates=True).execute()
                )
                craft_success_count = len(craft_resp.data) if craft_resp and craft_resp.data else 0
                craft_fail_count = len(crafts_to_insert) - craft_success_count
            except Exception as e:
                craft_fail_count = len(crafts_to_insert)
                await log_error(interaction.guild, "Backfill failed during craft insertion", error=e)

        # Batch insert defeats
        if defeats_to_insert:
            try:
                # Defeats don't have a unique constraint, so we just insert.
                defeat_resp = await run_supabase_sync(
                    lambda: supabase.table("super_defeats").insert(defeats_to_insert).execute()
                )
                defeat_success_count = len(defeat_resp.data) if defeat_resp and defeat_resp.data else 0
                defeat_fail_count = len(defeats_to_insert) - defeat_success_count
            except Exception as e:
                defeat_fail_count = len(defeats_to_insert)
                await log_error(interaction.guild, "Backfill failed during defeat insertion", error=e)

        # --- Final Report ---
        report_embed = discord.Embed(title="✅ Event Backfill Complete", color=discord.Color.green())
        report_embed.description = f"Processed **{len(events_data)}** events from `{file_path}`."
        report_embed.add_field(name="Super Crafts", value=f"**Success:** {craft_success_count}\n**Skipped/Failed:** {craft_fail_count}", inline=True)
        report_embed.add_field(name="Super Defeats", value=f"**Success:** {defeat_success_count}\n**Skipped/Failed:** {defeat_fail_count}", inline=True)
        
        await interaction.followup.send(embed=report_embed, ephemeral=True)

# --- Register Command Groups ---
tree.add_command(NerdAdminGroup())

@tree.command(name="servercodes", description="Shows available Florr.io server codes with interactive filters.")
@app_commands.describe(
    region="[Optional] Start by filtering for a specific Server region.",
    map_name="[Optional] Start by filtering for a specific Biome (shows all regions)."
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America (NA)", value="na"),
    app_commands.Choice(name="Europe (EU)", value="eu"),
    app_commands.Choice(name="Asia (AS)", value="as"),
])
@app_commands.choices(map_name=[
    app_commands.Choice(name="Garden", value="garden"),
    app_commands.Choice(name="Desert", value="desert"),
    app_commands.Choice(name="Ocean", value="ocean"),
    app_commands.Choice(name="Jungle", value="jungle"),
    app_commands.Choice(name="Ant Hell", value="ant hell"),
    app_commands.Choice(name="Hel", value="hel"),
    app_commands.Choice(name="Sewers", value="sewers"),
    app_commands.Choice(name="Factory", value="factory"),
])
async def servercodes(interaction: discord.Interaction, region: Optional[str] = None, map_name: Optional[str] = None):
    # Permission check for sending messages in the channel
    if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
        if not interaction.guild: return
        bot_perms = interaction.channel.permissions_for(interaction.guild.me)
        if not bot_perms.send_messages or not bot_perms.embed_links:
            err_msg = "❌ I need `Send Messages` and `Embed Links` permissions in this channel to show the server list."
            try:
                await interaction.response.send_message(err_msg, ephemeral=True)
            except (discord.Forbidden, discord.HTTPException):
                pass
            return

    await interaction.response.defer(thinking=True, ephemeral=False)

    view = ServerCodeView(initial_region=region, initial_map=map_name)

    try:
        initial_embed = await view._create_server_embed()
        message = await interaction.followup.send(embed=initial_embed, view=view, wait=True)
        view.message = message
    except Exception as e:
        await log_error(interaction.guild, "Failed to send initial /servercodes view", error=e, interaction=interaction)
        try: await interaction.followup.send("❌ An error occurred while preparing the server list.", ephemeral=True)
        except discord.HTTPException: pass

@tree.command(name="webhook", description="[Owner] Manage custom, persistent webhooks for announcements.")
@app_commands.describe(
    action="The operation to perform.",
    name="A unique name for the webhook (for all actions except 'list').",
    channel="The channel for the 'create' action.",
    avatar_choice="The avatar for the 'create' action.",
    content="The message content for 'send' or 'edit' actions.",
    message_id="The ID of the message to 'edit'."
)
@app_commands.choices(action=[
    app_commands.Choice(name="create", value="create"),
    app_commands.Choice(name="send", value="send"),
    app_commands.Choice(name="edit", value="edit"),
    app_commands.Choice(name="delete", value="delete"),
    app_commands.Choice(name="list", value="list"),
])
@app_commands.autocomplete(
    name=user_webhook_name_autocomplete,
    avatar_choice=webhook_avatar_autocomplete
)
async def webhook(
    interaction: discord.Interaction,
    action: str,
    name: Optional[str] = None,
    channel: Optional[discord.TextChannel] = None,
    avatar_choice: Optional[str] = None,
    content: Optional[str] = None,
    message_id: Optional[str] = None
):
    # Owner-only check for the entire command
    if interaction.user.id != OWNER_USER_ID:
        await interaction.response.send_message("❌ Unauthorized. This command is for the bot owner only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # --- LIST Action ---
    if action == "list":
        all_webhooks = await get_all_user_webhooks()
        if not all_webhooks:
            await interaction.followup.send("No custom webhooks have been created yet.", ephemeral=True)
            return
            
        embed = discord.Embed(title="Custom Webhooks", color=NERDY_YELLOW)
        desc_parts = []
        for wh in all_webhooks:
            channel_obj = guild.get_channel(wh['channel_id'])
            channel_mention = channel_obj.mention if channel_obj else f"Unknown Channel (ID: {wh['channel_id']})"
            desc_parts.append(f"**Name:** `{wh['name']}`\n**Channel:** {channel_mention}\n")
        
        embed.description = "\n".join(desc_parts)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    # --- Parameter Validation for other actions ---
    if not name:
        await interaction.followup.send("❌ The `name` parameter is required for this action.", ephemeral=True)
        return

    # --- CREATE Action ---
    if action == "create":
        if not channel or not avatar_choice:
            await interaction.followup.send("❌ The `channel` and `avatar_choice` parameters are required to create a webhook.", ephemeral=True)
            return

        purpose = f"user_webhook_{name}"
        if await get_user_webhook_url(name):
            await interaction.followup.send(f"❌ A webhook with the name `{name}` already exists.", ephemeral=True)
            return

        if not channel.permissions_for(guild.me).manage_webhooks:
            await interaction.followup.send(f"❌ I need `Manage Webhooks` permission in {channel.mention}.", ephemeral=True)
            return

        avatar_bytes: Optional[bytes] = None
        try:
            source_type, value = avatar_choice.split(":", 1)
            
            if source_type == "member":
                member_id = int(value)
                member = await guild.fetch_member(member_id)
                avatar_url = member.display_avatar.url if member.display_avatar else member.default_avatar.url
                async with aiohttp.ClientSession() as session:
                    avatar_bytes = await fetch_avatar_bytes(session, avatar_url)
            
            elif source_type == "image":
                folder_id, filename = value.split(":", 1)
                image_path = os.path.join(PROFILE_PIC_BASE_PATH, folder_id, filename)
                if os.path.exists(image_path):
                    with open(image_path, "rb") as f:
                        avatar_bytes = f.read()
                else:
                    await interaction.followup.send(f"❌ Could not find image file: `{filename}`", ephemeral=True)
                    return
        except Exception as e:
            await log_error(guild, f"Error processing avatar choice for webhook creation", error=e, interaction=interaction)
            await interaction.followup.send("❌ Error processing avatar choice.", ephemeral=True)
            return

        try:
            new_webhook = await channel.create_webhook(name=name, avatar=avatar_bytes, reason=f"Custom webhook by owner")
            await run_supabase_sync(
                lambda: supabase.table("webhooks").insert({
                    "discord_guild_id": guild.id, "channel_id": channel.id,
                    "purpose": purpose, "webhook_url": new_webhook.url
                }).execute()
            )
            await interaction.followup.send(f"✅ Successfully created webhook `{name}` in {channel.mention}.", ephemeral=True)
        except Exception as e:
            await log_error(guild, f"Error creating custom webhook '{name}'", error=e, interaction=interaction)
            await interaction.followup.send("❌ An error occurred while creating the webhook.", ephemeral=True)
        return

    # --- SEND Action ---
    elif action == "send":
        if not content:
            await interaction.followup.send("❌ The `content` parameter is required to send a message.", ephemeral=True)
            return
        
        processed_content, mention_error = await block_unwanted_mentions(content, interaction.user.id)
        if mention_error:
            await interaction.followup.send(f"❌ {mention_error}", ephemeral=True)
            return
        
        webhook_url = await get_user_webhook_url(name)
        if not webhook_url:
            await interaction.followup.send(f"❌ Could not find a webhook named `{name}`.", ephemeral=True)
            return

        try:
            webhook = discord.Webhook.from_url(webhook_url, session=bot.http_session)
            sent_message = await webhook.send(processed_content, wait=True)
            await interaction.followup.send(f"✅ Message sent via webhook `{name}`.\n**Message ID:** `{sent_message.id}`", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send(f"❌ Webhook `{name}` not found on Discord. It may have been deleted.", ephemeral=True)
        except Exception as e:
            await log_error(guild, f"Error sending message with webhook '{name}'", error=e, interaction=interaction)
            await interaction.followup.send("❌ An error occurred while sending the message.", ephemeral=True)
        return

    # --- EDIT Action ---
    elif action == "edit":
        if not message_id or not content:
            await interaction.followup.send("❌ `message_id` and `content` are required to edit a message.", ephemeral=True)
            return

        processed_content, mention_error = await block_unwanted_mentions(content, interaction.user.id)
        if mention_error:
            await interaction.followup.send(f"❌ {mention_error}", ephemeral=True)
            return

        webhook_url = await get_user_webhook_url(name)
        if not webhook_url:
            await interaction.followup.send(f"❌ Could not find a webhook named `{name}`.", ephemeral=True)
            return

        try:
            webhook = discord.Webhook.from_url(webhook_url, session=bot.http_session)
            await webhook.edit_message(message_id, content=processed_content)
            await interaction.followup.send(f"✅ Message `{message_id}` successfully edited.", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send(f"❌ Could not find a message with ID `{message_id}` to edit.", ephemeral=True)
        except Exception as e:
            await log_error(guild, f"Error editing message '{message_id}'", error=e, interaction=interaction)
            await interaction.followup.send("❌ An error occurred while editing the message.", ephemeral=True)
        return

    # --- DELETE Action ---
    elif action == "delete":
        purpose = f"user_webhook_{name}"
        webhook_url = await get_user_webhook_url(name)

        if webhook_url:
            try:
                webhook = discord.Webhook.from_url(webhook_url, session=bot.http_session)
                await webhook.delete()
            except discord.NotFound: pass
            except Exception as e: await log_error(guild, f"Could not delete webhook '{name}' from Discord, but proceeding.", error=e)

        try:
            await run_supabase_sync(lambda: supabase.table("webhooks").delete().eq("purpose", purpose).execute())
            await interaction.followup.send(f"✅ Webhook `{name}` has been deleted.", ephemeral=True)
        except Exception as e:
            await log_error(guild, f"Error deleting webhook '{name}' from database", error=e, interaction=interaction)
            await interaction.followup.send(f"❌ Error removing webhook from DB.", ephemeral=True)
        return

@tree.command(name="setup_guild", description="[Admin] Manage this server's tracked Florr guilds.")
@app_commands.check(check_is_admin)
@app_commands.describe(
    action="The action to perform.",
    tag="The guild tag (e.g., [HC1]). Required for add, edit, and remove.",
    role="The role for the guild. Required for 'add', optional for 'edit'.",
    channel="The list channel for the guild. Required for 'add', optional for 'edit'."
)
@app_commands.choices(action=[
    app_commands.Choice(name="List Tracked Guilds", value="list"),
    app_commands.Choice(name="Add a Tracked Guild", value="add"),
    app_commands.Choice(name="Edit a Tracked Guild", value="edit"),
    app_commands.Choice(name="Remove a Tracked Guild", value="remove"),
])
@app_commands.autocomplete(tag=tracked_guild_tag_autocomplete)
async def setup_guild(
    interaction: discord.Interaction,
    action: str,
    tag: Optional[str] = None,
    role: Optional[discord.Role] = None,
    channel: Optional[discord.TextChannel] = None
):
    guild = interaction.guild
    if not guild: return

    await interaction.response.defer(ephemeral=True)

    # --- LIST Action ---
    if action == "list":
        config = await load_server_config(guild.id)
        tracked_guilds = config.get('tracked_guilds', {})

        if not tracked_guilds:
            await interaction.followup.send("There are no Florr guilds currently being tracked in this server.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Tracked Florr Guilds for {guild.name}", color=NERDY_YELLOW)
        for t, data in sorted(tracked_guilds.items()):
            role_obj = guild.get_role(data.get('discord_role_id')) if data.get('discord_role_id') else None
            channel_obj = guild.get_channel(data.get('member_list_channel_id')) if data.get('member_list_channel_id') else None
            value = (
                f"**Discord Role:** {role_obj.mention if role_obj else '`Not Set`'}\n"
                f"**Member List Channel:** {channel_obj.mention if channel_obj else '`Not Set`'}"
            )
            embed.add_field(name=f"Guild Tag: `{t}`", value=value, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    # --- Parameter Validation for other actions ---
    if not tag:
        await interaction.followup.send("❌ The `tag` parameter is required for this action.", ephemeral=True)
        return

    normalized_tag = _normalize_guild_tag(tag)
    config = await load_server_config(guild.id)
    existing_guild_data = config.get('tracked_guilds', {}).get(normalized_tag)

    # --- ADD Action ---
    if action == "add":
        if not role or not channel:
            await interaction.followup.send("❌ The `role` and `channel` parameters are required to add a guild.", ephemeral=True)
            return
        if existing_guild_data:
            await interaction.followup.send(f"❌ The guild `{normalized_tag}` is already tracked. Use `/setup_guild action:edit` to modify it.", ephemeral=True)
            return
        
        try:
            await run_supabase_sync(lambda: supabase.table("tracked_florr_guilds").insert({
                "discord_guild_id": guild.id,
                "florr_guild_tag": normalized_tag,
                "discord_role_id": role.id,
                "member_list_channel_id": channel.id
            }).execute())
            await load_server_config(guild.id) # Refresh cache
            await interaction.followup.send(f"✅ Successfully added `{normalized_tag}` to the tracked guilds list.", ephemeral=True)
            await log_info(guild, f"{interaction.user.name} added tracked guild '{normalized_tag}' via /setup_guild.")
        except Exception as e:
            await log_error(guild, f"Failed to add tracked guild {normalized_tag}", error=e, interaction=interaction)
            await interaction.followup.send("❌ A database error occurred while adding the guild.", ephemeral=True)

    # --- EDIT Action ---
    elif action == "edit":
        if not role and not channel:
            await interaction.followup.send("❌ You must provide a new `role` or a new `channel` to edit.", ephemeral=True)
            return
        if not existing_guild_data:
            await interaction.followup.send(f"❌ The guild `{normalized_tag}` is not currently being tracked.", ephemeral=True)
            return
            
        updates = {}
        if role: updates['discord_role_id'] = role.id
        if channel: updates['member_list_channel_id'] = channel.id
        
        try:
            await run_supabase_sync(lambda: supabase.table("tracked_florr_guilds").update(updates).eq("discord_guild_id", guild.id).eq("florr_guild_tag", normalized_tag).execute())
            await load_server_config(guild.id) # Refresh cache
            await interaction.followup.send(f"✅ Successfully edited `{normalized_tag}`.", ephemeral=True)
            await log_info(guild, f"{interaction.user.name} edited tracked guild '{normalized_tag}' via /setup_guild.")
        except Exception as e:
            await log_error(guild, f"Failed to edit tracked guild {normalized_tag}", error=e, interaction=interaction)
            await interaction.followup.send("❌ A database error occurred while editing the guild.", ephemeral=True)

    # --- REMOVE Action ---
    elif action == "remove":
        if not existing_guild_data:
            await interaction.followup.send(f"❌ The guild `{normalized_tag}` is not currently being tracked.", ephemeral=True)
            return
            
        try:
            await run_supabase_sync(lambda: supabase.table("tracked_florr_guilds").delete().eq("discord_guild_id", guild.id).eq("florr_guild_tag", normalized_tag).execute())
            await load_server_config(guild.id) # Refresh cache
            await interaction.followup.send(f"✅ Successfully removed `{normalized_tag}` from the tracked guilds list.", ephemeral=True)
            await log_info(guild, f"{interaction.user.name} removed tracked guild '{normalized_tag}' via /setup_guild.")
        except Exception as e:
            await log_error(guild, f"Failed to remove tracked guild {normalized_tag}", error=e, interaction=interaction)
            await interaction.followup.send("❌ A database error occurred while removing the guild.", ephemeral=True)

@tree.command(name="help", description="Shows a pointer to the main help command.")
async def help_command(interaction: discord.Interaction):
    if not bot.user:
        await interaction.response.send_message("Bot is not ready, please try again.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Help Information",
        description=f"Please use the {get_cmd_mention('nerdhelp')} command for a full list of features.",
        color=NERDY_YELLOW
    )
    if bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=False)

# --- Bot Startup ---
if __name__ == "__main__":
    print("--- Initializing FlorrNerd Bot ---")
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