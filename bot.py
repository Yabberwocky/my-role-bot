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
from typing import Optional # Added for type hinting clarity

# --- CONTEXT FOR FUTURE LLMS ---
# (Please do not remove this comment block)
#
# Bot Name: TheNerd's Pingslave
# Owner: Vibhor / TheNerd / sweet_honey (Discord ID: 1230848174218940416)
# Target Server: Catercord (This bot is intended for use only in this specific server)
# Primary Purpose: Manage verification and information related to the "[HC1]" guild within the game Florr.io.
#   - "[HC1]" is a guild in Florr.io, originally named "HC". Members can be HC or non-HC.
#   - The bot verifies members, stores their in-game names (IGNs) in Supabase,
#     maintains a static public list of HC members in a dedicated channel (using username ➔ IGN format),
#     provides an interactive paginated list via /hcmembers (using username ➔ IGN format),
#     and offers utility commands. /bulkupdate expects username ➔ IGN format.
# Hosting Environment:
#   - Code Files: `bot.py` (this file), `requirements.txt` (listing discord, supabase, flask)
#   - Platform: Render (Free Tier) via a private GitHub repository.
#   - Keep-Alive: Uses a basic Flask web server (`keep_alive` function) monitored by an external
#     service (like Uptime Robot) hitting the Flask endpoint to prevent Render's free instance from sleeping.
#   - Environment Variables: DISCORD_BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY are set directly in Render's environment settings.
# Database: Supabase (PostgreSQL) used to store HC member IGNs linked to Discord IDs.
# Key Features: /verify, /hcverify (stores IGN), static list updates, /hcmembers (interactive list), /syncnicknames, /wither, /bulkupdate.
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
BOT_ID = 1365572437185400893 # Bot's own User ID (Retrieved dynamically later)
MAX_WITHER_SECONDS = 600 # Max duration for /wither in seconds (10 minutes)
INFO_LOG_CHANNEL_ID = 1317943895606165579 # Channel for general info logs
ERROR_LOG_CHANNEL_ID = 1362988767367135453 # Channel for error logs
MEMBERS_PER_PAGE = 50 # Members per page in lists
NERDY_YELLOW = discord.Color.gold() # Embed color

# --- Supabase Client ---
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase client created successfully.")
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
BOT_ID = bot.user.id if bot.user else None # Get Bot ID once ready

# --- Flask App (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Pingslave bot is alive!"

def run_flask():
    try:
        port = int(os.environ.get('PORT', 8080))
        print(f"Attempting to start Flask server on host 0.0.0.0 port {port}")
        app.run(host='0.0.0.0', port=port)
        print("Flask server finished.") # Should only print if server stops gracefully/crashes
    except OSError as e:
         print(f"Flask server failed to start (OSError): {e}. Port {port} might be in use.")
    except Exception as e:
        print(f"Flask server failed to start (General Exception): {e}")
        print(traceback.format_exc())

def keep_alive():
    """Starts the Flask server in a background daemon thread."""
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("Keep alive thread initiated.")

# --- Utility Functions ---
async def run_supabase_sync(func):
    """Runs a synchronous Supabase function in an executor."""
    if not supabase:
        print("Attempted Supabase operation, but client is not initialized.")
        raise ConnectionError("Supabase client is not available.")
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func)
    except APIError as api_err:
        print(f"Supabase API Error: {api_err}")
        raise
    except Exception as e:
        print(f"Error running Supabase function in executor: {e}")
        raise

# --- Logging ---
async def log_to_channel(channel_id: int, guild: Optional[discord.Guild], message: Optional[str] = None, embed: Optional[discord.Embed] = None):
    """Sends a log message or embed to a specified channel, checking permissions."""
    if not guild:
        print(f"Log Error: Cannot log to channel {channel_id}, Guild context is missing. Content: {message or 'Embed'}")
        return

    log_channel = guild.get_channel(channel_id)
    if not isinstance(log_channel, discord.TextChannel):
        print(f"Log Error: Channel ID {channel_id} not found or is not a text channel in guild {guild.name}.")
        return

    bot_member = guild.me
    if not bot_member:
        print(f"Log Error: Could not find bot member in guild {guild.name} for permission check.")
        return # Cannot check permissions if bot member object isn't found

    perms = log_channel.permissions_for(bot_member)
    can_send = perms.send_messages
    can_embed = perms.embed_links

    if not can_send or (embed and not can_embed):
        missing = []
        if not can_send: missing.append("Send Messages")
        if embed and not can_embed: missing.append("Embed Links")
        print(f"Log Error: Missing permissions ({', '.join(missing)}) in log channel {log_channel.mention} ({guild.name}).")
        return

    try:
        if embed:
            await log_channel.send(embed=embed)
        elif message:
            safe_message = (message[:1997] + "...") if len(message) > 2000 else message
            await log_channel.send(safe_message)
    except discord.Forbidden:
        print(f"Log Error: Forbidden to send message in log channel {log_channel.mention} ({guild.name}) (permissions changed?).")
    except discord.HTTPException as http_err:
        print(f"Log Error: Discord HTTP error sending to {log_channel.mention} ({guild.name}): {http_err.status} {http_err.code} - {http_err.text}")
    except Exception as e:
        print(f"Log Error: Unexpected error sending to log channel {log_channel.mention} ({guild.name}): {e}")

async def log_info(guild: Optional[discord.Guild], message: str, embed: Optional[discord.Embed] = None):
    """Logs an informational message with a timestamp."""
    if not embed:
        embed = discord.Embed(description=message, color=NERDY_YELLOW)
        embed.timestamp = discord.utils.utcnow()
    await log_to_channel(INFO_LOG_CHANNEL_ID, guild, embed=embed)

async def log_error(guild: Optional[discord.Guild], message: str, error: Optional[Exception] = None, interaction: Optional[discord.Interaction] = None, embed: Optional[discord.Embed] = None):
    """Logs an error message, optionally including exception details and interaction context."""
    if not embed:
        embed = discord.Embed(title="⚠️ Bot Error / Warning", description=message, color=discord.Color.red())
        embed.timestamp = discord.utils.utcnow()

        if interaction:
            cmd_name = interaction.command.name if interaction.command else 'Unknown Command'
            channel_info = f" in {interaction.channel.mention}" if isinstance(interaction.channel, discord.TextChannel) else f" in channel ID `{interaction.channel_id}`" if interaction.channel else ""
            user_info = f"{interaction.user.mention} (`{interaction.user.id}`)"
            context = f"Command: `/{cmd_name}`{channel_info}\nUser: {user_info}"
            embed.add_field(name="Context", value=context, inline=False)

        if error:
            err_type = type(error).__name__
            err_msg = str(error)
            tb_list = traceback.format_exception(type(error), error, error.__traceback__, limit=6) # Slightly more traceback
            tb_str = "".join(tb_list)
            if len(tb_str) > 950: tb_str = tb_str[:950] + "\n... (Traceback truncated)" # Adjust limit for field constraints

            err_details = f"**Type:** `{err_type}`\n"
            if err_msg: err_details += f"**Message:** `{err_msg}`\n"
            err_details += f"**Traceback:**\n```py\n{tb_str}\n```"

            # Ensure the field value fits within Discord's limit
            if len(err_details) > 1024:
                 err_details = err_details[:1021] + "..."
            embed.add_field(name="Error Details", value=err_details, inline=False)

            # Print full traceback to console regardless of embed truncation
            full_tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            print(f"--- ERROR LOGGED ---\nGuild: {guild.id if guild else 'N/A'}\nContext Msg: {message}\nError: {err_type}: {err_msg}\nTraceback:\n{full_tb}\n--- END ERROR ---")

    await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, embed=embed)

