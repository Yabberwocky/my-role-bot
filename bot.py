# -*- coding: utf-8 -*-
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
#   - Environment Variables: DISCORD_BOT_MAIN_TOKEN, SUPABASE_URL, SUPABASE_ADMIN_KEY are set directly in Render's environment settings.
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
MAIN_TOKEN = os.getenv("MAIN_DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ADMIN_KEY = os.getenv("SUPABASE_ADMIN_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
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
KEYWORD_TABLE_NAME = "keyword_phrases" # Supabase table name
keyword_data_cache: Dict[str, Any] = {} # id (str) -> KeywordRule details
total_keywords = 0
discovered_keywords_count = 0
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


AI_PROMPTS = {
    "HUMAN_SYSTEM_INSTRUCTION": (
        "You are a chat participant in a Discord server. Mimic human typing style: use lowercase, avoid excessive punctuation (especially ending periods/exclamation marks), "
        "keep messages relatively short and conversational. Engage naturally with the ongoing discussion based on the provided history and the user's last message. "
        "Your goal is to blend in."
    ),
    "FLORR_IMAGE_NAME_EXTRACTION": """Analyze the provided image(s), which are screenshots from the game Florr.io, potentially showing a guild member list.
Your task is to identify and extract In-Game Names (IGNs) of players who appear to be ONLINE or CURRENTLY ACTIVE within a guild member list context.

Known Valid In-Game Names (use this as your reference):
--- BEGIN KNOWN NAMES LIST ---
{known_igns_list_str}
--- END KNOWN NAMES LIST ---

**Instructions for Guild Member Lists (if present in the image):**
- Focus on identifying players who are displayed in a way that suggests they are currently online or active in the guild. Games often distinguish online members from offline ones in these lists (e.g., brighter names, different icons, or placement).
- Use your general knowledge of game UIs to infer this online/active status from the visual presentation in the guild list.
- If a name is visible in a guild list but appears to be offline or inactive, DO NOT extract it.
- If the image is definitively NOT a guild member list (e.g., general gameplay, chat messages without a structured list), you may identify any names from the "Known Valid In-Game Names" list if they are clearly visible. Prioritize guild list rules if a guild list is clearly present.

General Output Instructions:
1. List each clearly identifiable player name that meets ALL criteria above on a NEW LINE.
2. These names must, as accurately as possible, match one of the names from the "Known Valid In-Game Names" list provided.
3. If a name from the list appears to be partially visible or has minor OCR inaccuracies but you are confident it's a match to a name in the provided list AND meets the online/active criteria for guild lists, output the name *from the list*.
4. Output ONLY the names. Do NOT include any other text, commentary, numbering, or formatting.
5. If the same name (meeting all criteria) appears multiple times, list it only once in the final output.
6. If, after applying all rules, no player names (from the provided list, meeting all criteria including appearing online/active in guild lists) are clearly identifiable in any of the image(s), output the exact phrase: NO_NAMES_FOUND

Example of expected output if "PlayerName1" and "PlayerName2" (both appearing online in a guild list) were in the known list and found:
PlayerName1
PlayerName2
""",
    "KEYWORD_DISCOVERY_SYSTEM_INSTRUCTION": (
        "You are a helpful and slightly playful bot. A user just made the FIRST EVER discovery of your secret keyword phrase '{phrase_identifier}'.\n"
        "1. Start by warmly and enthusiastically congratulating {user_display_name} on this unique discovery!\n"
        "2. Then, seamlessly transition into a creative, human-like response related to their triggering message, keeping in mind the keyword's theme.\n"
        "   - Keyword Theme/Speciality: {speciality}\n"
        "   - Specific Instructions: {instructions}\n"
        "Keep the entire response concise and conversational, like a human. Do not refer to yourself in the third person."
    ),
    "KEYWORD_TRIGGER_SYSTEM_INSTRUCTION": (
        "{human_system_instruction}\n\n" # This will be formatted with the actual human system instruction
        "CONTEXT: Respond to a user message that triggered the keyword '{phrase_identifier}'.\n"
        "SPECIALITY: {speciality}\n"
        "INSTRUCTIONS: {instructions}\n"
        "Focus on the user's triggering message, using history for context. Do not refer to yourself in third person."
    ),
    "BOT_PURPOSE_GENERAL": "I'm TheNerd's Pingslave, here to help manage verification and guild info for [HC1] in Florr.io on Catercord. I also have some fun AI features and can provide info on various topics if you ask!",
    "HCVERIFY_COMMAND_EXPLANATION": (
        "The `/hcverify` command is a staff tool used to formally verify a member into the [HC1] Florr.io guild. "
        "When used, it links the member's Discord account to their specified in-game name (IGN) in our database. "
        "This also usually involves assigning them the HC role, removing any 'Unverified' roles, and setting their server nickname to their IGN. "
        "It's a key step for new HC members!"
    ),
    "FLORR_IO_GAME_INFO_BRIEF": (
        "Florr.io is a dynamic multiplayer browser game where you control a flower. "
        "The main goal is to survive and thrive by collecting petals dropped by mobs and other players. "
        "These petals are used to upgrade your flower, making you stronger and unlocking new abilities. "
        "It's all about skillful maneuvering, strategic upgrades, and intense PvP action!"
    ),
    "CATERCORD_SERVER_INFO": (
        "Catercord is the primary Discord server where I, Pingslave, am most active. It's the central hub for the [HC1] Florr.io guild. "
        "In Catercord, members share game tips, organize group activities, discuss strategies, and stay updated on all guild-related matters. "
        "I help out by managing member verifications, tracking activity, and providing useful information. "
        "It's the place to be if you're part of [HC1] or interested in joining!"
    ),
    "PRIVATE_SERVER_INFO": (
        "The private server (ID: {PRIVATE_SERVER_ID}) is a special environment primarily used by my owner, TheNerd (sweet_honey), for testing, development, and sometimes for specific administrative tasks. "
        "My behavior and command availability might be different there as it's often a sandbox for new features before they are rolled out more broadly."
    ),
    "RANDOM_SERVER_INFO": ( # Make sure RANDOM_SERVER_ID is available here, or pass it via kwargs
        "The server you're asking about (ID: {RANDOM_SERVER_ID}) has a unique setup for me. "
        "Notably, the `/wither` command has special logic there, potentially involving a unique 'Withered' role. "
        "Access to commands like `/wither` in that server is typically restricted to whitelisted users or server administrators."
    ),
    # Add more prompts as needed, following the user's list of ~20 topics.
    # Example:
    "BOT_COMMANDS_GENERAL_OVERVIEW": "I have a range of commands! Use `/nerdhelp` to see a list. Some are for guild management like `/hcverify`, others for fun like `/florr` to send messages with custom avatars, and AI interactions through keywords or direct pings.",
    "SUPABASE_DATABASE_INFO": "I use a Supabase (PostgreSQL) database to store important information, like the in-game names of [HC1] members and their linked Discord IDs, as well as activity logs and keyword configurations.",
    "RENDER_HOSTING_INFO": "I'm hosted on Render's free tier. To keep me awake, a simple Flask web server runs in the background, and an external service pings it regularly.",
    "AI_FEATURES_OVERVIEW": "I can respond to secret keywords, chat with you in designated channels or when you reply to me, and even help generate messages for some commands! My AI capabilities are powered by Google's Gemini models.",
}

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

# --- Google Gemini AI Client ---
ai_model_2_5_flash = None
ai_model_2_0_flash = None
ai_model_2_0_flash_lite = None

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        # Import the specific exception for rate limiting
        import google.api_core.exceptions as google_exceptions
        
        genai.configure(api_key=GEMINI_API_KEY)
        print("Attempting to configure Google Gemini AI clients...")

        try:
            ai_model_2_5_flash = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
            print("  Successfully configured Highest Gemini model.")
        except Exception as e_highest:
            print(f"  WARNING: Failed to configure Highest Gemini model: {e_highest}. This model will be unavailable.")
            ai_model_2_5_flash = None

        try:
            ai_model_2_0_flash = genai.GenerativeModel('gemini-2.0-flash') # Changed from 'gemini-2.0-flash'
            print("  Successfully configured Standard Gemini model.")
        except Exception as e_standard:
            print(f"  WARNING: Failed to configure Standard Gemini model: {e_standard}. This model will be unavailable.")
            ai_model_2_0_flash = None
            
        try:
            ai_model_2_0_flash_lite = genai.GenerativeModel('gemini-2.0-flash-lite')
            print("  Successfully configured Lite Gemini model.")
        except Exception as e_lite:
            print(f"  WARNING: Failed to configure Lite Gemini model: {e_lite}. This model will be unavailable.")
            ai_model_2_0_flash_lite = None

        if not ai_model_2_5_flash and not ai_model_2_0_flash and not ai_model_2_0_flash_lite:
            print("CRITICAL: All Google Gemini AI models failed to initialize. AI features will be disabled.")
        else:
            print("Google Gemini AI client configuration finished.")

    except ImportError:
        print("WARNING: 'google-generativeai' or 'google-api-core' library not found. AI features disabled. Run 'pip install google-generativeai google-api-core'")
        ai_model_2_5_flash = ai_model_2_0_flash = ai_model_2_0_flash_lite = None
    except Exception as e:
        print(f"CRITICAL: Failed initial Google Gemini configuration step: {e}")
        ai_model_2_5_flash = ai_model_2_0_flash = ai_model_2_0_flash_lite = None
else:
    print("INFO: GEMINI_API_KEY not found in environment variables. AI features disabled.")
    ai_model_2_5_flash = ai_model_2_0_flash = ai_model_2_0_flash_lite = None

# --- Utility Functions ---

def get_prompt(prompt_key: str, **kwargs) -> Optional[str]:
    """Retrieves and formats a prompt string from the AI_PROMPTS dictionary."""
    raw_prompt = AI_PROMPTS.get(prompt_key)
    if raw_prompt:
        try:
            # Add global constants to kwargs automatically if they are in the prompt
            # and not already provided by the caller. This makes it easier to use
            # constants like PRIVATE_SERVER_ID in prompts without passing them every time.
            # Be cautious with this if prompt keys might collide with global var names.
            # For specific known ones:
            if '{PRIVATE_SERVER_ID}' in raw_prompt and 'PRIVATE_SERVER_ID' not in kwargs:
                kwargs['PRIVATE_SERVER_ID'] = PRIVATE_SERVER_ID
            if '{RANDOM_SERVER_ID}' in raw_prompt and 'RANDOM_SERVER_ID' not in kwargs:
                kwargs['RANDOM_SERVER_ID'] = RANDOM_SERVER_ID

            return raw_prompt.format(**kwargs)
        except KeyError as e:
            print(f"Prompt Error: Missing key '{e}' for prompt '{prompt_key}' with args {kwargs}")
            # Fallback to raw prompt or handle error as preferred
            return raw_prompt # Or return None / raise error
        except Exception as format_e:
            print(f"Prompt Error: General formatting error for prompt '{prompt_key}': {format_e}")
            return raw_prompt
    print(f"Prompt Error: Prompt key '{prompt_key}' not found.")
    return None

# Helper to get the list of available models in order of preference
def get_ai_model_priority_list():
    models = []
    if ai_model_2_5_flash: # Highest
        models.append({'instance': ai_model_2_5_flash, 'name': 'Gemini 2.5 Flash (Preview)', 'id': 'gemini_2_5_flash'})
    if ai_model_2_0_flash: # Standard
        models.append({'instance': ai_model_2_0_flash, 'name': 'Gemini 2.0 Flash', 'id': 'gemini_2_0_flash'})
    if ai_model_2_0_flash_lite: # Lite
        models.append({'instance': ai_model_2_0_flash_lite, 'name': 'Gemini 2.0 Flash Lite', 'id': 'gemini_2_0_flash_lite'})
    return models

async def send_ai_chat_response(
    trigger_type: str,
    history: List[discord.Message],
    prompt_key_for_ai: Optional[str] = None,
    prompt_kwargs_for_ai: Optional[Dict[str, Any]] = None,
    system_instruction_key: Optional[str] = None,
    system_instruction_kwargs: Optional[Dict[str, Any]] = None,
    discovery_congrats_user: Optional[discord.User] = None,
    keyword_triggered_rule_data: Optional[Dict[str, Any]] = None,
    user_message_content: Optional[str] = None, # Raw content of the user's message
    interaction_for_command_reply: Optional[discord.Interaction] = None # For replying to commands
):
    if not get_ai_model_priority_list():
        print("AI Send Error: No AI models available/configured.")
        if interaction_for_command_reply:
            try:
                if interaction_for_command_reply.response.is_done():
                    await interaction_for_command_reply.followup.send("AI is currently unavailable.", ephemeral=True)
                else:
                    await interaction_for_command_reply.response.send_message("AI is currently unavailable.", ephemeral=True)
            except Exception: pass
        return

    channel_to_send_in: Optional[discord.abc.Messageable] = None
    guild_for_log: Optional[discord.Guild] = None
    message_to_reply_to: Optional[discord.Message] = None

    if interaction_for_command_reply: # Command trigger
        channel_to_send_in = interaction_for_command_reply.channel
        guild_for_log = interaction_for_command_reply.guild
        # For commands, we don't reply to a message in history, we reply to the interaction
    elif history: # Chat-based triggers
        triggering_message_context = history[-1]
        channel_to_send_in = triggering_message_context.channel
        guild_for_log = triggering_message_context.guild
        if trigger_type not in ["AlwaysOn"]:
            message_to_reply_to = triggering_message_context
    else:
        print(f"AI Error (send_ai_chat_response): History empty and no interaction provided for trigger '{trigger_type}'. Cannot determine channel.")
        return

    if not channel_to_send_in:
        print(f"AI Error (send_ai_chat_response): Could not determine channel for trigger '{trigger_type}'.")
        return

    preferred_model_id_for_call: Optional[str] = None
    final_system_instruction_str: Optional[str] = None
    actual_prompt_for_ai: Optional[str] = None

    # Determine model and system instructions
    if trigger_type == "AlwaysOn":
        preferred_model_id_for_call = 'gemini_2_0_flash'
        sys_instruct_key = system_instruction_key or "HUMAN_SYSTEM_INSTRUCTION"
        final_system_instruction_str = get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
        actual_prompt_for_ai = user_message_content or "(responded to chat flow)"
        if prompt_key_for_ai:
             actual_prompt_for_ai = get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {})) or actual_prompt_for_ai

    elif trigger_type == "Discovery" and keyword_triggered_rule_data and discovery_congrats_user:
        preferred_model_id_for_call = 'gemini_2_5_flash'
        sys_instruct_key = "KEYWORD_DISCOVERY_SYSTEM_INSTRUCTION"
        final_system_instruction_str = get_prompt(
            sys_instruct_key,
            phrase_identifier=keyword_triggered_rule_data['phrase_identifier'],
            user_display_name=discovery_congrats_user.display_name.lower(),
            speciality=keyword_triggered_rule_data.get('speciality', 'General'),
            instructions=keyword_triggered_rule_data.get('instructions', 'Respond naturally.')
        )
        actual_prompt_for_ai = f"user message: '{user_message_content}' (triggered first discovery of keyword: '{keyword_triggered_rule_data['phrase_identifier']}')"

    elif trigger_type == "Keyword" and keyword_triggered_rule_data:
        preferred_model_id_for_call = 'gemini_2_5_flash'
        sys_instruct_key = "KEYWORD_TRIGGER_SYSTEM_INSTRUCTION"
        human_sys_instruct = get_prompt("HUMAN_SYSTEM_INSTRUCTION")
        final_system_instruction_str = get_prompt(
            sys_instruct_key,
            human_system_instruction=human_sys_instruct,
            phrase_identifier=keyword_triggered_rule_data['phrase_identifier'],
            speciality=keyword_triggered_rule_data.get('speciality', 'General'),
            instructions=keyword_triggered_rule_data.get('instructions', 'Respond naturally.')
        )
        actual_prompt_for_ai = f"keyword '{keyword_triggered_rule_data['phrase_identifier']}' triggered by message: '{user_message_content}'"
    
    elif trigger_type in ["Reply", "Mention"]:
        preferred_model_id_for_call = 'gemini_2_5_flash'
        sys_instruct_key = system_instruction_key or "HUMAN_SYSTEM_INSTRUCTION"
        final_system_instruction_str = get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
        actual_prompt_for_ai = user_message_content or "(general interaction)"
        if prompt_key_for_ai:
            actual_prompt_for_ai = get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {})) or actual_prompt_for_ai

    elif trigger_type.startswith("COMMAND_"): # For AI responses triggered by commands
        preferred_model_id_for_call = 'gemini_2_5_flash' # Default high quality for direct command output
        # System instruction typically from prompt_key_for_ai or a general bot persona
        sys_instruct_key = system_instruction_key or "BOT_PURPOSE_GENERAL" # Default, can be overridden by command
        final_system_instruction_str = get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
        # The main prompt comes from prompt_key_for_ai
        if not prompt_key_for_ai:
            print(f"AI Send Error: No prompt_key_for_ai provided for COMMAND trigger '{trigger_type}'.")
            if interaction_for_command_reply: await interaction_for_command_reply.followup.send("Error: AI prompt missing.", ephemeral=True)
            return
        actual_prompt_for_ai = get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {}))
        if not actual_prompt_for_ai:
            print(f"AI Send Error: Could not load prompt for key '{prompt_key_for_ai}' for trigger '{trigger_type}'.")
            if interaction_for_command_reply: await interaction_for_command_reply.followup.send("Error: AI prompt could not be loaded.", ephemeral=True)
            return
    else: # Fallback for other or undefined trigger types
        preferred_model_id_for_call = 'gemini_2_0_flash' # Default to standard
        sys_instruct_key = system_instruction_key or "HUMAN_SYSTEM_INSTRUCTION"
        final_system_instruction_str = get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
        actual_prompt_for_ai = user_message_content or "(general query)"
        if prompt_key_for_ai:
            actual_prompt_for_ai = get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {})) or actual_prompt_for_ai

    if not actual_prompt_for_ai:
        log_msg_content = f"AI Send Error: Prompt for AI was empty for trigger '{trigger_type}'."
        if history and history[-1]: log_msg_content += f" Msg: {history[-1].id}"
        elif interaction_for_command_reply: log_msg_content += f" Interaction: {interaction_for_command_reply.id}"
        await log_error(guild_for_log, log_msg_content)
        if interaction_for_command_reply: await interaction_for_command_reply.followup.send("Error: AI prompt was empty.", ephemeral=True)
        return

    ai_response_processed = None
    try:
        # Typing indicator for chat-based, commands handle their own "thinking" state
        typing_context = contextlib.nullcontext()
        if isinstance(channel_to_send_in, discord.TextChannel) and not interaction_for_command_reply:
            typing_context = channel_to_send_in.typing()

        async with typing_context:
            ai_response_raw = await get_ai_response(
                prompt=actual_prompt_for_ai,
                history=history if not interaction_for_command_reply else None, # Commands might not need chat history
                system_instruction=final_system_instruction_str,
                preferred_model_id=preferred_model_id_for_call
            )

        if not ai_response_raw:
            log_msg_content = f"AI for '{trigger_type}' (prompt key: {prompt_key_for_ai or 'N/A'}) returned None/empty."
            if history and history[-1]: log_msg_content += f" Msg: {history[-1].id}"
            elif interaction_for_command_reply: log_msg_content += f" Interaction: {interaction_for_command_reply.id}"
            await log_info(guild_for_log, log_msg_content)
            fail_msg = "... (couldn't think of a response right now)"
            
            if interaction_for_command_reply: await interaction_for_command_reply.followup.send(fail_msg, ephemeral=True)
            elif trigger_type == "AlwaysOn": await channel_to_send_in.send(fail_msg)
            elif message_to_reply_to: await message_to_reply_to.reply(fail_msg, mention_author=False)
            return

        ai_response_processed = ai_response_raw.strip()
        if ai_response_processed.endswith(('.', '!', '?')):
            ai_response_processed = ai_response_processed[:-1]
        
        bot_name_prefix_lower = "thenerd's pingslave:" # Assuming this is your bot's name
        if bot.user and bot.user.name: # Use actual bot name if available
            bot_name_prefix_lower = f"{bot.user.name.lower()}:"

        if ai_response_processed.lower().startswith(bot_name_prefix_lower):
            ai_response_processed = ai_response_processed[len(bot_name_prefix_lower):].lstrip()

        if len(ai_response_processed) > 1950: # Discord message limit is 2000
             ai_response_processed = ai_response_processed[:1947] + "..."

    except Exception as ai_call_err:
        log_msg_content = f"Error during get_ai_response for '{trigger_type}' (prompt key: {prompt_key_for_ai or 'N/A'})"
        if history and history[-1]: log_msg_content += f" Msg: {history[-1].id}"
        elif interaction_for_command_reply: log_msg_content += f" Interaction: {interaction_for_command_reply.id}"
        await log_error(guild_for_log, log_msg_content, error=ai_call_err)
        fail_msg = "... (ran into a snag trying to respond)"
        
        if interaction_for_command_reply: await interaction_for_command_reply.followup.send(fail_msg, ephemeral=True)
        elif trigger_type == "AlwaysOn": await channel_to_send_in.send(fail_msg)
        elif message_to_reply_to: await message_to_reply_to.reply(fail_msg, mention_author=False)
        return

    if ai_response_processed:
        final_message_content_to_send = ""
        if trigger_type == "Discovery" and discovery_congrats_user and keyword_triggered_rule_data:
            final_message_content_to_send = (
                f"# 🎉 \n woohoo, {discovery_congrats_user.mention}! you're the first to find the secret phrase: **'{discord.utils.escape_markdown(keyword_triggered_rule_data['phrase_identifier'])}'**! 🎉\n\n"
                f"{ai_response_processed}"
            )
        else:
            final_message_content_to_send = ai_response_processed
        
        if trigger_type == "Keyword" and keyword_triggered_rule_data:
            final_message_content_to_send += f"\n*(You triggered the keyword: `{discord.utils.escape_markdown(keyword_triggered_rule_data['phrase_identifier'])}`)*"

        try:
            if interaction_for_command_reply:
                # For commands, send as a followup to the (likely deferred) interaction
                # Ensure interaction is not already responded to in a final way if not deferred.
                if interaction_for_command_reply.response.is_done():
                    await interaction_for_command_reply.followup.send(final_message_content_to_send, ephemeral=trigger_type.endswith("_EPHEMERAL")) # Example for ephemeral flag
                else: # Should have been deferred
                    await interaction_for_command_reply.response.send_message(final_message_content_to_send, ephemeral=trigger_type.endswith("_EPHEMERAL"))
            elif trigger_type == "AlwaysOn":
                 await channel_to_send_in.send(final_message_content_to_send)
            elif message_to_reply_to:
                 mention_author_flag = trigger_type in ["Reply", "Keyword", "Discovery"]
                 await message_to_reply_to.reply(final_message_content_to_send, mention_author=mention_author_flag)
            else:
                 await channel_to_send_in.send(final_message_content_to_send)
                 log_msg_content = f"AI response for '{trigger_type}' sent to channel directly as message_to_reply_to was None"
                 if history and history[-1]: log_msg_content += f" (Msg ID: {history[-1].id})."
                 await log_info(guild_for_log, log_msg_content)

        except (discord.Forbidden, discord.HTTPException) as reply_err:
            log_msg_content = f"Failed to send processed AI '{trigger_type}' response"
            if history and history[-1]: log_msg_content += f" for msg {history[-1].id}"
            elif interaction_for_command_reply: log_msg_content += f" for interaction {interaction_for_command_reply.id}"
            await log_error(guild_for_log, log_msg_content, error=reply_err)

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
        embed.add_field(name="\u200B\n🕵️ Secret Phrase Discovery", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('discoveries')} · Show secret phrase discovery progress.", value="\u200B", inline=False)
        embed.add_field(name="\u200B\n💬 Messaging", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('message')} · Send a message as the bot (opt. AI).", value="\u200B", inline=False)
        embed.add_field(name=f"{get_cmd_mention('florr')} · Send msg with custom name & Florr pic.", value="\u200B", inline=False)
        embed.add_field(name="\u200B\n⚙️ Other", value="\u200B", inline=False)
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
    """Loads all In-Game Names from Supabase into an in-memory cache."""
    global ingame_name_cache
    if not supabase:
        await log_error(guild_for_log, "IGN Cache loading failed: Supabase unavailable.", ping_owner=True)
        ingame_name_cache = [] # Ensure it's empty on failure
        return

    print("Loading IGN cache from Supabase...")
    try:
        # Fetch all non-null ingame_name entries
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("ingame_name")
                           .not_.is_("ingame_name", "null") # Ensure we only get non-null IGNs
                           .execute()
        )

        if not resp or not hasattr(resp, 'data') or not resp.data:
            await log_info(guild_for_log, "No IGN data found or failed to fetch for cache. IGN cache will be empty.")
            ingame_name_cache = []
            return

        # Extract unique IGNs from the response
        temp_igns = set()
        for entry in resp.data:
            ign = entry.get("ingame_name")
            if ign: # Check if ign is not None and not an empty string
                temp_igns.add(str(ign)) # Convert to string just in case

        ingame_name_cache = sorted(list(temp_igns), key=str.lower) # Store as a sorted list (case-insensitive sort)

        print(f"Loaded {len(ingame_name_cache)} unique In-Game Names into cache.")
        await log_info(guild_for_log, f"Successfully loaded {len(ingame_name_cache)} IGNs into local cache.")

    except (APIError, ConnectionError, Exception) as e:
        await log_error(guild_for_log, "Failed to load IGN cache from Supabase", error=e, ping_owner=True)
        ingame_name_cache = [] # Clear cache on error

