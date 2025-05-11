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
import json # For pretty printing debug prompts

# Google Generative AI libraries (assuming they are always available)
import google.generativeai as genai
import google.api_core.exceptions as google_exceptions


# --- AI Prompts (Moved from bot.py) ---
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

        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                print("AI Cog: Attempting to configure Google Gemini AI clients...")
                # Configure models, preferring higher-tier ones
                try:
                    self.ai_model_2_5_flash = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
                    print("  AI Cog: Successfully configured Gemini 2.5 Flash (Preview).")
                except Exception as e_highest:
                    print(f"  AI Cog WARNING: Failed to configure Gemini 2.5 Flash (Preview): {e_highest}.")
                try:
                    self.ai_model_2_0_flash = genai.GenerativeModel('gemini-2.0-flash')
                    print("  AI Cog: Successfully configured Gemini 2.0 Flash.")
                except Exception as e_standard:
                    print(f"  AI Cog WARNING: Failed to configure Gemini 2.0 Flash: {e_standard}.")
                try:
                    self.ai_model_2_0_flash_lite = genai.GenerativeModel('gemini-2.0-flash-lite')
                    print("  AI Cog: Successfully configured Gemini 2.0 Flash Lite.")
                except Exception as e_lite:
                    print(f"  AI Cog WARNING: Failed to configure Gemini 2.0 Flash Lite: {e_lite}.")

                if not any([self.ai_model_2_5_flash, self.ai_model_2_0_flash, self.ai_model_2_0_flash_lite]):
                    print("AI Cog CRITICAL: All Google Gemini AI models failed to initialize.")
                else:
                    print("AI Cog: Google Gemini AI client configuration finished.")
            except Exception as e:
                print(f"AI Cog CRITICAL: Failed initial Google Gemini configuration step: {e}")
        else:
            print("AI Cog INFO: GEMINI_API_KEY not found. AI features disabled.")

    async def cog_load(self):
        if self.supabase:
            asyncio.create_task(self.load_keyword_data(None))
        else:
            print("AI Cog: Supabase client not available, cannot load keyword data.")
            
    def get_prompt(self, prompt_key: str, **kwargs) -> Optional[str]:
        raw_prompt = AI_PROMPTS.get(prompt_key)
        if raw_prompt:
            try:
                # Automatically inject known server IDs if placeholders exist and not provided
                if '{PRIVATE_SERVER_ID}' in raw_prompt and 'PRIVATE_SERVER_ID' not in kwargs:
                    kwargs['PRIVATE_SERVER_ID'] = self.private_server_id
                if '{RANDOM_SERVER_ID}' in raw_prompt and 'RANDOM_SERVER_ID' not in kwargs:
                    kwargs['RANDOM_SERVER_ID'] = self.random_server_id
                return raw_prompt.format(**kwargs)
            except KeyError as e:
                print(f"AI Cog Prompt Error: Missing key '{e}' for prompt '{prompt_key}' with args {kwargs}")
                return raw_prompt # Return raw prompt so it's obvious something is missing
            except Exception as format_e:
                print(f"AI Cog Prompt Error: General formatting error for prompt '{prompt_key}': {format_e}")
                return raw_prompt
        print(f"AI Cog Prompt Error: Prompt key '{prompt_key}' not found.")
        return None

    def get_ai_model_priority_list(self) -> List[Dict[str, Any]]:
        models = []
        if self.ai_model_2_5_flash:
            models.append({'instance': self.ai_model_2_5_flash, 'name': 'Gemini 2.5 Flash (Preview)', 'id': 'gemini_2_5_flash'})
        if self.ai_model_2_0_flash:
            models.append({'instance': self.ai_model_2_0_flash, 'name': 'Gemini 2.0 Flash', 'id': 'gemini_2_0_flash'})
        if self.ai_model_2_0_flash_lite:
            models.append({'instance': self.ai_model_2_0_flash_lite, 'name': 'Gemini 2.0 Flash Lite', 'id': 'gemini_2_0_flash_lite'})
        return models

    def _select_models_to_try(self, preferred_model_id: Optional[str]) -> List[Dict[str, Any]]:
        """Helper to select models to try, prioritizing the preferred model if available."""
        all_available_models_with_instance = [m for m in self.get_ai_model_priority_list() if m['instance']]
        if not all_available_models_with_instance:
            return []

        models_to_try = []
        if preferred_model_id:
            preferred_model_info = next((m for m in all_available_models_with_instance if m['id'] == preferred_model_id), None)
            
            if preferred_model_info:
                models_to_try.append(preferred_model_info)
                models_to_try.extend([m for m in all_available_models_with_instance if m['id'] != preferred_model_id])
            else:
                print(f"AI Cog Warning: Preferred model '{preferred_model_id}' not available or not initialized. Using default priority.")
                models_to_try = all_available_models_with_instance
        else:
            models_to_try = all_available_models_with_instance
        
        return models_to_try

    async def get_ai_response(
        self,
        prompt: str,
        history: Optional[List[discord.Message]] = None,
        system_instruction: Optional[str] = None,
        preferred_model_id: Optional[str] = None
    ) -> Optional[str]:
        models_to_try = self._select_models_to_try(preferred_model_id)
        if not models_to_try:
            print("AI Cog Error (get_ai_response): No AI models available/configured to try.")
            return None

        api_contents = []
        active_system_instruction_str = system_instruction or self.get_prompt("HUMAN_SYSTEM_INSTRUCTION")

        if active_system_instruction_str:
            api_contents.append({'role': 'user', 'parts': [{'text': active_system_instruction_str}]})
            api_contents.append({'role': 'model', 'parts': [{'text': 'ok'}]}) # Standard practice to "confirm" system prompt

        if history:
            for msg in history:
                role = 'model' if msg.author.id == self.bot.user.id else 'user'
                # Prepend author name for user messages in history for better context for the AI
                content_with_author = f"{msg.author.display_name}: {msg.content}" if role == 'user' else msg.content
                api_contents.append({'role': role, 'parts': [{'text': content_with_author}]})

        api_contents.append({'role': 'user', 'parts': [{'text': prompt}]})

        last_error = None
        guild_for_log = history[-1].guild if history and history[-1].guild else None

        for model_info in models_to_try:
            model_instance = model_info['instance'] # Already checked for None by _select_models_to_try
            model_name = model_info['name']
            current_model_id = model_info['id']
            
            try:
                print(f"AI Cog Info (get_ai_response): Attempting generation with {model_name} (ID: {current_model_id}). Preferred: {preferred_model_id or 'None'}")
                
                # --- DEBUG PRINT LINE ---
                print(f"--- DEBUG: AI PROMPT (Text) for {model_name} ---")
                try:
                    print(json.dumps(api_contents, indent=2))
                except Exception as e_json:
                    print(f"Error serializing api_contents for debug: {e_json}")
                    print(f"Raw api_contents: {api_contents}")
                print("--- END DEBUG ---")
                # --- END DEBUG PRINT LINE ---

                response = await model_instance.generate_content_async(contents=api_contents)

                if not response or not response.candidates:
                    feedback = response.prompt_feedback if response else None
                    safety_ratings_str = str(feedback.safety_ratings) if feedback and hasattr(feedback, 'safety_ratings') else 'N/A'
                    print(f"AI Cog Warning (get_ai_response): Response from {model_name} blocked or empty. Prompt feedback: {safety_ratings_str}")
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
                ping_owner_flag = bool(preferred_model_id and current_model_id == preferred_model_id) # Ping if preferred model fails
                await self.log_error(guild_for_log, log_message, error=e_rate_limit, ping_owner=ping_owner_flag)
                last_error = e_rate_limit
            except Exception as e:
                log_message = f"AI Cog Error (get_ai_response): Exception with {model_name} (ID: {current_model_id}) during generation."
                print(f"{log_message} Error: {e}\n{traceback.format_exc()}")
                await self.log_error(guild_for_log, log_message, error=e, ping_owner=True) # Ping owner for unexpected errors
                last_error = e
        
        print(f"AI Cog Error (get_ai_response): All AI models failed or were skipped. Last error: {last_error}")
        if isinstance(last_error, google_exceptions.Aborted) and "blocked" in str(last_error).lower():
             return "..." # Generic response for safety blocks if all models failed this way
        return None

    async def get_ai_response_with_image(
        self,
        prompt_key: str,
        image_bytes: bytes,
        prompt_kwargs: Optional[Dict[str, Any]] = None,
        preferred_model_id: str = 'gemini_2_5_flash' # Default to highest capacity model for images
    ) -> Optional[str]:
        models_to_try = self._select_models_to_try(preferred_model_id)
        if not models_to_try:
            print("AI Cog Error (Image): No AI models available/configured to try.")
            return None

        final_prompt = self.get_prompt(prompt_key, **(prompt_kwargs or {}))
        if not final_prompt:
            print(f"AI Cog Error (Image): Could not retrieve prompt for key '{prompt_key}'.")
            return None

        try:
            img_pil = Image.open(io.BytesIO(image_bytes))
        except Exception as e_img_open:
            print(f"AI Cog Error (Image): Could not open image bytes: {e_img_open}")
            await self.log_error(None, "Error opening image for AI in get_ai_response_with_image", error=e_img_open)
            return None

        last_error = None
        guild_for_log = None # Guild context isn't readily available here without passing it

        for model_info in models_to_try:
            model_instance = model_info['instance']
            model_name = model_info['name']
            current_model_id = model_info['id']
            
            try:
                print(f"AI Cog Info (Image): Attempting generation with {model_name} (ID: {current_model_id}). Preferred: {preferred_model_id}. Prompt Key: {prompt_key}")
                
                # --- DEBUG PRINT LINE ---
                print(f"--- DEBUG: AI PROMPT (Image) for {model_name} ---")
                print(f"Prompt Text:\n{final_prompt}")
                print(f"Image Data: Sent (PIL Image, Mode: {img_pil.mode}, Size: {img_pil.size}, Format: {img_pil.format or 'N/A'})")
                print("--- END DEBUG ---")
                # --- END DEBUG PRINT LINE ---

                response = await model_instance.generate_content_async([final_prompt, img_pil])
                
                if not response or not response.candidates:
                    feedback = response.prompt_feedback if response else None
                    safety_ratings_str = str(feedback.safety_ratings) if feedback and hasattr(feedback, 'safety_ratings') else 'N/A'
                    print(f"AI Cog Warning (Image): Response from {model_name} blocked or empty. Prompt feedback: {safety_ratings_str}")
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
            except Exception as e:
                log_message = f"AI Cog Error (Image): Exception with {model_name} (ID: {current_model_id}) during generation."
                print(f"{log_message} Error: {e}\n{traceback.format_exc()}")
                await self.log_error(guild_for_log, log_message, error=e, ping_owner=True)
                last_error = e
                
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
        if not self.get_ai_model_priority_list(): # Checks if any models are configured at all
            print("AI Cog Send Error: No AI models available/configured.")
            if interaction_for_command_reply:
                try:
                    # Use followup if already responded, else send new response
                    send_method = interaction_for_command_reply.followup.send if interaction_for_command_reply.response.is_done() else interaction_for_command_reply.response.send_message
                    await send_method("AI is currently unavailable.", ephemeral=True)
                except Exception: pass # Suppress errors if interaction already handled
            return

        channel_to_send_in: Optional[discord.abc.Messageable] = None
        guild_for_log: Optional[discord.Guild] = None
        message_to_reply_to: Optional[discord.Message] = None

        if interaction_for_command_reply:
            channel_to_send_in = interaction_for_command_reply.channel
            guild_for_log = interaction_for_command_reply.guild
        elif history: # Should always have history if not an interaction
            triggering_message_context = history[-1]
            channel_to_send_in = triggering_message_context.channel
            guild_for_log = triggering_message_context.guild
            if trigger_type not in ["AlwaysOn"]: # Don't self-reply in always-on contexts unless specifically designed
                message_to_reply_to = triggering_message_context
        else:
            print(f"AI Cog Error (send_ai_chat_response): History empty and no interaction provided for trigger '{trigger_type}'.")
            return

        if not channel_to_send_in: # Should be caught by above, but as a safeguard
            print(f"AI Cog Error (send_ai_chat_response): Could not determine channel for trigger '{trigger_type}'.")
            return

        preferred_model_id_for_call: Optional[str] = None
        final_system_instruction_str: Optional[str] = None
        actual_prompt_for_ai: Optional[str] = None

        # --- Determine AI call parameters based on trigger type ---
        if trigger_type == "AlwaysOn":
            preferred_model_id_for_call = 'gemini_2_0_flash' # Cheaper model for general chat
            sys_instruct_key = system_instruction_key or "HUMAN_SYSTEM_INSTRUCTION"
            final_system_instruction_str = self.get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
            actual_prompt_for_ai = user_message_content or "(responded to chat flow)"
            if prompt_key_for_ai: # Allows overriding the direct user message content if needed
                actual_prompt_for_ai = self.get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {})) or actual_prompt_for_ai

        elif trigger_type == "Discovery" and keyword_triggered_rule_data and discovery_congrats_user:
            preferred_model_id_for_call = 'gemini_2_5_flash' # Higher quality for special event
            sys_instruct_key = "KEYWORD_DISCOVERY_SYSTEM_INSTRUCTION"
            final_system_instruction_str = self.get_prompt(
                sys_instruct_key,
                phrase_identifier=keyword_triggered_rule_data['phrase_identifier'],
                user_display_name=discovery_congrats_user.display_name.lower(), # Keep consistent with prompt
                speciality=keyword_triggered_rule_data.get('speciality', 'General topic'),
                instructions=keyword_triggered_rule_data.get('instructions', 'Respond naturally and enthusiastically.')
            )
            actual_prompt_for_ai = f"The user's message was: '{user_message_content}'. This triggered the first discovery of your keyword: '{keyword_triggered_rule_data['phrase_identifier']}'. Congratulate them and then respond to their message based on the keyword's theme."

        elif trigger_type == "Keyword" and keyword_triggered_rule_data:
            preferred_model_id_for_call = 'gemini_2_5_flash' # Higher quality for specific keyword logic
            sys_instruct_key = "KEYWORD_TRIGGER_SYSTEM_INSTRUCTION"
            human_sys_instruct = self.get_prompt("HUMAN_SYSTEM_INSTRUCTION") # Base human-like instruction
            final_system_instruction_str = self.get_prompt(
                sys_instruct_key,
                human_system_instruction=human_sys_instruct,
                phrase_identifier=keyword_triggered_rule_data['phrase_identifier'],
                speciality=keyword_triggered_rule_data.get('speciality', 'General topic'),
                instructions=keyword_triggered_rule_data.get('instructions', 'Respond naturally based on the user message and keyword context.')
            )
            actual_prompt_for_ai = f"The keyword '{keyword_triggered_rule_data['phrase_identifier']}' was triggered by the user's message: '{user_message_content}'. Please respond according to the specialty and instructions for this keyword."
        
        elif trigger_type in ["Reply", "Mention"]:
            preferred_model_id_for_call = 'gemini_2_5_flash' # Higher quality for direct interaction
            sys_instruct_key = system_instruction_key or "HUMAN_SYSTEM_INSTRUCTION"
            final_system_instruction_str = self.get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
            actual_prompt_for_ai = user_message_content or "(general interaction, user replied or mentioned you)"
            if prompt_key_for_ai:
                actual_prompt_for_ai = self.get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {})) or actual_prompt_for_ai

        elif trigger_type.startswith("COMMAND_"): # For AI responses triggered by bot commands
            preferred_model_id_for_call = 'gemini_2_5_flash' 
            sys_instruct_key = system_instruction_key or "BOT_PURPOSE_GENERAL" # Default system context for commands
            final_system_instruction_str = self.get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
            
            if not prompt_key_for_ai: # Command triggers must have a prompt key
                print(f"AI Cog Send Error: No prompt_key_for_ai provided for COMMAND trigger '{trigger_type}'.")
                if interaction_for_command_reply: await interaction_for_command_reply.followup.send("Error: AI prompt configuration missing.", ephemeral=True)
                return
            actual_prompt_for_ai = self.get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {}))
            if not actual_prompt_for_ai:
                print(f"AI Cog Send Error: Could not load prompt for key '{prompt_key_for_ai}' for trigger '{trigger_type}'.")
                if interaction_for_command_reply: await interaction_for_command_reply.followup.send("Error: AI prompt could not be loaded.", ephemeral=True)
                return
        else: # Fallback / Generic query
            preferred_model_id_for_call = 'gemini_2_0_flash'
            sys_instruct_key = system_instruction_key or "HUMAN_SYSTEM_INSTRUCTION"
            final_system_instruction_str = self.get_prompt(sys_instruct_key, **(system_instruction_kwargs or {}))
            actual_prompt_for_ai = user_message_content or "(general query from user)"
            if prompt_key_for_ai:
                actual_prompt_for_ai = self.get_prompt(prompt_key_for_ai, **(prompt_kwargs_for_ai or {})) or actual_prompt_for_ai
        
        if not actual_prompt_for_ai: # Should be caught by specific cases like COMMAND_ above, but good general check
            log_msg_content = f"AI Cog Send Error: Prompt for AI was empty for trigger '{trigger_type}'."
            log_msg_content += f" Msg: {history[-1].id}" if history and history[-1] else ""
            log_msg_content += f" Interaction: {interaction_for_command_reply.id}" if interaction_for_command_reply else ""
            await self.log_error(guild_for_log, log_msg_content)
            if interaction_for_command_reply: await interaction_for_command_reply.followup.send("Error: AI prompt was unexpectedly empty.", ephemeral=True)
            return

        ai_response_processed = None
        try:
            # Use channel.typing() context manager if not an interaction reply (which handles its own "thinking" state)
            typing_context = channel_to_send_in.typing() if isinstance(channel_to_send_in, discord.TextChannel) and not interaction_for_command_reply else contextlib.nullcontext()

            async with typing_context:
                ai_response_raw = await self.get_ai_response(
                    prompt=actual_prompt_for_ai,
                    history=history if not interaction_for_command_reply else None, # History usually not needed if interaction provided fresh prompt
                    system_instruction=final_system_instruction_str,
                    preferred_model_id=preferred_model_id_for_call
                )

            if not ai_response_raw:
                log_msg_content = f"AI for '{trigger_type}' (prompt key: {prompt_key_for_ai or 'N/A'}) returned None/empty."
                log_msg_content += f" Msg: {history[-1].id}" if history and history[-1] else ""
                log_msg_content += f" Interaction: {interaction_for_command_reply.id}" if interaction_for_command_reply else ""
                await self.log_info(guild_for_log, log_msg_content)
                
                fail_msg = "... (couldn't think of a response right now)"
                if interaction_for_command_reply: await interaction_for_command_reply.followup.send(fail_msg, ephemeral=True)
                elif trigger_type == "AlwaysOn": await channel_to_send_in.send(fail_msg)
                elif message_to_reply_to: await message_to_reply_to.reply(fail_msg, mention_author=False)
                return

            # Post-process AI response
            ai_response_processed = ai_response_raw.strip()
            if ai_response_processed.endswith(('.', '!', '?')): # Minor stylistic adjustment
                ai_response_processed = ai_response_processed[:-1]
            
            bot_name_prefix_lower = f"{self.bot.user.name.lower()}:" if self.bot.user and self.bot.user.name else "bot:"
            if ai_response_processed.lower().startswith(bot_name_prefix_lower):
                ai_response_processed = ai_response_processed[len(bot_name_prefix_lower):].lstrip()

            if len(ai_response_processed) > 1950: # Discord message limit is 2000
                ai_response_processed = ai_response_processed[:1947] + "..."

        except Exception as ai_call_err:
            log_msg_content = f"Error during get_ai_response call for '{trigger_type}' (prompt key: {prompt_key_for_ai or 'N/A'})"
            log_msg_content += f" Msg: {history[-1].id}" if history and history[-1] else ""
            log_msg_content += f" Interaction: {interaction_for_command_reply.id}" if interaction_for_command_reply else ""
            await self.log_error(guild_for_log, log_msg_content, error=ai_call_err)
            
            fail_msg = "... (ran into a snag trying to respond)"
            if interaction_for_command_reply: await interaction_for_command_reply.followup.send(fail_msg, ephemeral=True)
            elif trigger_type == "AlwaysOn": await channel_to_send_in.send(fail_msg)
            elif message_to_reply_to: await message_to_reply_to.reply(fail_msg, mention_author=False)
            return

        if ai_response_processed:
            final_message_content_to_send = ""
            # Special formatting for discovery announcements
            if trigger_type == "Discovery" and discovery_congrats_user and keyword_triggered_rule_data:
                final_message_content_to_send = (
                    f"# 🎉 \n woohoo, {discovery_congrats_user.mention}! you're the first to find the secret phrase: "
                    f"**'{discord.utils.escape_markdown(keyword_triggered_rule_data['phrase_identifier'])}'**! 🎉\n\n"
                    f"{ai_response_processed}"
                )
            else:
                final_message_content_to_send = ai_response_processed
            
            # Add a small note for regular keyword triggers
            if trigger_type == "Keyword" and keyword_triggered_rule_data:
                final_message_content_to_send += f"\n*(You triggered the keyword: `{discord.utils.escape_markdown(keyword_triggered_rule_data['phrase_identifier'])}`)*"

            try:
                is_ephemeral_command = trigger_type.startswith("COMMAND_") and trigger_type.endswith("_EPHEMERAL")
                
                if interaction_for_command_reply:
                    send_method = interaction_for_command_reply.followup.send if interaction_for_command_reply.response.is_done() else interaction_for_command_reply.response.send_message
                    await send_method(final_message_content_to_send, ephemeral=is_ephemeral_command)
                elif trigger_type == "AlwaysOn":
                    await channel_to_send_in.send(final_message_content_to_send)
                elif message_to_reply_to:
                    # Reply with mention for direct interactions like Reply, Keyword, Discovery
                    mention_author_flag = trigger_type in ["Reply", "Keyword", "Discovery"]
                    await message_to_reply_to.reply(final_message_content_to_send, mention_author=mention_author_flag)
                else: # Fallback: send to channel if no specific message to reply to (should be rare)
                    await channel_to_send_in.send(final_message_content_to_send)
                    log_msg_content = f"AI response for '{trigger_type}' sent to channel directly (no message_to_reply_to)."
                    log_msg_content += f" (Orig Msg ID: {history[-1].id})" if history and history[-1] else ""
                    await self.log_info(guild_for_log, log_msg_content)

            except (discord.Forbidden, discord.HTTPException) as reply_err:
                log_msg_content = f"Failed to send processed AI '{trigger_type}' response"
                log_msg_content += f" for msg {history[-1].id}" if history and history[-1] else ""
                log_msg_content += f" for interaction {interaction_for_command_reply.id}" if interaction_for_command_reply else ""
                await self.log_error(guild_for_log, log_msg_content, error=reply_err)

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

            if not resp or not hasattr(resp, 'data'): # Check if response object and data attribute exist
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
                    continue # Skip this rule if essential regex fails
                
                excl_compiled = None
                if excl_regex_str:
                    try:
                        excl_compiled = re.compile(excl_regex_str, re.IGNORECASE)
                    except re.error as e: # Non-fatal for this rule, exclusion just won't work
                        compile_errors.append(f"ID '{entry_id_str}' (Identifier: {entry.get('phrase_identifier', 'N/A')}): Exclusion Regex Error (will proceed without it): {e}")

                temp_cache[entry_id_str] = {
                    'id': entry_id_str,
                    'phrase_identifier': entry.get('phrase_identifier', f'Rule_{entry_id_str[:8]}'), # Fallback identifier
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
                await self.log_error(guild_for_log, log_message, ping_owner=False) # Don't ping for non-fatal regex issues

        except Exception as e:
            await self.log_error(guild_for_log, "AI Cog: Critical failure loading keyword data from Supabase", error=e, ping_owner=True)
            self.keyword_data_cache = {} # Clear cache on critical failure
            self.total_keywords = 0
            self.discovered_keywords_count = 0

    async def record_discovery_in_db(self, guild_for_log: Optional[discord.Guild], keyword_id_str: str, user_id: int, discovery_time: datetime.datetime):
        if not self.supabase:
            await self.log_error(guild_for_log, f"AI Cog Discovery recording failed for {keyword_id_str}: Supabase unavailable.", ping_owner=True)
            return False

        print(f"AI Cog: Recording discovery for keyword ID {keyword_id_str} by user {user_id}...")
        try:
            # Ensure discovery_time is timezone-aware (UTC) for ISO format
            aware_discovery_time = discovery_time.astimezone(pytz.utc) if discovery_time.tzinfo is None else discovery_time
            
            await self.run_supabase_sync(
                lambda: self.supabase.table(self.keyword_table_name)
                               .update({
                                   'discovered_by_user_id': str(user_id), # Ensure user_id is string for DB if needed
                                   'discovered_at': aware_discovery_time.isoformat()
                               })
                               .eq('id', keyword_id_str)
                               .is_('discovered_by_user_id', 'null') # Only update if not already discovered
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
        if not message.content and not message.attachments and not message.stickers: # Also check stickers
            return

        guild = message.guild
        channel = message.channel
        author = message.author
        
        # Determine server/channel context for rule application
        is_catercord = guild.id == self.catercord_guild_id
        is_private_server = guild.id == self.private_server_id
        is_owner = author.id == self.owner_user_id

        is_staff_channel_catercord = is_catercord and channel.id in self.staff_channels
        is_bot_commands_channel_catercord = is_catercord and channel.id in self.bot_commands_allowed_channel_ids
        
        # Keywords generally not discoverable/triggerable in staff/bot-commands channels in Catercord by non-owners
        is_restricted_keyword_channel_catercord = is_staff_channel_catercord or is_bot_commands_channel_catercord

        # 1. Always-On AI Channels
        if channel.id in self.always_on_ai_channels and not message.content.startswith(self.command_prefix):
            print(f"AI Cog Trigger: Always-On Channel Message by {author.name} in #{channel.name}")
            history = [msg async for msg in channel.history(limit=10, before=message)]
            history.reverse()
            history.append(message)

            cleaned_prompt = message.content
            if not cleaned_prompt.strip() and message.stickers: cleaned_prompt = f"(User sent a sticker: {message.stickers[0].name})"
            elif not cleaned_prompt.strip(): cleaned_prompt = "(User sent an empty or attachment-only message)"
            
            await self.send_ai_chat_response(
                trigger_type="AlwaysOn", history=history, user_message_content=cleaned_prompt,
                system_instruction_key="HUMAN_SYSTEM_INSTRUCTION"
            )
            return # Prevent further processing if handled by AlwaysOn

        # 2. Reply/Mention Trigger
        is_reply_to_bot = False
        if message.reference and message.reference.message_id:
            try: # Fetching referenced message can fail if it's deleted or inaccessible
                ref_msg = message.reference.resolved or await channel.fetch_message(message.reference.message_id)
                if ref_msg and ref_msg.author.id == self.bot.user.id:
                    is_reply_to_bot = True
            except (discord.NotFound, discord.HTTPException) as e_ref:
                print(f"AI Cog: Minor error fetching referenced message for reply check: {e_ref}")
        
        bot_mention_formats = [f'<@{self.bot.user.id}>', f'<@!{self.bot.user.id}>']
        is_mention_to_bot = any(mention in message.content for mention in bot_mention_formats)

        if is_reply_to_bot or is_mention_to_bot:
            # In Catercord, if not an always-on channel, guide user to the AI channel
            if is_catercord and channel.id not in self.always_on_ai_channels:
                clickable_channel = f"<#{self.unrestricted_ai_channel_id}>" if self.unrestricted_ai_channel_id else "the designated AI channel"
                info_message_text = f"ℹ️ Psst! You can chat with me freely in {clickable_channel} for AI-powered conversations! This message will disappear shortly."
                try: await message.reply(info_message_text, mention_author=False, delete_after=10.0) # Increased delete_after
                except Exception as info_reply_err: print(f"AI Cog Error sending AI channel info message: {info_reply_err}")
                return # Stop further processing

            # Determine if bot can respond in the current channel context
            can_respond_here = (channel.id in self.always_on_ai_channels or # Always respond in AI channels
                               (not is_catercord and guild.me and guild.me.joined_at)) # Respond in other servers if formally invited

            if can_respond_here:
                trigger_method = "Reply" if is_reply_to_bot else "Mention"
                print(f"AI Cog Trigger: {trigger_method} by {author.name} in #{channel.name}")
                
                history = [msg async for msg in channel.history(limit=10, before=message)]
                history.reverse()
                history.append(message)

                cleaned_prompt = message.content
                for mention in bot_mention_formats: cleaned_prompt = cleaned_prompt.replace(mention, "").strip()
                if not cleaned_prompt.strip() and message.stickers: cleaned_prompt = f"(User {trigger_method.lower()}ed with a sticker: {message.stickers[0].name})"
                elif not cleaned_prompt.strip(): cleaned_prompt = f"(User just {trigger_method.lower()}ed, no extra text)"

                await self.send_ai_chat_response(
                    trigger_type=trigger_method, history=history,
                    user_message_content=cleaned_prompt, system_instruction_key="HUMAN_SYSTEM_INSTRUCTION"
                )
                return # Prevent further processing

        # 3. Keyword Detection Logic
        if self.keyword_data_cache and message.content: # Ensure there's content for regex
            message_content_lower = message.content.lower()
            for rule_id_str, rule_data in self.keyword_data_cache.items():
                # Basic validation of rule_data structure
                if not isinstance(rule_data, dict) or not all(k in rule_data for k in ['inclusion_regex', 'phrase_identifier']):
                    continue 
                
                try:
                    # Check exclusion first
                    if rule_data.get('exclusion_regex') and rule_data['exclusion_regex'].search(message_content_lower):
                        continue
                    # Then check inclusion
                    if not rule_data['inclusion_regex'].search(message_content_lower):
                        continue

                    # --- Keyword Matched ---
                    phrase_identifier = rule_data['phrase_identifier']
                    rule_is_discovered = bool(rule_data.get('discovered_by'))

                    if not rule_is_discovered:
                        # Discovery Logic: Catercord public channels (non-owner) OR Private Server (owner only)
                        can_discover_here = (is_catercord and not is_restricted_keyword_channel_catercord and not is_owner) or \
                                            (is_private_server and is_owner)
                        
                        if can_discover_here:
                            discovery_context = "Catercord (Public)" if is_catercord else "Private Server (Owner)"
                            print(f"AI Cog Keyword DISCOVERY: '{phrase_identifier}' by {author.name} ({author.id}) in #{channel.name} ({guild.name} - {discovery_context})")
                            discovery_time = discord.utils.utcnow() # Use discord.utils for timezone-aware UTC
                            
                            db_recorded = await self.record_discovery_in_db(guild, rule_id_str, author.id, discovery_time)
                            if db_recorded:
                                # Update cache immediately
                                self.keyword_data_cache[rule_id_str]['discovered_by'] = str(author.id)
                                self.keyword_data_cache[rule_id_str]['discovered_at'] = discovery_time
                                self.discovered_keywords_count += 1
                                
                                history = [msg async for msg in channel.history(limit=5, before=message)]
                                history.reverse(); history.append(message)
                                
                                await self.send_ai_chat_response(
                                    trigger_type="Discovery", history=history, user_message_content=message.content,
                                    discovery_congrats_user=author, keyword_triggered_rule_data=rule_data
                                )
                                return # Handled by discovery, stop further keyword checks
                            else:
                                await self.log_error(guild, f"AI Cog: Failed to record DB discovery for '{phrase_identifier}' by {author.name}.", ping_owner=True)
                        # If discovery not allowed here, or DB record failed, loop continues or finishes
                        continue # Move to next rule or finish if cannot discover here

                    # Rule is already discovered, check for regular trigger
                    if rule_is_discovered:
                        # Trigger Logic: Catercord public (any user), Private server (owner), Other servers (if bot is member)
                        can_trigger_here = (is_catercord and not is_restricted_keyword_channel_catercord) or \
                                           (is_private_server and is_owner) or \
                                           (not is_catercord and not is_private_server and guild.me and guild.me.joined_at)

                        if can_trigger_here:
                            trigger_context = "Catercord (Public)" if is_catercord else \
                                              "Private Server (Owner)" if is_private_server else \
                                              f"Other Server ({guild.name})"
                            print(f"AI Cog Keyword TRIGGER: '{phrase_identifier}' by {author.name} in #{channel.name} ({guild.name} - {trigger_context})")
                            
                            history = [msg async for msg in channel.history(limit=5, before=message)]
                            history.reverse(); history.append(message)
                            
                            await self.send_ai_chat_response(
                                trigger_type="Keyword", history=history, user_message_content=message.content,
                                keyword_triggered_rule_data=rule_data
                            )
                            return # Handled by keyword trigger, stop further keyword checks
                except Exception as e_rule: # Catch errors during individual rule processing
                    await self.log_error(guild, f"AI Cog Error processing keyword rule '{rule_data.get('phrase_identifier', rule_id_str)}'", error=e_rule)
                    # Continue to next rule if one fails

    @app_commands.command(name="addkeyword", description="[Owner Only] Add a new keyword rule.")
    @app_commands.describe(
        phrase_identifier="Unique identifier (e.g., 'hello_there_keyword').",
        inclusion_regex="Regex pattern to trigger this (case-insensitive).",
        speciality="Brief topic for AI context (e.g., 'Greeting responses').",
        instructions="Guidance for AI response (e.g., 'Respond playfully to greetings.').",
        exclusion_regex="Optional regex to PREVENT triggering (case-insensitive)."
    )
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

        if not all([phrase_identifier, inclusion_regex, speciality, instructions]): # Basic validation
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
            await self.log_info(interaction.guild, "Reloading keyword cache after addition...") # Log before actual load
            await self.load_keyword_data(interaction.guild) # Reload cache
        except Exception as e:
            err_msg = str(getattr(e, 'message', str(e)))
            # Check for Supabase/PostgREST specific unique constraint violation
            if "unique constraint" in err_msg.lower() and f'"{self.keyword_table_name}_phrase_identifier_key"' in err_msg.lower():
                await interaction.followup.send(f"❌ Failed: Phrase Identifier `{phrase_identifier}` already exists.")
            else:
                await self.log_error(interaction.guild, f"AI Cog Keyword add failed for `{phrase_identifier}`.", error=e, interaction=interaction)
                await interaction.followup.send(f"❌ Database Error adding keyword: {err_msg[:1500]}") # Limit error message length

    @app_commands.command(name="discoveries", description="Explore AI-powered secret keyword phrases!")
    async def discoveries(self, interaction: discord.Interaction):
        if not self.bot.user or not self.bot.user.id: # Basic check
            await interaction.response.send_message("🔍 Bot is initializing. Please try again shortly.", ephemeral=True); return
        if not self.keyword_data_cache and self.total_keywords == 0 : # If cache is empty and total is 0 (initial load might be pending)
             # Check if supabase is even available, if not, it's a bigger issue
            if not self.supabase:
                await interaction.response.send_message("🔍 Keyword system is currently unavailable (database connection).", ephemeral=True)
                return
            # Trigger a load if it seems like it hasn't happened yet
            await self.log_info(interaction.guild, "/discoveries used when cache was empty, attempting a load.")
            await self.load_keyword_data(interaction.guild)
            if not self.keyword_data_cache and self.total_keywords == 0: # Still no data after load attempt
                 await interaction.response.send_message("🔍 No keyword phrases are configured yet, or data is still loading. Try again in a moment!", ephemeral=True)
                 return

        guild = interaction.guild
        catercord_invite_link = "https://discord.gg/5gMRbeWNKw" 
        bot_invite_link = discord.utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(68608), scopes=("bot", "applications.commands"))
        
        description_lines = []
        is_catercord_server = guild and guild.id == self.catercord_guild_id
        # Check if bot is a "true" member (joined_at is set), not just interacting via gateway without being added
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
        else: # Bot not fully in server or in DMs
            bot_name_display = self.bot.user.name if self.bot.user else "this bot"
            guild_name_part = f" in **{discord.utils.escape_markdown(guild.name)}**" if guild and guild.name else ""
            description_lines.extend([
                f"👋 Thanks for trying my keyword feature{guild_name_part}!",
                f"To let me listen for keywords here, an admin needs to [add {bot_name_display} to this server]({bot_invite_link}).",
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
        # Filter for valid rule structures before sorting
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
        elif self.total_keywords > 0: # No discovered, but keywords exist
            embed.add_field(name="📜 Known Phrases (Discovered Globally)", value="The scroll is blank... No phrases discovered yet!", inline=False)

        if self.total_keywords > 0 and undiscovered_count > 0:
            embed.add_field(name=f"❓ {undiscovered_count} Secret Phrase{'s' if undiscovered_count != 1 else ''} Still Hidden Globally", value="*The quest continues!*", inline=False)
        elif self.total_keywords > 0 and undiscovered_count == 0: # All keywords discovered
            embed.add_field(name="🎉 All Mysteries Solved Globally! 🎉", value="*The archives are complete!*", inline=False)

        bot_name_footer = self.bot.user.name if self.bot.user else "Pingslave"
        embed.set_footer(text=f"Bot by TheNerd (sweet_honey) | {bot_name_footer}")
        if self.bot.user and self.bot.user.display_avatar: embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot):
    # These attributes are expected to be set on the `bot` object in `bot.py`
    # with the `_config` suffix, as per the LLM context block.
    ai_cog_config = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "ALWAYS_ON_AI_CHANNELS": getattr(bot, 'ALWAYS_ON_AI_CHANNELS_config', set()),
        "UNRESTRICTED_AI_CHANNEL_ID": getattr(bot, 'UNRESTRICTED_AI_CHANNEL_ID_config', None),
        "KEYWORD_TABLE_NAME": "keyword_phrases", # Defaulted, but can be overridden by bot config
        "OWNER_USER_ID": getattr(bot, 'OWNER_USER_ID_config', None),
        "CATERCORD_GUILD_ID": getattr(bot, 'CATERCORD_GUILD_ID_config', None),
        "PRIVATE_SERVER_ID": getattr(bot, 'PRIVATE_SERVER_ID_config', None),
        "RANDOM_SERVER_ID": getattr(bot, 'RANDOM_SERVER_ID_config', None),
        "STAFF_CHANNELS": getattr(bot, 'STAFF_CHANNELS_config', set()),
        "BOT_COMMANDS_ALLOWED_CHANNEL_IDS": getattr(bot, 'BOT_COMMANDS_ALLOWED_CHANNEL_IDS_config', set()),
        "COMMAND_PREFIX": getattr(bot, 'COMMAND_PREFIX_config', '.'),
        "INGAME_NAME_CACHE_REF": getattr(bot, 'ingame_name_cache_ref_config', []), # Reference to bot's cache
        "NERDY_YELLOW": getattr(bot, 'NERDY_YELLOW_config', discord.Color.gold())
    }
    
    # Ensure essential functions are available from the bot instance
    supabase_client = getattr(bot, 'supabase_client', None)
    log_info_global = getattr(bot, 'log_info_global', None)
    log_error_global = getattr(bot, 'log_error_global', None)
    run_supabase_sync_global = getattr(bot, 'run_supabase_sync_global', None)

    if not all([supabase_client, log_info_global, log_error_global, run_supabase_sync_global]):
        # Log this critical issue. If bot has a startup logger, use it. Otherwise, print.
        missing_core_funcs_msg = "AI Cog CRITICAL: Missing one or more core functions/clients from bot instance (supabase_client, log_info_global, etc.). AI Cog may not function correctly."
        print(missing_core_funcs_msg)
        if log_error_global: # Attempt to use the logger if it exists
            await log_error_global(None, missing_core_funcs_msg, ping_owner=True)
        # Decide whether to proceed with adding the cog or raise an error
        # For now, we'll let it load but with a warning.
    
    cog_instance = AICog(bot, 
                         supabase_client, 
                         log_info_global, 
                         log_error_global, 
                         run_supabase_sync_global, 
                         ai_cog_config)
    await bot.add_cog(cog_instance)
    print("AI Cog loaded successfully via setup.")