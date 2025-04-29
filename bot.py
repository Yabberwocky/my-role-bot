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
from typing import Optional, Tuple, List

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
#   - Environment Variables: DISCORD_BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY are set directly in Render's environment settings.
# Database: Supabase (PostgreSQL) used to store HC member IGNs linked to Discord IDs.
# Key Features: /verify, /hcverify (stores IGN), static list updates, /hcmembers (interactive list), /syncnicknames, /wither, /bulkupdate.
# --- END CONTEXT ---

# --- Configuration ---
TOKEN = os.getenv("MTM2MDE4MjMwMjczNDU0OTA1Mw.GXFQEV.T8C7rxK0-3pn1_ob4REpzi9C8GT5dk5Vvxy2m8")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
REMOVE_ROLE_ID = 1360176495947022447 # "Unverified" role
ADD_ROLE_ID_VERIFY = 1248708073019805717 # "Verified" role
ADD_ROLE_ID_HC = 1230235110415274004 # "HC" role
ALLOWED_CHANNEL_IDS = {1354431395140731165, 1330664430148780102, 1248710731407560835} # Channels for /hcmembers
HC_MEMBER_LIST_CHANNEL_ID = 1354431395140731165 # Channel for static list
HC_LIST_EMBED_TITLE = "**\[HC1\] Guild Members**"
ALLOWED_WITHER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692} # User IDs for /wither
SELF_PROTECTED_ID = 1230848174218940416 # Protected from /wither
BOT_ID: Optional[int] = None # Bot's own User ID (set in on_ready)
MAX_WITHER_SECONDS = 600 # Max duration for /wither (10 minutes)
INFO_LOG_CHANNEL_ID = 1317943895606165579 # Info log channel
ERROR_LOG_CHANNEL_ID = 1362988767367135453 # Error log channel
MEMBERS_PER_PAGE = 50 # Members per page in lists
NERDY_YELLOW = discord.Color.gold() # Embed color

# --- Supabase Client ---
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try: supabase = create_client(SUPABASE_URL, SUPABASE_KEY); print("Supabase client created successfully.")
    except Exception as e: print(f"CRITICAL: Failed Supabase client creation: {e}"); supabase = None
else: print("CRITICAL: Supabase credentials missing."); supabase = None

# --- Discord Setup ---
intents = discord.Intents.default(); intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# --- Flask App (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Pingslave bot is alive!"
def run_flask():
    try: port = int(os.environ.get('PORT', 8080)); print(f"Starting Flask server on 0.0.0.0:{port}"); app.run(host='0.0.0.0', port=port)
    except Exception as e: print(f"Flask server failed: {e}\n{traceback.format_exc()}")
def keep_alive(): flask_thread = threading.Thread(target=run_flask, daemon=True); flask_thread.start(); print("Keep alive thread initiated.")

# --- Utility Functions ---
async def run_supabase_sync(func):
    """Runs sync Supabase func in executor."""
    if not supabase: raise ConnectionError("Supabase client unavailable.")
    try: loop = asyncio.get_running_loop(); return await loop.run_in_executor(None, func)
    except APIError as e: print(f"Supabase API Error: {e}"); raise
    except Exception as e: print(f"Supabase executor Error: {e}"); raise

# --- Logging ---
async def log_to_channel(channel_id: int, guild: Optional[discord.Guild], message: Optional[str] = None, embed: Optional[discord.Embed] = None):
    """Sends log to a channel, checking permissions."""
    if not guild: print(f"Log Error: No Guild for channel {channel_id}."); return
    log_channel = guild.get_channel(channel_id)
    if not isinstance(log_channel, discord.TextChannel): print(f"Log Error: Channel {channel_id} invalid in {guild.name}."); return
    # Check if bot object and its user are ready before accessing guild.me
    if not bot or not bot.user: print(f"Log Error: Bot not ready, cannot get member object in {guild.name}."); return
    bot_member = guild.get_member(bot.user.id) # More reliable way to get self member
    if not bot_member: print(f"Log Error: Cannot find bot ({bot.user.id if bot.user else 'N/A'}) in {guild.name}."); return
    perms = log_channel.permissions_for(bot_member)
    if not perms.send_messages or (embed and not perms.embed_links): print(f"Log Error: Missing Send/Embed perms in {log_channel.mention}."); return
    try:
        if embed: await log_channel.send(embed=embed)
        elif message: await log_channel.send((message[:1997] + "...") if len(message) > 2000 else message)
    except discord.Forbidden: print(f"Log Error: Forbidden in {log_channel.mention}.")
    except discord.HTTPException as e: print(f"Log Error: HTTP {e.status} in {log_channel.mention}: {e.text}")
    except Exception as e: print(f"Log Error: Send fail in {log_channel.mention}: {e}")

async def log_info(guild: Optional[discord.Guild], message: str, embed: Optional[discord.Embed] = None):
    """Logs an info message."""
    if not embed: embed = discord.Embed(description=message, color=NERDY_YELLOW); embed.timestamp = discord.utils.utcnow()
    await log_to_channel(INFO_LOG_CHANNEL_ID, guild, embed=embed)

async def log_error(guild: Optional[discord.Guild], message: str, error: Optional[Exception] = None, interaction: Optional[discord.Interaction] = None, embed: Optional[discord.Embed] = None):
    """Logs an error with context and traceback."""
    if not embed:
        embed = discord.Embed(title="⚠️ Bot Error / Warning", description=message, color=discord.Color.red()); embed.timestamp = discord.utils.utcnow()
        if interaction:
            cmd_name = interaction.command.name if interaction.command else 'N/A'
            cmd = f"`/{cmd_name}`"
            chan_mention = interaction.channel.mention if isinstance(interaction.channel, discord.TextChannel) else ""
            chan_info = f" in {chan_mention}" if chan_mention else f" Ch:{interaction.channel_id}" if interaction.channel else ""
            user = f"{interaction.user.mention} (`{interaction.user.id}`)"
            embed.add_field(name="Context", value=f"Cmd: {cmd}{chan_info}\nUser: {user}", inline=False)
        if error:
            etype, emsg = type(error).__name__, str(error)
            tb = "".join(traceback.format_exception(type(error), error, error.__traceback__, limit=6))
            tb_short = (tb[:950] + "\n... (Truncated)") if len(tb) > 950 else tb
            details = f"**Type:** `{etype}`\n" + (f"**Msg:** `{emsg}`\n" if emsg else "") + f"**Traceback:**\n```py\n{tb_short}\n```"
            # Check length before adding field
            if len(details) > 1024:
                 details = details[:1021] + "...```" # Truncate preserving code block where possible
            embed.add_field(name="Error Details", value=details, inline=False)
            full_tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            print(f"---\nERROR LOGGED:\nGuild: {guild.id if guild else 'N/A'}\nCtx: {message}\nErr: {etype}: {emsg}\n{full_tb}---\n")
    await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, embed=embed)


