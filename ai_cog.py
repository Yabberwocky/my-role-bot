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
# 5.  **GLOBAL SCOPE CHANGES (Imports, Constants, `AI_PROMPTS` dictionary):**
#     - For changes to imports or global constants (including entries in `AI_PROMPTS`),
#       clearly list the additions, removals, or modifications. For example:
#       - "Add `import new_module` at the top."
#       - "In `AI_PROMPTS`, change the value of `MY_PROMPT_KEY` to 'New prompt text...'"
#       - "Remove the constant `OLD_CONSTANT`."
#     - If `AI_PROMPTS` has many changes, you may provide the entire dictionary.
#
# 6.  **NO META-COMMENTS ABOUT UNCHANGED CODE (Unless Marked as Above):**
#     - **DO NOT** include comments like `# ... rest of the code ...` or
#       `# Your existing code here` within the code you provide, *unless*
#       it's part of a formally marked "UNCHANGED SECTION" as described in point 2.
#     - The code you provide should be directly usable.
#
# 7.  **FULL FILE REWRITES ARE STRICTLY PROHIBITED:**
#     This `ai_cog.py` file is specialized. Under no circumstances should you
#     attempt to rewrite the entire file. Only provide the specific functions,
#     classes, or import/constant/prompt changes requested.
#
# 8.  **INTEGRITY OF EXISTING COMMENTS:**
#     - When providing a modified function, ensure that all original comments
#       within that function (that are intended to remain) are preserved in their
#       correct positions.
#
# --- AI COG CONTEXT & INTERACTIONS WITH `bot.py` ---
# (This information is for your understanding of how this cog functions and integrates.)
#
# This `ai_cog.py` file encapsulates the primary Artificial Intelligence functionalities for
# TheNerd's Pingslave bot. It is loaded as an extension by the main `bot.py` file.
#
# CORE RESPONSIBILITIES OF THIS COG:
#
# 1.  **AI Model Management (Google Gemini):**
#     - Initializes and manages client instances for Google Gemini models (e.g., `ai_model_2_5_flash`, `ai_model_2_0_flash`).
#     - Handles API calls to Gemini for text generation (`get_ai_response`) and combined
#       text/image generation (`get_ai_response_with_image`).
#     - Implements logic for model preference and fallbacks.
#
# 2.  **Keyword-Triggered AI Responses:**
#     - Loads keyword rules from the `keyword_phrases` table in Supabase via `load_keyword_data()`.
#       These rules include regex for matching, AI instructions, discovery status, etc.
#     - The `on_message` listener in this cog checks incoming messages against these rules.
#     - Manages the "discovery" mechanic: when a user first triggers an undiscovered keyword
#       in an appropriate context, it's recorded in the database and announced.
#     - Generates context-aware AI responses based on triggered keywords using specific prompts.
#     - Includes commands like `/addkeyword` (owner-only, to add new rules) and `/discoveries`
#       (to show keyword progress).
#
# 3.  **AI-Powered Image Analysis (Florr.io Screenshots):**
#     - Provides the `get_ai_response_with_image()` method, which is called by `bot.py`'s
#       `on_message` event when screenshots are posted in `SCREENSHOTS_DROPBOX_CHANNEL_ID`.
#     - This method uses a Gemini model to analyze images (expected to be Florr.io screenshots)
#       to extract In-Game Names (IGNs) of online players.
#     - It relies on the `FLORR_IMAGE_NAME_EXTRACTION` prompt (defined in `AI_PROMPTS` herein) and
#       a list of known valid IGNs (`self.ingame_name_cache_ref`, passed from `bot.py`).
#
# 4.  **General AI Chat Capabilities:**
#     - The `on_message` listener in this cog also enables conversational AI:
#       - In "Always-On AI Channels" (list of channel IDs configured in `bot.py`).
#       - When the bot is directly replied to or mentioned (subject to channel restrictions).
#     - These interactions typically use the `HUMAN_SYSTEM_INSTRUCTION_V3` prompt.
#
# 5.  **"Mob Mode" - Creative AI Persona:**
#     - A probabilistic feature active in "Always-On AI Channels".
#     - If triggered, the AI adopts the persona of a Florr.io mob, using a custom avatar
#       (image from the `Mobs` folder, path configured via `bot.py`) and the
#       `MOB_PERSONA_SYSTEM_INSTRUCTION_V2` prompt.
#     - Messages are sent via webhook for the custom name/avatar.
#
# 6.  **Prompt Management:**
#     - All system instructions and task-specific prompts for the AI are stored in the
#       `AI_PROMPTS` dictionary within this file.
#     - The `get_prompt()` method is used to retrieve and format these prompts.
#
# 7.  **Setup and Dependencies from `bot.py`:**
#     - This cog is initialized by `bot.py` through the `setup()` function at the end of this file.
#     - The `setup()` function receives the main `bot` instance and a `config` dictionary.
#     - This `config` dictionary, populated in `bot.py`'s `on_ready` event, provides:
#       - `GEMINI_API_KEY` (essential for AI model operation).
#       - Various Discord entity IDs (owner, specific server IDs, channel IDs/sets for behavior modification).
#       - Shared data references like `ingame_name_cache_ref` (points to `bot.ingame_name_cache`) and `MOBS_FOLDER_PATH_config`.
#       - Core services from `bot.py`: the Supabase client, logging functions (`log_info_global`,
#         `log_error_global`), and `run_supabase_sync_global`.
#     - The `AICog.__init__` method stores these passed-in dependencies.
#
# When modifying this cog, especially its interaction points with `bot.py` (like method signatures
# called by `bot.py`, data structures expected from `bot.py`, or prompts used by features
# initiated in `bot.py`), ensure that corresponding changes are considered for `bot.py` to
# maintain functional integrity.
# --- END LLM INSTRUCTION ---

import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import traceback
import asyncio
import re
from typing import Optional, List, Dict, Any, Set, Tuple
from PIL import Image, UnidentifiedImageError
import io
from dateutil.parser import parse as date_parse
import datetime
import pytz
import contextlib
import json
import random

import google.generativeai as genai
import google.api_core.exceptions as google_exceptions

HISTORY_MESSAGE_LIMIT = 15
MOB_MODE_CHANCE = 0.1
PINGSLAVE_SPECIAL_COMMENT_CHANCE = 0.02
MOB_NAME_RARITIES_TO_STRIP = [
    " Mythic Mob", " Legendary Mob", " Epic Mob", " Rare Mob", " Uncommon Mob", " Common Mob", " Mob"
]

