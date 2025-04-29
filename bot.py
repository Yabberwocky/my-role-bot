# -*- coding: utf-8 -*-
import os
import threading
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button, button
from flask import Flask
from supabase import create_client, Client
from postgrest import APIError
import traceback
import math

# --- CONTEXT FOR FUTURE LLMS ---
# (Please do not remove this comment block)
#
# Bot Name: TheNerd's Pingslave
# Owner: Vibhor / TheNerd / sweet_honey (Discord ID: 1230848174218940416)
# Target Server: Catercord (This bot is intended for use only in this specific server)
# Primary Purpose: Manage verification and information related to the "[HC1]" guild within the game Florr.io.
#   - "[HC1]" is a guild in Florr.io, originally named "HC". Members can be HC or non-HC.
#   - The bot verifies members, stores their in-game names (IGNs) in Supabase,
#     maintains a static public list of HC members in a dedicated channel,
#     provides an interactive paginated list via /hcmembers, and offers utility commands.
# Hosting Environment:
#   - Code Files: `bot.py` (this file), `requirements.txt` (listing discord, supabase, flask)
#   - Platform: Render (Free Tier) via a private GitHub repository.
#   - Keep-Alive: Uses a basic Flask web server (`keep_alive` function) monitored by an external
#     service (like Uptime Robot) hitting the Flask endpoint to prevent Render's free instance from sleeping.
#   - Environment Variables: DISCORD_BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY are set directly in Render's environment settings.
# Database: Supabase (PostgreSQL) used to store HC member IGNs linked to Discord IDs.
# Key Features: /verify, /hcverify (stores IGN), static list updates, /hcmembers (interactive list), /syncnicknames, /wither.
# --- END CONTEXT ---

# --- Configuration ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
REMOVE_ROLE_ID = 1360176495947022447
ADD_ROLE_ID_VERIFY = 1248708073019805717
ADD_ROLE_ID_HC = 1230235110415274004
ALLOWED_CHANNEL_IDS = {1354431395140731165, 1330664430148780102, 1248710731407560835}
HC_MEMBER_LIST_CHANNEL_ID = 1354431395140731165
HC_LIST_EMBED_TITLE = "**\[HC1\] Guild Members**"
ALLOWED_WITHER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692}
SELF_PROTECTED_ID = 1230848174218940416
BOT_ID = 1365572437185400893
MAX_WITHER_SECONDS = 600
INFO_LOG_CHANNEL_ID = 1317943895606165579
ERROR_LOG_CHANNEL_ID = 1362988767367135453
MEMBERS_PER_PAGE = 50
NERDY_YELLOW = discord.Color.gold()

# --- Supabase Client ---
if SUPABASE_URL and SUPABASE_KEY:
    try: supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY); print("Supabase client created.")
    except Exception as e: print(f"CRITICAL: Supabase client failed: {e}"); supabase = None
else: print("CRITICAL: Supabase credentials missing."); supabase = None

# --- Discord Setup ---
intents = discord.Intents.default(); intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents); tree = bot.tree

# --- Flask App ---
# *** Corrected Flask Setup ***
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    try:
        # Use a larger port if 8080 causes issues in your environment
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        print(f"Flask server failed to start: {e}")

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.start()
    print("Keep alive thread started.")
# *** End Corrected Flask Setup ***

# --- Utility Functions ---
async def run_supabase_sync(func):
    try: return await bot.loop.run_in_executor(None, func)
    except APIError as api_err: print(f"Supabase API Error: {api_err}"); raise
    except Exception as e: print(f"Executor Error: {e}"); raise

# --- Logging ---
async def log_to_channel(channel_id: int, guild: discord.Guild, message: str = None, embed: discord.Embed = None):
    if not guild: print(f"Log Error: No guild for channel {channel_id}. Msg: {message or 'Embed'}") ; return
    log_channel = guild.get_channel(channel_id)
    if log_channel:
        try:
            if embed: await log_channel.send(embed=embed)
            elif message: await log_channel.send(message[:1997] + "..." if len(message) > 2000 else message)
        except discord.Forbidden: print(f"Log Error: Perms missing for channel {channel_id} ({guild.name}).")
        except discord.HTTPException as http_err: print(f"Log Error: Discord HTTP error {channel_id} ({guild.name}): {http_err.status} {http_err.code} - {http_err.text}")
        except Exception as e: print(f"Log Error: Send fail {channel_id} ({guild.name}): {e}")
    else: print(f"Log Error: Channel {channel_id} not found in {guild.name}.")
async def log_info(guild: discord.Guild, message: str, embed: discord.Embed = None):
    if not embed: embed = discord.Embed(description=message, color=NERDY_YELLOW)
    await log_to_channel(INFO_LOG_CHANNEL_ID, guild, embed=embed)
async def log_error(guild: discord.Guild, message: str, error: Exception = None, interaction: discord.Interaction = None, embed: discord.Embed = None):
    if not embed:
        embed = discord.Embed(title="⚠️ Error / Warning", description=message, color=discord.Color.red())
        if interaction:
            context = f"Cmd: `/{interaction.command.name if interaction.command else 'N/A'}`"
            if interaction.guild: context += f" in #{interaction.channel.name}"
            context += f"\nUser: `{interaction.user}` ({interaction.user.id})"
            embed.add_field(name="Context", value=context, inline=False)
        if error:
            err_details = f"**Type:** `{type(error).__name__}`\n**Msg:** `{str(error)}`\n"
            tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__, limit=5))
            err_details += f"**Traceback:**\n```py\n{tb_str[:1000]}{'...' if len(tb_str)>1000 else ''}\n```"
            embed.add_field(name="Error Details", value=err_details, inline=False)
            print(f"--- ERROR TRACEBACK ---\nGuild: {guild.id if guild else 'N/A'}\nCtx: {message}\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}\n--- END ---")
    await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, embed=embed)

# --- Embed Pagination View ---
class HCPagesView(View):
    def __init__(self, data: list, total_members: int, timeout=300.0):
        super().__init__(timeout=timeout)
        self.data = data
        self.total_members = total_members
        self.current_page = 0
        self.total_pages = math.ceil(len(self.data) / MEMBERS_PER_PAGE) if data else 1
        self.message = None # Store message for timeout editing

        self.update_buttons()

    def create_page_embed(self) -> discord.Embed:
        start_index = self.current_page * MEMBERS_PER_PAGE
        end_index = start_index + MEMBERS_PER_PAGE
        page_data = self.data[start_index:end_index]
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, color=NERDY_YELLOW)
        desc_lines = []
        idx = start_index + 1
        for member, ingame_name in page_data:
            safe_user = discord.utils.escape_markdown(member.name) # Discord Username
            safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
            desc_lines.append(f"{idx}. {safe_user} ➔ {safe_ign}")
            idx += 1
        embed.description = "\n".join(desc_lines) if desc_lines else "No members on this page."
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} | Total HC Members: {self.total_members}")
        return embed

    def update_buttons(self):
        # Check if buttons have been added (children list exists and has items)
        if hasattr(self, 'children') and len(self.children) >= 2:
            # Assuming previous is the first button and next is the second
            prev_button = self.children[0]
            next_button = self.children[1]
            if isinstance(prev_button, Button):
                prev_button.disabled = self.current_page == 0
            if isinstance(next_button, Button):
                next_button.disabled = self.current_page >= self.total_pages - 1
        elif hasattr(self, 'previous_button') and hasattr(self, 'next_button'): # Fallback for direct access if needed
             self.previous_button.disabled = self.current_page == 0
             self.next_button.disabled = self.current_page >= self.total_pages - 1

    @button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="hc_prev_interactive")
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_page_embed()
            try: await interaction.response.edit_message(embed=embed, view=self)
            except discord.NotFound: await log_error(interaction.guild, "Paginated msg edit fail (NF)", interaction=interaction)
            except discord.HTTPException as e: await log_error(interaction.guild, f"Paginated msg edit fail (HTTP {e.status})", error=e, interaction=interaction)
        else:
            # Acknowledge the interaction even if no change happens
            try: await interaction.response.defer()
            except discord.InteractionResponded: pass # Ignore if already responded (e.g., rapid clicks)

    @button(label="Next", style=discord.ButtonStyle.blurple, custom_id="hc_next_interactive")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_page_embed()
            try: await interaction.response.edit_message(embed=embed, view=self)
            except discord.NotFound: await log_error(interaction.guild, "Paginated msg edit fail (NF)", interaction=interaction)
            except discord.HTTPException as e: await log_error(interaction.guild, f"Paginated msg edit fail (HTTP {e.status})", error=e, interaction=interaction)
        else:
            # Acknowledge the interaction even if no change happens
            try: await interaction.response.defer()
            except discord.InteractionResponded: pass # Ignore if already responded

    async def on_timeout(self):
        if self.message:
            try:
                # Disable all buttons in the view
                for item in self.children:
                    if isinstance(item, Button):
                        item.disabled = True
                await self.message.edit(view=self)
                print(f"Pagination View: Buttons disabled on timeout (message ID: {self.message.id}).")
            except (discord.NotFound, discord.HTTPException, AttributeError) as e:
                 print(f"Pagination View: Failed to disable buttons on timeout (message ID: {self.message.id if self.message else 'Unknown'}): {e}")
            except Exception as e:
                 print(f"Pagination View: Unexpected error disabling buttons on timeout - {e}")
        else:
            print("Pagination View: Timeout occurred but no message was associated with the view.")


