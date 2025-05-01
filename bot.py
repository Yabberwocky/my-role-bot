# -*- coding: utf-8 -*-
import os
import threading
import asyncio
import discord
from discord import app_commands
from typing import Dict, Optional
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button, button
from flask import Flask
from supabase import create_client, Client
from postgrest import APIError
import traceback
import math
from typing import Optional, Tuple, List, Dict # Keep this one, it's used more broadly
from dotenv import load_dotenv

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
# Key Features: /verify, /hcverify (stores IGN), static list updates, /hcmembers (interactive list), /syncnicknames, /wither, /bulkupdate, /nerdhelp.
# --- END CONTEXT ---

# --- Configuration ---
load_dotenv()  # harmless in production; only loads if a .env file exists
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
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
# Define bot instance here before using it in logging setup
bot = commands.Bot(command_prefix="!", intents=intents)
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
    # Check bot object exists before accessing bot.user
    if not bot or not bot.user: print(f"Log Error: Bot not ready, cannot get member object in {guild.name}."); return
    bot_member = guild.get_member(bot.user.id)
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
            if len(details) > 1024:
                 details = details[:1021] + "...```"
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
        # Check if children exist and have at least 2 elements before accessing
        if hasattr(self, 'children') and len(self.children) >= 2:
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
            if not interaction.response.is_done():
                 await interaction.response.edit_message(embed=embed, view=self)
            elif self.message:
                 await self.message.edit(embed=embed, view=self)
            else:
                 # Log this potential issue
                 print(f"Warning: edit_message called but interaction was done and self.message is None (Interaction ID: {interaction.id})")
                 await interaction.followup.send("Error updating view.", ephemeral=True)
        except discord.NotFound:
            print(f"Paginator edit fail: Original message {self.message.id if self.message else 'Unknown'} not found.")
            # Disable buttons on the view instance if message is gone
            for item in self.children:
                if isinstance(item, Button): item.disabled = True
            self.stop() # Stop the view as well
        except discord.HTTPException as e:
            # Log error with guild context if possible
            guild = interaction.guild or (self.message.guild if self.message else None)
            await log_error(guild, "Paginator edit fail (HTTP)", error=e, interaction=interaction)
        except Exception as e:
            guild = interaction.guild or (self.message.guild if self.message else None)
            await log_error(guild, "Paginator edit fail (General)", error=e, interaction=interaction)

    @button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="hc_prev_interactive", row=0)
    async def previous_button(self, interaction: discord.Interaction, b: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.edit_message(interaction)
        else:
            # Only defer if the interaction hasn't already been responded to or deferred
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer()
            except discord.InteractionResponded: pass # Already responded, do nothing
            except discord.NotFound: print("Previous Button: Interaction expired before defer.")
            except Exception as e: await log_error(interaction.guild, "Previous Button Defer Error", e, interaction)

    @button(label="Next", style=discord.ButtonStyle.blurple, custom_id="hc_next_interactive", row=0)
    async def next_button(self, interaction: discord.Interaction, b: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.edit_message(interaction)
        else:
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer()
            except discord.InteractionResponded: pass
            except discord.NotFound: print("Next Button: Interaction expired before defer.")
            except Exception as e: await log_error(interaction.guild, "Next Button Defer Error", e, interaction)

    async def on_timeout(self):
        if self.message:
            try:
                # Create a new view with disabled buttons before editing
                view_copy = View.from_message(self.message) # Get a representation of the current view state
                for item in view_copy.children:
                    if isinstance(item, Button):
                        item.disabled = True
                await self.message.edit(view=view_copy) # Edit with the disabled copy
                print(f"Paginator timeout: Disabled buttons on message {self.message.id}")
            except discord.NotFound: print(f"Paginator timeout edit fail: Message {self.message.id} not found.")
            except Exception as e:
                 guild = self.message.guild
                 await log_error(guild, f"Paginator timeout edit fail on message {self.message.id}", error=e)
        self.stop()


# --- Core HC List Logic ---
async def fetch_hc_member_data(guild: discord.Guild) -> Tuple[List[Tuple[Optional[discord.Member], str]], int]:
    """ Fetches HC members (sorted by username#discriminator) and IGNs."""
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"HC Role {ADD_ROLE_ID_HC} not found.")
        return [], 0

    # Ensure members are cached before proceeding
    if not guild.chunked:
        try:
            print(f"Attempting to chunk guild {guild.name} (ID: {guild.id}) for fetch_hc_member_data...")
            await guild.chunk(cache=True)
            print(f"Successfully chunked guild {guild.name}.")
        except discord.ClientException as e:
            # This can happen if members intent is disabled or bot lacks permissions
             await log_error(guild, "Guild chunking failed (ClientException - check intents/perms)", error=e)
             # Proceed without chunking, results might be incomplete
             print(f"Warning: Proceeding without chunking for guild {guild.name}, member list may be incomplete.")
        except Exception as e:
             await log_error(guild, "Guild chunking failed unexpectedly in fetch_hc_member_data", error=e)
             # Proceed, but log the error
             print(f"Warning: Unexpected error during chunking for guild {guild.name}, proceeding...")


    members_with_role = [m for m in guild.members if hc_role in m.roles and not m.bot]
    total = len(members_with_role)
    # Sort members case-insensitively by name, then discriminator
    members_sorted = sorted(members_with_role, key=lambda m: (m.name.lower(), m.discriminator))
    ids = [str(m.id) for m in members_sorted]
    ign_map = {}
    if supabase and ids:
        try:
            chunk_size = 500 # Supabase might have limits on IN clause size
            for i in range(0, len(ids), chunk_size):
                chunk = ids[i:i+chunk_size]
                print(f"Fetching IGNs for chunk {i//chunk_size + 1} (Size: {len(chunk)})")
                resp = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").in_("discord_id", chunk).execute())
                if resp and hasattr(resp, 'data') and resp.data:
                    # Ensure discord_id is treated as string for consistency
                    ign_map.update({str(r['discord_id']): r.get("ingame_name") or "Unknown" for r in resp.data if 'discord_id' in r})
                await asyncio.sleep(0.1) # Small delay between chunks if needed
            print(f"Finished fetching IGNs, found {len(ign_map)} entries.")
        except ConnectionError as e:
             await log_error(guild, "Supabase connection unavailable during IGN fetch.", error=e)
             ign_map = {mid: "DB Connection Err" for mid in ids} # Indicate error for all
        except APIError as e:
             await log_error(guild, "Supabase API Error during IGN fetch.", error=e)
             ign_map = {mid: "DB API Err" for mid in ids}
        except Exception as e:
            await log_error(guild, "Unexpected error during IGN fetch.", error=e)
            ign_map = {mid: "DB Fetch Err" for mid in ids}

    # Map sorted members to their fetched IGNs
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
            # Handle potential null members gracefully
            user=discord.utils.escape_markdown(f"{m.name}#{m.discriminator}" if m and m.discriminator != '0' else getattr(m, 'name', 'Unknown User')) if m else "*User Left Guild?*"
            ign_s=discord.utils.escape_markdown(ign or "Unknown")
            desc.append(f"{idx}. {user} ➔ {ign_s}")
            idx += 1
        full_desc = "\n".join(desc)
        # Discord embed description limit is 4096
        if len(full_desc) > 4096:
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
    bot_mem = guild.get_member(bot.user.id)
    if not bot_mem:
        # Attempt to fetch if not in cache (might happen in rare cases)
        try:
            bot_mem = await guild.fetch_member(bot.user.id)
            print(f"Fetched bot member object for static list update in {guild.name}")
        except discord.NotFound:
             await log_error(guild, f"Cannot update static list: Bot not found in guild {guild.name} (even after fetch).")
             return
        except discord.HTTPException as e:
            await log_error(guild, f"Cannot update static list: HTTP error fetching bot member in {guild.name}.", error=e)
            return
        except Exception as e:
            await log_error(guild, f"Cannot update static list: Unexpected error fetching bot member in {guild.name}.", error=e)
            return
    if not bot_mem: # Double check after potential fetch
         await log_error(guild, f"Cannot update static list: Bot member object unavailable in {guild.name}.")
         return

    perms = chan.permissions_for(bot_mem)
    # Check specific permissions needed
    required_perms = {
        "Send Messages": perms.send_messages,
        "Embed Links": perms.embed_links,
        "Read Message History": perms.read_message_history,
        "Manage Messages": perms.manage_messages # Needed for efficient cleanup
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
            # Fetch slightly more to be safe, limit history scan
            async for msg in chan.history(limit=max(num_new, 15) + 5):
                 # Ensure message is from the bot and has the specific embed title
                 if msg.author and msg.author.id == bot.user.id and msg.embeds:
                      if msg.embeds[0].title and msg.embeds[0].title == HC_LIST_EMBED_TITLE:
                           existing.append(msg)
        except discord.Forbidden:
             await log_error(guild, f"History permission denied in {chan.mention} during static list update.")
             return # Cannot proceed without history
        except Exception as e:
            await log_error(guild, "Error fetching history for static list update", error=e)
            return # Stop if history fetch fails

        # Sort existing messages chronologically (oldest first)
        existing.sort(key=lambda m: m.created_at)
        num_exist = len(existing)
        print(f"Static List Update ({guild.name}): Found {num_exist} existing bot messages, Need to display {num_new} pages.")

        tasks = []
        messages_to_delete = []
        # Add small delay to avoid rate limits, especially on edits/sends
        delay = 1.2

        # Edit existing messages or send new ones
        for i in range(num_new):
            await asyncio.sleep(delay) # Apply delay before each action
            if i < num_exist:
                print(f"  Editing message {existing[i].id} (Page {i+1})")
                tasks.append(existing[i].edit(embed=new_embeds[i]))
            else:
                print(f"  Sending new message (Page {i+1})")
                tasks.append(chan.send(embed=new_embeds[i]))

        # Identify surplus messages to delete
        if num_exist > num_new:
            messages_to_delete = existing[num_new:]
            print(f"  Identified {len(messages_to_delete)} surplus messages to delete.")

        # Execute edits/sends concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        edit_send_errors = 0
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                edit_send_errors += 1
                action = "Edit" if i < num_exist else "Send"
                # Try to get message ID even for failed edits
                msg_id = existing[i].id if i < num_exist else "New"
                await log_error(guild, f"Static list {action} failed for Page {i+1} (MsgID: {msg_id})", error=res)

        # Delete surplus messages
        delete_errors = 0
        if messages_to_delete:
            # Use bulk delete if possible and needed
            can_bulk_delete = perms.manage_messages and len(messages_to_delete) > 1
            if can_bulk_delete:
                try:
                    await asyncio.sleep(delay) # Delay before bulk delete too
                    await chan.delete_messages(messages_to_delete)
                    print(f"  Bulk deleted {len(messages_to_delete)} surplus messages.")
                except discord.HTTPException as e:
                    # Handle specific HTTP errors like 400 Bad Request (e.g., message too old)
                    print(f"  Bulk delete failed (HTTP {e.status}): {e.text}. Falling back to individual deletion.")
                    can_bulk_delete = False # Force fallback
                except Exception as e:
                    await log_error(guild, f"Bulk delete failed unexpectedly", error=e)
                    can_bulk_delete = False # Assume fallback is safer

            # Fallback to individual deletion if bulk failed or wasn't possible
            if not can_bulk_delete:
                 print(f"  Attempting individual deletion for {len(messages_to_delete)} messages.")
                 for msg_del in messages_to_delete:
                    await asyncio.sleep(delay) # Delay each individual delete
                    try:
                        await msg_del.delete()
                        print(f"  Individually deleted surplus message {msg_del.id}")
                    except discord.NotFound:
                        print(f"  Skipped deleting message {msg_del.id} (already gone).")
                    except discord.Forbidden:
                        delete_errors += 1
                        await log_error(guild, f"Failed to delete surplus message {msg_del.id} (Forbidden)")
                        # Stop trying if forbidden, likely a persistent issue
                        print("  Stopping further individual deletes due to Forbidden error.")
                        break
                    except Exception as e:
                        delete_errors += 1
                        await log_error(guild, f"Failed to delete surplus message {msg_del.id}", error=e)

        # Log final status
        status_msg = f"Static list update complete ({num_new} pages displayed)."
        if edit_send_errors > 0: status_msg += f" Encountered {edit_send_errors} edit/send errors."
        if delete_errors > 0: status_msg += f" Encountered {delete_errors} delete errors."
        # Use error log level if any errors occurred
        log_level = log_error if edit_send_errors > 0 or delete_errors > 0 else log_info
        await log_level(guild, status_msg)

    except Exception as e:
        await log_error(guild, "Unhandled error during static list update process", error=e)


# --- Discord Events ---
@bot.event
async def on_ready():
    print("--- on_ready event started ---") # DIAGNOSTIC PRINT
    global BOT_ID, command_ids
    if bot.user:
        BOT_ID = bot.user.id
        print(f"Logged in as {bot.user} (ID: {BOT_ID})") # This should now appear
        print(f"Discord.py v{discord.__version__}")
    else:
        print("CRITICAL ERROR: Bot user object not found on ready.")
        # Consider attempting to exit or stop if bot.user is None
        return

    print("Syncing application commands...")
    synced_commands = []
    try:
        # Sync globally. Consider syncing per-guild if commands are guild-specific
        # synced_commands = await tree.sync(guild=discord.Object(id=YOUR_GUILD_ID)) # Example for guild sync
        synced_commands = await tree.sync() # Global sync
        print(f"Synced {len(synced_commands)} application commands globally.")
        command_ids.clear() # Clear old IDs before populating
        for cmd in synced_commands:
            # Ensure it's a base command and not a group/subcommand placeholder
            if isinstance(cmd, app_commands.Command):
                command_ids[cmd.name] = cmd.id
                print(f"  Stored ID for /{cmd.name}: {cmd.id}")
            elif isinstance(cmd, app_commands.Group):
                 print(f"  Found command group: {cmd.name} (Subcommands might be synced)")
                 # You might need to handle groups differently if you need their IDs
                 # Or iterate through cmd.commands if necessary for subcommand IDs
            else:
                 print(f"  Found unknown type during sync: {type(cmd)}")

        # Check if the dictionary is populated
        if command_ids:
            print(f"Stored command IDs: {command_ids}")
        else:
             print("Warning: command_ids dictionary is empty after sync. Help command may not show clickable links.")

    except discord.HTTPException as e:
        print(f"Command Sync failed (HTTPException): {e}")
        # Log this error to your error channel if possible
        first_guild = bot.guilds[0] if bot.guilds else None
        if first_guild:
            await log_error(first_guild, "Application Command Sync failed on startup (HTTPException).", error=e)
    except Exception as e:
        print(f"Command Sync failed (Unexpected Error): {e}\n{traceback.format_exc()}")
        first_guild = bot.guilds[0] if bot.guilds else None
        if first_guild:
            await log_error(first_guild, "Application Command Sync failed on startup (Exception).", error=e)

    # Ensure the bot has guilds before proceeding with guild-specific setup
    if not bot.guilds:
        print("Bot is not currently in any guilds. Skipping guild setup.")
        return

    print(f"Performing initial setup for {len(bot.guilds)} guild(s)...")
    # Process guilds one by one to avoid potential rate limits on setup tasks
    guilds_to_process = list(bot.guilds) # Create a copy to avoid issues if list changes
    for guild in guilds_to_process:
        print(f"  Processing guild: {guild.name} (ID: {guild.id})")
        try:
            # Log bot readiness per guild
            await log_info(guild, f"Bot ready and online. Synced {len(synced_commands)} commands.")
            # Update the static list on startup for each relevant guild
            await update_hc_member_list(guild)
            # Add a small delay between processing guilds if necessary
            await asyncio.sleep(1)
        except Exception as e:
            # Log errors specific to the guild setup
            await log_error(guild, f"Error during on_ready setup for this guild", error=e)

    print("--- on_ready event finished ---")


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Ignore updates for bots or if roles haven't changed
    if after.bot or before.roles == after.roles:
        return

    guild = after.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    # If HC role isn't configured or found, no need to proceed
    if not hc_role: return

    had_hc_role = hc_role in before.roles
    has_hc_role = hc_role in after.roles

    # Trigger update only if the HC role status changed
    if had_hc_role != has_hc_role:
        action = "added to" if has_hc_role else "removed from"
        await log_info(guild, f"HC role (`{hc_role.name}`) {action} user {after.mention} (`{after.id}`). Triggering static list update.")
        try:
            # Schedule the update, don't block the event handler for too long
            asyncio.create_task(update_hc_member_list(guild))
        except Exception as e:
             # Log the error if task creation or the update itself fails immediately
             await log_error(guild, f"Failed to trigger static list update after role change for {after.mention}", error=e)


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
            await interaction.followup.send(user_msg, ephemeral=True)
        else:
            # Otherwise, send the initial response
            await interaction.response.send_message(user_msg, ephemeral=True)
    except discord.NotFound:
        # Interaction might have expired between error and response
        print(f"Error Handler: Interaction {interaction.id} already expired or deleted.")
    except discord.InteractionResponded:
         # Should ideally be caught by is_done(), but handle defensively
         try:
             await interaction.followup.send(user_msg, ephemeral=True)
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

class BulkUpdateModal(Modal, title="Bulk Update IGNs"):
    data = TextInput(
        label="Paste list (username#tag ➔ IGN)",
        style=discord.TextStyle.paragraph,
        placeholder="ExampleUser#1234 ➔ CoolIGN\nAnotherUser ➔ AnotherIGN\n(One entry per line, format flexible)",
        required=True,
        min_length=5,
        max_length=4000 # Discord's max length for text input
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Defer ephemerally while processing
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.guild
        if not guild or not supabase:
            # Log internal error as well
            await log_error(guild, "Bulk update failed: Guild or Supabase unavailable.", interaction=interaction)
            await interaction.followup.send("❌ Internal error (Guild or Database unavailable). Please contact an admin.", ephemeral=True)
            return

        lines = self.data.value.strip().splitlines()
        if not lines:
            await interaction.followup.send("⚠️ Input was empty. No changes made.", ephemeral=True)
            return

        # --- Member Caching Strategy ---
        # Fetch members efficiently. Chunking might be needed for very large servers,
        # but guild.members should be sufficient if intents are enabled and cache is populated.
        member_map_id = {} # Discord ID (str) -> Member object
        member_map_name_disc = {} # Lowercase "name#discriminator" -> Member object
        member_map_name_only = {} # Lowercase name/display_name -> Member object
        try:
            # Ensure guild members are cached if needed
            if not guild.chunked:
                print(f"Chunking guild {guild.name} for bulk update modal...")
                await guild.chunk(cache=True)
            # Build lookup dictionaries
            for m in guild.members:
                if m.bot: continue # Skip bots
                member_map_id[str(m.id)] = m
                # Handle users with new username system (discriminator '0')
                if m.discriminator != '0':
                    member_map_name_disc[f"{m.name}#{m.discriminator}".lower()] = m
                # Map both username and display name (nickname) for flexibility
                member_map_name_only[m.name.lower()] = m
                if m.nick: # Only map nickname if it exists
                    member_map_name_only[m.display_name.lower()] = m # display_name is nickname if set

        except Exception as e:
            await log_error(guild, "Bulk update member fetch/chunking fail", error=e, interaction=interaction)
            await interaction.followup.send("❌ Error fetching server members. Cannot process update.", ephemeral=True)
            return
        # --- End Member Caching ---

        success_count, fail_count, not_found_count = 0, 0, 0
        log_details = [] # For detailed feedback in the result embed
        payload = [] # List of dicts to upsert to Supabase

        for idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line: continue # Skip empty lines

            # Find the separator. Allow flexibility (e.g., ->, =>, :)? For now, just ➔
            separator = "➔"
            if separator not in line:
                fail_count += 1
                log_details.append(f"❌ L{idx}: Invalid format (Missing '{separator}') - Line: `{line[:60]}`")
                continue

            parts = line.split(separator, 1)
            identifier_raw, ign_raw = map(str.strip, parts)
            ign = ign_raw

            # Clean identifier: remove leading list numbers/dots/spaces
            identifier_clean = identifier_raw.lstrip('0123456789. ')
            identifier_lower = identifier_clean.lower() # For case-insensitive matching

            if not identifier_clean or not ign:
                fail_count += 1
                log_details.append(f"❌ L{idx}: Missing user identifier or IGN - User: `{identifier_raw[:30]}`, IGN: `{ign_raw[:30]}`")
                continue

            # --- Member Matching Logic ---
            member: Optional[discord.Member] = None
            # 1. Try matching by ID first (most reliable)
            if identifier_clean.isdigit():
                member = member_map_id.get(identifier_clean)
            # 2. Try matching by "username#discriminator" (case-insensitive)
            if not member and '#' in identifier_clean:
                member = member_map_name_disc.get(identifier_lower)
            # 3. Try matching by name or display name (case-insensitive)
            if not member:
                 member = member_map_name_only.get(identifier_lower)
            # --- End Member Matching ---

            if not member:
                fail_count += 1
                not_found_count += 1
                log_details.append(f"❓ L{idx}: User not found - Identifier: `{discord.utils.escape_markdown(identifier_clean)}`")
                continue

            # Validate/Truncate IGN length (Supabase column limit?) Assume 100 for now.
            ign_limit = 100
            if len(ign) > ign_limit:
                 ign_original = ign
                 ign = ign[:ign_limit]
                 log_details.append(f"⚠️ L{idx}: IGN for {member.mention} truncated from `{ign_original}` to `{ign}`.")

            # Add to Supabase payload
            payload.append({
                "discord_id": str(member.id),
                 # Store consistent name format
                "discord_name": f"{member.name}#{member.discriminator}" if member.discriminator != '0' else member.name,
                "ingame_name": ign
            })

        # --- Database Upsert ---
        db_error = None
        if payload:
            try:
                print(f"Bulk update: Upserting {len(payload)} records to Supabase.")
                # Use upsert with on_conflict to update existing entries or insert new ones
                await run_supabase_sync(
                    lambda: supabase.table("hc_members")
                                    .upsert(payload, on_conflict="discord_id") # Assumes discord_id is unique constraint
                                    .execute()
                )
                success_count = len(payload)
                print("Bulk update: Supabase upsert successful.")
            except Exception as e:
                db_error = e
                fail_count += len(payload) # Assume all in payload failed if DB error occurs
                success_count = 0
                await log_error(guild, "Bulk update Supabase upsert failed", error=e, interaction=interaction)
                log_details.append(f"🔥 **Database Error:** Failed to save {len(payload)} entries. Error: `{type(e).__name__}`")
        # --- End Database Upsert ---

        # --- Final Response ---
        result_color = discord.Color.green() if fail_count == 0 and not db_error else (discord.Color.orange() if success_count > 0 else discord.Color.red())
        embed = discord.Embed(title="Bulk IGN Update Results", color=result_color)

        format_issue_count = fail_count - not_found_count - (len(payload) if db_error else 0)
        summary = (f"Processed Lines: {len(lines)}\n"
                   f"✅ Successful Updates: {success_count}\n"
                   f"❌ Failed Entries: {fail_count}\n"
                   f"  - User Not Found: {not_found_count}\n"
                   f"  - Format/Data Issues: {format_issue_count}\n"
                   f"{'  - Database Save Failed: ' + str(len(payload)) if db_error else ''}")
        embed.description = summary

        if log_details:
            # Paginate details if too long for one field? For now, just truncate.
            log_output = "\n".join(log_details)
            details_limit = 1024 # Discord embed field value limit
            if len(log_output) > details_limit:
                log_output = log_output[:details_limit - 4] + "\n..."
            embed.add_field(name="Details", value=log_output, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)
        # --- End Final Response ---

        # Log summary to info channel
        summary_for_log = summary.replace('\n', ' | ').replace('  - ', '') # Condense for logs
        await log_info(guild, f"Bulk update by `{interaction.user}` completed. Results: {summary_for_log}")

        # Trigger static list update if successful updates occurred
        if success_count > 0:
            print("Bulk update successful, triggering static list refresh.")
            # Run as a separate task to avoid blocking
            asyncio.create_task(update_hc_member_list(guild))

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        # Overload default on_error to provide better logging/feedback
        await log_error(interaction.guild, "Error in BulkUpdateModal", error=error, interaction=interaction)
        try:
            # Try to respond ephemerally if the interaction is still valid
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An unexpected error occurred submitting the form.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An unexpected error occurred submitting the form.", ephemeral=True)
        except Exception as e_resp:
             print(f"Failed to send error response for BulkUpdateModal error: {e_resp}")


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
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    role_to_remove = guild.get_role(REMOVE_ROLE_ID)
    role_to_add = guild.get_role(ADD_ROLE_ID_VERIFY)

    # Role existence checks
    missing_roles = []
    if REMOVE_ROLE_ID and not role_to_remove: missing_roles.append(f"Unverified Role (ID: {REMOVE_ROLE_ID})")
    if ADD_ROLE_ID_VERIFY and not role_to_add: missing_roles.append(f"Verified Role (ID: {ADD_ROLE_ID_VERIFY})")
    if missing_roles:
        msg = f"❌ Setup Error: Roles not found: {', '.join(missing_roles)}. Please configure the bot."
        await interaction.response.send_message(msg, ephemeral=True)
        await log_error(guild, f"Verify failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return
    # We definitely need the role to add
    if not role_to_add:
         msg = f"❌ Setup Error: Verified Role (ID: {ADD_ROLE_ID_VERIFY}) not configured correctly."
         await interaction.response.send_message(msg, ephemeral=True)
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
        await interaction.response.send_message(msg, ephemeral=True)
        await log_error(guild, f"Verify failed: Bot hierarchy issue. Reason: {hierarchy_reason}", interaction=interaction)
        return

    # Defer ephemerally while roles are changed
    await interaction.response.defer(thinking=True, ephemeral=True)

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
            await interaction.followup.send(f"ℹ️ {user.mention} is already verified (has '{role_to_add.name}' and not '{role_to_remove.name if role_to_remove else ''}').", ephemeral=True)
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
            await interaction.followup.send(f"✅ Successfully verified {user.mention}.", ephemeral=True)

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
             await interaction.followup.send("ℹ️ No role changes were needed.", ephemeral=True)

    except discord.Forbidden:
        await log_error(guild, "Verify failed: Bot lacks permissions (Forbidden).", interaction=interaction)
        await interaction.followup.send("❌ Failed: I don't have the necessary permissions to manage roles for this user.", ephemeral=True)
    except discord.HTTPException as e:
        await log_error(guild, "Verify failed: Discord API error.", error=e, interaction=interaction)
        await interaction.followup.send("❌ Failed: A Discord API error occurred. Please try again later.", ephemeral=True)
    except Exception as e:
        await log_error(guild, "Unexpected error during /verify.", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)


# --- Unverify Command ---
@tree.command(name="unverify", description="Revert user to Unverified (adds Unverified, removes Verified).")
@app_commands.describe(user="The user to unverify.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def unverify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    role_to_add = guild.get_role(REMOVE_ROLE_ID) # Role to ADD is 'Unverified'
    role_to_remove = guild.get_role(ADD_ROLE_ID_VERIFY) # Role to REMOVE is 'Verified'

    # Role existence checks
    missing_roles = []
    if REMOVE_ROLE_ID and not role_to_add: missing_roles.append(f"Unverified Role (ID: {REMOVE_ROLE_ID})")
    if ADD_ROLE_ID_VERIFY and not role_to_remove: missing_roles.append(f"Verified Role (ID: {ADD_ROLE_ID_VERIFY})")
    if missing_roles:
        msg = f"❌ Setup Error: Roles not found: {', '.join(missing_roles)}. Please configure the bot."
        await interaction.response.send_message(msg, ephemeral=True)
        await log_error(guild, f"Unverify failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return
    # We definitely need the 'Unverified' role to add it
    if not role_to_add:
         msg = f"❌ Setup Error: Unverified Role (ID: {REMOVE_ROLE_ID}) not configured correctly."
         await interaction.response.send_message(msg, ephemeral=True)
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
         await interaction.response.send_message(msg, ephemeral=True)
         await log_error(guild, f"Unverify failed: Bot hierarchy issue. Reason: {hierarchy_reason}", interaction=interaction)
         return

    # Defer ephemerally
    await interaction.response.defer(thinking=True, ephemeral=True)

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
            await interaction.followup.send(f"ℹ️ {user.mention} is already Unverified (has '{role_to_add.name}' and not '{role_to_remove.name if role_to_remove else ''}').", ephemeral=True)
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
            await interaction.followup.send(f"✅ Successfully unverified {user.mention}.", ephemeral=True)

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
             await interaction.followup.send("ℹ️ No role changes were needed.", ephemeral=True)

    except discord.Forbidden:
        await log_error(guild, "Unverify failed: Bot lacks permissions (Forbidden).", interaction=interaction)
        await interaction.followup.send("❌ Failed: I don't have the necessary permissions to manage roles for this user.", ephemeral=True)
    except discord.HTTPException as e:
        await log_error(guild, "Unverify failed: Discord API error.", error=e, interaction=interaction)
        await interaction.followup.send("❌ Failed: A Discord API error occurred. Please try again later.", ephemeral=True)
    except Exception as e:
        await log_error(guild, "Unexpected error during /unverify.", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)


# --- REFINED HC Verify Command ---
@tree.command(name="hcverify", description="Verify user into HC, store IGN, set nickname.")
@app_commands.describe(user="User to HC verify.", ingame_name="User's Florr IGN (will be used as nickname).")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return
    if not supabase:
        await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
        await log_error(guild, "HCVerify failed: Supabase client unavailable.", interaction=interaction)
        return

    # Defer publicly as this command makes visible changes (roles, nick, list update)
    await interaction.response.defer(thinking=True, ephemeral=False) # Changed to False

    # Get necessary roles
    role_unverified = guild.get_role(REMOVE_ROLE_ID)
    role_verified = guild.get_role(ADD_ROLE_ID_VERIFY)
    role_hc = guild.get_role(ADD_ROLE_ID_HC)
    bot_member = guild.me

    # Check if required roles exist
    missing_roles = []
    if ADD_ROLE_ID_VERIFY and not role_verified: missing_roles.append(f"Verified (ID: {ADD_ROLE_ID_VERIFY})")
    if ADD_ROLE_ID_HC and not role_hc: missing_roles.append(f"HC (ID: {ADD_ROLE_ID_HC})")
    # Unverified role is optional to remove, but good to check if configured
    if REMOVE_ROLE_ID and not role_unverified: print(f"Warning: Unverified Role (ID: {REMOVE_ROLE_ID}) not found, cannot remove it.")

    if not role_verified or not role_hc: # HC and Verified are critical
        msg = f"❌ Setup Error: Missing critical roles: {', '.join(missing_roles)}. Please configure the bot."
        # Use followup since we deferred
        await interaction.followup.send(msg, ephemeral=True)
        await log_error(guild, f"HCVerify failed: Missing critical roles - {', '.join(missing_roles)}", interaction=interaction)
        return

    # --- Prepare for actions ---
    log_summary = [] # For internal logging
    result_summary = [] # For user feedback embed
    errors_occurred = False
    db_success = False
    role_changes_succeeded = False
    nick_success = False
    reason = f"HC Verified by {interaction.user} (ID: {interaction.user.id})"
    can_manage_user_roles = bot_member.top_role.position > user.top_role.position
    can_manage_user_nick = can_manage_user_roles # Nick management requires similar hierarchy

    # --- Role Management ---
    roles_to_add_final = []
    roles_to_remove_final = []
    original_hc_status = role_hc in user.roles

    # Determine desired state
    desired_adds = []
    desired_removes = []
    if not (role_verified in user.roles): desired_adds.append(role_verified)
    if not original_hc_status: desired_adds.append(role_hc)
    if role_unverified and (role_unverified in user.roles): desired_removes.append(role_unverified)

    # Check bot hierarchy for each desired change
    for role in desired_adds:
        if bot_member.top_role.position > role.position:
            roles_to_add_final.append(role)
        else:
            errors_occurred=True
            reason_skip=f"Bot hierarchy too low to add role '{role.name}'"
            result_summary.append(f"⚠️ Skipped adding `{role.name}` (Hierarchy).")
            log_summary.append(f"Role add skip: {reason_skip}")
            await log_info(guild, f"HCVerify: {reason_skip} for {user.mention}")
    for role in desired_removes:
        if bot_member.top_role.position > role.position:
            roles_to_remove_final.append(role)
        else:
            errors_occurred=True
            reason_skip=f"Bot hierarchy too low to remove role '{role.name}'"
            result_summary.append(f"⚠️ Skipped removing `{role.name}` (Hierarchy).")
            log_summary.append(f"Role remove skip: {reason_skip}")
            await log_info(guild, f"HCVerify: {reason_skip} for {user.mention}")

    # Apply role changes if any are possible and needed
    if roles_to_add_final or roles_to_remove_final:
        try:
            # Perform additions and removals (Discord API handles this efficiently)
            await user.edit(roles=[r for r in user.roles if r not in roles_to_remove_final] + roles_to_add_final, reason=reason)

            added_names = ', '.join(f"`{r.name}`" for r in roles_to_add_final)
            removed_names = ', '.join(f"`{r.name}`" for r in roles_to_remove_final)
            if added_names: result_summary.append(f"➕ Roles Added: {added_names}")
            if removed_names: result_summary.append(f"➖ Roles Removed: {removed_names}")
            log_summary.append("Role update successful for applicable roles.")
            role_changes_succeeded = True # Mark role change as successful
        except discord.Forbidden:
            errors_occurred=True
            result_summary.append("⚠️ Role Error: Permissions error during update.")
            log_summary.append("Role update failed: Forbidden")
            await log_error(guild, "HCVerify role update failed (Forbidden)", interaction=interaction)
        except discord.HTTPException as e:
            errors_occurred=True
            result_summary.append("⚠️ Role Error: Discord API Error during update.")
            log_summary.append(f"Role update failed: HTTP {e.status}")
            await log_error(guild, "HCVerify role update failed (HTTPException)", error=e, interaction=interaction)
        except Exception as e:
            errors_occurred=True
            result_summary.append("⚠️ Role Error: Unknown error during update.")
            log_summary.append(f"Role update fail: {type(e).__name__}")
            await log_error(guild, "HCVerify unexpected role error", error=e, interaction=interaction)
    elif not desired_adds and not desired_removes:
        # Only report this if no hierarchy skips happened for roles
        if not any("Role add skip" in s or "Role remove skip" in s for s in log_summary):
             result_summary.append("ℹ️ Roles already correct.")
             log_summary.append("No role changes needed.")

    # --- Database Update ---
    ign_to_store = ingame_name.strip()
    if not ign_to_store:
        errors_occurred=True
        result_summary.append(f"⚠️ DB Error: In-game name cannot be empty.")
        log_summary.append(f"DB fail: Empty IGN provided.")
        await log_error(guild, "HCVerify DB upsert fail: Empty IGN", interaction=interaction)
    else:
        try:
            await run_supabase_sync( lambda: supabase.table("hc_members").upsert({
                    "discord_id": str(user.id),
                    "discord_name": f"{user.name}#{user.discriminator}" if user.discriminator != '0' else user.name,
                    "ingame_name": ign_to_store
                }, on_conflict="discord_id").execute() # Assumes discord_id is unique constraint
            )
            result_summary.append(f"💾 IGN Stored: `{discord.utils.escape_markdown(ign_to_store)}`")
            log_summary.append("Supabase upsert OK")
            db_success = True
        except APIError as e:
            errors_occurred=True
            err_detail=f"API Error ({e.code or 'N/A'}): {e.message or 'Unknown'}"
            result_summary.append(f"⚠️ DB Error: {err_detail}")
            log_summary.append(f"DB fail: {e}")
            await log_error(guild, "HCVerify DB upsert fail (APIError)", error=e, interaction=interaction)
        except Exception as e: # Catch ConnectionError here too via run_supabase_sync
            errors_occurred=True
            err_type = type(e).__name__
            result_summary.append(f"⚠️ DB Error: {err_type}.")
            log_summary.append(f"DB fail: {err_type}")
            await log_error(guild, f"HCVerify DB upsert fail ({err_type})", error=e, interaction=interaction)

    # --- Nickname Management ---
    # Truncate nickname to Discord's 32 char limit
    nickname_to_set = ign_to_store[:32] if ign_to_store else "" # Use stored IGN, handle empty case
    truncated = ign_to_store != nickname_to_set and ign_to_store # Check if truncation happened

    if not nickname_to_set:
        # Don't treat empty IGN as error for nickname *if* DB step failed already
        if db_success: # Only log as error if DB was ok but IGN was empty somehow
            errors_occurred=True
            result_summary.append("⚠️ Nickname Error: Cannot set empty nickname.")
            log_summary.append("Nick skipped (empty IGN)")
    elif user.nick == nickname_to_set:
        result_summary.append(f"🏷️ Nickname already matches stored IGN.")
        log_summary.append("Nick already set")
        nick_success = True # Considered success
    elif not can_manage_user_nick:
        errors_occurred=True
        result_summary.append(f"⚠️ Nickname Skipped (Hierarchy).")
        log_summary.append("Nick skipped (Hierarchy)")
        await log_info(guild, f"HCVerify: Nickname change skipped for {user.mention} (Hierarchy).")
    else:
        try:
            await user.edit(nick=nickname_to_set, reason=reason)
            nick_msg = f"🏷️ Nickname Set: `{discord.utils.escape_markdown(nickname_to_set)}`"
            if truncated: nick_msg += " (truncated)"
            result_summary.append(nick_msg)
            log_summary.append(f"Nick set{' (trunc)' if truncated else ''}")
            nick_success = True
        except discord.Forbidden:
            errors_occurred=True
            result_summary.append("⚠️ Nickname Error: Permissions error.")
            log_summary.append("Nick fail: Forbidden")
            await log_error(guild, "HCVerify nick fail (Forbidden)", interaction=interaction)
        except discord.HTTPException as e:
            errors_occurred=True
            result_summary.append("⚠️ Nickname Error: API Error.")
            log_summary.append(f"Nick fail: HTTP {e.status}")
            await log_error(guild, "HCVerify nick fail (HTTPException)", error=e, interaction=interaction)
        except Exception as e:
            errors_occurred=True
            result_summary.append("⚠️ Nickname Error: Unknown error.")
            log_summary.append(f"Nick fail: {type(e).__name__}")
            await log_error(guild, "HCVerify unexpected nick error", error=e, interaction=interaction)

    # --- Final Response & Logging ---
    final_color = discord.Color.green() if not errors_occurred else discord.Color.orange()
    final_title = f"{'✅' if not errors_occurred else '⚠️'} HC Verify Processed: {user.display_name}"
    if errors_occurred: final_title += " (with issues/skips)"

    # Ensure result_summary is not empty
    if not result_summary: result_summary.append("ℹ️ No actions were performed.")

    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    try:
        # Use followup as we deferred
        await interaction.followup.send(embed=final_embed)
    except (discord.NotFound, discord.HTTPException) as e:
        await log_error(guild, "HCVerify failed final followup send", error=e, interaction=interaction)
        # Try sending to channel if followup fails? Might be excessive.

    await log_info(guild, f"`{interaction.user}` HCVerify for {user.mention}. Summary: {'; '.join(log_summary)}.")

    # Trigger list update if roles changed to add HC OR if DB was updated successfully
    # (even if roles didn't change, IGN might have been corrected)
    if (role_changes_succeeded and role_hc in roles_to_add_final) or db_success:
         print(f"HCVerify: Triggering list update for {user.name} (HC role added: {role_hc in roles_to_add_final}, DB success: {db_success}).")
         # Run as task
         asyncio.create_task(update_hc_member_list(guild))


# --- REFINED Un-HC-Verify Command ---
@tree.command(name="unhcverify", description="Remove HC role and reset nickname for a user.")
@app_commands.describe(user="The user to remove from HC.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def unhcverify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    # Defer publicly
    await interaction.response.defer(thinking=True, ephemeral=False) # Changed to False

    role_hc = guild.get_role(ADD_ROLE_ID_HC)
    bot_member = guild.me

    if not role_hc:
        msg = f"❌ Setup Error: HC Role (ID: {ADD_ROLE_ID_HC}) not found. Cannot perform action."
        await interaction.followup.send(msg, ephemeral=True)
        await log_error(guild, f"UnHCVerify failed: HC role not found.", interaction=interaction)
        return

    # --- Prepare ---
    log_summary = []
    result_summary = []
    errors_occurred = False
    role_was_removed = False
    nick_was_reset = False
    reason = f"Un-HC-Verified by {interaction.user} (ID: {interaction.user.id})"
    can_manage_user_roles = bot_member.top_role.position > user.top_role.position
    can_manage_user_nick = can_manage_user_roles
    can_manage_hc_role = bot_member.top_role.position > role_hc.position
    has_hc_role = role_hc in user.roles
    nick_needs_reset = user.nick is not None # Check if user has any nickname

    # --- Role Removal ---
    if not has_hc_role:
        result_summary.append(f"ℹ️ User doesn't have the `{role_hc.name}` role.")
        log_summary.append("HC role already absent.")
    elif not can_manage_hc_role:
        errors_occurred=True
        reason_skip=f"Bot hierarchy too low to remove role '{role_hc.name}'"
        result_summary.append(f"⚠️ Skipped removing `{role_hc.name}` (Hierarchy).")
        log_summary.append(f"Role remove skip: {reason_skip}")
        await log_info(guild, f"UnHCVerify: {reason_skip} for {user.mention}")
    else:
        try:
            # Use edit to remove just the one role
            await user.remove_roles(role_hc, reason=reason)
            result_summary.append(f"➖ Role Removed: `{role_hc.name}`")
            log_summary.append("HC role removed OK")
            role_was_removed = True
        except discord.Forbidden:
            errors_occurred=True
            result_summary.append("⚠️ Role Error: Permissions error removing role.")
            log_summary.append("Role remove fail: Forbidden")
            await log_error(guild, "UnHCVerify role remove fail (Forbidden)", interaction=interaction)
        except discord.HTTPException as e:
            errors_occurred=True
            result_summary.append("⚠️ Role Error: API Error removing role.")
            log_summary.append(f"Role remove fail: HTTP {e.status}")
            await log_error(guild, "UnHCVerify role remove fail (HTTPException)", error=e, interaction=interaction)
        except Exception as e:
            errors_occurred=True
            result_summary.append("⚠️ Role Error: Unknown error removing role.")
            log_summary.append(f"Role remove fail: {type(e).__name__}")
            await log_error(guild, "UnHCVerify unexpected role error", error=e, interaction=interaction)

    # --- Nickname Reset ---
    if not nick_needs_reset:
        result_summary.append("🏷️ User has no nickname to reset.")
        log_summary.append("No nickname reset needed.")
    elif not can_manage_user_nick:
        errors_occurred=True
        result_summary.append(f"⚠️ Nickname Reset Skipped (Hierarchy).")
        log_summary.append("Nick reset skipped (Hierarchy)")
        await log_info(guild, f"UnHCVerify: Nickname reset skipped for {user.mention} (Hierarchy).")
    else:
         try:
             await user.edit(nick=None, reason=reason) # Setting nick to None resets it
             result_summary.append("🏷️ Nickname Reset")
             log_summary.append("Nick reset OK")
             nick_was_reset = True
         except discord.Forbidden:
             errors_occurred=True
             result_summary.append("⚠️ Nickname Error: Permissions error resetting nick.")
             log_summary.append("Nick reset fail: Forbidden")
             await log_error(guild, "UnHCVerify nick reset fail (Forbidden)", interaction=interaction)
         except discord.HTTPException as e:
             errors_occurred=True
             result_summary.append("⚠️ Nickname Error: API Error resetting nick.")
             log_summary.append(f"Nick reset fail: HTTP {e.status}")
             await log_error(guild, "UnHCVerify nick reset fail (HTTPException)", error=e, interaction=interaction)
         except Exception as e:
             errors_occurred=True
             result_summary.append("⚠️ Nickname Error: Unknown error resetting nick.")
             log_summary.append(f"Nick reset fail: {type(e).__name__}")
             await log_error(guild, "UnHCVerify unexpected nick reset error", error=e, interaction=interaction)

    # --- Final Response & Logging ---
    final_color = discord.Color.green() if not errors_occurred else discord.Color.orange()
    final_title = f"{'✅' if not errors_occurred else '⚠️'} Un-HC Verify Processed: {user.display_name}"
    if errors_occurred: final_title += " (with issues/skips)"

    if not result_summary: result_summary.append("ℹ️ No actions were performed.")

    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    try:
        await interaction.followup.send(embed=final_embed)
    except (discord.NotFound, discord.HTTPException) as e:
        await log_error(guild, "UnHCVerify failed final followup send", error=e, interaction=interaction)

    await log_info(guild, f"`{interaction.user}` UnHCVerify for {user.mention}. Summary: {'; '.join(log_summary)}.")

    # Trigger list update only if the HC role was actually removed
    if role_was_removed:
        print(f"UnHCVerify: Triggering list update for {user.name} as HC role was removed.")
        asyncio.create_task(update_hc_member_list(guild))


# --- HC Members Interactive List ---
@tree.command(name="hcmembers", description="Show interactive list of [HC1] members (username#tag ➔ IGN).")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    # Check channel restrictions
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        allowed_mentions = [f"<#{ch_id}>" for ch_id in ALLOWED_CHANNEL_IDS if guild.get_channel(ch_id)] # Mention valid channels
        msg = f"❌ This command only works in: {', '.join(allowed_mentions) or 'configured channels'}"
        await interaction.response.send_message(msg, ephemeral=True)
        return

    # Defer publicly as the list is public
    await interaction.response.defer(thinking=True, ephemeral=False)

    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Database unavailable.", discord.Color.red()))
        await log_error(guild, "/hcmembers failed: Supabase unavailable.", interaction=interaction)
        return

    try:
        data, total = await fetch_hc_member_data(guild)

        if not data:
            hc_role = guild.get_role(ADD_ROLE_ID_HC)
            role_name = f"`{hc_role.name}`" if hc_role else f"HC role (ID: {ADD_ROLE_ID_HC})"
            description = f"No members currently found with the {role_name} role."
            # Add note if DB fetch might have failed partially
            if any("DB" in ign for _, ign in data): # Quick check if any placeholder errors exist
                 description += "\n(Note: There might have been database connection issues.)"
            embed = create_embed(title=HC_LIST_EMBED_TITLE, description=description, color=discord.Color.orange())
            await interaction.followup.send(embed=embed)
            return

        # Create and send the paginated view
        view = HCPagesView(data, total)
        initial_embed = view.create_page_embed()
        # Send the initial message and store it in the view for updates
        message = await interaction.followup.send(embed=initial_embed, view=view)
        view.message = message # IMPORTANT: Link the message to the view

        await log_info(guild, f"/hcmembers used by `{interaction.user}` in {interaction.channel.mention if interaction.channel else 'N/A'}.")

    except ConnectionError as e:
        await log_error(guild, "/hcmembers DB connection error", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Database Connection Error. Could not fetch member IGNs.", discord.Color.red()))
    except APIError as e:
        await log_error(guild, "/hcmembers Supabase API error", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Database API Error. Could not fetch member IGNs.", discord.Color.red()))
    except Exception as e:
        await log_error(guild, "Unhandled /hcmembers error", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ An unexpected error occurred while generating the list.", discord.Color.red()))


# --- Refresh Static List Command ---
@tree.command(name="refresh", description="Manually refresh static [HC1] list (username#tag ➔ IGN).")
@app_commands.checks.has_permissions(manage_roles=True) # Keep permission check
async def refresh(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    # Defer ephemerally, the result is the list being updated, not a direct message
    await interaction.response.defer(thinking=True, ephemeral=True)

    if not supabase:
        await interaction.followup.send("❌ Database connection unavailable.", ephemeral=True)
        await log_error(guild, "/refresh failed: Supabase unavailable.", interaction=interaction)
        return

    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(list_channel, discord.TextChannel):
        msg = f"❌ Configuration Error: Static list channel (ID: {HC_MEMBER_LIST_CHANNEL_ID}) is invalid or not found."
        await interaction.followup.send(msg, ephemeral=True)
        await log_error(guild, f"/refresh failed: Static list channel invalid.", interaction=interaction)
        return

    try:
        await log_info(guild, f"Manual static list refresh initiated by `{interaction.user}`.")
        # Run the update function (don't await if it's long, but for now await is fine)
        await update_hc_member_list(guild)
        # Confirm initiation to the user
        await interaction.followup.send(f"✅ Refresh initiated for the static list in {list_channel.mention}. Please allow a moment for it to update.", ephemeral=True)
    except Exception as e:
        await log_error(guild, "Error initiating /refresh", error=e, interaction=interaction)
        await interaction.followup.send("❌ An unexpected error occurred while starting the refresh process.", ephemeral=True)


# --- Bulk Update Command ---
@tree.command(name="bulkupdate", description="Open form to bulk update IGNs (username#tag ➔ IGN).")
@app_commands.checks.has_permissions(manage_roles=True) # Requires role management perms
async def bulkupdate(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    try:
        # Send the modal to the user
        await interaction.response.send_modal(BulkUpdateModal())
        # Log that the modal was opened (on_submit handles the results)
        await log_info(interaction.guild, f"`{interaction.user}` opened the bulk IGN update modal.")
    except Exception as e:
        await log_error(interaction.guild, "Failed to open BulkUpdateModal", error=e, interaction=interaction)
        # Try to send an error message if the modal fails to send
        if not interaction.response.is_done():
            try: await interaction.response.send_message("❌ Error opening the bulk update form. Please try again.", ephemeral=True)
            except Exception: pass # Ignore further errors


# --- Sync Nicknames Command ---
@tree.command(name="syncnicknames", description="Sync all HC members' nicknames with their stored IGNs.")
@app_commands.checks.has_permissions(manage_nicknames=True) # User needs manage nicknames
@app_commands.checks.bot_has_permissions(manage_nicknames=True) # Bot needs manage nicknames
async def syncnicknames(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    # Defer ephemerally while processing
    await interaction.response.defer(thinking=True, ephemeral=True)

    if not supabase:
        await interaction.edit_original_response(content="❌ Database connection unavailable.")
        await log_error(guild, "/syncnicknames failed: Supabase unavailable.", interaction=interaction)
        return

    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await interaction.edit_original_response(content=f"❌ Configuration Error: HC Role (ID: {ADD_ROLE_ID_HC}) not found.")
        await log_error(guild, f"/syncnicknames failed: HC role not found.", interaction=interaction)
        return

    # --- Start Sync Process ---
    start_time = discord.utils.utcnow()
    await log_info(guild, f"Nickname sync initiated by `{interaction.user}`.")
    # Placeholder message, replace ID with actual emoji ID if available
    loading_emoji = "<a:loading:12345>" # Replace 12345 with your actual emoji ID or use text
    await interaction.edit_original_response(content=f"{loading_emoji} Fetching data...")

    # 1. Fetch all IGNs from Supabase
    ign_data = {} # discord_id (str) -> ingame_name (str)
    try:
        resp = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").execute())
        if resp and hasattr(resp, 'data') and resp.data:
             # Ensure keys are strings and filter out entries without required fields
            ign_data = {str(item['discord_id']): item['ingame_name']
                        for item in resp.data
                        if item.get('discord_id') and item.get('ingame_name')}
        print(f"SyncNick ({guild.name}): Fetched {len(ign_data)} IGNs from database.")
    except Exception as e:
        await log_error(guild, "SyncNick: Database fetch failed", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Database fetch failed. Cannot proceed.")
        return

    # 2. Get all members with the HC role
    hc_members: List[discord.Member] = []
    try:
        # Ensure members are cached
        if not guild.chunked:
            print(f"Chunking guild {guild.name} for sync nicknames...")
            await guild.chunk(cache=True)
        # Filter members with the role, excluding bots
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

    # 3. Iterate and Update Nicknames
    await interaction.edit_original_response(content=f"{loading_emoji} Syncing {total_hc_members} members...")
    # Counters for summary
    counts = {'proc': 0, 'upd': 0, 'skip_match': 0, 'skip_no_ign': 0, 'skip_empty': 0, 'skip_hier': 0, 'fail_forbid': 0, 'fail_http': 0, 'fail_other': 0}
    bot_pos = guild.me.top_role.position
    last_prog_update_time = asyncio.get_event_loop().time()
    update_interval = 5.0 # Update progress every 5 seconds
    members_per_batch = 50 # Or update every N members

    for idx, member in enumerate(hc_members):
        counts['proc'] += 1
        member_id_str = str(member.id)

        # Hierarchy check: Bot must be higher than the member to change nick
        if bot_pos <= member.top_role.position:
            counts['skip_hier'] += 1
            continue # Skip this member

        # Get stored IGN
        stored_ign = ign_data.get(member_id_str)
        if not stored_ign:
            counts['skip_no_ign'] += 1
            continue # Skip if no IGN stored

        # Prepare target nickname
        target_nick = stored_ign.strip()
        if not target_nick:
            counts['skip_empty'] += 1
            continue # Skip if stored IGN is empty/whitespace

        # Truncate to Discord limit
        target_nick = target_nick[:32]

        # Check if update is needed
        if member.nick == target_nick:
            counts['skip_match'] += 1
            continue # Skip if nickname already matches

        # Attempt nickname update
        try:
            await member.edit(nick=target_nick, reason=f"Nickname Sync initiated by {interaction.user.id}")
            counts['upd'] += 1
            # Optional small delay to avoid hitting rate limits aggressively
            await asyncio.sleep(0.2)
        except discord.Forbidden:
            counts['fail_forbid'] += 1
            # Log this specific failure maybe? Or rely on summary.
        except discord.HTTPException as e_http:
            counts['fail_http'] += 1
            # Log potentially interesting HTTP errors
            print(f"SyncNick ({guild.name}): HTTP error {e_http.status} updating nick for {member.id}")
        except Exception as e_other:
            counts['fail_other'] += 1
            await log_error(guild, f"SyncNick: Unexpected error updating nick for {member.mention}", error=e_other, interaction=interaction) # Log unexpected errors


        # Update progress periodically
        now = asyncio.get_event_loop().time()
        if (now - last_prog_update_time > update_interval) or (counts['proc'] % members_per_batch == 0) or (counts['proc'] == total_hc_members):
            try:
                # Check if interaction still exists before editing
                await interaction.edit_original_response(content=f"{loading_emoji} Syncing... ({counts['proc']}/{total_hc_members})")
                last_prog_update_time = now
            except (discord.NotFound, discord.HTTPException):
                # If interaction edit fails, stop trying to update it but continue sync
                print(f"SyncNick ({guild.name}): Progress update failed (Interaction likely expired). Continuing sync...")
                last_prog_update_time = now + 999 # Prevent further attempts


    # 4. Send Final Summary
    end_time = discord.utils.utcnow()
    duration = (end_time - start_time).total_seconds()
    summary_embed = discord.Embed(title="✅ Nickname Sync Complete!", color=NERDY_YELLOW, timestamp=end_time)

    # Calculate total skips and fails
    total_skipped = counts['skip_match'] + counts['skip_no_ign'] + counts['skip_empty'] + counts['skip_hier']
    total_failed = counts['fail_forbid'] + counts['fail_http'] + counts['fail_other']

    summary_lines = [
        f"⏱️ **Duration:** {duration:.2f} seconds",
        f"👥 **Total HC Members Found:** {total_hc_members}",
        f"🔄 **Members Processed:** {counts['proc']}",
        f"✅ **Nicknames Updated:** {counts['upd']}",
        f"ℹ️ **Skipped (No Change Needed/Hierarchy):** {total_skipped}",
        f"   - Already Matched: {counts['skip_match']}",
        f"   - No/Empty IGN Stored: {counts['skip_no_ign'] + counts['skip_empty']}",
        f"   - Bot Hierarchy Too Low: {counts['skip_hier']}",
        f"❌ **Failed Updates:** {total_failed}",
        f"   - Permissions Error: {counts['fail_forbid']}",
        f"   - API/HTTP Error: {counts['fail_http']}",
        f"   - Other Errors: {counts['fail_other']}"
    ]
    summary_embed.description = "\n".join(summary_lines)

    # Try to edit the original deferred response first
    try:
        await interaction.edit_original_response(content=None, embed=summary_embed)
    except (discord.NotFound, discord.HTTPException) as e_edit:
        print(f"SyncNick ({guild.name}): Final summary edit failed ({e_edit}). Attempting followup.")
        # If edit fails (e.g., interaction expired), try sending as a new followup
        try:
            await interaction.followup.send(embed=summary_embed, ephemeral=True)
        except Exception as e_followup:
            print(f"SyncNick ({guild.name}): Final followup send also failed: {e_followup}")
            # Log the summary internally if user notification failed
            await log_error(guild, "SyncNick: Could not send final summary to user.", embed=summary_embed, interaction=interaction)
    except Exception as e_outer:
        print(f"SyncNick ({guild.name}): Unknown error sending final summary: {e_outer}")
        await log_error(guild, "SyncNick: Unknown error sending final summary.", error=e_outer, embed=summary_embed, interaction=interaction)


    # Log the detailed summary internally regardless of user message success
    log_embed = discord.Embed(title="Nickname Sync Finished", description="\n".join(summary_lines), color=NERDY_YELLOW)
    log_embed.set_footer(text=f"Initiated by {interaction.user}")
    await log_info(guild, "", embed=log_embed)


# --- Wither Command ---
@tree.command(name="wither", description="Temporarily remove roles from a user.")
@app_commands.describe(
    user="User to wither.",
    time="Duration in minutes (0.1 to 10, default 2)."
)
async def wither(interaction: discord.Interaction, user: discord.Member, time: app_commands.Range[float, 0.1, 10.0] = 2.0):
    guild = interaction.guild
    invoker = interaction.user # Member object of the user running the command

    # Pre-checks (must be done before deferring potentially)
    if not guild:
        await interaction.response.send_message("This command cannot be used outside a server.", ephemeral=True)
        return

    bot_member = guild.me # Bot's member object in the guild

    async def fail_check(log_reason: str, user_message: str):
        """Helper to send ephemeral failure message and log error."""
        # Ensure response is only sent once
        send_method = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        try:
            # Use create_embed helper
            await send_method(embed=create_embed(user_message, discord.Color.red()), ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded, discord.HTTPException) as e:
             # Catch common errors if sending fails
            print(f"Wither Check Fail Send Error: {type(e).__name__} - {e}")
        except Exception as e:
             print(f"Wither Check Fail Send Error (Unknown): {e}")
        # Log the failure reason
        await log_error(guild, f"Wither check fail ({invoker.name} -> {user.name}): {log_reason}", interaction=interaction)

    # 1. Permission Check (Invoker)
    if invoker.id not in ALLOWED_WITHER_IDS:
        # Defer ephemerally *before* sending fail message if not already done
        if not interaction.response.is_done():
            try: await interaction.response.defer(ephemeral=True)
            except discord.InteractionResponded: pass # Race condition handled
        await fail_check("Invoker permission denied.", "❌ You do not have permission to use this command.")
        return

    # 2. Defer Publicly (thinking state visible) - DO THIS *AFTER* invoker check
    # If the invoker check passed, we intend to proceed publicly.
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(thinking=True, ephemeral=False)
        except discord.InteractionResponded:
             # If it was already responded to (e.g., by the failed ephemeral defer above somehow)
             # This shouldn't normally happen if logic flow is correct, but handle defensively.
             print(f"Warning: Interaction {interaction.id} was already responded to before public defer in wither.")
             pass

    # 3. Target Checks (Self, Protected, Bot, Hierarchy)
    if user.id == invoker.id: await fail_check("Target self.", "🤨 You cannot wither yourself."); return
    # Check protected ID, allow if invoker IS the protected ID
    if user.id == SELF_PROTECTED_ID and invoker.id != SELF_PROTECTED_ID: await fail_check("Target protected.", f"😨 Cannot wither the protected user (<@{SELF_PROTECTED_ID}>)."); return
    if user.id == BOT_ID: await fail_check("Target bot.", "😭 You cannot wither me!"); return
    if user.bot: await fail_check("Target other bot.", "🤖 You cannot wither other bots."); return
    # Check guild owner, allow if invoker IS the owner
    if guild.owner_id and user.id == guild.owner_id and invoker.id != guild.owner_id: await fail_check("Target guild owner.", f"👑 You cannot wither the server owner (<@{guild.owner_id}>)."); return
    # Bot hierarchy check
    if bot_member.top_role.position <= user.top_role.position: await fail_check("Bot hierarchy low.", f"❌ My highest role ('{bot_member.top_role.name}') is not high enough to manage {user.mention}'s roles."); return
    # Invoker hierarchy check (unless invoker is owner)
    if invoker.id != guild.owner_id and invoker.top_role.position <= user.top_role.position: await fail_check("Invoker hierarchy low.", f"❌ Your highest role ('{invoker.top_role.name}') is not high enough to wither {user.mention}."); return
    # Bot permissions check
    if not bot_member.guild_permissions.manage_roles: await fail_check("Bot missing manage_roles perm.", "❌ I lack the `Manage Roles` permission needed for this command."); return


    # 4. Get Original Roles (excluding @everyone)
    original_roles = [r for r in user.roles if r.id != guild.default_role.id]
    if not original_roles:
        # Use followup since we deferred publicly
        await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} has no roles (other than @everyone) to remove.", discord.Color.orange()), ephemeral=False)
        return

    # --- Start of Main Wither Logic (Outer Try Block) ---
    try:
        # Calculate duration
        wither_seconds = min(max(1, int(time * 60)), int(MAX_WITHER_SECONDS or 600)) # Ensure bounds, convert minutes to seconds
        actual_minutes = wither_seconds / 60.0
        reason_wither = f"Withered by {invoker.name} ({invoker.id}) for {actual_minutes:.1f}m."

        # --- Role Removal ---
        # Filter roles the bot can actually manage based on hierarchy
        roles_to_remove_actually = [r for r in original_roles if bot_member.top_role.position > r.position]
        skipped_roles_remove = [r for r in original_roles if r not in roles_to_remove_actually]

        if not roles_to_remove_actually:
             await interaction.followup.send(embed=create_embed(f"ℹ️ Cannot wither {user.display_name}: None of their roles are below my highest role.", color=discord.Color.orange()), ephemeral=False)
             await log_info(guild, f"Wither attempt on {user.name} by {invoker.name} failed: No manageable roles.")
             return

        # Perform role removal using edit (replace roles with only @everyone)
        # Ensure @everyone role exists (should always be true)
        everyone_role = guild.default_role
        await user.edit(roles=[everyone_role], reason=reason_wither)

        # --- Send Confirmation ---
        roles_removed_names = (', '.join(f"`{r.name}`" for r in roles_to_remove_actually) or 'None Manageable')
        # Truncate if too long for embed description field part
        if len(roles_removed_names) > 900: roles_removed_names = roles_removed_names[:897] + "..."

        wither_desc = f"{user.mention} has been withered by {invoker.mention} for **{actual_minutes:.1f} minutes**!\n\n**Roles Removed:** {roles_removed_names}"
        if skipped_roles_remove:
            skipped_names = (', '.join(f"`{r.name}`" for r in skipped_roles_remove))
            if len(skipped_names) > 100: skipped_names = skipped_names[:97] + "..."
            wither_desc += f"\n*(Skipped {len(skipped_roles_remove)} role(s) due to hierarchy: {skipped_names})*"

        await interaction.followup.send(embed=create_embed(title="🌪️ Wither Cast! 🌪️", description=wither_desc, color=discord.Color.dark_purple()), ephemeral=False)

        # --- Log Action ---
        log_msg = f"`{user.name}` ({user.id}) withered by `{invoker.name}` ({invoker.id}) for {actual_minutes:.1f}m. Roles removed: {', '.join(r.name for r in roles_to_remove_actually) or 'N/A'}."
        if skipped_roles_remove: log_msg += f" Skipped (hierarchy): {', '.join(r.name for r in skipped_roles_remove)}."
        await log_info(guild, log_msg)

        # --- Wait Period ---
        await asyncio.sleep(wither_seconds)

        # --- Role Restore (Inner Try Block) ---
        try:
            # Refetch member and bot objects to ensure data/perms are current
            # Use fetch_member as user might have rejoined/roles changed externally
            member_after = await guild.fetch_member(user.id)
            # Fetch bot member too in case its roles changed
            bot_member_after = await guild.fetch_member(bot.user.id) if bot.user else await guild.fetch_me()
            reason_restore = f"Wither expired after {actual_minutes:.1f}m. Restoring roles."

            # --- Pre-Restore Checks ---
            # Check bot permissions again before restore attempt
            if not bot_member_after.guild_permissions.manage_roles:
                await log_error(guild, f"Wither restore fail for {member_after.mention}: Bot lost `Manage Roles` permission.")
                # Attempt to notify in channel
                if interaction.channel: await interaction.channel.send(f"⚠️ Failed to restore roles for {member_after.mention}: Bot permissions missing.")
                return

            # Check bot hierarchy again (user might have gotten higher roles)
            if bot_member_after.top_role.position <= member_after.top_role.position:
                await log_error(guild, f"Wither restore fail: Bot hierarchy now too low for {member_after.mention}.")
                if interaction.channel: await interaction.channel.send(f"⚠️ Failed to restore roles for {member_after.mention}: Hierarchy issue.")
                return

            # --- Determine Roles to Restore ---
            # Check existence and hierarchy for each original role again
            valid_restore_roles = [] # Roles that still exist and bot can assign
            skipped_deleted_names = [] # Names of roles that were deleted
            skipped_hierarchy_names = [] # Names of roles now above bot

            original_role_ids = {r.id for r in original_roles} # Set for efficient lookup
            current_valid_roles = {r.id: r for r in guild.roles} # Map of current roles in guild

            for role_id in original_role_ids:
                role_obj = current_valid_roles.get(role_id)
                if not role_obj:
                    # Find original name if possible (might be inaccurate if ID reused)
                    original_name = next((r.name for r in original_roles if r.id == role_id), f"ID {role_id}")
                    skipped_deleted_names.append(original_name)
                elif bot_member_after.top_role.position > role_obj.position:
                    valid_restore_roles.append(role_obj) # Add the valid Role object
                else:
                    skipped_hierarchy_names.append(role_obj.name)

            if skipped_deleted_names: await log_info(guild, f"Wither restore notice for {member_after.name}: Roles seem deleted: {', '.join(skipped_deleted_names)}.")
            if skipped_hierarchy_names: await log_info(guild, f"Wither restore notice for {member_after.name}: Roles skipped (hierarchy): {', '.join(skipped_hierarchy_names)}.")

            if not valid_restore_roles:
                await log_info(guild, f"Wither restore: No valid roles left to restore for {member_after.name}.")
                if interaction.channel: await interaction.channel.send(f"ℹ️ Wither ended for {member_after.mention}, but no valid roles could be restored (deleted or hierarchy issues).")
                return

            # --- Attempt Role Restore ---
            # Combine valid roles to restore with the @everyone role
            final_roles_to_set = valid_restore_roles + [guild.default_role]
            await member_after.edit(roles=final_roles_to_set, reason=reason_restore)

            # --- Send Restore Confirmation ---
            restored_names = (', '.join(f"`{r.name}`" for r in valid_restore_roles))
            restore_msg = f"✨ {member_after.mention}'s roles have been restored!"
            # Add details about skipped roles if any
            if skipped_deleted_names or skipped_hierarchy_names:
                restore_msg += "\n*(Some original roles were not restored due to being deleted or hierarchy issues.)*"

            # Use followup for restore message if original interaction is still valid
            # otherwise send to channel directly.
            try:
                 await interaction.followup.send(embed=create_embed(restore_msg, color=NERDY_YELLOW), ephemeral=False)
            except (discord.NotFound, discord.HTTPException) as e_followup:
                print(f"Wither restore followup failed ({e_followup}), attempting to send to channel.")
                # Fallback to sending in the original channel if followup fails
                if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                    try: await interaction.channel.send(embed=create_embed(restore_msg, color=NERDY_YELLOW))
                    except Exception as e_chan_send: await log_error(guild, "Wither failed channel send after followup fail", error=e_chan_send)
                else: await log_info(guild, f"Wither restore OK for {member_after.mention}, but couldn't send followup or channel message.")

            await log_info(guild, f"Restored roles for `{member_after.name}` ({member_after.id}). Roles: {', '.join(r.name for r in valid_restore_roles)}")

        # --- Inner Except Blocks (Handling Restore Errors) ---
        except discord.NotFound:
            # User left the server during the wither period
            await log_info(guild, f"Wither restore skipped: User `{user.name}` ({user.id}) left the server.")
            # Attempt to notify channel
            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                try: await interaction.channel.send(f"ℹ️ Wither ended for {user.display_name}, but they have left the server.")
                except Exception: pass # Ignore failure to notify
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
            # Catch any other unexpected errors during restore
            await log_error(guild, f"Wither restore failed: Unexpected error for {user.name} ({user.id}).", error=e)
            if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
                try: await interaction.channel.send(f"⚠️ An unexpected error occurred trying to restore roles for {user.display_name}.")
                except Exception: pass

    # --- Outer Except Blocks (Handling Role Removal Errors) ---
    except discord.Forbidden:
        # This implies the initial role removal failed
        await log_error(guild, f"Wither initial remove failed: Forbidden for {user.name} ({user.id}).", interaction=interaction)
        # Try to edit the deferred response to show failure
        try: await interaction.edit_original_response(content=f"❌ Failed to remove roles for {user.display_name}: Permissions error.", embed=None, view=None)
        except Exception: pass # Ignore if editing fails
    except discord.HTTPException as e:
        await log_error(guild, f"Wither initial remove failed: API error for {user.name} ({user.id}).", error=e, interaction=interaction)
        try: await interaction.edit_original_response(content=f"❌ Failed to remove roles for {user.display_name}: Discord API error.", embed=None, view=None)
        except Exception: pass
    except Exception as e:
        # Catch any other unexpected errors during the initial removal phase
        await log_error(guild, f"Wither initial remove failed: Unexpected error for {user.name} ({user.id}).", error=e, interaction=interaction)
        try: await interaction.edit_original_response(content=f"❌ An unexpected error occurred trying to wither {user.display_name}.", embed=None, view=None)
        except Exception: pass


# --- MODIFIED Nerd Help Command ---
@tree.command(name="nerdhelp", description="Show the list of available bot commands.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return
    # Ensure bot object and user are available before proceeding
    if not bot or not bot.user:
        print("Error: Bot object not available in nerdhelp command.") # Log issue
        await interaction.response.send_message("Bot is not fully ready, cannot generate help. Please try again shortly.", ephemeral=True)
        return

    # Check if command_ids dictionary is populated (important for clickable links)
    if not command_ids:
        print("Warning: command_ids dictionary is empty during nerdhelp execution! Syncing may have failed.")
        # Optionally inform the user, or just let the fallback work
        # await interaction.response.send_message("Command information might be loading. If commands aren't clickable, try again later.", ephemeral=True)

    embed = discord.Embed(title="🤓 Pingslave Bot Commands", description="Click on a command name to use it!", color=NERDY_YELLOW)

    # Get channel mentions safely
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    list_channel_mention = list_channel.mention if list_channel else f"Channel ID `{HC_MEMBER_LIST_CHANNEL_ID}`"
    # Filter allowed channels to only those existing in the current guild
    allowed_ch_mentions = [f"<#{ch_id}>" for ch_id in ALLOWED_CHANNEL_IDS if guild.get_channel(ch_id)]
    allowed_chs_str = ", ".join(allowed_ch_mentions) or "`None Configured or Found`"

    # --- Build Embed Fields using get_cmd_mention ---
    embed.add_field(name="\u200B\n🔑 **Verification & HC Management**", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('verify')} `<user>`", value="> Grants `Verified`, removes `Unverified`.\n> *Requires:* `Manage Roles`", inline=True)
    embed.add_field(name=f"{get_cmd_mention('unverify')} `<user>`", value="> Removes `Verified`, adds `Unverified`.\n> *Requires:* `Manage Roles`", inline=True)
    embed.add_field(name="\u200B", value="\u200B", inline=False) # Spacer field
    embed.add_field(name=f"{get_cmd_mention('hcverify')} `<user> <IGN>`", value="> Adds `HC`/`Verified`, stores IGN, sets nick, updates list.\n> *Requires:* `Manage Roles`", inline=False)
    embed.add_field(name=f"{get_cmd_mention('unhcverify')} `<user>`", value="> Removes `HC`, resets nick, updates list.\n> *Requires:* `Manage Roles`", inline=False)

    embed.add_field(name="\u200B\n📊 **[HC1] Member List**", value="*Lists show `Username#Tag ➔ IGN`*", inline=False)
    embed.add_field(name=f"{get_cmd_mention('hcmembers')}", value=f"> Interactive HC list.\n> *Requires:* `Everyone` (in {allowed_chs_str})", inline=True)
    embed.add_field(name=f"{get_cmd_mention('refresh')}", value=f"> Updates static list in {list_channel_mention}.\n> *Requires:* `Manage Roles`", inline=True)

    embed.add_field(name="\u200B\n\n⚙️ **Utilities**", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('bulkupdate')}", value="> Bulk update IGNs via form.\n> *Requires:* `Manage Roles`", inline=True)
    embed.add_field(name=f"{get_cmd_mention('syncnicknames')}", value="> Syncs HC nicks to stored IGNs.\n> *Requires:* `Manage Nicknames`", inline=True)
    embed.add_field(name="\u200B", value="\u200B", inline=False) # Spacer field
    embed.add_field(name=f"{get_cmd_mention('wither')} `<user> [time]`", value=f"> Temporarily removes roles (0.1-{MAX_WITHER_SECONDS / 60:.0f} min).\n> *Requires:* `Special Permission` (Specific User IDs)", inline=True)
    embed.add_field(name=f"{get_cmd_mention('nerdhelp')}", value="> Shows this help message.\n> *Requires:* `Everyone`", inline=True)

    # --- Footer and Thumbnail ---
    embed.set_footer(text="Bot by TheNerd | sweet_honey")
    # Set thumbnail if bot has an avatar
    if bot.user and bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)

    # --- Send Response ---
    try:
        # Send publicly as it's a help command
        await interaction.response.send_message(embed=embed, ephemeral=False)
    except Exception as e:
         # Log error if sending fails
        print(f"Error sending nerdhelp response: {e}")
        await log_error(guild, "Failed to send nerdhelp response", error=e, interaction=interaction)
        # Try a followup if initial send failed (though unlikely for send_message)
        try:
            if interaction.response.is_done():
                 await interaction.followup.send("Failed to generate help embed.", ephemeral=True)
        except Exception: pass


# --- Bot Startup ---
if __name__ == "__main__":
    print("--- Initializing Pingslave Bot ---")
    # Essential checks before starting
    if not TOKEN:
        print("CRITICAL: DISCORD_BOT_TOKEN environment variable not found. Bot cannot start.")
    elif not supabase:
        print("CRITICAL: Supabase client initialization failed. Check URL/Key and connection. Bot may have limited functionality.")
        # Decide if you want the bot to run without Supabase or exit
        # exit(1) # Example: exit if Supabase fails
    else:
        print("Discord Token and Supabase Client OK.")
        print("Starting Keep Alive Flask server...")
        keep_alive() # Starts Flask in a separate thread

        try:
            print("Attempting to start Discord Bot...")
            # --- IMPORTANT: REMOVED log_handler=None ---
            # This allows default discord.py logging to show connection/sync status
            bot.run(TOKEN)
        except discord.LoginFailure:
            # Token is invalid
            print("CRITICAL: Discord Login Failed. The provided DISCORD_BOT_TOKEN is invalid or expired.")
        except discord.PrivilegedIntentsRequired:
            # Member intent is likely missing in Discord Dev Portal settings
            print("CRITICAL: Privileged Intents (Server Members Intent) required but not enabled in the Discord Developer Portal.")
        except Exception as e:
            # Catch any other unexpected errors during startup
            print(f"CRITICAL: Unexpected error during bot execution: {e}")
            print(traceback.format_exc()) # Print full traceback for debugging

    print("--- Bot process has potentially ended (check logs for specific errors) ---")