# --- Embed Pagination View ---
class HCPagesView(View):
    """A view for paginating through the HC member list using `username ➔ IGN` format."""
    def __init__(self, data: list[tuple[Optional[discord.Member], str]], total_members: int, timeout=300.0):
        super().__init__(timeout=timeout)
        self.data = data
        self.total_members = total_members
        self.current_page = 0
        self.total_pages = math.ceil(len(self.data) / MEMBERS_PER_PAGE) if self.data else 1
        self.message: Optional[discord.Message] = None

        self.update_buttons()

    def create_page_embed(self) -> discord.Embed:
        """Creates the embed for the current page using `username ➔ IGN` format."""
        start_index = self.current_page * MEMBERS_PER_PAGE
        end_index = start_index + MEMBERS_PER_PAGE
        page_data = self.data[start_index:end_index]

        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, color=NERDY_YELLOW)
        desc_lines = []
        current_item_index = start_index + 1

        for member, ingame_name in page_data:
            if member:
                # --- FORMAT CHANGE HERE: Use member.name instead of member.display_name ---
                safe_user = discord.utils.escape_markdown(member.name) # Includes #discriminator
                safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
                # desc_lines.append(f"{current_item_index}. {safe_user} (`{member.display_name}`) ➔ {safe_ign}") # Old format
                desc_lines.append(f"{current_item_index}. {safe_user} ➔ {safe_ign}")
            else:
                safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
                desc_lines.append(f"{current_item_index}. *User Left Server?* ➔ {safe_ign}")
            current_item_index += 1

        embed.description = "\n".join(desc_lines) if desc_lines else "No members found on this page."
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} | Total HC Members: {self.total_members}")
        embed.timestamp = discord.utils.utcnow()
        return embed

    def update_buttons(self):
        """Disables/Enables previous/next buttons based on current page."""
        if hasattr(self, 'children') and len(self.children) >= 2:
            prev_button, next_button = self.children[0], self.children[1]
            if isinstance(prev_button, Button): prev_button.disabled = self.current_page == 0
            if isinstance(next_button, Button): next_button.disabled = self.current_page >= self.total_pages - 1
        else: print("Warning: Could not find buttons in HCPagesView children.")

    async def edit_message(self, interaction: discord.Interaction):
        """Helper to edit the message with the current state."""
        embed = self.create_page_embed()
        self.update_buttons()
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.NotFound: await log_error(interaction.guild, "Paginated message edit failed (NotFound).", interaction=interaction)
        except discord.HTTPException as e: await log_error(interaction.guild, f"Paginated message edit failed (HTTP {e.status}).", error=e, interaction=interaction)
        except Exception as e: await log_error(interaction.guild, f"Paginated message edit failed (Unexpected).", error=e, interaction=interaction)

    @button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="hc_prev_interactive", row=0)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.edit_message(interaction)
        else:
            try: await interaction.response.defer()
            except discord.InteractionResponded: pass

    @button(label="Next", style=discord.ButtonStyle.blurple, custom_id="hc_next_interactive", row=0)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.edit_message(interaction)
        else:
            try: await interaction.response.defer()
            except discord.InteractionResponded: pass

    async def on_timeout(self):
        """Disables buttons when the view times out."""
        if self.message:
            try:
                for item in self.children:
                    if isinstance(item, Button): item.disabled = True
                await self.message.edit(view=self)
                print(f"Pagination View: Buttons disabled on timeout (Message ID: {self.message.id}).")
            except (discord.NotFound, discord.HTTPException, AttributeError) as e: print(f"Pagination View: Failed to disable buttons on timeout (Message ID: {self.message.id if self.message else 'Unknown'}): {e}")
            except Exception as e: print(f"Pagination View: Unexpected error disabling buttons on timeout: {e}")
        else: print("Pagination View: Timeout occurred but no message associated.")

# --- Core HC List Logic ---
async def fetch_hc_member_data(guild: discord.Guild) -> tuple[list[tuple[Optional[discord.Member], str]], int]:
    """Fetches HC role members and their IGNs from Supabase."""
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"HC Role (ID: {ADD_ROLE_ID_HC}) not found in fetch_hc_member_data.")
        return [], 0

    members_with_role = [m for m in guild.members if hc_role in m.roles and not m.bot]
    total_count = len(members_with_role)

    # --- SORTING CHANGE: Sort by username (case-insensitive) ---
    members_sorted = sorted(members_with_role, key=lambda m: m.name.lower())
    member_ids = [str(m.id) for m in members_sorted]
    ign_map = {}

    if supabase and member_ids:
        try:
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
                    ign_map.update({r['discord_id']: r.get("ingame_name") or "Unknown" for r in resp.data})
                await asyncio.sleep(0.1)
        except ConnectionError:
             await log_error(guild, "Supabase connection error during IGN fetch.")
             ign_map = {mid: "DB Error" for mid in member_ids}
        except Exception as e:
             await log_error(guild, "Failed bulk IGN fetch.", error=e)
             ign_map = {mid: "Fetch Error" for mid in member_ids}

    member_tuples = [(m, ign_map.get(str(m.id), "Unknown")) for m in members_sorted]
    return member_tuples, total_count

def generate_hc_list_embeds(data: list[tuple[Optional[discord.Member], str]], total_members: int) -> list[discord.Embed]:
    """Generates embeds for the static list using `username ➔ IGN` format."""
    embeds = []
    if not data:
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, description="No HC members found or could not retrieve details.", color=discord.Color.orange())
        embed.set_footer(text="Page 1/1 | Total HC Members: 0")
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
                # --- FORMAT CHANGE HERE: Use member.name ---
                safe_user = discord.utils.escape_markdown(member.name) # username#tag
                safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
                desc_lines.append(f"{current_item_index}. {safe_user} ➔ {safe_ign}")
            else:
                safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
                desc_lines.append(f"{current_item_index}. *User Left Server?* ➔ {safe_ign}")
            current_item_index += 1

        embed.description = "\n".join(desc_lines) if desc_lines else "No members on this page."
        embed.set_footer(text=f"Page {page_num + 1}/{total_pages} | Total HC Members: {total_members}")
        embed.timestamp = discord.utils.utcnow()
        embeds.append(embed)

    return embeds

