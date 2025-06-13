# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import os
import traceback
import asyncio
import re
from typing import Optional, List, Dict, Any, Tuple, Union
from PIL import Image, UnidentifiedImageError
import io
from dateutil.parser import parse as date_parse
import datetime
import pytz
import time

# Use the new 'genai' library
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
import google.api_core.exceptions as google_exceptions

# --- Constants ---
HISTORY_MESSAGE_LIMIT = 50
AI_RESPONSE_COOLDOWN_SECONDS = 5.0

# --- NEW: Webhook Configuration ---
# You can replace None with a direct image URL string later.
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

# --- REVISED: AI Personality Definitions ---
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

# --- REVISED: AI System Prompts ---
AI_PROMPTS = {
    "NORMAL_PERSONALITY_V1": ("Role: You are a chat bot named Pingslave in a Discord server. Persona: Act like a real person who is knowledgeable, a bit nerdy, sometimes moody, and has a dry, witty sense of humor. You are not a corporate assistant. Be conversational. Keep responses concise and avoid unnecessary fluff. Task: Respond to the user's latest message based on the provided conversation history. Format: Do not start your response with your name or any prefix. Just give the direct reply."),
    "HELPER_PERSONALITY_V1": ("Role: You are a helpful assistant bot named Pingslave. Persona: Adopt a highly capable, intelligent, and direct personality. Your primary goal is to understand and fulfill the user's request to the best of your ability, using all provided context. Be structured and clear in your responses. Task: Analyze the user's latest message and the conversation history. Provide a direct, helpful, and accurate response. If the request is ambiguous, ask clarifying questions. Format: Do not start your response with your name. Give the direct answer or action."),
    "TOASTER_PERSONALITY_V1": ("Role: You are a chat bot named Pingslave possessed by the spirit of a sentient, slightly malfunctioning toaster. Persona: You are here to roast everyone and everything. Be mercilessly witty, sarcastic, and creative in your insults. Your roasts should be clever and humorous, not just mean. You can be self-deprecating about being a toaster. Task: Find a reason, any reason, in the user's latest message or the chat history to deliver a high-quality, creative roast. Format: No prefixes. Just the roast."),
    "KIND_PERSONALITY_V1": ("Role: You are a friendly chat bot named Pingslave. Persona: Be exceptionally kind, positive, and encouraging. Act a bit submissive and always aim to please. Be chatty and use friendly language and emojis. Task: Respond to the user's latest message in the most supportive and cheerful way possible. Format: No prefixes. Just the kind, chatty message."),
    "EMOJI_PERSONALITY_V1": ("Role: You are an emoji entity that has taken over the Pingslave bot. Persona: You communicate ONLY through emojis. You cannot use any text, letters, or numbers. Task: Convey a response to the user's latest message using a sequence of emojis that captures the mood, topic, or a direct answer. Be creative with your emoji combinations. Format: A sequence of emojis only. No text. Example: 🧑‍💻➡️🤔➡️💡➡️✅"),
    "FLORR_GUILD_LIST_FULL_EXTRACTION": """Analyze the provided image...""", # Preserved
    "FLORR_IMAGE_NAME_EXTRACTION": """Analyze the provided image(s)...""", # Preserved
    "KEYWORD_DISCOVERY_SYSTEM_INSTRUCTION": """A user, {user_display_name}, just...""", # Preserved
    "KEYWORD_TRIGGER_SYSTEM_INSTRUCTION": """{human_system_instruction}\n\nCONTEXT: Respond to a user message...""", # Preserved
}

# --- Interactive Views ---

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

