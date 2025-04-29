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
REMOVE_ROLE_ID = 1360176495947022447 # "Unverified" role (to be removed on verify/hcverify)
ADD_ROLE_ID_VERIFY = 1248708073019805717 # "Verified" role (added on verify/hcverify)
ADD_ROLE_ID_HC = 1230235110415274004 # "HC" role (added on hcverify)
ALLOWED_CHANNEL_IDS = {1354431395140731165, 1330664430148780102, 1248710731407560835} # Channels for /hcmembers
HC_MEMBER_LIST_CHANNEL_ID = 1354431395140731165 # Channel for the static list
HC_LIST_EMBED_TITLE = "**\[HC1\] Guild Members**"
ALLOWED_WITHER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692} # User IDs allowed to use /wither
SELF_PROTECTED_ID = 1230848174218940416 # User ID protected from /wither by others
BOT_ID = 1365572437185400893 # Bot's own User ID
MAX_WITHER_SECONDS = 600 # Max duration for /wither in seconds (10 minutes)
INFO_LOG_CHANNEL_ID = 1317943895606165579 # Channel for general info logs
ERROR_LOG_CHANNEL_ID = 1362988767367135453 # Channel for error logs
MEMBERS_PER_PAGE = 50 # Members per page in lists
NERDY_YELLOW = discord.Color.gold() # Embed color

# --- Supabase Client ---
supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase client created successfully.")
        # Optional: Test connection
        # response = supabase.table('hc_members').select('discord_id', count='exact').limit(1).execute()
        # print(f"Supabase connection test successful. Count: {response.count}")
    except Exception as e:
        print(f"CRITICAL: Failed to create Supabase client: {e}")
        supabase = None
else:
    print("CRITICAL: SUPABASE_URL or SUPABASE_KEY environment variables are missing.")
    supabase = None

# --- Discord Setup ---
intents = discord.Intents.default()
intents.members = True # Crucial for member operations and lists
intents.message_content = False # Not needed for slash commands
bot = commands.Bot(command_prefix="!", intents=intents) # Prefix is unused for slash commands
tree = bot.tree

# --- Flask App (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Pingslave bot is alive!"

def run_flask():
    try:
        # Render typically assigns the port via the PORT environment variable
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Flask server failed to start: {e}")

def keep_alive():
    """Starts the Flask server in a background thread."""
    flask_thread = threading.Thread(target=run_flask, daemon=True) # Use daemon thread
    flask_thread.start()
    print("Keep alive thread started.")

# --- Utility Functions ---
async def run_supabase_sync(func):
    """Runs a synchronous Supabase function in an executor."""
    if not supabase:
        print("Attempted Supabase operation, but client is not initialized.")
        raise ConnectionError("Supabase client is not available.")
    try:
        # Ensure bot.loop is available, might need adjustment if run very early
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func)
    except APIError as api_err:
        print(f"Supabase API Error: {api_err}")
        raise # Re-raise for specific handling
    except Exception as e:
        print(f"Error running Supabase function in executor: {e}")
        raise # Re-raise general errors

# --- Logging ---
async def log_to_channel(channel_id: int, guild: discord.Guild | None, message: str | None = None, embed: discord.Embed | None = None):
    """Sends a log message or embed to a specified channel."""
    if not guild:
        print(f"Log Error: Cannot log to channel {channel_id}, Guild context is missing. Message: {message or 'Embed'}")
        return
    log_channel = guild.get_channel(channel_id)
    if isinstance(log_channel, discord.TextChannel): # Check if it's a text channel
        try:
            # Check permissions before attempting to send
            bot_member = guild.me
            perms = log_channel.permissions_for(bot_member)
            if not perms.send_messages or (embed and not perms.embed_links):
                 missing = []
                 if not perms.send_messages: missing.append("Send Messages")
                 if embed and not perms.embed_links: missing.append("Embed Links")
                 print(f"Log Error: Missing permissions ({', '.join(missing)}) in log channel #{log_channel.name} ({guild.name}).")
                 return

            if embed:
                await log_channel.send(embed=embed)
            elif message:
                # Truncate message if too long for Discord
                safe_message = (message[:1997] + "...") if len(message) > 2000 else message
                await log_channel.send(safe_message)
        except discord.Forbidden:
            # This might still happen if permissions change between check and send
            print(f"Log Error: Forbidden to send message in log channel #{log_channel.name} ({guild.name}).")
        except discord.HTTPException as http_err:
            print(f"Log Error: Discord HTTP error when sending to #{log_channel.name} ({guild.name}): {http_err.status} {http_err.code} - {http_err.text}")
        except Exception as e:
            print(f"Log Error: Unexpected error sending to log channel #{log_channel.name} ({guild.name}): {e}")
    else:
        print(f"Log Error: Channel ID {channel_id} not found or is not a text channel in guild {guild.name}.")

async def log_info(guild: discord.Guild | None, message: str, embed: discord.Embed | None = None):
    """Logs an informational message."""
    if not embed:
        embed = discord.Embed(description=message, color=NERDY_YELLOW)
        embed.timestamp = discord.utils.utcnow()
    await log_to_channel(INFO_LOG_CHANNEL_ID, guild, embed=embed)

async def log_error(guild: discord.Guild | None, message: str, error: Exception | None = None, interaction: discord.Interaction | None = None, embed: discord.Embed | None = None):
    """Logs an error message, optionally including exception details and interaction context."""
    if not embed:
        embed = discord.Embed(title="⚠️ Bot Error / Warning", description=message, color=discord.Color.red())
        embed.timestamp = discord.utils.utcnow()
        if interaction:
            context = f"Command: `/{interaction.command.name if interaction.command else 'Unknown'}`"
            if interaction.channel: context += f" in {interaction.channel.mention}" if isinstance(interaction.channel, discord.TextChannel) else f" in channel `{interaction.channel.id}`"
            context += f"\nUser: {interaction.user.mention} (`{interaction.user.id}`)"
            embed.add_field(name="Context", value=context, inline=False)
        if error:
            err_type = type(error).__name__
            err_msg = str(error)
            # Format traceback (limit length)
            tb_list = traceback.format_exception(type(error), error, error.__traceback__, limit=5)
            tb_str = "".join(tb_list)
            if len(tb_str) > 1000: tb_str = tb_str[:1000] + "\n... (Traceback truncated)"

            err_details = f"**Type:** `{err_type}`\n"
            if err_msg: err_details += f"**Message:** `{err_msg}`\n"
            err_details += f"**Traceback:**\n```py\n{tb_str}\n```"

            embed.add_field(name="Error Details", value=err_details[:1024], inline=False) # Ensure field value doesn't exceed limit
            # Also print full traceback to console for debugging
            full_tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            print(f"--- ERROR LOGGED ---\nGuild: {guild.id if guild else 'N/A'}\nContext Msg: {message}\nError: {err_type}: {err_msg}\nTraceback:\n{full_tb}\n--- END ERROR ---")

    await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, embed=embed)

# --- Embed Pagination View ---
class HCPagesView(View):
    """A view for paginating through the HC member list."""
    def __init__(self, data: list[tuple[discord.Member | None, str]], total_members: int, timeout=300.0):
        super().__init__(timeout=timeout)
        self.data = data
        self.total_members = total_members
        self.current_page = 0
        # Recalculate total_pages based on potentially filtered data length
        self.total_pages = math.ceil(len(self.data) / MEMBERS_PER_PAGE) if self.data else 1
        self.message: discord.Message | None = None # Store message for timeout editing

        self.update_buttons() # Initial button state

    def create_page_embed(self) -> discord.Embed:
        """Creates the embed for the current page."""
        start_index = self.current_page * MEMBERS_PER_PAGE
        end_index = start_index + MEMBERS_PER_PAGE
        page_data = self.data[start_index:end_index]

        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, color=NERDY_YELLOW)
        desc_lines = []
        current_item_index = start_index + 1

        for member, ingame_name in page_data:
            if member: # Check if member object exists (could be None if member left)
                safe_user = discord.utils.escape_markdown(member.display_name) # Use display_name
                safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
                desc_lines.append(f"{current_item_index}. {safe_user} (`{member.name}`) ➔ {safe_ign}")
            else:
                # Handle case where member object is None (user might have left)
                safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
                desc_lines.append(f"{current_item_index}. *User Left Server?* ➔ {safe_ign}")
            current_item_index += 1

        if not desc_lines:
            embed.description = "No members found on this page."
        else:
            embed.description = "\n".join(desc_lines)

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} | Total HC Members: {self.total_members}")
        embed.timestamp = discord.utils.utcnow()
        return embed

    def update_buttons(self):
        """Disables/Enables previous/next buttons based on current page."""
        # Access buttons via self children assuming order [prev, next]
        if hasattr(self, 'children') and len(self.children) >= 2:
            prev_button = self.children[0]
            next_button = self.children[1]
            if isinstance(prev_button, Button):
                prev_button.disabled = self.current_page == 0
            if isinstance(next_button, Button):
                next_button.disabled = self.current_page >= self.total_pages - 1
        else:
             print("Warning: Could not find buttons in HCPagesView children to update state.")

    async def edit_message(self, interaction: discord.Interaction):
        """Helper to edit the message with the current state."""
        embed = self.create_page_embed()
        self.update_buttons()
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.NotFound:
            await log_error(interaction.guild, "Paginated message edit failed (NotFound - msg likely deleted).", interaction=interaction)
        except discord.HTTPException as e:
            await log_error(interaction.guild, f"Paginated message edit failed (HTTP {e.status}).", error=e, interaction=interaction)
        except Exception as e:
             await log_error(interaction.guild, f"Paginated message edit failed (Unexpected).", error=e, interaction=interaction)

    @button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="hc_prev_interactive", row=0)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.edit_message(interaction)
        else:
            # Acknowledge the interaction even if no change happens
            try: await interaction.response.defer()
            except discord.InteractionResponded: pass

    @button(label="Next", style=discord.ButtonStyle.blurple, custom_id="hc_next_interactive", row=0)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.edit_message(interaction)
        else:
            # Acknowledge the interaction even if no change happens
            try: await interaction.response.defer()
            except discord.InteractionResponded: pass

    async def on_timeout(self):
        """Disables buttons when the view times out."""
        if self.message:
            try:
                # Disable all buttons
                for item in self.children:
                    if isinstance(item, Button):
                        item.disabled = True
                await self.message.edit(view=self)
                print(f"Pagination View: Buttons disabled on timeout (message ID: {self.message.id}).")
            except (discord.NotFound, discord.HTTPException, AttributeError) as e:
                 # Common errors if message deleted or perms change
                 print(f"Pagination View: Failed to disable buttons on timeout (message ID: {self.message.id if self.message else 'Unknown'}): {e}")
            except Exception as e:
                 # Catch unexpected errors
                 print(f"Pagination View: Unexpected error disabling buttons on timeout - {e}")
        else:
            print("Pagination View: Timeout occurred but no message was associated with the view.")