# --- Embed Pagination View ---
class HCPagesView(View):
    """ Paginated view for HC members (numbered, username#tag ➔ IGN)."""
    def __init__(self, data: List[Tuple[Optional[discord.Member], str]], total_members: int, timeout=300.0):
        super().__init__(timeout=timeout)
        self.data = data
        self.total_members = total_members
        self.current_page = 0
        self.total_pages = math.ceil(len(self.data) / MEMBERS_PER_PAGE) if self.data else 1
        self.message: Optional[discord.Message] = None
        self.update_buttons()

    def create_page_embed(self) -> discord.Embed:
        start = self.current_page * MEMBERS_PER_PAGE
        page_data = self.data[start : start + MEMBERS_PER_PAGE]
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, color=NERDY_YELLOW)
        desc = []
        idx = start + 1
        for member, ign in page_data:
            user = discord.utils.escape_markdown(f"{member.name}#{member.discriminator}" if member and member.discriminator != '0' else member.name) if member else "*User Left?*"
            ign_str = discord.utils.escape_markdown(ign or "Unknown")
            desc.append(f"{idx}. {user} ➔ {ign_str}")
            idx += 1
        embed.description = "\n".join(desc) if desc else "No members."
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} | Total: {self.total_members}")
        embed.timestamp = discord.utils.utcnow()
        return embed

    def update_buttons(self):
        # Ensure children are populated before accessing
        if hasattr(self, 'children') and len(self.children) >= 2:
            # Assuming first two children are previous and next buttons
            prev_button = self.children[0]
            next_button = self.children[1]
            if isinstance(prev_button, Button):
                prev_button.disabled = self.current_page == 0
            if isinstance(next_button, Button):
                next_button.disabled = self.current_page >= self.total_pages - 1

    async def edit_message(self, interaction: discord.Interaction):
        embed = self.create_page_embed()
        self.update_buttons()
        try:
            # Use edit_original_response if interaction hasn't been responded to yet (e.g. initial send),
            # otherwise use edit_message for subsequent edits. Check response state.
            if not interaction.response.is_done():
                 await interaction.response.edit_message(embed=embed, view=self)
            elif self.message: # Ensure self.message exists before trying to edit
                 await self.message.edit(embed=embed, view=self)
            else: # Fallback if message somehow got lost
                 await interaction.followup.send("Error updating view.", ephemeral=True)

        except discord.NotFound:
            print(f"Paginator edit fail: Original message {self.message.id if self.message else 'Unknown'} not found.")
            # Disable buttons on timeout if message is gone
            for item in self.children:
                if isinstance(item, Button): item.disabled = True
            # Don't try to edit if message not found
        except discord.HTTPException as e:
            await log_error(interaction.guild, "Paginator edit fail (HTTP)", error=e, interaction=interaction)
        except Exception as e:
            await log_error(interaction.guild, "Paginator edit fail (General)", error=e, interaction=interaction)

    @button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="hc_prev_interactive", row=0)
    async def previous_button(self, interaction: discord.Interaction, b: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.edit_message(interaction) # Pass interaction here
        else:
            # Defer only if no action is taken to prevent "Interaction Failed"
            try:
                await interaction.response.defer()
            except discord.InteractionResponded: # Catch if we already responded somehow
                pass
            except discord.NotFound: # Catch if the interaction expired before deferring
                print("Previous Button: Interaction expired before defer.")
            except Exception as e:
                 await log_error(interaction.guild, "Previous Button Defer Error", e, interaction)


    @button(label="Next", style=discord.ButtonStyle.blurple, custom_id="hc_next_interactive", row=0)
    async def next_button(self, interaction: discord.Interaction, b: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.edit_message(interaction) # Pass interaction here
        else:
            # Defer only if no action is taken
            try:
                await interaction.response.defer()
            except discord.InteractionResponded:
                pass
            except discord.NotFound:
                print("Next Button: Interaction expired before defer.")
            except Exception as e:
                 await log_error(interaction.guild, "Next Button Defer Error", e, interaction)


    async def on_timeout(self):
        if self.message:
            try:
                for item in self.children:
                    if isinstance(item, Button): item.disabled = True
                # Make sure view=self is included to persist disabled state
                await self.message.edit(view=self)
                print(f"Paginator timeout: Disabled buttons on message {self.message.id}")
            except discord.NotFound:
                 print(f"Paginator timeout edit fail: Message {self.message.id} not found.")
            except Exception as e:
                 # Avoid logging errors during timeout if guild is unavailable
                 guild = self.message.guild
                 if guild:
                      await log_error(guild, f"Paginator timeout edit fail on message {self.message.id}", error=e)
                 else:
                      print(f"Paginator timeout edit fail on message {self.message.id} (guild unavailable): {e}")
        self.stop() # Ensure the view stops listening


# --- Core HC List Logic ---
async def fetch_hc_member_data(guild: discord.Guild) -> Tuple[List[Tuple[Optional[discord.Member], str]], int]:
    """ Fetches HC members (sorted by username#discriminator) and IGNs."""
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"HC Role {ADD_ROLE_ID_HC} not found.")
        return [], 0
    # Ensure member cache is populated if needed (though intents.members should handle this)
    if not guild.chunked:
        try:
            await guild.chunk(cache=True)
            print(f"Chunked guild {guild.name} for fetch_hc_member_data.")
        except Exception as e:
             await log_error(guild, "Guild chunking failed in fetch_hc_member_data", error=e)
             # Continue anyway, might get partial results if cache isn't full

    members_with_role = [m for m in guild.members if hc_role in m.roles and not m.bot]
    total = len(members_with_role)
    # Sort by username (case-insensitive) then discriminator
    members_sorted = sorted(members_with_role, key=lambda m: (m.name.lower(), m.discriminator))
    ids = [str(m.id) for m in members_sorted]
    ign_map = {}
    if supabase and ids:
        try:
            # Fetch in chunks to avoid potential Supabase limits (though 500 is usually fine)
            chunk_size = 500
            for i in range(0, len(ids), chunk_size):
                chunk = ids[i:i+chunk_size]
                resp = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").in_("discord_id", chunk).execute())
                if resp and hasattr(resp, 'data') and resp.data:
                    ign_map.update({r['discord_id']: r.get("ingame_name") or "Unknown" for r in resp.data})
                await asyncio.sleep(0.1) # Small delay between chunks
        except ConnectionError as e: # Catch specific Supabase connection error
             await log_error(guild, "Supabase connection unavailable during IGN fetch.", error=e)
             ign_map = {mid: "DB Connection Err" for mid in ids} # Indicate connection issue
        except APIError as e:
             await log_error(guild, "Supabase API Error during IGN fetch.", error=e)
             ign_map = {mid: "DB API Err" for mid in ids} # Indicate API issue
        except Exception as e:
            await log_error(guild, "Unexpected error during IGN fetch.", error=e)
            ign_map = {mid: "DB Fetch Err" for mid in ids} # Generic fetch error

    # Combine members and their IGNs
    result_data = [(m, ign_map.get(str(m.id), "Unknown")) for m in members_sorted]
    return result_data, total

def generate_hc_list_embeds(data: List[Tuple[Optional[discord.Member], str]], total: int) -> List[discord.Embed]:
    """ Generates static list embeds (numbered, username#tag ➔ IGN)."""
    if not data:
        e=discord.Embed(title=HC_LIST_EMBED_TITLE, description="No HC members found.", color=discord.Color.orange())
        e.set_footer(text="Page 1/1 | Total: 0")
        e.timestamp=discord.utils.utcnow()
        return [e]

    embeds = []
    pages = math.ceil(len(data) / MEMBERS_PER_PAGE)
    for page in range(pages):
        start = page * MEMBERS_PER_PAGE
        page_data = data[start : start + MEMBERS_PER_PAGE]
        e = discord.Embed(title=HC_LIST_EMBED_TITLE, color=NERDY_YELLOW)
        desc = []
        idx = start + 1
        for m, ign in page_data:
            user=discord.utils.escape_markdown(f"{m.name}#{m.discriminator}" if m and m.discriminator != '0' else m.name) if m else "*User Left Guild?*"
            ign_s=discord.utils.escape_markdown(ign or "Unknown")
            desc.append(f"{idx}. {user} ➔ {ign_s}")
            idx += 1
        # Check if description exceeds limit
        full_desc = "\n".join(desc)
        if len(full_desc) > 4096:
            # This shouldn't happen with MEMBERS_PER_PAGE=50, but good to check
            full_desc = full_desc[:4093] + "..."
        e.description=full_desc
        e.set_footer(text=f"Page {page+1}/{pages} | Total: {total}")
        e.timestamp=discord.utils.utcnow()
        embeds.append(e)
    return embeds

async def update_hc_member_list(guild: discord.Guild):
    """ Updates static HC list (username#tag ➔ IGN format)."""
    chan = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(chan, discord.TextChannel):
        await log_error(guild, f"Static list channel {HC_MEMBER_LIST_CHANNEL_ID} invalid or not found.")
        return

    if not bot or not bot.user:
        await log_error(guild, "Cannot update static list: Bot user object not available.")
        return
    bot_mem = guild.get_member(bot.user.id) # Use get_member
    if not bot_mem:
        await log_error(guild, f"Cannot update static list: Bot not found in guild {guild.name}.")
        return

    perms = chan.permissions_for(bot_mem)
    required_perms = {
        "Send Messages": perms.send_messages,
        "Embed Links": perms.embed_links,
        "Read Message History": perms.read_message_history,
        "Manage Messages": perms.manage_messages
    }
    missing = [p for p, has in required_perms.items() if not has]
    if missing:
        await log_error(guild, f"Bot missing permissions in {chan.mention} for static list update: {', '.join(missing)}")
        return

    try:
        await log_info(guild, f"Starting static list update in {chan.mention}...")
        data, total = await fetch_hc_member_data(guild)
        new_embeds = generate_hc_list_embeds(data, total)
        num_new = len(new_embeds)

        existing: List[discord.Message] = []
        try:
            # Fetch slightly more messages just in case of non-bot messages interfering
            async for msg in chan.history(limit=max(num_new, 15)): # Fetch at least 15 or num_new
                # Ensure message has an author before checking ID
                if msg.author and msg.author.id == bot.user.id and msg.embeds:
                     # Check title robustly
                     if msg.embeds[0].title and msg.embeds[0].title == HC_LIST_EMBED_TITLE:
                          existing.append(msg)
        except discord.Forbidden:
             await log_error(guild, f"History permission denied in {chan.mention} during static list update.")
             return
        except Exception as e:
            await log_error(guild, "Error fetching history for static list update", error=e)
            return

        # Sort oldest to newest to match sending/editing order
        existing.sort(key=lambda m: m.created_at)
        num_exist = len(existing)
        print(f"Static List Update ({guild.name}): Found {num_exist} existing bot messages, Need to display {num_new} pages.")

        # --- Edit/Send/Delete Logic ---
        tasks = []
        messages_to_delete = []

        # Edit existing messages or send new ones
        for i in range(num_new):
            await asyncio.sleep(1.2) # Rate limiting per action
            if i < num_exist: # Edit existing message
                print(f"  Editing message {existing[i].id} (Page {i+1})")
                tasks.append(existing[i].edit(embed=new_embeds[i]))
            else: # Send new message
                print(f"  Sending new message (Page {i+1})")
                tasks.append(chan.send(embed=new_embeds[i]))

        # Identify surplus messages to delete
        if num_exist > num_new:
            messages_to_delete = existing[num_new:]
            print(f"  Identified {len(messages_to_delete)} surplus messages to delete.")

        # Execute edits/sends
        results = await asyncio.gather(*tasks, return_exceptions=True)
        edit_send_errors = 0
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                edit_send_errors += 1
                action = "Edit" if i < num_exist else "Send"
                msg_id = existing[i].id if i < num_exist else "New"
                await log_error(guild, f"Static list {action} failed for Page {i+1} (MsgID: {msg_id})", error=res)

        # Execute deletions if necessary
        delete_errors = 0
        if messages_to_delete:
            # Use bulk delete if possible and sensible (more than 1 message)
            can_bulk_delete = perms.manage_messages and len(messages_to_delete) > 1
            if can_bulk_delete:
                try:
                    # Bulk delete can only handle messages < 14 days old. Handle potential errors.
                    await chan.delete_messages(messages_to_delete)
                    print(f"  Bulk deleted {len(messages_to_delete)} surplus messages.")
                except discord.HTTPException as e:
                    # Handle cases like messages being too old for bulk delete
                    print(f"  Bulk delete failed (HTTP {e.status}): {e.text}. Falling back to individual deletion.")
                    can_bulk_delete = False # Force individual deletion fallback
                except Exception as e:
                    await log_error(guild, f"Bulk delete failed unexpectedly", error=e)
                    can_bulk_delete = False # Force individual deletion fallback

            # Fallback to individual deletion if bulk delete is not possible or failed
            if not can_bulk_delete:
                 for msg_del in messages_to_delete:
                    await asyncio.sleep(1.2) # Rate limit individual deletes too
                    try:
                        await msg_del.delete()
                        print(f"  Individually deleted surplus message {msg_del.id}")
                    except Exception as e:
                        delete_errors += 1
                        await log_error(guild, f"Failed to delete surplus message {msg_del.id}", error=e)

        # Log completion status
        status_msg = f"Static list update complete ({num_new} pages displayed)."
        if edit_send_errors > 0: status_msg += f" Encountered {edit_send_errors} edit/send errors."
        if delete_errors > 0: status_msg += f" Encountered {delete_errors} delete errors."
        log_level = log_error if edit_send_errors > 0 or delete_errors > 0 else log_info
        await log_level(guild, status_msg)

    except Exception as e:
        await log_error(guild, "Unhandled error during static list update process", error=e)


# --- Discord Events ---
@bot.event
async def on_ready():
    global BOT_ID
    if bot.user:
        BOT_ID = bot.user.id
        print(f"Logged in as {bot.user} (ID: {BOT_ID})")
        print(f"Discord.py v{discord.__version__}")
    else:
        print("CRITICAL ERROR: Bot user object not found on ready.")
        return # Cannot proceed without bot user

    synced_count = 0
    try:
        synced = await tree.sync()
        synced_count = len(synced)
        print(f"Synced {synced_count} application commands globally.")
    except Exception as e:
        print(f"Command Sync failed: {e}")
        # Try to log error to the first available guild's error channel
        first_guild = bot.guilds[0] if bot.guilds else None
        if first_guild:
            await log_error(first_guild, "Application Command Sync failed on startup.", error=e)

    if not bot.guilds:
        print("Bot is not currently in any guilds.")
        return

    print(f"Performing initial setup for {len(bot.guilds)} guild(s)...")
    # Create a list of guilds to iterate over to avoid issues if guild list changes during iteration
    guilds_to_process = list(bot.guilds)
    for guild in guilds_to_process:
        print(f"  Processing guild: {guild.name} (ID: {guild.id})")
        try:
            # Log ready status first
            await log_info(guild, f"Bot ready and online. Synced {synced_count} commands.")
            # Then update the static list for this guild
            await update_hc_member_list(guild)
            await asyncio.sleep(1) # Small delay between guilds
        except Exception as e:
            # Log error specific to this guild's setup
            await log_error(guild, f"Error during on_ready setup for this guild", error=e)
    print("Initial setup loop complete.")


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Ignore updates for bots or if roles haven't changed
    if after.bot or before.roles == after.roles:
        return

    guild = after.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    # Ignore if HC role doesn't exist in the server
    if not hc_role:
        # Maybe log this once if it happens often, but avoid spamming logs
        # print(f"Warning: HC Role ID {ADD_ROLE_ID_HC} not found in guild {guild.name} during on_member_update.")
        return

    # Check if the HC role status specifically changed
    had_hc_role = hc_role in before.roles
    has_hc_role = hc_role in after.roles

    if had_hc_role != has_hc_role:
        action = "added to" if has_hc_role else "removed from"
        # Log the change
        await log_info(guild, f"HC role (`{hc_role.name}`) {action} user {after.mention} (`{after.id}`). Triggering static list update.")
        # Trigger the list update
        try:
            await update_hc_member_list(guild)
        except Exception as e:
             await log_error(guild, f"Failed to update static list after role change for {after.mention}", error=e)


# --- App Command Error Handling ---
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    guild = interaction.guild
    user_msg = "❌ An unexpected error occurred. Please try again later."
    log_desc = "Unhandled App Command Error"
    error_to_log = error # Default to logging the original error

    # Specific error handling
    if isinstance(error, app_commands.CommandNotFound):
        # This usually shouldn't happen with synced commands, but good practice
        print(f"CommandNotFound error received for interaction: {interaction.data.get('name', 'N/A')}")
        # No need to inform user or log excessively unless debugging sync issues
        return
    elif isinstance(error, app_commands.MissingPermissions):
        perms = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
        user_msg = f"❌ You lack the required permissions: {perms}"
        log_desc = f"User Missing Permissions: {perms}"
        error_to_log = None # Don't need full traceback for permissions issue
    elif isinstance(error, app_commands.BotMissingPermissions):
        perms = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
        user_msg = f"❌ I lack the required permissions: {perms}. Please contact an admin."
        log_desc = f"Bot Missing Permissions: {perms}"
        error_to_log = None
    elif isinstance(error, app_commands.CheckFailure):
        # Catch generic check failures (like custom checks or has_permissions failing without specific exception)
        user_msg = "❌ You do not meet the requirements to use this command."
        log_desc = f"Check Failure ({type(error).__name__})"
        error_to_log = None # Usually no traceback needed
    elif isinstance(error, app_commands.CommandInvokeError):
        # This wraps errors raised *inside* the command function
        original_error = error.original
        error_to_log = original_error # Log the underlying error
        user_msg = f"❌ An error occurred while running the command: `{type(original_error).__name__}`"
        log_desc = "Command Invoke Error"
        # Print traceback for easier debugging during development/testing
        print(f"CommandInvokeError in command '{interaction.command.name if interaction.command else 'Unknown'}':")
        traceback.print_exception(type(original_error), original_error, original_error.__traceback__)
    elif isinstance(error, app_commands.TransformerError):
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
    else:
        # Catch any other app_commands specific errors or fallback
        log_desc = f"Unknown App Command Error Type: `{type(error).__name__}`"

    # Log the error with context
    await log_error(guild, log_desc, error=error_to_log, interaction=interaction)

    # Attempt to inform the user, trying followup if already responded
    try:
        if interaction.response.is_done():
            await interaction.followup.send(user_msg, ephemeral=True)
        else:
            await interaction.response.send_message(user_msg, ephemeral=True)
    except discord.NotFound:
        print(f"Error Handler: Interaction {interaction.id} already expired.")
    except discord.InteractionResponded:
         # If it was somehow responded to between the check and the send
         try:
              await interaction.followup.send(user_msg, ephemeral=True)
         except Exception as e:
              print(f"Error Handler: Failed to send followup after InteractionResponded: {e}")
    except Exception as e:
        # Catch other potential issues sending the error message
        print(f"Error Handler: Failed to send error message to user: {e}")


# --- Modals ---
def create_embed(description: str, color: discord.Color = NERDY_YELLOW, title: Optional[str] = None) -> discord.Embed:
     embed = discord.Embed(title=title, description=description, color=color)
     # Optionally add a timestamp to embeds created this way
     # embed.timestamp = discord.utils.utcnow()
     return embed

class BulkUpdateModal(Modal, title="Bulk Update IGNs"):
    """ Modal for bulk update (username#tag ➔ IGN format). Handles input without numbers."""
    data = TextInput(
        label="Paste list (username#tag ➔ IGN)",
        style=discord.TextStyle.paragraph,
        placeholder="ExampleUser#1234 ➔ CoolIGN\nAnotherUser ➔ AnotherIGN\n(One entry per line, format flexible)",
        required=True,
        min_length=5,
        max_length=4000 # Discord limit
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.guild
        if not guild or not supabase:
            await interaction.followup.send("❌ Internal error (Guild or DB unavailable).", ephemeral=True)
            return

        lines = self.data.value.strip().splitlines()
        if not lines:
            await interaction.followup.send("⚠️ Input was empty.", ephemeral=True)
            return

        # Pre-fetch members for efficient lookup
        member_map_id = {}
        member_map_name_disc = {} # For username#1234 format
        member_map_name_only = {} # For new username format or display name fallback
        try:
            if not guild.chunked: await guild.chunk(cache=True)
            for m in guild.members:
                if m.bot: continue
                member_map_id[str(m.id)] = m
                # Store both with and without discriminator for matching flexibility
                if m.discriminator != '0': # Old username format
                    member_map_name_disc[f"{m.name}#{m.discriminator}".lower()] = m
                member_map_name_only[m.name.lower()] = m # New username format
                member_map_name_only[m.display_name.lower()] = m # Also check display name

        except Exception as e:
            await log_error(guild, "Bulk update member fetch/chunking fail", error=e, interaction=interaction)
            await interaction.followup.send("❌ Error fetching server members. Cannot process update.", ephemeral=True)
            return

        success_count, fail_count, not_found_count = 0, 0, 0
        log_details = []
        payload = []

        for idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line: continue

            parts = line.split("➔", 1)
            if len(parts) != 2:
                fail_count += 1
                log_details.append(f"❌ L{idx}: Invalid format (Missing '➔') - Line: `{line[:50]}`")
                continue

            identifier_raw, ign_raw = map(str.strip, parts)
            ign = ign_raw

            # Clean identifier: remove potential leading list numbers/dots/spaces
            identifier_clean = identifier_raw.lstrip('0123456789. ')
            identifier_lower = identifier_clean.lower()

            if not identifier_clean or not ign:
                fail_count += 1
                log_details.append(f"❌ L{idx}: Missing user identifier or IGN after cleaning - User: `{identifier_raw[:30]}`, IGN: `{ign_raw[:30]}`")
                continue

            member: Optional[discord.Member] = None
            # Prioritize ID lookup if the identifier looks like an ID
            if identifier_clean.isdigit():
                member = member_map_id.get(identifier_clean)

            # Then try username#discriminator
            if not member:
                member = member_map_name_disc.get(identifier_lower)

            # Finally, try username only / display name
            if not member:
                 member = member_map_name_only.get(identifier_lower)


            if not member:
                fail_count += 1
                not_found_count += 1
                log_details.append(f"❓ L{idx}: User not found - Identifier: `{discord.utils.escape_markdown(identifier_clean)}`")
                continue

            # Check for IGN length (Supabase might have limits, but Discord nick limit is 32)
            if len(ign) > 100: # Arbitrary reasonable limit for IGN storage
                 ign = ign[:100] # Truncate if excessively long
                 log_details.append(f"⚠️ L{idx}: IGN for {member.mention} truncated to 100 chars.")


            # Found member, prepare payload for Supabase
            payload.append({
                "discord_id": str(member.id),
                "discord_name": f"{member.name}#{member.discriminator}" if member.discriminator != '0' else member.name, # Store full for reference
                "ingame_name": ign
            })

        # Perform Supabase upsert if there's data
        db_error = None
        if payload:
            try:
                await run_supabase_sync(
                    lambda: supabase.table("hc_members")
                                    .upsert(payload, on_conflict="discord_id")
                                    .execute()
                )
                success_count = len(payload)
            except Exception as e:
                db_error = e
                fail_count += len(payload) # Count payload items as failures if DB operation fails
                success_count = 0 # Reset success count on DB error
                await log_error(guild, "Bulk update Supabase upsert failed", error=e, interaction=interaction)
                log_details.append(f"🔥 **Database Error:** Failed to save {len(payload)} entries. See error logs.")

        # --- Prepare and send response ---
        result_color = discord.Color.green() if fail_count == 0 and not db_error else (discord.Color.orange() if success_count > 0 else discord.Color.red())
        embed = discord.Embed(title="Bulk IGN Update Results", color=result_color)

        summary = (
            f"Processed Lines: {len(lines)}\n"
            f"✅ Successful Updates: {success_count}\n"
            f"❌ Failed Entries: {fail_count} (Not Found: {not_found_count}, Format/Data Issues: {fail_count - not_found_count})\n"
            f"{'🔥 Database Error occurred!' if db_error else ''}"
        )
        embed.description = summary

        # Add details about issues if any occurred
        if log_details:
            log_output = "\n".join(log_details)
            # Handle potential embed field value limit (1024 chars)
            if len(log_output) > 1024:
                log_output = log_output[:1021] + "..."
            embed.add_field(name="Details", value=log_output, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

        # Log summary to info channel
        # --- FIX APPLIED HERE ---
        summary_for_log = summary.replace('\n', ' | ') # Perform replace *before* f-string
        await log_info(guild, f"Bulk update initiated by `{interaction.user}` completed. Results: {summary_for_log}")
        # --- END FIX ---

        # Trigger static list update if successful changes were made
        if success_count > 0:
            # Add a small delay before updating list to ensure DB write consistency if needed
            await asyncio.sleep(0.5)
            await update_hc_member_list(guild)


# --- Slash Commands ---

# --- Verify Command ---
@tree.command(name="verify", description="Verify a standard user (adds Verified, removes Unverified).")
@app_commands.describe(user="The user to verify.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    if not guild: # Should not happen in guild command, but good practice
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    # Fetch roles by ID
    role_to_remove = guild.get_role(REMOVE_ROLE_ID)
    role_to_add = guild.get_role(ADD_ROLE_ID_VERIFY)

    # Check if roles exist
    missing_roles = []
    # Only add to missing if the role ID is configured but not found
    if REMOVE_ROLE_ID and not role_to_remove: missing_roles.append(f"Unverified Role (ID: {REMOVE_ROLE_ID})")
    if ADD_ROLE_ID_VERIFY and not role_to_add: missing_roles.append(f"Verified Role (ID: {ADD_ROLE_ID_VERIFY})")
    if missing_roles:
        await interaction.response.send_message(f"❌ Setup Error: The following role(s) could not be found: {', '.join(missing_roles)}. Please contact an admin.", ephemeral=True)
        await log_error(guild, f"Verify command failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return

    # Ensure the role we need to add actually exists before proceeding
    if not role_to_add:
         await interaction.response.send_message(f"❌ Setup Error: Verified Role (ID: {ADD_ROLE_ID_VERIFY}) not found. Cannot verify.", ephemeral=True)
         return


    # Hierarchy check (Corrected - using .position)
    bot_member = guild.me
    if bot_member.top_role.position <= user.top_role.position \
       or bot_member.top_role.position <= role_to_add.position \
       or (role_to_remove and bot_member.top_role.position <= role_to_remove.position):
         await interaction.response.send_message("❌ Hierarchy Error: I cannot manage roles for this user or the roles involved (my top role is not high enough).", ephemeral=True)
         await log_error(guild, f"Verify command failed: Bot hierarchy too low for user {user.mention} or roles.", interaction=interaction)
         return

    # Check invoker hierarchy
    if interaction.user.top_role <= user.top_role and interaction.user.id != guild.owner_id:
         await interaction.response.send_message("❌ Hierarchy Error: You cannot manage roles for this user.", ephemeral=True)
         return

    await interaction.response.defer(thinking=True, ephemeral=True) # Defer privately initially

    actions_taken = []
    reason = f"Verified by {interaction.user} (ID: {interaction.user.id})"
    modified = False

    try:
        # Check if user already has the 'Verified' role and doesn't have 'Unverified' (if configured)
        has_verified = role_to_add in user.roles
        # Check unverified role only if it's configured AND found
        has_unverified = role_to_remove and role_to_remove in user.roles

        if has_verified and not has_unverified:
             await interaction.followup.send(f"ℹ️ {user.mention} is already verified.", ephemeral=True)
             return

        # Prepare modifications
        roles_to_add_list = []
        roles_to_remove_list = []

        if has_unverified: # role_to_remove is guaranteed to exist here if has_unverified is True
            roles_to_remove_list.append(role_to_remove)
            actions_taken.append(f"➖ Removed `{role_to_remove.name}`")
            modified = True
        if not has_verified:
            roles_to_add_list.append(role_to_add)
            actions_taken.append(f"➕ Added `{role_to_add.name}`")
            modified = True

        # Apply modifications if any changes were needed
        if modified:
            # Using add/remove_roles is generally safer than edit(roles=...)
            if roles_to_add_list:
                await user.add_roles(*roles_to_add_list, reason=reason)
            if roles_to_remove_list:
                 await user.remove_roles(*roles_to_remove_list, reason=reason)

            await log_info(guild, f"`{interaction.user}` verified {user.mention}. Actions: {', '.join(actions_taken)}.")
            # Send private confirmation
            await interaction.followup.send(f"✅ Successfully verified {user.mention}.", ephemeral=True)
            # Send public notification in the channel command was used
            public_embed = create_embed(f"✅ **{user.display_name}** has been verified!\n" + "\n".join(actions_taken), discord.Color.green())
            try:
                # Ensure channel is text channel before sending
                if isinstance(interaction.channel, discord.TextChannel):
                    await interaction.channel.send(embed=public_embed)
                else:
                    await log_info(guild, f"Skipped public verify notification for {user.mention} (command used outside text channel).")

            except (discord.Forbidden, discord.HTTPException) as e:
                await log_error(guild,"Failed to send public verify notification", error=e, interaction=interaction)
        else:
            # This case should be caught by the initial check, but as a fallback
            await interaction.followup.send("ℹ️ No role changes were needed.", ephemeral=True)

    except discord.Forbidden:
        await log_error(guild, "Verify command failed: Bot lacks permissions (Forbidden).", interaction=interaction)
        await interaction.followup.send("❌ Failed: I don't have the necessary permissions to modify roles.", ephemeral=True)
    except discord.HTTPException as e:
        await log_error(guild, "Verify command failed: Discord API error.", error=e, interaction=interaction)
        await interaction.followup.send("❌ Failed: An error occurred while communicating with Discord.", ephemeral=True)
    except Exception as e:
        await log_error(guild, "Unexpected error during /verify command.", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)

# --- Unverify Command ---
@tree.command(name="unverify", description="Revert a user to Unverified status (adds Unverified, removes Verified).")
@app_commands.describe(user="The user to unverify.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def unverify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    # Fetch roles by ID
    role_to_add = guild.get_role(REMOVE_ROLE_ID) # Add "Unverified"
    role_to_remove = guild.get_role(ADD_ROLE_ID_VERIFY) # Remove "Verified"

    # Check if roles exist - Crucial for this command to function
    missing_roles = []
    if REMOVE_ROLE_ID and not role_to_add: missing_roles.append(f"Unverified Role (ID: {REMOVE_ROLE_ID})")
    if ADD_ROLE_ID_VERIFY and not role_to_remove: missing_roles.append(f"Verified Role (ID: {ADD_ROLE_ID_VERIFY})")
    if missing_roles:
        await interaction.response.send_message(f"❌ Setup Error: The following role(s) could not be found: {', '.join(missing_roles)}. Please contact an admin.", ephemeral=True)
        await log_error(guild, f"Unverify command failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return

    # Ensure the role we need to add ("Unverified") exists before proceeding
    if not role_to_add:
         await interaction.response.send_message(f"❌ Setup Error: Unverified Role (ID: {REMOVE_ROLE_ID}) not found. Cannot unverify.", ephemeral=True)
         return


    # Hierarchy check (Corrected - using .position)
    bot_member = guild.me
    if bot_member.top_role.position <= user.top_role.position \
       or bot_member.top_role.position <= role_to_add.position \
       or (role_to_remove and bot_member.top_role.position <= role_to_remove.position):
         await interaction.response.send_message("❌ Hierarchy Error: I cannot manage roles for this user or the roles involved (my top role is not high enough).", ephemeral=True)
         await log_error(guild, f"Unverify command failed: Bot hierarchy too low for user {user.mention} or roles.", interaction=interaction)
         return

    # Check invoker hierarchy
    if interaction.user.top_role <= user.top_role and interaction.user.id != guild.owner_id:
         await interaction.response.send_message("❌ Hierarchy Error: You cannot manage roles for this user.", ephemeral=True)
         return


    await interaction.response.defer(thinking=True, ephemeral=True) # Defer privately

    actions_taken = []
    reason = f"Unverified by {interaction.user} (ID: {interaction.user.id})"
    modified = False

    try:
        # Check current state
        has_unverified = role_to_add in user.roles
        has_verified = role_to_remove and role_to_remove in user.roles # Check only if role_to_remove exists

        if has_unverified and not has_verified:
             await interaction.followup.send(f"ℹ️ {user.mention} is already in the 'Unverified' state (has Unverified, lacks Verified).", ephemeral=True)
             return

        # Prepare modifications
        roles_to_add_list = []
        roles_to_remove_list = []

        if has_verified: # role_to_remove is guaranteed to exist here if has_verified is True
            roles_to_remove_list.append(role_to_remove)
            actions_taken.append(f"➖ Removed `{role_to_remove.name}`")
            modified = True
        if not has_unverified:
            roles_to_add_list.append(role_to_add) # role_to_add is guaranteed to exist by check above
            actions_taken.append(f"➕ Added `{role_to_add.name}`")
            modified = True

        # Apply modifications
        if modified:
            # Using add/remove_roles is generally safer
            if roles_to_add_list:
                 await user.add_roles(*roles_to_add_list, reason=reason)
            if roles_to_remove_list:
                 await user.remove_roles(*roles_to_remove_list, reason=reason)

            await log_info(guild, f"`{interaction.user}` unverified {user.mention}. Actions: {', '.join(actions_taken)}.")
            # Send private confirmation
            await interaction.followup.send(f"✅ Successfully unverified {user.mention}.", ephemeral=True)
             # Send public notification
            public_embed = create_embed(f"↩️ **{user.display_name}** has been unverified.\n" + "\n".join(actions_taken), discord.Color.orange())
            try:
                # Ensure channel is text channel before sending
                 if isinstance(interaction.channel, discord.TextChannel):
                    await interaction.channel.send(embed=public_embed)
                 else:
                     await log_info(guild, f"Skipped public unverify notification for {user.mention} (command used outside text channel).")
            except (discord.Forbidden, discord.HTTPException) as e:
                await log_error(guild, "Failed to send public unverify notification", error=e, interaction=interaction)
        else:
            await interaction.followup.send("ℹ️ No role changes were needed.", ephemeral=True)

    except discord.Forbidden:
        await log_error(guild, "Unverify command failed: Bot lacks permissions (Forbidden).", interaction=interaction)
        await interaction.followup.send("❌ Failed: I don't have the necessary permissions to modify roles.", ephemeral=True)
    except discord.HTTPException as e:
        await log_error(guild, "Unverify command failed: Discord API error.", error=e, interaction=interaction)
        await interaction.followup.send("❌ Failed: An error occurred while communicating with Discord.", ephemeral=True)
    except Exception as e:
        await log_error(guild, "Unexpected error during /unverify command.", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)


# --- HC Verify Command ---
@tree.command(name="hcverify", description="Verify user into HC, store IGN, set nickname.")
@app_commands.describe(user="User to HC verify.", ingame_name="User's Florr IGN (will be used as nickname).")
@app_commands.checks.has_permissions(manage_roles=True, manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return
    if not supabase:
        await interaction.response.send_message("❌ Database connection is unavailable. Cannot store IGN.", ephemeral=True)
        await log_error(guild, "HCVerify failed: Supabase client not available.", interaction=interaction)
        return

    # Defer publicly as the final message is usually public
    # Check defer state *before* deferring
    if not interaction.response.is_done():
         await interaction.response.defer(thinking=True, ephemeral=False)
    else:
         # If already deferred (e.g., by a previous check), log or proceed carefully
         print(f"Warning: Interaction {interaction.id} was already responded to before hcverify deferral.")
         # Decide if you need to followup.send or just continue processing

    # Fetch roles
    role_unverified = guild.get_role(REMOVE_ROLE_ID)
    role_verified = guild.get_role(ADD_ROLE_ID_VERIFY)
    role_hc = guild.get_role(ADD_ROLE_ID_HC)

    # Check if roles exist
    missing_roles = []
    if not role_unverified: missing_roles.append(f"Unverified (ID: {REMOVE_ROLE_ID})")
    if not role_verified: missing_roles.append(f"Verified (ID: {ADD_ROLE_ID_VERIFY})")
    if not role_hc: missing_roles.append(f"HC (ID: {ADD_ROLE_ID_HC})")
    if missing_roles:
        # Use followup if deferred, otherwise response
        send_func = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send_func(f"❌ Setup Error: Missing roles: {', '.join(missing_roles)}. Contact admin.", ephemeral=True)
        await log_error(guild, f"HCVerify failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return

    # Hierarchy checks (Corrected - using .position and inside the function)
    bot_member = guild.me
    send_func = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message

    # Compare position integers, not Role objects directly with integers
    if bot_member.top_role.position <= user.top_role.position \
       or bot_member.top_role.position <= role_verified.position \
       or bot_member.top_role.position <= role_hc.position \
       or (role_unverified and bot_member.top_role.position <= role_unverified.position):
         await send_func("❌ Hierarchy Error: I cannot manage roles for this user or the required roles (my top role is not high enough).", ephemeral=True)
         await log_error(guild, f"HCVerify failed: Bot hierarchy too low for {user.mention} or roles.", interaction=interaction)
         return

    # Check invoker hierarchy (remains the same logic)
    if interaction.user.top_role <= user.top_role and interaction.user.id != guild.owner_id:
         await send_func("❌ Hierarchy Error: You cannot manage roles/nicknames for this user.", ephemeral=True)
         return

    # Check bot hierarchy for nickname (using .position for consistency)
    if bot_member.top_role.position <= user.top_role.position:
         await send_func("❌ Hierarchy Error: I cannot change the nickname for this user (my top role is not high enough).", ephemeral=True)
         await log_error(guild, f"HCVerify failed: Bot hierarchy too low to change nick for {user.mention}.", interaction=interaction)
         return


    log_summary = []
    result_summary = []
    errors_occurred = False
    reason = f"HC Verified by {interaction.user} (ID: {interaction.user.id})"

    # --- Role Management ---
    roles_to_add = []
    roles_to_remove = []
    needs_role_update = False
    original_hc_status = role_hc in user.roles # Check if user already had HC role

    if role_unverified and role_unverified in user.roles:
        roles_to_remove.append(role_unverified)
        log_summary.append("Will remove Unverified role")
        needs_role_update = True
    if role_verified not in user.roles:
        roles_to_add.append(role_verified)
        log_summary.append("Will add Verified role")
        needs_role_update = True
    if not original_hc_status: # Only add HC if they don't have it
        roles_to_add.append(role_hc)
        log_summary.append("Will add HC role")
        needs_role_update = True

    if needs_role_update:
        try:
            # Use add_roles and remove_roles for clarity and atomicity if possible
            # Check if user object needs refresh before role modification if significant time passed
            # current_user_roles = await guild.fetch_member(user.id).roles # Might be overkill usually
            if roles_to_add: await user.add_roles(*roles_to_add, reason=reason)
            if roles_to_remove: await user.remove_roles(*roles_to_remove, reason=reason)
            added_names = ', '.join(f"`{r.name}`" for r in roles_to_add)
            removed_names = ', '.join(f"`{r.name}`" for r in roles_to_remove)
            if added_names: result_summary.append(f"➕ Roles Added: {added_names}")
            if removed_names: result_summary.append(f"➖ Roles Removed: {removed_names}")
            log_summary.append("Role update successful")
        except (discord.Forbidden, discord.HTTPException) as e:
            errors_occurred = True
            err_msg = "Failed to update roles (Permissions)" if isinstance(e, discord.Forbidden) else "Failed to update roles (API Error)"
            result_summary.append(f"⚠️ {err_msg}")
            log_summary.append(f"Role update failed: {type(e).__name__}")
            await log_error(guild, "HCVerify role update failed", error=e, interaction=interaction)
        except Exception as e:
             errors_occurred = True
             result_summary.append("⚠️ Failed to update roles (Unknown Error)")
             log_summary.append(f"Role update failed unexpectedly: {type(e).__name__}")
             await log_error(guild, "HCVerify unexpected role update error", error=e, interaction=interaction)

    elif not needs_role_update:
        result_summary.append("ℹ️ Roles already correct.")
        log_summary.append("No role changes needed")

    # --- Database Update ---
    db_success = False
    try:
        ign_to_store = ingame_name.strip()
        if not ign_to_store:
             raise ValueError("In-game name cannot be empty after stripping whitespace.")

        await run_supabase_sync(
            lambda: supabase.table("hc_members")
                            .upsert({
                                "discord_id": str(user.id),
                                "discord_name": f"{user.name}#{user.discriminator}" if user.discriminator != '0' else user.name,
                                "ingame_name": ign_to_store
                            }, on_conflict="discord_id")
                            .execute()
        )
        result_summary.append(f"💾 IGN Stored: `{discord.utils.escape_markdown(ign_to_store)}`")
        log_summary.append("Supabase upsert successful")
        db_success = True
    except ValueError as e: # Catch empty IGN specifically
         errors_occurred = True
         result_summary.append(f"⚠️ DB Error: {e}")
         log_summary.append(f"Supabase upsert failed: {e}")
         await log_error(guild, "HCVerify DB upsert failed", error=e, interaction=interaction)
    except Exception as e:
        errors_occurred = True
        result_summary.append("⚠️ Database Error: Failed to store IGN.")
        log_summary.append(f"Supabase upsert failed: {type(e).__name__}")
        await log_error(guild, "HCVerify DB upsert failed", error=e, interaction=interaction)

    # --- Nickname Management ---
    nick_success = False
    nickname_to_set = ingame_name.strip()[:32] # Max 32 chars for Discord nicknames
    truncated = len(ingame_name.strip()) > 32

    if not nickname_to_set:
        result_summary.append("⚠️ Nickname Error: IGN is empty, cannot set nickname.")
        log_summary.append("Nickname skipped (empty IGN)")
        errors_occurred = True # Consider this an error state
    elif user.nick == nickname_to_set:
        result_summary.append(f"🏷️ Nickname already set: `{discord.utils.escape_markdown(nickname_to_set)}`")
        log_summary.append("Nickname already correct")
        nick_success = True # Still counts as success if already correct
    else:
        try:
            await user.edit(nick=nickname_to_set, reason=reason)
            nick_msg = f"🏷️ Nickname Set: `{discord.utils.escape_markdown(nickname_to_set)}`"
            if truncated: nick_msg += " (truncated)"
            result_summary.append(nick_msg)
            log_summary.append(f"Nickname set{' (truncated)' if truncated else ''}")
            nick_success = True
        except discord.Forbidden:
            errors_occurred = True
            result_summary.append("⚠️ Nickname Error: Failed to set nickname (Permissions).")
            log_summary.append("Nickname change failed: Forbidden")
            await log_error(guild, "HCVerify nickname change failed (Forbidden)", interaction=interaction)
        except discord.HTTPException as e:
             errors_occurred = True
             result_summary.append("⚠️ Nickname Error: Failed to set nickname (API Error).")
             log_summary.append(f"Nickname change failed: HTTPException {e.status}")
             await log_error(guild, "HCVerify nickname change failed (HTTPException)", error=e, interaction=interaction)
        except Exception as e:
            errors_occurred = True
            result_summary.append("⚠️ Nickname Error: Failed to set nickname (Unknown Error).")
            log_summary.append(f"Nickname change failed unexpectedly: {type(e).__name__}")
            await log_error(guild, "HCVerify unexpected nickname change error", error=e, interaction=interaction)


    # --- Final Response & Logging ---
    final_color = discord.Color.orange() if errors_occurred else discord.Color.green()
    final_title = f"{'✅' if not errors_occurred else '⚠️'} HC Verified: {user.display_name}"
    if errors_occurred: final_title += " (with issues)"

    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    # Use followup.send as we deferred earlier
    try:
        await interaction.followup.send(embed=final_embed)
    except (discord.NotFound, discord.HTTPException) as e:
         await log_error(guild, "HCVerify failed to send final followup message", error=e, interaction=interaction)

    # Log the overall operation
    await log_info(guild, f"`{interaction.user}` initiated HCVerify for {user.mention}. Summary: {'; '.join(log_summary)}.")

    # Update static list if HC role was newly added OR if it already existed and DB update was successful
    if (role_hc in roles_to_add) or (original_hc_status and db_success):
         print(f"HCVerify: Triggering list update for {user.name}.") # Debug print
         # Add a small delay before updating list to allow Discord/DB changes to potentially propagate
         await asyncio.sleep(1.0)
         await update_hc_member_list(guild)


# --- Un-HC-Verify Command ---
@tree.command(name="unhcverify", description="Remove HC role and reset nickname for a user.")
@app_commands.describe(user="The user to remove from HC.")
@app_commands.checks.has_permissions(manage_roles=True, manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def unhcverify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    # Check defer state *before* deferring
    if not interaction.response.is_done():
         await interaction.response.defer(thinking=True, ephemeral=False)
    else:
         print(f"Warning: Interaction {interaction.id} was already responded to before unhcverify deferral.")

    # Fetch HC role
    role_hc = guild.get_role(ADD_ROLE_ID_HC)
    if not role_hc:
        send_func = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send_func(f"❌ Setup Error: HC Role (ID: {ADD_ROLE_ID_HC}) not found. Contact admin.", ephemeral=True)
        await log_error(guild, f"UnHCVerify failed: HC role not found.", interaction=interaction)
        return

    # Hierarchy checks (Corrected - using .position)
    bot_member = guild.me
    send_func = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message

    # Check bot hierarchy for managing the HC role itself
    if bot_member.top_role.position <= user.top_role.position \
       or bot_member.top_role.position <= role_hc.position:
         await send_func("❌ Hierarchy Error: I cannot manage the HC role for this user (my top role is not high enough).", ephemeral=True)
         await log_error(guild, f"UnHCVerify failed: Bot hierarchy too low for {user.mention} or HC role.", interaction=interaction)
         return

    # Check invoker hierarchy
    if interaction.user.top_role <= user.top_role and interaction.user.id != guild.owner_id:
         await send_func("❌ Hierarchy Error: You cannot manage roles/nicknames for this user.", ephemeral=True)
         return

    # Separate check for nickname hierarchy (using .position) - only warn if nick needs changing
    nick_reset_needed = user.nick is not None
    if nick_reset_needed and bot_member.top_role.position <= user.top_role.position:
         # Log the error but proceed with role removal if possible
         await log_error(guild, f"UnHCVerify warning: Bot hierarchy too low to reset nick for {user.mention}, but attempting role removal.", interaction=interaction)
         # Optionally inform user nickname won't be reset:
         # await send_func("⚠️ Warning: My role is too low to reset this user's nickname, but I will attempt to remove the HC role.", ephemeral=True)


    log_summary = []
    result_summary = []
    errors_occurred = False
    reason = f"Un-HC-Verified by {interaction.user} (ID: {interaction.user.id})"
    role_was_removed = False

    # --- Role Removal ---
    if role_hc not in user.roles:
        await send_func(f"ℹ️ {user.mention} does not have the `{role_hc.name}` role.", ephemeral=True)
        # No need to proceed further if they don't have the role
        return
    else:
        try:
            await user.remove_roles(role_hc, reason=reason)
            result_summary.append(f"➖ Role Removed: `{role_hc.name}`")
            log_summary.append("HC role removed successfully")
            role_was_removed = True
        except discord.Forbidden:
            errors_occurred = True
            result_summary.append("⚠️ Role Error: Failed to remove HC role (Permissions).")
            log_summary.append("HC role removal failed: Forbidden")
            await log_error(guild, "UnHCVerify role removal failed (Forbidden)", interaction=interaction)
        except discord.HTTPException as e:
            errors_occurred = True
            result_summary.append("⚠️ Role Error: Failed to remove HC role (API Error).")
            log_summary.append(f"HC role removal failed: HTTPException {e.status}")
            await log_error(guild, "UnHCVerify role removal failed (HTTPException)", error=e, interaction=interaction)
        except Exception as e:
             errors_occurred = True
             result_summary.append("⚠️ Role Error: Failed to remove HC role (Unknown Error).")
             log_summary.append(f"HC role removal failed unexpectedly: {type(e).__name__}")
             await log_error(guild, "UnHCVerify unexpected role removal error", error=e, interaction=interaction)


    # --- Nickname Reset ---
    # Only attempt reset if the user actually has a nickname AND bot hierarchy allows it
    if nick_reset_needed:
        if bot_member.top_role.position > user.top_role.position: # Check hierarchy again explicitly
             try:
                 await user.edit(nick=None, reason=reason)
                 result_summary.append("🏷️ Nickname Reset")
                 log_summary.append("Nickname reset successfully")
             except discord.Forbidden: # Should be caught by hierarchy but check again
                 errors_occurred = True
                 result_summary.append("⚠️ Nickname Error: Failed to reset nickname (Permissions).")
                 log_summary.append("Nickname reset failed: Forbidden")
                 await log_error(guild, "UnHCVerify nickname reset failed (Forbidden)", interaction=interaction)
             except discord.HTTPException as e:
                  errors_occurred = True
                  result_summary.append("⚠️ Nickname Error: Failed to reset nickname (API Error).")
                  log_summary.append(f"Nickname reset failed: HTTPException {e.status}")
                  await log_error(guild, "UnHCVerify nickname reset failed (HTTPException)", error=e, interaction=interaction)
             except Exception as e:
                 errors_occurred = True
                 result_summary.append("⚠️ Nickname Error: Failed to reset nickname (Unknown Error).")
                 log_summary.append(f"Nickname reset failed unexpectedly: {type(e).__name__}")
                 await log_error(guild, "UnHCVerify unexpected nickname reset error", error=e, interaction=interaction)
        else:
            # Hierarchy check already failed, report it if not already done implicitly
            result_summary.append("⚠️ Nickname Error: Skipped reset (Bot hierarchy too low).")
            log_summary.append("Nickname reset skipped (Hierarchy)")
            errors_occurred = True # Indicate an issue occurred
    else:
        result_summary.append("🏷️ No nickname to reset.")
        log_summary.append("No nickname to reset")

    # --- Final Response & Logging ---
    final_color = discord.Color.orange() if errors_occurred else discord.Color.green()
    final_title = f"{'✅' if not errors_occurred else '⚠️'} Un-HC-Verified: {user.display_name}"
    if errors_occurred: final_title += " (with issues)"

    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    try:
        await interaction.followup.send(embed=final_embed)
    except (discord.NotFound, discord.HTTPException) as e:
        await log_error(guild, "UnHCVerify failed to send final followup message", error=e, interaction=interaction)

    # Log the overall operation
    await log_info(guild, f"`{interaction.user}` initiated UnHCVerify for {user.mention}. Summary: {'; '.join(log_summary)}.")

    # Update static list if the role was successfully removed
    if role_was_removed:
        print(f"UnHCVerify: Triggering list update for {user.name}.") # Debug print
        # Add a small delay
        await asyncio.sleep(1.0)
        await update_hc_member_list(guild)


# --- HC Members Interactive List ---
@tree.command(name="hcmembers", description="Show interactive list of [HC1] members (username#tag ➔ IGN).")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    # Check channel permissions
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        allowed_mentions = []
        for channel_id in ALLOWED_CHANNEL_IDS:
            channel = guild.get_channel(channel_id)
            if channel:
                allowed_mentions.append(channel.mention)
            else:
                 allowed_mentions.append(f"ID:{channel_id}") # Fallback if channel not found

        await interaction.response.send_message(f"❌ This command can only be used in the following channel(s): {', '.join(allowed_mentions) or 'None configured'}", ephemeral=True)
        return

    # Defer publicly as the list is public
    await interaction.response.defer(thinking=True, ephemeral=False)

    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Database connection is unavailable.", discord.Color.red()))
        await log_error(guild, "/hcmembers failed: Supabase client not available.", interaction=interaction)
        return

    try:
        data, total = await fetch_hc_member_data(guild)

        if not data:
            hc_role = guild.get_role(ADD_ROLE_ID_HC)
            role_name = f"`{hc_role.name}`" if hc_role else f"the configured HC role (ID: {ADD_ROLE_ID_HC})"
            description = f"No members found with {role_name}."
            if total > 0: # This might indicate a DB fetch issue despite members having the role
                 description += "\n(Note: Some members have the role, but their data couldn't be fetched.)"
            embed = create_embed(title=HC_LIST_EMBED_TITLE, description=description, color=discord.Color.orange())
            await interaction.followup.send(embed=embed)
            return

        # Create the view and initial embed
        view = HCPagesView(data, total)
        initial_embed = view.create_page_embed()

        # Send the initial message and store it in the view
        message = await interaction.followup.send(embed=initial_embed, view=view)
        view.message = message # Assign the sent message to the view

        await log_info(guild, f"/hcmembers command used by `{interaction.user}` in {interaction.channel.mention if interaction.channel else 'Unknown Channel'}.")

    except ConnectionError as e: # Specific Supabase connection error
         await log_error(guild, "/hcmembers DB connection error", error=e, interaction=interaction)
         await interaction.followup.send(embed=create_embed("❌ Error connecting to the database.", discord.Color.red()))
    except APIError as e: # Specific Supabase API error
         await log_error(guild, "/hcmembers Supabase API error", error=e, interaction=interaction)
         await interaction.followup.send(embed=create_embed("❌ Error retrieving data from the database.", discord.Color.red()))
    except Exception as e:
        await log_error(guild, "Unhandled error during /hcmembers command", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ An unexpected error occurred while fetching the member list.", discord.Color.red()))


# --- Refresh Static List Command ---
@tree.command(name="refresh", description="Manually refresh static [HC1] list (username#tag ➔ IGN).")
@app_commands.checks.has_permissions(manage_roles=True) # Or a more specific permission if desired
async def refresh(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    # Defer privately as it's just a confirmation message
    await interaction.response.defer(thinking=True, ephemeral=True)

    if not supabase:
        await interaction.followup.send("❌ Database connection is unavailable.", ephemeral=True)
        await log_error(guild, "/refresh failed: Supabase client not available.", interaction=interaction)
        return

    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(list_channel, discord.TextChannel):
        await interaction.followup.send(f"❌ Configuration Error: The static list channel (ID: {HC_MEMBER_LIST_CHANNEL_ID}) is invalid or not found.", ephemeral=True)
        await log_error(guild, f"/refresh failed: Static list channel invalid.", interaction=interaction)
        return

    try:
        await log_info(guild, f"Manual static list refresh initiated by `{interaction.user}`.")
        # Run the update function (it handles its own internal logging)
        await update_hc_member_list(guild)
        # Confirm initiation to the user
        await interaction.followup.send(f"✅ Refresh initiated for the static HC member list in {list_channel.mention}. Please allow a moment for it to update.", ephemeral=True)
    except Exception as e:
        # Catch any unexpected errors during the refresh *initiation* process
        await log_error(guild, "Error initiating /refresh command", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred while trying to start the refresh.", ephemeral=True)


# --- Bulk Update Command ---
@tree.command(name="bulkupdate", description="Open form to bulk update IGNs (username#tag ➔ IGN).")
@app_commands.checks.has_permissions(manage_roles=True) # Requires permissions to potentially trigger list updates etc.
async def bulkupdate(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    try:
        # Send the modal to the user
        await interaction.response.send_modal(BulkUpdateModal())
        # Log that the modal was opened (on_submit handles results logging)
        await log_info(interaction.guild, f"`{interaction.user}` opened the bulk IGN update modal.")
    except Exception as e:
        await log_error(interaction.guild, "Failed to open BulkUpdateModal", error=e, interaction=interaction)
        # Try to send an error message if the modal failed to send
        if not interaction.response.is_done():
            try:
                await interaction.response.send_message("❌ There was an error opening the bulk update form.", ephemeral=True)
            except Exception:
                pass # Avoid error loops if sending response also fails


# --- Sync Nicknames Command ---
@tree.command(name="syncnicknames", description="Sync all HC members' nicknames with their stored IGNs.")
@app_commands.checks.has_permissions(manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_nicknames=True)
async def syncnicknames(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    # Defer privately, the final result will be shown ephemerally
    await interaction.response.defer(thinking=True, ephemeral=True)

    if not supabase:
        await interaction.edit_original_response(content="❌ Database connection is unavailable.")
        await log_error(guild, "/syncnicknames failed: Supabase client not available.", interaction=interaction)
        return

    # Get HC Role
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await interaction.edit_original_response(content=f"❌ Configuration Error: HC Role (ID: {ADD_ROLE_ID_HC}) not found.")
        await log_error(guild, f"/syncnicknames failed: HC role not found.", interaction=interaction)
        return

    start_time = discord.utils.utcnow()
    await log_info(guild, f"Nickname sync initiated by `{interaction.user}`.")
    await interaction.edit_original_response(content="<a:loading:12345> Fetching member and IGN data...") # Use a loading emoji if available

    # --- Data Fetching ---
    ign_data = {}
    fetch_error = None
    try:
        resp = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").execute())
        if resp and hasattr(resp, 'data') and resp.data:
            ign_data = {item['discord_id']: item['ingame_name']
                        for item in resp.data
                        if item.get('discord_id') and item.get('ingame_name')} # Ensure both ID and IGN exist
            print(f"SyncNick ({guild.name}): Fetched {len(ign_data)} IGN records from Supabase.")
        else:
            print(f"SyncNick ({guild.name}): No IGN data returned from Supabase.")
            # Not necessarily an error, maybe the table is empty

    except Exception as e:
        fetch_error = e
        await log_error(guild, "SyncNick: Supabase data fetch failed", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Failed to fetch IGN data from the database.")
        return

    # Get HC members
    try:
        if not guild.chunked: await guild.chunk(cache=True) # Ensure members are cached
        hc_members = [m for m in guild.members if hc_role in m.roles and not m.bot]
        total_hc_members = len(hc_members)
        print(f"SyncNick ({guild.name}): Found {total_hc_members} members with the HC role.")
    except Exception as e:
        await log_error(guild, "SyncNick: Failed to fetch/chunk guild members", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Failed to retrieve member list from the server.")
        return


    if total_hc_members == 0:
        await interaction.edit_original_response(content=f"ℹ️ No members found with the `{hc_role.name}` role. Nothing to sync.")
        return

    await interaction.edit_original_response(content=f"<a:loading:12345> Syncing nicknames for {total_hc_members} HC members...")

    # --- Syncing Logic ---
    counts = {'processed': 0, 'updated': 0, 'skipped_match': 0, 'skipped_no_ign': 0, 'skipped_empty_ign': 0, 'fail_hierarchy': 0, 'fail_forbidden': 0, 'fail_other': 0}
    bot_top_role = guild.me.top_role
    last_progress_update_time = asyncio.get_event_loop().time()

    for idx, member in enumerate(hc_members):
        counts['processed'] += 1
        member_id_str = str(member.id)

        # Hierarchy Check (Bot vs Member)
        if bot_top_role <= member.top_role and member.id != guild.owner_id:
            counts['fail_hierarchy'] += 1
            continue # Skip this member

        # Get Stored IGN
        stored_ign = ign_data.get(member_id_str)
        if not stored_ign:
            counts['skipped_no_ign'] += 1
            continue # Skip if no IGN stored in DB

        # Validate IGN and prepare target nickname
        target_nickname = stored_ign.strip()
        if not target_nickname:
             counts['skipped_empty_ign'] += 1
             continue # Skip if stored IGN is empty/whitespace

        target_nickname = target_nickname[:32] # Truncate to Discord limit

        # Check if update is needed
        if member.nick == target_nickname:
            counts['skipped_match'] += 1
            continue # Skip if nickname already matches

        # Attempt Nickname Update
        try:
            await member.edit(nick=target_nickname, reason=f"Nickname Sync initiated by {interaction.user.id}")
            counts['updated'] += 1
            await asyncio.sleep(0.2) # Small delay to avoid hitting rate limits aggressively
        except discord.Forbidden:
            counts['fail_forbidden'] += 1
            # Log first few forbidden errors for diagnosis
            if counts['fail_forbidden'] <= 3:
                 await log_error(guild, f"SyncNick: Forbidden error updating nick for {member.mention} (`{member.id}`)", interaction=interaction, embed=None) # Don't need full embed usually
        except discord.HTTPException as e:
             counts['fail_other'] += 1
             # Log first few other HTTP errors
             if counts['fail_other'] <= 3:
                  await log_error(guild, f"SyncNick: HTTP error updating nick for {member.mention} (`{member.id}`)", error=e, interaction=interaction, embed=None)
        except Exception as e:
            counts['fail_other'] += 1
            # Log first few unexpected errors
            if counts['fail_other'] <= 3:
                 await log_error(guild, f"SyncNick: Unexpected error updating nick for {member.mention} (`{member.id}`)", error=e, interaction=interaction, embed=None)


        # Progress Update (every 5 seconds or every 50 members)
        current_time = asyncio.get_event_loop().time()
        if current_time - last_progress_update_time > 5.0 or counts['processed'] % 50 == 0:
            try:
                progress_msg = f"<a:loading:12345> Syncing nicknames... ({counts['processed']}/{total_hc_members})"
                await interaction.edit_original_response(content=progress_msg)
                last_progress_update_time = current_time
            except (discord.NotFound, discord.HTTPException):
                 print(f"SyncNick ({guild.name}): Failed to update progress message (Interaction likely expired or API error).")
                 break # Stop trying to update progress if interaction fails

    # --- Final Summary ---
    end_time = discord.utils.utcnow()
    duration = (end_time - start_time).total_seconds()
    summary_embed = discord.Embed(title="✅ Nickname Sync Complete!", color=NERDY_YELLOW, timestamp=end_time)

    summary_lines = [
        f"⏱️ **Duration:** {duration:.2f} seconds",
        f"👥 **Total HC Members:** {total_hc_members}",
        f"🔄 **Processed:** {counts['processed']}",
        f"✅ **Nicknames Updated:** {counts['updated']}",
        f"ℹ️ **Skipped (Already Match):** {counts['skipped_match']}",
        f"❓ **Skipped (No IGN in DB):** {counts['skipped_no_ign']}",
        f"❓ **Skipped (Empty IGN in DB):** {counts['skipped_empty_ign']}",
        f"❌ **Failed (Hierarchy):** {counts['fail_hierarchy']}",
        f"❌ **Failed (Permissions):** {counts['fail_forbidden']}",
        f"❌ **Failed (Other Errors):** {counts['fail_other']}"
    ]
    summary_embed.description = "\n".join(summary_lines)

    try:
        await interaction.edit_original_response(content=None, embed=summary_embed)
    except (discord.NotFound, discord.HTTPException):
        print(f"SyncNick ({guild.name}): Failed to send final summary (Interaction likely expired or API error).")
        # Optionally try sending as a new followup message
        try:
             await interaction.followup.send(embed=summary_embed, ephemeral=True)
        except Exception as e:
             print(f"SyncNick ({guild.name}): Failed to send final summary as followup: {e}")

    # Log final summary to info channel
    log_embed = discord.Embed(title="Nickname Sync Finished", description="\n".join(summary_lines), color=NERDY_YELLOW)
    log_embed.set_footer(text=f"Initiated by {interaction.user} ({interaction.user.id})")
    await log_info(guild, "", embed=log_embed)


# --- Wither Command ---
@tree.command(name="wither", description="Temporarily remove all roles from a user (except @everyone).")
@app_commands.describe(
    user="The user to apply the wither effect to.",
    time="Duration in minutes (0.1 to 10, default is 2 minutes)."
)
async def wither(interaction: discord.Interaction, user: discord.Member, time: app_commands.Range[float, 0.1, 10.0] = 2.0):
    guild = interaction.guild
    invoker = interaction.user
    if not guild: # Should be impossible for guild command
        await interaction.response.send_message("Cannot use this command here.", ephemeral=True)
        return

    bot_member = guild.me

    # --- Pre-Checks ---
    async def fail_check(log_reason: str, user_message: str, log_error_details: Optional[Exception] = None):
        # Ensure interaction hasn't already been responded to before sending error
        send_func = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        try:
            await send_func(embed=create_embed(user_message, discord.Color.red()), ephemeral=True)
        except Exception as e:
            print(f"Wither Check Fail: Could not send message '{user_message}'. Error: {e}")
        # Log after attempting to notify user
        await log_error(guild, f"Wither check failed ({invoker.name} -> {user.name}): {log_reason}", error=log_error_details, interaction=interaction)


    # 1. Permission Check (Invoker)
    if invoker.id not in ALLOWED_WITHER_IDS:
        # Need to check response state before sending
        if not interaction.response.is_done(): await interaction.response.defer(ephemeral=True) # Defer first if not done
        await fail_check("Invoker permission denied.", "❌ You do not have permission to use this command.")
        return

    # Defer early if possible, checks below might take time
    if not interaction.response.is_done():
        # Defer publicly as the main success message is public
        await interaction.response.defer(thinking=True, ephemeral=False)

    # 2. Target Checks
    if user.id == invoker.id:
        await fail_check("Target is self.", "🤨 You cannot wither yourself.")
        return
    if user.id == SELF_PROTECTED_ID and invoker.id != SELF_PROTECTED_ID:
        await fail_check("Target is protected.", "😨 You cannot wither the bot owner!")
        return
    if user.id == BOT_ID:
        await fail_check("Target is bot.", "😭 You cannot wither me!")
        return
    if user.bot:
        await fail_check("Target is another bot.", "🤖 Bots cannot be withered.")
        return
    if user.id == guild.owner_id and invoker.id != guild.owner_id:
        await fail_check("Target is guild owner.", "👑 The server owner cannot be withered (except by themselves).")
        return

    # 3. Hierarchy Checks (Corrected - using .position)
    if bot_member.top_role.position <= user.top_role.position:
        await fail_check("Bot hierarchy too low.", "❌ My role is not high enough to manage this user's roles.")
        return
    # Check if invoker can manage the target (unless invoker is owner)
    if invoker.id != guild.owner_id and invoker.top_role.position <= user.top_role.position: # Use .position for consistency
        await fail_check("Invoker hierarchy too low.", "❌ Your role is not high enough to wither this user.")
        return

    # --- Execution ---
    # Already deferred above if possible

    original_roles = [r for r in user.roles if r != guild.default_role] # Exclude @everyone

    if not original_roles:
        # Use followup as we should have deferred
        await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} has no roles (besides @everyone) to remove.", discord.Color.orange()), ephemeral=False) # Maybe make this public?
        return

    try:
        # Phase 1: Remove Roles
        # Validate duration is within reasonable bounds (Range check helps, but good practice)
        wither_duration_seconds = max(1, int(time * 60)) # Ensure at least 1 second
        max_seconds = int(MAX_WITHER_SECONDS) if MAX_WITHER_SECONDS else 600 # Use configured max or default
        wither_duration_seconds = min(wither_duration_seconds, max_seconds) # Cap duration
        actual_minutes = wither_duration_seconds / 60.0

        reason_wither = f"Withered by {invoker.name} ({invoker.id}) for {actual_minutes:.1f} minutes."

        # Ensure bot still has perms right before editing
        current_bot_perms = bot_member.guild_permissions
        if not current_bot_perms.manage_roles:
             await fail_check("Bot lost manage_roles perm.", "❌ I seem to have lost permission to manage roles just now. Aborting.")
             return

        await user.edit(roles=[], reason=reason_wither) # Empty list removes all roles except @everyone

        roles_removed_str = (', '.join(f"`{r.name}`" for r in original_roles))
        if len(roles_removed_str) > 1000: # Avoid exceeding embed limits
             roles_removed_str = roles_removed_str[:997] + "..."

        await interaction.followup.send(embed=create_embed(
            title="🌪️ Wither Cast! 🌪️",
            description=f"{user.mention} has been withered by {invoker.mention} for **{actual_minutes:.1f} minutes**!\n\n**Roles Removed:** {roles_removed_str}",
            color=discord.Color.dark_purple()
        ), ephemeral=False) # Send public message
        await log_info(guild, f"`{user.name}` (`{user.id}`) withered by `{invoker.name}` (`{invoker.id}`) for {actual_minutes:.1f}m. Roles removed: {', '.join(r.name for r in original_roles)}")

        # Phase 2: Wait
        await asyncio.sleep(wither_duration_seconds)

        # Phase 3: Restore Roles
        # Re-fetch member and bot objects in case state changed (e.g., permissions, user left)
        try:
            member_after = await guild.fetch_member(user.id)
            # Re-fetch bot member too, in case its roles changed
            bot_member_after = await guild.fetch_member(BOT_ID) if BOT_ID else guild.me

            reason_restore = f"Wither ended after {actual_minutes:.1f} minutes (invoked by {invoker.id})."

            # Check hierarchy again before restoring (using .position)
            if bot_member_after.top_role.position <= member_after.top_role.position:
                 await log_error(guild, f"Wither restore failed: Bot hierarchy too low for {member_after.mention}.", interaction=interaction)
                 # Try to notify in channel if possible
                 try: await interaction.channel.send(f"⚠️ Failed to restore roles for {member_after.mention} - bot hierarchy is now too low.")
                 except Exception: pass
                 return # Cannot restore

            # Check permissions again
            if not bot_member_after.guild_permissions.manage_roles:
                 await log_error(guild, f"Wither restore failed: Bot lost manage_roles perm for {member_after.mention}.", interaction=interaction)
                 try: await interaction.channel.send(f"⚠️ Failed to restore roles for {member_after.mention} - bot lost permissions.")
                 except Exception: pass
                 return # Cannot restore

            # Validate original roles still exist before adding them back
            valid_original_roles = []
            for r in original_roles:
                fetched_role = guild.get_role(r.id)
                if fetched_role:
                    valid_original_roles.append(fetched_role)

            if len(valid_original_roles) != len(original_roles):
                 deleted_count = len(original_roles) - len(valid_original_roles)
                 await log_info(guild, f"Wither restore notice: {deleted_count} original role(s) for {member_after.name} no longer exist. Restoring valid ones.")

            if not valid_original_roles:
                 await log_info(guild, f"Wither restore: No valid original roles left to restore for {member_after.name}.")
                 # Send a message indicating nothing was restored if needed
                 try: await interaction.channel.send(f"ℹ️ Wither ended for {member_after.mention}, but no original roles could be restored (they may have been deleted).")
                 except Exception: pass
                 return


            await member_after.edit(roles=valid_original_roles, reason=reason_restore)

            # Send confirmation of restore (use followup as original is done)
            # Check if channel is still accessible before sending followup
            if interaction.channel:
                try:
                    await interaction.followup.send(embed=create_embed(f"✨ {member_after.mention}'s roles have been restored!", color=NERDY_YELLOW), ephemeral=False) # Public confirmation
                except (discord.NotFound, discord.HTTPException) as e:
                     await log_error(guild, "Wither failed to send restore followup message", error=e, interaction=interaction)
            else:
                 await log_info(guild, f"Wither restore successful for {member_after.mention}, but couldn't send followup (channel unavailable).")

            await log_info(guild, f"Restored roles for `{member_after.name}` (`{member_after.id}`) after wither.")

        except discord.NotFound:
            # User left the server before roles could be restored
            await log_info(guild, f"Wither restore skipped: User `{user.name}` (`{user.id}`) left the server.")
            # Optionally notify the channel (check channel exists first)
            if interaction.channel:
                 try:
                     await interaction.channel.send(f"ℹ️ Wither ended, but {user.display_name} left the server before roles could be restored.")
                 except Exception: pass
        except discord.Forbidden:
            phase = "restore"
            await log_error(guild, f"Wither {phase} failed: Bot lacks permissions (Forbidden) for {user.name}.", interaction=interaction)
            if interaction.channel:
                 try: await interaction.channel.send(f"⚠️ Failed to {phase} roles for {user.display_name} - Permissions error.")
                 except Exception: pass
        except discord.HTTPException as e:
             phase = "restore"
             await log_error(guild, f"Wither {phase} failed: Discord API error for {user.name}.", error=e, interaction=interaction)
             if interaction.channel:
                  try: await interaction.channel.send(f"⚠️ Failed to {phase} roles for {user.display_name} - Discord API error.")
                  except Exception: pass
        except Exception as e:
            phase = "restore"
            await log_error(guild, f"Wither {phase} failed: Unexpected error for {user.name}.", error=e, interaction=interaction)
            if interaction.channel:
                 try: await interaction.channel.send(f"⚠️ Failed to {phase} roles for {user.display_name} - Unexpected error.")
                 except Exception: pass


    except discord.Forbidden:
         phase = "remove"
         # This implies the initial role removal failed
         await log_error(guild, f"Wither {phase} failed: Bot lacks permissions (Forbidden) for {user.name}.", interaction=interaction)
         # Edit the deferred response if possible (it should be a followup)
         try: await interaction.edit_original_response(content=f"❌ Failed to {phase} roles for {user.display_name} - Permissions error.", embed=None, view=None)
         except Exception: pass # Ignore if editing fails
    except discord.HTTPException as e:
         phase = "remove"
         await log_error(guild, f"Wither {phase} failed: Discord API error for {user.name}.", error=e, interaction=interaction)
         try: await interaction.edit_original_response(content=f"❌ Failed to {phase} roles for {user.display_name} - Discord API error.", embed=None, view=None)
         except Exception: pass
    except Exception as e:
        phase = "remove"
        await log_error(guild, f"Wither {phase} failed: Unexpected error for {user.name}.", error=e, interaction=interaction)
        try: await interaction.edit_original_response(content=f"❌ Failed to {phase} roles for {user.display_name} - Unexpected error.", embed=None, view=None)
        except Exception: pass


# --- Nerd Help Command ---
@tree.command(name="nerdhelp", description="Show the list of available bot commands.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🤓 Pingslave Bot Commands",
        description="Here are the commands I understand:",
        color=NERDY_YELLOW
    )

    # Get channel mentions dynamically
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    list_channel_mention = list_channel.mention if list_channel else f"Channel ID `{HC_MEMBER_LIST_CHANNEL_ID}` (Not Found?)"

    allowed_channel_mentions = []
    for ch_id in ALLOWED_CHANNEL_IDS:
        ch = guild.get_channel(ch_id)
        allowed_channel_mentions.append(ch.mention if ch else f"`ID:{ch_id}`")
    allowed_channels_str = ", ".join(allowed_channel_mentions) if allowed_channel_mentions else "`None Configured`"

    # Helper to add fields consistently
    def add_command_field(name: str, description: str, permissions: str = "Everyone", note: Optional[str] = None):
        value = f"{description}\n*Permissions:* `{permissions}`"
        if note:
            value += f"\n*Note:* {note}"
        embed.add_field(name=name, value=value, inline=False)

    # --- Verification Section ---
    embed.add_field(name="\u200B\n--- Verification & HC Management ---", value="\u200B", inline=False)
    add_command_field("`/verify <user>`", "Grants the `Verified` role and removes `Unverified`.", "Manage Roles")
    add_command_field("`/unverify <user>`", "Reverts a user to `Unverified` status (removes `Verified`, adds `Unverified`).", "Manage Roles")
    add_command_field("`/hcverify <user> <IGN>`", "Verifies user into HC, stores IGN, sets nickname, and updates the HC list.", "Manage Roles, Manage Nicknames")
    add_command_field("`/unhcverify <user>`", "Removes HC role, resets nickname, and updates the HC list.", "Manage Roles, Manage Nicknames")

    # --- HC List Section ---
    embed.add_field(name="\u200B\n--- [HC1] Member List ---", value="*Lists show `Discord Username#Tag ➔ In-Game Name`*", inline=False)
    add_command_field("`/hcmembers`", "Shows an interactive, paginated list of current HC members.", "Everyone", f"Can only be used in: {allowed_channels_str}.")
    add_command_field("`/refresh`", "Manually triggers an update of the static HC member list.", "Manage Roles", f"Updates the list posted in {list_channel_mention}.")

    # --- Utilities Section ---
    embed.add_field(name="\u200B\n--- Utilities ---", value="\u200B", inline=False)
    add_command_field("`/bulkupdate`", "Opens a form to paste multiple `Username#Tag ➔ IGN` entries for updating the database. Updates the HC list.", "Manage Roles")
    add_command_field("`/syncnicknames`", "Updates the Discord nicknames of all HC members to match their stored IGN (max 32 chars).", "Manage Nicknames")
    add_command_field("`/wither <user> [time]`", "Temporarily removes all roles from a user. Restores roles after the specified time.", "Special Permission (Bot Owner/Allowed IDs)", f"Duration: 0.1 to {MAX_WITHER_SECONDS / 60:.0f} minutes (default 2).")
    add_command_field("`/nerdhelp`", "Displays this help message.", "Everyone")

    # Footer and Thumbnail
    embed.set_footer(text="Bot by TheNerd | sweet_honey")
    if bot.user and bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)

    # Send the help message publicly in the channel it was invoked
    await interaction.response.send_message(embed=embed, ephemeral=False)


# --- Bot Startup ---
if __name__ == "__main__":
    print("--- Initializing Pingslave Bot ---")
    if not TOKEN:
        print("CRITICAL: DISCORD_BOT_TOKEN environment variable not found.")
    elif not supabase: # Checks if Supabase client was successfully created
        print("CRITICAL: Supabase client initialization failed. Check URL/Key and connection.")
    else:
        print("Discord Token and Supabase Client OK.")
        print("Starting Keep Alive Flask server...")
        keep_alive() # Start the Flask thread

        try:
            print("Attempting to start Discord Bot...")
            # Consider adding basic logging setup here if needed before bot.run
            # logging.basicConfig(level=logging.INFO)
            bot.run(TOKEN, log_handler=None) # Use default logging or configure as needed
        except discord.LoginFailure:
            print("CRITICAL: Discord Login Failed. Check if the token is valid and correct.")
        except discord.PrivilegedIntentsRequired:
            print("CRITICAL: Privileged Intents (likely Server Members Intent) are required but not enabled in the Discord Developer Portal.")
        except Exception as e:
            print(f"CRITICAL: An unexpected error occurred during bot execution: {e}")
            print(traceback.format_exc())

    print("--- Bot process has ended ---")