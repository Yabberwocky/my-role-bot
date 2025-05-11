# -*- coding: utf-8 -*-
# --- LLM CONTEXT FOR AI COG ---
# (Please do not remove this comment block)
#
# This `ai_cog.py` file contains the primary AI-related functionalities for TheNerd's Pingslave bot.
# However, certain features in the main `bot.py` file still interact with or depend on this cog.
#
# When modifying this AI Cog, especially functions related to AI responses,
# image processing, or keyword data, be aware that the following areas
# in `bot.py` might require corresponding updates:
#
# 1. Image-Based Activity Logging (in `on_message` within `bot.py`):
#    - The screenshot processing logic in `bot.py`'s `on_message` event
#      (specifically for messages in `SCREENSHOTS_DROPBOX_CHANNEL_ID`)
#      calls `AICog.get_ai_response_with_image()` for extracting in-game names.
#    - It also relies on `AICog.ingame_name_cache_ref` (passed during cog setup
#      and referring to `bot.ingame_name_cache` in `bot.py`) for validating
#      extracted names.
#    - Changes to the `FLORR_IMAGE_NAME_EXTRACTION` prompt or the behavior/signature
#      of `get_ai_response_with_image()` in this cog will likely affect `bot.py`.
#
# 2. `/message` Command (in `bot.py`):
#    - This command has an option to use AI for generating message content.
#    - When AI is selected, it calls `AICog.get_ai_response()` and uses
#      `AICog.get_prompt("HUMAN_SYSTEM_INSTRUCTION")`.
#    - Modifications to these methods or the `HUMAN_SYSTEM_INSTRUCTION` prompt
#      in this cog could impact the `/message` command in `bot.py`.
#
# 3. `/refresh` Command (in `bot.py`):
#    - This command is responsible for reloading keyword data, among other things.
#    - It calls `AICog.load_keyword_data()`.
#    - Changes to the `load_keyword_data()` method in this cog (e.g., its
#      parameters or return values, though currently it has none it directly uses)
#      might necessitate changes in how `/refresh` calls it in `bot.py`.
#
# 4. Configuration and Initialization:
#    - This cog is initialized in `bot.py` (typically in `on_ready` via `bot.load_extension('ai_cog')`).
#    - The `setup()` function in this cog receives the `bot` instance and a `config` dictionary.
#    - This `config` dictionary is populated in `bot.py` with various constants and references
#      (e.g., `OWNER_USER_ID`, `CATERCORD_GUILD_ID`, `ALWAYS_ON_AI_CHANNELS`, `STAFF_CHANNELS`,
#      `ingame_name_cache_ref`, logging functions, Supabase client).
#    - If the way these configurations are passed or named changes in `bot.py`,
#      the `setup()` function and potentially the `__init__` method of `AICog`
#      will need to be updated accordingly.
#
# Always consider these interactions when making changes to ensure both `ai_cog.py`
# and `bot.py` remain synchronized and functional.
# --- END LLM CONTEXT ---

import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import traceback
import asyncio
import re
from typing import Optional, List, Dict, Any, Set, Tuple
from PIL import Image
import io
from dateutil.parser import parse as date_parse
import datetime
import pytz
import contextlib

# Attempt to import Google Generative AI libraries
try:
    import google.generativeai as genai
    import google.api_core.exceptions as google_exceptions
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False
    print("WARNING (AI Cog): 'google-generativeai' or 'google-api-core' not found. AI features will be disabled.")
    # Define dummy classes/exceptions if not available, so the rest of the code doesn't break
    class genai: # type: ignore
        @staticmethod
        def configure(api_key): pass
        class GenerativeModel:
            def __init__(self, model_name): pass
            async def generate_content_async(self, contents, safety_settings=None): return None
    class google_exceptions: # type: ignore
        ResourceExhausted = Exception
        Aborted = Exception