# --- Core HC List Logic ---
async def fetch_hc_member_data(guild: discord.Guild) -> tuple[list[tuple[discord.Member | None, str]], int]:
    """Fetches HC role members and their IGNs from Supabase."""
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"HC Role (ID: {ADD_ROLE_ID_HC}) not found in fetch_hc_member_data.")
        return [], 0

    # Get members with the HC role (requires Members intent)
    # Ensure bots are excluded
    members_with_role = [m for m in guild.members if hc_role in m.roles and not m.bot]
    total_count = len(members_with_role) # Total count based on role membership

    # Sort members by display name (case-insensitive)
    members_sorted = sorted(members_with_role, key=lambda m: m.display_name.lower())
    member_ids = [str(m.id) for m in members_sorted]
    ign_map = {}

    if supabase and member_ids:
        try:
            # Fetch IGNs in chunks to avoid potential URL length limits if member_ids is huge
            chunk_size = 500
            for i in range(0, len(member_ids), chunk_size):
                chunk_ids = member_ids[i:i + chunk_size]
                resp = await run_supabase_sync(
                    lambda: supabase.table("hc_members")
                                    .select("discord_id, ingame_name")
                                    .in_("discord_id", chunk_ids)
                                    .execute()
                )
                if resp and hasattr(resp, 'data') and resp.data:
                    # Update map, default missing IGN to "Unknown"
                    ign_map.update({r['discord_id']: r.get("ingame_name") or "Unknown" for r in resp.data})
                await asyncio.sleep(0.1) # Brief pause between chunks

        except ConnectionError: # Raised by run_supabase_sync if client is None
             await log_error(guild, "Supabase connection error during IGN fetch.")
             # Populate map indicating DB error for all members we tried to fetch
             ign_map = {mid: "DB Error" for mid in member_ids}
        except Exception as e:
             await log_error(guild, "Failed bulk IGN fetch.", error=e)
             # Populate map indicating generic error
             ign_map = {mid: "Fetch Error" for mid in member_ids}

    # Combine member objects with their fetched IGNs
    # Use get(id, default) for safety
    member_tuples = [(m, ign_map.get(str(m.id), "Unknown")) for m in members_sorted]

    # Note: member_tuples might be shorter than total_count if DB fails,
    # but total_count reflects role membership count.
    return member_tuples, total_count

def generate_hc_list_embeds(data: list[tuple[discord.Member | None, str]], total_members: int) -> list[discord.Embed]:
    """Generates a list of embeds for the static HC member list."""
    embeds = []

    if not data: # Handle case where data list is empty
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, description="No HC members found or could not retrieve details.", color=discord.Color.orange())
        embed.set_footer(text="Page 1/1 | Total HC Members: 0") # Show 0 if list is empty
        embed.timestamp = discord.utils.utcnow()
        return [embed]

    total_pages = math.ceil(len(data) / MEMBERS_PER_PAGE)

    for page_num in range(total_pages):
        start_index = page_num * MEMBERS_PER_PAGE
        end_index = start_index + MEMBERS_PER_PAGE
        page_data = data[start_index:end_index]

        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, color=NERDY_YELLOW)
        desc_lines = []
        current_item_index = start_index + 1

        for member, ingame_name in page_data:
            if member:
                safe_user = discord.utils.escape_markdown(member.display_name)
                safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
                desc_lines.append(f"{current_item_index}. {safe_user} (`{member.name}`) ➔ {safe_ign}")
            else:
                safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
                desc_lines.append(f"{current_item_index}. *User Left Server?* ➔ {safe_ign}")
            current_item_index += 1

        embed.description = "\n".join(desc_lines)
        embed.set_footer(text=f"Page {page_num + 1}/{total_pages} | Total HC Members: {total_members}")
        embed.timestamp = discord.utils.utcnow()
        embeds.append(embed)

    return embeds

async def update_hc_member_list(guild: discord.Guild):
    """Fetches HC members, generates embeds, and updates/posts them in the static list channel."""
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(list_channel, discord.TextChannel):
        await log_error(guild, f"Static list channel (ID: {HC_MEMBER_LIST_CHANNEL_ID}) not found or is not a text channel.")
        return

    bot_member = guild.me
    if not bot_member:
        await log_error(guild, "Could not find bot member in guild during static list update.")
        return

    # Check necessary permissions in the list channel
    perms = list_channel.permissions_for(bot_member)
    required_perms = {"send_messages": perms.send_messages, "embed_links": perms.embed_links, "read_message_history": perms.read_message_history, "manage_messages": perms.manage_messages}
    missing_perms = [name for name, has in required_perms.items() if not has]
    if missing_perms:
        await log_error(guild, f"Bot lacks required permissions in static list channel {list_channel.mention}: {', '.join(missing_perms)}")
        return

    try:
        await log_info(guild, f"Starting static HC list update in {list_channel.mention}...")
        member_data, total_count = await fetch_hc_member_data(guild)
        new_embeds = generate_hc_list_embeds(member_data, total_count)
        num_new_pages = len(new_embeds)

        # Find existing messages posted by the bot with the correct title
        existing_messages: list[discord.Message] = []
        try:
            async for message in list_channel.history(limit=20): # Look further back if needed
                if message.author.id == bot.user.id and message.embeds and message.embeds[0].title == HC_LIST_EMBED_TITLE:
                    existing_messages.append(message)
            # Sort oldest first, crucial for matching pages correctly
            existing_messages.sort(key=lambda m: m.created_at)
        except discord.Forbidden:
             await log_error(guild, f"Cannot read history in {list_channel.mention}. Check Read Message History permission.")
             return
        except Exception as e:
            await log_error(guild, f"Error searching history in {list_channel.mention}.", error=e)
            return # Abort update if history search fails

        num_existing = len(existing_messages)
        print(f"Static List Update ({guild.name}): Found {num_existing} existing message(s), need {num_new_pages} page(s).")

        # --- Edit/Send Loop ---
        # Edit existing messages or send new ones as needed
        edited_or_sent_message_ids = set()
        for i in range(num_new_pages):
            embed_to_use = new_embeds[i]
            if i < num_existing:
                # Try to edit the corresponding existing message
                msg_to_edit = existing_messages[i]
                try:
                    await msg_to_edit.edit(embed=embed_to_use)
                    edited_or_sent_message_ids.add(msg_to_edit.id)
                    print(f"  Edited message {msg_to_edit.id} (Page {i+1}/{num_new_pages})")
                    await asyncio.sleep(1.2) # Rate limiting (be generous)
                except discord.NotFound:
                    print(f"  Existing message {msg_to_edit.id} not found (likely deleted), sending new page {i+1}.")
                    # If edit fails because message is gone, send a new one instead
                    try:
                        new_msg = await list_channel.send(embed=embed_to_use)
                        edited_or_sent_message_ids.add(new_msg.id)
                        print(f"  Sent new message {new_msg.id} (Page {i+1}/{num_new_pages})")
                        await asyncio.sleep(1.2)
                    except Exception as send_e:
                        await log_error(guild, f"Failed to send static list page {i+1} after edit failed.", error=send_e)
                except discord.Forbidden:
                     await log_error(guild, f"Failed to edit static list msg {i+1} (ID: {msg_to_edit.id}) - Forbidden.")
                     break # Stop if permissions fail
                except Exception as edit_e:
                    await log_error(guild, f"Failed to edit static list msg {i+1} (ID: {msg_to_edit.id}).", error=edit_e)
                    edited_or_sent_message_ids.add(msg_to_edit.id) # Keep track even if edit failed
            else:
                # Need to send a new message for this page
                try:
                    new_msg = await list_channel.send(embed=embed_to_use)
                    edited_or_sent_message_ids.add(new_msg.id)
                    print(f"  Sent new message {new_msg.id} (Page {i+1}/{num_new_pages})")
                    await asyncio.sleep(1.2)
                except discord.Forbidden:
                    await log_error(guild, f"Failed to send static list page {i+1} - Forbidden.")
                    break # Stop if permissions fail
                except Exception as send_e:
                    await log_error(guild, f"Failed to send static list page {i+1}.", error=send_e)

        # --- Delete Surplus Old Messages ---
        # Delete any old messages that are no longer needed
        messages_to_delete = [msg for msg in existing_messages if msg.id not in edited_or_sent_message_ids]

        if messages_to_delete:
             print(f"  Deleting {len(messages_to_delete)} surplus static list message(s)...")
             deleted_count = 0
             for msg_to_delete in messages_to_delete:
                 try:
                     await msg_to_delete.delete()
                     deleted_count += 1
                     print(f"    Deleted surplus message {msg_to_delete.id}")
                     await asyncio.sleep(1.2) # Rate limiting for deletes
                 except discord.Forbidden:
                     await log_error(guild, f"Failed to delete surplus msg (ID: {msg_to_delete.id}) - Missing Manage Messages perm?")
                     break # Stop trying if permissions are wrong
                 except discord.NotFound:
                     print(f"    Tried to delete surplus message {msg_to_delete.id}, but it was already gone.")
                 except Exception as delete_e:
                     await log_error(guild, f"Failed to delete surplus msg (ID: {msg_to_delete.id}).", error=delete_e)
             await log_info(guild, f"Deleted {deleted_count}/{len(messages_to_delete)} surplus static list message(s).")

        await log_info(guild, f"Static HC list update complete in {list_channel.mention} ({num_new_pages} pages updated/sent).")

    except Exception as e:
        await log_error(guild, f"Overall static list update error in {list_channel.mention}.", error=e)
        print(f"CRITICAL ERROR during update_hc_member_list ({guild.name}): {e}\n{traceback.format_exc()}")