async def get_ai_response(
    prompt: str,
    history: Optional[List[discord.Message]] = None,
    system_instruction: Optional[str] = None, # This will be the actual string after get_prompt
    preferred_model_id: Optional[str] = None
) -> Optional[str]:
    all_available_models = get_ai_model_priority_list()
    if not all_available_models:
        print("AI Error (get_ai_response): No AI models available.")
        return None

    models_to_try = []
    if preferred_model_id:
        preferred_model_found = False
        for model_info_iter in all_available_models: # Use a different loop variable name
            if model_info_iter['id'] == preferred_model_id:
                models_to_try.append(model_info_iter)
                preferred_model_found = True
                break
        if preferred_model_found:
            for model_info_iter in all_available_models:
                if model_info_iter['id'] != preferred_model_id:
                    models_to_try.append(model_info_iter)
        else:
            print(f"AI Warning (get_ai_response): Preferred model '{preferred_model_id}' not available. Using default priority.")
            models_to_try = all_available_models
    else:
        models_to_try = all_available_models

    if not models_to_try:
        print("AI Error (get_ai_response): No models to try after filtering for preference.")
        return None

    api_contents = []
    # Use the passed system_instruction string directly
    active_system_instruction_str = system_instruction or get_prompt("HUMAN_SYSTEM_INSTRUCTION")

    if active_system_instruction_str:
        api_contents.append({'role': 'user', 'parts': [{'text': active_system_instruction_str}]})
        api_contents.append({'role': 'model', 'parts': [{'text': 'ok'}]})

    if history:
        for msg in history:
            role = 'model' if msg.author.id == bot.user.id else 'user'
            content_with_author = f"{msg.author.display_name}: {msg.content}" if role == 'user' and bot.user and msg.author.id != bot.user.id else msg.content
            api_contents.append({'role': role, 'parts': [{'text': content_with_author}]})

    api_contents.append({'role': 'user', 'parts': [{'text': prompt}]})

    last_error = None
    guild_for_log = history[-1].guild if history and history[-1].guild else None

    for model_info in models_to_try:
        model_instance = model_info['instance']
        model_name = model_info['name']
        current_model_id = model_info['id']
        try:
            print(f"AI Info (get_ai_response): Attempting generation with {model_name} (ID: {current_model_id}). Preferred: {preferred_model_id or 'None'}")
            response = await model_instance.generate_content_async(
                contents=api_contents,
            )

            if not response.candidates:
                print(f"AI Warning (get_ai_response): Response from {model_name} blocked. Prompt feedback: {response.prompt_feedback.safety_ratings if response.prompt_feedback else 'N/A'}")
                await log_info(guild_for_log, f"AI response from {model_name} (ID: {current_model_id}) blocked (safety filters).")
                last_error = Exception(f"Blocked by safety filters using {model_name}")
                if preferred_model_id and current_model_id == preferred_model_id:
                    await log_error(guild_for_log, f"AI response from PREFERRED model {model_name} (ID: {current_model_id}) was blocked.", error=last_error, ping_owner=False)
                continue

            ai_reply = response.text
            print(f"AI Info (get_ai_response): Successfully generated response with {model_name} (ID: {current_model_id}).")
            return ai_reply

        except google_exceptions.ResourceExhausted as e_rate_limit:
            log_message = f"AI Rate Limit: {model_name} (ID: {current_model_id}) hit a rate limit. Attempting fallback."
            print(log_message)
            # Log to extraordinary if preferred model is rate limited, ordinary otherwise for fallback
            ping_owner_flag = bool(preferred_model_id and current_model_id == preferred_model_id)
            await log_error(guild_for_log, log_message, error=e_rate_limit, ping_owner=ping_owner_flag)
            last_error = e_rate_limit
            continue

        except Exception as e:
            log_message = f"AI Error (get_ai_response): Exception with {model_name} (ID: {current_model_id}) during generation."
            print(f"{log_message} Error: {e}\n{traceback.format_exc()}") # Print traceback for general errors
             # Ping owner if preferred model fails for other reasons, or any model fails critically
            ping_owner_flag = True # Default to pinging, can be refined
            await log_error(guild_for_log, log_message, error=e, ping_owner=ping_owner_flag)
            last_error = e
            continue

    print(f"AI Error (get_ai_response): All AI models failed or were skipped. Last error: {last_error}")
    if isinstance(last_error, google_exceptions.Aborted) and "blocked" in str(last_error).lower():
         return "..."
    return None