# --- Core HC List Logic ---
async def fetch_hc_member_data(guild: discord.Guild) -> tuple[list[tuple[discord.Member, str]], int]:
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role: await log_error(guild, f"Role {ADD_ROLE_ID_HC} not found."); return [], 0
    # Fetch members directly from guild - requires Members intent
    members_unsorted = [m for m in guild.members if hc_role in m.roles and not m.bot] # Ensure members intent is enabled and exclude bots
    total_count = len(members_unsorted)
    members_sorted = sorted(members_unsorted, key=lambda m: m.name.lower()) # Sort by username
    member_tuples = []
    member_ids = [str(m.id) for m in members_sorted]
    ign_map = {}
    if supabase and member_ids:
        try:
            # Fetch IGNs in chunks if necessary (though 1000 is usually fine for Supabase 'in' filter)
            chunk_size = 500 # Adjust if needed
            for i in range(0, len(member_ids), chunk_size):
                chunk_ids = member_ids[i:i + chunk_size]
                resp = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").in_("discord_id", chunk_ids).execute())
                if resp and resp.data:
                    ign_map.update({r['discord_id']: r.get("ingame_name", "Unknown") for r in resp.data})
                await asyncio.sleep(0.1) # Small delay between chunks if needed

        except Exception as e:
             await log_error(guild, "Failed bulk IGN fetch.", error=e);
             # Populate with error state only for those we tried to fetch but failed overall
             ign_map = {mid: "DB Err" for mid in member_ids} # Or keep existing partial map if preferred
    for member in members_sorted:
        member_tuples.append((member, ign_map.get(str(member.id), "Unknown"))) # Default to Unknown if not found
    return member_tuples, total_count

def generate_hc_list_embeds(data: list[tuple[discord.Member, str]], total_members: int) -> list[discord.Embed]:
    embeds = []
    if not data: # Handle case where data list is empty even if total_members > 0 (e.g., DB error during fetch)
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, description="No members found or error retrieving details.", color=discord.Color.orange())
        embed.set_footer(text="Page 1/1 | Total HC Members: 0") # Show 0 if list is empty
        return [embed]

    total_pages = math.ceil(len(data) / MEMBERS_PER_PAGE)
    for page_num in range(total_pages):
        start_index = page_num * MEMBERS_PER_PAGE
        end_index = start_index + MEMBERS_PER_PAGE
        page_data = data[start_index:end_index]
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, color=NERDY_YELLOW)
        desc_lines = []
        idx = start_index + 1
        for member, ingame_name in page_data:
            # Ensure member object is valid before accessing attributes
            if member:
                safe_user = discord.utils.escape_markdown(member.name) # Discord Username
                safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
                desc_lines.append(f"{idx}. {safe_user} ➔ {safe_ign}")
            else:
                desc_lines.append(f"{idx}. Unknown Member ➔ {discord.utils.escape_markdown(ingame_name if ingame_name else 'Unknown')}")
            idx += 1

        embed.description = "\n".join(desc_lines) if desc_lines else "No members on this page." # Should not happen if data is not empty
        embed.set_footer(text=f"Page {page_num + 1}/{total_pages} | Total HC Members: {total_members}")
        embeds.append(embed)

    return embeds

async def update_hc_member_list(guild: discord.Guild): # Static list update
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not list_channel: await log_error(guild, f"Static list channel {HC_MEMBER_LIST_CHANNEL_ID} not found."); return

    # Check bot permissions in the target channel
    bot_member = guild.get_member(bot.user.id)
    if not bot_member: await log_error(guild, "Couldn't find bot member in guild."); return # Should not happen
    perms = list_channel.permissions_for(bot_member)
    if not perms.read_message_history or not perms.send_messages or not perms.embed_links or not perms.manage_messages:
        missing_perms = []
        if not perms.read_message_history: missing_perms.append("Read History")
        if not perms.send_messages: missing_perms.append("Send Messages")
        if not perms.embed_links: missing_perms.append("Embed Links")
        if not perms.manage_messages: missing_perms.append("Manage Messages (for deleting old)")
        await log_error(guild, f"Bot lacks permissions in static list channel #{list_channel.name}: {', '.join(missing_perms)}")
        return

    try:
        await log_info(guild, f"Starting static HC list update in #{list_channel.name}...")
        member_data, total_count = await fetch_hc_member_data(guild)
        new_embeds = generate_hc_list_embeds(member_data, total_count)
        num_new_pages = len(new_embeds)

        existing_messages = []
        try:
            # Fetch a reasonable number of recent messages to find existing list pages
            async for message in list_channel.history(limit=20): # Increased limit slightly
                if message.author == bot.user and message.embeds and message.embeds[0].title == HC_LIST_EMBED_TITLE:
                    existing_messages.append(message)
            existing_messages.sort(key=lambda m: m.created_at) # Sort oldest first (important!)
        except discord.Forbidden: await log_error(guild, f"Cannot read history in {list_channel.name}. Check Read Message History perm."); return
        except Exception as e: await log_error(guild, f"Error searching history in {list_channel.name}.", error=e); return

        num_existing = len(existing_messages)
        print(f"Static List Update: Found {num_existing} existing message(s), need {num_new_pages} page(s).")

        # --- Edit/Send Loop ---
        messages_to_keep = []
        for i in range(num_new_pages):
            embed_to_use = new_embeds[i]
            if i < num_existing:
                # Edit existing message
                msg = existing_messages[i]
                try:
                    await msg.edit(embed=embed_to_use)
                    messages_to_keep.append(msg.id)
                    print(f"  Edited message {msg.id} (Page {i+1}/{num_new_pages})")
                    await asyncio.sleep(1.1) # Discord rate limit for edits is stricter
                except discord.NotFound:
                     print(f"  Existing message {msg.id} not found, will send new one.")
                     # Need to send a new message instead
                     try:
                         new_msg = await list_channel.send(embed=embed_to_use)
                         messages_to_keep.append(new_msg.id)
                         print(f"  Sent new message {new_msg.id} (Page {i+1}/{num_new_pages})")
                         await asyncio.sleep(1.1)
                     except Exception as send_e:
                         await log_error(guild, f"Failed send static list page {i+1} after edit fail.", error=send_e)
                except Exception as e:
                    await log_error(guild, f"Failed edit static list msg {i+1} (ID: {msg.id}).", error=e)
                    messages_to_keep.append(msg.id) # Keep it even if edit failed, try delete later if needed
            else:
                # Send new message
                try:
                    new_msg = await list_channel.send(embed=embed_to_use)
                    messages_to_keep.append(new_msg.id)
                    print(f"  Sent new message {new_msg.id} (Page {i+1}/{num_new_pages})")
                    await asyncio.sleep(1.1)
                except Exception as e:
                    await log_error(guild, f"Failed send static list page {i+1}.", error=e)

        # --- Delete Surplus Old Messages ---
        # Only delete messages that were previously part of the list but are no longer needed
        messages_to_delete = [msg for msg in existing_messages if msg.id not in messages_to_keep]

        if messages_to_delete:
             print(f"  Deleting {len(messages_to_delete)} surplus message(s)...")
             deleted_count = 0
             for msg_to_delete in messages_to_delete:
                 try:
                     await msg_to_delete.delete()
                     deleted_count += 1
                     print(f"    Deleted surplus message {msg_to_delete.id}")
                     await asyncio.sleep(1.1) # Rate limiting for deletes
                 except discord.Forbidden:
                     await log_error(guild, f"Failed delete surplus msg (ID: {msg_to_delete.id}) - Missing Manage Messages perm?")
                     break # Stop trying if permissions are wrong
                 except discord.NotFound:
                     print(f"    Tried to delete surplus message {msg_to_delete.id}, but it was already gone.")
                 except Exception as e:
                     await log_error(guild, f"Failed delete surplus msg (ID: {msg_to_delete.id}).", error=e)
             await log_info(guild, f"Deleted {deleted_count}/{len(messages_to_delete)} surplus static list message(s).")

        await log_info(guild, f"Static HC list update complete in #{list_channel.name} ({num_new_pages} pages).")

    except Exception as e:
        await log_error(guild, f"Overall static list update error in #{list_channel.name}.", error=e)
        print(f"CRITICAL ERROR during update_hc_member_list: {e}\n{traceback.format_exc()}")