async def update_hc_member_list(guild: discord.Guild):
    """Fetches HC members, generates embeds (`username ➔ IGN`), and updates the static list channel."""
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(list_channel, discord.TextChannel):
        await log_error(guild, f"Static list channel (ID: {HC_MEMBER_LIST_CHANNEL_ID}) not found or invalid.")
        return

    bot_member = guild.me
    if not bot_member:
        await log_error(guild, "Could not find bot member in guild for static list update.")
        return

    # Check permissions
    perms = list_channel.permissions_for(bot_member)
    required = {"send_messages": perms.send_messages, "embed_links": perms.embed_links, "read_message_history": perms.read_message_history, "manage_messages": perms.manage_messages}
    missing = [name for name, has in required.items() if not has]
    if missing:
        await log_error(guild, f"Bot lacks permissions in static list channel {list_channel.mention}: {', '.join(missing)}")
        return

    try:
        await log_info(guild, f"Starting static HC list update in {list_channel.mention}...")
        # Data fetch uses username sorting now
        member_data, total_count = await fetch_hc_member_data(guild)
        # Embed generation uses username format now
        new_embeds = generate_hc_list_embeds(member_data, total_count)
        num_new_pages = len(new_embeds)

        # Find existing messages
        existing_messages: list[discord.Message] = []
        try:
            async for message in list_channel.history(limit=25): # Increased limit slightly
                # Check author ID and embed title
                if message.author.id == bot.user.id and message.embeds and message.embeds[0].title == HC_LIST_EMBED_TITLE:
                    existing_messages.append(message)
            existing_messages.sort(key=lambda m: m.created_at) # Oldest first
        except discord.Forbidden: await log_error(guild, f"Cannot read history in {list_channel.mention}."); return
        except Exception as e: await log_error(guild, f"Error searching history in {list_channel.mention}.", error=e); return

        num_existing = len(existing_messages)
        print(f"Static List Update ({guild.name}): Found {num_existing} existing msg(s), need {num_new_pages} page(s).")

        # --- Edit/Send Loop ---
        edited_or_sent_message_ids = set()
        max_pages = max(num_new_pages, num_existing)
        for i in range(max_pages):
            if i < num_new_pages and i < num_existing: # Edit existing
                msg_to_edit = existing_messages[i]
                embed_to_use = new_embeds[i]
                try:
                    await msg_to_edit.edit(embed=embed_to_use)
                    edited_or_sent_message_ids.add(msg_to_edit.id)
                    print(f"  Edited message {msg_to_edit.id} (Page {i+1})")
                    await asyncio.sleep(1.2)
                except discord.NotFound: print(f"  Existing message {msg_to_edit.id} not found (Page {i+1}), skipping edit.")
                except discord.Forbidden: await log_error(guild, f"Failed to edit static list msg {i+1} (ID: {msg_to_edit.id}) - Forbidden."); break
                except Exception as e: await log_error(guild, f"Failed to edit static list msg {i+1} (ID: {msg_to_edit.id}).", error=e); edited_or_sent_message_ids.add(msg_to_edit.id)

            elif i < num_new_pages: # Send new page
                embed_to_use = new_embeds[i]
                try:
                    new_msg = await list_channel.send(embed=embed_to_use)
                    edited_or_sent_message_ids.add(new_msg.id)
                    print(f"  Sent new message {new_msg.id} (Page {i+1})")
                    await asyncio.sleep(1.2)
                except discord.Forbidden: await log_error(guild, f"Failed to send static list page {i+1} - Forbidden."); break
                except Exception as e: await log_error(guild, f"Failed to send static list page {i+1}.", error=e)

            elif i >= num_new_pages and i < num_existing: # Delete surplus existing page
                 msg_to_delete = existing_messages[i]
                 if msg_to_delete.id not in edited_or_sent_message_ids: # Avoid deleting if we failed to edit but still kept track
                     try:
                         print(f"  Deleting surplus message {msg_to_delete.id} (Old Page {i+1})")
                         await msg_to_delete.delete()
                         await asyncio.sleep(1.2)
                     except discord.Forbidden: await log_error(guild, f"Failed to delete surplus msg (ID: {msg_to_delete.id}) - Forbidden."); break
                     except discord.NotFound: print(f"    Tried to delete surplus msg {msg_to_delete.id}, but already gone.")
                     except Exception as e: await log_error(guild, f"Failed to delete surplus msg (ID: {msg_to_delete.id}).", error=e)

        # --- Final Cleanup (in case loop broke or logic missed something) ---
        # Refetch history to find messages *really* left over
        final_check_messages = []
        deleted_in_cleanup = 0
        try:
             async for message in list_channel.history(limit=num_new_pages + 10): # Check a bit more than needed
                if message.author.id == bot.user.id and message.embeds and message.embeds[0].title == HC_LIST_EMBED_TITLE:
                     if message.id not in edited_or_sent_message_ids: # Check if it was one we meant to keep
                         try:
                              print(f"  Cleanup: Deleting unexpected/old message {message.id}")
                              await message.delete()
                              deleted_in_cleanup += 1
                              await asyncio.sleep(1.2)
                         except Exception as e:
                              print(f"  Cleanup: Error deleting message {message.id}: {e}")
             if deleted_in_cleanup > 0:
                  await log_info(guild, f"Static List Cleanup: Deleted {deleted_in_cleanup} extra message(s).")
        except Exception as e:
             print(f"Static List Cleanup: Error during final check: {e}")


        await log_info(guild, f"Static HC list update complete in {list_channel.mention} ({num_new_pages} pages expected).")

    except Exception as e:
        await log_error(guild, f"Overall static list update error in {list_channel.mention}.", error=e)
        print(f"CRITICAL ERROR during update_hc_member_list ({guild.name}): {e}\n{traceback.format_exc()}")