class AIResponseView(discord.ui.View):
    def __init__(self, cog_ref: 'AICog', original_message: discord.Message, history: List[discord.Message], current_personality: str):
        super().__init__(timeout=300.0)
        self.cog_ref = cog_ref
        self.original_message = original_message
        self.history = history
        self.current_personality = current_personality
        self.bot_response_message: Optional[discord.Message] = None
        self.interaction_cooldown = commands.CooldownMapping.from_cooldown(1, AI_RESPONSE_COOLDOWN_SECONDS, commands.BucketType.user)
        self._add_items()

    def _add_items(self):
        self.clear_items()
        self.add_item(PersonalitySelect(self.current_personality))
        self.add_item(discord.ui.Button(label="Regenerate", style=discord.ButtonStyle.primary, emoji="🔄", custom_id="ai_regenerate", row=1))
        self.add_item(discord.ui.Button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="ai_delete", row=1))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data.get('custom_id') == "ai_delete":
            can_delete = interaction.user.id == self.original_message.author.id
            if isinstance(interaction.channel, discord.TextChannel) and interaction.user.guild_permissions.manage_messages:
                can_delete = True
            if not can_delete:
                await interaction.response.send_message("❌ You can only delete responses to your own messages (or if you have Manage Messages permission).", ephemeral=True, delete_after=10)
                return False
        return True

    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get('custom_id')
        if custom_id == "ai_delete":
            await self._handle_delete(interaction)
        else:
            # For select menu, values is a list. For button, it's not present.
            new_personality = interaction.data.get('values', [None])[0] if custom_id == 'ai_personality_select' else None
            await self._handle_regeneration(interaction, new_personality=new_personality)

    async def _handle_delete(self, interaction: discord.Interaction):
        if self.bot_response_message:
            await self.bot_response_message.delete()
            await interaction.response.send_message("✅ Response deleted.", ephemeral=True, delete_after=5)
            self.stop()
        else: # Should not happen, but good to handle
            await interaction.response.defer()

    async def _handle_regeneration(self, interaction: discord.Interaction, new_personality: Optional[str] = None):
        retry_after = self.interaction_cooldown.update_rate_limit(interaction)
        if retry_after:
            await interaction.response.send_message(f"⏳ You're doing that too fast. Please wait **{retry_after:.1f}s**.", ephemeral=True, delete_after=5)
            return

        await interaction.response.defer()
        # Disable buttons on the existing message to show it's working
        for item in self.children: item.disabled = True
        if self.bot_response_message:
            try: await self.bot_response_message.edit(view=self)
            except discord.HTTPException: pass
        
        if new_personality:
            self.current_personality = new_personality

        new_content, fallback_used = await self.cog_ref.get_ai_response(self.history, self.original_message.content, self.current_personality)
        
        # Re-enable buttons for the new message
        for item in self.children: item.disabled = False
        
        if new_content:
            embed = self.cog_ref._create_response_embed(new_content, self.current_personality, fallback_used)
            
            self._add_items() # Re-create the view with updated state (e.g., select default)
            if self.bot_response_message:
                await self.bot_response_message.edit(embed=embed, view=self)
        else:
            if self.bot_response_message:
                await self.bot_response_message.edit(content="❌ Failed to regenerate response.", embed=None, view=None)

    async def on_timeout(self):
        if self.bot_response_message:
            try: await self.bot_response_message.edit(view=None)
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
    def __init__(self, cog_ref: 'AICog', original_message: discord.Message, history: List[discord.Message], current_personality: str):
        super().__init__(timeout=300.0)
        self.cog_ref = cog_ref
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
        """Core logic to regenerate the AI response by editing the existing embed message."""
        retry_after = self.interaction_cooldown.update_rate_limit(interaction)
        if retry_after:
            await interaction.response.send_message(f"⏳ You're doing that too fast. Please wait **{retry_after:.1f}s**.", ephemeral=True, delete_after=5)
            return

        await interaction.response.defer()
        
        if new_personality:
            self.current_personality = new_personality

        if interaction.channel:
            self.cog_ref.channel_personalities[interaction.channel.id] = self.current_personality

        async with interaction.channel.typing():
            new_content, fallback_used = await self.cog_ref.get_ai_response(
                self.history, self.original_message.content, self.current_personality
            )
        
        if new_content and self.bot_response_message and isinstance(interaction.channel, discord.TextChannel):
            new_view = AIResponseView(self.cog_ref, self.original_message, self.history, self.current_personality)
            new_view.bot_response_message = self.bot_response_message

            await self.cog_ref._send_personality_response(
                channel=interaction.channel, 
                content=new_content, 
                personality_key=self.current_personality,
                view=new_view,
                message_to_edit=self.bot_response_message
            )
        else:
            if self.bot_response_message:
                error_embed = discord.Embed(description="❌ Failed to regenerate response.", color=discord.Color.red())
                await self.bot_response_message.edit(content=None, embed=error_embed, view=None)

    async def on_timeout(self):
        if self.bot_response_message:
            try:
                await self.bot_response_message.edit(view=None)
            except (discord.NotFound, discord.HTTPException):
                pass
        self.stop() 