# --- Discord Events ---
# --- CORRECTED on_ready ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    synced_count = 0
    try:
        # Sync commands first
        print("Attempting to sync application commands...")
        synced = await tree.sync()
        synced_count = len(synced)
        print(f"Synced {synced_count} application commands.")

        # Perform actions for each guild the bot is in
        if not bot.guilds:
            print("Bot is not currently in any guilds.")
            return # Exit if no guilds

        print(f"Running initial setup for {len(bot.guilds)} guild(s)...")
        # Use a copy of the list in case the bot leaves/joins guilds during setup
        guilds_to_process = list(bot.guilds)
        for guild in guilds_to_process:
            print(f"  Processing guild: {guild.name} ({guild.id})")
            try:
                # Log bot readiness in the guild's info channel
                await log_info(guild, f"Bot Ready. Synced {synced_count} commands.")

                # Update the static HC member list for the guild
                print(f"    Updating HC member list for {guild.name}...")
                await update_hc_member_list(guild)
                print(f"    HC member list update initiated for {guild.name}.")

                # Short delay between guilds if necessary, can be adjusted or removed
                await asyncio.sleep(1) # Helps avoid potential rate limits if many guilds start at once

            except Exception as guild_e:
                log_msg = f"Error during on_ready setup for guild {guild.name} ({guild.id})."
                print(f"ERROR: {log_msg} - {guild_e}")
                # Try logging the guild-specific error to the error channel
                try:
                    await log_error(guild, log_msg, error=guild_e)
                except Exception as log_err_e:
                    print(f"CRITICAL: Failed to log guild setup error for {guild.name}: {log_err_e}")

        print("Initial guild setup complete.")

    except discord.HTTPException as http_err:
        # Specifically handle HTTP errors during sync (like rate limits or other API issues)
        print(f"Sync fail (HTTPException): {http_err.status} {http_err.code} - {http_err.text}")
        # Try logging the sync error (use first available guild if any)
        primary_guild = bot.guilds[0] if bot.guilds else None
        if primary_guild:
            try:
                await log_error(primary_guild, "Command Sync failed (HTTPException).", error=http_err)
            except Exception as log_e:
                 print(f"CRITICAL: Failed to log sync HTTP error: {log_e}")
        else:
            print("CRITICAL: Command Sync failed (HTTPException) and no guilds available to log to.")

    except Exception as e:
        # Catch any other exceptions during sync or the overall process
        print(f"Sync fail or general on_ready error (Exception): {e}")
        print(traceback.format_exc()) # Print full traceback for general errors
        # Try logging the sync error (use first available guild if any)
        primary_guild = bot.guilds[0] if bot.guilds else None
        if primary_guild:
            try:
                await log_error(primary_guild, "Command Sync failed or general on_ready error.", error=e)
            except Exception as log_e:
                 print(f"CRITICAL: Failed to log sync/general error: {log_e}")
        else:
            print(f"CRITICAL: Command Sync failed/general error and no guilds available to log to.")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    guild = after.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        # Log role missing error once if needed, but avoid spamming logs
        # print(f"Warning: HC Role {ADD_ROLE_ID_HC} not found in guild {guild.name} for on_member_update.")
        return

    # Check if the HC role status changed
    before_has_hc = hc_role in before.roles
    after_has_hc = hc_role in after.roles

    if before_has_hc != after_has_hc:
        action = "added to" if after_has_hc else "removed from"
        log_embed = discord.Embed(
            description=f"HC role `{hc_role.name}` {action} user `{after.name}` ({after.id}). Updating static list.",
            color=discord.Color.purple()
        )
        await log_info(guild, "", embed=log_embed)
        # Trigger the static list update
        await update_hc_member_list(guild)

# --- Error Handling for App Commands ---
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    guild = interaction.guild # Can be None in DMs, but context suggests server-only bot
    user_message = "❌ An unexpected error occurred." # Default user message
    log_description = "Unhandled application command error."
    log_error_obj = error # The original error to log

    # Simplify error checking and response logic
    if isinstance(error, app_commands.CommandNotFound):
        print(f"Command not found triggered for: {interaction.command.name if interaction.command else 'N/A'}")
        # Usually, Discord handles this, no need to respond unless debugging.
        return
    elif isinstance(error, app_commands.MissingPermissions):
        missing_perms_str = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
        user_message = f"❌ You lack the required permissions: {missing_perms_str}"
        log_description = f"User `{interaction.user}` ({interaction.user.id}) lacked permissions ({missing_perms_str}) for `/{interaction.command.name if interaction.command else 'N/A'}`."
        log_error_obj = None # Don't log the exception itself, the description is enough
    elif isinstance(error, app_commands.CheckFailure):
        # This catches failed `has_permissions` or other custom checks.
        # Could be permissions, could be role checks, could be custom logic.
        user_message = "❌ You do not meet the requirements to use this command."
        # Extract check failure type if possible (less common without custom checks)
        check_fail_type = type(error).__name__
        log_description = f"User `{interaction.user}` ({interaction.user.id}) failed command checks ({check_fail_type}) for `/{interaction.command.name if interaction.command else 'N/A'}`."
        log_error_obj = None
    elif isinstance(error, app_commands.CommandInvokeError):
        # This means the command code itself raised an exception
        original_error = error.original
        user_message = f"❌ An error occurred while running the command: `{type(original_error).__name__}`"
        log_description = f"Error occurred during invocation of `/{interaction.command.name if interaction.command else 'N/A'}`."
        log_error_obj = original_error # Log the underlying error
        print(f"CommandInvokeError for /{interaction.command.name if interaction.command else 'N/A'} by {interaction.user}: {original_error}")
    elif isinstance(error, app_commands.TransformerError):
         user_message = f"❌ Invalid input provided: {error}"
         log_description = f"TransformerError for `/{interaction.command.name if interaction.command else 'N/A'}` by {interaction.user}."
         log_error_obj = error
    elif isinstance(error, app_commands.CommandOnCooldown):
        user_message = f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f} seconds."
        log_description = f"User `{interaction.user}` hit cooldown for `/{interaction.command.name if interaction.command else 'N/A'}`."
        log_error_obj = None # Cooldowns aren't usually logged as errors unless debugging them
    else:
        # Catch-all for other potential app command errors
        user_message = "❌ An unknown error occurred while processing the command."
        log_description = f"An unknown AppCommandError occurred: `{type(error).__name__}`"
        log_error_obj = error
        print(f"Unknown AppCommandError: {type(error).__name__} - {error}")

    # Log the error details to the error channel
    if guild: # Only log if we have guild context
        await log_error(guild, log_description, error=log_error_obj, interaction=interaction)
    else:
        print(f"App Command Error occurred outside of a guild context: {log_description} - Error: {log_error_obj}")

    # Try to send an ephemeral response to the user
    try:
        if interaction.response.is_done():
            await interaction.followup.send(user_message, ephemeral=True)
        else:
            await interaction.response.send_message(user_message, ephemeral=True)
    except discord.InteractionResponded:
        # If we already responded somehow (e.g., defer followed by immediate error), try followup
        try: await interaction.followup.send(user_message, ephemeral=True)
        except Exception as followup_e: print(f"Failed to send error followup message: {followup_e}")
    except discord.NotFound:
        print("Interaction not found when trying to send error message.") # Interaction might have expired
    except discord.HTTPException as http_e:
        print(f"Failed to send error message due to Discord HTTP error: {http_e.status} {http_e.code}")
    except Exception as send_e:
        print(f"An unexpected error occurred while trying to send the error message to the user: {send_e}")