# --- Discord Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    synced_count = 0
    try:
        # Sync application commands globally or for specific guilds if needed
        # tree.copy_global_to(guild=discord.Object(id=...)) # Example for guild-specific sync
        print("Attempting to sync application commands...")
        synced = await tree.sync() # Sync globally
        synced_count = len(synced)
        print(f"Successfully synced {synced_count} application commands.")

    except discord.HTTPException as http_err:
        print(f"Command Sync failed (HTTPException): {http_err.status} {http_err.code} - {http_err.text}")
        # Attempt to log error if guilds are available
        primary_guild = bot.guilds[0] if bot.guilds else None
        if primary_guild: await log_error(primary_guild, "Command Sync failed (HTTPException).", error=http_err)
    except Exception as e:
        print(f"Command Sync failed (General Exception): {e}")
        print(traceback.format_exc())
        primary_guild = bot.guilds[0] if bot.guilds else None
        if primary_guild: await log_error(primary_guild, "Command Sync failed (General Exception).", error=e)

    # Initial setup for guilds
    if not bot.guilds:
        print("Bot is not currently in any guilds.")
        return

    print(f"Running initial setup for {len(bot.guilds)} guild(s)...")
    # Use a copy in case the list changes during iteration
    guilds_to_process = list(bot.guilds)
    for guild in guilds_to_process:
        print(f"  Processing guild: {guild.name} ({guild.id})")
        try:
            # Log bot readiness in the guild's info channel
            await log_info(guild, f"Bot ready and online. Synced {synced_count} commands.")

            # Update the static HC member list for the guild
            print(f"    Initiating HC member list update for {guild.name}...")
            await update_hc_member_list(guild)
            print(f"    HC member list update initiated for {guild.name}.")

            await asyncio.sleep(1) # Brief pause between guilds

        except Exception as guild_e:
            log_msg = f"Error during on_ready setup for guild {guild.name} ({guild.id})."
            print(f"ERROR: {log_msg} - {guild_e}")
            # Attempt to log the guild-specific error
            try: await log_error(guild, log_msg, error=guild_e)
            except Exception as log_err_e: print(f"CRITICAL: Failed to log guild setup error for {guild.name}: {log_err_e}")

    print("Initial guild setup complete.")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    """Triggers static list update if HC role is added/removed."""
    guild = after.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role: return # Role doesn't exist in this guild

    # Check if HC role status specifically changed
    before_has_hc = hc_role in before.roles
    after_has_hc = hc_role in after.roles

    if before_has_hc != after_has_hc:
        action = "added to" if after_has_hc else "removed from"
        log_embed = discord.Embed(
            description=f"Detected HC role (`{hc_role.name}`) {action} user {after.mention} (`{after.name}`). Triggering static list update.",
            color=discord.Color.purple()
        )
        await log_info(guild, "", embed=log_embed)
        await update_hc_member_list(guild)