# --- Discord Events ---
@bot.event
async def on_ready():
    global BOT_ID # Update global BOT_ID
    BOT_ID = bot.user.id
    print(f"Logged in as {bot.user} (ID: {BOT_ID})")
    print(f"Discord.py version: {discord.__version__}")
    synced_count = 0
    try:
        print("Attempting to sync application commands...")
        synced = await tree.sync()
        synced_count = len(synced)
        print(f"Successfully synced {synced_count} application commands.")
    except Exception as e:
        print(f"Command Sync failed: {e}")
        primary_guild = bot.guilds[0] if bot.guilds else None
        if primary_guild: await log_error(primary_guild, "Command Sync failed.", error=e)

    # Initial setup for guilds
    if not bot.guilds: print("Bot is not currently in any guilds."); return
    print(f"Running initial setup for {len(bot.guilds)} guild(s)...")
    guilds_to_process = list(bot.guilds)
    for guild in guilds_to_process:
        print(f"  Processing guild: {guild.name} ({guild.id})")
        try:
            await log_info(guild, f"Bot ready and online. Synced {synced_count} commands.")
            print(f"    Initiating HC member list update for {guild.name}...")
            await update_hc_member_list(guild)
            print(f"    HC member list update initiated for {guild.name}.")
            await asyncio.sleep(1)
        except Exception as guild_e:
            log_msg = f"Error during on_ready setup for guild {guild.name} ({guild.id})."
            print(f"ERROR: {log_msg} - {guild_e}")
            try: await log_error(guild, log_msg, error=guild_e)
            except Exception as log_err_e: print(f"CRITICAL: Failed to log guild setup error for {guild.name}: {log_err_e}")
    print("Initial guild setup complete.")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    """Triggers static list update if HC role is added/removed."""
    # Ignore updates to bots or if roles haven't changed
    if after.bot or before.roles == after.roles: return

    guild = after.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role: return # Role doesn't exist here

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
    """Global handler for slash command errors."""
    guild = interaction.guild
    user_message = "❌ An unexpected error occurred."
    log_description = "Unhandled application command error."
    error_to_log = error

    # Specific error handling logic... (same as previous version, omitted for brevity but included in final code block)
    if isinstance(error, app_commands.CommandNotFound): return
    elif isinstance(error, app_commands.MissingPermissions): perms = ", ".join(f"`{p}`" for p in error.missing_permissions); user_message=f"❌ You lack permissions: {perms}"; log_description=f"User {interaction.user.mention} lacked perms ({perms})"; error_to_log=None
    elif isinstance(error, app_commands.BotMissingPermissions): perms = ", ".join(f"`{p}`" for p in error.missing_permissions); user_message=f"❌ I lack permissions: {perms}"; log_description=f"Bot missing perms ({perms})"; error_to_log=None
    elif isinstance(error, app_commands.CheckFailure): user_message="❌ Requirements not met."; log_description=f"User {interaction.user.mention} failed checks ({type(error).__name__})"; error_to_log=None
    elif isinstance(error, app_commands.CommandInvokeError): original=error.original; user_message=f"❌ Command error: `{type(original).__name__}`"; log_description=f"Error invoking `/{interaction.command.name if interaction.command else 'N/A'}`"; error_to_log=original; print(f"CmdInvokeErr: /{interaction.command.name if interaction.command else 'N/A'} by {interaction.user}: {original}")
    elif isinstance(error, app_commands.TransformerError): user_message=f"❌ Invalid input: {error}"; log_description=f"TransformerError for `/{interaction.command.name if interaction.command else 'N/A'}`"; error_to_log=error
    elif isinstance(error, app_commands.CommandOnCooldown): user_message=f"⏳ Cooldown: Try again in {error.retry_after:.1f}s."; log_description=f"User {interaction.user.mention} hit cooldown"; error_to_log=None
    else: user_message="❌ Unknown command error."; log_description=f"Unknown AppCommandError: `{type(error).__name__}`"; print(f"UnknownAppErr: {type(error).__name__} - {error}")


    # Log the error
    await log_error(guild, log_description, error=error_to_log, interaction=interaction)

    # Respond ephemerally
    try:
        send_method = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send_method(user_message, ephemeral=True)
    except discord.InteractionResponded: # If it somehow got responded to between check and send
        try: await interaction.followup.send(user_message, ephemeral=True)
        except Exception: pass # Give up trying to respond
    except (discord.NotFound, discord.HTTPException): pass # Ignore errors sending if interaction is gone
    except Exception as send_e: print(f"Failed to send error followup message: {send_e}")

# --- Modals ---
def create_embed(description: str, color: discord.Color = NERDY_YELLOW, title: Optional[str] = None) -> discord.Embed:
     """Helper to create simple embeds."""
     return discord.Embed(title=title, description=description, color=color)