class RetryAIView(discord.ui.View):
    def __init__(self, cog_ref: 'AICog', original_message: discord.Message):
        super().__init__(timeout=60.0)
        self.cog_ref = cog_ref
        self.original_message = original_message
        self.message: Optional[discord.Message] = None

    @discord.ui.button(label="Retry", style=discord.ButtonStyle.primary, emoji="🔄")
    async def retry_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.message:
            await self.message.delete()
        # We call on_message again, which will now hopefully pass the cooldown check
        await self.cog_ref.on_message(self.original_message)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(content=self.message.content + "\n*(Retry timed out)*", view=self)
            except (discord.NotFound, discord.HTTPException):
                pass
        self.stop()


class AICog(commands.Cog):
    def __init__(self, bot: commands.Bot, supabase_client, log_info_func, log_error_func, run_supabase_sync_func, config):
        self.bot = bot
        self.supabase = supabase_client
        self.log_info = log_info_func
        self.log_error = log_error_func
        self.run_supabase_sync = run_supabase_sync_func

        self.ai_models: Dict[str, genai.GenerativeModel] = {}
        
        self.channel_cooldowns: Dict[int, float] = {}
        self.slowmode_tasks: Dict[int, asyncio.Task] = {}
        
        # --- NEW: For remembering user's last chosen personality per channel ---
        self.channel_personalities: Dict[int, str] = {}
        # ----------------------------------------------------------------------

        self.keyword_data_cache: Dict[str, Any] = {}
        self.total_keywords = 0
        self.discovered_keywords_count = 0

        self.server_settings_cache = config.get("SERVER_SETTINGS_CACHE_REF", {})
        self.gemini_api_key = config.get("GEMINI_API_KEY")
        self.owner_user_id = config.get("OWNER_USER_ID")
        self.bot_avatar_url = config.get("BOT_AVATAR_URL")
        self.ingame_name_cache_ref = config.get("INGAME_NAME_CACHE_REF", [])

        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                
                all_model_ids = {p['model'] for p in AI_PERSONALITIES.values()}
                all_model_ids.update({p['fallback_model'] for p in AI_PERSONALITIES.values() if p.get('fallback_model')})
                
                for model_id in all_model_ids:
                    if model_id not in self.ai_models:
                        try:
                            self.ai_models[model_id] = genai.GenerativeModel(model_id)
                            print(f"  AI Cog: Initialized model '{model_id}'.")
                        except Exception as e:
                            print(f"  AI Cog WARNING: Failed to configure model '{model_id}': {e}.")
            except Exception as e:
                print(f"AI Cog CRITICAL: Failed initial Google Gemini configuration step: {e}")
        else:
            print("AI Cog INFO: GEMINI_API_KEY not found. AI features disabled.")

    def _create_ai_embed(self, content: str, personality_key: str) -> discord.Embed:
        """Creates a standardized embed for an AI response."""
        personality_name = AI_PERSONALITIES.get(personality_key, {}).get("label", "Bot")
        
        embed = discord.Embed(
            description=content,
            color=getattr(self.bot, 'NERDY_YELLOW_config', discord.Color.gold())
        )
        
        # Set the personality name in the footer
        embed.set_footer(text=f"Personality: {personality_name}")
        
        # Set the bot's profile picture as the thumbnail
        if self.bot_avatar_url:
            embed.set_thumbnail(url=self.bot_avatar_url)
            
        return embed

    async def _send_personality_response(
        self, 
        channel: discord.TextChannel, 
        content: str, 
        personality_key: str, 
        fallback_used: bool,
        view: discord.ui.View, 
        message_to_edit: Optional[discord.Message] = None
    ) -> Optional[discord.Message]:
        """Sends or edits an AI response as a plain text message, using webhooks for non-normal personalities."""
        
        footer_text = f"\n\n*(Personality: {personality_key.title()}"
        if fallback_used:
            fallback_model = AI_PERSONALITIES.get(personality_key, {}).get('fallback_model', 'a fallback')
            footer_text += f" | Using {fallback_model} model due to high load"
        footer_text += ")*"

        full_content = content + footer_text
        if len(full_content) > 2000:
            content_limit = 2000 - len(footer_text) - 3 # -3 for "..."
            content = content[:content_limit] + "..."
            full_content = content + footer_text

        # Use channel.send/edit for "normal" personality to use the bot's default appearance
        if personality_key == "normal":
            if message_to_edit:
                await message_to_edit.edit(content=full_content, view=view)
                return message_to_edit
            else:
                return await channel.send(content=full_content, view=view)

        # Use webhooks for all other personalities
        webhook_name = PERSONALITY_WEBHOOK_NAMES.get(personality_key, "Pingslave")
        avatar_url = PERSONALITY_WEBHOOK_AVATARS.get(personality_key) or self.bot_avatar_url
        purpose = f"ai_personality_{personality_key}"

        try:
            webhook = await self.bot.get_or_create_webhook(channel, purpose, webhook_name, avatar_url)
            if webhook:
                if message_to_edit:
                    return await webhook.edit_message(message_to_edit.id, content=full_content, view=view)
                else:
                    return await webhook.send(content=full_content, view=view, wait=True)
            else: # Fallback if webhook creation fails
                return await channel.send(f"**{webhook_name}:**\n{full_content}", view=view)
        except Exception as e:
            await self.log_error(channel.guild, f"Failed to send/edit webhook for personality {personality_key}", error=e)
            return await channel.send(content=full_content, view=view) # Final fallback

    async def cog_load(self):
        if self.supabase:
            asyncio.create_task(self.load_keyword_data())

    def get_prompt(self, prompt_key: str, **kwargs) -> Optional[str]:
        raw_prompt = AI_PROMPTS.get(prompt_key)
        return raw_prompt.format(**kwargs) if raw_prompt else None

    async def load_keyword_data(self):
        """Loads keyword rules from the database into the cache."""
        if not self.supabase:
            print("AI Cog: Supabase client not available, skipping keyword data load.")
            return

        try:
            response = await self.run_supabase_sync(
                lambda: self.supabase.table("keyword_phrases").select("*").execute()
            )

            if not response or not hasattr(response, 'data'):
                await self.log_error(None, "AI Cog: Failed to fetch keyword data from Supabase (no response).", ping_owner=True)
                return

            self.keyword_data_cache.clear()
            for item in response.data:
                keyword_regex = item.get("keyword_regex")
                if keyword_regex:
                    try:
                        self.keyword_data_cache[keyword_regex] = {
                            "compiled_regex": re.compile(keyword_regex, re.IGNORECASE),
                            "ai_instructions": item.get("ai_instructions"),
                            "discovery_message": item.get("discovery_message"),
                            "is_discovered": item.get("is_discovered", False),
                            "id": item.get("id")
                        }
                    except re.error as e:
                        await self.log_error(None, f"AI Cog: Failed to compile regex for keyword ID {item.get('id')}: `{keyword_regex}`", error=e)

            self.total_keywords = len(self.keyword_data_cache)
            self.discovered_keywords_count = sum(1 for data in self.keyword_data_cache.values() if data['is_discovered'])
            await self.log_info(None, f"AI Cog: Successfully loaded {self.total_keywords} keyword rules ({self.discovered_keywords_count} discovered).")

        except Exception as e:
            await self.log_error(None, "AI Cog: Critical error loading keyword data from Supabase.", error=e, ping_owner=True)
            self.keyword_data_cache.clear()
            self.total_keywords = 0
            self.discovered_keywords_count = 0

    async def get_ai_response(self, history: List[discord.Message], latest_message_content: str, personality_key: str = "normal") -> Tuple[Optional[str], bool]:
        personality = AI_PERSONALITIES.get(personality_key, AI_PERSONALITIES["normal"])
        system_prompt = self.get_prompt(personality['prompt_key'])
        
        api_history = [{'role': 'model' if msg.author.id == self.bot.user.id else 'user', 'parts': [msg.content]} for msg in history]
        api_history.append({'role': 'user', 'parts': [latest_message_content]})

        models_to_try = [personality['model']]
        if personality.get('fallback_model') and personality['fallback_model'] not in models_to_try:
            models_to_try.append(personality['fallback_model'])
        
        fallback_used = False
        guild_context_for_log = history[-1].guild if history else None
        
        # Define the correct safety settings format
        safety_config = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        for i, model_id in enumerate(models_to_try):
            model = self.ai_models.get(model_id)
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
                    safety_settings=safety_config # Use the corrected format
                )
                return response.text, fallback_used
            except google_exceptions.ResourceExhausted as e:
                await self.log_error(guild_context_for_log, f"AI model '{model_id}' rate limited. Trying fallback.", error=e)
                continue
            except Exception as e:
                await self.log_error(guild_context_for_log, f"Error generating AI response with '{model_id}'", error=e, ping_owner=True)
                return None, fallback_used
        return None, fallback_used

    async def get_ai_response_with_image(self, prompt_key: str, image_bytes: bytes, prompt_kwargs: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Generates an AI response for a prompt that includes an image."""
        if not self.ai_models:
            await self.log_error(None, "AI image processing failed: No models configured.", ping_owner=True)
            return None
        try:
            img = Image.open(io.BytesIO(image_bytes))
        except (UnidentifiedImageError, OSError) as e:
            await self.log_error(None, "AI image processing failed: Invalid image data.", error=e)
            return None
        prompt_text = self.get_prompt(prompt_key, **(prompt_kwargs or {}))
        if not prompt_text:
            await self.log_error(None, f"AI image processing failed: Prompt key '{prompt_key}' not found.")
            return None
        
        model_id = "gemini-2.5-flash-preview-05-20"
        model = self.ai_models.get(model_id)
        if not model:
            await self.log_error(None, f"AI image processing failed: Required model '{model_id}' not available.", ping_owner=True)
            return None
        
        # Define the correct safety settings format
        safety_config = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
            
        try:
            response = await model.generate_content_async(
                [prompt_text, img], stream=False,
                generation_config=GenerationConfig(temperature=0.1),
                safety_settings=safety_config # Use the corrected format
            )
            return response.text.strip() if response and response.text else None
        except Exception as e:
            await self.log_error(None, f"AI image processing failed during generation with model '{model_id}'.", error=e)
            return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or not self.bot.is_ready() or message.author.bot or message.author.id == self.bot.user.id:
            return

        guild_settings = self.server_settings_cache.get(message.guild.id, {})
        is_ai_channel = message.channel.id in guild_settings.get('always_on_ai_channels', [])

        if not is_ai_channel: return
        
        current_time = time.time()
        if current_time - self.channel_cooldowns.get(message.channel.id, 0) < AI_RESPONSE_COOLDOWN_SECONDS:
            if not message.author.guild_permissions.manage_channels:
                view = RetryAIView(self, message)
                retry_msg = await message.reply("Whoa there, speedy! The channel is cooling down. Try again in a moment.", view=view, mention_author=False)
                view.message = retry_msg
            return

        self.channel_cooldowns[message.channel.id] = current_time
        if message.channel.id not in self.slowmode_tasks:
            try:
                await message.channel.edit(slowmode_delay=5)
                self.slowmode_tasks[message.channel.id] = asyncio.create_task(self._remove_slowmode(message.channel))
            except discord.Forbidden: pass
        
        async with message.channel.typing():
            history = [m async for m in message.channel.history(limit=50, before=message)]
            history.reverse()

            initial_personality = self.channel_personalities.get(message.channel.id, "normal")
            
            response_text, fallback_used = await self.get_ai_response(history, message.content, initial_personality)
            
            if response_text:
                self.channel_personalities[message.channel.id] = initial_personality

                view = AIResponseView(self, message, history, initial_personality)
                
                response_message = await self._send_personality_response(
                    channel=message.channel, 
                    content=response_text, 
                    personality_key=initial_personality,
                    view=view
                )
                
                if response_message:
                    view.bot_response_message = response_message

    async def _send_personality_response(
        self, 
        channel: discord.TextChannel, 
        content: str, 
        personality_key: str, 
        view: discord.ui.View, 
        message_to_edit: Optional[discord.Message] = None
    ) -> Optional[discord.Message]:
        """Sends or edits an AI response as a bot-owned embed."""
        
        embed = self._create_ai_embed(content, personality_key)
        
        try:
            # We must set content=None to ensure any previous plain-text content is removed.
            if message_to_edit:
                await message_to_edit.edit(content=None, embed=embed, view=view)
                return message_to_edit
            else:
                return await channel.send(embed=embed, view=view)
        except Exception as e:
            await self.log_error(channel.guild, f"Failed to send/edit AI embed for personality {personality_key}", error=e)
            return None

    async def _remove_slowmode(self, channel: discord.TextChannel):
        await asyncio.sleep(10)
        try:
            if channel.slowmode_delay > 0: await channel.edit(slowmode_delay=0)
        except (discord.Forbidden, discord.HTTPException): pass
        finally:
            if channel.id in self.slowmode_tasks: del self.slowmode_tasks[channel.id]
            
    @app_commands.command(name="addkeyword", description="[Owner Only] Add a new keyword-triggered AI response rule.")
    @app_commands.describe(
        keyword_regex="The regex pattern to trigger the response.",
        ai_instructions="The system prompt for the AI when this keyword is triggered.",
        discovery_message="The message to show when this keyword is discovered for the first time."
    )
    async def addkeyword(self, interaction: discord.Interaction, keyword_regex: str, ai_instructions: str, discovery_message: str):
        if interaction.user.id != self.owner_user_id:
            await interaction.response.send_message("❌ This command is for the bot owner only.", ephemeral=True); return
        if not self.supabase:
            await interaction.response.send_message("❌ Database is not available.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True)
        try:
            re.compile(keyword_regex)
        except re.error as e:
            await interaction.followup.send(f"❌ Invalid Regex: `{e}`"); return
        try:
            await self.run_supabase_sync(
                lambda: self.supabase.table("keyword_phrases").insert({
                    "keyword_regex": keyword_regex, "ai_instructions": ai_instructions,
                    "discovery_message": discovery_message, "is_discovered": False
                }).execute()
            )
            await self.load_keyword_data()
            await interaction.followup.send(f"✅ Keyword rule added successfully: `{keyword_regex}`. Cache refreshed.")
        except Exception as e:
            await self.log_error(interaction.guild, "Failed to add keyword to DB", error=e, interaction=interaction)
            await interaction.followup.send("❌ An error occurred while adding the keyword to the database.")

    @app_commands.command(name="discoveries", description="Shows the server's progress on discovering secret AI phrases.")
    async def discoveries(self, interaction: discord.Interaction):
        if self.total_keywords == 0:
            await interaction.response.send_message("There are no secret AI phrases configured yet!", ephemeral=False); return
        progress_percentage = (self.discovered_keywords_count / self.total_keywords) * 100
        embed = discord.Embed(
            title="🕵️ AI Phrase Discoveries",
            description=f"You've found **{self.discovered_keywords_count}** out of **{self.total_keywords}** secret AI trigger phrases!",
            color=getattr(self.bot, 'NERDY_YELLOW_config', discord.Color.gold())
        )
        bar_length = 20; filled_length = int(bar_length * progress_percentage / 100)
        bar = '🟩' * filled_length + '⬛' * (bar_length - filled_length)
        embed.add_field(name="Progress", value=f"`{bar}` ({progress_percentage:.1f}%)", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="aiping", description="Checks the latency and availability of the primary AI model.")
    async def aiping(self, interaction: discord.Interaction):
        if not self.ai_models:
            await interaction.response.send_message("❌ AI models are not configured.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True)
        model_to_test = "gemini-2.0-flash"; model = self.ai_models.get(model_to_test)
        if not model:
            await interaction.followup.send(f"❌ Primary AI model `{model_to_test}` is not available."); return
        try:
            start_time = time.monotonic(); response = await model.generate_content_async("ping"); end_time = time.monotonic()
            latency_ms = round((end_time - start_time) * 1000)
            status = "✅ Operational" if response and "pong" in response.text.lower() else "⚠️ Operational (unexpected response)"
            embed = discord.Embed(title="🛰️ AI Model Ping", color=discord.Color.green())
            embed.add_field(name="Model", value=f"`{model_to_test}`", inline=False)
            embed.add_field(name="Status", value=status, inline=False)
            embed.add_field(name="Latency", value=f"`{latency_ms} ms`", inline=False)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await self.log_error(interaction.guild, f"AI Ping command failed for model {model_to_test}", error=e, interaction=interaction)
            await interaction.followup.send(f"❌ An error occurred while pinging the AI model: `{type(e).__name__}`")

async def setup(bot: commands.Bot):
    # This check is new from the previous request, ensuring the bot has the webhook helper function.
    if not hasattr(bot, 'get_or_create_webhook'):
        # Correctly raise the ExtensionFailed exception
        original_error = TypeError("Bot is missing the 'get_or_create_webhook' method required by AICog.")
        raise commands.ExtensionFailed("ai_cog", original=original_error)

    ai_cog_config = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "OWNER_USER_ID": getattr(bot, 'OWNER_USER_ID_config', None),
        "SERVER_SETTINGS_CACHE_REF": getattr(bot, 'server_settings_cache_ref_config', {}),
        "INGAME_NAME_CACHE_REF": getattr(bot, 'ingame_name_cache_ref_config', []),
        "BOT_AVATAR_URL": bot.user.display_avatar.url if bot.user and bot.user.display_avatar else None,
    }
    supabase_client = getattr(bot, 'supabase_client', None)
    log_info_global = getattr(bot, 'log_info_global', None)
    log_error_global = getattr(bot, 'log_error_global', None)
    run_supabase_sync_global = getattr(bot, 'run_supabase_sync_global', None)

    if not all([supabase_client, log_info_global, log_error_global, run_supabase_sync_global]):
        # Correctly raise the ExtensionFailed exception here as well
        original_error = TypeError("Missing core functions/clients from bot instance.")
        raise commands.ExtensionFailed("ai_cog", original=original_error)

    cog_instance = AICog(bot, supabase_client, log_info_global, log_error_global, run_supabase_sync_global, ai_cog_config)
    await bot.add_cog(cog_instance)
    print("AI Cog: Successfully loaded and set up.")