# --- App Command Error Handling ---
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handles errors raised by slash commands."""
    guild = interaction.guild
    user_message = "❌ An unexpected error occurred while processing your command." # Default
    log_description = "Unhandled application command error."
    error_to_log = error # Log the original error by default

    # Handle specific error types
    if isinstance(error, app_commands.CommandNotFound):
        print(f"CommandNotFound triggered for: {interaction.command.name if interaction.command else 'N/A'}")
        return # Discord usually handles this; no need to respond.
    elif isinstance(error, app_commands.MissingPermissions):
        perms = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
        user_message = f"❌ You lack the required permissions: {perms}"
        log_description = f"User {interaction.user.mention} lacked permissions ({perms}) for `/{interaction.command.name if interaction.command else 'N/A'}`."
        error_to_log = None # Description is sufficient
    elif isinstance(error, app_commands.BotMissingPermissions):
        perms = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
        user_message = f"❌ I lack the permissions needed for this command: {perms}"
        log_description = f"Bot missing permissions ({perms}) for `/{interaction.command.name if interaction.command else 'N/A'}`."
        error_to_log = None
    elif isinstance(error, app_commands.CheckFailure):
        # Generic check failure (e.g., custom checks, or sometimes perm checks)
        user_message = "❌ You do not meet the requirements to use this command."
        log_description = f"User {interaction.user.mention} failed command checks ({type(error).__name__}) for `/{interaction.command.name if interaction.command else 'N/A'}`."
        error_to_log = None
    elif isinstance(error, app_commands.CommandInvokeError):
        # Error originated within the command's code
        original = error.original
        user_message = f"❌ An error occurred within the command: `{type(original).__name__}`"
        log_description = f"Error invoking `/{interaction.command.name if interaction.command else 'N/A'}`."
        error_to_log = original # Log the underlying error
        print(f"CommandInvokeError for /{interaction.command.name if interaction.command else 'N/A'} by {interaction.user}: {original}")
        # Optionally print traceback here too
        # print(traceback.format_exception(type(original), original, original.__traceback__))
    elif isinstance(error, app_commands.TransformerError):
         user_message = f"❌ Invalid input provided: {error}"
         log_description = f"TransformerError for `/{interaction.command.name if interaction.command else 'N/A'}` by {interaction.user}."
         error_to_log = error
    elif isinstance(error, app_commands.CommandOnCooldown):
        user_message = f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f} seconds."
        log_description = f"User {interaction.user.mention} hit cooldown for `/{interaction.command.name if interaction.command else 'N/A'}`."
        error_to_log = None # Usually not logged as an error
    else:
        # Catch-all for other app command errors
        user_message = "❌ An unknown error occurred processing the command."
        log_description = f"Unknown AppCommandError: `{type(error).__name__}`"
        print(f"Unknown AppCommandError: {type(error).__name__} - {error}")

    # Log the detailed error
    if guild: await log_error(guild, log_description, error=error_to_log, interaction=interaction)
    else: print(f"App Command Error (No Guild Context): {log_description} - Error: {error_to_log}")

    # Send ephemeral feedback to the user
    try:
        if interaction.response.is_done():
            await interaction.followup.send(user_message, ephemeral=True)
        else:
            await interaction.response.send_message(user_message, ephemeral=True)
    except discord.InteractionResponded:
        # Try followup again if response was somehow already sent
        try: await interaction.followup.send(user_message, ephemeral=True)
        except Exception as followup_e: print(f"Failed to send error followup: {followup_e}")
    except discord.NotFound: print("Interaction expired or was deleted before error message could be sent.")
    except discord.HTTPException as http_e: print(f"Failed to send error message (HTTPException): {http_e.status} {http_e.code}")
    except Exception as send_e: print(f"Failed to send error message (Unexpected): {send_e}")

# --- Modals ---
def create_embed(description: str, color: discord.Color = NERDY_YELLOW, title: str | None = None) -> discord.Embed:
     """Helper to create simple embeds."""
     embed = discord.Embed(title=title, description=description, color=color)
     return embed

class BulkUpdateModal(Modal, title="Bulk Update IGNs"):
    """Modal for bulk updating IGNs based on Discord username."""
    data = TextInput(
        label="Paste list (DiscordName#Tag or DisplayName ➔ IGN)",
        style=discord.TextStyle.paragraph,
        placeholder="ExampleUser#1234 ➔ CoolFlorrName\nAnother User ➔ AnotherIGN\n(One entry per line)",
        required=True,
        min_length=5,
        max_length=4000 # Discord limit
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.guild
        if not guild: return # Should not happen from slash command

        if not supabase:
            await interaction.followup.send(embed=create_embed("❌ Supabase client is not available.", discord.Color.red()), ephemeral=True)
            await log_error(guild, "Bulk Update Modal: Supabase client missing.", interaction=interaction)
            return

        lines = self.data.value.strip().splitlines()
        if not lines:
            await interaction.followup.send(embed=create_embed("⚠️ No data provided.", discord.Color.orange()), ephemeral=True)
            return

        # Pre-fetch members for efficiency (requires Members intent)
        try:
            if not guild.chunked: await guild.chunk() # Ensure member cache is populated
            members_map_name = {m.name.lower(): m for m in guild.members if not m.bot} # name#discriminator
            members_map_display = {m.display_name.lower(): m for m in guild.members if not m.bot}
            members_map_id = {str(m.id): m for m in guild.members if not m.bot}
        except Exception as e:
            await log_error(guild, "Bulk Update Modal: Failed to fetch/map guild members.", error=e, interaction=interaction)
            await interaction.followup.send(embed=create_embed("❌ Error preparing member list. Cannot proceed.", discord.Color.red()), ephemeral=True)
            return

        success_count, fail_count, not_found_count = 0, 0, 0
        results_log = [] # Stores ('type', 'message')
        upsert_payload = []

        for idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line: continue # Skip empty lines

            if "➔" not in line:
                fail_count += 1
                results_log.append(('f', f"L{idx}: Format Error (Missing '➔'). Line: `{line[:50]}`"))
                continue

            try:
                discord_identifier, ingame_name = map(str.strip, line.split("➔", 1))
                if not discord_identifier or not ingame_name:
                    fail_count += 1
                    results_log.append(('f', f"L{idx}: Missing Discord name/ID or IGN. Line: `{line[:50]}`"))
                    continue
            except ValueError:
                fail_count += 1
                results_log.append(('f', f"L{idx}: Format Error (Splitting '➔'). Line: `{line[:50]}`"))
                continue

            # Find member by ID, Name#Tag, or Display Name
            member: discord.Member | None = None
            identifier_lower = discord_identifier.lower()

            if discord_identifier.isdigit() and discord_identifier in members_map_id:
                 member = members_map_id[discord_identifier]
            elif identifier_lower in members_map_name:
                member = members_map_name[identifier_lower]
            elif identifier_lower in members_map_display:
                member = members_map_display[identifier_lower]
            # Add fuzzy matching here if desired, but it's slow and potentially inaccurate

            if not member:
                fail_count += 1
                not_found_count += 1
                results_log.append(('f', f"L{idx}: User `{discord.utils.escape_markdown(discord_identifier)}` not found in server."))
                continue

            # Add valid entry to payload for bulk upsert
            upsert_payload.append({
                "discord_id": str(member.id),
                "discord_name": member.name, # Store canonical username
                "ingame_name": ingame_name
            })

        # --- Perform Bulk Upsert ---
        db_errors_occured = False
        if upsert_payload:
            try:
                print(f"Bulk Update: Attempting to upsert {len(upsert_payload)} records.")
                await run_supabase_sync(
                    lambda: supabase.table("hc_members")
                                    .upsert(upsert_payload, on_conflict="discord_id") # Assumes discord_id is PK/Unique
                                    .execute()
                )
                # If no exception, assume all in payload succeeded
                success_count = len(upsert_payload)
                print(f"Bulk Update: Upsert successful for {success_count} records.")
            except ConnectionError:
                db_errors_occured = True
                fail_count += len(upsert_payload) # All failed
                results_log.append(('f', "DB: Connection Error during bulk upsert."))
                await log_error(guild, "Bulk DB Connection Error", interaction=interaction)
            except APIError as api_err:
                db_errors_occured = True
                fail_count += len(upsert_payload) # Assume all failed
                results_log.append(('f', f"DB: API Error during bulk upsert: {api_err.message}"))
                await log_error(guild, f"Bulk DB APIError", error=api_err, interaction=interaction)
            except Exception as e:
                db_errors_occured = True
                fail_count += len(upsert_payload) # Assume all failed
                results_log.append(('f', f"DB: Unexpected error during bulk upsert: {type(e).__name__}"))
                await log_error(guild, f"Bulk DB unexpected error", error=e, interaction=interaction)
        else:
             print("Bulk Update: No valid entries found to upsert.")


        # --- Prepare Results Embed ---
        embed = discord.Embed(title="Bulk Update Results", color=NERDY_YELLOW if not fail_count else discord.Color.orange())
        summary = f"Lines Processed: {len(lines)}\n" \
                  f"✅ Successfully Saved/Updated: {success_count}\n" \
                  f"❌ Failures: {fail_count}\n" \
                  f"  - User Not Found: {not_found_count}\n" \
                  f"  - Format/DB Errors: {fail_count - not_found_count}"
        embed.description = summary

        error_details = "\n".join([r[1] for r in results_log if r[0] == 'f'])
        if error_details:
            field_value = (error_details[:1021] + "...") if len(error_details) > 1024 else error_details
            embed.add_field(name="Issues Encountered", value=field_value, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

        # Log summary
        log_embed = discord.Embed(
            description=f"Bulk IGN update finished for `{interaction.user}`. Success: {success_count}, Fail: {fail_count}.",
            color=NERDY_YELLOW if not fail_count else discord.Color.orange()
        )
        await log_info(guild, "", embed=log_embed)

        # Update the static list if changes were successfully made
        if success_count > 0:
            await update_hc_member_list(guild)

# --- Slash Commands ---

# --- Verify Command ---
@tree.command(name="verify", description="Verify a standard user (adds Verified, removes Unverified).")
@app_commands.describe(user="The user to verify.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    unverified_role = guild.get_role(REMOVE_ROLE_ID)
    verified_role = guild.get_role(ADD_ROLE_ID_VERIFY)
    actions_performed = []
    missing_setup_roles = []

    # Check if configured roles exist
    if not unverified_role: missing_setup_roles.append(f"'Unverified' (ID: {REMOVE_ROLE_ID})")
    if not verified_role: missing_setup_roles.append(f"'Verified' (ID: {ADD_ROLE_ID_VERIFY})")

    if missing_setup_roles:
        errmsg = f"Bot setup error: Cannot find required role(s): {', '.join(missing_setup_roles)}."
        await log_error(guild, f"/verify setup error: {errmsg}", interaction=interaction)
        await interaction.response.send_message(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
        return

    # Check bot hierarchy vs target user
    if guild.me.top_role <= user.top_role and user.id != guild.owner_id:
         errmsg = f"I cannot manage roles for {user.mention} because their highest role (`{user.top_role.name}`) is equal to or higher than mine (`{guild.me.top_role.name}`)."
         await log_error(guild, f"/verify hierarchy error: {errmsg}", interaction=interaction)
         await interaction.response.send_message(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
         return

    # Defer response after initial checks
    await interaction.response.defer(thinking=True, ephemeral=True) # Ephemeral thinking

    try:
        modified = False
        reason = f"Verified by {interaction.user} via /verify command."

        # Remove 'Unverified' role if present
        if unverified_role and unverified_role in user.roles:
            await user.remove_roles(unverified_role, reason=reason)
            actions_performed.append(f"➖ Removed `{unverified_role.name}`")
            modified = True

        # Add 'Verified' role if not present
        if verified_role and verified_role not in user.roles:
            await user.add_roles(verified_role, reason=reason)
            actions_performed.append(f"➕ Added `{verified_role.name}`")
            modified = True

        if not modified:
            embed = create_embed(f"ℹ️ No role changes needed for {user.display_name}. They likely already have the correct roles.", discord.Color.orange())
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            log_msg = f"`{interaction.user}` verified {user.mention} (`{user.id}`). Actions: {' '.join(actions_performed)}."
            await log_info(guild, log_msg)
            embed = create_embed(f"✅ **{user.display_name}** has been verified!\n" + "\n".join(actions_performed), discord.Color.green())
            # Send public confirmation, keep followup ephemeral for command feedback
            await interaction.followup.send(embed=create_embed("✅ Verification successful!", discord.Color.green()), ephemeral=True)
            try: await interaction.channel.send(embed=embed) # Send public confirmation in channel
            except Exception as public_send_e: await log_error(guild, "Failed to send public verify confirmation", error=public_send_e, interaction=interaction)


    except discord.Forbidden:
        errmsg = f"I lack permissions to manage roles for {user.mention}. Please check my role position and 'Manage Roles' permission."
        await log_error(guild, f"/verify Forbidden: {errmsg}", interaction=interaction)
        await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
    except discord.HTTPException as http_e:
        errmsg = f"A Discord API error occurred while verifying {user.mention}."
        await log_error(guild, f"/verify HTTPException: {errmsg}", error=http_e, interaction=interaction)
        await interaction.followup.send(embed=create_embed(f"❌ {errmsg} (HTTP {http_e.status})", discord.Color.red()), ephemeral=True)
    except Exception as e:
        # This is the block where the original error occurred.
        errmsg = f"An unexpected error occurred while verifying {user.mention}."
        await log_error(guild, f"/verify error processing {user.display_name} ({user.id})", error=e, interaction=interaction)
        # Ensure followup is used correctly after defer.
        await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)


# --- Unverify Command ---
@tree.command(name="unverify", description="Revert a user to Unverified status.")
@app_commands.describe(user="The user to unverify.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def unverify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    verified_role = guild.get_role(ADD_ROLE_ID_VERIFY) # Role to remove
    unverified_role = guild.get_role(REMOVE_ROLE_ID) # Role to add
    actions_performed = []
    missing_setup_roles = []

    if not verified_role: missing_setup_roles.append(f"'Verified' (ID: {ADD_ROLE_ID_VERIFY})")
    if not unverified_role: missing_setup_roles.append(f"'Unverified' (ID: {REMOVE_ROLE_ID})")

    if missing_setup_roles:
        errmsg = f"Bot setup error: Cannot find required role(s): {', '.join(missing_setup_roles)}."
        await log_error(guild, f"/unverify setup error: {errmsg}", interaction=interaction)
        await interaction.response.send_message(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
        return

    if guild.me.top_role <= user.top_role and user.id != guild.owner_id:
         errmsg = f"I cannot manage roles for {user.mention} because their highest role (`{user.top_role.name}`) is equal to or higher than mine (`{guild.me.top_role.name}`)."
         await log_error(guild, f"/unverify hierarchy error: {errmsg}", interaction=interaction)
         await interaction.response.send_message(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
         return

    await interaction.response.defer(thinking=True, ephemeral=True) # Ephemeral thinking

    try:
        modified = False
        reason = f"Unverified by {interaction.user} via /unverify command."

        # Remove 'Verified' role if present
        if verified_role and verified_role in user.roles:
            await user.remove_roles(verified_role, reason=reason)
            actions_performed.append(f"➖ Removed `{verified_role.name}`")
            modified = True

        # Add 'Unverified' role if not present
        if unverified_role and unverified_role not in user.roles:
            await user.add_roles(unverified_role, reason=reason)
            actions_performed.append(f"➕ Added `{unverified_role.name}`")
            modified = True

        if not modified:
            embed = create_embed(f"ℹ️ No role changes needed for {user.display_name}. They likely already have the unverified roles.", discord.Color.orange())
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            log_msg = f"`{interaction.user}` unverified {user.mention} (`{user.id}`). Actions: {' '.join(actions_performed)}."
            await log_info(guild, log_msg)
            embed = create_embed(f"✅ **{user.display_name}** has been unverified!\n" + "\n".join(actions_performed), discord.Color.green())
            # Send public confirmation
            await interaction.followup.send(embed=create_embed("✅ Un-verification successful!", discord.Color.green()), ephemeral=True)
            try: await interaction.channel.send(embed=embed)
            except Exception as public_send_e: await log_error(guild, "Failed to send public unverify confirmation", error=public_send_e, interaction=interaction)

    except discord.Forbidden:
        errmsg = f"I lack permissions to manage roles for {user.mention}. Please check my role position and 'Manage Roles' permission."
        await log_error(guild, f"/unverify Forbidden: {errmsg}", interaction=interaction)
        await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
    except discord.HTTPException as http_e:
        errmsg = f"A Discord API error occurred while un-verifying {user.mention}."
        await log_error(guild, f"/unverify HTTPException: {errmsg}", error=http_e, interaction=interaction)
        await interaction.followup.send(embed=create_embed(f"❌ {errmsg} (HTTP {http_e.status})", discord.Color.red()), ephemeral=True)
    except Exception as e:
        errmsg = f"An unexpected error occurred while un-verifying {user.mention}."
        await log_error(guild, f"/unverify error processing {user.display_name} ({user.id})", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)


# --- HC Verify Command ---
@tree.command(name="hcverify", description="Verify user into HC, store IGN, set nickname.")
@app_commands.describe(user="The user to HC verify.", ingame_name="The user's Florr.io In-Game Name.")
@app_commands.checks.has_permissions(manage_roles=True, manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    await interaction.response.defer(thinking=True, ephemeral=False) # Public defer
    guild = interaction.guild

    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Database connection is unavailable. Cannot save IGN.", discord.Color.red()), ephemeral=True)
        await log_error(guild, "HCVerify: Supabase client missing.", interaction=interaction)
        return

    # Role IDs
    unverified_role = guild.get_role(REMOVE_ROLE_ID)
    verified_role = guild.get_role(ADD_ROLE_ID_VERIFY)
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    log_actions, response_lines = [], []
    missing_roles = []

    # Check required roles exist
    if not unverified_role: missing_roles.append(f"'Unverified' ({REMOVE_ROLE_ID})")
    if not verified_role: missing_roles.append(f"'Verified' ({ADD_ROLE_ID_VERIFY})")
    if not hc_role: missing_roles.append(f"'HC' ({ADD_ROLE_ID_HC})")
    if missing_roles:
        errmsg = f"Bot setup error: Cannot find required role(s): {', '.join(missing_roles)}."
        await log_error(guild, f"/hcverify setup error: {errmsg}", interaction=interaction)
        await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
        return

    # Hierarchy check
    if guild.me.top_role <= user.top_role and user.id != guild.owner_id:
         errmsg = f"I cannot manage roles/nickname for {user.mention} due to role hierarchy."
         await log_error(guild, f"/hcverify hierarchy error: {errmsg}", interaction=interaction)
         await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
         return

    try:
        original_had_hc_role = hc_role in user.roles
        roles_to_add = []
        roles_modified = False
        reason = f"HC Verified by {interaction.user}."

        # 1. Role Management
        if unverified_role and unverified_role in user.roles:
            await user.remove_roles(unverified_role, reason=reason)
            log_actions.append(f"Removed Unverified Role (`{unverified_role.name}`)")
            roles_modified = True
        if verified_role and verified_role not in user.roles: roles_to_add.append(verified_role)
        if hc_role and hc_role not in user.roles: roles_to_add.append(hc_role)

        if roles_to_add:
            await user.add_roles(*roles_to_add, reason=reason)
            added_names = ', '.join([f"`{r.name}`" for r in roles_to_add])
            log_actions.append(f"Added Roles: {added_names}")
            response_lines.append(f"➕ Roles Added: {added_names}")
            roles_modified = True
        elif not roles_modified:
            response_lines.append("ℹ️ Roles already assigned.")

        # 2. Database Update
        db_ok = False
        try:
            await run_supabase_sync(
                lambda: supabase.table("hc_members")
                                .upsert({"discord_id": str(user.id), "discord_name": user.name, "ingame_name": ingame_name}, on_conflict="discord_id")
                                .execute()
            )
            log_actions.append(f"Upserted IGN: '{ingame_name}'")
            response_lines.append(f"💾 IGN Saved: `{discord.utils.escape_markdown(ingame_name)}`")
            db_ok = True
        except ConnectionError:
             log_actions.append("DB Upsert FAILED (Connection Error)")
             response_lines.append("⚠️ Database connection failed!")
             await log_error(guild, f"DB connection failed for {user.display_name} ({user.id}) during HCVerify", interaction=interaction)
        except Exception as e:
            log_actions.append(f"DB Upsert FAILED ({type(e).__name__})")
            response_lines.append("⚠️ Database save failed!")
            await log_error(guild, f"DB upsert failed for {user.display_name} ({user.id}) during HCVerify", error=e, interaction=interaction)

        # 3. Nickname Management
        nick_change_status = "No change"
        nickname_truncated = False
        target_nick = ingame_name[:32] # Discord limit
        if len(ingame_name) > 32: nickname_truncated = True

        if user.nick != target_nick:
            try:
                await user.edit(nick=target_nick, reason=reason)
                nick_msg = f"🏷️ Nickname Set: `{discord.utils.escape_markdown(target_nick)}`"
                if nickname_truncated: nick_msg += " (truncated)"
                log_actions.append(f"Set Nickname: '{target_nick}'" + (" (truncated)" if nickname_truncated else ""))
                response_lines.append(nick_msg)
                nick_change_status = "Success"
            except discord.Forbidden:
                log_actions.append("Nickname update FAILED (Forbidden)")
                response_lines.append("⚠️ Nickname update failed (Permissions)")
                nick_change_status = "Perms Fail"
            except Exception as e:
                log_actions.append(f"Nickname update FAILED ({type(e).__name__})")
                response_lines.append("⚠️ Nickname update failed (Error)")
                nick_change_status = "Error"
                await log_error(guild, f"Nickname update failed for {user.display_name} ({user.id}) during HCVerify", error=e, interaction=interaction)
        else:
            log_actions.append("Nickname already correct")
            response_lines.append("🏷️ Nickname already correct.")

        # 4. Final Logging and Response
        log_message = f"`{interaction.user}` HC verified `{user.display_name}` ({user.id}). Actions: {'; '.join(log_actions)}."
        await log_info(guild, log_message)

        title_suffix = ""
        is_error_state = not db_ok or nick_change_status in ["Perms Fail", "Error"]
        if nickname_truncated and nick_change_status == "Success": title_suffix += " (IGN truncated in nick)"
        if is_error_state: title_suffix += " (with issues)"

        embed_color = discord.Color.green() if not is_error_state else discord.Color.orange()
        final_embed = create_embed(
            title=f"✅ HC Verified: {user.display_name}{title_suffix}",
            description="\n".join(response_lines) if response_lines else "No specific actions logged.",
            color=embed_color
        )
        await interaction.followup.send(embed=final_embed) # Public result

        # 5. Update Static List if HC role added OR if IGN updated for existing HC member
        newly_added_hc = hc_role and hc_role in roles_to_add
        if newly_added_hc or (original_had_hc_role and db_ok):
            await update_hc_member_list(guild)

    except discord.Forbidden as fe:
        errmsg = f"Failed HCVerify for {user.mention}. I lack permissions (Manage Roles/Nicknames)."
        await log_error(guild, errmsg, error=fe, interaction=interaction)
        await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
    except discord.HTTPException as http_e:
         errmsg = f"Discord API error during HCVerify for {user.mention}."
         await log_error(guild, errmsg, error=http_e, interaction=interaction)
         await interaction.followup.send(embed=create_embed(f"❌ {errmsg} (HTTP {http_e.status})", discord.Color.red()), ephemeral=True)
    except Exception as e:
        errmsg = f"An unexpected error occurred during HCVerify for {user.mention}."
        await log_error(guild, errmsg, error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)

# --- Un-HC-Verify Command ---
@tree.command(name="unhcverify", description="Remove HC role and reset nickname.")
@app_commands.describe(user="The user to remove from HC verification.")
@app_commands.checks.has_permissions(manage_roles=True, manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def unhcverify(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(thinking=True, ephemeral=False) # Public defer
    guild = interaction.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    log_actions, response_lines = [], []

    if not hc_role:
        errmsg = f"Bot setup error: Cannot find the HC role (ID: {ADD_ROLE_ID_HC})."
        await log_error(guild, f"/unhcverify setup error: {errmsg}", interaction=interaction)
        await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
        return

    if guild.me.top_role <= user.top_role and user.id != guild.owner_id:
        errmsg = f"I cannot manage roles/nickname for {user.mention} due to role hierarchy."
        await log_error(guild, f"/unhcverify hierarchy error: {errmsg}", interaction=interaction)
        await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
        return

    try:
        role_removed = False
        reason = f"Un-HC-Verified by {interaction.user}."

        # 1. Role Removal
        if hc_role in user.roles:
            await user.remove_roles(hc_role, reason=reason)
            log_actions.append(f"Removed HC Role (`{hc_role.name}`)")
            response_lines.append(f"➖ Role Removed: `{hc_role.name}`")
            role_removed = True
        else:
            # If user doesn't have the role, maybe still reset nick? Or just inform?
            # Current logic: Inform and stop if role not present.
            await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} does not have the `{hc_role.name}` role.", discord.Color.orange()), ephemeral=True)
            return

        # 2. Nickname Reset
        nick_reset_status = "No change"
        if user.nick is not None:
            try:
                await user.edit(nick=None, reason=reason)
                log_actions.append("Reset Nickname")
                response_lines.append("🏷️ Nickname Reset")
                nick_reset_status = "Success"
            except discord.Forbidden:
                log_actions.append("Nickname reset FAILED (Forbidden)")
                response_lines.append("⚠️ Nickname reset failed (Permissions)")
                nick_reset_status = "Perms Fail"
            except Exception as e:
                log_actions.append(f"Nickname reset FAILED ({type(e).__name__})")
                response_lines.append("⚠️ Nickname reset failed (Error)")
                nick_reset_status = "Error"
                await log_error(guild, f"Nickname reset failed for {user.display_name} ({user.id}) during UnHCVerify", error=e, interaction=interaction)
        else:
            log_actions.append("No nickname to reset")
            response_lines.append("🏷️ User had no nickname.")

        # 3. Final Logging and Response
        log_message = f"`{interaction.user}` Un-HC-verified `{user.display_name}` ({user.id}). Actions: {'; '.join(log_actions)}."
        await log_info(guild, log_message)

        is_error_state = nick_reset_status in ["Perms Fail", "Error"]
        title_suffix = " (with issues)" if is_error_state else ""
        embed_color = discord.Color.green() if not is_error_state else discord.Color.orange()

        final_embed = create_embed(
            title=f"✅ Un-HC-Verified: {user.display_name}{title_suffix}",
            description="\n".join(response_lines),
            color=embed_color
        )
        await interaction.followup.send(embed=final_embed) # Public result

        # 4. Update Static List if role was successfully removed
        if role_removed:
            await update_hc_member_list(guild)

    except discord.Forbidden as fe:
        errmsg = f"Failed UnHCVerify for {user.mention}. I lack permissions (Manage Roles/Nicknames)."
        await log_error(guild, errmsg, error=fe, interaction=interaction)
        # Check if followup already sent
        if not interaction.is_expired():
            try: await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
            except discord.InteractionResponded: pass # Ignore if somehow already responded
    except discord.HTTPException as http_e:
         errmsg = f"Discord API error during UnHCVerify for {user.mention}."
         await log_error(guild, errmsg, error=http_e, interaction=interaction)
         if not interaction.is_expired():
            try: await interaction.followup.send(embed=create_embed(f"❌ {errmsg} (HTTP {http_e.status})", discord.Color.red()), ephemeral=True)
            except discord.InteractionResponded: pass
    except Exception as e:
        errmsg = f"An unexpected error occurred during UnHCVerify for {user.mention}."
        await log_error(guild, errmsg, error=e, interaction=interaction)
        if not interaction.is_expired():
            try: await interaction.followup.send(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
            except discord.InteractionResponded: pass


# --- HC Members Interactive List ---
@tree.command(name="hcmembers", description="Show an interactive list of [HC1] members.")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    # Check channel restriction
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        allowed_mentions = [f"<#{cid}>" for cid in ALLOWED_CHANNEL_IDS if guild.get_channel(cid)]
        allowed_list = ", ".join(allowed_mentions) if allowed_mentions else "specific configured channels"
        embed = create_embed(f"❌ Please use this command in one of the allowed channels: {allowed_list}", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=False) # Acknowledge publicly

    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Database connection is unavailable. Cannot fetch members.", discord.Color.red()))
        await log_error(guild, "/hcmembers: Supabase client missing.", interaction=interaction)
        return

    try:
        # Fetch data (list of (Member|None, ign), total_role_count)
        member_data, total_count = await fetch_hc_member_data(guild)

        if not member_data:
            # Either no members have the role, or DB fetch failed entirely
            hc_role = guild.get_role(ADD_ROLE_ID_HC)
            role_mention = f"`{hc_role.name}`" if hc_role else f"(Role ID: {ADD_ROLE_ID_HC})"
            desc = f"No members currently have the {role_mention} role."
            if total_count > 0: # Implies role exists, but maybe DB failed?
                 desc = f"Found {total_count} members with the {role_mention} role, but could not retrieve IGN details."

            embed = create_embed(f"{HC_LIST_EMBED_TITLE}\n{desc}", discord.Color.orange())
            await interaction.followup.send(embed=embed)
        else:
            # Create and send the paginated view
            view = HCPagesView(member_data, total_count)
            initial_embed = view.create_page_embed()
            # Send the initial message and store it in the view
            message = await interaction.followup.send(embed=initial_embed, view=view)
            view.message = message # Link message to view for timeout handling
            await log_info(guild, f"/hcmembers interactive list generated by `{interaction.user}` in {interaction.channel.mention}.")

    except Exception as e:
        await log_error(guild, "/hcmembers: Error generating interactive list.", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ An unexpected error occurred while fetching the member list.", discord.Color.red()))


# --- Refresh Static List Command ---
@tree.command(name="refresh", description="Manually refresh the static [HC1] member list.")
@app_commands.checks.has_permissions(manage_roles=True) # Or other appropriate permission
async def refresh(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True) # Ephemeral thinking feedback
    guild = interaction.guild
    if not guild: return # Should be guild context

    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Database connection unavailable.", discord.Color.red()), ephemeral=True)
        return

    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(list_channel, discord.TextChannel):
        await interaction.followup.send(embed=create_embed(f"❌ Static list channel (ID: {HC_MEMBER_LIST_CHANNEL_ID}) not found or invalid.", discord.Color.red()), ephemeral=True)
        await log_error(guild, f"/refresh: Static list channel invalid.", interaction=interaction)
        return

    try:
        await log_info(guild, f"Manual refresh of static list in {list_channel.mention} triggered by `{interaction.user}`.")
        await update_hc_member_list(guild) # Call the update function
        # log_info on completion is handled inside update_hc_member_list
        embed = create_embed(f"✅ Refresh initiated for the static HC list in {list_channel.mention}. It may take a moment to update.", discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await log_error(guild, "Error during manual /refresh execution.", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ An unexpected error occurred during the refresh process.", discord.Color.red()), ephemeral=True)

# --- Bulk Update Command ---
@tree.command(name="bulkupdate", description="Open a form to bulk update member IGNs.")
@app_commands.checks.has_permissions(manage_roles=True) # Adjust permission if needed
async def bulkupdate(interaction: discord.Interaction):
    try:
        await interaction.response.send_modal(BulkUpdateModal())
        await log_info(interaction.guild, f"`{interaction.user}` opened the bulk IGN update modal.")
    except Exception as e:
        await log_error(interaction.guild, "Error opening bulk update modal.", error=e, interaction=interaction)
        # Check if interaction already responded (e.g., modal failed to send)
        if not interaction.response.is_done():
             try: await interaction.response.send_message(embed=create_embed("❌ Failed to open the bulk update form.",discord.Color.red()),ephemeral=True)
             except discord.InteractionResponded: pass # Ignore if already responded somehow

# --- Sync Nicknames Command ---
@tree.command(name="syncnicknames", description="Sync all HC members' nicknames with their stored IGNs.")
@app_commands.checks.has_permissions(manage_nicknames=True) # Requires Manage Nicknames
@app_commands.checks.bot_has_permissions(manage_nicknames=True)
async def syncnicknames(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True) # Ephemeral thinking
    guild = interaction.guild
    if not guild: return

    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Database connection unavailable.", discord.Color.red()), ephemeral=True)
        return

    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await interaction.followup.send(embed=create_embed(f"❌ HC Role (ID: {ADD_ROLE_ID_HC}) not found.", discord.Color.red()), ephemeral=True)
        return

    start_time = discord.utils.utcnow()
    await log_info(guild, f"Nickname sync started by `{interaction.user}` for role `{hc_role.name}`.")
    await interaction.edit_original_response(content="🔄 Fetching HC members and IGN data...")

    # 1. Fetch IGN Data
    ign_data = {}
    try:
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                            .select("discord_id, ingame_name")
                            .execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            ign_data = {item['discord_id']: item['ingame_name'] for item in resp.data if item.get('ingame_name') and item.get('discord_id')}
        print(f"SyncNick ({guild.name}): Fetched {len(ign_data)} IGN records.")
    except ConnectionError:
        await log_error(guild, "SyncNicknames: Database connection failed.", interaction=interaction)
        await interaction.edit_original_response(content="❌ Failed to connect to the database.")
        return
    except Exception as e:
        await log_error(guild, "SyncNicknames: Database fetch failed.", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Failed to fetch IGN data from the database.")
        return

    # 2. Get HC Members
    hc_members = [m for m in guild.members if hc_role in m.roles and not m.bot]
    total_hc_members = len(hc_members)
    if total_hc_members == 0:
        await interaction.edit_original_response(content=f"ℹ️ No members found with the `{hc_role.name}` role.")
        return

    await interaction.edit_original_response(content=f"🔄 Syncing nicknames for {total_hc_members} HC members...")

    # 3. Process Members
    counts = {'processed': 0, 'updated': 0, 'skipped_match': 0, 'skipped_no_ign': 0, 'fail_perms': 0, 'fail_other': 0, 'fail_hierarchy': 0}
    last_update_time = asyncio.get_event_loop().time()
    bot_top_role = guild.me.top_role

    for idx, member in enumerate(hc_members):
        counts['processed'] += 1
        member_id_str = str(member.id)

        # Check hierarchy before attempting edit
        if bot_top_role <= member.top_role and member.id != guild.owner_id:
            counts['fail_hierarchy'] += 1
            if counts['fail_hierarchy'] < 5: # Log first few hierarchy failures
                 await log_error(guild, f"SyncNick Hierarchy Fail: Cannot edit {member.name} ({member.id}). Bot role too low.", interaction=interaction, embed=None)
            continue # Skip member

        # Check if IGN exists
        stored_ign = ign_data.get(member_id_str)
        if not stored_ign:
            counts['skipped_no_ign'] += 1
            continue

        target_nick = stored_ign[:32]

        # Check if update needed
        if member.nick == target_nick:
            counts['skipped_match'] += 1
            continue

        # Attempt nickname update
        try:
            await member.edit(nick=target_nick, reason=f"Nickname Sync by {interaction.user}")
            counts['updated'] += 1
            await asyncio.sleep(0.15) # Slightly longer delay for edits
        except discord.Forbidden:
            counts['fail_perms'] += 1
            # Avoid log spam for repeated permission errors
            if counts['fail_perms'] < 5:
                 await log_error(guild, f"SyncNick Perms Fail: Forbidden to edit nick for {member.name} ({member.id}).", interaction=interaction, embed=None)
        except discord.HTTPException as http_e:
            counts['fail_other'] += 1
            if counts['fail_other'] < 5:
                await log_error(guild, f"SyncNick HTTP Fail: Nick edit for {member.name}. Status: {http_e.status}", error=http_e, interaction=interaction, embed=None)
            await asyncio.sleep(0.5) # Back off slightly on HTTP errors
        except Exception as e:
            counts['fail_other'] += 1
            if counts['fail_other'] < 5:
                await log_error(guild, f"SyncNick Other Fail: Nick edit for {member.name}", error=e, interaction=interaction, embed=None)

        # Update progress indicator periodically
        current_time = asyncio.get_event_loop().time()
        if current_time - last_update_time > 5.0: # Update every 5 secs
            try:
                await interaction.edit_original_response(content=f"🔄 Syncing... ({counts['processed']}/{total_hc_members})")
                last_update_time = current_time
            except (discord.NotFound, discord.InteractionResponded): break # Stop if interaction gone
            except discord.HTTPException: await asyncio.sleep(2) # Wait if update fails

    # 4. Final Summary
    end_time = discord.utils.utcnow()
    duration = (end_time - start_time).total_seconds()
    embed = discord.Embed(title="Nickname Sync Complete!", color=NERDY_YELLOW, timestamp=end_time)
    summary = (
        f"Processed: {counts['processed']}/{total_hc_members}\n"
        f"✅ Updated: {counts['updated']}\n"
        f"ℹ️ Skipped (Match): {counts['skipped_match']}\n"
        f"⚠️ Skipped (No IGN): {counts['skipped_no_ign']}\n"
        f"❌ Failed (Hierarchy): {counts['fail_hierarchy']}\n"
        f"❌ Failed (Perms): {counts['fail_perms']}\n"
        f"❌ Failed (Other): {counts['fail_other']}\n\n"
        f"Duration: {duration:.2f} seconds"
    )
    embed.description = summary

    try:
        await interaction.edit_original_response(content=None, embed=embed)
    except (discord.NotFound, discord.InteractionResponded):
        print(f"SyncNick ({guild.name}): Interaction expired before final summary.")
    except discord.HTTPException as http_final_e:
        print(f"SyncNick ({guild.name}): Failed to send final summary embed ({http_final_e.status})")

    log_embed = discord.Embed(title="Nickname Sync Finished", description=summary, color=NERDY_YELLOW).set_footer(text=f"Triggered by {interaction.user}")
    await log_info(guild, "", embed=log_embed)


# --- Wither Command ---
@tree.command(name="wither", description="Temporarily remove all roles from a user (except @everyone).")
@app_commands.describe(
    user="The user to wither.",
    time="Time in minutes (0.1 to 10, default 2)."
)
async def wither(interaction: discord.Interaction, user: discord.Member, time: app_commands.Range[float, 0.1, 10.0] = 2.0):
    guild = interaction.guild
    invoker = interaction.user
    bot_member = guild.me

    # --- Pre-checks ---
    async def fail_and_log(reason: str, public_msg: str, log_error_obj: Exception | None = None):
        """Logs internal reason, sends ephemeral message."""
        await log_error(guild, f"Wither Failure ({invoker.name} -> {user.name}): {reason}", error=log_error_obj, interaction=interaction)
        # Use followup if deferred, response otherwise. Check is_done() for safety.
        send_method = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        try:
            await send_method(embed=create_embed(public_msg, discord.Color.red()), ephemeral=True)
        except discord.InteractionResponded: # If somehow already responded differently
             try: await interaction.followup.send(embed=create_embed(public_msg, discord.Color.red()), ephemeral=True)
             except Exception: pass # Ignore followup error if already responded
        except Exception as send_e: print(f"Wither: Failed to send failure message: {send_e}")


    # 1. Permission Check
    if invoker.id not in ALLOWED_WITHER_IDS:
        await fail_and_log("Invoker lacks wither permission.", "❌ You lack the divine permission to cast Wither.")
        return

    # 2. Target Checks
    if user.id == invoker.id: await fail_and_log("Attempted self-wither.", "🤨 Why wither yourself?", None); return
    if user.id == SELF_PROTECTED_ID and invoker.id != SELF_PROTECTED_ID: await fail_and_log("Attempted to wither protected ID.", "😨 You dare attempt to wither the Creator?!"); return
    if user.id == BOT_ID: await fail_and_log("Attempted to wither the bot.", "😭 Master... you would wither *me*...?"); return
    if user.bot: await fail_and_log("Attempted to wither a bot.", "🤖 Wither has no effect on fellow bots."); return
    if user.id == guild.owner_id and invoker.id != guild.owner_id: await fail_and_log("Attempted to wither server owner.", "👑 Wither cannot be cast upon the server owner!"); return

    # 3. Time Validation (Handled by Range decorator now)
    time_seconds = int(time * 60)

    # 4. Hierarchy Checks
    if bot_member.top_role <= user.top_role: await fail_and_log(f"Bot role too low ({bot_member.top_role.name} vs {user.top_role.name}).", "❌ I cannot wither someone whose highest role is equal to or above mine!"); return
    if invoker.top_role <= user.top_role and invoker.id != guild.owner_id: await fail_and_log(f"Invoker role too low ({invoker.top_role.name} vs {user.top_role.name}).", "❌ You cannot wither someone whose highest role is equal to or above yours."); return

    # --- Execution ---
    await interaction.response.defer(thinking=True, ephemeral=False) # Public defer

    original_roles = [role for role in user.roles if role != guild.default_role]
    if not original_roles:
        await log_info(guild, f"Wither cancelled: User {user.mention} had no roles to remove.")
        await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} has no roles to remove.", discord.Color.orange()))
        return

    try:
        # Remove roles
        await user.edit(roles=[], reason=f"Withered by {invoker.name} for {time:.2f}m")
        role_names_str = ', '.join([f"`{r.name}`" for r in original_roles])
        if len(role_names_str) > 1000: role_names_str = role_names_str[:1000] + "..."

        embed = create_embed(
            title="🌪️ Wither Cast! 🌪️",
            description=f"{user.mention} has been withered by {invoker.mention} for **{time:.2f} minutes**!\n\nRoles removed: {role_names_str}",
            color=discord.Color.dark_purple()
        )
        await interaction.followup.send(embed=embed) # Public confirmation
        await log_info(guild, f"`{user.name}` ({user.id}) withered by `{invoker.name}` for {time:.2f}m. Roles removed: [{', '.join(str(r.id) for r in original_roles)}]")

        # --- Wait Period ---
        await asyncio.sleep(time_seconds)

        # --- Restore Roles ---
        member_after_wait = await guild.fetch_member(user.id) # Re-fetch member

        if bot_member.top_role <= member_after_wait.top_role:
             await log_error(guild, f"Wither Restore Fail: Bot role no longer high enough for {member_after_wait.name}.")
             await interaction.followup.send(embed=create_embed(f"⚠️ Failed to restore roles for {member_after_wait.mention} - hierarchy issue.", discord.Color.red()), ephemeral=True)
             return

        await member_after_wait.edit(roles=original_roles, reason=f"Wither duration ({time:.2f}m) ended.")
        await interaction.followup.send(embed=create_embed(f"✨ {member_after_wait.mention}'s roles have been restored!", color=NERDY_YELLOW)) # Public restore
        await log_info(guild, f"Restored roles for `{member_after_wait.name}` ({member_after_wait.id}) after wither.")

    except discord.NotFound: # Catch if user left during wait
         await log_info(guild, f"User `{user.name}` ({user.id}) could not be found for role restoration (likely left server).")
         # No followup needed if user left
    except discord.Forbidden as fe:
         # Check if error happened during removal or restore phase based on context
         phase = "restore" if interaction.response.is_done() else "remove"
         await fail_and_log(f"Forbidden error during role {phase}.", f"❌ Failed to {phase} roles due to permissions. Check hierarchy.", log_error_obj=fe)
    except discord.HTTPException as http_e:
        phase = "restore" if interaction.response.is_done() else "remove"
        await fail_and_log(f"HTTPException during role {phase}.", f"❌ Discord API error during role {phase}.", log_error_obj=http_e)
    except Exception as e:
        phase = "restore" if interaction.response.is_done() else "remove"
        await fail_and_log(f"Unexpected error during wither {phase}.", f"❌ An unexpected error occurred during wither {phase}.", log_error_obj=e)


# --- Nerd Help Command ---
@tree.command(name="nerdhelp", description="Show the list of available bot commands.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    embed = discord.Embed(title="🤓 Pingslave Bot Commands", description="Here are the commands you can use:", color=NERDY_YELLOW)

    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    list_channel_mention = list_channel.mention if list_channel else f"(Channel ID: {HC_MEMBER_LIST_CHANNEL_ID})"
    allowed_channel_mentions = [f"<#{cid}>" for cid in ALLOWED_CHANNEL_IDS if guild.get_channel(cid)]
    allowed_channels_str = ", ".join(allowed_channel_mentions) if allowed_channel_mentions else "configured channels"

    # Helper to add fields consistently
    def add_help_field(name: str, value: str, permissions: str = "Everyone", notes: str | None = None):
        field_value = f"{value}\n**Permissions:** `{permissions}`"
        if notes: field_value += f"\n**Note:** {notes}"
        embed.add_field(name=name, value=field_value, inline=False)

    # Group commands logically
    embed.add_field(name="\u200B", value="**--- User Verification ---**", inline=False)
    add_help_field("/verify `<user>`", "Assigns 'Verified', removes 'Unverified'.", "Manage Roles")
    add_help_field("/unverify `<user>`", "Assigns 'Unverified', removes 'Verified'.", "Manage Roles")
    add_help_field("/hcverify `<user>` `<IGN>`", "Verifies into HC: saves IGN, assigns roles, sets nickname.", "Manage Roles, Manage Nicknames", "Adds 'Verified' & 'HC'. Updates list.")
    add_help_field("/unhcverify `<user>`", "Removes HC role, resets nickname.", "Manage Roles, Manage Nicknames", "Updates list.")

    embed.add_field(name="\u200B", value="**--- [HC1] Guild List ---**", inline=False)
    add_help_field("/hcmembers", "Shows interactive HC member list (IGNs included).", "Everyone", f"Use in: {allowed_channels_str}.")
    add_help_field("/refresh", "Manually updates the static HC list.", "Manage Roles", f"Updates list in {list_channel_mention}.")

    embed.add_field(name="\u200B", value="**--- Utilities & Admin ---**", inline=False)
    add_help_field("/bulkupdate", "Opens a form to bulk update member IGNs.", "Manage Roles", "Format: `Name#Tag or ID ➔ IGN`. Updates list.")
    add_help_field("/syncnicknames", "Updates HC member nicks from stored IGNs.", "Manage Nicknames", "Sets nick to IGN (max 32 chars).")
    add_help_field("/wither `<user>` `[time]`", "Temporarily removes all roles.", "Special Permission", f"Default 2m, Max {MAX_WITHER_SECONDS/60:.0f}m. Needs allowlist.")
    add_help_field("/nerdhelp", "Shows this help menu.", "Everyone")

    embed.set_footer(text="Bot by TheNerd | Stay nerdy!")
    if bot.user and bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)

    await interaction.response.send_message(embed=embed, ephemeral=False) # Public help message

# --- Bot Startup ---
if __name__ == "__main__":
    print("--- Initializing Pingslave Bot ---")
    if not TOKEN:
        print("CRITICAL: DISCORD_BOT_TOKEN environment variable not set. Bot cannot start.")
    elif not supabase:
        # Supabase client failure logged earlier
        print("CRITICAL: Supabase client failed to initialize. Functionality will be limited. Bot will not run.")
        # Exit if Supabase is absolutely critical
        # exit(1)
    else:
        print("Discord token and Supabase client seem okay.")
        print("Starting Flask keep-alive thread...")
        keep_alive() # Start the Flask app in background thread

        try:
            print("Attempting to run Discord bot...")
            bot.run(TOKEN) # This is blocking
        except discord.LoginFailure:
            print("CRITICAL: Bot login failed. Token is invalid or missing.")
        except discord.PrivilegedIntentsRequired:
             print("CRITICAL: Privileged Intents (Server Members) are required but not enabled in the Discord Developer Portal.")
        except Exception as e:
            print(f"CRITICAL: Bot execution failed with an unexpected error: {e}")
            print(traceback.format_exc())

    print("--- Bot process finished ---")