async def get_ai_response_with_image(
    prompt_key: str,
    image_bytes: bytes,
    prompt_kwargs: Optional[Dict[str, Any]] = None,
    preferred_model_id: str = 'gemini_2_5_flash' # Default to highest for images
) -> Optional[str]:
    all_available_models = get_ai_model_priority_list()
    if not all_available_models:
        print("AI Error (Image): No AI models available.")
        return None

    models_to_try = []
    if preferred_model_id:
        preferred_model_found = False
        for model_info_iter in all_available_models:
            if model_info_iter['id'] == preferred_model_id:
                models_to_try.append(model_info_iter)
                preferred_model_found = True
                break
        if preferred_model_found:
            for model_info_iter in all_available_models:
                if model_info_iter['id'] != preferred_model_id:
                    models_to_try.append(model_info_iter)
        else:
            print(f"AI Warning (Image): Preferred model '{preferred_model_id}' not available. Using default priority.")
            models_to_try = all_available_models
    else:
        models_to_try = all_available_models
    
    if not models_to_try:
        print("AI Error (Image): No models to try after filtering for preference.")
        return None

    final_prompt = get_prompt(prompt_key, **(prompt_kwargs or {}))
    if not final_prompt:
        print(f"AI Error (Image): Could not retrieve prompt for key '{prompt_key}'.")
        return None

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e_img_open:
        print(f"AI Error (Image): Could not open image bytes: {e_img_open}")
        await log_error(None, "Error opening image for AI in get_ai_response_with_image", error=e_img_open)
        return None

    last_error = None
    guild_for_log = None

    for model_info in models_to_try:
        model_instance = model_info['instance']
        model_name = model_info['name']
        current_model_id = model_info['id']
        try:
            print(f"AI Info (Image): Attempting generation with {model_name} (ID: {current_model_id}). Preferred: {preferred_model_id}. Prompt Key: {prompt_key}")
            response = await model_instance.generate_content_async(
                [final_prompt, img],
            )

            if not response.candidates:
                print(f"AI Warning (Image): Response from {model_name} blocked. Prompt feedback: {response.prompt_feedback.safety_ratings if response.prompt_feedback else 'N/A'}")
                await log_info(guild_for_log, f"AI image response from {model_name} (ID: {current_model_id}) blocked (safety filters).")
                last_error = Exception(f"Blocked by safety filters using {model_name} for image.")
                if preferred_model_id and current_model_id == preferred_model_id:
                    await log_error(guild_for_log, f"AI image response from PREFERRED model {model_name} (ID: {current_model_id}) was blocked.", error=last_error, ping_owner=False)
                continue

            ai_reply = response.text
            print(f"AI Info (Image): Successfully generated response with {model_name} (ID: {current_model_id}).")
            return ai_reply

        except google_exceptions.ResourceExhausted as e_rate_limit:
            log_message = f"AI Rate Limit (Image): {model_name} (ID: {current_model_id}) hit a rate limit. Attempting fallback."
            print(log_message)
            ping_owner_flag = bool(preferred_model_id and current_model_id == preferred_model_id)
            await log_error(guild_for_log, log_message, error=e_rate_limit, ping_owner=ping_owner_flag)
            last_error = e_rate_limit
            continue

        except Exception as e:
            log_message = f"AI Error (Image): Exception with {model_name} (ID: {current_model_id}) during generation."
            print(f"{log_message} Error: {e}\n{traceback.format_exc()}")
            ping_owner_flag = True
            await log_error(guild_for_log, log_message, error=e, ping_owner=ping_owner_flag)
            last_error = e
            continue
            
    print(f"AI Error (Image): All AI models failed for image processing. Last error: {last_error}")
    if isinstance(last_error, google_exceptions.Aborted) and "blocked" in str(last_error).lower():
         return "..."
    return None
    
async def load_keyword_data(guild_for_log: Optional[discord.Guild]):
    """Loads enabled keyword rules from Supabase into the in-memory cache."""
    global keyword_data_cache, total_keywords, discovered_keywords_count
    if not supabase:
        await log_error(guild_for_log, "Keyword loading failed: Supabase unavailable.", ping_owner=True)
        return

    print("Loading keyword data from Supabase...")
    try:
        # --- MODIFIED SELECT STATEMENT ---
        resp = await run_supabase_sync(
            lambda: supabase.table(KEYWORD_TABLE_NAME)
                           .select("id, phrase_identifier, inclusion_regex, exclusion_regex, speciality, instructions, discovered_by_user_id, discovered_at") # <-- Fetch NEW columns, REMOVED old ones
                           .eq("is_enabled", True)
                           .execute()
        )
        # --- END MODIFICATION ---

        if not resp or not hasattr(resp, 'data'):
            await log_info(guild_for_log, "No keyword data found or failed to fetch.")
            keyword_data_cache = {}
            total_keywords = 0
            discovered_keywords_count = 0
            return

        temp_cache = {}
        temp_discovered_count = 0
        compile_errors = []

        for entry in resp.data:
            entry_id_str = str(entry['id']) # Ensure ID is stored as string key
            incl_regex_str = entry['inclusion_regex']
            excl_regex_str = entry['exclusion_regex']
            incl_compiled = None
            excl_compiled = None

            # Compile Inclusion Regex (No change here)
            try:
                if not incl_regex_str: raise ValueError("Inclusion regex cannot be empty")
                incl_compiled = re.compile(incl_regex_str, re.IGNORECASE)
            except (re.error, ValueError) as e:
                compile_errors.append(f"ID '{entry_id_str}' (Identifier: {entry.get('phrase_identifier', 'N/A')}): Inclusion Regex Error: {e}")
                continue

            # Compile Exclusion Regex (No change here)
            try:
                if excl_regex_str:
                    excl_compiled = re.compile(excl_regex_str, re.IGNORECASE)
            except re.error as e:
                 compile_errors.append(f"ID '{entry_id_str}' (Identifier: {entry.get('phrase_identifier', 'N/A')}): Exclusion Regex Error: {e}")

            # --- MODIFIED CACHE STRUCTURE ---
            # Store compiled data and NEW fields
            temp_cache[entry_id_str] = {
                'id': entry_id_str,
                'phrase_identifier': entry.get('phrase_identifier', f'Rule_{entry_id_str[:8]}'),
                'inclusion_regex': incl_compiled,
                'exclusion_regex': excl_compiled, # Can be None
                'speciality': entry.get('speciality'), # <-- NEW
                'instructions': entry.get('instructions'), # <-- NEW
                'discovered_by': entry.get('discovered_by_user_id'), # String or None
                'discovered_at': date_parse(entry['discovered_at']) if entry.get('discovered_at') else None # Parse timestamp
            }
            # --- END MODIFICATION ---

            if temp_cache[entry_id_str]['discovered_by']:
                temp_discovered_count += 1

        keyword_data_cache = temp_cache
        total_keywords = len(keyword_data_cache)
        discovered_keywords_count = temp_discovered_count

        print(f"Loaded {total_keywords} enabled keyword rules. Discovered: {discovered_keywords_count}.")
        if compile_errors:
            log_message = "Keyword Regex Compilation Errors:\n- " + "\n- ".join(compile_errors)
            print(f"WARNING: {log_message}")
            await log_error(guild_for_log, log_message, ping_owner=False)

    except (APIError, ConnectionError, Exception) as e:
        await log_error(guild_for_log, "Failed to load keyword data from Supabase", error=e, ping_owner=True)
        keyword_data_cache = {}
        total_keywords = 0
        discovered_keywords_count = 0