# --- AI Prompts (Moved from bot.py) ---
# This remains a large dictionary, as per the original structure.
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
        "{human_system_instruction}\n\n"
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
        self.bot = bot
        self.supabase = supabase_client
        self.log_info = log_info_func
        self.log_error = log_error_func
        self.run_supabase_sync = run_supabase_sync_func
        
        # AI Models
        self.ai_model_2_5_flash = None
        self.ai_model_2_0_flash = None
        self.ai_model_2_0_flash_lite = None
        
        # Keyword Cache
        self.keyword_data_cache: Dict[str, Any] = {}
        self.total_keywords = 0
        self.discovered_keywords_count = 0
        
        # Configuration constants passed from main bot
        self.gemini_api_key = config.get("GEMINI_API_KEY")
        self.always_on_ai_channels = config.get("ALWAYS_ON_AI_CHANNELS", set())
        self.unrestricted_ai_channel_id = config.get("UNRESTRICTED_AI_CHANNEL_ID")
        self.keyword_table_name = config.get("KEYWORD_TABLE_NAME", "keyword_phrases")
        self.owner_user_id = config.get("OWNER_USER_ID")
        self.catercord_guild_id = config.get("CATERCORD_GUILD_ID")
        self.private_server_id = config.get("PRIVATE_SERVER_ID")
        self.random_server_id = config.get("RANDOM_SERVER_ID") # Used in get_prompt
        self.staff_channels = config.get("STAFF_CHANNELS", set())
        self.bot_commands_allowed_channel_ids = config.get("BOT_COMMANDS_ALLOWED_CHANNEL_IDS", set())
        self.command_prefix = config.get("COMMAND_PREFIX", ".")
        # This cog needs access to the main bot's ingame_name_cache for FLORR_IMAGE_NAME_EXTRACTION
        self.ingame_name_cache_ref = config.get("INGAME_NAME_CACHE_REF", [])


        if GOOGLE_AI_AVAILABLE and self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                print("AI Cog: Attempting to configure Google Gemini AI clients...")
                try:
                    self.ai_model_2_5_flash = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
                    print("  AI Cog: Successfully configured Highest Gemini model.")
                except Exception as e_highest:
                    print(f"  AI Cog WARNING: Failed to configure Highest Gemini model: {e_highest}.")
                try:
                    self.ai_model_2_0_flash = genai.GenerativeModel('gemini-2.0-flash')
                    print("  AI Cog: Successfully configured Standard Gemini model.")
                except Exception as e_standard:
                    print(f"  AI Cog WARNING: Failed to configure Standard Gemini model: {e_standard}.")
                try:
                    self.ai_model_2_0_flash_lite = genai.GenerativeModel('gemini-2.0-flash-lite')
                    print("  AI Cog: Successfully configured Lite Gemini model.")
                except Exception as e_lite:
                    print(f"  AI Cog WARNING: Failed to configure Lite Gemini model: {e_lite}.")

                if not self.ai_model_2_5_flash and not self.ai_model_2_0_flash and not self.ai_model_2_0_flash_lite:
                    print("AI Cog CRITICAL: All Google Gemini AI models failed to initialize.")
                else:
                    print("AI Cog: Google Gemini AI client configuration finished.")
            except Exception as e:
                print(f"AI Cog CRITICAL: Failed initial Google Gemini configuration step: {e}")
        elif not GOOGLE_AI_AVAILABLE:
             print("AI Cog INFO: Google AI libraries not found. AI features disabled.")
        else: # No API Key
            print("AI Cog INFO: GEMINI_API_KEY not found. AI features disabled.")

    async def cog_load(self):
        """Called when the cog is loaded."""
        # It's better to call async operations like load_keyword_data here
        # or ensure it's called from an async context after cog is ready.
        # We can schedule it as a task.
        if self.supabase:
            asyncio.create_task(self.load_keyword_data(None)) # Pass None for guild, will be handled
        else:
            print("AI Cog: Supabase client not available, cannot load keyword data.")
            
    # --- Prompt Utility ---
    def get_prompt(self, prompt_key: str, **kwargs) -> Optional[str]:
        """Retrieves and formats a prompt string from AI_PROMPTS."""
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

    # --- AI Model Utilities ---
    def get_ai_model_priority_list(self) -> List[Dict[str, Any]]:
        """Helper to get the list of available models in order of preference."""
        models = []
        if self.ai_model_2_5_flash:
            models.append({'instance': self.ai_model_2_5_flash, 'name': 'Gemini 2.5 Flash (Preview)', 'id': 'gemini_2_5_flash'})
        if self.ai_model_2_0_flash:
            models.append({'instance': self.ai_model_2_0_flash, 'name': 'Gemini 2.0 Flash', 'id': 'gemini_2_0_flash'})
        if self.ai_model_2_0_flash_lite:
            models.append({'instance': self.ai_model_2_0_flash_lite, 'name': 'Gemini 2.0 Flash Lite', 'id': 'gemini_2_0_flash_lite'})
        return models

    async def get_ai_response(
        self,
        prompt: str,
        history: Optional[List[discord.Message]] = None,
        system_instruction: Optional[str] = None,
        preferred_model_id: Optional[str] = None
    ) -> Optional[str]:
        """Generates a text response from an AI model."""
        all_available_models = self.get_ai_model_priority_list()
        if not all_available_models:
            print("AI Cog Error (get_ai_response): No AI models available.")
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
                print(f"AI Cog Warning (get_ai_response): Preferred model '{preferred_model_id}' not available. Using default priority.")
                models_to_try = all_available_models
        else:
            models_to_try = all_available_models

        if not models_to_try:
            print("AI Cog Error (get_ai_response): No models to try after filtering for preference.")
            return None

        api_contents = []
        active_system_instruction_str = system_instruction or self.get_prompt("HUMAN_SYSTEM_INSTRUCTION")

        if active_system_instruction_str:
            api_contents.append({'role': 'user', 'parts': [{'text': active_system_instruction_str}]})
            api_contents.append({'role': 'model', 'parts': [{'text': 'ok'}]})

        if history:
            for msg in history:
                role = 'model' if msg.author.id == self.bot.user.id else 'user'
                content_with_author = f"{msg.author.display_name}: {msg.content}" if role == 'user' and self.bot.user and msg.author.id != self.bot.user.id else msg.content
                api_contents.append({'role': role, 'parts': [{'text': content_with_author}]})

        api_contents.append({'role': 'user', 'parts': [{'text': prompt}]})

        last_error = None
        guild_for_log = history[-1].guild if history and history[-1].guild else None

        for model_info in models_to_try:
            model_instance = model_info['instance']
            model_name = model_info['name']
            current_model_id = model_info['id']
            if not model_instance: continue # Skip if model failed to init
            try:
                print(f"AI Cog Info (get_ai_response): Attempting generation with {model_name} (ID: {current_model_id}). Preferred: {preferred_model_id or 'None'}")
                response = await model_instance.generate_content_async(contents=api_contents)

                if not response or not response.candidates: # Added check for response itself
                    print(f"AI Cog Warning (get_ai_response): Response from {model_name} blocked or empty. Prompt feedback: {response.prompt_feedback.safety_ratings if response and response.prompt_feedback else 'N/A'}")
                    await self.log_info(guild_for_log, f"AI response from {model_name} (ID: {current_model_id}) blocked (safety filters or empty).")
                    last_error = Exception(f"Blocked by safety filters or empty response using {model_name}")
                    if preferred_model_id and current_model_id == preferred_model_id:
                        await self.log_error(guild_for_log, f"AI response from PREFERRED model {model_name} (ID: {current_model_id}) was blocked/empty.", error=last_error, ping_owner=False)
                    continue

                ai_reply = response.text
                print(f"AI Cog Info (get_ai_response): Successfully generated response with {model_name} (ID: {current_model_id}).")
                return ai_reply

            except google_exceptions.ResourceExhausted as e_rate_limit:
                log_message = f"AI Cog Rate Limit: {model_name} (ID: {current_model_id}) hit a rate limit. Attempting fallback."
                print(log_message)
                ping_owner_flag = bool(preferred_model_id and current_model_id == preferred_model_id)
                await self.log_error(guild_for_log, log_message, error=e_rate_limit, ping_owner=ping_owner_flag)
                last_error = e_rate_limit
                continue
            except Exception as e:
                log_message = f"AI Cog Error (get_ai_response): Exception with {model_name} (ID: {current_model_id}) during generation."
                print(f"{log_message} Error: {e}\n{traceback.format_exc()}")
                ping_owner_flag = True
                await self.log_error(guild_for_log, log_message, error=e, ping_owner=ping_owner_flag)
                last_error = e
                continue

        print(f"AI Cog Error (get_ai_response): All AI models failed or were skipped. Last error: {last_error}")
        if isinstance(last_error, google_exceptions.Aborted) and "blocked" in str(last_error).lower():
             return "..." # Safety block
        return None

    async def get_ai_response_with_image(
        self,
        prompt_key: str,
        image_bytes: bytes,
        prompt_kwargs: Optional[Dict[str, Any]] = None,
        preferred_model_id: str = 'gemini_2_5_flash'
    ) -> Optional[str]:
        """Generates a text response from an AI model based on a prompt and an image."""
        all_available_models = self.get_ai_model_priority_list()
        if not all_available_models:
            print("AI Cog Error (Image): No AI models available.")
            return None

        models_to_try = []
        # Logic to select model based on preference (same as get_ai_response)
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
                print(f"AI Cog Warning (Image): Preferred model '{preferred_model_id}' not available. Using default priority.")
                models_to_try = all_available_models
        else:
            models_to_try = all_available_models
        
        if not models_to_try:
            print("AI Cog Error (Image): No models to try after filtering for preference.")
            return None

        final_prompt = self.get_prompt(prompt_key, **(prompt_kwargs or {}))
        if not final_prompt:
            print(f"AI Cog Error (Image): Could not retrieve prompt for key '{prompt_key}'.")
            return None

        try:
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as e_img_open:
            print(f"AI Cog Error (Image): Could not open image bytes: {e_img_open}")
            await self.log_error(None, "Error opening image for AI in get_ai_response_with_image", error=e_img_open)
            return None

        last_error = None
        guild_for_log = None # Cannot easily get guild context here without passing it

        for model_info in models_to_try:
            model_instance = model_info['instance']
            model_name = model_info['name']
            current_model_id = model_info['id']
            if not model_instance: continue # Skip if model failed to init
            try:
                print(f"AI Cog Info (Image): Attempting generation with {model_name} (ID: {current_model_id}). Preferred: {preferred_model_id}. Prompt Key: {prompt_key}")
                response = await model_instance.generate_content_async([final_prompt, img])
                
                if not response or not response.candidates: # Added check for response itself
                    print(f"AI Cog Warning (Image): Response from {model_name} blocked or empty. Prompt feedback: {response.prompt_feedback.safety_ratings if response and response.prompt_feedback else 'N/A'}")
                    await self.log_info(guild_for_log, f"AI image response from {model_name} (ID: {current_model_id}) blocked (safety filters or empty).")
                    last_error = Exception(f"Blocked by safety filters or empty response using {model_name} for image.")
                    if preferred_model_id and current_model_id == preferred_model_id:
                        await self.log_error(guild_for_log, f"AI image response from PREFERRED model {model_name} (ID: {current_model_id}) was blocked/empty.", error=last_error, ping_owner=False)
                    continue

                ai_reply = response.text
                print(f"AI Cog Info (Image): Successfully generated response with {model_name} (ID: {current_model_id}).")
                return ai_reply

            except google_exceptions.ResourceExhausted as e_rate_limit:
                log_message = f"AI Cog Rate Limit (Image): {model_name} (ID: {current_model_id}) hit a rate limit. Attempting fallback."
                print(log_message)
                ping_owner_flag = bool(preferred_model_id and current_model_id == preferred_model_id)
                await self.log_error(guild_for_log, log_message, error=e_rate_limit, ping_owner=ping_owner_flag)
                last_error = e_rate_limit
                continue
            except Exception as e:
                log_message = f"AI Cog Error (Image): Exception with {model_name} (ID: {current_model_id}) during generation."
                print(f"{log_message} Error: {e}\n{traceback.format_exc()}")
                ping_owner_flag = True
                await self.log_error(guild_for_log, log_message, error=e, ping_owner=ping_owner_flag)
                last_error = e
                continue
                
        print(f"AI Cog Error (Image): All AI models failed for image processing. Last error: {last_error}")
        if isinstance(last_error, google_exceptions.Aborted) and "blocked" in str(last_error).lower():
            return "..."
        return None

    async def send_ai_chat_response(
        self,
        trigger_type: str,
        history: List[discord.Message],
        prompt_key_for_ai: Optional[str] = None,
        prompt_kwargs_for_ai: Optional[Dict[str, Any]] = None,
        system_instruction_key: Optional[str] = None,
        system_instruction_kwargs: Optional[Dict[str, Any]] = None,
        discovery_congrats_user: Optional[discord.User] = None,
        keyword_triggered_rule_data: Optional[Dict[str, Any]] = None,
        user_message_content: Optional[str] = None,
        interaction_for_command_reply: Optional[discord.Interaction] = None
    ):
        if not self.get_ai_model_priority_list():
            print("AI Cog Send Error: No AI models available/configured.")
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

        if interaction_for_command_reply:
            channel_to_send_in = interaction_for_command_reply.channel
            guild_for_log = interaction_for_command_reply.guild
        elif history:
            triggering_message_context = history[-1]
            channel_to_send_in = triggering_message_context.channel
            guild_for_log = triggering_message_context.guild
            if trigger_type not in ["AlwaysOn"]: # Don't reply to self for AlwaysOn
                message_to_reply_to = triggering_message_context
        else:
            print(f"AI Cog Error (send_ai_chat_response): History empty and no interaction provided for trigger '{trigger_type}'.")
            return

        if not channel_to_send_in:
            print(f"AI Cog Error (send_ai_chat_response): Could not determine channel for trigger '{trigger_type}'.")
            return

        preferred_model_id_for_call: Optional[str] = None
        final_system_instruction_str: Optional[str] = None
        actual_prompt_for_ai: Optional[str] = None

        # Determine model and system instructions
        if trigger_type == "AlwaysOn":
            preferred_model_id_for_call = 'gemini_2_0_flash'
            sys_instruct_key = system_instruction_key or "HUMAN_SYSTEM_INSTRUCTION"
            final_system_instruction_str = self.get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
            actual_prompt_for_ai = user_message_content or "(responded to chat flow)"
            if prompt_key_for_ai:
                actual_prompt_for_ai = self.get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {})) or actual_prompt_for_ai

        elif trigger_type == "Discovery" and keyword_triggered_rule_data and discovery_congrats_user:
            preferred_model_id_for_call = 'gemini_2_5_flash'
            sys_instruct_key = "KEYWORD_DISCOVERY_SYSTEM_INSTRUCTION"
            final_system_instruction_str = self.get_prompt(
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
            human_sys_instruct = self.get_prompt("HUMAN_SYSTEM_INSTRUCTION")
            final_system_instruction_str = self.get_prompt(
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
            final_system_instruction_str = self.get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
            actual_prompt_for_ai = user_message_content or "(general interaction)"
            if prompt_key_for_ai:
                actual_prompt_for_ai = self.get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {})) or actual_prompt_for_ai

        elif trigger_type.startswith("COMMAND_"): # For AI responses triggered by commands (e.g. /message with AI)
            preferred_model_id_for_call = 'gemini_2_5_flash' 
            sys_instruct_key = system_instruction_key or "BOT_PURPOSE_GENERAL"
            final_system_instruction_str = self.get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
            if not prompt_key_for_ai:
                print(f"AI Cog Send Error: No prompt_key_for_ai provided for COMMAND trigger '{trigger_type}'.")
                if interaction_for_command_reply: await interaction_for_command_reply.followup.send("Error: AI prompt missing.", ephemeral=True)
                return
            actual_prompt_for_ai = self.get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {}))
            if not actual_prompt_for_ai:
                print(f"AI Cog Send Error: Could not load prompt for key '{prompt_key_for_ai}' for trigger '{trigger_type}'.")
                if interaction_for_command_reply: await interaction_for_command_reply.followup.send("Error: AI prompt could not be loaded.", ephemeral=True)
                return
        else: # Fallback
            preferred_model_id_for_call = 'gemini_2_0_flash'
            sys_instruct_key = system_instruction_key or "HUMAN_SYSTEM_INSTRUCTION"
            final_system_instruction_str = self.get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
            actual_prompt_for_ai = user_message_content or "(general query)"
            if prompt_key_for_ai:
                actual_prompt_for_ai = self.get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {})) or actual_prompt_for_ai
        
        if not actual_prompt_for_ai:
            log_msg_content = f"AI Cog Send Error: Prompt for AI was empty for trigger '{trigger_type}'."
            if history and history[-1]: log_msg_content += f" Msg: {history[-1].id}"
            elif interaction_for_command_reply: log_msg_content += f" Interaction: {interaction_for_command_reply.id}"
            await self.log_error(guild_for_log, log_msg_content)
            if interaction_for_command_reply: await interaction_for_command_reply.followup.send("Error: AI prompt was empty.", ephemeral=True)
            return

        ai_response_processed = None
        try:
            typing_context = contextlib.nullcontext()
            if isinstance(channel_to_send_in, discord.TextChannel) and not interaction_for_command_reply:
                typing_context = channel_to_send_in.typing()

            async with typing_context:
                ai_response_raw = await self.get_ai_response(
                    prompt=actual_prompt_for_ai,
                    history=history if not interaction_for_command_reply else None,
                    system_instruction=final_system_instruction_str,
                    preferred_model_id=preferred_model_id_for_call
                )

            if not ai_response_raw:
                log_msg_content = f"AI for '{trigger_type}' (prompt key: {prompt_key_for_ai or 'N/A'}) returned None/empty."
                if history and history[-1]: log_msg_content += f" Msg: {history[-1].id}"
                elif interaction_for_command_reply: log_msg_content += f" Interaction: {interaction_for_command_reply.id}"
                await self.log_info(guild_for_log, log_msg_content)
                fail_msg = "... (couldn't think of a response right now)"
                
                if interaction_for_command_reply: await interaction_for_command_reply.followup.send(fail_msg, ephemeral=True)
                elif trigger_type == "AlwaysOn": await channel_to_send_in.send(fail_msg)
                elif message_to_reply_to: await message_to_reply_to.reply(fail_msg, mention_author=False)
                return

            ai_response_processed = ai_response_raw.strip()
            if ai_response_processed.endswith(('.', '!', '?')):
                ai_response_processed = ai_response_processed[:-1]
            
            bot_name_prefix_lower = "thenerd's pingslave:"
            if self.bot.user and self.bot.user.name:
                bot_name_prefix_lower = f"{self.bot.user.name.lower()}:"

            if ai_response_processed.lower().startswith(bot_name_prefix_lower):
                ai_response_processed = ai_response_processed[len(bot_name_prefix_lower):].lstrip()

            if len(ai_response_processed) > 1950:
                ai_response_processed = ai_response_processed[:1947] + "..."

        except Exception as ai_call_err:
            log_msg_content = f"Error during get_ai_response for '{trigger_type}' (prompt key: {prompt_key_for_ai or 'N/A'})"
            if history and history[-1]: log_msg_content += f" Msg: {history[-1].id}"
            elif interaction_for_command_reply: log_msg_content += f" Interaction: {interaction_for_command_reply.id}"
            await self.log_error(guild_for_log, log_msg_content, error=ai_call_err)
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
                    if interaction_for_command_reply.response.is_done():
                        await interaction_for_command_reply.followup.send(final_message_content_to_send, ephemeral=trigger_type.endswith("_EPHEMERAL"))
                    else:
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
                    await self.log_info(guild_for_log, log_msg_content)

            except (discord.Forbidden, discord.HTTPException) as reply_err:
                log_msg_content = f"Failed to send processed AI '{trigger_type}' response"
                if history and history[-1]: log_msg_content += f" for msg {history[-1].id}"
                elif interaction_for_command_reply: log_msg_content += f" for interaction {interaction_for_command_reply.id}"
                await self.log_error(guild_for_log, log_msg_content, error=reply_err)

    # --- Keyword Data Management ---
    async def load_keyword_data(self, guild_for_log: Optional[discord.Guild]):
        """Loads enabled keyword rules from Supabase into the in-memory cache."""
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
                await self.log_info(guild_for_log, "AI Cog: No keyword data found or failed to fetch.")
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
                incl_compiled = None
                excl_compiled = None

                try:
                    if not incl_regex_str: raise ValueError("Inclusion regex cannot be empty")
                    incl_compiled = re.compile(incl_regex_str, re.IGNORECASE)
                except (re.error, ValueError) as e:
                    compile_errors.append(f"ID '{entry_id_str}' (Identifier: {entry.get('phrase_identifier', 'N/A')}): Inclusion Regex Error: {e}")
                    continue
                try:
                    if excl_regex_str:
                        excl_compiled = re.compile(excl_regex_str, re.IGNORECASE)
                except re.error as e:
                    compile_errors.append(f"ID '{entry_id_str}' (Identifier: {entry.get('phrase_identifier', 'N/A')}): Exclusion Regex Error: {e}")

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
                log_message = "AI Cog Keyword Regex Compilation Errors:\n- " + "\n- ".join(compile_errors)
                print(f"AI Cog WARNING: {log_message}")
                await self.log_error(guild_for_log, log_message, ping_owner=False)

        except Exception as e: # Catch generic Exception from run_supabase_sync or others
            await self.log_error(guild_for_log, "AI Cog: Failed to load keyword data from Supabase", error=e, ping_owner=True)
            self.keyword_data_cache = {}
            self.total_keywords = 0
            self.discovered_keywords_count = 0

    async def record_discovery_in_db(self, guild_for_log: Optional[discord.Guild], keyword_id_str: str, user_id: int, discovery_time: datetime.datetime):
        """Updates the Supabase table to record the first discovery."""
        if not self.supabase:
            await self.log_error(guild_for_log, f"AI Cog Discovery recording failed for {keyword_id_str}: Supabase unavailable.", ping_owner=True)
            return False

        print(f"AI Cog: Recording discovery for keyword ID {keyword_id_str} by user {user_id}...")
        try:
            await self.run_supabase_sync(
                lambda: self.supabase.table(self.keyword_table_name)
                               .update({
                                   'discovered_by_user_id': str(user_id),
                                   'discovered_at': discovery_time.isoformat()
                               })
                               .eq('id', keyword_id_str)
                               .is_('discovered_by_user_id', 'null')
                               .execute()
            )
            print(f"AI Cog: Successfully recorded discovery for keyword ID {keyword_id_str}.")
            return True
        except Exception as e: # Catch generic Exception
            await self.log_error(guild_for_log, f"AI Cog: Failed to record discovery for keyword ID {keyword_id_str} in Supabase", error=e, ping_owner=True)
            return False

    # --- Event Listener for AI features ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or not self.bot.is_ready() or not self.bot.user or \
           message.author.id == self.bot.user.id or message.author.bot:
            return
        if not message.content and not message.attachments:
            return

        guild = message.guild
        channel = message.channel
        author = message.author
        
        is_catercord = guild.id == self.catercord_guild_id
        is_private_server = guild.id == self.private_server_id
        is_owner = author.id == self.owner_user_id

        is_staff_channel_catercord = False
        is_bot_commands_channel_catercord = False
        if is_catercord:
            is_staff_channel_catercord = channel.id in self.staff_channels # Uses cog's config
            is_bot_commands_channel_catercord = channel.id in self.bot_commands_allowed_channel_ids # Uses cog's config
        
        is_restricted_keyword_discovery_channel_catercord = is_staff_channel_catercord or is_bot_commands_channel_catercord

        # 1. Always-On AI Channels
        if channel.id in self.always_on_ai_channels and not message.content.startswith(self.command_prefix):
            print(f"AI Cog Trigger: Always-On Channel Message by {author.name} in #{channel.name}")
            history = []
            try:
                async for msg_hist in channel.history(limit=10, before=message): history.append(msg_hist)
                history.reverse()
                history.append(message)
            except Exception as e: print(f"AI Cog Error fetching history for AlwaysOn: {e}"); history.append(message)

            cleaned_prompt = message.content
            if not cleaned_prompt.strip() and message.stickers: cleaned_prompt = f"(User sent a sticker: {message.stickers[0].name})"
            elif not cleaned_prompt.strip(): cleaned_prompt = "(User sent an empty or attachment-only message)"
            
            await self.send_ai_chat_response(
                trigger_type="AlwaysOn", history=history, user_message_content=cleaned_prompt,
                system_instruction_key="HUMAN_SYSTEM_INSTRUCTION"
            )
            return

        # 2. Reply/Mention Trigger
        should_trigger_reply_mention = False
        is_reply_to_bot = False
        bot_mention_formats = [f'<@{self.bot.user.id}>', f'<@!{self.bot.user.id}>']

        if message.reference and message.reference.message_id:
            try:
                ref_msg = message.reference.resolved
                if not ref_msg and message.reference.channel_id == channel.id:
                    ref_msg = await channel.fetch_message(message.reference.message_id)
                if ref_msg and ref_msg.author.id == self.bot.user.id:
                    should_trigger_reply_mention = True
                    is_reply_to_bot = True
            except Exception as e_ref: print(f"AI Cog: Minor error fetching referenced message: {e_ref}")

        if not should_trigger_reply_mention and any(mention in message.content for mention in bot_mention_formats):
            should_trigger_reply_mention = True

        if should_trigger_reply_mention:
            if is_catercord and channel.id not in self.always_on_ai_channels:
                clickable_channel = f"<#{self.unrestricted_ai_channel_id}>"
                info_message_text = f"ℹ️ Psst! You can chat with me freely in {clickable_channel} for AI-powered conversations! This message will disappear shortly."
                try: await message.reply(info_message_text, mention_author=False, delete_after=7.0)
                except Exception as info_reply_err: print(f"AI Cog Error sending AI channel info message: {info_reply_err}")
                return

            can_respond_here = False
            if channel.id in self.always_on_ai_channels: can_respond_here = True
            elif not is_catercord and guild.me and guild.me.joined_at: can_respond_here = True
            
            if can_respond_here:
                print(f"AI Cog Trigger: Reply/Mention by {author.name} in #{channel.name}")
                history = []
                try:
                    async for msg_hist in channel.history(limit=10, before=message): history.append(msg_hist)
                    history.reverse()
                    history.append(message)
                except Exception as e: print(f"AI Cog Error fetching history for reply/mention: {e}"); history.append(message)

                cleaned_prompt = message.content
                for mention in bot_mention_formats: cleaned_prompt = cleaned_prompt.replace(mention, "").strip()
                if not cleaned_prompt.strip() and message.stickers: cleaned_prompt = f"(User replied/mentioned with a sticker: {message.stickers[0].name})"
                elif not cleaned_prompt.strip(): cleaned_prompt = "(just replied/mentioned, no extra text)"

                await self.send_ai_chat_response(
                    trigger_type="Reply" if is_reply_to_bot else "Mention", history=history,
                    user_message_content=cleaned_prompt, system_instruction_key="HUMAN_SYSTEM_INSTRUCTION"
                )
                return

        # 3. Keyword Detection Logic
        if self.keyword_data_cache:
            message_content_lower = message.content.lower()
            for rule_id_str, rule_data in self.keyword_data_cache.items():
                try:
                    if not isinstance(rule_data, dict) or not all(k in rule_data for k in ['inclusion_regex', 'phrase_identifier', 'speciality', 'instructions']):
                        continue
                    if rule_data.get('exclusion_regex') and rule_data['exclusion_regex'].search(message_content_lower):
                        continue
                    if not rule_data['inclusion_regex'].search(message_content_lower):
                        continue

                    rule_is_discovered = bool(rule_data.get('discovered_by'))
                    phrase_identifier = rule_data['phrase_identifier']

                    if not rule_is_discovered:
                        can_discover_this_rule = False; discovery_context_server = ""
                        if is_catercord and not is_restricted_keyword_discovery_channel_catercord and not is_owner:
                            can_discover_this_rule = True; discovery_context_server = "Catercord (Public Channel)"
                        elif is_private_server and is_owner:
                            can_discover_this_rule = True; discovery_context_server = "Private Server (Owner Discovery)"
                        
                        if can_discover_this_rule:
                            print(f"AI Cog Keyword DISCOVERY: '{phrase_identifier}' by {author.name} ({author.id}) in #{channel.name} ({guild.name} - {discovery_context_server})")
                            discovery_time = discord.utils.utcnow()
                            db_recorded = await self.record_discovery_in_db(guild, rule_id_str, author.id, discovery_time)
                            if db_recorded:
                                self.keyword_data_cache[rule_id_str]['discovered_by'] = str(author.id)
                                self.keyword_data_cache[rule_id_str]['discovered_at'] = discovery_time
                                self.discovered_keywords_count += 1
                                
                                history = []; 
                                try:
                                    async for hist_msg in channel.history(limit=5, before=message): history.append(hist_msg)
                                    history.reverse(); history.append(message)
                                except Exception as e: print(f"AI Cog Error fetching history for keyword discovery: {e}"); history.append(message)
                                
                                await self.send_ai_chat_response(
                                    trigger_type="Discovery", history=history, user_message_content=message.content,
                                    discovery_congrats_user=author, keyword_triggered_rule_data=rule_data
                                )
                                break 
                            else: await self.log_error(guild, f"AI Cog: Failed to record discovery in DB for '{phrase_identifier}' by {author.name}.", ping_owner=True)
                        continue 

                    if self.keyword_data_cache[rule_id_str].get('discovered_by'):
                        can_trigger_this_rule = False; trigger_context_server = ""
                        if is_catercord and not is_restricted_keyword_discovery_channel_catercord:
                            can_trigger_this_rule = True; trigger_context_server = "Catercord (Public Channel)"
                        elif is_private_server and is_owner:
                            can_trigger_this_rule = True; trigger_context_server = "Private Server (Owner Trigger)"
                        elif not is_catercord and not is_private_server and guild.me and guild.me.joined_at:
                            can_trigger_this_rule = True; trigger_context_server = f"Other Server ({guild.name})"
                        
                        if can_trigger_this_rule:
                            print(f"AI Cog Keyword TRIGGER: '{phrase_identifier}' by {author.name} in #{channel.name} ({guild.name} - {trigger_context_server})")
                            history = []; 
                            try:
                                async for hist_msg in channel.history(limit=5, before=message): history.append(hist_msg)
                                history.reverse(); history.append(message)
                            except Exception as e: print(f"AI Cog Error fetching history for keyword trigger: {e}"); history.append(message)
                            
                            await self.send_ai_chat_response(
                                trigger_type="Keyword", history=history, user_message_content=message.content,
                                keyword_triggered_rule_data=rule_data
                            )
                            break 
                except Exception as e_rule:
                    await self.log_error(guild, f"AI Cog Error processing keyword rule '{rule_data.get('phrase_identifier', rule_id_str)}'", error=e_rule)


    # --- AI Commands ---
    @app_commands.command(name="addkeyword", description="[Owner Only] Add a new keyword rule to the database.")
    @app_commands.describe(
        phrase_identifier="Unique identifier for this keyword (e.g., 'rule_linking').",
        inclusion_regex="Regex pattern to trigger this keyword (case-insensitive).",
        exclusion_regex="Optional regex pattern to PREVENT triggering (case-insensitive).",
        speciality="Brief topic/area the keyword relates to (for AI context).",
        instructions="Guidance for the AI on how to respond when triggered."
    )
    async def addkeyword(
        self,
        interaction: discord.Interaction,
        phrase_identifier: str,
        inclusion_regex: str,
        speciality: str,
        instructions: str,
        exclusion_regex: Optional[str] = None
    ):
        guild = interaction.guild
        if interaction.user.id != self.owner_user_id:
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return
        if not self.supabase : # Simplified check, assumes self.bot.check_supabase_available might not be directly callable or needed if self.supabase is None
            await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
            return

        if not phrase_identifier or not inclusion_regex or not speciality or not instructions:
            await interaction.response.send_message("❌ Missing required fields.", ephemeral=True)
            return
        try:
            re.compile(inclusion_regex, re.IGNORECASE)
            if exclusion_regex: re.compile(exclusion_regex, re.IGNORECASE)
        except re.error as e:
            await interaction.response.send_message(f"❌ Invalid Regex pattern: `{e}`", ephemeral=True)
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
            await self.log_info(guild, f"Owner `{interaction.user}` added keyword: `{phrase_identifier}`.")
            await self.log_info(guild, "Reloading keyword cache after addition...")
            await self.load_keyword_data(guild)
        except Exception as e: # Simplified error handling for Supabase
            err_msg = str(getattr(e, 'message', str(e))) # Get Postgrest message or generic error string
            if "unique constraint" in err_msg.lower() and f'"{self.keyword_table_name}_phrase_identifier_key"' in err_msg.lower():
                await interaction.followup.send(f"❌ Failed: Phrase Identifier `{phrase_identifier}` already exists.")
            else:
                await self.log_error(guild, f"AI Cog Keyword add failed for `{phrase_identifier}`.", error=e, interaction=interaction)
                await interaction.followup.send(f"❌ Database Error adding keyword: {err_msg[:500]}")

    @app_commands.command(name="discoveries", description="Explore the world of AI-powered secret keyword phrases!")
    async def discoveries(self, interaction: discord.Interaction):
        if not self.bot or not self.bot.user or not self.bot.user.id:
            await interaction.response.send_message("🔍 Bot not fully initialized.", ephemeral=True); return
        if not self.keyword_data_cache:
            await interaction.response.send_message("🔍 Keyword data loading. Try again shortly!", ephemeral=True); return

        guild = interaction.guild
        catercord_invite_link = "https://discord.gg/5gMRbeWNKw" # This can be made a config const
        bot_invite_link = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=68608&integration_type=0&scope=applications.commands+bot"
        description_lines = []
        is_catercord_server = guild and guild.id == self.catercord_guild_id
        bot_is_true_guild_member = guild and guild.me and guild.me.joined_at

        if is_catercord_server:
            guild_name_display = f"this server ({guild.name})" if guild and guild.name else "Catercord"
            description_lines.extend([
                f"🕵️‍♂️ I'll respond to any known secret phrases you type here in {guild_name_display}.",
                f"🎉 Be the first to find a new one, and I'll announce your grand discovery!"
            ])
        elif guild and bot_is_true_guild_member:
            description_lines.extend([
                f"🕵️‍♂️ I'll respond to *already discovered* secret phrases in this server.",
                f"➡️ To discover **new** secret phrases, join [**Catercord**]({catercord_invite_link})!"
            ])
        else:
            bot_name_display = self.bot.user.name if self.bot.user and self.bot.user.name else "this bot"
            if guild:
                guild_name_display = guild.name if guild.name and guild.name.strip() else "this server"
                description_lines.extend([
                    f"👋 Thanks for trying my keyword feature in **{guild_name_display}**!",
                    f"To let me listen here, an admin needs to formally [add {bot_name_display} to **{guild_name_display}**]({bot_invite_link}).",
                    f"➡️ For discovering **new** phrases, the adventure is in [**Catercord**]({catercord_invite_link})!"
                ])
            else: # DMs
                 description_lines.extend([
                    f"👋 Thanks for checking out my keyword feature!",
                    f"🔗 To use me in a server, an admin can [add {bot_name_display} to their server]({bot_invite_link}).",
                    f"➡️ The main place to discover **new** secret phrases is [**Catercord**]({catercord_invite_link})!"
                ])

        description_lines.append("\n---")
        if self.total_keywords > 0:
            description_lines.append(f"**Overall Progress:** {self.discovered_keywords_count} / {self.total_keywords} phrases revealed globally.")
        else:
            description_lines.append("\n*No keyword phrases are currently configured.*")

        embed = discord.Embed(title="🔮 AI Keyword Mysteries 🔮", description="\n".join(description_lines), color=discord.Color.gold()) # NERDY_YELLOW equivalent
        
        discovered_list_formatted = []
        undiscovered_count = 0
        valid_rules = [rule for rule_id, rule in self.keyword_data_cache.items() if isinstance(rule, dict) and 'phrase_identifier' in rule]
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
            embed.add_field(name="📜 Known Phrases (Discovered Globally)", value=discovered_text_joined, inline=False)
        elif self.total_keywords > 0:
            embed.add_field(name="📜 Known Phrases (Discovered Globally)", value="The scroll is blank... No phrases discovered yet!", inline=False)

        if self.total_keywords > 0 and undiscovered_count > 0:
            embed.add_field(name=f"❓ {undiscovered_count} Secret Phrase{'s' if undiscovered_count != 1 else ''} Still Hidden Globally", value="*The quest continues!*", inline=False)
        elif self.total_keywords > 0 and undiscovered_count == 0:
            embed.add_field(name="🎉 All Mysteries Solved Globally! 🎉", value="*The archives are complete!*", inline=False)

        bot_name_footer = self.bot.user.name if self.bot.user and self.bot.user.name else "Pingslave"
        embed.set_footer(text=f"Bot by TheNerd (sweet_honey) | {bot_name_footer}")
        if self.bot.user and self.bot.user.display_avatar: embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot):
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
        "NERDY_YELLOW": getattr(bot, 'NERDY_YELLOW_config', discord.Color.gold()) # Example with default
    }
    
    cog_instance = AICog(bot, 
                         getattr(bot, 'supabase_client', None), 
                         getattr(bot, 'log_info_global', None), 
                         getattr(bot, 'log_error_global', None), 
                         getattr(bot, 'run_supabase_sync_global', None), 
                         ai_cog_config)
    await bot.add_cog(cog_instance)
    print("AI Cog loaded successfully via setup.")