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
from typing import Optional, Tuple, List, Dict

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
                 await interaction.followup.send("Error updating view.", ephemeral=True)
        except discord.NotFound:
            print(f"Paginator edit fail: Original message {self.message.id if self.message else 'Unknown'} not found.")
            for item in self.children:
                if isinstance(item, Button): item.disabled = True
        except discord.HTTPException as e:
            await log_error(interaction.guild, "Paginator edit fail (HTTP)", error=e, interaction=interaction)
        except Exception as e:
            await log_error(interaction.guild, "Paginator edit fail (General)", error=e, interaction=interaction)

    @button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="hc_prev_interactive", row=0)
    async def previous_button(self, interaction: discord.Interaction, b: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.edit_message(interaction)
        else:
            try:
                await interaction.response.defer()
            except discord.InteractionResponded: pass
            except discord.NotFound: print("Previous Button: Interaction expired before defer.")
            except Exception as e: await log_error(interaction.guild, "Previous Button Defer Error", e, interaction)

    @button(label="Next", style=discord.ButtonStyle.blurple, custom_id="hc_next_interactive", row=0)
    async def next_button(self, interaction: discord.Interaction, b: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.edit_message(interaction)
        else:
            try:
                await interaction.response.defer()
            except discord.InteractionResponded: pass
            except discord.NotFound: print("Next Button: Interaction expired before defer.")
            except Exception as e: await log_error(interaction.guild, "Next Button Defer Error", e, interaction)

    async def on_timeout(self):
        if self.message:
            try:
                for item in self.children:
                    if isinstance(item, Button): item.disabled = True
                await self.message.edit(view=self)
                print(f"Paginator timeout: Disabled buttons on message {self.message.id}")
            except discord.NotFound: print(f"Paginator timeout edit fail: Message {self.message.id} not found.")
            except Exception as e:
                 guild = self.message.guild
                 if guild: await log_error(guild, f"Paginator timeout edit fail on message {self.message.id}", error=e)
                 else: print(f"Paginator timeout edit fail on message {self.message.id} (guild unavailable): {e}")
        self.stop()


# --- Core HC List Logic ---
async def fetch_hc_member_data(guild: discord.Guild) -> Tuple[List[Tuple[Optional[discord.Member], str]], int]:
    """ Fetches HC members (sorted by username#discriminator) and IGNs."""
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"HC Role {ADD_ROLE_ID_HC} not found.")
        return [], 0
    if not guild.chunked:
        try:
            await guild.chunk(cache=True)
            print(f"Chunked guild {guild.name} for fetch_hc_member_data.")
        except Exception as e:
             await log_error(guild, "Guild chunking failed in fetch_hc_member_data", error=e)

    members_with_role = [m for m in guild.members if hc_role in m.roles and not m.bot]
    total = len(members_with_role)
    members_sorted = sorted(members_with_role, key=lambda m: (m.name.lower(), m.discriminator))
    ids = [str(m.id) for m in members_sorted]
    ign_map = {}
    if supabase and ids:
        try:
            chunk_size = 500
            for i in range(0, len(ids), chunk_size):
                chunk = ids[i:i+chunk_size]
                resp = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").in_("discord_id", chunk).execute())
                if resp and hasattr(resp, 'data') and resp.data:
                    ign_map.update({r['discord_id']: r.get("ingame_name") or "Unknown" for r in resp.data})
                await asyncio.sleep(0.1)
        except ConnectionError as e:
             await log_error(guild, "Supabase connection unavailable during IGN fetch.", error=e)
             ign_map = {mid: "DB Connection Err" for mid in ids}
        except APIError as e:
             await log_error(guild, "Supabase API Error during IGN fetch.", error=e)
             ign_map = {mid: "DB API Err" for mid in ids}
        except Exception as e:
            await log_error(guild, "Unexpected error during IGN fetch.", error=e)
            ign_map = {mid: "DB Fetch Err" for mid in ids}

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
        full_desc = "\n".join(desc)
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
            async for msg in chan.history(limit=max(num_new, 15)):
                if msg.author and msg.author.id == bot.user.id and msg.embeds:
                     if msg.embeds[0].title and msg.embeds[0].title == HC_LIST_EMBED_TITLE:
                          existing.append(msg)
        except discord.Forbidden:
             await log_error(guild, f"History permission denied in {chan.mention} during static list update.")
             return
        except Exception as e:
            await log_error(guild, "Error fetching history for static list update", error=e)
            return

        existing.sort(key=lambda m: m.created_at)
        num_exist = len(existing)
        print(f"Static List Update ({guild.name}): Found {num_exist} existing bot messages, Need to display {num_new} pages.")

        tasks = []
        messages_to_delete = []

        for i in range(num_new):
            await asyncio.sleep(1.2)
            if i < num_exist:
                print(f"  Editing message {existing[i].id} (Page {i+1})")
                tasks.append(existing[i].edit(embed=new_embeds[i]))
            else:
                print(f"  Sending new message (Page {i+1})")
                tasks.append(chan.send(embed=new_embeds[i]))

        if num_exist > num_new:
            messages_to_delete = existing[num_new:]
            print(f"  Identified {len(messages_to_delete)} surplus messages to delete.")

        results = await asyncio.gather(*tasks, return_exceptions=True)
        edit_send_errors = 0
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                edit_send_errors += 1
                action = "Edit" if i < num_exist else "Send"
                msg_id = existing[i].id if i < num_exist else "New"
                await log_error(guild, f"Static list {action} failed for Page {i+1} (MsgID: {msg_id})", error=res)

        delete_errors = 0
        if messages_to_delete:
            can_bulk_delete = perms.manage_messages and len(messages_to_delete) > 1
            if can_bulk_delete:
                try:
                    await chan.delete_messages(messages_to_delete)
                    print(f"  Bulk deleted {len(messages_to_delete)} surplus messages.")
                except discord.HTTPException as e:
                    print(f"  Bulk delete failed (HTTP {e.status}): {e.text}. Falling back to individual deletion.")
                    can_bulk_delete = False
                except Exception as e:
                    await log_error(guild, f"Bulk delete failed unexpectedly", error=e)
                    can_bulk_delete = False

            if not can_bulk_delete:
                 for msg_del in messages_to_delete:
                    await asyncio.sleep(1.2)
                    try:
                        await msg_del.delete()
                        print(f"  Individually deleted surplus message {msg_del.id}")
                    except Exception as e:
                        delete_errors += 1
                        await log_error(guild, f"Failed to delete surplus message {msg_del.id}", error=e)

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
    global BOT_ID, command_ids
    if bot.user:
        BOT_ID = bot.user.id
        print(f"Logged in as {bot.user} (ID: {BOT_ID})")
        print(f"Discord.py v{discord.__version__}")
    else:
        print("CRITICAL ERROR: Bot user object not found on ready.")
        return

    print("Syncing application commands...")
    synced_commands = []
    try:
        synced_commands = await tree.sync()
        print(f"Synced {len(synced_commands)} application commands globally.")
        command_ids.clear()
        for cmd in synced_commands:
            if isinstance(cmd, app_commands.Command):
                command_ids[cmd.name] = cmd.id
                print(f"  Stored ID for /{cmd.name}: {cmd.id}")
        print(f"Stored command IDs: {command_ids}")
    except Exception as e:
        print(f"Command Sync failed: {e}")
        first_guild = bot.guilds[0] if bot.guilds else None
        if first_guild:
            await log_error(first_guild, "Application Command Sync failed on startup.", error=e)

    if not bot.guilds:
        print("Bot is not currently in any guilds.")
        return

    print(f"Performing initial setup for {len(bot.guilds)} guild(s)...")
    guilds_to_process = list(bot.guilds)
    for guild in guilds_to_process:
        print(f"  Processing guild: {guild.name} (ID: {guild.id})")
        try:
            await log_info(guild, f"Bot ready and online. Synced {len(synced_commands)} commands.")
            await update_hc_member_list(guild)
            await asyncio.sleep(1)
        except Exception as e:
            await log_error(guild, f"Error during on_ready setup for this guild", error=e)
    print("Initial setup loop complete.")


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if after.bot or before.roles == after.roles:
        return
    guild = after.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role: return

    had_hc_role = hc_role in before.roles
    has_hc_role = hc_role in after.roles

    if had_hc_role != has_hc_role:
        action = "added to" if has_hc_role else "removed from"
        await log_info(guild, f"HC role (`{hc_role.name}`) {action} user {after.mention} (`{after.id}`). Triggering static list update.")
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
    error_to_log = error

    if isinstance(error, app_commands.CommandNotFound):
        print(f"CommandNotFound error received for interaction: {interaction.data.get('name', 'N/A')}")
        return
    elif isinstance(error, app_commands.MissingPermissions):
        perms = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
        user_msg = f"❌ You lack the required permissions: {perms}"
        log_desc = f"User Missing Permissions: {perms}"
        error_to_log = None
    elif isinstance(error, app_commands.BotMissingPermissions):
        perms = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
        user_msg = f"❌ I lack the required permissions: {perms}. Please contact an admin."
        log_desc = f"Bot Missing Permissions: {perms}"
        error_to_log = None
    elif isinstance(error, app_commands.CheckFailure):
        user_msg = "❌ You do not meet the requirements to use this command."
        log_desc = f"Check Failure ({type(error).__name__})"
        error_to_log = None
    elif isinstance(error, app_commands.CommandInvokeError):
        original_error = error.original
        error_to_log = original_error
        user_msg = f"❌ An error occurred while running the command: `{type(original_error).__name__}`"
        log_desc = "Command Invoke Error"
        print(f"CommandInvokeError in command '{interaction.command.name if interaction.command else 'Unknown'}':")
        traceback.print_exception(type(original_error), original_error, original_error.__traceback__)
    elif isinstance(error, app_commands.TransformerError):
        user_msg = f"❌ Invalid input provided: {error}"
        log_desc = f"Transformer Error: {error}"
        error_to_log = error
    elif isinstance(error, app_commands.CommandOnCooldown):
        user_msg = f"⏳ This command is on cooldown. Please try again in {error.retry_after:.1f} seconds."
        log_desc = f"Command Cooldown Hit ({error.retry_after:.1f}s)"
        error_to_log = None
    elif isinstance(error, app_commands.NoPrivateMessage):
         user_msg = "❌ This command cannot be used in Direct Messages."
         log_desc = "Command used in DM"
         error_to_log = None
    else:
        log_desc = f"Unknown App Command Error Type: `{type(error).__name__}`"

    await log_error(guild, log_desc, error=error_to_log, interaction=interaction)

    try:
        if interaction.response.is_done():
            await interaction.followup.send(user_msg, ephemeral=True)
        else:
            await interaction.response.send_message(user_msg, ephemeral=True)
    except discord.NotFound: print(f"Error Handler: Interaction {interaction.id} already expired.")
    except discord.InteractionResponded:
         try: await interaction.followup.send(user_msg, ephemeral=True)
         except Exception as e: print(f"Error Handler: Failed to send followup after InteractionResponded: {e}")
    except Exception as e: print(f"Error Handler: Failed to send error message to user: {e}")


# --- Modals ---
def create_embed(description: str, color: discord.Color = NERDY_YELLOW, title: Optional[str] = None) -> discord.Embed:
     embed = discord.Embed(title=title, description=description, color=color)
     return embed

class BulkUpdateModal(Modal, title="Bulk Update IGNs"):
    data = TextInput( label="Paste list (username#tag ➔ IGN)", style=discord.TextStyle.paragraph, placeholder="ExampleUser#1234 ➔ CoolIGN\nAnotherUser ➔ AnotherIGN\n(One entry per line, format flexible)", required=True, min_length=5, max_length=4000 )
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
        member_map_id = {}
        member_map_name_disc = {}
        member_map_name_only = {}
        try:
            if not guild.chunked: await guild.chunk(cache=True)
            for m in guild.members:
                if m.bot: continue
                member_map_id[str(m.id)] = m
                if m.discriminator != '0': member_map_name_disc[f"{m.name}#{m.discriminator}".lower()] = m
                member_map_name_only[m.name.lower()] = m
                member_map_name_only[m.display_name.lower()] = m
        except Exception as e:
            await log_error(guild, "Bulk update member fetch/chunking fail", error=e, interaction=interaction)
            await interaction.followup.send("❌ Error fetching server members. Cannot process update.", ephemeral=True)
            return
        success_count, fail_count, not_found_count = 0, 0, 0
        log_details = []
        payload = []
        for idx, line in enumerate(lines, 1):
            line = line.strip();
            if not line: continue
            parts = line.split("➔", 1)
            if len(parts) != 2:
                fail_count += 1; log_details.append(f"❌ L{idx}: Invalid format (Missing '➔') - Line: `{line[:50]}`"); continue
            identifier_raw, ign_raw = map(str.strip, parts); ign = ign_raw
            identifier_clean = identifier_raw.lstrip('0123456789. '); identifier_lower = identifier_clean.lower()
            if not identifier_clean or not ign:
                fail_count += 1; log_details.append(f"❌ L{idx}: Missing user identifier or IGN - User: `{identifier_raw[:30]}`, IGN: `{ign_raw[:30]}`"); continue
            member: Optional[discord.Member] = None
            if identifier_clean.isdigit(): member = member_map_id.get(identifier_clean)
            if not member: member = member_map_name_disc.get(identifier_lower)
            if not member: member = member_map_name_only.get(identifier_lower)
            if not member:
                fail_count += 1; not_found_count += 1; log_details.append(f"❓ L{idx}: User not found - Identifier: `{discord.utils.escape_markdown(identifier_clean)}`"); continue
            if len(ign) > 100: ign = ign[:100]; log_details.append(f"⚠️ L{idx}: IGN for {member.mention} truncated.")
            payload.append({"discord_id": str(member.id), "discord_name": f"{member.name}#{member.discriminator}" if member.discriminator != '0' else member.name, "ingame_name": ign})
        db_error = None
        if payload:
            try:
                await run_supabase_sync(lambda: supabase.table("hc_members").upsert(payload, on_conflict="discord_id").execute())
                success_count = len(payload)
            except Exception as e:
                db_error = e; fail_count += len(payload); success_count = 0
                await log_error(guild, "Bulk update Supabase upsert failed", error=e, interaction=interaction)
                log_details.append(f"🔥 **Database Error:** Failed to save {len(payload)} entries.")
        result_color = discord.Color.green() if fail_count == 0 and not db_error else (discord.Color.orange() if success_count > 0 else discord.Color.red())
        embed = discord.Embed(title="Bulk IGN Update Results", color=result_color)
        summary = (f"Processed Lines: {len(lines)}\n✅ Successful Updates: {success_count}\n"
                   f"❌ Failed Entries: {fail_count} (Not Found: {not_found_count}, Format/Data Issues: {fail_count - not_found_count})\n"
                   f"{'🔥 Database Error occurred!' if db_error else ''}")
        embed.description = summary
        if log_details:
            log_output = "\n".join(log_details)
            if len(log_output) > 1024: log_output = log_output[:1021] + "..."
            embed.add_field(name="Details", value=log_output, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
        summary_for_log = summary.replace('\n', ' | ')
        await log_info(guild, f"Bulk update by `{interaction.user}` completed. Results: {summary_for_log}")
        if success_count > 0:
            await asyncio.sleep(0.5); await update_hc_member_list(guild)


# --- Slash Commands ---

# --- Verify Command ---
@tree.command(name="verify", description="Verify a standard user (adds Verified, removes Unverified).")
@app_commands.describe(user="The user to verify.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    if not guild: await interaction.response.send_message("This command can only be used in a server.", ephemeral=True); return

    role_to_remove = guild.get_role(REMOVE_ROLE_ID)
    role_to_add = guild.get_role(ADD_ROLE_ID_VERIFY)

    missing_roles = []
    if REMOVE_ROLE_ID and not role_to_remove: missing_roles.append(f"Unverified Role (ID: {REMOVE_ROLE_ID})")
    if ADD_ROLE_ID_VERIFY and not role_to_add: missing_roles.append(f"Verified Role (ID: {ADD_ROLE_ID_VERIFY})")
    if missing_roles:
        await interaction.response.send_message(f"❌ Setup Error: Roles not found: {', '.join(missing_roles)}.", ephemeral=True)
        await log_error(guild, f"Verify failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return
    if not role_to_add:
         await interaction.response.send_message(f"❌ Setup Error: Verified Role (ID: {ADD_ROLE_ID_VERIFY}) not found.", ephemeral=True); return

    bot_member = guild.me
    hierarchy_fail = False; hierarchy_reason = ""
    if bot_member.top_role.position <= role_to_add.position: hierarchy_fail=True; hierarchy_reason=f"Cannot assign '{role_to_add.name}'."
    elif role_to_remove and bot_member.top_role.position <= role_to_remove.position: hierarchy_fail=True; hierarchy_reason=f"Cannot remove '{role_to_remove.name}'."
    if hierarchy_fail:
        await interaction.response.send_message(f"❌ Hierarchy Error: {hierarchy_reason} (My role isn't high enough).", ephemeral=True)
        await log_error(guild, f"Verify failed: Bot hierarchy issue. Reason: {hierarchy_reason}", interaction=interaction)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)
    actions_taken = []; reason = f"Verified by {interaction.user}"; modified = False
    try:
        has_verified = role_to_add in user.roles
        has_unverified = role_to_remove and role_to_remove in user.roles
        if has_verified and not has_unverified: await interaction.followup.send(f"ℹ️ {user.mention} is already verified.", ephemeral=True); return
        roles_to_add_list = []; roles_to_remove_list = []
        if has_unverified: roles_to_remove_list.append(role_to_remove); actions_taken.append(f"➖ Removed `{role_to_remove.name}`"); modified = True
        if not has_verified: roles_to_add_list.append(role_to_add); actions_taken.append(f"➕ Added `{role_to_add.name}`"); modified = True
        if modified:
            if roles_to_add_list: await user.add_roles(*roles_to_add_list, reason=reason)
            if roles_to_remove_list: await user.remove_roles(*roles_to_remove_list, reason=reason)
            await log_info(guild, f"`{interaction.user}` verified {user.mention}. Actions: {', '.join(actions_taken)}.")
            await interaction.followup.send(f"✅ Successfully verified {user.mention}.", ephemeral=True)
            public_embed = create_embed(f"✅ **{user.display_name}** has been verified!\n" + "\n".join(actions_taken), discord.Color.green())
            try:
                if isinstance(interaction.channel, discord.TextChannel): await interaction.channel.send(embed=public_embed)
                else: await log_info(guild, f"Skipped public verify notification for {user.mention} (non-text channel).")
            except (discord.Forbidden, discord.HTTPException) as e: await log_error(guild,"Failed to send public verify notification", error=e, interaction=interaction)
        else: await interaction.followup.send("ℹ️ No role changes were needed.", ephemeral=True)
    except discord.Forbidden:
        await log_error(guild, "Verify failed: Forbidden.", interaction=interaction)
        await interaction.followup.send("❌ Failed: Permissions error.", ephemeral=True)
    except discord.HTTPException as e:
        await log_error(guild, "Verify failed: API error.", error=e, interaction=interaction)
        await interaction.followup.send("❌ Failed: Discord API error.", ephemeral=True)
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
    if not guild: await interaction.response.send_message("This command can only be used in a server.", ephemeral=True); return

    role_to_add = guild.get_role(REMOVE_ROLE_ID)
    role_to_remove = guild.get_role(ADD_ROLE_ID_VERIFY)

    missing_roles = []
    if REMOVE_ROLE_ID and not role_to_add: missing_roles.append(f"Unverified Role (ID: {REMOVE_ROLE_ID})")
    if ADD_ROLE_ID_VERIFY and not role_to_remove: missing_roles.append(f"Verified Role (ID: {ADD_ROLE_ID_VERIFY})")
    if missing_roles:
        await interaction.response.send_message(f"❌ Setup Error: Roles not found: {', '.join(missing_roles)}.", ephemeral=True)
        await log_error(guild, f"Unverify failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction)
        return
    if not role_to_add:
         await interaction.response.send_message(f"❌ Setup Error: Unverified Role (ID: {REMOVE_ROLE_ID}) not found.", ephemeral=True); return

    bot_member = guild.me
    hierarchy_fail = False; hierarchy_reason = ""
    if bot_member.top_role.position <= role_to_add.position: hierarchy_fail=True; hierarchy_reason=f"Cannot assign '{role_to_add.name}'."
    elif role_to_remove and bot_member.top_role.position <= role_to_remove.position: hierarchy_fail=True; hierarchy_reason=f"Cannot remove '{role_to_remove.name}'."
    if hierarchy_fail:
         await interaction.response.send_message(f"❌ Hierarchy Error: {hierarchy_reason} (My role isn't high enough).", ephemeral=True)
         await log_error(guild, f"Unverify failed: Bot hierarchy issue. Reason: {hierarchy_reason}", interaction=interaction)
         return

    await interaction.response.defer(thinking=True, ephemeral=True)
    actions_taken = []; reason = f"Unverified by {interaction.user}"; modified = False
    try:
        has_unverified = role_to_add in user.roles
        has_verified = role_to_remove and role_to_remove in user.roles
        if has_unverified and not has_verified: await interaction.followup.send(f"ℹ️ {user.mention} is already Unverified.", ephemeral=True); return
        roles_to_add_list = []; roles_to_remove_list = []
        if has_verified: roles_to_remove_list.append(role_to_remove); actions_taken.append(f"➖ Removed `{role_to_remove.name}`"); modified = True
        if not has_unverified: roles_to_add_list.append(role_to_add); actions_taken.append(f"➕ Added `{role_to_add.name}`"); modified = True
        if modified:
            if roles_to_add_list: await user.add_roles(*roles_to_add_list, reason=reason)
            if roles_to_remove_list: await user.remove_roles(*roles_to_remove_list, reason=reason)
            await log_info(guild, f"`{interaction.user}` unverified {user.mention}. Actions: {', '.join(actions_taken)}.")
            await interaction.followup.send(f"✅ Successfully unverified {user.mention}.", ephemeral=True)
            public_embed = create_embed(f"↩️ **{user.display_name}** has been unverified.\n" + "\n".join(actions_taken), discord.Color.orange())
            try:
                 if isinstance(interaction.channel, discord.TextChannel): await interaction.channel.send(embed=public_embed)
                 else: await log_info(guild, f"Skipped public unverify notification for {user.mention} (non-text channel).")
            except (discord.Forbidden, discord.HTTPException) as e: await log_error(guild, "Failed to send public unverify notification", error=e, interaction=interaction)
        else: await interaction.followup.send("ℹ️ No role changes were needed.", ephemeral=True)
    except discord.Forbidden:
        await log_error(guild, "Unverify failed: Forbidden.", interaction=interaction)
        await interaction.followup.send("❌ Failed: Permissions error.", ephemeral=True)
    except discord.HTTPException as e:
        await log_error(guild, "Unverify failed: API error.", error=e, interaction=interaction)
        await interaction.followup.send("❌ Failed: Discord API error.", ephemeral=True)
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
    if not guild: await interaction.response.send_message("This command must be used in a server.", ephemeral=True); return
    if not supabase:
        await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
        await log_error(guild, "HCVerify failed: Supabase client unavailable.", interaction=interaction); return

    if not interaction.response.is_done(): await interaction.response.defer(thinking=True, ephemeral=False)
    else: print(f"Warning: Interaction {interaction.id} already responded to before hcverify deferral.")

    role_unverified = guild.get_role(REMOVE_ROLE_ID)
    role_verified = guild.get_role(ADD_ROLE_ID_VERIFY)
    role_hc = guild.get_role(ADD_ROLE_ID_HC)
    bot_member = guild.me
    send_func = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message

    missing_roles = []
    if ADD_ROLE_ID_VERIFY and not role_verified: missing_roles.append(f"Verified (ID: {ADD_ROLE_ID_VERIFY})")
    if ADD_ROLE_ID_HC and not role_hc: missing_roles.append(f"HC (ID: {ADD_ROLE_ID_HC})")
    if REMOVE_ROLE_ID and not role_unverified: missing_roles.append(f"Unverified (ID: {REMOVE_ROLE_ID})")
    if missing_roles:
        await send_func(f"❌ Setup Error: Missing critical roles: {', '.join(missing_roles)}.", ephemeral=True)
        await log_error(guild, f"HCVerify failed: Missing roles - {', '.join(missing_roles)}", interaction=interaction); return

    log_summary = []; result_summary = []
    errors_occurred = False; db_success = False
    role_changes_attempted = False; role_changes_succeeded = False
    reason = f"HC Verified by {interaction.user}"
    can_manage_user = bot_member.top_role.position > user.top_role.position

    # Role Management
    roles_to_add_final = []; roles_to_remove_final = []
    original_hc_status = role_hc and role_hc in user.roles
    desired_adds = []; desired_removes = []
    if role_verified and role_verified not in user.roles: desired_adds.append(role_verified)
    if role_hc and not original_hc_status: desired_adds.append(role_hc)
    if role_unverified and role_unverified in user.roles: desired_removes.append(role_unverified)

    for role in desired_adds:
        if bot_member.top_role.position > role.position: roles_to_add_final.append(role)
        else: errors_occurred=True; reason_skip=f"Bot hierarchy low for role '{role.name}'"; result_summary.append(f"⚠️ Skipped adding `{role.name}` (Hierarchy)."); log_summary.append(f"Role add skip: {reason_skip}"); await log_info(guild, f"HCVerify: {reason_skip}")
    for role in desired_removes:
        if bot_member.top_role.position > role.position: roles_to_remove_final.append(role)
        else: errors_occurred=True; reason_skip=f"Bot hierarchy low for role '{role.name}'"; result_summary.append(f"⚠️ Skipped removing `{role.name}` (Hierarchy)."); log_summary.append(f"Role remove skip: {reason_skip}"); await log_info(guild, f"HCVerify: {reason_skip}")

    if roles_to_add_final or roles_to_remove_final:
        role_changes_attempted = True
        try:
            if roles_to_add_final: await user.add_roles(*roles_to_add_final, reason=reason)
            if roles_to_remove_final: await user.remove_roles(*roles_to_remove_final, reason=reason)
            added_names = ', '.join(f"`{r.name}`" for r in roles_to_add_final); removed_names = ', '.join(f"`{r.name}`" for r in roles_to_remove_final)
            if added_names: result_summary.append(f"➕ Roles Added: {added_names}")
            if removed_names: result_summary.append(f"➖ Roles Removed: {removed_names}")
            log_summary.append("Role update successful for applicable roles"); role_changes_succeeded = True
        except discord.Forbidden: errors_occurred=True; result_summary.append("⚠️ Role Error: Permissions error."); log_summary.append("Role update failed: Forbidden"); await log_error(guild, "HCVerify role update failed (Forbidden)", interaction=interaction)
        except discord.HTTPException as e: errors_occurred=True; result_summary.append("⚠️ Role Error: Discord API Error."); log_summary.append(f"Role update failed: HTTP {e.status}"); await log_error(guild, "HCVerify role update failed (HTTPException)", error=e, interaction=interaction)
        except Exception as e: errors_occurred=True; result_summary.append("⚠️ Role Error: Unknown Error."); log_summary.append(f"Role update fail: {type(e).__name__}"); await log_error(guild, "HCVerify unexpected role error", error=e, interaction=interaction)
    elif not desired_adds and not desired_removes: result_summary.append("ℹ️ Roles already correct."); log_summary.append("No role changes needed")

    # Database Update
    try:
        ign_to_store = ingame_name.strip()
        if not ign_to_store: raise ValueError("In-game name cannot be empty.")
        await run_supabase_sync( lambda: supabase.table("hc_members").upsert({"discord_id": str(user.id), "discord_name": f"{user.name}#{user.discriminator}" if user.discriminator != '0' else user.name, "ingame_name": ign_to_store }, on_conflict="discord_id").execute())
        result_summary.append(f"💾 IGN Stored: `{discord.utils.escape_markdown(ign_to_store)}`"); log_summary.append("Supabase upsert OK"); db_success = True
    except ValueError as e: errors_occurred=True; result_summary.append(f"⚠️ DB Error: {e}"); log_summary.append(f"DB fail: {e}"); await log_error(guild, "HCVerify DB upsert fail (ValueError)", error=e, interaction=interaction)
    except APIError as e: errors_occurred=True; err_detail=f"API Error: {e.message}" if hasattr(e,'message') else f"Code: {e.code or 'N/A'}"; result_summary.append(f"⚠️ DB Error ({err_detail})"); log_summary.append(f"DB fail: {e}"); await log_error(guild, "HCVerify DB upsert fail (APIError)", error=e, interaction=interaction)
    except Exception as e: errors_occurred=True; result_summary.append("⚠️ DB Error: Unknown."); log_summary.append(f"DB fail: {type(e).__name__}"); await log_error(guild, "HCVerify DB upsert fail (Exception)", error=e, interaction=interaction)

    # Nickname Management
    nick_success = False; nickname_to_set = ingame_name.strip()[:32]; truncated = len(ingame_name.strip()) > 32
    if not nickname_to_set: errors_occurred=True; result_summary.append("⚠️ Nickname Error: IGN empty."); log_summary.append("Nick skipped (empty)")
    elif user.nick == nickname_to_set: result_summary.append(f"🏷️ Nickname already set."); log_summary.append("Nick OK"); nick_success = True
    elif not can_manage_user: errors_occurred=True; result_summary.append(f"⚠️ Nickname Skipped (Hierarchy)."); log_summary.append("Nick skipped (Hierarchy)"); await log_info(guild, f"HCVerify: Nickname change skipped for {user.mention} (Hierarchy).")
    else:
        try:
            await user.edit(nick=nickname_to_set, reason=reason)
            nick_msg = f"🏷️ Nickname Set: `{discord.utils.escape_markdown(nickname_to_set)}`"+ (" (truncated)" if truncated else "")
            result_summary.append(nick_msg); log_summary.append(f"Nick set{' (trunc)' if truncated else ''}"); nick_success = True
        except discord.Forbidden: errors_occurred=True; result_summary.append("⚠️ Nickname Error: Permissions."); log_summary.append("Nick fail: Forbidden"); await log_error(guild, "HCVerify nick fail (Forbidden)", interaction=interaction)
        except discord.HTTPException as e: errors_occurred=True; result_summary.append("⚠️ Nickname Error: API Error."); log_summary.append(f"Nick fail: HTTP {e.status}"); await log_error(guild, "HCVerify nick fail (HTTPException)", error=e, interaction=interaction)
        except Exception as e: errors_occurred=True; result_summary.append("⚠️ Nickname Error: Unknown."); log_summary.append(f"Nick fail: {type(e).__name__}"); await log_error(guild, "HCVerify unexpected nick error", error=e, interaction=interaction)

    # Final Response & Logging
    final_color = discord.Color.orange() if errors_occurred else discord.Color.green()
    final_title = f"{'✅' if not errors_occurred else '⚠️'} HC Verify Processed: {user.display_name}"+(" (with issues/skips)" if errors_occurred else "")
    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    try: await interaction.followup.send(embed=final_embed)
    except (discord.NotFound, discord.HTTPException) as e: await log_error(guild, "HCVerify failed final followup", error=e, interaction=interaction)
    await log_info(guild, f"`{interaction.user}` HCVerify for {user.mention}. Summary: {'; '.join(log_summary)}.")
    if role_changes_succeeded or db_success:
         print(f"HCVerify: Triggering list update for {user.name} (Role success: {role_changes_succeeded}, DB success: {db_success}).")
         await asyncio.sleep(1.0); await update_hc_member_list(guild)


# --- REFINED Un-HC-Verify Command ---
@tree.command(name="unhcverify", description="Remove HC role and reset nickname for a user.")
@app_commands.describe(user="The user to remove from HC.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def unhcverify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    if not guild: await interaction.response.send_message("This command must be used in a server.", ephemeral=True); return

    if not interaction.response.is_done(): await interaction.response.defer(thinking=True, ephemeral=False)
    else: print(f"Warning: Interaction {interaction.id} already responded to before unhcverify deferral.")

    role_hc = guild.get_role(ADD_ROLE_ID_HC)
    bot_member = guild.me
    send_func = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message

    if not role_hc:
        await send_func(f"❌ Setup Error: HC Role (ID: {ADD_ROLE_ID_HC}) not found.", ephemeral=True)
        await log_error(guild, f"UnHCVerify failed: HC role not found.", interaction=interaction); return

    log_summary = []; result_summary = []
    errors_occurred = False; role_was_removed = False
    reason = f"Un-HC-Verified by {interaction.user}"
    can_manage_user = bot_member.top_role.position > user.top_role.position
    can_manage_hc_role = bot_member.top_role.position > role_hc.position
    nick_reset_needed = user.nick is not None

    # Role Removal
    if role_hc not in user.roles:
        try: await send_func(f"ℹ️ {user.mention} doesn't have the `{role_hc.name}` role.", ephemeral=True)
        except Exception: await send_func(f"ℹ️ {user.mention} doesn't have the `{role_hc.name}` role.")
        return
    elif not can_manage_hc_role:
        errors_occurred=True; reason_skip=f"Bot hierarchy low for role '{role_hc.name}'"; result_summary.append(f"⚠️ Skipped removing `{role_hc.name}` (Hierarchy)."); log_summary.append(f"Role remove skip: {reason_skip}"); await log_info(guild, f"UnHCVerify: {reason_skip}")
    else:
        try:
            await user.remove_roles(role_hc, reason=reason)
            result_summary.append(f"➖ Role Removed: `{role_hc.name}`"); log_summary.append("HC role removed OK"); role_was_removed = True
        except discord.Forbidden: errors_occurred=True; result_summary.append("⚠️ Role Error: Permissions."); log_summary.append("Role remove fail: Forbidden"); await log_error(guild, "UnHCVerify role remove fail (Forbidden)", interaction=interaction)
        except discord.HTTPException as e: errors_occurred=True; result_summary.append("⚠️ Role Error: API Error."); log_summary.append(f"Role remove fail: HTTP {e.status}"); await log_error(guild, "UnHCVerify role remove fail (HTTPException)", error=e, interaction=interaction)
        except Exception as e: errors_occurred=True; result_summary.append("⚠️ Role Error: Unknown."); log_summary.append(f"Role remove fail: {type(e).__name__}"); await log_error(guild, "UnHCVerify unexpected role error", error=e, interaction=interaction)

    # Nickname Reset
    if nick_reset_needed:
        if not can_manage_user: errors_occurred=True; result_summary.append(f"⚠️ Nickname Skipped (Hierarchy)."); log_summary.append("Nick reset skipped (Hierarchy)"); await log_info(guild, f"UnHCVerify: Nickname reset skipped for {user.mention} (Hierarchy).")
        else:
             try:
                 await user.edit(nick=None, reason=reason)
                 result_summary.append("🏷️ Nickname Reset"); log_summary.append("Nick reset OK")
             except discord.Forbidden: errors_occurred=True; result_summary.append("⚠️ Nickname Error: Permissions."); log_summary.append("Nick reset fail: Forbidden"); await log_error(guild, "UnHCVerify nick reset fail (Forbidden)", interaction=interaction)
             except discord.HTTPException as e: errors_occurred=True; result_summary.append("⚠️ Nickname Error: API Error."); log_summary.append(f"Nick reset fail: HTTP {e.status}"); await log_error(guild, "UnHCVerify nick reset fail (HTTPException)", error=e, interaction=interaction)
             except Exception as e: errors_occurred=True; result_summary.append("⚠️ Nickname Error: Unknown."); log_summary.append(f"Nick reset fail: {type(e).__name__}"); await log_error(guild, "UnHCVerify unexpected nick reset error", error=e, interaction=interaction)
    else: result_summary.append("🏷️ No nickname to reset."); log_summary.append("No nick reset needed")

    # Final Response & Logging
    final_color = discord.Color.orange() if errors_occurred else discord.Color.green()
    final_title = f"{'✅' if not errors_occurred else '⚠️'} Un-HC Verify Processed: {user.display_name}"+(" (with issues/skips)" if errors_occurred else "")
    final_embed = create_embed(title=final_title, description="\n".join(result_summary), color=final_color)
    try: await interaction.followup.send(embed=final_embed)
    except (discord.NotFound, discord.HTTPException) as e: await log_error(guild, "UnHCVerify failed final followup", error=e, interaction=interaction)
    await log_info(guild, f"`{interaction.user}` UnHCVerify for {user.mention}. Summary: {'; '.join(log_summary)}.")
    if role_was_removed:
        print(f"UnHCVerify: Triggering list update for {user.name}.")
        await asyncio.sleep(1.0); await update_hc_member_list(guild)


# --- HC Members Interactive List ---
@tree.command(name="hcmembers", description="Show interactive list of [HC1] members (username#tag ➔ IGN).")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild: await interaction.response.send_message("This command can only be used in a server.", ephemeral=True); return
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        allowed_mentions = [f"<#{ch_id}>" for ch_id in ALLOWED_CHANNEL_IDS] # Use channel mentions
        await interaction.response.send_message(f"❌ This command only works in: {', '.join(allowed_mentions) or 'None configured'}", ephemeral=True); return
    await interaction.response.defer(thinking=True, ephemeral=False)
    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Database unavailable.", discord.Color.red())); await log_error(guild, "/hcmembers failed: Supabase unavailable.", interaction=interaction); return
    try:
        data, total = await fetch_hc_member_data(guild)
        if not data:
            hc_role = guild.get_role(ADD_ROLE_ID_HC); role_name = f"`{hc_role.name}`" if hc_role else f"HC role (ID: {ADD_ROLE_ID_HC})"
            description = f"No members found with {role_name}." + ("\n(DB fetch issue?)" if total > 0 else "")
            embed = create_embed(title=HC_LIST_EMBED_TITLE, description=description, color=discord.Color.orange()); await interaction.followup.send(embed=embed); return
        view = HCPagesView(data, total); initial_embed = view.create_page_embed()
        message = await interaction.followup.send(embed=initial_embed, view=view); view.message = message
        await log_info(guild, f"/hcmembers used by `{interaction.user}` in {interaction.channel.mention if interaction.channel else 'N/A'}.")
    except ConnectionError as e: await log_error(guild, "/hcmembers DB connection error", error=e, interaction=interaction); await interaction.followup.send(embed=create_embed("❌ DB Connection Error.", discord.Color.red()))
    except APIError as e: await log_error(guild, "/hcmembers Supabase API error", error=e, interaction=interaction); await interaction.followup.send(embed=create_embed("❌ DB API Error.", discord.Color.red()))
    except Exception as e: await log_error(guild, "Unhandled /hcmembers error", error=e, interaction=interaction); await interaction.followup.send(embed=create_embed("❌ Unexpected error.", discord.Color.red()))


# --- Refresh Static List Command ---
@tree.command(name="refresh", description="Manually refresh static [HC1] list (username#tag ➔ IGN).")
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild: await interaction.response.send_message("Must be used in a server.", ephemeral=True); return
    await interaction.response.defer(thinking=True, ephemeral=True)
    if not supabase: await interaction.followup.send("❌ DB unavailable.", ephemeral=True); await log_error(guild, "/refresh failed: Supabase unavailable.", interaction=interaction); return
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(list_channel, discord.TextChannel):
        await interaction.followup.send(f"❌ Config Error: Static list channel invalid (ID: {HC_MEMBER_LIST_CHANNEL_ID}).", ephemeral=True)
        await log_error(guild, f"/refresh failed: Static list channel invalid.", interaction=interaction); return
    try:
        await log_info(guild, f"Manual refresh initiated by `{interaction.user}`.")
        await update_hc_member_list(guild)
        await interaction.followup.send(f"✅ Refresh initiated for {list_channel.mention}. Please wait.", ephemeral=True)
    except Exception as e:
        await log_error(guild, "Error initiating /refresh", error=e, interaction=interaction)
        await interaction.followup.send("❌ Unexpected error starting refresh.", ephemeral=True)


# --- Bulk Update Command ---
@tree.command(name="bulkupdate", description="Open form to bulk update IGNs (username#tag ➔ IGN).")
@app_commands.checks.has_permissions(manage_roles=True)
async def bulkupdate(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild: await interaction.response.send_message("Must be used in a server.", ephemeral=True); return
    try:
        await interaction.response.send_modal(BulkUpdateModal())
        await log_info(interaction.guild, f"`{interaction.user}` opened bulk update modal.")
    except Exception as e:
        await log_error(interaction.guild, "Failed to open BulkUpdateModal", error=e, interaction=interaction)
        if not interaction.response.is_done():
            try: await interaction.response.send_message("❌ Error opening bulk update form.", ephemeral=True)
            except Exception: pass


# --- Sync Nicknames Command ---
@tree.command(name="syncnicknames", description="Sync all HC members' nicknames with their stored IGNs.")
@app_commands.checks.has_permissions(manage_nicknames=True) # Keep this check, useful admin command
@app_commands.checks.bot_has_permissions(manage_nicknames=True)
async def syncnicknames(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild: await interaction.response.send_message("Must be used in a server.", ephemeral=True); return
    await interaction.response.defer(thinking=True, ephemeral=True)
    if not supabase: await interaction.edit_original_response(content="❌ DB unavailable."); await log_error(guild, "/syncnicknames failed: Supabase unavailable.", interaction=interaction); return
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role: await interaction.edit_original_response(content=f"❌ Config Error: HC Role (ID: {ADD_ROLE_ID_HC}) not found."); await log_error(guild, f"/syncnicknames failed: HC role not found.", interaction=interaction); return

    start_time = discord.utils.utcnow(); await log_info(guild, f"Nickname sync initiated by `{interaction.user}`.")
    await interaction.edit_original_response(content="<a:loading:12345> Fetching data...") # Use actual loading emoji ID if available

    ign_data = {}; fetch_error = None
    try:
        resp = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").execute())
        if resp and hasattr(resp, 'data') and resp.data: ign_data = {item['discord_id']: item['ingame_name'] for item in resp.data if item.get('discord_id') and item.get('ingame_name')}
        print(f"SyncNick ({guild.name}): Fetched {len(ign_data)} IGNs.")
    except Exception as e: fetch_error = e; await log_error(guild, "SyncNick: DB fetch failed", error=e, interaction=interaction); await interaction.edit_original_response(content="❌ DB fetch failed."); return

    try:
        if not guild.chunked: await guild.chunk(cache=True)
        hc_members = [m for m in guild.members if hc_role in m.roles and not m.bot]; total_hc_members = len(hc_members)
        print(f"SyncNick ({guild.name}): Found {total_hc_members} HC members.")
    except Exception as e: await log_error(guild, "SyncNick: Member fetch/chunk failed", error=e, interaction=interaction); await interaction.edit_original_response(content="❌ Member fetch failed."); return
    if total_hc_members == 0: await interaction.edit_original_response(content=f"ℹ️ No members with `{hc_role.name}` role found."); return

    await interaction.edit_original_response(content=f"<a:loading:12345> Syncing {total_hc_members} members...")
    counts = {'proc': 0, 'upd': 0, 'skip_match': 0, 'skip_no_ign': 0, 'skip_empty': 0, 'fail_hier': 0, 'fail_forbid': 0, 'fail_other': 0}
    bot_pos = guild.me.top_role.position; last_prog_time = asyncio.get_event_loop().time()

    for idx, member in enumerate(hc_members):
        counts['proc'] += 1; member_id_str = str(member.id)
        if bot_pos <= member.top_role.position: counts['fail_hier'] += 1; continue
        stored_ign = ign_data.get(member_id_str)
        if not stored_ign: counts['skip_no_ign'] += 1; continue
        target_nick = stored_ign.strip()
        if not target_nick: counts['skip_empty'] += 1; continue
        target_nick = target_nick[:32]
        if member.nick == target_nick: counts['skip_match'] += 1; continue
        try:
            await member.edit(nick=target_nick, reason=f"Sync by {interaction.user.id}")
            counts['upd'] += 1; await asyncio.sleep(0.2)
        except discord.Forbidden: counts['fail_forbid'] += 1; #if counts['fail_forbid'] <= 3: await log_error(guild, f"SyncNick: Forbidden for {member.mention}", embed=None)
        except discord.HTTPException: counts['fail_other'] += 1; #if counts['fail_other'] <= 3: await log_error(guild, f"SyncNick: HTTP error for {member.mention}", embed=None)
        except Exception as e: counts['fail_other'] += 1; #if counts['fail_other'] <= 3: await log_error(guild, f"SyncNick: Error for {member.mention}", error=e, embed=None)

        now = asyncio.get_event_loop().time()
        if now - last_prog_time > 5.0 or counts['proc'] % 50 == 0:
            try: await interaction.edit_original_response(content=f"<a:loading:12345> Syncing... ({counts['proc']}/{total_hc_members})"); last_prog_time = now
            except (discord.NotFound, discord.HTTPException): print(f"SyncNick ({guild.name}): Progress update failed."); break

    end_time = discord.utils.utcnow(); duration = (end_time - start_time).total_seconds()
    summary_embed = discord.Embed(title="✅ Nickname Sync Complete!", color=NERDY_YELLOW, timestamp=end_time)
    summary_lines = [f"⏱️ **Duration:** {duration:.2f}s", f"👥 **Total HC:** {total_hc_members}", f"🔄 **Processed:** {counts['proc']}", f"✅ **Updated:** {counts['upd']}",
                     f"ℹ️ **Skipped (Match):** {counts['skip_match']}", f"❓ **Skipped (No/Empty IGN):** {counts['skip_no_ign'] + counts['skip_empty']}",
                     f"❌ **Failed (Hierarchy):** {counts['fail_hier']}", f"❌ **Failed (Perms/Other):** {counts['fail_forbid'] + counts['fail_other']}"]
    summary_embed.description = "\n".join(summary_lines)
    try: await interaction.edit_original_response(content=None, embed=summary_embed)
    except (discord.NotFound, discord.HTTPException):
    print(f"SyncNick ({guild.name}): Final summary failed.")
    try: # Moved to new line and indented
        await interaction.followup.send(embed=summary_embed, ephemeral=True)
    except Exception as e_inner: # Added separate handling for the inner try's exception
        print(f"SyncNick ({guild.name}): Final followup failed: {e_inner}")
    log_embed = discord.Embed(title="Nickname Sync Finished", description="\n".join(summary_lines), color=NERDY_YELLOW); log_embed.set_footer(text=f"By {interaction.user}")
    await log_info(guild, "", embed=log_embed)


# --- Wither Command ---
@tree.command(name="wither", description="Temporarily remove roles from a user.")
@app_commands.describe(user="User to wither.", time="Duration in minutes (0.1 to 10, default 2).")
async def wither(interaction: discord.Interaction, user: discord.Member, time: app_commands.Range[float, 0.1, 10.0] = 2.0):
    guild = interaction.guild; invoker = interaction.user
    if not guild: await interaction.response.send_message("Cannot use here.", ephemeral=True); return
    bot_member = guild.me

    async def fail_check(log_reason: str, user_message: str):
        send_func = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        try: await send_func(embed=create_embed(user_message, discord.Color.red()), ephemeral=True)
        except Exception as e: print(f"Wither Check Fail Send Error: {e}")
        await log_error(guild, f"Wither check fail ({invoker.name} -> {user.name}): {log_reason}", interaction=interaction)

    if invoker.id not in ALLOWED_WITHER_IDS:
        if not interaction.response.is_done(): await interaction.response.defer(ephemeral=True)
        await fail_check("Invoker permission denied.", "❌ No permission."); return
    if not interaction.response.is_done(): await interaction.response.defer(thinking=True, ephemeral=False) # Defer publicly
    if user.id == invoker.id: await fail_check("Target self.", "🤨 Cannot wither yourself."); return
    if user.id == SELF_PROTECTED_ID and invoker.id != SELF_PROTECTED_ID: await fail_check("Target protected.", "😨 Cannot wither owner."); return
    if user.id == BOT_ID: await fail_check("Target bot.", "😭 Cannot wither me."); return
    if user.bot: await fail_check("Target other bot.", "🤖 Cannot wither bots."); return
    if user.id == guild.owner_id and invoker.id != guild.owner_id: await fail_check("Target owner.", "👑 Cannot wither owner."); return
    if bot_member.top_role.position <= user.top_role.position: await fail_check("Bot hierarchy low.", "❌ My role isn't high enough."); return
    if invoker.id != guild.owner_id and invoker.top_role.position <= user.top_role.position: await fail_check("Invoker hierarchy low.", "❌ Your role isn't high enough."); return

    original_roles = [r for r in user.roles if r != guild.default_role]
    if not original_roles: await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} has no roles.", discord.Color.orange()), ephemeral=False); return

    try:
        wither_seconds = min(max(1, int(time * 60)), int(MAX_WITHER_SECONDS or 600)); actual_minutes = wither_seconds / 60.0
        reason_wither = f"Wither by {invoker.name} for {actual_minutes:.1f}m."
        if not bot_member.guild_permissions.manage_roles: await fail_check("Bot lost perms before remove.", "❌ Lost perms."); return

        roles_to_remove_actually = [r for r in original_roles if bot_member.top_role.position > r.position]
        skipped_roles_remove = [r for r in original_roles if r not in roles_to_remove_actually]
        await user.edit(roles=[], reason=reason_wither) # Removes manageable roles

        roles_removed_str = (', '.join(f"`{r.name}`" for r in roles_to_remove_actually) or 'None Manageable')[:900]
        wither_desc = f"{user.mention} withered by {invoker.mention} for **{actual_minutes:.1f}m**!\n**Removed:** {roles_removed_str}"
        if skipped_roles_remove: skipped_str = (', '.join(f"`{r.name}`" for r in skipped_roles_remove))[:100]; wither_desc += f"\n*(Skipped {len(skipped_roles_remove)} due to hierarchy: {skipped_str}...)*"
        await interaction.followup.send(embed=create_embed(title="🌪️ Wither Cast! 🌪️", description=wither_desc, color=discord.Color.dark_purple()), ephemeral=False)
        log_msg = f"`{user.name}` withered by `{invoker.name}`. Roles removed: {', '.join(r.name for r in roles_to_remove_actually) or 'N/A'}."
        if skipped_roles_remove: log_msg += f" Skipped: {', '.join(r.name for r in skipped_roles_remove)}."
        await log_info(guild, log_msg)

        await asyncio.sleep(wither_seconds)

        try:
            member_after = await guild.fetch_member(user.id)
            bot_member_after = await guild.fetch_member(BOT_ID) if BOT_ID else await guild.fetch_me()
            reason_restore = f"Wither end after {actual_minutes:.1f}m."
            if bot_member_after.top_role.position <= member_after.top_role.position: await log_error(guild, f"Wither restore fail: Bot hierarchy low for {member_after.mention}."); await interaction.channel.send(f"⚠️ Failed restore for {member_after.mention} - hierarchy low.") ; return
            if not bot_member_after.guild_permissions.manage_roles: await log_error(guild, f"Wither restore fail: Bot lost perms for {member_after.mention}."); await interaction.channel.send(f"⚠️ Failed restore for {member_after.mention} - perms lost."); return

            valid_restore = []; skipped_del = []; skipped_hier = []
            for r in original_roles:
                fetched = guild.get_role(r.id)
                if not fetched: skipped_del.append(r.name)
                elif bot_member_after.top_role.position > fetched.position: valid_restore.append(fetched)
                else: skipped_hier.append(fetched.name)
            if skipped_del: await log_info(guild, f"Wither restore notice: Roles deleted for {member_after.name}: {', '.join(skipped_del)}.")
            if skipped_hier: await log_info(guild, f"Wither restore notice: Roles hierarchy issue for {member_after.name}: {', '.join(skipped_hier)}.")
            if not valid_restore: await log_info(guild, f"Wither restore: No valid roles left for {member_after.name}."); await interaction.channel.send(f"ℹ️ Wither ended for {member_after.mention}, no roles restored."); return

            await member_after.edit(roles=valid_restore, reason=reason_restore)
            restore_msg = f"✨ {member_after.mention}'s roles restored!" + ("\n*(Some skipped)*" if skipped_del or skipped_hier else "")
            if interaction.channel:
                try: await interaction.followup.send(embed=create_embed(restore_msg, color=NERDY_YELLOW), ephemeral=False)
                except (discord.NotFound, discord.HTTPException) as e: await log_error(guild, "Wither failed restore followup", error=e)
            else: await log_info(guild, f"Wither restore OK for {member_after.mention}, channel gone.")
            await log_info(guild, f"Restored roles for `{member_after.name}`. Roles: {', '.join(r.name for r in valid_restore)}")
        # Corrected example for discord.NotFound
except discord.NotFound:
    await log_info(guild, f"Wither restore skip: `{user.name}` left.")
    if interaction.channel:
        try: # Moved to new line and indented under the 'if'
            await interaction.channel.send(f"ℹ️ Wither ended, {user.display_name} left.")
        except Exception: # Indented under the 'try'
            pass # Keep original behavior

# Corrected example for discord.Forbidden
except discord.Forbidden:
    await log_error(guild, f"Wither restore fail: Forbidden for {user.name}.")
    if interaction.channel:
        try: # Moved to new line and indented
            await interaction.channel.send(f"⚠️ Failed restore {user.display_name} - Perms error.")
        except Exception: # Indented under the 'try'
            pass # Keep original behavior

# Corrected example for discord.HTTPException
except discord.HTTPException as e:
    await log_error(guild, f"Wither restore fail: API error for {user.name}.", error=e)
    if interaction.channel:
        try: # Moved to new line and indented
            await interaction.channel.send(f"⚠️ Failed restore {user.display_name} - API error.")
        except Exception: # Indented under the 'try'
            pass # Keep original behavior

# Corrected example for generic Exception
except Exception as e:
    await log_error(guild, f"Wither restore fail: Unexpected for {user.name}.", error=e)
    if interaction.channel:
        try: # Moved to new line and indented
            await interaction.channel.send(f"⚠️ Failed restore {user.display_name} - Error.")
        except Exception: # Indented under the 'try'
            pass # Keep original behavior
    # Corrected example for discord.Forbidden
except discord.Forbidden:
    await log_error(guild, f"Wither remove fail: Forbidden for {user.name}.")
    try: # Moved to new line and indented
        await interaction.edit_original_response(content=f"❌ Failed remove roles {user.display_name} - Perms error.", embed=None, view=None)
    except Exception: # Indented under the 'try'
        pass # Keep original behavior

# Corrected example for discord.HTTPException
except discord.HTTPException as e:
    await log_error(guild, f"Wither remove fail: API error for {user.name}.", error=e)
    try: # Moved to new line and indented
        await interaction.edit_original_response(content=f"❌ Failed remove roles {user.display_name} - API error.", embed=None, view=None)
    except Exception: # Indented under the 'try'
        pass # Keep original behavior

# Corrected example for generic Exception
except Exception as e:
    await log_error(guild, f"Wither remove fail: Unexpected for {user.name}.", error=e)
    try: # Moved to new line and indented
        await interaction.edit_original_response(content=f"❌ Failed remove roles {user.display_name} - Error.", embed=None, view=None)
    except Exception: # Indented under the 'try'
        pass # Keep original behavior


# --- MODIFIED Nerd Help Command ---
@tree.command(name="nerdhelp", description="Show the list of available bot commands.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild: await interaction.response.send_message("Must be used in a server.", ephemeral=True); return

    embed = discord.Embed(title="🤓 Pingslave Bot Commands", description="Click on a command to use it!", color=NERDY_YELLOW)

    def get_cmd_mention(name: str) -> str:
        cmd_id = command_ids.get(name)
        if cmd_id: return f"</{name}:{cmd_id}>"
        else: print(f"Warn: No ID for cmd '/{name}' in nerdhelp."); return f"`/{name}`" # Fallback

    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID); list_channel_mention = list_channel.mention if list_channel else f"ID `{HC_MEMBER_LIST_CHANNEL_ID}`"
    allowed_ch_mentions = [f"<#{ch_id}>" for ch_id in ALLOWED_CHANNEL_IDS]; allowed_chs_str = ", ".join(allowed_ch_mentions) or "`None Configured`"

    embed.add_field(name="\u200B\n🔑 **Verification & HC Management**", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('verify')} `<user>`", value="> Grants `Verified`, removes `Unverified`.\n> *Requires:* `Manage Roles`", inline=True)
    embed.add_field(name=f"{get_cmd_mention('unverify')} `<user>`", value="> Removes `Verified`, adds `Unverified`.\n> *Requires:* `Manage Roles`", inline=True)
    embed.add_field(name="\u200B", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('hcverify')} `<user> <IGN>`", value="> Adds `HC`/`Verified`, stores IGN, sets nick, updates list.\n> *Requires:* `Manage Roles`", inline=False)
    embed.add_field(name=f"{get_cmd_mention('unhcverify')} `<user>`", value="> Removes `HC`, resets nick, updates list.\n> *Requires:* `Manage Roles`", inline=False)

    embed.add_field(name="\u200B\n📊 **[HC1] Member List**", value="*Lists show `Username#Tag ➔ IGN`*", inline=False)
    embed.add_field(name=f"{get_cmd_mention('hcmembers')}", value=f"> Interactive HC list.\n> *Requires:* `Everyone` (in {allowed_chs_str})", inline=True)
    embed.add_field(name=f"{get_cmd_mention('refresh')}", value=f"> Updates static list in {list_channel_mention}.\n> *Requires:* `Manage Roles`", inline=True)

    embed.add_field(name="\u200B\n\n⚙️ **Utilities**", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('bulkupdate')}", value="> Bulk update IGNs form.\n> *Requires:* `Manage Roles`", inline=True)
    embed.add_field(name=f"{get_cmd_mention('syncnicknames')}", value="> Syncs HC nicks to IGNs.\n> *Requires:* `Manage Nicknames`", inline=True)
    embed.add_field(name="\u200B", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('wither')} `<user> [time]`", value=f"> Temporarily removes roles (0.1-{MAX_WITHER_SECONDS / 60:.0f} min).\n> *Requires:* `Special Permission`", inline=True)
    embed.add_field(name=f"{get_cmd_mention('nerdhelp')}", value="> Shows this help message.\n> *Requires:* `Everyone`", inline=True)

    embed.set_footer(text="Bot by TheNerd | sweet_honey")
    if bot.user and bot.user.display_avatar: embed.set_thumbnail(url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=False)


# --- Bot Startup ---
if __name__ == "__main__":
    print("--- Initializing Pingslave Bot ---")
    if not TOKEN:
        print("CRITICAL: DISCORD_BOT_TOKEN environment variable not found.")
    elif not supabase:
        print("CRITICAL: Supabase client initialization failed. Check URL/Key and connection.")
    else:
        print("Discord Token and Supabase Client OK.")
        print("Starting Keep Alive Flask server...")
        keep_alive()

        try:
            print("Attempting to start Discord Bot...")
            bot.run(TOKEN, log_handler=None)
        except discord.LoginFailure:
            print("CRITICAL: Discord Login Failed. Check token.")
        except discord.PrivilegedIntentsRequired:
            print("CRITICAL: Privileged Intents (Server Members) required but not enabled.")
        except Exception as e:
            print(f"CRITICAL: Unexpected error during bot execution: {e}")
            print(traceback.format_exc())

    print("--- Bot process has ended ---")