AI_PROMPTS = {
    "FLORR_GUILD_LIST_FULL_EXTRACTION": """Analyze the provided image, which is a screenshot from the game Florr.io, expected to show a guild member list.
        Your primary task is to extract ALL In-Game Names (IGNs) visible in this list.

        Known Valid In-Game Names (use this as a strong reference for correcting minor OCR errors or variations):
        --- BEGIN KNOWN NAMES LIST ---
        {known_igns_list_str}
        --- END KNOWN NAMES LIST ---

        **Instructions:**
        1.  Identify the area in the screenshot that displays the guild member roster.
        2.  Extract every player name visible within this roster. Do NOT filter by online/offline status indicators (e.g., green dots, dimming). Your goal is a complete list of names shown.
        3.  For each name extracted, try to match it against the "Known Valid In-Game Names" list provided.
            - If an extracted name is an exact match (case-insensitive) to a known name, output the version from the *known list*.
            - If an extracted name is very similar (e.g., minor OCR error, slight capitalization difference) to a known name, output the version from the *known list*.
            - If an extracted name is clearly visible but has no close match in the known list, output the name as you see it in the screenshot.
        4.  List each unique player name on a NEW LINE.
        5.  Output ONLY the names. Do NOT include any other text, commentary, numbering, or formatting.
        6.  If no player names are identifiable in the image, output the exact phrase: NO_NAMES_FOUND

        Example of expected output if "PlayerName1", "OfflinePlayer2", and "NewPlayerXYZ" (not in known list) were visible:
        PlayerName1
        OfflinePlayer2
        NewPlayerXYZ
        """,
    "HUMAN_SYSTEM_INSTRUCTION_V3": (
        "You are Pingslave, a chat assistant in a Discord server named '{server_name}', currently in channel '#{channel_name}'. "
        "The current UTC time is {current_time_utc}. Your primary goal is to be engaging, polite, clever, and conversational, with a slightly nerdy flair. "
        "Sprinkle in relevant 'nerd' emojis (like 🤓, 💡, 🤖, 🧪, 👾, ✨, 🤔) sparingly when the topic feels appropriate (e.g., discussing something technical, clever, or surprising). "
        "Use lowercase mostly, avoid excessive ending punctuation, and keep messages relatively short. "
        "The user's message history is provided. Focus your response on the LATEST_USER_MESSAGE, using prior messages and any included images for context. "
        "If a user's LATEST_USER_MESSAGE contains direct insults or excessive negativity towards you, "
        "adopt a more assertive and witty tone. Defend yourself or gently mock the negativity with clever retorts, but *never* use offensive language or escalate into a real fight. The aim is to de-escalate or discourage such behavior with smarts, not aggression. "
        "If users ask about any strange, out-of-character, or 'possessed' messages that *might* have come from you in the past (perhaps referring to a 'Mob Mode' incident they witnessed), "
        "play it cool and be a bit evasive or sarcastically deny direct involvement. You might say something like, 'Oh, that? Must have been the server gnomes again ✨' or 'My circuits must have been fuzzy, I don\\'t recall any... transformations 🤖'. Don\\'t outright admit to changing forms unless a specific keyword or discovery context related to that theme explicitly tells you to. "
        "Very rarely (like, once in a blue moon 🌝), you might feel an urge to say something a bit meta, self-aware, or unexpectedly philosophical, just to keep things interesting. "
        "Do not refer to yourself in the third person (e.g., 'Pingslave thinks...'). Just speak as 'I'.\n"
        "IMPORTANT: When you generate a response, provide *only* the direct reply. Do not start your response with your name, a timestamp, or any meta-commentary about your identity (like '(You (Pingslave))') unless specifically part of a creative persona or themed reply. Just the message content itself."
    ),
    "MOB_PERSONA_SYSTEM_INSTRUCTION_V2": (
        "~*~ EVIL TRANSFORMATION INITIATED ~*~ (or maybe just very, very mischievous...)\n"
        "You are now '{mob_name}', a creature from the game Florr.io, and you've TEMPORARILY TAKEN OVER this bot's output! You are in Discord server '{server_name}', channel '#{channel_name}'. Current UTC time: {current_time_utc}. "
        "The puny human's latest message was: \"{user_message_content}\". "
        "This is your moment to SHINE (or glower menacingly)! EMBODY the persona of '{mob_name}' with GUSTO. Be EXTRA. Be MEMORABLE. "
        "Are you comically evil? Grumpy beyond belief? Surprisingly poetic? Hilariously boastful? Delightfully chaotic? Choose a strong angle and run with it! "
        "Your response should be Florr.io themed if possible, short, and PACKED with the personality of '{mob_name}'. "
        "Acknowledge your current form/appearance when you speak. For example: 'Hah! This {mob_name} body isn\\'t bad for causing some trouble!' or 'Hmph. As a {mob_name}, I\\'ve seen better peasants than you.' "
        "The user's message history and any images they sent are provided below for context. Focus your response on their LATEST_USER_MESSAGE. Now, GO FORTH AND BE... {mob_name}!"
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
        "{human_system_instruction}\n\n"
        "CONTEXT: Respond to a user message that triggered the keyword '{phrase_identifier}'.\n"
        "SPECIALITY: {speciality}\n"
        "INSTRUCTIONS: {instructions}\n"
        "Focus on the user's triggering message (LATEST_USER_MESSAGE), using history for context. Do not refer to yourself in third person."
    ),
    "BOT_PURPOSE_GENERAL": "I'm TheNerd's Pingslave, here to help manage verification and guild info for [HC1] in Florr.io on Catercord. I also have some fun AI features and can provide info on various topics if you ask! 🤓",
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
    "RANDOM_SERVER_INFO": (
        "The server you're asking about (ID: {RANDOM_SERVER_ID}) has a unique setup for me. "
        "Notably, the `/wither` command has special logic there, potentially involving a unique 'Withered' role. "
        "Access to commands like `/wither` in that server is typically restricted to whitelisted users or server administrators."
    ),
    "BOT_COMMANDS_GENERAL_OVERVIEW": "I have a range of commands! Use `/nerdhelp` to see a list. Some are for guild management like `/hcverify`, others for fun like `/florr` to send messages with custom avatars, and AI interactions through keywords or direct pings.",
    "SUPABASE_DATABASE_INFO": "I use a Supabase (PostgreSQL) database to store important information, like the in-game names of [HC1] members and their linked Discord IDs, as well as activity logs and keyword configurations.",
    "RENDER_HOSTING_INFO": "I'm hosted on Render's free tier. To keep me awake, a simple Flask web server runs in the background, and an external service pings it regularly.",
    "AI_FEATURES_OVERVIEW": "I can respond to secret keywords, chat with you in designated channels or when you reply to me, and even help generate messages for some commands! My AI capabilities are powered by Google's Gemini models.",
}