# --- Modals ---
# Helper function for modals/embeds if not already defined elsewhere
def create_embed(description: str, color: discord.Color = NERDY_YELLOW, title: str = None) -> discord.Embed:
     embed = discord.Embed(title=title, description=description, color=color)
     return embed

class BulkUpdateModal(Modal, title="Bulk Update IGNs"):
    data = TextInput(
        label="Paste list (DiscordName ➔ InGameName)",
        style=discord.TextStyle.paragraph,
        placeholder="ExampleUser#1234 ➔ CoolFlorrName\nAnother User ➔ AnotherIGN\n...",
        required=True,
        max_length=4000 # Max modal text input length
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.guild

        if not supabase:
            await interaction.followup.send(embed=create_embed("❌ Supabase client is not available.", discord.Color.red()), ephemeral=True)
            await log_error(guild, "Bulk Update Modal: Supabase client missing.", interaction=interaction)
            return

        success_count, fail_count, not_found_count = 0, 0, 0
        results_log = [] # Store tuples: ('type', 'message') e.g., ('f', 'L1: Format Error')
        lines = self.data.value.strip().splitlines()

        if not lines:
            await interaction.followup.send(embed=create_embed("⚠️ No data provided in the modal.", discord.Color.orange()), ephemeral=True)
            return

        # Fetch guild members once for efficient lookup (requires Members intent)
        try:
            await guild.chunk() # Ensure member cache is populated if large server
            members_map = {m.name.lower(): m for m in guild.members if not m.bot} # Lowercase name for case-insensitive matching
            members_map_display = {m.display_name.lower(): m for m in guild.members if not m.bot} # Also check display names
        except Exception as e:
             await log_error(guild, "Bulk Update Modal: Failed to fetch/map guild members.", error=e, interaction=interaction)
             await interaction.followup.send(embed=create_embed("❌ Error fetching server members. Cannot proceed.", discord.Color.red()), ephemeral=True)
             return

        upsert_payload = []

        for idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line: continue # Skip empty lines

            if "➔" not in line:
                fail_count += 1
                results_log.append(('f', f"L{idx}: Invalid format (Missing '➔'). Line: `{line[:50]}`"))
                continue

            try:
                discord_name_raw, ingame_name = map(str.strip, line.split("➔", 1))
                if not discord_name_raw or not ingame_name:
                    fail_count += 1
                    results_log.append(('f', f"L{idx}: Missing Discord name or IGN. Line: `{line[:50]}`"))
                    continue
            except ValueError:
                fail_count += 1
                results_log.append(('f', f"L{idx}: Error splitting line by '➔'. Line: `{line[:50]}`"))
                continue

            # Attempt to find the member
            member = members_map.get(discord_name_raw.lower())
            if not member:
                member = members_map_display.get(discord_name_raw.lower()) # Fallback to display name

            if not member:
                 # Try finding by ID if the input might be an ID
                try:
                    maybe_id = int(discord_name_raw)
                    member = guild.get_member(maybe_id)
                except ValueError:
                     pass # Not an ID

            if not member:
                # Final attempt: Fuzzy matching (optional, can be slow)
                # match = discord.utils.find(lambda m: discord_name_raw.lower() in m.name.lower() or discord_name_raw.lower() in m.display_name.lower(), guild.members)
                # if match: member = match # Use with caution

                fail_count += 1
                not_found_count += 1
                results_log.append(('f', f"L{idx}: User `{discord.utils.escape_markdown(discord_name_raw)}` not found."))
                continue

            # If member found, prepare data for upsert
            upsert_payload.append({
                "discord_id": str(member.id),
                "discord_name": member.name, # Store canonical name
                "ingame_name": ingame_name
            })
            # Note: We will perform the actual DB operation in bulk later for efficiency

        # Perform bulk upsert if payload is not empty
        db_errors = 0
        if upsert_payload:
            try:
                print(f"Bulk Update: Attempting to upsert {len(upsert_payload)} records.")
                await run_supabase_sync(
                    lambda: supabase.table("hc_members")
                    .upsert(upsert_payload, on_conflict="discord_id")
                    .execute()
                )
                success_count = len(upsert_payload) # Assume all succeed if no exception
                print(f"Bulk Update: Upsert successful for {success_count} records.")
            except APIError as api_err:
                db_errors = len(upsert_payload) # Assume all failed on API error
                fail_count += db_errors
                results_log.append(('f', f"DB: Supabase API Error during bulk upsert: {api_err.message}"))
                await log_error(guild, f"Bulk DB APIError", error=api_err, interaction=interaction)
            except Exception as e:
                db_errors = len(upsert_payload) # Assume all failed on general error
                fail_count += db_errors
                results_log.append(('f', f"DB: Unexpected error during bulk upsert: {type(e).__name__}"))
                await log_error(guild, f"Bulk DB unexpected error", error=e, interaction=interaction)

        # Prepare results embed
        embed = discord.Embed(title="Bulk Update Results", color=NERDY_YELLOW)
        summary = f"✅ Processed: {len(lines)}\n" \
                  f"💾 Successfully Saved/Updated: {success_count}\n" \
                  f"❌ Failures: {fail_count}\n" \
                  f"  - User Not Found: {not_found_count}\n" \
                  f"  - Format/DB Errors: {fail_count - not_found_count}"
        embed.description = summary

        # Add detailed issues if any occurred
        error_details = "\n".join([r[1] for r in results_log if r[0] == 'f'])
        if error_details:
            # Truncate if too long for embed field value
            field_value = (error_details[:1021] + "...") if len(error_details) > 1024 else error_details
            embed.add_field(name="Issues Encountered", value=field_value, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

        # Log the action
        log_embed = discord.Embed(
            description=f"Bulk IGN update executed by `{interaction.user}`. Success: {success_count}, Fail: {fail_count}.",
            color=NERDY_YELLOW
        )
        await log_info(guild, "", embed=log_embed)

        # Update the static list if any successful upserts occurred
        if success_count > 0:
            await update_hc_member_list(guild)


# --- Slash Commands ---
# Condensed command definitions remain the same
@tree.command(name="verify", description="Verify a user.") @app_commands.describe(user="User") @app_commands.checks.has_permissions(manage_roles=True)
async def verify(i: discord.Interaction, user: discord.Member): g=i.guild; rr,ar=g.get_role(REMOVE_ROLE_ID),g.get_role(ADD_ROLE_ID_VERIFY); act,log=[],[]; missing_roles=[]; if not rr:log.append(f"Role {REMOVE_ROLE_ID} NF"); missing_roles.append(f"Remove Role ({REMOVE_ROLE_ID})"); if not ar:log.append(f"Role {ADD_ROLE_ID_VERIFY} NF"); missing_roles.append(f"Add Role ({ADD_ROLE_ID_VERIFY})"); if missing_roles: await log_error(g,f"/verify setup error: Missing roles {'; '.join(missing_roles)}", interaction=i); await i.response.send_message(embed=create_embed(f"❌ Bot setup error: Cannot find required role(s): {', '.join(missing_roles)}.", discord.Color.red()), ephemeral=True); return; try: modified=False; if rr and rr in user.roles: await user.remove_roles(rr, reason=f"Verified by {i.user}"); act.append(f"➖ Removed `{rr.name}`"); modified=True; if ar and ar not in user.roles: await user.add_roles(ar, reason=f"Verified by {i.user}"); act.append(f"➕ Added `{ar.name}`"); modified=True; if not modified: embed=create_embed(f"ℹ️ No role changes needed for {user.display_name}. They likely already have the correct roles.", discord.Color.orange()); await i.response.send_message(embed=embed,ephemeral=True); else: log_msg=f"Verified `{user.display_name}` ({user.id}). Actions: {' '.join(act)}."; await log_info(g,f"`{i.user}` used /verify: {log_msg}"); embed=create_embed(f"✅ Verified **{user.display_name}**!\n"+"\n".join(act), discord.Color.green()); await i.response.send_message(embed=embed); except discord.Forbidden: await log_error(g,f"/verify Forbidden: Cannot manage roles for {user.display_name} ({user.id}). Check hierarchy/perms.", interaction=i); await i.response.send_message(embed=create_embed("❌ I don't have permission to manage this user's roles. My role might be too low.", discord.Color.red()),ephemeral=True); except Exception as e: await log_error(g,f"/verify error processing {user.display_name} ({user.id})", error=e, interaction=i); await i.response.send_message(embed=create_embed("❌ An unexpected error occurred during verification.", discord.Color.red()),ephemeral=True)
@tree.command(name="unverify", description="Unverify a user.") @app_commands.describe(user="User") @app_commands.checks.has_permissions(manage_roles=True)
async def unverify(i: discord.Interaction, user: discord.Member): g=i.guild; rr,ar=g.get_role(ADD_ROLE_ID_VERIFY),g.get_role(REMOVE_ROLE_ID); act,log=[],[]; missing_roles=[]; if not rr:log.append(f"Role {ADD_ROLE_ID_VERIFY} NF"); missing_roles.append(f"Verify Role ({ADD_ROLE_ID_VERIFY})"); if not ar:log.append(f"Role {REMOVE_ROLE_ID} NF"); missing_roles.append(f"Unverified Role ({REMOVE_ROLE_ID})"); if missing_roles: await log_error(g,f"/unverify setup error: Missing roles {';'.join(missing_roles)}", interaction=i); await i.response.send_message(embed=create_embed(f"❌ Bot setup error: Cannot find required role(s): {', '.join(missing_roles)}.", discord.Color.red()), ephemeral=True); return; try: modified=False; if rr and rr in user.roles: await user.remove_roles(rr, reason=f"Unverified by {i.user}"); act.append(f"➖ Removed `{rr.name}`"); modified=True; if ar and ar not in user.roles: await user.add_roles(ar, reason=f"Unverified by {i.user}"); act.append(f"➕ Added `{ar.name}`"); modified=True; if not modified: embed=create_embed(f"ℹ️ No role changes needed for {user.display_name}. They likely already have the unverified roles.", discord.Color.orange()); await i.response.send_message(embed=embed,ephemeral=True); else: log_msg=f"Unverified `{user.display_name}` ({user.id}). Actions: {' '.join(act)}."; await log_info(g,f"`{i.user}` used /unverify: {log_msg}"); embed=create_embed(f"✅ Unverified **{user.display_name}**!\n"+"\n".join(act), discord.Color.green()); await i.response.send_message(embed=embed); except discord.Forbidden: await log_error(g,f"/unverify Forbidden: Cannot manage roles for {user.display_name} ({user.id}). Check hierarchy/perms.", interaction=i); await i.response.send_message(embed=create_embed("❌ I don't have permission to manage this user's roles. My role might be too low.", discord.Color.red()),ephemeral=True); except Exception as e: await log_error(g,f"/unverify error processing {user.display_name} ({user.id})", error=e, interaction=i); await i.response.send_message(embed=create_embed("❌ An unexpected error occurred during un-verification.", discord.Color.red()),ephemeral=True)
@tree.command(name="hcverify", description="HC Verify user, store IGN, set nickname.") @app_commands.describe(user="User", ingame_name="Florr IGN") @app_commands.checks.has_permissions(manage_roles=True)
async def hcverify(i: discord.Interaction, user: discord.Member, ingame_name: str): await i.response.defer(thinking=True, ephemeral=False); g=i.guild; if not supabase: await i.followup.send(embed=create_embed("❌ Supabase client is not available.", discord.Color.red()),ephemeral=True); await log_error(g, "HCVerify: Supabase client missing.", interaction=i); return; rr,arv,arh=g.get_role(REMOVE_ROLE_ID),g.get_role(ADD_ROLE_ID_VERIFY),g.get_role(ADD_ROLE_ID_HC); roles_to_add=[]; log_actions,response_lines=[],[]; missing_roles=[]; if not rr: missing_roles.append(f"Remove Role ({REMOVE_ROLE_ID})"); if not arv: missing_roles.append(f"Verify Role ({ADD_ROLE_ID_VERIFY})"); if not arh: missing_roles.append(f"HC Role ({ADD_ROLE_ID_HC})"); if missing_roles: await log_error(g,f"/hcverify setup error: Missing roles {'; '.join(missing_roles)}", interaction=i); await i.followup.send(embed=create_embed(f"❌ Bot setup error: Cannot find required role(s): {', '.join(missing_roles)}.", discord.Color.red()), ephemeral=True); return; try: # Role Management original_had_hc_role = arh and arh in user.roles; roles_modified = False; if rr and rr in user.roles: await user.remove_roles(rr, reason=f"HC Verified by {i.user}"); log_actions.append(f"Removed Unverified Role (`{rr.name}`)"); roles_modified = True; if arv and arv not in user.roles: roles_to_add.append(arv); if arh and arh not in user.roles: roles_to_add.append(arh); if roles_to_add: await user.add_roles(*roles_to_add, reason=f"HC Verified by {i.user}"); added_names=', '.join([f"`{r.name}`" for r in roles_to_add]); log_actions.append(f"Added Roles: {added_names}"); response_lines.append(f"➕ Roles Added: {added_names}"); roles_modified = True; if not roles_modified and not roles_to_add: response_lines.append("ℹ️ Roles already correct."); # Database Update db_ok=False; try: await run_supabase_sync(lambda: supabase.table("hc_members").upsert({"discord_id":str(user.id),"discord_name":user.name,"ingame_name":ingame_name},on_conflict="discord_id").execute()); log_actions.append(f"Upserted IGN: {ingame_name}"); response_lines.append(f"💾 IGN Saved: `{discord.utils.escape_markdown(ingame_name)}`"); db_ok=True; except Exception as e: await log_error(g,f"DB upsert failed for {user.display_name} ({user.id}) during HCVerify", error=e, interaction=i); log_actions.append("DB Upsert FAILED"); response_lines.append("⚠️ Database save failed!"); # Nickname Management nick_change_status="No change"; nickname_truncated=False; target_nick=ingame_name[:32]; if len(ingame_name) > 32: nickname_truncated = True; if user.nick != target_nick: try: await user.edit(nick=target_nick, reason=f"HC Verified by {i.user}"); log_actions.append(f"Set Nickname: '{target_nick}'" + (" (truncated)" if nickname_truncated else "")); response_lines.append(f"🏷️ Nickname Set: `{discord.utils.escape_markdown(target_nick)}`" + (" (truncated)" if nickname_truncated else "")); nick_change_status="Success"; except discord.Forbidden: log_actions.append("Nickname update FAILED (Forbidden)"); response_lines.append("⚠️ Nickname update failed (Permissions)"); nick_change_status="Perms Fail"; except Exception as e: await log_error(g,f"Nickname update failed for {user.display_name} ({user.id}) during HCVerify", error=e, interaction=i); log_actions.append(f"Nickname update FAILED ({type(e).__name__})"); response_lines.append("⚠️ Nickname update failed (Error)"); nick_change_status="Error"; else: log_actions.append("Nickname already correct"); response_lines.append("🏷️ Nickname already correct."); # Final Logging and Response log_message=f"`{i.user}` HC verified `{user.display_name}` ({user.id}). Actions: {'; '.join(log_actions)}."; await log_info(g,log_message); title_suffix = " (IGN truncated in nickname)" if nickname_truncated and nick_change_status=="Success" else "" title_suffix += " (DB/Nick issues)" if not db_ok or nick_change_status not in ["Success", "No change"] else "" embed=create_embed(title=f"✅ HC Verified: {user.display_name}{title_suffix}",description="\n".join(response_lines) if response_lines else "No actions performed.",color=discord.Color.green() if db_ok and nick_change_status in ["Success", "No change"] else discord.Color.orange()); await i.followup.send(embed=embed,ephemeral=False); # Update static list if HC role was added or if user already had HC role and IGN was updated successfully newly_added_hc = arh and arh in roles_to_add if newly_added_hc or (original_had_hc_role and db_ok): await update_hc_member_list(g); except discord.Forbidden as fe: await log_error(g,f"/hcverify Forbidden: Cannot manage roles/nick for {user.display_name} ({user.id}). Check hierarchy/perms.", error=fe, interaction=i); await i.followup.send(embed=create_embed("❌ I don't have permission to manage this user's roles or nickname. My role might be too low.",discord.Color.red()),ephemeral=True); except Exception as e: await log_error(g,f"/hcverify Unexpected error processing {user.display_name} ({user.id})", error=e, interaction=i); await i.followup.send(embed=create_embed("❌ An unexpected error occurred during HC verification.",discord.Color.red()),ephemeral=True)
@tree.command(name="unhcverify", description="Remove HC role and reset nickname.") @app_commands.describe(user="User") @app_commands.checks.has_permissions(manage_roles=True)
async def unhcverify(i: discord.Interaction, user: discord.Member): await i.response.defer(thinking=True, ephemeral=False); g=i.guild; arh=g.get_role(ADD_ROLE_ID_HC); log_actions,response_lines=[],[]; if not arh: await log_error(g,f"/unhcverify setup error: Missing HC Role {ADD_ROLE_ID_HC}", interaction=i); await i.followup.send(embed=create_embed(f"❌ Bot setup error: Cannot find the HC role ({ADD_ROLE_ID_HC}).", discord.Color.red()),ephemeral=True); return; try: # Role Removal role_removed = False; if arh in user.roles: await user.remove_roles(arh, reason=f"Un-HC-Verified by {i.user}"); log_actions.append(f"Removed HC Role (`{arh.name}`)"); response_lines.append(f"➖ Role Removed: `{arh.name}`"); role_removed = True; else: await i.followup.send(embed=create_embed(f"ℹ️ {user.display_name} does not have the `{arh.name}` role.",discord.Color.orange()),ephemeral=True); return; # Don't proceed if they didn't have the role # Nickname Reset nick_reset_status = "No change"; if user.nick is not None: try: await user.edit(nick=None, reason=f"Un-HC-Verified by {i.user}"); log_actions.append("Reset Nickname"); response_lines.append("🏷️ Nickname Reset"); nick_reset_status="Success"; except discord.Forbidden: log_actions.append("Nickname reset FAILED (Forbidden)"); response_lines.append("⚠️ Nickname reset failed (Permissions)"); nick_reset_status="Perms Fail"; except Exception as e: await log_error(g,f"Nickname reset failed for {user.display_name} ({user.id}) during UnHCVerify", error=e, interaction=i); log_actions.append(f"Nickname reset FAILED ({type(e).__name__})"); response_lines.append("⚠️ Nickname reset failed (Error)"); nick_reset_status="Error"; else: log_actions.append("No nickname to reset"); response_lines.append("🏷️ User had no nickname."); # Final Logging and Response log_message=f"`{i.user}` Un-HC-verified `{user.display_name}` ({user.id}). Actions: {'; '.join(log_actions)}."; await log_info(g,log_message); title_suffix = " (nickname reset failed)" if nick_reset_status not in ["Success", "No change"] else "" embed=create_embed(title=f"✅ Un-HC-Verified: {user.display_name}{title_suffix}",description="\n".join(response_lines),color=discord.Color.green() if nick_reset_status in ["Success", "No change"] else discord.Color.orange()); await i.followup.send(embed=embed); # Update static list if role was successfully removed if role_removed: await update_hc_member_list(g); except discord.Forbidden as fe: await log_error(g,f"/unhcverify Forbidden: Cannot manage roles/nick for {user.display_name} ({user.id}). Check hierarchy/perms.", error=fe, interaction=i); await i.followup.send(embed=create_embed("❌ I don't have permission to manage this user's roles or nickname. My role might be too low.",discord.Color.red()),ephemeral=True); except Exception as e: await log_error(g,f"/unhcverify Unexpected error processing {user.display_name} ({user.id})", error=e, interaction=i); await i.followup.send(embed=create_embed("❌ An unexpected error occurred during Un-HC-verification.",discord.Color.red()),ephemeral=True)

# /hcmembers updated
@tree.command(name="hcmembers", description="Show an interactive list of [HC1] members.")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    # Ensure command is used in a guild context
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    # Check channel restriction first
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        allowed_mentions = [f"<#{cid}>" for cid in ALLOWED_CHANNEL_IDS if guild.get_channel(cid)]
        allowed_list = ", ".join(allowed_mentions) if allowed_mentions else "configured channels"
        embed = create_embed(f"❌ Please use this command in one of the allowed channels: {allowed_list}", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=False) # Acknowledge publicly

    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Database connection is unavailable. Cannot fetch members.", discord.Color.red()))
        await log_error(guild, "/hcmembers: Supabase client missing.", interaction=interaction)
        return

    try:
        member_data, total_count = await fetch_hc_member_data(guild)

        if not member_data:
            # Handle case where role exists but no members have it, or DB error occurred during fetch
            embed = create_embed(f"{HC_LIST_EMBED_TITLE}\nNo HC members found or error fetching details.", discord.Color.orange())
            await interaction.followup.send(embed=embed)
        else:
            # Create and send the paginated view
            view = HCPagesView(member_data, total_count)
            initial_embed = view.create_page_embed()
            # Send the initial message and store it in the view for timeout handling
            message = await interaction.followup.send(embed=initial_embed, view=view)
            view.message = message # IMPORTANT: Link message to view
            await log_info(guild, f"/hcmembers interactive list generated by `{interaction.user}` in #{interaction.channel.name}.")

    except Exception as e:
        await log_error(guild, "/hcmembers: Error generating interactive list.", error=e, interaction=interaction)
        # Ensure followup is used if defer was successful
        try:
            await interaction.followup.send(embed=create_embed("❌ An unexpected error occurred while fetching the member list.", discord.Color.red()))
        except discord.HTTPException as http_e: # Handle cases where the followup fails
             print(f"Failed to send error followup for /hcmembers: {http_e}")


# /refresh updates static list
@tree.command(name="refresh", description="Refresh the static [HC1] member list.")
@app_commands.checks.has_permissions(manage_roles=True) # Assuming refresh needs manage roles, adjust if needed
async def refresh(interaction: discord.Interaction):
    # Defer ephemerally first, makes sense for a refresh command
    await interaction.response.defer(thinking=True, ephemeral=True)
    guild = interaction.guild

    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Database connection is unavailable. Cannot refresh.", discord.Color.red()), ephemeral=True)
        await log_error(guild, "/refresh: Supabase client missing.", interaction=interaction)
        return

    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not list_channel:
        await interaction.followup.send(embed=create_embed(f"❌ Static list channel (ID: {HC_MEMBER_LIST_CHANNEL_ID}) not found.", discord.Color.red()), ephemeral=True)
        await log_error(guild, f"/refresh: Static list channel {HC_MEMBER_LIST_CHANNEL_ID} not found.", interaction=interaction)
        return

    try:
        await log_info(guild, f"Manual refresh of static list triggered by `{interaction.user}`.")
        await update_hc_member_list(guild) # Call the main update function
        embed = create_embed(f"✅ Successfully triggered refresh for the static HC list in {list_channel.mention}!", discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)
        # log_info is already called inside update_hc_member_list upon completion/start

    except Exception as e:
        await log_error(guild, "Error during manual /refresh execution.", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ An unexpected error occurred during the refresh.", discord.Color.red()), ephemeral=True)

# Condensed command definitions remain the same
@tree.command(name="bulkupdate", description="Bulk update IGNs via modal.") @app_commands.checks.has_permissions(manage_roles=True)
async def bulkupdate(i: discord.Interaction): try: await i.response.send_modal(BulkUpdateModal()); await log_info(i.guild, f"`{i.user}` opened the bulk IGN update modal."); except Exception as e: await log_error(i.guild, "Error opening bulk update modal.", error=e, interaction=i); if not i.response.is_done(): await i.response.send_message(embed=create_embed("❌ Failed to open the bulk update form.",discord.Color.red()),ephemeral=True)
@tree.command(name="syncnicknames", description="Sync all HC nicks with stored IGNs.") @app_commands.checks.has_permissions(manage_roles=True)
async def syncnicknames(i: discord.Interaction): await i.response.defer(thinking=True,ephemeral=True); g=i.guild; if not supabase: await i.followup.send(embed=create_embed("❌ Database connection is unavailable.", discord.Color.red()),ephemeral=True); await log_error(g, "SyncNicknames: Supabase client missing.", interaction=i); return; arh=g.get_role(ADD_ROLE_ID_HC); if not arh: await i.followup.send(embed=create_embed(f"❌ HC Role (ID: {ADD_ROLE_ID_HC}) not found.", discord.Color.red()),ephemeral=True); await log_error(g, f"SyncNicknames: HC Role {ADD_ROLE_ID_HC} not found.", interaction=i); return; start_time = discord.utils.utcnow(); await log_info(g,f"Nickname sync started by `{i.user}`."); await i.edit_original_response(content="🔄 Fetching HC members and IGN data..."); ign_data={}; try: # Fetch all IGNs from Supabase resp=await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").execute()); if resp and resp.data: ign_data={item['discord_id']: item['ingame_name'] for item in resp.data if item.get('ingame_name') and item.get('discord_id')}; print(f"SyncNick: Fetched {len(ign_data)} IGN records from DB.") except Exception as e: await log_error(g,"SyncNicknames: Database fetch failed.", error=e, interaction=i); await i.edit_original_response(content="❌ Failed to fetch IGN data from the database."); return; counts={'processed':0, 'updated':0, 'skipped_match':0, 'skipped_no_ign':0, 'fail_perms':0, 'fail_other':0}; # Get all members with the HC role hc_members=[m for m in g.members if arh in m.roles and not m.bot]; total_hc_members=len(hc_members); if total_hc_members == 0: await i.edit_original_response(content="ℹ️ No members found with the HC role."); return; await i.edit_original_response(content=f"🔄 Syncing nicknames for {total_hc_members} HC members..."); last_update_time = asyncio.get_event_loop().time(); for idx, member in enumerate(hc_members): counts['processed']+=1; member_id_str=str(member.id); # Check if IGN exists for this member if member_id_str not in ign_data: counts['skipped_no_ign']+=1; continue; stored_ign=ign_data[member_id_str]; target_nick=stored_ign[:32]; # Check if update is needed if member.nick == target_nick: counts['skipped_match']+=1; continue; # Attempt nickname update try: await member.edit(nick=target_nick, reason=f"Nickname Sync by {i.user}"); counts['updated']+=1; await asyncio.sleep(0.1) # Small delay to potentially avoid rate limits on edits except discord.Forbidden: counts['fail_perms']+=1; await log_error(g, f"SyncNick Perms Fail: Cannot edit nick for {member.name} ({member.id}). Bot role too low?", interaction=i, embed=None) # Avoid embed spam except discord.HTTPException as http_e: counts['fail_other']+=1; await log_error(g, f"SyncNick HTTP Fail: Nick edit for {member.name} ({member.id}). Status: {http_e.status}", error=http_e, interaction=i, embed=None) except Exception as e: counts['fail_other']+=1; await log_error(g, f"SyncNick Other Fail: Nick edit for {member.name} ({member.id})", error=e, interaction=i, embed=None) # Update progress periodically current_time = asyncio.get_event_loop().time() if current_time - last_update_time > 5.0: # Update every 5 seconds try: await i.edit_original_response(content=f"🔄 Syncing... ({counts['processed']}/{total_hc_members})"); last_update_time = current_time; except discord.NotFound: print("SyncNick: Interaction expired during progress update."); break # Stop if interaction is gone except discord.HTTPException as http_prog_e: print(f"SyncNick: Failed to update progress ({http_prog_e.status})"); await asyncio.sleep(2) # Wait longer if progress update fails # Final summary end_time = discord.utils.utcnow(); duration = (end_time - start_time).total_seconds(); embed=discord.Embed(title="Nickname Sync Complete!",color=NERDY_YELLOW, timestamp=end_time); summary = ( f"Processed: {counts['processed']}/{total_hc_members}\n" f"✅ Updated: {counts['updated']}\n" f"ℹ️ Skipped (Match): {counts['skipped_match']}\n" f"⚠️ Skipped (No IGN): {counts['skipped_no_ign']}\n" f"❌ Failed (Perms): {counts['fail_perms']}\n" f"❌ Failed (Other): {counts['fail_other']}\n\n" f"Duration: {duration:.2f} seconds" ) embed.description=summary; try: await i.edit_original_response(content=None, embed=embed); except discord.NotFound: print("SyncNick: Interaction expired before sending final summary."); except discord.HTTPException as http_final_e: print(f"SyncNick: Failed to send final summary embed ({http_final_e.status})"); log_embed=discord.Embed(title="Nickname Sync Finished", description=summary, color=NERDY_YELLOW).set_footer(text=f"Triggered by {i.user}"); await log_info(g,"",embed=log_embed)

# /wither command (restored version)
@tree.command(name="wither", description="Temporarily remove all roles from a user.")
@app_commands.describe(user="The user to wither", time="Time (in minutes, defaults to 2, max 10)")
async def wither(interaction: discord.Interaction, user: discord.Member, time: float = 2.0):
    guild = interaction.guild
    interaction_user = interaction.user # The user invoking the command
    bot_member = guild.me # The bot's member object

    # --- Pre-checks ---
    async def fail_and_log(reason: str, public_msg: str, log_error_obj: Exception = None):
        # Logs the internal reason and sends an ephemeral message to the command user.
        await log_error(guild, f"Wither Failure: {reason}", error=log_error_obj, interaction=interaction)
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=create_embed(public_msg, discord.Color.red()), ephemeral=True)
        else:
            await interaction.followup.send(embed=create_embed(public_msg, discord.Color.red()), ephemeral=True)

    # 1. Permission Check
    if interaction_user.id not in ALLOWED_WITHER_IDS:
        await fail_and_log(f"User `{interaction_user}` ({interaction_user.id}) lacks wither permission.", "❌ You lack the divine permission to cast Wither.")
        return

    # 2. Target Checks
    if user.id == interaction_user.id:
        await fail_and_log("User attempted self-wither.", "🤨 Why would you want to wither yourself?", log_error_obj=None)
        return
    if user.id == SELF_PROTECTED_ID and interaction_user.id != SELF_PROTECTED_ID: # Allow self-wither for protected ID
        await fail_and_log(f"User `{interaction_user}` attempted to wither the Creator ({user.id}).", "😨 You dare attempt to wither the Creator?!")
        return
    if user.id == BOT_ID:
        await fail_and_log("User attempted to wither the bot.", "😭 Master... you would wither *me*...?")
        return
    if user.bot:
         await fail_and_log(f"User attempted to wither a bot ({user.name}).", "🤖 Wither has no effect on fellow bots.")
         return

    # 3. Time Validation
    time_seconds = int(time * 60)
    max_mins = MAX_WITHER_SECONDS / 60
    if not (0 < time_seconds <= MAX_WITHER_SECONDS):
        await fail_and_log(f"Invalid time provided ({time} minutes / {time_seconds}s). Max is {MAX_WITHER_SECONDS}s.", f"❌ Time must be between 0 and {max_mins:.0f} minutes.")
        return

    # 4. Hierarchy Check (Bot vs Target)
    if bot_member.top_role <= user.top_role:
        await fail_and_log(f"Bot role (`{bot_member.top_role.name}`) is not high enough to manage roles for {user.name} (`{user.top_role.name}`).", "❌ I cannot wither someone whose highest role is equal to or above mine!")
        return

    # 5. Hierarchy Check (Invoker vs Target) - Optional but good practice
    if interaction_user.top_role <= user.top_role and interaction_user.id != guild.owner_id:
         await fail_and_log(f"Invoker `{interaction_user.name}` role (`{interaction_user.top_role.name}`) not high enough for {user.name} (`{user.top_role.name}`).", "❌ You cannot wither someone whose highest role is equal to or above yours.")
         return

    # --- Execution ---
    # Defer public response now that checks passed
    await interaction.response.defer(thinking=True, ephemeral=False)

    # Store original roles (excluding @everyone)
    original_roles = [role for role in user.roles if role != guild.default_role]
    if not original_roles:
        await log_info(guild, f"Wither cancelled: User {user.name} ({user.id}) had no roles to remove.")
        await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} has no roles to remove.", discord.Color.orange()))
        return

    try:
        # Remove roles (replace with empty list, keeping @everyone implicitly)
        await user.edit(roles=[], reason=f"Withered by {interaction_user.name} for {time:.2f}m")
        role_names = ', '.join([f"`{r.name}`" for r in original_roles])
        if len(role_names) > 1000: role_names = role_names[:1000] + "..." # Avoid exceeding embed limits
        embed = create_embed(
            title="🌪️ Wither Cast! 🌪️",
            description=f"{user.mention} has been withered by {interaction_user.mention} for **{time:.2f} minutes**!\n\nRoles removed: {role_names}",
            color=discord.Color.dark_purple()
        )
        await interaction.followup.send(embed=embed) # Public confirmation
        await log_info(guild, f"`{user.name}` ({user.id}) withered by `{interaction_user.name}` for {time:.2f}m. Roles removed: [{', '.join(str(r.id) for r in original_roles)}]")

        # --- Wait Period ---
        await asyncio.sleep(time_seconds)

        # --- Restore Roles ---
        # Re-fetch the member object in case they left and rejoined, or properties changed
        try:
            member_after_wait = await guild.fetch_member(user.id)
            if member_after_wait:
                # Check hierarchy again before restoring (in case roles changed during wither)
                if bot_member.top_role <= member_after_wait.top_role:
                     await log_error(guild, f"Wither Restore Fail: Bot role no longer high enough for {member_after_wait.name} after wait period.")
                     await interaction.followup.send(embed=create_embed(f"⚠️ Failed to restore roles for {member_after_wait.mention} - my role hierarchy is no longer sufficient.", discord.Color.red()), ephemeral=True) # Ephemeral notice of failure
                     return

                await member_after_wait.edit(roles=original_roles, reason=f"Wither duration ({time:.2f}m) ended.")
                await interaction.followup.send(embed=create_embed(f"✨ {member_after_wait.mention}'s roles have been restored!", color=NERDY_YELLOW)) # Public restore message
                await log_info(guild, f"Restored roles for `{member_after_wait.name}` ({member_after_wait.id}) after wither.")
            else:
                # This case should be covered by fetch_member raising NotFound, but added for clarity
                await log_info(guild, f"User `{user.name}` ({user.id}) left the server before roles could be restored.")
                # No message needed in channel if user left

        except discord.NotFound:
            await log_info(guild, f"User `{user.name}` ({user.id}) could not be found for role restoration (likely left).")
            # No message needed in channel if user left
        except discord.Forbidden as fe_restore:
            await log_error(guild, "Wither restore failed (Forbidden). Check hierarchy/perms.", error=fe_restore)
            await interaction.followup.send(embed=create_embed(f"⚠️ Failed to restore roles for {user.mention} due to permission issues. Please check bot permissions and role hierarchy.", discord.Color.red()), ephemeral=True) # Ephemeral failure notice
        except Exception as e_restore:
            await log_error(guild, "Wither restore failed (Unexpected Error).", error=e_restore)
            await interaction.followup.send(embed=create_embed(f"⚠️ An unexpected error occurred while restoring roles for {user.mention}.", discord.Color.red()), ephemeral=True) # Ephemeral failure notice

    except discord.Forbidden as fe_remove:
         # This error happens during the initial role removal
         await fail_and_log("Remove roles Forbidden during initial wither cast.", "❌ Failed to remove roles initially due to permissions. Check role hierarchy.", log_error_obj=fe_remove)
    except Exception as e_remove:
         # This catches unexpected errors during the initial role removal or the wait setup
         await fail_and_log("Unexpected error during wither process (before restore).", "❌ An unexpected error occurred while trying to wither the user.", log_error_obj=e_remove)


# /nerdhelp definition (public)
@tree.command(name="nerdhelp", description="Show Catercord slash commands help menu.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command provides server-specific help and can only be used within the server.", ephemeral=True)
        return

    embed = discord.Embed(title="🤓 Catercord Command List", description="Here are the available slash commands:", color=NERDY_YELLOW)
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    list_channel_mention = list_channel.mention if list_channel else f"(Channel ID: {HC_MEMBER_LIST_CHANNEL_ID})"
    allowed_channel_mentions = [f"<#{cid}>" for cid in ALLOWED_CHANNEL_IDS if guild.get_channel(cid)]
    allowed_channels_str = ", ".join(allowed_channel_mentions) if allowed_channel_mentions else "configured channels"

    def add_help_field(name: str, value: str, permissions: str = "Everyone", notes: str = None):
        full_value = value
        full_value += f"\n**Permissions:** `{permissions}`" if permissions else ""
        full_value += f"\n**Note:** {notes}" if notes else ""
        embed.add_field(name=name, value=full_value, inline=False)

    # User Management Commands
    embed.add_field(name="\u200B", value="**--- User Verification ---**", inline=False) # Separator
    add_help_field("/verify <user>", "Assigns the 'Verified' role and removes 'Unverified'.", "Manage Roles")
    add_help_field("/unverify <user>", "Assigns the 'Unverified' role and removes 'Verified'.", "Manage Roles")
    add_help_field("/hcverify <user> <IGN>", "Verifies user into HC, saves IGN, assigns roles, sets nickname.", "Manage Roles", "Removes 'Unverified', adds 'Verified' & 'HC'. Updates static list.")
    add_help_field("/unhcverify <user>", "Removes the 'HC' role and resets the user's nickname.", "Manage Roles", "Updates static list.")

    # HC List Commands
    embed.add_field(name="\u200B", value="**--- [HC1] Guild List ---**", inline=False) # Separator
    add_help_field("/hcmembers", "Shows an interactive, paginated list of HC members and their IGNs.", "Everyone", f"Usable only in: {allowed_channels_str}.")
    add_help_field("/refresh", "Manually forces an update of the static HC member list.", "Manage Roles", f"Updates the list message(s) in {list_channel_mention}.")

    # Utility/Admin Commands
    embed.add_field(name="\u200B", value="**--- Utilities & Admin ---**", inline=False) # Separator
    add_help_field("/bulkupdate", "Opens a form to bulk update/add member IGNs.", "Manage Roles", "Format: `DiscordName ➔ InGameName` per line. Updates static list after.")
    add_help_field("/syncnicknames", "Updates nicknames for all HC members based on their stored IGN.", "Manage Roles", "Sets nickname to IGN (max 32 chars).")
    add_help_field("/wither <user> [time]", "Temporarily removes all roles from a user (except @everyone).", "Special Permission", f"Default 2 mins, Max {MAX_WITHER_SECONDS/60:.0f} mins. Requires specific user ID config.")
    add_help_field("/nerdhelp", "Shows this help menu.", "Everyone")

    embed.set_footer(text="Bot by TheNerd | Stay nerdy!")
    if bot.user and bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)

    # Send publicly
    await interaction.response.send_message(embed=embed, ephemeral=False)


# --- Bot Startup ---
if __name__ == "__main__":
    print("Initializing Bot...")
    if TOKEN:
        print("Discord token found.")
        if supabase:
            print("Supabase client configured.")
            print("Starting Flask keep-alive thread...")
            keep_alive() # Start the keep-alive web server
            try:
                print("Starting Discord Bot...")
                # Running the bot within an async context manager if possible,
                # though bot.run() blocks, so this is more for structure.
                # asyncio.run(bot.start(TOKEN)) # Alternative way to run
                bot.run(TOKEN) # This blocks until the bot stops
            except discord.LoginFailure:
                print("CRITICAL: Bot login failed. Check the DISCORD_BOT_TOKEN.")
            except discord.PrivilegedIntentsRequired:
                 print("CRITICAL: Privileged Intents (Server Members Intent) are required but not enabled in the Discord Developer Portal.")
            except Exception as e:
                print(f"CRITICAL: Bot run failed with an unexpected error: {e}")
                print(traceback.format_exc())
        else:
            print("CRITICAL: Supabase client failed to initialize. Bot will not run.")
    else:
        print("CRITICAL: DISCORD_BOT_TOKEN environment variable not set. Bot cannot start.")