async def record_discovery_in_db(guild_for_log: Optional[discord.Guild], keyword_id_str: str, user_id: int, discovery_time: datetime.datetime):
    """Updates the Supabase table to record the first discovery."""
    if not supabase:
        await log_error(guild_for_log, f"Discovery recording failed for {keyword_id_str}: Supabase unavailable.", ping_owner=True)
        return False # Indicate failure

    print(f"Recording discovery for keyword ID {keyword_id_str} by user {user_id}...")
    try:
        await run_supabase_sync(
            lambda: supabase.table(KEYWORD_TABLE_NAME)
                           .update({
                               'discovered_by_user_id': str(user_id),
                               'discovered_at': discovery_time.isoformat() # Use ISO format with timezone
                           })
                           .eq('id', keyword_id_str) # Match by UUID string
                           .is_('discovered_by_user_id', 'null') # Ensure we only update if not already discovered
                           .execute()
        )
        # Assuming success if no error. Check affected rows if needed via response inspection.
        print(f"Successfully recorded discovery for keyword ID {keyword_id_str}.")
        return True # Indicate success
    except (APIError, ConnectionError, Exception) as e:
        await log_error(guild_for_log, f"Failed to record discovery for keyword ID {keyword_id_str} in Supabase", error=e, ping_owner=True)
        return False # Indicate failure



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
    Fetches HC members from Discord and Supabase, including all-time activity counts.
    Logs warnings for mismatches (Role w/o DB, DB w/o Role/Member).
    Returns a list of dicts: [{'member': discord.Member | None, 'discord_id': str | None, 'discord_name': str | None, 'ign': str, 'activity_count': int, 'last_seen': date | None}]
    and the total count.
    Data is sorted by Discord name (if available), then IGN (case-insensitive).
    """
    print(f"Fetch HC Data ({guild.name}): Starting fetch...")
    hc_role = guild.get_role(HC1_ROLE_ID)
    if not hc_role:
        await log_error(guild, f"HC Role {HC1_ROLE_ID} not found during fetch.", ping_owner=True) # Ping owner on critical role missing
        return [], 0

    # 1. Fetch ALL entries from Supabase hc_members table
    all_db_members: Dict[str, Dict] = {} # discord_id -> {'ign': ign, 'discord_name': discord_name, 'processed': False}
    ign_only_members: Dict[str, Dict] = {} # ign_lower -> {'ign_original': ign, 'processed': False}
    all_igns_in_db: List[str] = [] # List of all original-case IGNs for activity fetching

    try:
        if not supabase: raise ConnectionError("Supabase client unavailable.")
        print(f"Fetch HC Data ({guild.name}): Fetching all from Supabase hc_members table...")
        # MODIFIED: Select discord_name as well
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members").select("discord_id, ingame_name, discord_name").execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            for entry in resp.data:
                ign = entry.get("ingame_name")
                if not ign: continue # Skip entries without an IGN
                all_igns_in_db.append(ign) # Add original case IGN
                d_id = entry.get("discord_id")
                d_name = entry.get("discord_name") # Get discord_name
                if d_id:
                    # Store discord_id as string consistently
                    all_db_members[str(d_id)] = {"ign": ign, "discord_name": d_name, "processed": False}
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
    activity_counts = await fetch_activity_data(guild, all_igns_in_db) # Fetches count and last_seen
    print(f"Fetch HC Data ({guild.name}): Fetched activity data for {len(activity_counts)} IGNs.")

    # 3. Get Discord members with the HC role
    discord_hc_members: List[discord.Member] = []
    try:
        if not guild.chunked and guild.member_count is not None and guild.member_count > 1000:
             try:
                 print(f"Fetch HC Data ({guild.name}): Chunking guild..."); await guild.chunk(cache=True)
             except Exception as chunk_e: print(f"WARN: Chunking failed: {chunk_e}") # Log warning, don't stop

        discord_hc_members = [m for m in guild.members if hc_role in m.roles and not m.bot]
        print(f"Fetch HC Data ({guild.name}): Found {len(discord_hc_members)} Discord members with HC role.")
    except Exception as e:
        await log_error(guild, "Guild chunking/member fetch failed during data fetch. List might be incomplete.", error=e, ping_owner=False)

    # 4. Correlate and Build Final Data Structure
    final_data: List[Dict[str, Any]] = []

    # Process Discord members with HC role
    for member in discord_hc_members:
        member_id_str = str(member.id)
        db_entry = all_db_members.get(member_id_str)
        ign = "Unknown"
        activity = {'count': 0, 'last_seen': None} # Default activity
        # Get member's current name for storage consistency if updating
        current_discord_name = f"{member.name}#{member.discriminator}" if member.discriminator != '0' else member.name


        if db_entry:
            ign = db_entry["ign"]
            db_entry["processed"] = True
            activity = activity_counts.get(ign.lower(), {'count': 0, 'last_seen': None})
        else:
            await log_info(guild, f"Fetch HC Data Warning: Discord member {member.mention} (`{member.id}`) has HC role but no matching DB entry found.")

        final_data.append({
            "member": member,
            "discord_id": member_id_str, # Add discord_id directly
            "discord_name": current_discord_name, # Add current discord_name
            "ign": ign,
            "activity_count": activity['count'],
            "last_seen": activity['last_seen']
        })

    # Process remaining DB entries (Discord member lost role/left or IGN-only)
    for d_id, entry_data in all_db_members.items():
        if not entry_data["processed"]:
            ign = entry_data["ign"]
            stored_discord_name = entry_data.get("discord_name") # Get stored name
            activity = activity_counts.get(ign.lower(), {'count': 0, 'last_seen': None})

            # Logging for Scenario 2 (DB entry exists, but member not found/no role)
            try:
                member_in_guild = guild.get_member(int(d_id))
                if member_in_guild:
                    if hc_role not in member_in_guild.roles:
                        await log_info(guild, f"Fetch HC Data Warning: DB entry exists for {member_in_guild.mention} (`{d_id}`), but they do **not** currently have the HC role. IGN: `{ign}`")
                else:
                    name_to_log = stored_discord_name or f"ID {d_id}"
                    await log_info(guild, f"Fetch HC Data Info: DB entry exists for user `{name_to_log}` (`{d_id}`), but they are not currently in this server (or couldn't be found). IGN: `{ign}`")
            except ValueError:
                 await log_error(guild, f"Fetch HC Data Error: Invalid Discord ID '{d_id}' found in database for IGN '{ign}'.", ping_owner=True)
            except Exception as e_log:
                 await log_error(guild, f"Fetch HC Data Error: Failed during Scenario 2 check for ID '{d_id}'", error=e_log, ping_owner=False)

            # Add to final data with member: None
            final_data.append({
                "member": None,
                "discord_id": d_id, # Stored discord_id
                "discord_name": stored_discord_name, # Stored discord_name
                "ign": ign,
                "activity_count": activity['count'],
                "last_seen": activity['last_seen']
            })

    # Add IGN-only entries (no discord_id)
    for ign_lower, entry_data in ign_only_members.items():
         ign = entry_data["ign_original"]
         activity = activity_counts.get(ign_lower, {'count': 0, 'last_seen': None})
         final_data.append({
             "member": None,
             "discord_id": None, # Explicitly None
             "discord_name": None, # Explicitly None
             "ign": ign,
             "activity_count": activity['count'],
             "last_seen": activity['last_seen']
         })


    # 5. Sort the final list
    final_data.sort(key=lambda item: (
        item['member'].name.lower() if item.get('member') else (item.get('discord_name', 'zzz') or 'zzz').lower(),
        item['member'].discriminator if item.get('member') else 'zzz', # Fallback for sorting
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
    global BOT_USER_ID, command_ids, STAFF_CHANNELS # Ensure all globals used are listed

    if bot.user:
        BOT_USER_ID = bot.user.id
        print(f"Logged in as {bot.user} (ID: {BOT_USER_ID})")
        print(f"Discord.py v{discord.__version__}")
        print(f"Bot Instance Type: {BOT_INSTANCE_TYPE}") # Log the instance type
    else:
        print("CRITICAL ERROR: Bot user object not found on ready.")
        # Consider logging this error to your extraordinary_logs channel if possible,
        # though if bot.user is None, guild context for logging might also be an issue.
        return # Critical failure, cannot proceed
    
    activity = discord.Activity(type=discord.ActivityType.watching, name="out for Pings | /nerdhelp")
    await bot.change_presence(status=discord.Status.online, activity=activity)

    # --- Command Syncing ---
    print("Syncing application commands...")
    synced_commands = []
    try:
        
        synced_commands = await tree.sync() # Your original global sync
        
        print(f"Synced {len(synced_commands)} application commands.")
        command_ids.clear() # Clear previous IDs
        for cmd in synced_commands:
            if hasattr(cmd, 'name') and hasattr(cmd, 'id'):
                command_ids[cmd.name] = cmd.id
                # If it's a group, store subcommand IDs too if your get_cmd_mention needs it
                if isinstance(cmd, app_commands.Group):
                    for sub_cmd in cmd.commands:
                        if isinstance(sub_cmd, app_commands.Command): # Check if it's a command, not another subgroup for this example
                             full_name = f"{cmd.name} {sub_cmd.name}" # Or however you reference subcommands
                             command_ids[full_name] = sub_cmd.id # Note: Discord might return separate IDs for subcommands
            else:
                print(f"  Skipped storing ID during sync for an item (type: {type(cmd)}, name: {getattr(cmd, 'name', 'N/A')})")
        if command_ids:
            print(f"Stored command IDs: {command_ids}")
        else:
            print("Warning: command_ids dictionary is empty after sync.")
    except discord.HTTPException as e:
        print(f"Command Sync failed (HTTPException): {e.status} - {e.text}")
        # Log this error if possible
        # await log_error(None, "Command Sync failed (HTTPException)", error=e, ping_owner=True)
    except Exception as e:
        print(f"Command Sync failed (Unexpected Error): {e}\n{traceback.format_exc()}")
        # Log this error if possible
        # await log_error(None, "Command Sync failed (Unexpected Error)", error=e, ping_owner=True)


    # --- Signal Bot Ready & Load Initial Data ---
    print(f"Bot is ready and connected to {len(bot.guilds)} guild(s).")
    
    # Determine the guild for logging readiness message
    log_guild_for_ready_msg = bot.get_guild(CATERCORD_GUILD_ID) or (bot.guilds[0] if bot.guilds else None)
    
    if log_guild_for_ready_msg:
        try:
             instance_info = f" ({BOT_INSTANCE_TYPE} instance)" if BOT_INSTANCE_TYPE != "PRODUCTION" else ""
             await log_info(log_guild_for_ready_msg, f"Bot ready and online{instance_info}. Synced {len(synced_commands)} commands.")
        except Exception as log_e:
             print(f"Failed to send initial ready log message: {log_e}")

    print("--- Loading initial data ---")
    # Pass a guild context for logging within these load functions if possible
    log_guild_for_data_load = bot.get_guild(CATERCORD_GUILD_ID) # Prefer Catercord for logs
    if not log_guild_for_data_load and bot.guilds: log_guild_for_data_load = bot.guilds[0] # Fallback

    await load_keyword_data(log_guild_for_data_load) # Load keywords
    await load_ign_cache(log_guild_for_data_load) # Load IGN cache

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

# --- New HCLeave Command (MODIFIED: Includes Role Changes if Discord ID found) ---
@tree.command(name="hcleave", description="Remove member from HC database by IGN & update roles if linked.") # MODIFIED Description
@app_commands.describe(
    ingame_name="The IGN to remove from the database."
)
@app_commands.autocomplete(ingame_name=ign_autocomplete)
@app_commands.checks.has_permissions(manage_roles=True) # User needs permission to trigger potential role changes
@app_commands.checks.bot_has_permissions(manage_roles=True) # Bot needs permission to manage roles
async def hcleave(interaction: discord.Interaction, ingame_name: str):
    """Removes HC database entry based on IGN and handles linked user roles."""
    guild = interaction.guild
    if not await check_supabase_available(interaction):
        try: # Attempt cleanup if deferred
            if interaction.response.is_done(): await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        except (discord.NotFound, discord.HTTPException): pass
        return
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=False)
        return
    if not supabase:
        await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=False)
        await log_error(guild, "hcleave failed: Supabase unavailable.", interaction=interaction)
        return

    # Defer publicly as it might involve visible role changes
    await interaction.response.defer(thinking=True, ephemeral=False)

    # --- Role Setup ---
    role_hc = guild.get_role(HC1_ROLE_ID)
    role_maybe_exhc = guild.get_role(EX_MEMBER_ROLE_ID)
    bot_member = guild.me

    # --- Role Existence Checks ---
    critical_roles_found = True
    missing_roles_log = []
    if not role_hc:
        critical_roles_found = False
        missing_roles_log.append(f"HC Role ({HC1_ROLE_ID})")
        print(f"hcleave Warning ({guild.name}): HC Role {HC1_ROLE_ID} not found.")
    if not role_maybe_exhc:
        # Not strictly critical for DB delete, but needed for role add
        # Consider if this should prevent the command entirely or just the role part
        # For now, let it proceed but log warning
        print(f"hcleave Warning ({guild.name}): Maybe-ExHC Role {EX_MEMBER_ROLE_ID} not found.")
        # If Maybe-ExHC MUST be added, uncomment below:
        # critical_roles_found = False
        # missing_roles_log.append(f"Maybe-ExHC Role ({EX_MEMBER_ROLE_ID})")

    # Stop if critical HC role is missing
    if not role_hc:
        msg = f"❌ Setup Error: HC Role (ID: {HC1_ROLE_ID}) not found. Cannot perform role actions."
        await interaction.followup.send(msg, ephemeral=False)
        await log_error(guild, f"hcleave failed: Missing critical HC role {HC1_ROLE_ID}", interaction=interaction)
        return

    # --- Prepare for actions ---
    log_summary = []
    result_summary = []
    errors_occurred = False
    db_removed = False
    role_changes_attempted = False
    role_changes_succeeded = False
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

    # --- Step 1: Check Database for IGN and potential Discord ID ---
    try:
        print(f"hcleave: Checking DB for entry matching IGN '{cleaned_ign}'...")
        fetch_resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .select("discord_id, ingame_name") # Fetch discord_id
                           .eq("ingame_name", cleaned_ign)
                           .maybe_single()
                           .execute()
        )

        if fetch_resp and hasattr(fetch_resp, 'data') and fetch_resp.data:
            found_discord_id = fetch_resp.data.get("discord_id")
            print(f"hcleave: Found DB entry for '{cleaned_ign}'. Linked Discord ID: {found_discord_id or 'None'}")
            if found_discord_id:
                 try:
                      member_to_modify = guild.get_member(int(found_discord_id))
                      if member_to_modify:
                           print(f"hcleave: Found Discord member {member_to_modify} ({found_discord_id}) linked to IGN '{cleaned_ign}'.")
                      else:
                           result_summary.append(f"ℹ️ DB entry found for `{cleaned_ign}`, but linked user ID `{found_discord_id}` is not in this server.")
                           log_summary.append(f"DB fetch OK, linked user {found_discord_id} not found in guild.")
                 except ValueError:
                      result_summary.append(f"⚠️ DB data issue: Invalid Discord ID '{found_discord_id}' found for IGN `{cleaned_ign}`.")
                      log_summary.append(f"DB fetch OK, but invalid Discord ID '{found_discord_id}' found.")
                      errors_occurred = True
                      found_discord_id = None # Treat as unlinked if ID is invalid
        else:
            print(f"hcleave: No DB entry found matching IGN '{cleaned_ign}'.")
            result_summary.append(f"ℹ️ No database entry found matching {target_identifier_log}.")
            log_summary.append(f"DB check: No match found for {cleaned_ign}")
            # If no DB entry, send message and stop. Nothing to delete or change roles for.
            await interaction.followup.send(embed=create_embed(title="ℹ️ HC Leave: No Action Needed", description="\n".join(result_summary), color=discord.Color.blue()))
            return # Exit the command

    except (APIError, ConnectionError, Exception) as e:
        errors_occurred = True
        result_summary.append(f"⚠️ DB Error checking for {target_identifier_log}: Could not proceed.")
        log_summary.append(f"DB check fail: {type(e).__name__}")
        await log_error(guild, f"hcleave DB check error for {cleaned_ign}", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed(title="❌ HC Leave Failed", description="\n".join(result_summary), color=discord.Color.red()))
        return # Exit command on DB check failure

    # --- Step 2: Attempt Role Changes (if member found) ---
    if member_to_modify and role_hc: # Ensure member and HC role objects exist
        role_changes_attempted = True
        can_manage_member = bot_member.top_role.position > member_to_modify.top_role.position
        can_remove_hc = bot_member.top_role.position > role_hc.position
        can_add_exhc = role_maybe_exhc and (bot_member.top_role.position > role_maybe_exhc.position)

        if not can_manage_member:
            errors_occurred = True
            result_summary.append(f"⚠️ Role Skipped: Bot hierarchy too low to manage {member_to_modify.mention}.")
            log_summary.append(f"Role change skipped (Bot hierarchy vs member {member_to_modify.id})")
        elif not (role_hc in member_to_modify.roles):
            result_summary.append(f"ℹ️ Role Info: {member_to_modify.mention} did not have the `{role_hc.name}` role.")
            log_summary.append(f"Role removal skipped ({member_to_modify.id} didn't have HC role)")
        else:
            roles_to_remove = []
            roles_to_add = []

            if can_remove_hc:
                roles_to_remove.append(role_hc)
            else:
                errors_occurred = True
                result_summary.append(f"⚠️ Role Skipped: Bot hierarchy too low to remove `{role_hc.name}`.")
                log_summary.append(f"Role removal skipped (Bot hierarchy vs HC role)")

            if role_maybe_exhc: # Only attempt add if the role exists
                if can_add_exhc:
                    if role_maybe_exhc not in member_to_modify.roles:
                         roles_to_add.append(role_maybe_exhc)
                else:
                    # Don't mark as error, just log inability to add maybe_exhc
                    result_summary.append(f"ℹ️ Role Info: Bot hierarchy too low to add `{role_maybe_exhc.name}`.")
                    log_summary.append(f"Role add skipped (Bot hierarchy vs Maybe-ExHC role)")

            if roles_to_remove or roles_to_add:
                try:
                    current_roles = member_to_modify.roles
                    final_role_set = [r for r in current_roles if r not in roles_to_remove] + roles_to_add
                    final_role_set = [r for r in final_role_set if r.id != guild.default_role.id] # Ensure @everyone isn't duplicated

                    await member_to_modify.edit(roles=final_role_set, reason=reason)
                    role_changes_succeeded = True
                    if role_hc in roles_to_remove:
                         hc_role_removed_flag = True
                         result_summary.append(f"➖ Role Removed: `{role_hc.name}` from {member_to_modify.mention}.")
                    if role_maybe_exhc in roles_to_add:
                         exhc_role_added_flag = True
                         result_summary.append(f"➕ Role Added: `{role_maybe_exhc.name}` to {member_to_modify.mention}.")
                    log_summary.append(f"Role update successful for {member_to_modify.id}. Removed: {hc_role_removed_flag}, Added ExHC: {exhc_role_added_flag}")
                except discord.Forbidden: errors_occurred = True; result_summary.append(f"⚠️ Role Error: Permissions error updating {member_to_modify.mention}."); log_summary.append(f"Role update fail: Forbidden for {member_to_modify.id}"); await log_error(guild, f"hcleave role update Forbidden for {member_to_modify.id}", interaction=interaction)
                except discord.HTTPException as e: errors_occurred = True; result_summary.append(f"⚠️ Role Error: Discord API Error updating {member_to_modify.mention}."); log_summary.append(f"Role update fail: HTTP {e.status} for {member_to_modify.id}"); await log_error(guild, f"hcleave role update HTTP for {member_to_modify.id}", error=e, interaction=interaction)
                except Exception as e: errors_occurred = True; result_summary.append(f"⚠️ Role Error: Unknown error updating {member_to_modify.mention}."); log_summary.append(f"Role update fail: {type(e).__name__} for {member_to_modify.id}"); await log_error(guild, f"hcleave role update unexpected error for {member_to_modify.id}", error=e, interaction=interaction)

    # --- Step 3: Database Deletion (if entry was found initially) ---
    # This runs regardless of role change success, as long as DB entry was found.
    try:
        print(f"hcleave: Attempting to delete DB entry matching IGN '{cleaned_ign}'...")
        delete_result = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                           .delete()
                           .eq("ingame_name", cleaned_ign) # Match by IGN
                           .execute()
        )
        # Check if deletion happened based on response data
        if delete_result and hasattr(delete_result, 'data') and delete_result.data:
             db_removed = True
             result_summary.append(f"🗑️ Database entry removed for {target_identifier_log}.")
             log_summary.append(f"DB entry delete OK for {cleaned_ign}")
        else:
             # This case *shouldn't* happen if we found the entry earlier, but handle defensively
             result_summary.append(f"ℹ️ Database entry for {target_identifier_log} seems to have disappeared before deletion.")
             log_summary.append(f"DB entry delete: No match found (unexpected) for {cleaned_ign}")
             # Consider setting errors_occurred=True here if this is unexpected
    except (APIError, ConnectionError, Exception) as e:
        errors_occurred = True
        result_summary.append(f"⚠️ DB Error removing {target_identifier_log}: {getattr(e, 'message', type(e).__name__)}")
        log_summary.append(f"DB delete fail: {type(e).__name__}")
        await log_error(guild, f"hcleave DB delete error for {cleaned_ign}", error=e, interaction=interaction)

    # --- Final Response & Logging ---
    final_color = discord.Color.green() if not errors_occurred else discord.Color.orange()
    final_title = f"{'✅' if not errors_occurred else '⚠️'} HC Leave Processed: {target_identifier_log}"
    if errors_occurred: final_title += " (with issues/skips)"
    if not result_summary: result_summary.append("ℹ️ No specific actions were performed or needed (check logs).") # Fallback if logic somehow leads here

    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    try:
        await interaction.followup.send(embed=final_embed, ephemeral=False)
    except (discord.NotFound, discord.HTTPException) as e:
        await log_error(guild, "hcleave failed final followup send", error=e, interaction=interaction)

    await log_info(guild, f"`{interaction.user}` processed /hcleave for {target_identifier_log}. Summary: {'; '.join(log_summary)}.")

    # Trigger list update ONLY if DB entry was successfully removed
    if db_removed:
        print(f"hcleave: Triggering list update for {target_identifier_log} (DB removed: {db_removed}).")
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

@tree.command(name="refresh", description="Manually refresh the interactive [HC1] list message AND reload keyword data.") # Updated description
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    guild = interaction.guild
    # --- Initial Checks ---
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return
    # Use check_supabase_available helper
    if not await check_supabase_available(interaction):
        # Helper handles ephemeral response/logging
        return
    # Ensure target guild for list refresh
    if guild.id != CATERCORD_GUILD_ID:
        await interaction.response.send_message("List refresh commands can only be used in the target server.", ephemeral=True)
        return
    # Ensure list channel exists (relevant for list update part)
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(list_channel, discord.TextChannel):
        await interaction.response.send_message(f"❌ Configuration Error: Static list channel (ID: {HC_MEMBER_LIST_CHANNEL_ID}) not found or invalid.", ephemeral=True)
        await log_error(guild, f"/refresh failed: Static list channel invalid.", interaction=interaction)
        return

    # --- Defer Publicly ---
    await interaction.response.defer(thinking=True, ephemeral=False)

    # --- Initial Feedback ---
    try:
        # Mention both actions in the initial feedback
        feedback_msg = f"⏳ Starting refresh...\n- Reloading keyword data from Supabase.\n- Updating interactive list in {list_channel.mention}."
        await interaction.followup.send(feedback_msg, ephemeral=False)
    except Exception as e_followup:
        # Log if the initial followup fails, but continue the refresh process
        await log_error(guild, "Failed initial /refresh followup send", error=e_followup, interaction=interaction)
        # Attempt to edit original response if followup failed (might also fail)
        try: await interaction.edit_original_response(content="⏳ Starting refresh...", embed=None, view=None)
        except Exception: pass


    # --- Execute Refresh Actions ---
    keyword_load_success = False
    list_update_success = False
    error_details = ""

    try:
        # 1. Reload Keyword Data
        await log_info(guild, f"Manual keyword data reload initiated by `{interaction.user}` via /refresh.")
        await load_keyword_data(guild)
        # Basic check: does the cache have items? Could be 0 legitimately.
        # A more robust check might involve comparing counts before/after, but let's rely on load_keyword_data's logging for errors.
        keyword_load_success = True # Assume success if no exception bubbled up
        print(f"Keyword reload complete. Cache size: {len(keyword_data_cache)}")

        # 2. Update Static List Message
        await log_info(guild, f"Manual interactive static list refresh initiated by `{interaction.user}` via /refresh.")
        await update_static_list_message(guild) # This function logs its own success/failure
        list_update_success = True # Assume success if no exception bubbled up from here
        print(f"Static list update triggered.")

        # --- Update Complete ---
        completion_msg = f"✅ Refresh complete!\n- Keyword data reloaded ({len(keyword_data_cache)} rules).\n- Interactive list update triggered in {list_channel.mention}."
        await interaction.edit_original_response(content=completion_msg, embed=None, view=None)
        await log_info(guild, f"/refresh command confirmed complete for user {interaction.user}.")

    except Exception as e:
        action = "keyword loading" if not keyword_load_success else "list updating"
        error_details = f" An error occurred during {action}."
        await log_error(guild, f"Error during /refresh process execution ({action})", error=e, interaction=interaction)
        try:
            # Edit original response to show failure
            await interaction.edit_original_response(content=f"❌ Refresh failed.{error_details}", embed=None, view=None)
        except Exception: pass # Ignore if editing final response fails

# --- Discovery Command (Further Refined Formatting for User-App Context) ---
@tree.command(name="discoveries", description="Explore the world of AI-powered secret keyword phrases!")
async def discoveries(interaction: discord.Interaction):
    # Ensure bot object and user ID are available
    if not bot or not bot.user or not bot.user.id:
        await interaction.response.send_message(
            "🔍 Bot is not fully initialized. Please try again in a moment.",
            ephemeral=True
        )
        return

    if not keyword_data_cache:
        await interaction.response.send_message(
            "🔍 Keyword data is still loading or not available. Please try again shortly!",
            ephemeral=True
        )
        return

    guild = interaction.guild
    catercord_invite_link = "https://discord.gg/5gMRbeWNKw"
    bot_invite_link = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=68608&integration_type=0&scope=applications.commands+bot"

    description_lines = []
    is_catercord_server = False
    bot_is_true_guild_member = False

    if guild:
        is_catercord_server = guild.id == CATERCORD_GUILD_ID
        if guild.me and guild.me.joined_at: # Check for true membership via joined_at
            bot_is_true_guild_member = True

    if is_catercord_server:
        guild_name_display = f"this server (**{guild.name}**)" if guild and guild.name else "Catercord"
        description_lines.extend([
            f"🕵️‍♂️ I'll respond to any known secret phrases you type here in {guild_name_display}.",
            f"🎉 Be the first to find a new one, and I'll announce your grand discovery!"
        ])
    elif guild and bot_is_true_guild_member: # In a non-Catercord server, AND bot is a true guild member
        description_lines.extend([
            f"🕵️‍♂️ I'll respond to any *already discovered* secret phrases you type in this server, since I'm a full member here.",
            f"➡️ To discover **new** secret phrases, you'll need to join [**Catercord**]({catercord_invite_link})!"
        ])
    else: # Covers DMs, or servers where the bot is NOT a true guild member (user-app context)
        bot_name_display = bot.user.name if bot.user and bot.user.name else "this bot"
        
        if guild: # User-app in a specific server context
            # Safely get guild name, providing a fallback if it's empty or None
            guild_name_display = guild.name if guild.name and guild.name.strip() else "this server"
            
            line1 = f"👋 Thanks for trying my keyword feature in **{guild_name_display}**!"
            
            # Construct the link text and the full line carefully for the bot invite
            link_text_invite_bot = f"add {bot_name_display} to **{guild_name_display}**"
            line2 = f"To let me listen for and respond to discovered keywords here, an admin needs to formally [{link_text_invite_bot}]({bot_invite_link})."
            
            line3 = f"➡️ For discovering **new** secret phrases, the adventure is in [**Catercord**]({catercord_invite_link})!"
            description_lines.extend([line1, line2, line3])
        else: # For DMs
            description_lines.extend([
                f"👋 Thanks for checking out my keyword feature!",
                f"🔗 To use me in a server so I can respond to keywords, an admin can [add {bot_name_display} to their server]({bot_invite_link}).",
                f"➡️ The main place to discover **new** secret phrases is [**Catercord**]({catercord_invite_link})!"
            ])

    # --- Keyword Progress and Discovered List (Existing Logic) ---
    description_lines.append("\n---")
    if total_keywords > 0:
        description_lines.append(f"**Overall Progress:** {discovered_keywords_count} / {total_keywords} phrases revealed globally.")
    else:
        description_lines.append("\n*No keyword phrases are currently configured.*")

    embed_title = "🔮 AI Keyword Mysteries 🔮"
    embed = discord.Embed(
        title=embed_title,
        description="\n".join(description_lines),
        color=NERDY_YELLOW
    )

    discovered_list_formatted = []
    undiscovered_count = 0
    valid_rules = [rule for rule_id, rule in keyword_data_cache.items() 
                   if isinstance(rule, dict) and 'phrase_identifier' in rule]
    sorted_rules = sorted(valid_rules, key=lambda r: str(r.get('phrase_identifier', '')).lower())

    for rule in sorted_rules:
        if rule.get('discovered_by'):
            user_id_str = rule['discovered_by']
            timestamp_dt = rule.get('discovered_at')
            user_mention = f"<@{user_id_str}>"
            time_display = ""
            if timestamp_dt and isinstance(timestamp_dt, datetime.datetime):
                timestamp_unix = int(timestamp_dt.timestamp())
                time_display = f" (<t:{timestamp_unix}:R>)"
            escaped_phrase_id = discord.utils.escape_markdown(str(rule['phrase_identifier']))
            discovered_list_formatted.append(
                f"🔹 `{escaped_phrase_id}` by {user_mention}{time_display}"
            )
        else:
            undiscovered_count += 1

    if discovered_list_formatted:
        discovered_text_joined = "\n".join(discovered_list_formatted)
        if len(discovered_text_joined) > 1020: # Max field value length
            discovered_text_joined = discovered_text_joined[:1015] + "\n... (more)"
        embed.add_field(name="📜 Known Phrases (Discovered Globally)", value=discovered_text_joined, inline=False)
    elif total_keywords > 0:
        embed.add_field(name="📜 Known Phrases (Discovered Globally)", value="The scroll is blank... No phrases discovered yet across all lands!", inline=False)

    if total_keywords > 0 and undiscovered_count > 0:
        embed.add_field(
            name=f"❓ {undiscovered_count} Secret Phrase{'s' if undiscovered_count != 1 else ''} Still Hidden Globally",
            value=f"*The quest for knowledge continues!*",
            inline=False
        )
    elif total_keywords > 0 and undiscovered_count == 0:
         embed.add_field(name="🎉 All Mysteries Solved Globally! 🎉", value="*The archives are complete!*", inline=False)

    bot_name_footer = bot.user.name if bot.user and bot.user.name else "Pingslave"
    embed.set_footer(text=f"Bot by TheNerd (sweet_honey) | {bot_name_footer}")
    if bot.user and bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)

    await interaction.response.send_message(embed=embed, ephemeral=False)

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
    # --- Initial Checks: Ignore DMs (unless specifically handled later), self, other bots, no content ---
    if not message.guild or not bot.is_ready() or not bot.user or message.author.id == bot.user.id or message.author.bot:
        return
    if not message.content and not message.attachments: # Ignore messages with no text and no attachments
        return

    guild = message.guild
    channel = message.channel
    author = message.author
    # now = discord.utils.utcnow() # Not used in this refactored version directly

    # --- Context Flags ---
    is_catercord = guild.id == CATERCORD_GUILD_ID
    is_private_server = guild.id == PRIVATE_SERVER_ID
    is_owner = author.id == OWNER_USER_ID

    # Catercord specific channel checks for keyword discovery restrictions
    is_staff_channel_catercord = False
    is_bot_commands_channel_catercord = False # Used for keyword discovery restrictions
    if is_catercord:
        is_staff_channel_catercord = channel.id in STAFF_CHANNELS
        is_bot_commands_channel_catercord = channel.id in BOT_COMMANDS_ALLOWED_CHANNEL_IDS

    # This flag is specifically for keyword discovery restrictions in Catercord
    is_restricted_keyword_discovery_channel_catercord = is_staff_channel_catercord or is_bot_commands_channel_catercord


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
                await log_error(guild, f"Screenshot activity error: Failed to get today's date ({date_error})", interaction=message) # interaction should be message
                return

            try:
                known_igns_str = "\n".join(ingame_name_cache) if ingame_name_cache else "No known names provided."
                
                for idx, image_att in enumerate(valid_image_attachments):
                    print(f"Processing image {idx + 1}/{num_images} (Filename: {image_att.filename}, ID: {image_att.id})...")
                    try:
                        image_data = await image_att.read()
                        # Use new prompt key and kwargs
                        ai_extracted_text_for_this_image = await get_ai_response_with_image(
                            prompt_key="FLORR_IMAGE_NAME_EXTRACTION", # New prompt key
                            image_bytes=image_data,
                            prompt_kwargs={'known_igns_list_str': known_igns_str}
                            # preferred_model_id defaults to 'gemini_2_5_flash' in get_ai_response_with_image
                        )
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
                                if ingame_name_cache and potential_names_from_ai_this_image:
                                    for ai_name in potential_names_from_ai_this_image:
                                        ai_name_lower = ai_name.lower()
                                        for cached_ign in ingame_name_cache:
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

    # --- 2. Always-On AI Channels (Responds to every message) ---
    if channel.id in ALWAYS_ON_AI_CHANNELS and not message.content.startswith(COMMAND_PREFIX):
        print(f"AI Trigger: Always-On Channel Message by {author.name} in #{channel.name}")
        history = []
        try:
            async for msg_hist in channel.history(limit=10, before=message):
                history.append(msg_hist)
            history.reverse() # Oldest to newest
            history.append(message) # Add current message to history for AI context
        except Exception as e:
            print(f"Error fetching history for AI AlwaysOn: {e}")
            history.append(message) # At least have the current message

        cleaned_prompt = message.content
        if not cleaned_prompt.strip() and message.stickers:
            cleaned_prompt = f"(User sent a sticker: {message.stickers[0].name})"
        elif not cleaned_prompt.strip():
             cleaned_prompt = "(User sent an empty or attachment-only message that wasn't an image)"

        # Use send_ai_chat_response with specific model preference for AlwaysOn
        await send_ai_chat_response(
            trigger_type="AlwaysOn",
            history=history,
            user_message_content=cleaned_prompt, # Pass the user's raw message
            system_instruction_key="HUMAN_SYSTEM_INSTRUCTION" # Default human-like system prompt
            # preferred_model_id will be 'gemini_2_0_flash' (standard) inside send_ai_chat_response for "AlwaysOn"
        )
        return # Message handled by AlwaysOn AI

    # --- 3. Reply/Mention Trigger ---
    should_trigger_reply_mention = False
    is_reply_to_bot = False
    bot_mention_formats = [f'<@{bot.user.id}>', f'<@!{bot.user.id}>']

    if message.reference and message.reference.message_id:
        try:
            ref_msg = message.reference.resolved
            if not ref_msg and message.reference.channel_id == channel.id : # Check if channel ID matches before fetching
                ref_msg = await channel.fetch_message(message.reference.message_id)
            
            if ref_msg and ref_msg.author.id == bot.user.id:
                should_trigger_reply_mention = True
                is_reply_to_bot = True
        except Exception as e_ref:
            print(f"Minor error fetching referenced message for reply check: {e_ref}")

    if not should_trigger_reply_mention and any(mention in message.content for mention in bot_mention_formats):
        should_trigger_reply_mention = True

    if should_trigger_reply_mention:
        # If in Catercord AND not an always-on channel, show the "psst" message.
        if is_catercord and channel.id not in ALWAYS_ON_AI_CHANNELS:
            clickable_channel = f"<#{UNRESTRICTED_AI_CHANNEL_ID}>" # This is an always-on channel
            info_message_text = (
                f"ℹ️ Psst! You can chat with me freely in {clickable_channel} "
                f"for AI-powered conversations! This message will disappear shortly."
            )
            try:
                await message.reply(info_message_text, mention_author=False, delete_after=7.0)
            except (discord.Forbidden, discord.HTTPException) as info_reply_err:
                print(f"Error sending AI channel info message: {info_reply_err}")
            return # Do not proceed with AI response in this restricted context

        # Proceed with AI response if:
        # 1. In an ALWAYS_ON_AI_CHANNELS (Catercord or otherwise if you expand that set).
        # 2. In any other server (not Catercord) where the bot is a full guild member.
        can_respond_here = False
        if channel.id in ALWAYS_ON_AI_CHANNELS: # This covers the main AI channel in Catercord
            can_respond_here = True
        elif not is_catercord and guild.me and guild.me.joined_at: # Other servers, if bot is full member
            can_respond_here = True
        
        if can_respond_here:
            print(f"AI Trigger: Reply/Mention by {author.name} in #{channel.name}")
            history = []
            try:
                async for msg_hist in channel.history(limit=10, before=message):
                    history.append(msg_hist)
                history.reverse()
                history.append(message) # Add current message to history
            except Exception as e:
                print(f"Error fetching history for AI reply/mention: {e}")
                history.append(message)

            cleaned_prompt = message.content
            for mention in bot_mention_formats:
                cleaned_prompt = cleaned_prompt.replace(mention, "").strip()
            if not cleaned_prompt.strip() and message.stickers:
                 cleaned_prompt = f"(User replied/mentioned with a sticker: {message.stickers[0].name})"
            elif not cleaned_prompt.strip():
                cleaned_prompt = "(just replied/mentioned, no extra text)"

            # Use send_ai_chat_response with specific model preference for Reply/Mention
            await send_ai_chat_response(
                trigger_type="Reply" if is_reply_to_bot else "Mention",
                history=history,
                user_message_content=cleaned_prompt,
                system_instruction_key="HUMAN_SYSTEM_INSTRUCTION"
                # preferred_model_id will be 'gemini_2_5_flash' (highest) inside send_ai_chat_response
            )
            return # Handled by AI reply/mention

    # --- 4. Keyword Detection Logic ---
    if keyword_data_cache: # Check if AI models are available implicitly by checking cache
        message_content_lower = message.content.lower()
        # global discovered_keywords_count # Ensure this is declared global if modified within this scope directly

        for rule_id_str, rule_data in keyword_data_cache.items():
            try:
                # Ensure rule_data is a dict and has essential keys
                if not isinstance(rule_data, dict) or not all(k in rule_data for k in ['inclusion_regex', 'phrase_identifier', 'speciality', 'instructions']):
                    # print(f"Skipping malformed rule_data for rule_id: {rule_id_str}") # Optional debug log
                    continue 

                if rule_data.get('exclusion_regex') and rule_data['exclusion_regex'].search(message_content_lower):
                    continue
                if not rule_data['inclusion_regex'].search(message_content_lower):
                    continue

                rule_is_discovered = bool(rule_data.get('discovered_by'))
                phrase_identifier = rule_data['phrase_identifier'] # Already a string

                # Discovery Logic
                if not rule_is_discovered:
                    can_discover_this_rule = False
                    discovery_context_server = ""
                    
                    if is_catercord and not is_restricted_keyword_discovery_channel_catercord and not is_owner:
                        can_discover_this_rule = True
                        discovery_context_server = "Catercord (Public Channel)"
                    elif is_private_server and is_owner:
                        can_discover_this_rule = True
                        discovery_context_server = "Private Server (Owner Discovery)"

                    if can_discover_this_rule:
                        print(f"Keyword DISCOVERY: '{phrase_identifier}' by {author.name} ({author.id}) in #{channel.name} ({guild.name} - {discovery_context_server})")
                        discovery_time = discord.utils.utcnow()
                        db_recorded = await record_discovery_in_db(guild, rule_id_str, author.id, discovery_time)
                        if db_recorded:
                            keyword_data_cache[rule_id_str]['discovered_by'] = str(author.id)
                            keyword_data_cache[rule_id_str]['discovered_at'] = discovery_time
                            # Ensure discovered_keywords_count is a global if modified here
                            # global discovered_keywords_count; discovered_keywords_count += 1 
                            
                            history = []
                            try:
                                async for hist_msg in channel.history(limit=5, before=message):
                                    history.append(hist_msg)
                                history.reverse()
                                history.append(message) # Add current message
                            except Exception as e: 
                                print(f"Error fetching history for keyword discovery AI: {e}")
                                history.append(message)
                            
                            await send_ai_chat_response(
                                trigger_type="Discovery",
                                history=history,
                                user_message_content=message.content, # Pass raw user message
                                discovery_congrats_user=author,
                                keyword_triggered_rule_data=rule_data # Pass the specific rule's data
                                # preferred_model_id will be 'gemini_2_5_flash', system instruction handled by "Discovery" type
                            )
                            break # Keyword handled by discovery
                        else:
                            await log_error(guild, f"Failed to record discovery in DB for '{phrase_identifier}' by {author.name}.", ping_owner=True)
                        # No "continue" here needed if discovery attempt was made, as we break on success.
                        # If DB record failed, it will naturally go to the next rule or end the loop.
                    continue # Continue to next rule if discovery not possible in this context


                # Trigger for already discovered keywords
                # This check is now separate from the discovery block
                if keyword_data_cache[rule_id_str].get('discovered_by'): # Check again, might have just been discovered by a parallel process (unlikely with asyncio but defensive)
                    can_trigger_this_rule = False
                    trigger_context_server = ""
                    
                    if is_catercord and not is_restricted_keyword_discovery_channel_catercord:
                        can_trigger_this_rule = True
                        trigger_context_server = "Catercord (Public Channel)"
                    elif is_private_server and is_owner: # Owner can trigger anywhere in private server
                        can_trigger_this_rule = True
                        trigger_context_server = "Private Server (Owner Trigger)"
                    elif not is_catercord and not is_private_server and guild.me and guild.me.joined_at: # Other servers, if bot is full member
                        can_trigger_this_rule = True
                        trigger_context_server = f"Other Server ({guild.name})"
                    
                    if can_trigger_this_rule:
                        # REMOVED COOLDOWN CHECK - if you want it back, re-add it here.
                        print(f"Keyword TRIGGER: '{phrase_identifier}' by {author.name} in #{channel.name} ({guild.name} - {trigger_context_server})")
                        history = []
                        try:
                            async for hist_msg in channel.history(limit=5, before=message):
                                history.append(hist_msg)
                            history.reverse()
                            history.append(message) # Add current message
                        except Exception as e: 
                            print(f"Error fetching history for keyword AI: {e}")
                            history.append(message)
                        
                        await send_ai_chat_response(
                            trigger_type="Keyword",
                            history=history,
                            user_message_content=message.content, # Pass raw user message
                            keyword_triggered_rule_data=rule_data # Pass the specific rule's data
                            # preferred_model_id will be 'gemini_2_5_flash', system instruction handled by "Keyword" type
                        )
                        break # Keyword handled by trigger
            except Exception as e_rule:
                 await log_error(guild, f"Error processing keyword rule '{rule_data.get('phrase_identifier', rule_id_str if isinstance(rule_id_str, str) else 'UnknownID')}'", error=e_rule)

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

# NEW Command: Add Keyword (Owner Only)
@tree.command(name="addkeyword", description="[Owner Only] Add a new keyword rule to the database.")
@app_commands.describe(
    phrase_identifier="Unique identifier for this keyword (e.g., 'rule_linking').",
    inclusion_regex="Regex pattern to trigger this keyword (case-insensitive).",
    exclusion_regex="Optional regex pattern to PREVENT triggering (case-insensitive).",
    speciality="Brief topic/area the keyword relates to (for AI context).",
    instructions="Guidance for the AI on how to respond when triggered."
)
async def addkeyword(
    interaction: discord.Interaction,
    phrase_identifier: str,
    inclusion_regex: str,
    speciality: str,
    instructions: str,
    exclusion_regex: Optional[str] = None # Make exclusion optional
):
    guild = interaction.guild # For logging context mainly
    # --- Owner Check ---
    if interaction.user.id != OWNER_USER_ID:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    # --- Database Check ---
    if not await check_supabase_available(interaction):
        return # Helper handles response

    # --- Input Validation (Basic) ---
    if not phrase_identifier or not inclusion_regex or not speciality or not instructions:
        await interaction.response.send_message("❌ Missing required fields. Please provide all required inputs.", ephemeral=True)
        return

    # --- Regex Validation (Attempt Compile) ---
    try:
        re.compile(inclusion_regex, re.IGNORECASE)
        if exclusion_regex:
            re.compile(exclusion_regex, re.IGNORECASE)
    except re.error as e:
        await interaction.response.send_message(f"❌ Invalid Regex pattern provided: `{e}`", ephemeral=True)
        return

    # --- Defer Response ---
    await interaction.response.defer(thinking=True, ephemeral=True)

    # --- Prepare Data for Supabase ---
    data_to_insert = {
        "phrase_identifier": phrase_identifier.strip(),
        "inclusion_regex": inclusion_regex.strip(),
        "exclusion_regex": exclusion_regex.strip() if exclusion_regex else None,
        "speciality": speciality.strip(),
        "instructions": instructions.strip(),
        "is_enabled": True, # Default to enabled
        # 'discovered_by_user_id', 'discovered_at' will be NULL by default
        # 'id' (UUID) will be generated by Supabase
    }

    # --- Insert into Supabase ---
    try:
        await run_supabase_sync(
            lambda: supabase.table(KEYWORD_TABLE_NAME)
                           .insert(data_to_insert)
                           .execute()
        )

        await interaction.followup.send(f"✅ Keyword rule `{phrase_identifier}` added successfully!")
        await log_info(guild, f"Owner `{interaction.user}` added keyword: `{phrase_identifier}`.")

        # --- Reload cache after adding ---
        await log_info(guild, "Reloading keyword cache after addition...")
        await load_keyword_data(guild)

    except APIError as e:
        # Check for unique constraint violation on phrase_identifier (adjust constraint name if needed)
        if "23505" in str(e.code) and f'"{KEYWORD_TABLE_NAME}_phrase_identifier_key"' in str(e.message):
             await interaction.followup.send(f"❌ Failed: Phrase Identifier `{phrase_identifier}` already exists.")
             await log_info(guild, f"Keyword add failed: Identifier `{phrase_identifier}` already exists (User: {interaction.user}).")
        # Check for unique constraint on UUID (shouldn't happen with auto-generation)
        elif "23505" in str(e.code) and f'"{KEYWORD_TABLE_NAME}_pkey"' in str(e.message):
             await log_error(guild, f"Keyword add failed: UUID conflict (unexpected!) for `{phrase_identifier}`.", error=e, interaction=interaction, ping_owner=True)
             await interaction.followup.send(f"❌ Database Error: Unexpected primary key conflict.")
        else:
             await log_error(guild, f"Keyword add failed: Supabase API Error for `{phrase_identifier}`.", error=e, interaction=interaction)
             await interaction.followup.send(f"❌ Database API Error adding keyword: {e.message}")
    except (ConnectionError, Exception) as e:
        await log_error(guild, f"Keyword add failed: Unexpected Error for `{phrase_identifier}`.", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred while adding the keyword.")

@tree.command(name="message", description="Send a message as the bot, optionally using AI.")
@app_commands.describe(
    message_content="The message content. If AI is used, this becomes the prompt.",
    ai="[Optional] Have AI generate the message content? (Defaults to No)"
)
@app_commands.choices(ai=[
    app_commands.Choice(name="No", value="no"),
    app_commands.Choice(name="Yes", value="yes"),
])
async def message(
    interaction: discord.Interaction,
    message_content: str,
    ai: Optional[str] = "no"
):
    if not interaction.channel:
        await interaction.response.send_message("This command needs a channel context.", ephemeral=True)
        return

    target_channel: discord.abc.Messageable = interaction.channel
    guild = interaction.guild
    use_ai_generation = ai.lower() == "yes" if ai else False
    final_content_to_send = message_content

    bot_is_true_guild_member = guild and interaction.guild.me and interaction.guild.me.joined_at

    # Deferral Logic
    if guild and not bot_is_true_guild_member:
        await interaction.response.defer(thinking=True, ephemeral=False)
    else:
        await interaction.response.defer(thinking=True, ephemeral=True)

    if use_ai_generation:
        if not get_ai_model_priority_list():
            # Edit the correct response based on deferral type
            if guild and not bot_is_true_guild_member:
                 await interaction.edit_original_response(content="⚠️ AI models unavailable. Sending original content.")
            else:
                 await interaction.followup.send("⚠️ AI models unavailable. Sending original content.", ephemeral=True)
        else:
            try:
                # For /message, user's input is the direct prompt. System instruction makes the bot sound human.
                # Let's use 'gemini_2_5_flash' for potentially better quality for a direct command.
                preferred_model_for_message_cmd = 'gemini_2_5_flash'
                ai_system_instruction_str = get_prompt("HUMAN_SYSTEM_INSTRUCTION")

                # Typing indicator only makes sense if sending to a TextChannel
                typing_ctx = target_channel.typing() if isinstance(target_channel, discord.TextChannel) else contextlib.nullcontext()
                async with typing_ctx:
                    ai_response_raw = await get_ai_response(
                        prompt=message_content, # User's text is the prompt
                        system_instruction=ai_system_instruction_str,
                        preferred_model_id=preferred_model_for_message_cmd
                        # No history passed for this command unless you want to fetch it
                    )
                
                if ai_response_raw:
                    processed_response = ai_response_raw.strip()
                    # Further stripping of "Bot Name:" can be done here if needed, like in send_ai_chat_response
                    bot_name_prefix_lower = f"{bot.user.name.lower()}:" if bot.user and bot.user.name else "pingslave:"
                    if processed_response.lower().startswith(bot_name_prefix_lower):
                        processed_response = processed_response[len(bot_name_prefix_lower):].lstrip()
                    if len(processed_response) > 1950: processed_response = processed_response[:1947] + "..."
                    final_content_to_send = processed_response
                    await log_info(guild, f"User `{interaction.user}` used /message with AI. Generated: '{final_content_to_send[:100].strip()}...'")
                else: # AI returned no response
                    if guild and not bot_is_true_guild_member: await interaction.edit_original_response(content="⚠️ AI generated no response. Sending original content.")
                    else: await interaction.followup.send("⚠️ AI generated no response. Sending original content.", ephemeral=True)

            except Exception as ai_err:
                await log_error(guild, f"AI generation error for /message", error=ai_err, interaction=interaction)
                if guild and not bot_is_true_guild_member: await interaction.edit_original_response(content="⚠️ AI generation error. Sending original content.")
                else: await interaction.followup.send("⚠️ AI generation error. Sending original content.", ephemeral=True)
    
    # Send Message
    try:
        if guild and not bot_is_true_guild_member: # User-app context, edit the public deferred message
            response_text = final_content_to_send
            if use_ai_generation and ai_response_raw : response_text += " *(AI Generated)*" # Add if AI was used AND successful
            if len(response_text) > 1990 : response_text = response_text[:1987] + "..."
            await interaction.edit_original_response(content=response_text, view=None, embed=None)
            await log_info(guild, f"User `{interaction.user}` used /message (User-App) in {target_channel.mention if isinstance(target_channel, discord.TextChannel) else 'UnknownChannel'}. AI Used: {use_ai_generation}, AI Success: {bool(ai_response_raw if use_ai_generation else False)}.")
        else: # True guild member or DM, send new message and confirm ephemerally
            if isinstance(target_channel, discord.TextChannel) and guild and interaction.guild.me:
                if not target_channel.permissions_for(interaction.guild.me).send_messages:
                    await interaction.edit_original_response(content=f"❌ I don't have 'Send Messages' permission in {target_channel.mention}.", view=None, embed=None) # Edits ephemeral
                    return
            
            await target_channel.send(final_content_to_send)
            confirmation_msg = "✅ Message sent."
            if use_ai_generation and ai_response_raw: confirmation_msg += " (AI Generated)"
            await interaction.edit_original_response(content=confirmation_msg, view=None, embed=None) # Edits ephemeral "Thinking..."
            await log_info(guild, f"User `{interaction.user}` used /message (Full Member/DM) in {target_channel.mention if isinstance(target_channel, discord.TextChannel) else 'DM/Group'}. AI Used: {use_ai_generation}, AI Success: {bool(ai_response_raw if use_ai_generation else False)}.")

    except discord.Forbidden:
        # For ephemeral followup, as original response was likely the deferral
        await interaction.followup.send(f"❌ Failed to send message: I lack permissions in this channel/context.", ephemeral=True)
        await log_error(guild, "/message failed sending: Forbidden", interaction=interaction)
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Failed to send message: Discord API error. {e.text}", ephemeral=True)
        await log_error(guild, "/message failed sending: HTTP Exception", error=e, interaction=interaction)
    except Exception as e:
        await interaction.followup.send(f"❌ An unexpected error occurred while sending the message.", ephemeral=True)
        await log_error(guild, "/message failed sending: Unexpected error", error=e, interaction=interaction, ping_owner=True)

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

@tree.command(name="florr", description="Send a message with a custom name and a chosen Florr-themed profile picture.") # New name and description
@app_commands.describe( # Update parameter descriptions
    name="The name to display for the message (1-80 characters).",
    profile="Choose a profile picture from the Petals/Mobs list.", # Updated
    message_content="The content of the message to send."
)
@app_commands.autocomplete(profile=profile_pic_autocomplete) # Ensure 'profile' matches param name
# @app_commands.checks.bot_has_permissions(manage_webhooks=True) # REMOVE - Bot needs it implicitly, user doesn't grant it
async def florr( # RENAME function, and parameters
    interaction: discord.Interaction,
    name: str, # Renamed from custom_name
    profile: str, # Renamed from profile_picture
    message_content: str
):
    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("This command can only be used in text channels.", ephemeral=True)
        return

    target_channel: discord.TextChannel = interaction.channel
    guild = interaction.guild

    await interaction.response.defer(thinking=True, ephemeral=True)

    # Validate custom name (now 'name')
    cleaned_name = name.strip() # Use 'name'
    if not (1 <= len(cleaned_name) <= 80):
        await interaction.followup.send("❌ Custom name must be 1-80 characters long.", ephemeral=True)
        return
    disallowed_in_names = ["@", "#", ":", "```", "discord"]
    if any(disallowed in cleaned_name.lower() for disallowed in disallowed_in_names) or cleaned_name.lower() == "clyde":
        await interaction.followup.send(f"❌ The custom name '{cleaned_name}' contains disallowed characters or is a reserved name.", ephemeral=True)
        return

    # Parse profile value (use 'profile')
    if profile in ["error_no_images_loaded", "error_no_matches_found"]:
        await interaction.followup.send(f"❌ Profile picture selection error: {profile.replace('_', ' ').title()}", ephemeral=True)
        return
        
    try:
        folder_id, filename_with_ext = profile.split(":", 1) # Use 'profile'
    except ValueError:
        await interaction.followup.send("❌ Invalid profile picture selection format.", ephemeral=True)
        await log_error(guild, f"/florr: Invalid profile value format received: '{profile}'", interaction=interaction) # Log with /florr
        return

    if folder_id not in [PETALS_FOLDER_NAME, MOBS_FOLDER_NAME]:
        await interaction.followup.send("❌ Invalid folder specified in profile picture selection.", ephemeral=True)
        await log_error(guild, f"/florr: Unknown folder_id in profile value: '{folder_id}'", interaction=interaction) # Log with /florr
        return

    if not PROFILE_PIC_BASE_PATH:
        await interaction.followup.send("⚠️ Configuration error: Profile picture base path not set. Contact bot owner.", ephemeral=True)
        await log_error(guild, "/florr command failed: PROFILE_PIC_BASE_PATH is not set.", interaction=interaction, ping_owner=True) # Log with /florr
        return
        
    image_path = os.path.join(PROFILE_PIC_BASE_PATH, folder_id, filename_with_ext)

    chosen_avatar_bytes: Optional[bytes] = None
    try:
        if not os.path.exists(image_path):
            await interaction.followup.send(f"❌ Error: Selected image file not found on server: `{filename_with_ext}`. Try `/refresh_images` (if implemented) or contact admin.", ephemeral=True) # Suggest refresh_images if you add it
            await log_error(guild, f"/florr: Image file not found at '{image_path}'. Cache might be stale.", interaction=interaction, ping_owner=True) # Log with /florr
            return
        with open(image_path, "rb") as f:
            chosen_avatar_bytes = f.read()
    except Exception as e:
        await interaction.followup.send(f"❌ Error reading selected image file: `{filename_with_ext}`.", ephemeral=True)
        await log_error(guild, f"Error reading image file {image_path} for /florr", error=e, interaction=interaction) # Log with /florr
        return

    if not chosen_avatar_bytes:
        await interaction.followup.send(f"❌ Failed to load bytes for image: `{filename_with_ext}`.", ephemeral=True)
        return

    # Webhook Logic
    temp_webhook: Optional[discord.Webhook] = None
    try:
        # Bot permissions check (implicitly needed for webhook creation)
        if guild and interaction.guild.me:
            bot_perms = target_channel.permissions_for(interaction.guild.me)
            if not bot_perms.manage_webhooks:
                await interaction.followup.send(f"❌ I lack the 'Manage Webhooks' permission in {target_channel.mention} to send this message.", ephemeral=True)
                await log_error(guild, f"/florr failed: Bot missing manage_webhooks permission.", interaction=interaction)
                return

        temp_webhook = await target_channel.create_webhook(
            name=cleaned_name,
            avatar=chosen_avatar_bytes,
            reason=f"Temp webhook for /florr by {interaction.user}"
        )
        await temp_webhook.send(content=message_content, wait=True)
        await interaction.edit_original_response(content=f"✅ Message sent as '{cleaned_name}' with picture '{folder_id}/{filename_with_ext}'.")
        await log_info(guild, f"User `{interaction.user}` used /florr as '{cleaned_name}' (Pic: {folder_id}/{filename_with_ext}) in {target_channel.mention}. Msg: '{message_content[:50].strip()}...'")

    except discord.Forbidden: # This would typically be caught by the explicit bot_perms check above now
        await interaction.edit_original_response(content=f"❌ I lack permissions (likely 'Manage Webhooks') in {target_channel.mention}.")
        await log_error(guild, f"/florr failed: Forbidden.", interaction=interaction)
    except discord.HTTPException as e:
        error_text = f"Discord API Error: Failed to send. Code: {e.code}, Text: {e.text}"
        await interaction.edit_original_response(content=error_text[:1900])
        await log_error(guild, f"/florr failed: HTTP Exception", error=e, interaction=interaction)
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ An unexpected error occurred.")
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