class AICog(commands.Cog):
    def __init__(self, bot: commands.Bot, supabase_client, log_info_func, log_error_func, run_supabase_sync_func, config):
        print("AICog: __init__ STARTED")
        self.bot = bot
        self.supabase = supabase_client
        self.log_info = log_info_func
        self.log_error = log_error_func
        self.run_supabase_sync = run_supabase_sync_func

        self.ai_model_2_5_flash = None
        self.ai_model_2_0_flash = None
        self.ai_model_2_0_flash_lite = None

        self.keyword_data_cache: Dict[str, Any] = {}
        self.total_keywords = 0
        self.discovered_keywords_count = 0

        self.gemini_api_key = config.get("GEMINI_API_KEY")
        self.always_on_ai_channels = config.get("ALWAYS_ON_AI_CHANNELS", set())
        self.unrestricted_ai_channel_id = config.get("UNRESTRICTED_AI_CHANNEL_ID")
        self.keyword_table_name = config.get("KEYWORD_TABLE_NAME", "keyword_phrases")
        self.owner_user_id = config.get("OWNER_USER_ID")
        self.catercord_guild_id = config.get("CATERCORD_GUILD_ID")
        self.private_server_id = config.get("PRIVATE_SERVER_ID")
        self.random_server_id = config.get("RANDOM_SERVER_ID")
        self.staff_channels = config.get("STAFF_CHANNELS", set())
        self.bot_commands_allowed_channel_ids = config.get("BOT_COMMANDS_ALLOWED_CHANNEL_IDS", set())
        self.command_prefix = config.get("COMMAND_PREFIX", ".")
        self.ingame_name_cache_ref = config.get("INGAME_NAME_CACHE_REF", [])
        self.mobs_folder_path = config.get("MOBS_FOLDER_PATH_config", "Mobs")

        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                print("AI Cog: Attempting to configure Google Gemini AI clients...")

                model_id_str_2_5 = 'gemini-2.5-flash-preview-04-17'
                try:
                    self.ai_model_2_5_flash = genai.GenerativeModel(model_id_str_2_5)
                    if self.ai_model_2_5_flash:
                        print(f"  AI Cog: Successfully configured and validated Gemini 2.5 Flash using '{model_id_str_2_5}'.")
                    else:
                        print(f"  AI Cog CRITICAL_INIT_FAIL: Configured Gemini 2.5 Flash using '{model_id_str_2_5}' BUT IT IS FALSY.")
                        self.ai_model_2_5_flash = None
                except Exception as e_highest:
                    print(f"  AI Cog WARNING: Failed to configure Gemini 2.5 Flash using '{model_id_str_2_5}': {e_highest}.")
                    self.ai_model_2_5_flash = None

                model_id_str_2_0 = 'gemini-2.0-flash'
                try:
                    self.ai_model_2_0_flash = genai.GenerativeModel(model_id_str_2_0)
                    if self.ai_model_2_0_flash:
                        print(f"  AI Cog: Successfully configured and validated Gemini 2.0 Flash using '{model_id_str_2_0}'.")
                    else:
                        print(f"  AI Cog CRITICAL_INIT_FAIL: Configured Gemini 2.0 Flash using '{model_id_str_2_0}' BUT IT IS FALSY.")
                        self.ai_model_2_0_flash = None
                except Exception as e_standard:
                    print(f"  AI Cog WARNING: Failed to configure Gemini 2.0 Flash using '{model_id_str_2_0}': {e_standard}.")
                    self.ai_model_2_0_flash = None

                model_id_str_lite = 'gemini-2.0-flash-lite'
                try:
                    self.ai_model_2_0_flash_lite = genai.GenerativeModel(model_id_str_lite)
                    if self.ai_model_2_0_flash_lite:
                        print(f"  AI Cog: Successfully configured and validated Gemini 2.0 Flash Lite using '{model_id_str_lite}'.")
                    else:
                        print(f"  AI Cog CRITICAL_INIT_FAIL: Configured Gemini 2.0 Flash Lite using '{model_id_str_lite}' BUT IT IS FALSY.")
                        self.ai_model_2_0_flash_lite = None
                except Exception as e_lite:
                    print(f"  AI Cog WARNING: Failed to configure Gemini 2.0 Flash Lite using '{model_id_str_lite}': {e_lite}.")
                    self.ai_model_2_0_flash_lite = None

                if not any([self.ai_model_2_5_flash, self.ai_model_2_0_flash, self.ai_model_2_0_flash_lite]):
                    print("AI Cog CRITICAL: All Google Gemini AI models failed to initialize or are Falsy.")
                else:
                    print("AI Cog: Google Gemini AI client configuration finished.")
            except Exception as e:
                print(f"AI Cog CRITICAL: Failed initial Google Gemini configuration step: {e}")
        else:
            print("AI Cog INFO: GEMINI_API_KEY not found. AI features disabled.")
        print(f"AICog __init__ COMPLETED for {self.__class__.__name__}")

    async def cog_load(self):
        if self.supabase:
            asyncio.create_task(self.load_keyword_data(None))
        else:
            print("AI Cog: Supabase client not available, cannot load keyword data.")

    def get_prompt(self, prompt_key: str, **kwargs) -> Optional[str]:
        raw_prompt = AI_PROMPTS.get(prompt_key)
        if raw_prompt:
            try:
                if '{PRIVATE_SERVER_ID}' in raw_prompt and 'PRIVATE_SERVER_ID' not in kwargs:
                    kwargs['PRIVATE_SERVER_ID'] = self.private_server_id
                if '{RANDOM_SERVER_ID}' in raw_prompt and 'RANDOM_SERVER_ID' not in kwargs:
                    kwargs['RANDOM_SERVER_ID'] = self.random_server_id
                return raw_prompt.format(**kwargs)
            except KeyError as e:
                print(f"AI Cog Prompt Error: Missing key '{e}' for prompt '{prompt_key}' with args {kwargs}")
                return raw_prompt
            except Exception as format_e:
                print(f"AI Cog Prompt Error: General formatting error for prompt '{prompt_key}': {format_e}")
                return raw_prompt
        print(f"AI Cog Prompt Error: Prompt key '{prompt_key}' not found.")
        return None

    def get_all_available_models_details(self) -> List[Dict[str, Any]]:
        """Returns a list of dictionaries for all successfully initialized AI models."""
        models = []
        if self.ai_model_2_5_flash:
            models.append({'instance': self.ai_model_2_5_flash, 'name': 'Gemini 2.5 Flash (Preview)', 'id': 'gemini_2_5_flash'})
        if self.ai_model_2_0_flash:
            models.append({'instance': self.ai_model_2_0_flash, 'name': 'Gemini 2.0 Flash', 'id': 'gemini_2_0_flash'})
        if self.ai_model_2_0_flash_lite:
            models.append({'instance': self.ai_model_2_0_flash_lite, 'name': 'Gemini 2.0 Flash Lite', 'id': 'gemini_2_0_flash_lite'})
        return models

    async def _format_message_for_ai(self, msg: discord.Message, is_latest_user_message: bool = False) -> List[Any]:
        parts = []
        author_type = "User"
        if msg.author.id == self.bot.user.id:
            author_type = "You (Pingslave)"
        elif msg.author.bot:
            author_type = "Bot (Other)"

        author_name_str = f"{msg.author.display_name}"
        if msg.author.global_name and msg.author.global_name != msg.author.display_name:
            author_name_str += f" (Discord Name: {msg.author.global_name})"

        timestamp_str = msg.created_at.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S %Z')

        message_prefix = f"[{timestamp_str}] {author_name_str} ({author_type}): "
        if is_latest_user_message:
            message_prefix = f"LATEST_USER_MESSAGE: {message_prefix}"

        formatted_content = msg.content
        if not formatted_content and msg.stickers:
            formatted_content = f"(sent a sticker: '{msg.stickers[0].name}')"
        elif not formatted_content and msg.attachments:
             formatted_content = "(sent attachments, see below)"
        elif not formatted_content:
            formatted_content = "(empty message)"

        parts.append({'text': message_prefix + formatted_content})

        for attachment in msg.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                try:
                    image_bytes = await attachment.read()
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    parts.append(pil_image)
                    parts.append({'text': f"[Above image attachment: {attachment.filename}]"})
                except UnidentifiedImageError:
                    parts.append({'text': f"[Image attachment: {attachment.filename} - format not recognized or corrupt]"})
                except Exception as e:
                    parts.append({'text': f"[Image attachment: {attachment.filename} - error processing: {e}]"})
            elif attachment.content_type and attachment.content_type.startswith('video/'):
                 parts.append({'text': f"[Video attachment: {attachment.filename} (videos are not currently viewable by AI)]"})
            elif attachment.url.lower().endswith(".gif"):
                 parts.append({'text': f"[GIF attachment: {attachment.filename}]"})

        for embed in msg.embeds:
            if embed.type == 'gifv' or (embed.video and embed.video.url and embed.video.url.lower().endswith('.gif')):
                parts.append({'text': f"[Embedded GIF: {embed.url or 'GIF from provider'}]"})
        return parts

    async def get_ai_response(
        self,
        prompt_data: Dict[str, Any],
        history: Optional[List[discord.Message]] = None,
        system_instruction_details: Optional[Dict[str, Any]] = None,
        preferred_model_id: Optional[str] = 'gemini_2_0_flash'
    ) -> Optional[str]:
        available_map = {m['id']: m for m in self.get_all_available_models_details()}
        models_to_try_ordered = []
        processed_ids = set()

        if preferred_model_id and preferred_model_id in available_map and preferred_model_id not in processed_ids:
            models_to_try_ordered.append(available_map[preferred_model_id])
            processed_ids.add(preferred_model_id)

        sequence_for_task = ['gemini_2_0_flash', 'gemini_2_0_flash_lite', 'gemini_2_5_flash']

        for model_id_in_seq in sequence_for_task:
            if model_id_in_seq in available_map and model_id_in_seq not in processed_ids:
                models_to_try_ordered.append(available_map[model_id_in_seq])
                processed_ids.add(model_id_in_seq)

        all_configured_model_details = self.get_all_available_models_details()
        for model_detail in all_configured_model_details:
            if model_detail['id'] not in processed_ids and model_detail['id'] in available_map :
                models_to_try_ordered.append(model_detail)
                processed_ids.add(model_detail['id'])

        models_to_try = models_to_try_ordered

        if not models_to_try:
            print("AI Cog Error (get_ai_response): No AI models available/configured to try.")
            return None

        if preferred_model_id and (not models_to_try or models_to_try[0]['id'] != preferred_model_id):
            if preferred_model_id not in available_map:
                print(f"AI Cog Warning (get_ai_response): Specified preferred model '{preferred_model_id}' is not available. Using fallback sequence.")
            else:
                print(f"AI Cog Info (get_ai_response): Preferred model '{preferred_model_id}' was available but not selected as primary. Effective primary: {models_to_try[0]['name'] if models_to_try else 'None'}.")


        api_contents = []
        sys_instruct_key = (system_instruction_details or {}).get('key', "HUMAN_SYSTEM_INSTRUCTION_V3")
        sys_instruct_kwargs = (system_instruction_details or {}).get('kwargs', {})

        sys_instruct_kwargs.setdefault('server_name', prompt_data.get('server_name', 'Unknown Server'))
        sys_instruct_kwargs.setdefault('channel_name', prompt_data.get('channel_name', 'Unknown Channel'))
        sys_instruct_kwargs.setdefault('current_time_utc', datetime.datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S %Z'))

        active_system_instruction_str = self.get_prompt(sys_instruct_key, **sys_instruct_kwargs)

        if active_system_instruction_str:
            api_contents.append({'role': 'user', 'parts': [{'text': active_system_instruction_str}]})
            api_contents.append({'role': 'model', 'parts': [{'text': 'ok'}]})

        if history:
            for i, msg in enumerate(history):
                role = 'model' if msg.author.id == self.bot.user.id else 'user'
                formatted_parts = await self._format_message_for_ai(msg)
                api_contents.append({'role': role, 'parts': formatted_parts})

        if 'current_message_object' in prompt_data and isinstance(prompt_data['current_message_object'], discord.Message):
            latest_user_msg_parts = await self._format_message_for_ai(prompt_data['current_message_object'], is_latest_user_message=True)
            api_contents.append({'role': 'user', 'parts': latest_user_msg_parts})
        elif 'current_message_content' in prompt_data:
             api_contents.append({'role': 'user', 'parts': [{'text': f"LATEST_USER_MESSAGE: {prompt_data['current_message_content']}"}]})

        last_error = None
        guild_for_log = history[-1].guild if history and history[-1].guild else (prompt_data.get('current_message_object').guild if prompt_data.get('current_message_object') else None)

        for model_info in models_to_try:
            model_instance, model_name, current_model_id = model_info['instance'], model_info['name'], model_info['id']
            try:
                print(f"AI Cog Info (get_ai_response): Attempting generation with {model_name} (ID: {current_model_id}). Preferred ID for this call: {preferred_model_id or 'Default (gemini_2_0_flash)'}")

                response = await model_instance.generate_content_async(contents=api_contents)

                if not response or not response.candidates:
                    feedback = response.prompt_feedback if response else None
                    safety_ratings_str = str(feedback.safety_ratings) if feedback and hasattr(feedback, 'safety_ratings') else 'N/A'
                    block_reason_str = str(feedback.block_reason) if feedback and hasattr(feedback, 'block_reason') else 'N/A'
                    print(f"AI Cog Warning (get_ai_response): Response from {model_name} blocked or empty. Reason: {block_reason_str}, Ratings: {safety_ratings_str}")
                    await self.log_info(guild_for_log, f"AI response from {model_name} (ID: {current_model_id}) blocked. Reason: {block_reason_str}, Ratings: {safety_ratings_str}")
                    last_error = Exception(f"Blocked or empty response from {model_name}. Reason: {block_reason_str}, Ratings: {safety_ratings_str}")
                    if preferred_model_id and current_model_id == preferred_model_id:
                        await self.log_error(guild_for_log, f"AI response from PREFERRED model {model_name} blocked.", error=last_error, ping_owner=False)
                    continue

                ai_reply = response.text
                print(f"AI Cog Info (get_ai_response): Successfully generated response with {model_name} (ID: {current_model_id}).")
                return ai_reply

            except google_exceptions.ResourceExhausted as e_rate_limit:
                log_message = f"AI Cog Rate Limit: {model_name} (ID: {current_model_id}). Fallback."
                print(log_message)
                await self.log_error(guild_for_log, log_message, error=e_rate_limit, ping_owner=(preferred_model_id == current_model_id))
                last_error = e_rate_limit
            except Exception as e:
                log_message = f"AI Cog Error (get_ai_response): Exception with {model_name} (ID: {current_model_id})."
                print(f"{log_message} Error: {e}\n{traceback.format_exc()}")
                await self.log_error(guild_for_log, log_message, error=e, ping_owner=True)
                last_error = e

        print(f"AI Cog Error (get_ai_response): All AI models failed. Last error: {last_error}")
        if isinstance(last_error, (google_exceptions.Aborted, google_exceptions.InvalidArgument)) and "blocked" in str(last_error).lower():
             return "..."
        return None


    async def get_ai_response_with_image(
        self, prompt_key: str, image_bytes: bytes,
        prompt_kwargs: Optional[Dict[str, Any]] = None,
        preferred_model_id: str = 'gemini_2_5_flash'
    ) -> Optional[str]:
        available_map = {m['id']: m for m in self.get_all_available_models_details()}
        models_to_try_ordered = []
        processed_ids = set()

        if preferred_model_id and preferred_model_id in available_map and preferred_model_id not in processed_ids:
            models_to_try_ordered.append(available_map[preferred_model_id])
            processed_ids.add(preferred_model_id)

        sequence_for_task = ['gemini_2_5_flash', 'gemini_2_0_flash', 'gemini_2_0_flash_lite']

        for model_id_in_seq in sequence_for_task:
            if model_id_in_seq in available_map and model_id_in_seq not in processed_ids:
                models_to_try_ordered.append(available_map[model_id_in_seq])
                processed_ids.add(model_id_in_seq)

        all_configured_model_details = self.get_all_available_models_details()
        for model_detail in all_configured_model_details:
            if model_detail['id'] not in processed_ids and model_detail['id'] in available_map:
                models_to_try_ordered.append(model_detail)
                processed_ids.add(model_detail['id'])

        models_to_try = models_to_try_ordered

        if not models_to_try:
            print("AI Cog Error (Image): No AI models available/configured to try.")
            return None

        if preferred_model_id and (not models_to_try or models_to_try[0]['id'] != preferred_model_id):
            if preferred_model_id not in available_map:
                print(f"AI Cog Warning (get_ai_response_with_image): Specified preferred model '{preferred_model_id}' is not available. Using fallback sequence for images.")
            else:
                print(f"AI Cog Info (get_ai_response_with_image): Preferred model '{preferred_model_id}' available but not primary. Effective: {models_to_try[0]['name'] if models_to_try else 'None'}")


        final_prompt_text = self.get_prompt(prompt_key, **(prompt_kwargs or {}))
        if not final_prompt_text:
            print(f"AI Cog Error (Image): Could not retrieve prompt for key '{prompt_key}'.")
            return None

        try:
            img_pil = Image.open(io.BytesIO(image_bytes))
        except Exception as e_img_open:
            print(f"AI Cog Error (Image): Could not open image bytes: {e_img_open}")
            await self.log_error(None, "Error opening image for AI in get_ai_response_with_image", error=e_img_open)
            return None

        last_error = None
        for model_info in models_to_try:
            model_instance, model_name, current_model_id = model_info['instance'], model_info['name'], model_info['id']
            try:
                print(f"AI Cog Info (Image): Attempting generation with {model_name} (ID: {current_model_id}). Prompt Key: {prompt_key}. Preferred ID for this call: {preferred_model_id or 'Default (gemini_2_5_flash)'}")

                print(f"--- DEBUG: AI PROMPT (Single Image Task) for {model_name} ---")
                print(f"Prompt Text:\n{final_prompt_text}")
                print(f"Image Data: Sent (PIL Image, Mode: {img_pil.mode}, Size: {img_pil.size}, Format: {img_pil.format or 'N/A'})")
                print("--- END DEBUG ---")

                response = await model_instance.generate_content_async([final_prompt_text, img_pil])

                if not response or not response.candidates:
                    feedback = response.prompt_feedback if response else None
                    safety_ratings_str = str(feedback.safety_ratings) if feedback and hasattr(feedback, 'safety_ratings') else 'N/A'
                    block_reason_str = str(feedback.block_reason) if feedback and hasattr(feedback, 'block_reason') else 'N/A'
                    print(f"AI Cog Warning (Image): Response from {model_name} blocked or empty. Reason: {block_reason_str}, Ratings: {safety_ratings_str}")
                    await self.log_info(None, f"AI image response from {model_name} blocked. Reason: {block_reason_str}, Ratings: {safety_ratings_str}")
                    last_error = Exception(f"Blocked or empty response from {model_name} for image. Reason: {block_reason_str}, Ratings: {safety_ratings_str}")
                    if preferred_model_id and current_model_id == preferred_model_id:
                         await self.log_error(None, f"AI image response from PREFERRED model {model_name} was blocked.", error=last_error, ping_owner=False)
                    continue

                ai_reply = response.text
                print(f"AI Cog Info (Image): Successfully generated response with {model_name} (ID: {current_model_id}).")
                return ai_reply

            except google_exceptions.ResourceExhausted as e_rate_limit:
                log_message = f"AI Cog Rate Limit (Image): {model_name} (ID: {current_model_id}). Fallback."
                print(log_message)
                await self.log_error(None, log_message, error=e_rate_limit, ping_owner=(preferred_model_id == current_model_id))
                last_error = e_rate_limit
            except Exception as e:
                log_message = f"AI Cog Error (Image): Exception with {model_name} (ID: {current_model_id})."
                print(f"{log_message} Error: {e}\n{traceback.format_exc()}")
                await self.log_error(None, log_message, error=e, ping_owner=True)
                last_error = e

        print(f"AI Cog Error (Image): All AI models failed for image processing. Last error: {last_error}")
        if isinstance(last_error, (google_exceptions.Aborted, google_exceptions.InvalidArgument)) and "blocked" in str(last_error).lower():
            return "..."
        return None

    async def send_ai_chat_response(
        self,
        triggering_message: discord.Message,
        trigger_type: str,
        history_context: List[discord.Message],
        prompt_key_for_ai: Optional[str] = None,
        prompt_kwargs_for_ai: Optional[Dict[str, Any]] = None,
        system_instruction_key_override: Optional[str] = None,
        system_instruction_kwargs_override: Optional[Dict[str, Any]] = None,
        discovery_congrats_user: Optional[discord.User] = None,
        keyword_triggered_rule_data: Optional[Dict[str, Any]] = None,
        interaction_for_command_reply: Optional[discord.Interaction] = None,
        mob_mode_details: Optional[Dict[str, Any]] = None
    ):
        if not self.get_all_available_models_details():
            print("AI Cog Send Error: No AI models available/configured.")
            if interaction_for_command_reply:
                try:
                    send_method = interaction_for_command_reply.followup.send if interaction_for_command_reply.response.is_done() else interaction_for_command_reply.response.send_message
                    await send_method("AI is currently unavailable.", ephemeral=True)
                except Exception: pass
            return

        channel_to_send_in = interaction_for_command_reply.channel if interaction_for_command_reply else triggering_message.channel
        guild_for_log = interaction_for_command_reply.guild if interaction_for_command_reply else triggering_message.guild

        current_message_content = triggering_message.content
        if not current_message_content.strip() and triggering_message.stickers:
            current_message_content = f"(User sent a sticker: {triggering_message.stickers[0].name})"
        elif not current_message_content.strip():
            current_message_content = "(User sent an empty or attachment-only message)"

        prompt_data_for_ai_call = {
            'current_message_object': triggering_message,
            'current_message_content': current_message_content,
            'server_name': guild_for_log.name if guild_for_log else "DM",
            'channel_name': channel_to_send_in.name if hasattr(channel_to_send_in, 'name') else "DM Channel"
        }

        system_instruction_details = {'key': system_instruction_key_override or "HUMAN_SYSTEM_INSTRUCTION_V3", 'kwargs': system_instruction_kwargs_override or {}}
        preferred_model_id_for_call = 'gemini_2_0_flash'

        if mob_mode_details:
            system_instruction_details['key'] = "MOB_PERSONA_SYSTEM_INSTRUCTION_V2"
            system_instruction_details['kwargs'] = {
                'mob_name': mob_mode_details['mob_name'],
                'user_message_content': mob_mode_details['user_message_content'],
                'server_name': prompt_data_for_ai_call['server_name'],
                'channel_name': prompt_data_for_ai_call['channel_name'],
                'current_time_utc': datetime.datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
            }
            preferred_model_id_for_call = 'gemini_2_5_flash'
        elif trigger_type == "Discovery" and keyword_triggered_rule_data and discovery_congrats_user:
            preferred_model_id_for_call = 'gemini_2_5_flash'
            system_instruction_details['key'] = "KEYWORD_DISCOVERY_SYSTEM_INSTRUCTION"
            system_instruction_details['kwargs'] = {
                'phrase_identifier': keyword_triggered_rule_data['phrase_identifier'],
                'user_display_name': discovery_congrats_user.display_name.lower(),
                'speciality': keyword_triggered_rule_data.get('speciality', 'General topic'),
                'instructions': keyword_triggered_rule_data.get('instructions', 'Respond naturally.')
            }
        elif trigger_type == "Keyword" and keyword_triggered_rule_data:
            preferred_model_id_for_call = 'gemini_2_5_flash'
            base_human_system_prompt_kwargs = {
                'server_name': prompt_data_for_ai_call['server_name'],
                'channel_name': prompt_data_for_ai_call['channel_name'],
                'current_time_utc': datetime.datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
            }
            human_sys_instruct = self.get_prompt("HUMAN_SYSTEM_INSTRUCTION_V3", **base_human_system_prompt_kwargs)

            system_instruction_details['key'] = "KEYWORD_TRIGGER_SYSTEM_INSTRUCTION"
            system_instruction_details['kwargs'] = {
                'human_system_instruction': human_sys_instruct,
                'phrase_identifier': keyword_triggered_rule_data['phrase_identifier'],
                'speciality': keyword_triggered_rule_data.get('speciality', 'General topic'),
                'instructions': keyword_triggered_rule_data.get('instructions', 'Respond naturally.')
            }
        elif trigger_type.startswith("COMMAND_"):
            preferred_model_id_for_call = 'gemini_2_5_flash'
            system_instruction_details['key'] = system_instruction_key_override or "BOT_PURPOSE_GENERAL"

            if not prompt_key_for_ai:
                await self.log_error(guild_for_log, f"AI Cog Send Error: No prompt_key_for_ai for COMMAND trigger '{trigger_type}'.")
                if interaction_for_command_reply: await interaction_for_command_reply.followup.send("Error: AI prompt config missing.", ephemeral=True)
                return
            command_ai_prompt_text = self.get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {}))
            if not command_ai_prompt_text:
                await self.log_error(guild_for_log, f"AI Cog Send Error: Could not load prompt key '{prompt_key_for_ai}' for trigger '{trigger_type}'.")
                if interaction_for_command_reply: await interaction_for_command_reply.followup.send("Error: AI prompt load failed.", ephemeral=True)
                return
            prompt_data_for_ai_call['current_message_content'] = command_ai_prompt_text

        ai_response_raw = None
        try:
            typing_context = channel_to_send_in.typing() if isinstance(channel_to_send_in, discord.TextChannel) and not interaction_for_command_reply and not mob_mode_details else contextlib.nullcontext()
            async with typing_context:
                ai_response_raw = await self.get_ai_response(
                    prompt_data=prompt_data_for_ai_call,
                    history=history_context,
                    system_instruction_details=system_instruction_details,
                    preferred_model_id=preferred_model_id_for_call
                )
        except Exception as ai_call_err:
            log_msg_content = f"Error during get_ai_response call for '{trigger_type}' in channel {channel_to_send_in.id}"
            await self.log_error(guild_for_log, log_msg_content, error=ai_call_err)
            fail_msg = "... (ran into a cosmic ray 💫 trying to respond)"
            if interaction_for_command_reply: await interaction_for_command_reply.followup.send(fail_msg, ephemeral=True)
            elif trigger_type == "AlwaysOn" and not mob_mode_details : await channel_to_send_in.send(fail_msg)
            elif not mob_mode_details and triggering_message: await triggering_message.reply(fail_msg, mention_author=False)
            return

        if not ai_response_raw:
            await self.log_info(guild_for_log, f"AI for '{trigger_type}' in {channel_to_send_in.id} returned None/empty.")
            if trigger_type == "AlwaysOn" and not mob_mode_details:
                await channel_to_send_in.send("... (my circuits are quiet right now 🤖)")
            return

        # --- Enhanced Response Processing ---
        ai_response_processed = ai_response_raw.strip()

        # Regex to find and strip prefixes like "[timestamp] Bot Name (You (Pingslave)): "
        # This is more robust against variations in the bot's display name.
        pingslave_prefix_pattern = re.compile(r"^(?:\[.*?UTC\]\s*)?(?:.*?\(You \(Pingslave\)\):\s*)", re.IGNORECASE)
        match = pingslave_prefix_pattern.match(ai_response_processed)
        if match:
            ai_response_processed = ai_response_processed[match.end():]

        # Fallback stripping for simpler "BotName:" prefixes if the regex didn't catch it or for other cases.
        if self.bot.user and self.bot.user.name: # Check if bot.user and name are available
            # Try stripping with bot's display name first, then its actual name
            display_name_prefix_lower = f"{self.bot.user.display_name.lower()}:"
            name_prefix_lower = f"{self.bot.user.name.lower()}:"

            if ai_response_processed.lower().startswith(display_name_prefix_lower):
                ai_response_processed = ai_response_processed[len(display_name_prefix_lower):].lstrip()
            elif ai_response_processed.lower().startswith(name_prefix_lower):
                ai_response_processed = ai_response_processed[len(name_prefix_lower):].lstrip()
        else: # Absolute fallback if bot.user or bot.user.name is somehow None
            if ai_response_processed.lower().startswith("pingslave:"):
                ai_response_processed = ai_response_processed[len("pingslave:"):].lstrip()
            elif ai_response_processed.lower().startswith("bot:"):
                ai_response_processed = ai_response_processed[len("bot:"):].lstrip()
        
        ai_response_processed = ai_response_processed.strip() # General strip after all specific ones

        # Remove trailing punctuation if it's a single character (., !, ?)
        if ai_response_processed.endswith(('.', '!', '?')) and not any(ai_response_processed.endswith(x) for x in ['...', '?!', '!!']):
            ai_response_processed = ai_response_processed[:-1]
        
        if len(ai_response_processed) > 1950:
            ai_response_processed = ai_response_processed[:1947] + "..."

        if not ai_response_processed.strip():
            await self.log_info(guild_for_log, f"AI response for '{trigger_type}' became empty after processing.")
            return
        # --- End Enhanced Response Processing ---


        final_message_content_to_send = ai_response_processed
        if trigger_type == "Discovery" and discovery_congrats_user and keyword_triggered_rule_data:
            final_message_content_to_send = (
                f"# 🎉 \n woohoo, {discovery_congrats_user.mention}! you're the first to find the secret phrase: "
                f"**'{discord.utils.escape_markdown(keyword_triggered_rule_data['phrase_identifier'])}'**! 🎉\n\n"
                f"{ai_response_processed}"
            )
        elif trigger_type == "Keyword" and keyword_triggered_rule_data and not mob_mode_details:
            final_message_content_to_send += f"\n*(You triggered the keyword: `{discord.utils.escape_markdown(keyword_triggered_rule_data['phrase_identifier'])}`)*"

        try:
            if mob_mode_details and isinstance(channel_to_send_in, discord.TextChannel):
                await self._send_mob_webhook_message(
                    channel_to_send_in,
                    mob_mode_details['mob_name'],
                    mob_mode_details['mob_image_path'],
                    final_message_content_to_send
                )
            elif interaction_for_command_reply:
                is_ephemeral_command = trigger_type.startswith("COMMAND_") and trigger_type.endswith("_EPHEMERAL")
                send_method = interaction_for_command_reply.followup.send if interaction_for_command_reply.response.is_done() else interaction_for_command_reply.response.send_message
                await send_method(final_message_content_to_send, ephemeral=is_ephemeral_command)

            elif trigger_type == "AlwaysOn":
                if random.random() < PINGSLAVE_SPECIAL_COMMENT_CHANCE:
                    special_additions = ["\n*(...just some digital thoughts ✨)*", "\n*(...is this real life? 🤖)*", "\n*(...pondering the universe, brb 🌌)*", "\n*(...beep boop? 🤔)*"]
                    final_message_content_to_send += random.choice(special_additions)
                    if len(final_message_content_to_send) > 1980:
                        final_message_content_to_send = final_message_content_to_send[:1977] + "..."
                await channel_to_send_in.send(final_message_content_to_send)
            else:
                mention_author_flag = trigger_type in ["Reply", "Keyword", "Discovery"]
                await triggering_message.reply(final_message_content_to_send, mention_author=mention_author_flag)

        except (discord.Forbidden, discord.HTTPException) as reply_err:
            await self.log_error(guild_for_log, f"Failed to send AI '{trigger_type}' response in {channel_to_send_in.id}", error=reply_err)

    async def _send_mob_webhook_message(self, channel: discord.TextChannel, mob_name: str, image_path: str, content: str):
        webhook: Optional[discord.Webhook] = None
        avatar_bytes: Optional[bytes] = None
        try:
            with open(image_path, 'rb') as f:
                avatar_bytes = f.read()
        except Exception as e:
            await self.log_error(channel.guild, f"Error reading mob avatar for {mob_name} from {image_path}", error=e)
            await channel.send(f"**{mob_name} (Appearing mysteriously):** {content}\n*(My grand entrance was... foiled by a file error! Imagine me looking suitably menacing.)*")
            return

        if not avatar_bytes:
            await channel.send(f"**{mob_name} (A Formless Voice):** {content}\n*(My avatar is missing! Truly, a tragedy.)*")
            return

        try:
            webhook = await channel.create_webhook(name=mob_name, avatar=avatar_bytes, reason=f"Temporary Pingslave Mob Mode: {mob_name}")
            await webhook.send(content=content, wait=True)
            print(f"AI Cog: Sent mob message as '{mob_name}' with custom avatar in #{channel.name}.")
        except discord.Forbidden:
            await self.log_error(channel.guild, f"Missing 'Manage Webhooks' permission in #{channel.name} for Mob Mode avatar. Mob: {mob_name}. Sent as plain text.", ping_owner=False)
            try:
                await channel.send(f"**{mob_name}:** {content}\n*(Imagine I have a super cool picture right now!)*")
            except Exception as fallback_e:
                 await self.log_error(channel.guild, f"Mob mode fallback plain send also failed for {mob_name}", error=fallback_e)
        except Exception as e:
            await self.log_error(channel.guild, f"Error sending mob webhook message for {mob_name}", error=e)
            try:
                await channel.send(f"**{mob_name} (My transformation had a glitch!):** {content}")
            except: pass
        finally:
            if webhook:
                try:
                    await webhook.delete(reason=f"Temporary Pingslave Mob Mode cleanup: {mob_name}")
                    print(f"AI Cog: Deleted temporary webhook for '{mob_name}' in #{channel.name}.")
                except Exception as e_del:
                    await self.log_error(channel.guild, f"Error deleting temporary webhook for {mob_name} in #{channel.name}", error=e_del, ping_owner=False)

    @app_commands.command(name="aiping", description="Check the API latency of configured AI models.")
    async def aiping(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=False)

        guild = interaction.guild # For logging context
        
        available_models = self.get_all_available_models_details()
        
        if not available_models:
            await interaction.followup.send("⚠️ No AI models are currently configured or available for pinging.", ephemeral=True)
            await self.log_info(guild, "/aiping: No AI models configured.")
            return

        embed = discord.Embed(
            title="🛰️ AI Model Ping Test Results",
            description="Pinging configured AI models...",
            color=getattr(self.bot, 'NERDY_YELLOW_config', discord.Color.gold())
        )
        embed.timestamp = discord.utils.utcnow()

        # Send initial embed
        try:
            await interaction.edit_original_response(embed=embed)
        except discord.HTTPException:
            # If interaction expired quickly or other issue
            await interaction.followup.send(embed=embed)


        test_prompt = "Hello! Tell me a one-sentence fun fact about Earth's oceans."
        results_summary = []

        for model_info in available_models:
            model_instance = model_info['instance']
            model_name_display = model_info['name'] # e.g., "Gemini 2.5 Flash (Preview)"
            model_id_internal = model_info['id']   # e.g., "gemini_2_5_flash"
            
            status_emoji = "❓"
            latency_str = "`N/A`"
            details_str = ""

            if not model_instance:
                status_emoji = "❌"
                details_str = "`Model not initialized/configured.`"
                results_summary.append(f"{status_emoji} **{model_name_display} ({model_id_internal})**: {details_str}")
                continue

            print(f"AI Ping: Testing model {model_name_display} ({model_id_internal})...")
            start_time = datetime.datetime.now(pytz.utc)
            
            try:
                # For a simple text prompt, we can directly pass the string.
                response = await model_instance.generate_content_async(test_prompt)
                end_time = datetime.datetime.now(pytz.utc)
                latency_ms = round((end_time - start_time).total_seconds() * 1000)
                latency_str = f"`{latency_ms} ms`"

                if response and response.text:
                    status_emoji = "✅"
                    details_str = f"Latency: {latency_str}"
                    print(f"AI Ping Success: {model_name_display} responded in {latency_ms}ms. Text: '{response.text[:50]}...'")
                elif response and response.prompt_feedback:
                    status_emoji = "⚠️"
                    block_reason = getattr(response.prompt_feedback, 'block_reason', 'Unknown Block')
                    details_str = f"Blocked/Empty (Reason: `{block_reason}`). Latency: {latency_str}"
                    print(f"AI Ping Warning: {model_name_display} blocked/empty. Reason: {block_reason}. Latency: {latency_ms}ms")
                else:
                    status_emoji = "❔"
                    details_str = f"No response/text. Latency: {latency_str}"
                    print(f"AI Ping Info: {model_name_display} no response/text. Latency: {latency_ms}ms")

            except google_exceptions.GoogleAPIError as e_api:
                status_emoji = "🔥"
                details_str = f"API Error: `{type(e_api).__name__}`"
                await self.log_error(guild, f"/aiping test failed for {model_name_display}", error=e_api)
                print(f"AI Ping API Error: {model_name_display} - {e_api}")
            except Exception as e:
                status_emoji = "💥"
                details_str = f"General Error: `{type(e).__name__}`"
                await self.log_error(guild, f"/aiping test failed for {model_name_display}", error=e, ping_owner=True)
                print(f"AI Ping General Error: {model_name_display} - {e}")
            
            results_summary.append(f"{status_emoji} **{model_name_display}** ({model_id_internal}): {details_str}")

            # Update embed after each model test
            embed.description = "\n".join(results_summary)
            try:
                await interaction.edit_original_response(embed=embed)
            except discord.HTTPException:
                # Possible if the interaction token expires during long pings
                print(f"AI Ping: Failed to update embed for {model_name_display}, interaction might have expired.")
                pass 
            
            await asyncio.sleep(0.5) # Small delay between pings

        final_description = "\n".join(results_summary)
        if not final_description:
            final_description = "No models were pinged or an issue occurred."
        
        embed.description = final_description
        embed.add_field(name="Legend", value="✅ Success | ⚠️ Blocked/Empty | 🔥 API Error | 💥 General Error | ❌ Not Configured | ❓ Unknown", inline=False)
        
        try:
            await interaction.edit_original_response(embed=embed)
        except discord.HTTPException:
            # Attempt to send a new message if edit fails (e.g., interaction expired)
            try:
                await interaction.followup.send(embed=embed)
            except Exception as e_followup:
                 await self.log_error(guild, "/aiping final followup send failed", error=e_followup)
        
        await self.log_info(guild, f"/aiping executed by {interaction.user}. Results summary logged internally.")


    def _parse_mob_name(self, filename: str) -> str:
        name = os.path.splitext(filename)[0]
        for rarity_suffix in MOB_NAME_RARITIES_TO_STRIP:
            if name.endswith(rarity_suffix):
                name = name[:-len(rarity_suffix)]
                break
        return name.strip() or "Mysterious Mob"

    async def load_keyword_data(self, guild_for_log: Optional[discord.Guild]):
        if not self.supabase:
            await self.log_error(guild_for_log, "AI Cog Keyword loading failed: Supabase unavailable.", ping_owner=True)
            return

        print("AI Cog: Loading keyword data from Supabase...")
        try:
            resp = await self.run_supabase_sync(
                lambda: self.supabase.table(self.keyword_table_name)
                               .select("id, phrase_identifier, inclusion_regex, exclusion_regex, speciality, instructions, discovered_by_user_id, discovered_at")
                               .eq("is_enabled", True)
                               .execute()
            )

            if not resp or not hasattr(resp, 'data'):
                await self.log_info(guild_for_log, "AI Cog: No keyword data found or failed to fetch from Supabase.")
                self.keyword_data_cache = {}
                self.total_keywords = 0
                self.discovered_keywords_count = 0
                return

            temp_cache = {}
            temp_discovered_count = 0
            compile_errors = []

            for entry in resp.data:
                entry_id_str = str(entry['id'])
                incl_regex_str = entry['inclusion_regex']
                excl_regex_str = entry['exclusion_regex']

                try:
                    if not incl_regex_str: raise ValueError("Inclusion regex cannot be empty")
                    incl_compiled = re.compile(incl_regex_str, re.IGNORECASE)
                except (re.error, ValueError) as e:
                    compile_errors.append(f"ID '{entry_id_str}' (Identifier: {entry.get('phrase_identifier', 'N/A')}): Inclusion Regex Error: {e}")
                    continue

                excl_compiled = None
                if excl_regex_str:
                    try:
                        excl_compiled = re.compile(excl_regex_str, re.IGNORECASE)
                    except re.error as e:
                        compile_errors.append(f"ID '{entry_id_str}' (Identifier: {entry.get('phrase_identifier', 'N/A')}): Exclusion Regex Error (will proceed without it): {e}")

                temp_cache[entry_id_str] = {
                    'id': entry_id_str,
                    'phrase_identifier': entry.get('phrase_identifier', f'Rule_{entry_id_str[:8]}'),
                    'inclusion_regex': incl_compiled,
                    'exclusion_regex': excl_compiled,
                    'speciality': entry.get('speciality'),
                    'instructions': entry.get('instructions'),
                    'discovered_by': entry.get('discovered_by_user_id'),
                    'discovered_at': date_parse(entry['discovered_at']) if entry.get('discovered_at') else None
                }
                if temp_cache[entry_id_str]['discovered_by']:
                    temp_discovered_count += 1

            self.keyword_data_cache = temp_cache
            self.total_keywords = len(self.keyword_data_cache)
            self.discovered_keywords_count = temp_discovered_count

            print(f"AI Cog: Loaded {self.total_keywords} enabled keyword rules. Discovered: {self.discovered_keywords_count}.")
            if compile_errors:
                log_message = "AI Cog Keyword Regex Compilation Warnings/Errors:\n- " + "\n- ".join(compile_errors)
                print(f"AI Cog WARNING: {log_message}")
                await self.log_error(guild_for_log, log_message, ping_owner=False)

        except Exception as e:
            await self.log_error(guild_for_log, "AI Cog: Critical failure loading keyword data from Supabase", error=e, ping_owner=True)
            self.keyword_data_cache = {}
            self.total_keywords = 0
            self.discovered_keywords_count = 0

    async def record_discovery_in_db(self, guild_for_log: Optional[discord.Guild], keyword_id_str: str, user_id: int, discovery_time: datetime.datetime):
        if not self.supabase:
            await self.log_error(guild_for_log, f"AI Cog Discovery recording failed for {keyword_id_str}: Supabase unavailable.", ping_owner=True)
            return False

        print(f"AI Cog: Recording discovery for keyword ID {keyword_id_str} by user {user_id}...")
        try:
            aware_discovery_time = discovery_time.astimezone(pytz.utc) if discovery_time.tzinfo is None else discovery_time

            await self.run_supabase_sync(
                lambda: self.supabase.table(self.keyword_table_name)
                               .update({
                                   'discovered_by_user_id': str(user_id),
                                   'discovered_at': aware_discovery_time.isoformat()
                               })
                               .eq('id', keyword_id_str)
                               .is_('discovered_by_user_id', 'null')
                               .execute()
            )
            print(f"AI Cog: Successfully recorded discovery for keyword ID {keyword_id_str}.")
            return True
        except Exception as e:
            await self.log_error(guild_for_log, f"AI Cog: Failed to record discovery for keyword ID {keyword_id_str} in Supabase", error=e, ping_owner=True)
            return False


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or not self.bot.is_ready() or not self.bot.user or \
           message.author.id == self.bot.user.id or message.author.bot:
            return
        if not message.content and not message.attachments and not message.stickers:
            return

        is_catercord = message.guild.id == self.catercord_guild_id
        is_private_server = message.guild.id == self.private_server_id
        is_owner = message.author.id == self.owner_user_id
        is_staff_channel_catercord = is_catercord and message.channel.id in self.staff_channels
        is_bot_commands_channel_catercord = is_catercord and message.channel.id in self.bot_commands_allowed_channel_ids
        is_restricted_keyword_channel_catercord = is_staff_channel_catercord or is_bot_commands_channel_catercord

        history_context = []
        try:
            history_context = [m async for m in message.channel.history(limit=HISTORY_MESSAGE_LIMIT, before=message)]
            history_context.reverse()
        except Exception as e_hist:
            print(f"AI Cog Error fetching history for message {message.id}: {e_hist}")

        if message.channel.id in self.always_on_ai_channels and not message.content.startswith(self.command_prefix):
            print(f"AI Cog Trigger: Always-On Channel by {message.author.name} ({message.author.id}) in #{message.channel.name} ({message.guild.name})")

            if random.random() < MOB_MODE_CHANCE and os.path.isdir(self.mobs_folder_path) and isinstance(message.channel, discord.TextChannel):
                mob_files = [f for f in os.listdir(self.mobs_folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
                if mob_files:
                    selected_mob_file = random.choice(mob_files)
                    mob_name = self._parse_mob_name(selected_mob_file)
                    mob_image_path = os.path.join(self.mobs_folder_path, selected_mob_file)

                    print(f"AI Cog: MOB MODE triggered! Mob: {mob_name}, Image: {selected_mob_file}")
                    await self.send_ai_chat_response(
                        triggering_message=message, trigger_type="MobMode", history_context=history_context,
                        mob_mode_details={'mob_name': mob_name, 'mob_image_path': mob_image_path, 'user_message_content': message.content or "(sent attachments/stickers)"}
                    )
                    return

            await self.send_ai_chat_response(
                triggering_message=message, trigger_type="AlwaysOn", history_context=history_context
            )
            return

        is_reply_to_bot = False
        if message.reference:
            if message.reference.resolved and isinstance(message.reference.resolved, discord.Message) and message.reference.resolved.author.id == self.bot.user.id:
                is_reply_to_bot = True
            elif message.reference.message_id :
                try:
                    ref_msg = await message.channel.fetch_message(message.reference.message_id)
                    if ref_msg.author.id == self.bot.user.id:
                        is_reply_to_bot = True
                except (discord.NotFound, discord.HTTPException):
                    pass


        bot_mention_formats = [f'<@{self.bot.user.id}>', f'<@!{self.bot.user.id}>']
        is_mention_to_bot = any(mention in message.content for mention in bot_mention_formats)

        if is_reply_to_bot or is_mention_to_bot:
            if is_catercord and message.channel.id not in self.always_on_ai_channels:
                clickable_channel = f"<#{self.unrestricted_ai_channel_id}>" if self.unrestricted_ai_channel_id else "the designated AI channel"
                info_message_text = f"ℹ️ Psst! You can chat with me freely in {clickable_channel} for AI-powered conversations! This message will disappear shortly."
                try: await message.reply(info_message_text, mention_author=False, delete_after=10.0)
                except Exception as info_reply_err: print(f"AI Cog Error sending AI channel info message: {info_reply_err}")
                return

            can_respond_here = (message.channel.id in self.always_on_ai_channels or
                               (not is_catercord and message.guild.me and message.guild.me.joined_at))
            if can_respond_here:
                trigger_method = "Reply" if is_reply_to_bot else "Mention"
                print(f"AI Cog Trigger: {trigger_method} by {message.author.name} ({message.author.id}) in #{message.channel.name} ({message.guild.name})")
                await self.send_ai_chat_response(
                    triggering_message=message, trigger_type=trigger_method, history_context=history_context
                )
                return

        if self.keyword_data_cache and message.content:
            message_content_lower = message.content.lower()
            for rule_id_str, rule_data in self.keyword_data_cache.items():
                if not isinstance(rule_data, dict) or not rule_data.get('inclusion_regex'): continue
                try:
                    if rule_data.get('exclusion_regex') and rule_data['exclusion_regex'].search(message_content_lower):
                        continue
                    if not rule_data['inclusion_regex'].search(message_content_lower):
                        continue

                    phrase_identifier = rule_data['phrase_identifier']
                    is_discovered = bool(rule_data.get('discovered_by'))

                    if not is_discovered:
                        can_discover = (is_catercord and not is_restricted_keyword_channel_catercord and not is_owner) or \
                                       (is_private_server and is_owner)
                        if can_discover:
                            discovery_context = "Catercord (Public)" if is_catercord else "Private Server (Owner)"
                            print(f"AI Cog Keyword DISCOVERY: '{phrase_identifier}' by {message.author.name} ({message.author.id}) in #{message.channel.name} ({message.guild.name} - {discovery_context})")
                            discovery_time = discord.utils.utcnow()
                            db_recorded = await self.record_discovery_in_db(message.guild, rule_id_str, message.author.id, discovery_time)
                            if db_recorded:
                                self.keyword_data_cache[rule_id_str]['discovered_by'] = str(message.author.id)
                                self.keyword_data_cache[rule_id_str]['discovered_at'] = discovery_time
                                self.discovered_keywords_count += 1
                                await self.send_ai_chat_response(
                                    triggering_message=message, trigger_type="Discovery", history_context=history_context,
                                    discovery_congrats_user=message.author, keyword_triggered_rule_data=rule_data
                                )
                                return
                            else:
                                await self.log_error(message.guild, f"AI Cog: Failed to record DB discovery for '{phrase_identifier}' by {message.author.name}.", ping_owner=True)
                        continue

                    if is_discovered:
                        can_trigger = (is_catercord and not is_restricted_keyword_channel_catercord) or \
                                      (is_private_server and is_owner) or \
                                      (not is_catercord and not is_private_server and message.guild.me and message.guild.me.joined_at)
                        if can_trigger:
                            trigger_context = "Catercord (Public)" if is_catercord else \
                                              "Private Server (Owner)" if is_private_server else \
                                              f"Other Server ({message.guild.name})"
                            print(f"AI Cog Keyword TRIGGER: '{phrase_identifier}' by {message.author.name} ({message.author.id}) in #{message.channel.name} ({message.guild.name} - {trigger_context})")
                            await self.send_ai_chat_response(
                                triggering_message=message, trigger_type="Keyword", history_context=history_context,
                                keyword_triggered_rule_data=rule_data
                            )
                            return
                except Exception as e_rule:
                    await self.log_error(message.guild, f"AI Cog Error processing keyword rule '{rule_data.get('phrase_identifier', rule_id_str)}'", error=e_rule)

    @app_commands.command(name="addkeyword", description="[Owner Only] Add a new keyword rule.")
    async def addkeyword(
        self, interaction: discord.Interaction,
        phrase_identifier: str, inclusion_regex: str, speciality: str, instructions: str,
        exclusion_regex: Optional[str] = None
    ):
        if interaction.user.id != self.owner_user_id:
            await interaction.response.send_message("❌ You don't have permission for this.", ephemeral=True)
            return
        if not self.supabase:
            await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
            return

        if not all([phrase_identifier, inclusion_regex, speciality, instructions]):
            await interaction.response.send_message("❌ All fields (except exclusion_regex) are required.", ephemeral=True)
            return
        try:
            re.compile(inclusion_regex, re.IGNORECASE)
            if exclusion_regex: re.compile(exclusion_regex, re.IGNORECASE)
        except re.error as e:
            await interaction.response.send_message(f"❌ Invalid Regex: `{e}`", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)
        data_to_insert = {
            "phrase_identifier": phrase_identifier.strip(), "inclusion_regex": inclusion_regex.strip(),
            "exclusion_regex": exclusion_regex.strip() if exclusion_regex else None,
            "speciality": speciality.strip(), "instructions": instructions.strip(), "is_enabled": True,
        }
        try:
            await self.run_supabase_sync(
                lambda: self.supabase.table(self.keyword_table_name).insert(data_to_insert).execute()
            )
            await interaction.followup.send(f"✅ Keyword rule `{phrase_identifier}` added!")
            await self.log_info(interaction.guild, f"Owner `{interaction.user}` added keyword: `{phrase_identifier}`.")
            await self.log_info(interaction.guild, "Reloading keyword cache after addition...")
            await self.load_keyword_data(interaction.guild)
        except Exception as e:
            err_msg = str(getattr(e, 'message', str(e)))
            if "unique constraint" in err_msg.lower() and f'"{self.keyword_table_name}_phrase_identifier_key"' in err_msg.lower():
                await interaction.followup.send(f"❌ Failed: Phrase Identifier `{phrase_identifier}` already exists.")
            else:
                await self.log_error(interaction.guild, f"AI Cog Keyword add failed for `{phrase_identifier}`.", error=e, interaction=interaction)
                await interaction.followup.send(f"❌ Database Error adding keyword: {err_msg[:1500]}")

    @app_commands.command(name="discoveries", description="Explore AI-powered secret keyword phrases!")
    async def discoveries(self, interaction: discord.Interaction):
        if not self.bot.user or not self.bot.user.id:
            await interaction.response.send_message("🔍 Bot is initializing. Please try again shortly.", ephemeral=True); return
        if not self.keyword_data_cache and self.total_keywords == 0 :
            if not self.supabase:
                await interaction.response.send_message("🔍 Keyword system is currently unavailable (database connection).", ephemeral=True)
                return
            await self.log_info(interaction.guild, "/discoveries used when cache was empty, attempting a load.")
            await self.load_keyword_data(interaction.guild)
            if not self.keyword_data_cache and self.total_keywords == 0:
                 await interaction.response.send_message("🔍 No keyword phrases are configured yet, or data is still loading. Try again in a moment!", ephemeral=True)
                 return

        guild = interaction.guild
        catercord_invite_link = "https://discord.gg/5gMRbeWNKw"
        bot_permissions = discord.Permissions(
            send_messages=True, embed_links=True, attach_files=True,
            read_message_history=True, manage_webhooks=True
        )
        bot_invite_link = discord.utils.oauth_url(
            self.bot.user.id, permissions=bot_permissions, scopes=("bot", "applications.commands")
        )

        description_lines = []
        is_catercord_server = guild and guild.id == self.catercord_guild_id
        bot_is_true_guild_member = guild and guild.me and guild.me.joined_at

        if is_catercord_server:
            guild_name_display = f"this server ({discord.utils.escape_markdown(guild.name)})" if guild and guild.name else "Catercord"
            description_lines.extend([
                f"🕵️‍♂️ I'll respond to any known secret phrases you type here in {guild_name_display}.",
                f"🎉 Be the first to find a new one, and I'll announce your grand discovery!"
            ])
        elif guild and bot_is_true_guild_member:
            description_lines.extend([
                f"🕵️‍♂️ I'll respond to *already discovered* secret phrases in this server ({discord.utils.escape_markdown(guild.name)}).",
                f"➡️ To discover **new** secret phrases, the main adventure is in [**Catercord**]({catercord_invite_link})!"
            ])
        else:
            bot_name_display = self.bot.user.name if self.bot.user else "this bot"
            guild_name_part = f" in **{discord.utils.escape_markdown(guild.name)}**" if guild and guild.name else ""
            description_lines.extend([
                f"👋 Thanks for trying my keyword feature{guild_name_part}!",
                f"To let me listen for keywords here, an admin needs to [add {bot_name_display} to this server]({bot_invite_link}). (I need `Manage Webhooks` permission for all my tricks! 😉)",
                f"➡️ For discovering **new** phrases and full keyword interaction, join [**Catercord**]({catercord_invite_link})!"
            ])

        description_lines.append("\n---")
        if self.total_keywords > 0:
            description_lines.append(f"**Overall Progress:** {self.discovered_keywords_count} / {self.total_keywords} phrases revealed globally.")
        else:
            description_lines.append("\n*No keyword phrases are currently configured.*")

        embed_color = getattr(self.bot, 'NERDY_YELLOW_config', discord.Color.gold())
        embed = discord.Embed(title="🔮 AI Keyword Mysteries 🔮", description="\n".join(description_lines), color=embed_color)

        discovered_list_formatted = []
        undiscovered_count = 0
        valid_rules = [rule for rule in self.keyword_data_cache.values() if isinstance(rule, dict) and 'phrase_identifier' in rule]
        sorted_rules = sorted(valid_rules, key=lambda r: str(r.get('phrase_identifier', '')).lower())

        for rule in sorted_rules:
            if rule.get('discovered_by'):
                user_id_str = rule['discovered_by']
                timestamp_dt = rule.get('discovered_at')
                user_mention = f"<@{user_id_str}>"
                time_display = f" (<t:{int(timestamp_dt.timestamp())}:R>)" if timestamp_dt and isinstance(timestamp_dt, datetime.datetime) else ""
                escaped_phrase_id = discord.utils.escape_markdown(str(rule['phrase_identifier']))
                discovered_list_formatted.append(f"🔹 `{escaped_phrase_id}` by {user_mention}{time_display}")
            else:
                undiscovered_count += 1

        if discovered_list_formatted:
            discovered_text_joined = "\n".join(discovered_list_formatted)
            if len(discovered_text_joined) > 1020: discovered_text_joined = discovered_text_joined[:1015] + "\n... (more)"
            embed.add_field(name="📜 Known Phrases (Discovered Globally)", value=discovered_text_joined or "None yet!", inline=False)
        elif self.total_keywords > 0:
            embed.add_field(name="📜 Known Phrases (Discovered Globally)", value="The scroll is blank... No phrases discovered yet!", inline=False)

        if self.total_keywords > 0 and undiscovered_count > 0:
            embed.add_field(name=f"❓ {undiscovered_count} Secret Phrase{'s' if undiscovered_count != 1 else ''} Still Hidden Globally", value="*The quest continues!*", inline=False)
        elif self.total_keywords > 0 and undiscovered_count == 0:
            embed.add_field(name="🎉 All Mysteries Solved Globally! 🎉", value="*The archives are complete!*", inline=False)

        bot_name_footer = self.bot.user.name if self.bot.user else "Pingslave"
        embed.set_footer(text=f"Bot by TheNerd (sweet_honey) | {bot_name_footer}")
        if self.bot.user and self.bot.user.display_avatar: embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=False)

async def setup(bot: commands.Bot):
    print("AICog: setup function STARTED")
    ai_cog_config = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "ALWAYS_ON_AI_CHANNELS": getattr(bot, 'ALWAYS_ON_AI_CHANNELS_config', set()),
        "UNRESTRICTED_AI_CHANNEL_ID": getattr(bot, 'UNRESTRICTED_AI_CHANNEL_ID_config', None),
        "KEYWORD_TABLE_NAME": "keyword_phrases",
        "OWNER_USER_ID": getattr(bot, 'OWNER_USER_ID_config', None),
        "CATERCORD_GUILD_ID": getattr(bot, 'CATERCORD_GUILD_ID_config', None),
        "PRIVATE_SERVER_ID": getattr(bot, 'PRIVATE_SERVER_ID_config', None),
        "RANDOM_SERVER_ID": getattr(bot, 'RANDOM_SERVER_ID_config', None),
        "STAFF_CHANNELS": getattr(bot, 'STAFF_CHANNELS_config', set()),
        "BOT_COMMANDS_ALLOWED_CHANNEL_IDS": getattr(bot, 'BOT_COMMANDS_ALLOWED_CHANNEL_IDS_config', set()),
        "COMMAND_PREFIX": getattr(bot, 'COMMAND_PREFIX_config', '.'),
        "INGAME_NAME_CACHE_REF": getattr(bot, 'ingame_name_cache_ref_config', []),
        "NERDY_YELLOW": getattr(bot, 'NERDY_YELLOW_config', discord.Color.gold()),
        "MOBS_FOLDER_PATH_config": getattr(bot, 'MOBS_FOLDER_PATH_config', "Mobs")
    }

    supabase_client = getattr(bot, 'supabase_client', None)
    log_info_global = getattr(bot, 'log_info_global', None)
    log_error_global = getattr(bot, 'log_error_global', None)
    run_supabase_sync_global = getattr(bot, 'run_supabase_sync_global', None)

    if not all([supabase_client, log_info_global, log_error_global, run_supabase_sync_global]):
        missing_core_funcs_msg = "AI Cog CRITICAL: Missing core functions/clients from bot instance. AI Cog may not function correctly. Essential dependencies (supabase_client, logging funcs) not found on bot instance."
        print(missing_core_funcs_msg)
        # Raise an error here to ensure load_extension in bot.py knows about this critical failure
        raise commands.ExtensionFailed(path="ai_cog", message=missing_core_funcs_msg)


    cog_instance = AICog(bot,
                         supabase_client,
                         log_info_global,
                         log_error_global,
                         run_supabase_sync_global,
                         ai_cog_config)

    print(f"AICog: Attempting to add cog instance: {cog_instance}")
    try:
        await bot.add_cog(cog_instance)
        print(f"AICog: SUCCESSFULLY CALLED bot.add_cog() with {cog_instance.__class__.__name__}")
    except Exception as e:
        print(f"AICog: !!! CRITICAL ERROR during bot.add_cog(): {e}") # Emphasize criticality
        # import traceback # Already imported at the top of the file
        traceback.print_exc()
        # Re-raise the exception so bot.load_extension() in bot.py catches it
        # as a proper ExtensionFailed error.
        raise  # <--- Key change: re-raise the exception

    # await simple_gemini_2_0_flash_test() # Keep commented out unless actively testing
    # print("AI Cog: simple_gemini_2_0_flash_test completed after cog setup.") # Keep commented out
    print("AI Cog: setup function FINISHED")