class BulkUpdateModal(Modal, title="Bulk Update IGNs"):
    """Modal for bulk updating IGNs using `username#tag ➔ IGN` format."""
    # --- FORMAT CHANGE HERE: Updated Label and Placeholder ---
    data = TextInput(
        label="Paste list (username#tag ➔ IGN)",
        style=discord.TextStyle.paragraph,
        placeholder="ExampleUser#1234 ➔ CoolFlorrName\nAnotherUser#5678 ➔ AnotherIGN\n(One entry per line)",
        required=True,
        min_length=5,
        max_length=4000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.guild
        if not guild: return

        if not supabase:
            await interaction.followup.send(embed=create_embed("❌ Supabase client unavailable.", discord.Color.red()), ephemeral=True)
            return

        lines = self.data.value.strip().splitlines()
        if not lines:
            await interaction.followup.send(embed=create_embed("⚠️ No data provided.", discord.Color.orange()), ephemeral=True)
            return

        # Pre-fetch members
        try:
            if not guild.chunked: await guild.chunk()
            # --- LOOKUP CHANGE: Prioritize username#tag map ---
            members_map_name = {m.name.lower(): m for m in guild.members if not m.bot} # username#tag lowercase
            members_map_id = {str(m.id): m for m in guild.members if not m.bot}
            members_map_display = {m.display_name.lower(): m for m in guild.members if not m.bot} # Fallback
        except Exception as e:
            await log_error(guild, "Bulk Update Modal: Failed to fetch/map members.", error=e, interaction=interaction)
            await interaction.followup.send(embed=create_embed("❌ Error preparing member list.", discord.Color.red()), ephemeral=True)
            return

        success_count, fail_count, not_found_count = 0, 0, 0
        results_log = []
        upsert_payload = []

        for idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line: continue

            if "➔" not in line:
                fail_count += 1; results_log.append(('f', f"L{idx}: Format Error (Missing '➔')")); continue
            try:
                discord_identifier, ingame_name = map(str.strip, line.split("➔", 1))
                if not discord_identifier or not ingame_name:
                    fail_count += 1; results_log.append(('f', f"L{idx}: Missing username/ID or IGN")); continue
            except ValueError:
                fail_count += 1; results_log.append(('f', f"L{idx}: Format Error (Splitting '➔')")); continue

            # Find member: Prioritize username#tag, then ID, then display name as fallback
            member: Optional[discord.Member] = None
            identifier_lower = discord_identifier.lower()

            if identifier_lower in members_map_name:
                member = members_map_name[identifier_lower]
            elif discord_identifier.isdigit() and discord_identifier in members_map_id:
                 member = members_map_id[discord_identifier]
            elif identifier_lower in members_map_display: # Fallback
                member = members_map_display[identifier_lower]

            if not member:
                fail_count += 1; not_found_count += 1; results_log.append(('f', f"L{idx}: User `{discord.utils.escape_markdown(discord_identifier)}` not found.")); continue

            # Prepare valid entry for upsert
            upsert_payload.append({ "discord_id": str(member.id), "discord_name": member.name, "ingame_name": ingame_name })

        # Perform Bulk Upsert
        db_errors_occured = False
        if upsert_payload:
            try:
                print(f"Bulk Update ({guild.name}): Upserting {len(upsert_payload)} records.")
                await run_supabase_sync(lambda: supabase.table("hc_members").upsert(upsert_payload, on_conflict="discord_id").execute())
                success_count = len(upsert_payload)
            except Exception as e:
                db_errors_occured = True
                fail_count += len(upsert_payload)
                err_type = "Connection Error" if isinstance(e, ConnectionError) else type(e).__name__
                results_log.append(('f', f"DB: {err_type} during bulk upsert."))
                await log_error(guild, f"Bulk DB {err_type}", error=e, interaction=interaction)
        else: print(f"Bulk Update ({guild.name}): No valid entries found.")

        # Prepare Results Embed
        embed_color = NERDY_YELLOW if not fail_count else discord.Color.orange()
        embed = discord.Embed(title="Bulk Update Results", color=embed_color)
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

        # Log summary & update static list if needed
        log_color = NERDY_YELLOW if not fail_count else discord.Color.orange()
        log_embed = discord.Embed(description=f"Bulk IGN update finished for `{interaction.user}`. Success: {success_count}, Fail: {fail_count}.", color=log_color)
        await log_info(guild, "", embed=log_embed)
        if success_count > 0: await update_hc_member_list(guild)


# --- Slash Commands ---
# Verify, Unverify, HCVerify, UnHCVerify, HCMembers, Refresh, SyncNicknames, Wither, NerdHelp
# (These commands remain largely the same as the previous version, focusing on internal logic,
# error handling, and permissions. The output format changes for HCMembers and Refresh are handled
# by the updated HCPagesView and generate_hc_list_embeds functions called by them.)
# Omitting the full code for these commands here for brevity, but they are included below.

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

    if not unverified_role: missing_setup_roles.append(f"'Unverified' (ID: {REMOVE_ROLE_ID})")
    if not verified_role: missing_setup_roles.append(f"'Verified' (ID: {ADD_ROLE_ID_VERIFY})")
    if missing_setup_roles:
        errmsg = f"Bot setup error: Cannot find role(s): {', '.join(missing_setup_roles)}."
        await log_error(guild, f"/verify setup error: {errmsg}", interaction=interaction)
        await interaction.response.send_message(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
        return

    if guild.me.top_role <= user.top_role and user.id != guild.owner_id:
         errmsg = f"I cannot manage roles for {user.mention} due to hierarchy."
         await interaction.response.send_message(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
         return

    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
        modified = False; reason = f"Verified by {interaction.user}"
        if unverified_role and unverified_role in user.roles: await user.remove_roles(unverified_role, reason=reason); actions_performed.append(f"➖ `{unverified_role.name}`"); modified = True
        if verified_role and verified_role not in user.roles: await user.add_roles(verified_role, reason=reason); actions_performed.append(f"➕ `{verified_role.name}`"); modified = True

        if not modified:
            await interaction.followup.send(embed=create_embed(f"ℹ️ No role changes for {user.display_name}.", discord.Color.orange()), ephemeral=True)
        else:
            log_msg = f"`{interaction.user}` verified {user.mention}. Actions: {' '.join(actions_performed)}."
            await log_info(guild, log_msg)
            pub_embed = create_embed(f"✅ **{user.display_name}** verified!\n" + "\n".join(actions_performed), discord.Color.green())
            await interaction.followup.send(embed=create_embed("✅ Verification successful!", discord.Color.green()), ephemeral=True)
            try: await interaction.channel.send(embed=pub_embed) # Public confirmation
            except Exception as e: await log_error(guild, "Failed public verify confirm", error=e)

    except discord.Forbidden: await interaction.followup.send(embed=create_embed(f"❌ Permission error managing roles for {user.mention}.", discord.Color.red()), ephemeral=True)
    except Exception as e:
        await log_error(guild, f"/verify error processing {user.display_name}", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Unexpected verify error.", discord.Color.red()), ephemeral=True)

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

    if not verified_role: missing_setup_roles.append(f"'Verified' ({ADD_ROLE_ID_VERIFY})")
    if not unverified_role: missing_setup_roles.append(f"'Unverified' ({REMOVE_ROLE_ID})")
    if missing_setup_roles:
        errmsg = f"Bot setup error: Cannot find role(s): {', '.join(missing_setup_roles)}."
        await interaction.response.send_message(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
        return

    if guild.me.top_role <= user.top_role and user.id != guild.owner_id:
         errmsg = f"I cannot manage roles for {user.mention} due to hierarchy."
         await interaction.response.send_message(embed=create_embed(f"❌ {errmsg}", discord.Color.red()), ephemeral=True)
         return

    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
        modified = False; reason = f"Unverified by {interaction.user}"
        if verified_role and verified_role in user.roles: await user.remove_roles(verified_role, reason=reason); actions_performed.append(f"➖ `{verified_role.name}`"); modified = True
        if unverified_role and unverified_role not in user.roles: await user.add_roles(unverified_role, reason=reason); actions_performed.append(f"➕ `{unverified_role.name}`"); modified = True

        if not modified:
            await interaction.followup.send(embed=create_embed(f"ℹ️ No role changes for {user.display_name}.", discord.Color.orange()), ephemeral=True)
        else:
            log_msg = f"`{interaction.user}` unverified {user.mention}. Actions: {' '.join(actions_performed)}."
            await log_info(guild, log_msg)
            pub_embed = create_embed(f"✅ **{user.display_name}** unverified!\n" + "\n".join(actions_performed), discord.Color.green())
            await interaction.followup.send(embed=create_embed("✅ Un-verification successful!", discord.Color.green()), ephemeral=True)
            try: await interaction.channel.send(embed=pub_embed)
            except Exception as e: await log_error(guild, "Failed public unverify confirm", error=e)

    except discord.Forbidden: await interaction.followup.send(embed=create_embed(f"❌ Permission error managing roles for {user.mention}.", discord.Color.red()), ephemeral=True)
    except Exception as e:
        await log_error(guild, f"/unverify error processing {user.display_name}", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Unexpected unverify error.", discord.Color.red()), ephemeral=True)


# --- HC Verify Command ---
@tree.command(name="hcverify", description="Verify user into HC, store IGN, set nickname.")
@app_commands.describe(user="The user to HC verify.", ingame_name="The user's Florr.io In-Game Name.")
@app_commands.checks.has_permissions(manage_roles=True, manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    await interaction.response.defer(thinking=True, ephemeral=False) # Public defer
    guild = interaction.guild

    if not supabase: await interaction.followup.send(embed=create_embed("❌ DB unavailable.", discord.Color.red()), ephemeral=True); return

    unverified_role, verified_role, hc_role = guild.get_role(REMOVE_ROLE_ID), guild.get_role(ADD_ROLE_ID_VERIFY), guild.get_role(ADD_ROLE_ID_HC)
    log_actions, response_lines, missing_roles = [], [], []
    if not unverified_role: missing_roles.append(f"'Unverified' ({REMOVE_ROLE_ID})")
    if not verified_role: missing_roles.append(f"'Verified' ({ADD_ROLE_ID_VERIFY})")
    if not hc_role: missing_roles.append(f"'HC' ({ADD_ROLE_ID_HC})")
    if missing_roles: await interaction.followup.send(embed=create_embed(f"❌ Setup error: Missing roles: {', '.join(missing_roles)}.", discord.Color.red()), ephemeral=True); return
    if guild.me.top_role <= user.top_role and user.id != guild.owner_id: await interaction.followup.send(embed=create_embed(f"❌ Cannot manage {user.mention} due to hierarchy.", discord.Color.red()), ephemeral=True); return

    try:
        original_had_hc_role = hc_role in user.roles; roles_to_add = []; roles_modified = False; reason = f"HC Verified by {interaction.user}"

        # 1. Roles
        if unverified_role and unverified_role in user.roles: await user.remove_roles(unverified_role, reason=reason); log_actions.append(f"Rm Unverified"); roles_modified = True
        if verified_role and verified_role not in user.roles: roles_to_add.append(verified_role)
        if hc_role and hc_role not in user.roles: roles_to_add.append(hc_role)
        if roles_to_add: await user.add_roles(*roles_to_add, reason=reason); added_names = ', '.join([f"`{r.name}`" for r in roles_to_add]); log_actions.append(f"Add: {added_names}"); response_lines.append(f"➕ Roles: {added_names}"); roles_modified = True
        elif not roles_modified: response_lines.append("ℹ️ Roles OK.")

        # 2. Database
        db_ok = False
        try: await run_supabase_sync(lambda: supabase.table("hc_members").upsert({"discord_id": str(user.id), "discord_name": user.name, "ingame_name": ingame_name}, on_conflict="discord_id").execute()); log_actions.append(f"Upsert IGN"); response_lines.append(f"💾 IGN: `{discord.utils.escape_markdown(ingame_name)}`"); db_ok = True
        except Exception as e: log_actions.append("DB FAILED"); response_lines.append("⚠️ DB Failed!"); await log_error(guild, f"DB upsert fail {user.display_name}", error=e, interaction=interaction)

        # 3. Nickname
        nick_change_status = "No change"; nickname_truncated = False; target_nick = ingame_name[:32]
        if len(ingame_name) > 32: nickname_truncated = True
        if user.nick != target_nick:
            try: await user.edit(nick=target_nick, reason=reason); nick_msg = f"🏷️ Nick: `{discord.utils.escape_markdown(target_nick)}`" + (" (trunc)" if nickname_truncated else ""); log_actions.append(f"Set Nick"); response_lines.append(nick_msg); nick_change_status = "Success"
            except discord.Forbidden: log_actions.append("Nick FAIL (Perms)"); response_lines.append("⚠️ Nick Fail (Perms)"); nick_change_status = "Perms Fail"
            except Exception as e: log_actions.append(f"Nick FAIL ({type(e).__name__})"); response_lines.append("⚠️ Nick Fail (Error)"); nick_change_status = "Error"; await log_error(guild, f"Nick fail {user.display_name}", error=e, interaction=interaction)
        else: log_actions.append("Nick OK"); response_lines.append("🏷️ Nick OK.")

        # 4. Log & Respond
        await log_info(guild, f"`{interaction.user}` HC verified `{user.display_name}`. {'; '.join(log_actions)}.")
        is_error = not db_ok or nick_change_status in ["Perms Fail", "Error"]
        title_suffix = " (with issues)" if is_error else ""
        embed_color = discord.Color.orange() if is_error else discord.Color.green()
        final_embed = create_embed(title=f"✅ HC Verified: {user.display_name}{title_suffix}", description="\n".join(response_lines), color=embed_color)
        await interaction.followup.send(embed=final_embed)

        # 5. Update List
        if (hc_role in roles_to_add) or (original_had_hc_role and db_ok): await update_hc_member_list(guild)

    except discord.Forbidden as fe: await interaction.followup.send(embed=create_embed(f"❌ Permission error managing {user.mention}.", discord.Color.red()), ephemeral=True); await log_error(guild, f"/hcverify Forbidden", error=fe, interaction=interaction)
    except Exception as e: await interaction.followup.send(embed=create_embed("❌ Unexpected HCVerify error.", discord.Color.red()), ephemeral=True); await log_error(guild, f"/hcverify error", error=e, interaction=interaction)

# --- Un-HC-Verify Command ---
@tree.command(name="unhcverify", description="Remove HC role and reset nickname.")
@app_commands.describe(user="The user to remove from HC verification.")
@app_commands.checks.has_permissions(manage_roles=True, manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def unhcverify(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(thinking=True, ephemeral=False)
    guild = interaction.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    log_actions, response_lines = [], []

    if not hc_role: await interaction.followup.send(embed=create_embed(f"❌ Setup error: Missing HC role.", discord.Color.red()), ephemeral=True); return
    if guild.me.top_role <= user.top_role and user.id != guild.owner_id: await interaction.followup.send(embed=create_embed(f"❌ Cannot manage {user.mention} due to hierarchy.", discord.Color.red()), ephemeral=True); return

    try:
        role_removed = False; reason = f"Un-HC-Verified by {interaction.user}"

        # 1. Role
        if hc_role in user.roles: await user.remove_roles(hc_role, reason=reason); log_actions.append(f"Rm HC Role"); response_lines.append(f"➖ Role: `{hc_role.name}`"); role_removed = True
        else: await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} lacks `{hc_role.name}`.", discord.Color.orange()), ephemeral=True); return

        # 2. Nickname
        nick_reset_status = "No change"
        if user.nick is not None:
            try: await user.edit(nick=None, reason=reason); log_actions.append("Reset Nick"); response_lines.append("🏷️ Nick Reset"); nick_reset_status = "Success"
            except discord.Forbidden: log_actions.append("Nick reset FAIL (Perms)"); response_lines.append("⚠️ Nick Reset Fail (Perms)"); nick_reset_status = "Perms Fail"
            except Exception as e: log_actions.append(f"Nick reset FAIL ({type(e).__name__})"); response_lines.append("⚠️ Nick Reset Fail (Error)"); nick_reset_status = "Error"; await log_error(guild, f"Nick reset fail {user.display_name}", error=e, interaction=interaction)
        else: log_actions.append("No nick"); response_lines.append("🏷️ No Nick.")

        # 3. Log & Respond
        await log_info(guild, f"`{interaction.user}` Un-HC-verified `{user.display_name}`. {'; '.join(log_actions)}.")
        is_error = nick_reset_status in ["Perms Fail", "Error"]
        title_suffix = " (with issues)" if is_error else ""
        embed_color = discord.Color.orange() if is_error else discord.Color.green()
        final_embed = create_embed(title=f"✅ Un-HC-Verified: {user.display_name}{title_suffix}", description="\n".join(response_lines), color=embed_color)
        await interaction.followup.send(embed=final_embed)

        # 4. Update List
        if role_removed: await update_hc_member_list(guild)

    except discord.Forbidden as fe: await interaction.followup.send(embed=create_embed(f"❌ Permission error managing {user.mention}.", discord.Color.red()), ephemeral=True); await log_error(guild, f"/unhcverify Forbidden", error=fe, interaction=interaction)
    except Exception as e: await interaction.followup.send(embed=create_embed("❌ Unexpected UnHCVerify error.", discord.Color.red()), ephemeral=True); await log_error(guild, f"/unhcverify error", error=e, interaction=interaction)


# --- HC Members Interactive List ---
@tree.command(name="hcmembers", description="Show an interactive list of [HC1] members (username ➔ IGN).")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild: await interaction.response.send_message("Use in a server.", ephemeral=True); return

    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        allowed = [f"<#{cid}>" for cid in ALLOWED_CHANNEL_IDS if guild.get_channel(cid)]
        await interaction.response.send_message(f"❌ Use in allowed channels: {', '.join(allowed) if allowed else 'N/A'}", ephemeral=True); return

    await interaction.response.defer(thinking=True, ephemeral=False)
    if not supabase: await interaction.followup.send(embed=create_embed("❌ DB unavailable.", discord.Color.red())); return

    try:
        # Uses username sorting and username format internally now
        member_data, total_count = await fetch_hc_member_data(guild)
        if not member_data:
            role = guild.get_role(ADD_ROLE_ID_HC)
            role_name = f"`{role.name}`" if role else f"ID {ADD_ROLE_ID_HC}"
            desc = f"No members found with {role_name} role." + (" Maybe DB error?" if total_count > 0 else "")
            await interaction.followup.send(embed=create_embed(f"{HC_LIST_EMBED_TITLE}\n{desc}", discord.Color.orange()))
        else:
            view = HCPagesView(member_data, total_count) # Uses username format now
            initial_embed = view.create_page_embed()
            message = await interaction.followup.send(embed=initial_embed, view=view)
            view.message = message
            await log_info(guild, f"/hcmembers list generated by `{interaction.user}`.")

    except Exception as e:
        await log_error(guild, "/hcmembers error", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Error fetching list.", discord.Color.red()))


# --- Refresh Static List Command ---
@tree.command(name="refresh", description="Manually refresh the static [HC1] member list (username ➔ IGN).")
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    guild = interaction.guild
    if not guild: return

    if not supabase: await interaction.followup.send(embed=create_embed("❌ DB unavailable.", discord.Color.red()), ephemeral=True); return
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(list_channel, discord.TextChannel): await interaction.followup.send(embed=create_embed(f"❌ List channel invalid.", discord.Color.red()), ephemeral=True); return

    try:
        await log_info(guild, f"Manual refresh static list triggered by `{interaction.user}`.")
        await update_hc_member_list(guild) # Uses username format internally now
        await interaction.followup.send(embed=create_embed(f"✅ Refresh initiated for list in {list_channel.mention}.", discord.Color.green()), ephemeral=True)
    except Exception as e:
        await log_error(guild, "/refresh error", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Refresh error.", discord.Color.red()), ephemeral=True)

# --- Bulk Update Command ---
@tree.command(name="bulkupdate", description="Open form to bulk update IGNs (username#tag ➔ IGN).")
@app_commands.checks.has_permissions(manage_roles=True)
async def bulkupdate(interaction: discord.Interaction):
    try:
        # Modal definition uses username format in placeholder now
        await interaction.response.send_modal(BulkUpdateModal())
        await log_info(interaction.guild, f"`{interaction.user}` opened bulk update modal.")
    except Exception as e:
        await log_error(interaction.guild, "Error opening bulk modal", error=e, interaction=interaction)
        if not interaction.response.is_done():
             try: await interaction.response.send_message("❌ Failed to open form.", ephemeral=True)
             except discord.InteractionResponded: pass

# --- Sync Nicknames Command ---
@tree.command(name="syncnicknames", description="Sync all HC members' nicknames with their stored IGNs.")
@app_commands.checks.has_permissions(manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_nicknames=True)
async def syncnicknames(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    guild = interaction.guild
    if not guild: return

    if not supabase: await interaction.followup.send(embed=create_embed("❌ DB unavailable.", discord.Color.red()), ephemeral=True); return
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role: await interaction.followup.send(embed=create_embed(f"❌ HC Role invalid.", discord.Color.red()), ephemeral=True); return

    start_time = discord.utils.utcnow()
    await log_info(guild, f"Nickname sync started by `{interaction.user}`.")
    await interaction.edit_original_response(content="🔄 Fetching data...")

    # Fetch IGNs
    ign_data = {}; try: resp = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").execute()); ign_data = {item['discord_id']: item['ingame_name'] for item in resp.data if item.get('ingame_name') and item.get('discord_id')} if resp and hasattr(resp, 'data') and resp.data else {}
    except Exception as e: await log_error(guild, "SyncNick DB Fetch Fail", error=e, interaction=interaction); await interaction.edit_original_response(content="❌ DB Fetch Fail."); return

    # Get HC Members
    hc_members = [m for m in guild.members if hc_role in m.roles and not m.bot]
    total = len(hc_members); if total == 0: await interaction.edit_original_response(content="ℹ️ No HC members found."); return
    await interaction.edit_original_response(content=f"🔄 Syncing {total} nicks...")

    # Process
    counts = {'p': 0, 'u': 0, 'k': 0, 'ni': 0, 'h': 0, 'f': 0, 'o': 0}; bot_top = guild.me.top_role
    for idx, m in enumerate(hc_members):
        counts['p'] += 1; mid = str(m.id)
        if bot_top <= m.top_role and m.id != guild.owner_id: counts['h'] += 1; continue
        ign = ign_data.get(mid); if not ign: counts['ni'] += 1; continue
        target = ign[:32]; if m.nick == target: counts['k'] += 1; continue
        try: await m.edit(nick=target, reason=f"Sync by {interaction.user}"); counts['u'] += 1; await asyncio.sleep(0.15)
        except discord.Forbidden: counts['f'] += 1
        except Exception as e: counts['o'] += 1; if counts['o'] < 5: await log_error(guild, f"SyncNick Err: {m.name}", error=e, embed=None)
        if idx % 25 == 0 and idx > 0: try: await interaction.edit_original_response(content=f"🔄 Syncing... ({idx}/{total})") except Exception: pass # Ignore transient update errors

    # Summary
    end_time = discord.utils.utcnow(); duration = (end_time - start_time).total_seconds()
    embed = discord.Embed(title="Nickname Sync Complete!", color=NERDY_YELLOW, timestamp=end_time)
    summary = f"Processed: {counts['p']}/{total}\n✅Upd: {counts['u']} | ℹ️Skip: {counts['k']} | ⚠️NoIGN: {counts['ni']}\n❌Fail (H): {counts['h']} | ❌Fail (P): {counts['f']} | ❌Fail (O): {counts['o']}\n⏱️Duration: {duration:.1f}s"
    embed.description = summary
    try: await interaction.edit_original_response(content=None, embed=embed)
    except Exception: print(f"SyncNick ({guild.name}): Failed final summary.")
    await log_info(guild, "", embed=discord.Embed(title="Nickname Sync Finished", description=summary, color=NERDY_YELLOW).set_footer(text=f"By {interaction.user}"))


# --- Wither Command ---
@tree.command(name="wither", description="Temporarily remove all roles from a user (except @everyone).")
@app_commands.describe(user="The user to wither.", time="Time in minutes (0.1 to 10, default 2).")
async def wither(interaction: discord.Interaction, user: discord.Member, time: app_commands.Range[float, 0.1, 10.0] = 2.0):
    guild = interaction.guild; invoker = interaction.user; bot_member = guild.me

    async def fail_log(reason: str, pub_msg: str, err: Optional[Exception] = None):
        await log_error(guild, f"Wither Fail ({invoker.name} -> {user.name}): {reason}", error=err, interaction=interaction)
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        try: await send(embed=create_embed(pub_msg, discord.Color.red()), ephemeral=True)
        except Exception: pass

    if invoker.id not in ALLOWED_WITHER_IDS: await fail_log("Invoker lacks perm.", "❌ No permission."); return
    if user.id == invoker.id: await fail_log("Self-wither.", "🤨 Why?"); return
    if user.id == SELF_PROTECTED_ID and invoker.id != SELF_PROTECTED_ID: await fail_log("Protected target.", "😨 Cannot wither Creator!"); return
    if user.id == BOT_ID: await fail_log("Target is bot.", "😭 Cannot wither myself!"); return
    if user.bot: await fail_log("Target is bot.", "🤖 Cannot wither bots."); return
    if user.id == guild.owner_id and invoker.id != guild.owner_id: await fail_log("Target is owner.", "👑 Cannot wither owner!"); return
    if bot_member.top_role <= user.top_role: await fail_log("Bot hierarchy low.", "❌ Cannot manage user (hierarchy)."); return
    if invoker.top_role <= user.top_role and invoker.id != guild.owner_id: await fail_log("Invoker hierarchy low.", "❌ Cannot manage user (hierarchy)."); return

    await interaction.response.defer(thinking=True, ephemeral=False)
    original_roles = [r for r in user.roles if r != guild.default_role]
    if not original_roles: await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} has no roles.", discord.Color.orange())); return

    try:
        time_seconds = int(time * 60)
        await user.edit(roles=[], reason=f"Wither by {invoker.name} ({time:.1f}m)")
        roles_str = ', '.join([f"`{r.name}`" for r in original_roles]); roles_str = (roles_str[:997] + '...') if len(roles_str) > 1000 else roles_str
        await interaction.followup.send(embed=create_embed(title="🌪️ Wither Cast! 🌪️", description=f"{user.mention} withered by {invoker.mention} for **{time:.1f} mins**!\nRemoved: {roles_str}", color=discord.Color.dark_purple()))
        await log_info(guild, f"`{user.name}` withered by `{invoker.name}` for {time:.1f}m.")

        await asyncio.sleep(time_seconds)

        member_after = await guild.fetch_member(user.id)
        if bot_member.top_role <= member_after.top_role: await log_error(guild, f"Wither Restore Fail: Bot hierarchy low for {member_after.name}."); await interaction.followup.send(embed=create_embed(f"⚠️ Failed restore {member_after.mention} (hierarchy).", discord.Color.red()), ephemeral=True); return
        await member_after.edit(roles=original_roles, reason=f"Wither ended ({time:.1f}m)")
        await interaction.followup.send(embed=create_embed(f"✨ {member_after.mention}'s roles restored!", color=NERDY_YELLOW))
        await log_info(guild, f"Restored roles for `{member_after.name}` after wither.")

    except discord.NotFound: await log_info(guild, f"`{user.name}` left before roles restored.")
    except discord.Forbidden as fe: phase="restore" if interaction.response.is_done() else "remove"; await fail_log(f"Forbidden {phase}.", f"❌ Permission error during {phase}.", err=fe)
    except Exception as e: phase="restore" if interaction.response.is_done() else "remove"; await fail_log(f"Error {phase}.", f"❌ Unexpected error during {phase}.", err=e)


# --- Nerd Help Command ---
@tree.command(name="nerdhelp", description="Show the list of available bot commands.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild: await interaction.response.send_message("Use in a server.", ephemeral=True); return

    embed = discord.Embed(title="🤓 Pingslave Bot Commands", description="Available commands:", color=NERDY_YELLOW)
    list_ch = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID); list_ch_m = list_ch.mention if list_ch else f"ID {HC_MEMBER_LIST_CHANNEL_ID}"
    allowed_chs = [f"<#{cid}>" for cid in ALLOWED_CHANNEL_IDS if guild.get_channel(cid)]; allowed_chs_str = ", ".join(allowed_chs) if allowed_chs else "N/A"

    def add_help(name: str, value: str, perms: str = "Everyone", notes: Optional[str] = None):
        fv = f"{value}\n**Permissions:** `{perms}`"; fv += f"\n**Note:** {notes}" if notes else ""; embed.add_field(name=name, value=fv, inline=False)

    embed.add_field(name="\u200B", value="**--- User Verification ---**", inline=False)
    add_help("/verify `<user>`", "Assigns 'Verified', removes 'Unverified'.", "Manage Roles")
    add_help("/unverify `<user>`", "Assigns 'Unverified', removes 'Verified'.", "Manage Roles")
    add_help("/hcverify `<user>` `<IGN>`", "Verifies into HC: saves IGN, roles, sets nick.", "Manage Roles, Manage Nicknames", "Updates list.")
    add_help("/unhcverify `<user>`", "Removes HC role, resets nick.", "Manage Roles, Manage Nicknames", "Updates list.")

    embed.add_field(name="\u200B", value="**--- [HC1] Guild List (username#tag ➔ IGN) ---**", inline=False) # Updated title
    add_help("/hcmembers", "Interactive HC member list.", "Everyone", f"Use in: {allowed_chs_str}.")
    add_help("/refresh", "Manually update static HC list.", "Manage Roles", f"Updates list in {list_ch_m}.")

    embed.add_field(name="\u200B", value="**--- Utilities & Admin ---**", inline=False)
    add_help("/bulkupdate", "Bulk update IGNs via form.", "Manage Roles", "Format: `username#tag ➔ IGN`. Updates list.")
    add_help("/syncnicknames", "Update HC nicks from stored IGNs.", "Manage Nicknames")
    add_help("/wither `<user>` `[time]`", "Temporarily remove all roles.", "Special Permission", f"Max {MAX_WITHER_SECONDS/60:.0f}m. Needs allowlist.")
    add_help("/nerdhelp", "Shows this help menu.", "Everyone")

    embed.set_footer(text="Bot by TheNerd | Stay nerdy!"); bot_user = bot.user
    if bot_user and bot_user.display_avatar: embed.set_thumbnail(url=bot_user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=False)


# --- Bot Startup ---
if __name__ == "__main__":
    print("--- Initializing Pingslave Bot ---")
    if not TOKEN: print("CRITICAL: DISCORD_BOT_TOKEN missing.")
    elif not supabase: print("CRITICAL: Supabase client failed. Bot will not run.")
    else:
        print("Token & Supabase OK.")
        print("Starting Keep Alive...")
        keep_alive()
        try:
            print("Starting Discord Bot run...")
            bot.run(TOKEN, log_handler=None) # Use default logging from discord.py for now
        except discord.LoginFailure: print("CRITICAL: Login Failure. Check Token.")
        except discord.PrivilegedIntentsRequired: print("CRITICAL: Privileged Intents (Members) missing in Dev Portal.")
        except Exception as e: print(f"CRITICAL: Bot run failed: {e}"); print(traceback.format_exc())
    print("--- Bot process finished ---")
