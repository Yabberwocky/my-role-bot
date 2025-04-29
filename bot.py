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
from typing import Optional, Tuple, List # Added for type hinting clarity

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
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase client created successfully.")
    except Exception as e:
        print(f"CRITICAL: Failed to create Supabase client: {e}")
        supabase = None
else:
    print("CRITICAL: SUPABASE_URL or SUPABASE_KEY environment variables missing.")
    supabase = None

# --- Discord Setup ---
intents = discord.Intents.default()
intents.members = True # Required for accessing member list, roles, etc.
intents.message_content = False # Not needed for slash commands
bot = commands.Bot(command_prefix="!", intents=intents) # Prefix not used by slash commands
tree = bot.tree

# --- Flask App (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Pingslave bot is alive!"

def run_flask():
    try:
        port = int(os.environ.get('PORT', 8080))
        print(f"Attempting to start Flask server on host 0.0.0.0 port {port}")
        # Note: Use 'waitress' or 'gunicorn' in production instead of app.run for better performance/stability
        app.run(host='0.0.0.0', port=port)
        print("Flask server finished.")
    except OSError as e:
         print(f"Flask server failed (OSError): {e}. Port {port} might be in use.")
    except Exception as e:
        print(f"Flask server failed (General Exception): {e}")
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
        print("Attempted Supabase operation, but client not initialized.")
        raise ConnectionError("Supabase client is not available.")
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func)
    except APIError as api_err:
        print(f"Supabase API Error: {api_err}")
        raise
    except Exception as e:
        print(f"Error running Supabase func in executor: {e}")
        raise

# --- Logging ---
async def log_to_channel(channel_id: int, guild: Optional[discord.Guild], message: Optional[str] = None, embed: Optional[discord.Embed] = None):
    """Sends a log message/embed to a channel, checking permissions."""
    if not guild: print(f"Log Error: No Guild for channel {channel_id}. Content: {message or 'Embed'}"); return
    log_channel = guild.get_channel(channel_id)
    if not isinstance(log_channel, discord.TextChannel): print(f"Log Error: Channel {channel_id} invalid in {guild.name}."); return

    bot_member = guild.me
    if not bot_member: print(f"Log Error: Cannot find bot in {guild.name}."); return

    perms = log_channel.permissions_for(bot_member)
    can_send, can_embed = perms.send_messages, perms.embed_links
    if not can_send or (embed and not can_embed):
        missing = [p for p, has in [("Send Messages", can_send), ("Embed Links", can_embed and embed)] if not has]
        print(f"Log Error: Missing perms ({', '.join(missing)}) in {log_channel.mention} ({guild.name})."); return

    try:
        if embed: await log_channel.send(embed=embed)
        elif message: await log_channel.send((message[:1997] + "...") if len(message) > 2000 else message)
    except discord.Forbidden: print(f"Log Error: Forbidden in {log_channel.mention} ({guild.name}).")
    except discord.HTTPException as http_err: print(f"Log Error: HTTP {http_err.status} in {log_channel.mention}: {http_err.text}")
    except Exception as e: print(f"Log Error: Send fail in {log_channel.mention}: {e}")

async def log_info(guild: Optional[discord.Guild], message: str, embed: Optional[discord.Embed] = None):
    """Logs an info message with timestamp."""
    if not embed: embed = discord.Embed(description=message, color=NERDY_YELLOW); embed.timestamp = discord.utils.utcnow()
    await log_to_channel(INFO_LOG_CHANNEL_ID, guild, embed=embed)

async def log_error(guild: Optional[discord.Guild], message: str, error: Optional[Exception] = None, interaction: Optional[discord.Interaction] = None, embed: Optional[discord.Embed] = None):
    """Logs an error with context and traceback."""
    if not embed:
        embed = discord.Embed(title="⚠️ Bot Error / Warning", description=message, color=discord.Color.red()); embed.timestamp = discord.utils.utcnow()
        if interaction:
            cmd = f"`/{interaction.command.name}`" if interaction.command else 'Unknown Cmd'
            chan = f" in {interaction.channel.mention}" if isinstance(interaction.channel, discord.TextChannel) else f" Ch:{interaction.channel_id}" if interaction.channel else ""
            user = f"{interaction.user.mention} (`{interaction.user.id}`)"
            embed.add_field(name="Context", value=f"Cmd: {cmd}{chan}\nUser: {user}", inline=False)
        if error:
            etype, emsg = type(error).__name__, str(error)
            tb = "".join(traceback.format_exception(type(error), error, error.__traceback__, limit=6))
            tb_short = (tb[:950] + "\n... (Truncated)") if len(tb) > 950 else tb
            details = f"**Type:** `{etype}`\n" + (f"**Msg:** `{emsg}`\n" if emsg else "") + f"**Traceback:**\n```py\n{tb_short}\n```"
            embed.add_field(name="Error Details", value=details[:1024], inline=False) # Limit field length
            full_tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            print(f"---\nERROR LOGGED:\nGuild: {guild.id if guild else 'N/A'}\nCtx: {message}\nErr: {etype}: {emsg}\n{full_tb}---\n")
    await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, embed=embed)

# --- Embed Pagination View ---
class HCPagesView(View):
    """ Paginated view for HC members (numbered, username#tag ➔ IGN format)."""
    def __init__(self, data: List[Tuple[Optional[discord.Member], str]], total_members: int, timeout=300.0):
        super().__init__(timeout=timeout)
        self.data = data
        self.total_members = total_members
        self.current_page = 0
        self.total_pages = math.ceil(len(self.data) / MEMBERS_PER_PAGE) if self.data else 1
        self.message: Optional[discord.Message] = None
        self.update_buttons()

    def create_page_embed(self) -> discord.Embed:
        """ Creates embed for current page (numbered, username#tag ➔ IGN)."""
        start_index = self.current_page * MEMBERS_PER_PAGE
        page_data = self.data[start_index : start_index + MEMBERS_PER_PAGE]
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, color=NERDY_YELLOW)
        desc_lines = []
        idx = start_index + 1
        for member, ign in page_data:
            user_str = discord.utils.escape_markdown(member.name) if member else "*User Left Server?*" # Use member.name
            ign_str = discord.utils.escape_markdown(ign if ign else "Unknown")
            desc_lines.append(f"{idx}. {user_str} ➔ {ign_str}")
            idx += 1
        embed.description = "\n".join(desc_lines) if desc_lines else "No members on this page."
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} | Total HC Members: {self.total_members}")
        embed.timestamp = discord.utils.utcnow()
        return embed

    def update_buttons(self):
        if hasattr(self, 'children') and len(self.children) >= 2:
            prev, nxt = self.children[0], self.children[1]
            if isinstance(prev, Button): prev.disabled = self.current_page == 0
            if isinstance(nxt, Button): nxt.disabled = self.current_page >= self.total_pages - 1

    async def edit_message(self, interaction: discord.Interaction):
        embed = self.create_page_embed(); self.update_buttons()
        try: await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e: await log_error(interaction.guild, "Paginator edit fail", error=e, interaction=interaction)

    @button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="hc_prev_interactive", row=0)
    async def previous_button(self, i: discord.Interaction, b: Button):
        if self.current_page > 0: self.current_page -= 1; await self.edit_message(i)
        else: try: await i.response.defer() except discord.InteractionResponded: pass

    @button(label="Next", style=discord.ButtonStyle.blurple, custom_id="hc_next_interactive", row=0)
    async def next_button(self, i: discord.Interaction, b: Button):
        if self.current_page < self.total_pages - 1: self.current_page += 1; await self.edit_message(i)
        else: try: await i.response.defer() except discord.InteractionResponded: pass

    async def on_timeout(self):
        if self.message:
            try:
                for item in self.children:
                    if isinstance(item, Button): item.disabled = True
                await self.message.edit(view=self); print(f"Paginator timeout: {self.message.id}")
            except Exception as e: print(f"Paginator timeout edit fail: {e}")

# --- Core HC List Logic ---
async def fetch_hc_member_data(guild: discord.Guild) -> Tuple[List[Tuple[Optional[discord.Member], str]], int]:
    """ Fetches HC members, sorted by username, and their IGNs."""
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role: await log_error(guild, f"HC Role {ADD_ROLE_ID_HC} not found."); return [], 0

    members_with_role = [m for m in guild.members if hc_role in m.roles and not m.bot]
    total_count = len(members_with_role)
    members_sorted = sorted(members_with_role, key=lambda m: m.name.lower()) # Sort by username
    member_ids = [str(m.id) for m in members_sorted]
    ign_map = {}

    if supabase and member_ids:
        try:
            # Fetch IGNs in chunks
            for i in range(0, len(member_ids), 500):
                chunk = member_ids[i:i+500]
                resp = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").in_("discord_id", chunk).execute())
                if resp and hasattr(resp, 'data') and resp.data: ign_map.update({r['discord_id']: r.get("ingame_name") or "Unknown" for r in resp.data})
                await asyncio.sleep(0.1)
        except Exception as e: await log_error(guild, "IGN fetch failed.", error=e); ign_map = {mid: "DB Error" for mid in member_ids}

    member_tuples = [(m, ign_map.get(str(m.id), "Unknown")) for m in members_sorted]
    return member_tuples, total_count

def generate_hc_list_embeds(data: List[Tuple[Optional[discord.Member], str]], total_members: int) -> List[discord.Embed]:
    """ Generates static list embeds (numbered, username#tag ➔ IGN)."""
    if not data:
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, description="No HC members found.", color=discord.Color.orange()); embed.set_footer(text="Page 1/1 | Total: 0"); embed.timestamp=discord.utils.utcnow(); return [embed]

    embeds = []; total_pages = math.ceil(len(data) / MEMBERS_PER_PAGE)
    for page_num in range(total_pages):
        start = page_num * MEMBERS_PER_PAGE; page_data = data[start : start + MEMBERS_PER_PAGE]
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, color=NERDY_YELLOW); desc = []
        idx = start + 1
        for member, ign in page_data:
            user_str = discord.utils.escape_markdown(member.name) if member else "*User Left?*" # Use member.name
            ign_str = discord.utils.escape_markdown(ign if ign else "Unknown")
            desc.append(f"{idx}. {user_str} ➔ {ign_str}"); idx += 1
        embed.description = "\n".join(desc); embed.set_footer(text=f"Page {page_num + 1}/{total_pages} | Total: {total_members}"); embed.timestamp=discord.utils.utcnow(); embeds.append(embed)
    return embeds

async def update_hc_member_list(guild: discord.Guild):
    """ Updates the static HC member list in the designated channel."""
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(list_channel, discord.TextChannel): await log_error(guild, f"Static list channel {HC_MEMBER_LIST_CHANNEL_ID} invalid."); return

    bot_member = guild.me;
    if not bot_member: await log_error(guild, f"Cannot find bot in {guild.name}."); return
    perms = list_channel.permissions_for(bot_member)
    req = {"Send Messages": perms.send_messages, "Embed Links": perms.embed_links, "Read History": perms.read_message_history, "Manage Messages": perms.manage_messages}
    missing = [p for p, h in req.items() if not h]
    if missing: await log_error(guild, f"Bot missing perms in {list_channel.mention}: {', '.join(missing)}"); return

    try:
        await log_info(guild, f"Starting static list update in {list_channel.mention}...")
        member_data, total_count = await fetch_hc_member_data(guild) # Uses username sort
        new_embeds = generate_hc_list_embeds(member_data, total_count) # Uses username format
        num_new = len(new_embeds)

        # Find existing messages
        existing_msgs: List[discord.Message] = []
        try: async for msg in list_channel.history(limit=30):
                if msg.author.id == bot.user.id and msg.embeds and msg.embeds[0].title == HC_LIST_EMBED_TITLE: existing_msgs.append(msg)
        except Exception as e: await log_error(guild, "History search failed", error=e); return
        existing_msgs.sort(key=lambda m: m.created_at) # Oldest first
        num_exist = len(existing_msgs)
        print(f"Static List ({guild.name}): Found {num_exist}, Need {num_new}.")

        # Edit/Send/Delete loop
        sent_or_edited_ids = set()
        for i in range(max(num_new, num_exist)):
            await asyncio.sleep(1.2) # Rate limit delay
            if i < num_new and i < num_exist: # Edit
                try: await existing_msgs[i].edit(embed=new_embeds[i]); sent_or_edited_ids.add(existing_msgs[i].id); print(f"  Edited {existing_msgs[i].id} (Page {i+1})")
                except Exception as e: print(f"  Edit Fail Pg {i+1}: {e}") # Log error below if critical
            elif i < num_new: # Send new
                try: new_msg = await list_channel.send(embed=new_embeds[i]); sent_or_edited_ids.add(new_msg.id); print(f"  Sent {new_msg.id} (Page {i+1})")
                except Exception as e: await log_error(guild, f"Static list send fail Pg {i+1}", error=e); break # Stop if send fails
            elif i < num_exist: # Delete extra old
                msg_del = existing_msgs[i]
                if msg_del.id not in sent_or_edited_ids:
                     try: await msg_del.delete(); print(f"  Deleted surplus {msg_del.id}")
                     except Exception as e: print(f"  Delete Fail {msg_del.id}: {e}") # Log error?

        # Cleanup check (optional but safer)
        # ... (Consider adding cleanup if messages often get stuck)

        await log_info(guild, f"Static list update complete ({num_new} pages).")

    except Exception as e: await log_error(guild, f"Static list update error", error=e)


# --- Discord Events ---
@bot.event
async def on_ready():
    global BOT_ID
    if bot.user: BOT_ID = bot.user.id; print(f"Logged in as {bot.user} (ID: {BOT_ID})"); print(f"Discord.py v{discord.__version__}")
    else: print("Error: Bot user not found on ready."); return

    synced_count = 0; try: synced = await tree.sync(); synced_count = len(synced); print(f"Synced {synced_count} cmds.")
    except Exception as e: print(f"Cmd Sync fail: {e}"); g = bot.guilds[0] if bot.guilds else None; if g: await log_error(g, "Cmd Sync fail.", error=e)

    if not bot.guilds: print("Bot not in any guilds."); return
    print(f"Initial setup for {len(bot.guilds)} guilds...")
    for guild in list(bot.guilds):
        print(f"  Processing {guild.name} ({guild.id})")
        try: await log_info(guild, f"Bot ready. Synced {synced_count} cmds."); await update_hc_member_list(guild); await asyncio.sleep(1)
        except Exception as e: await log_error(guild, f"on_ready setup error", error=e)
    print("Initial setup complete.")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if after.bot or before.roles == after.roles: return # Ignore bots and role-unchanged updates
    guild = after.guild; hc_role = guild.get_role(ADD_ROLE_ID_HC); if not hc_role: return
    b_has, a_has = hc_role in before.roles, hc_role in after.roles
    if b_has != a_has: act = "added" if a_has else "removed"; await log_info(guild, f"HC role `{hc_role.name}` {act} for {after.mention}. Updating list."); await update_hc_member_list(guild)

# --- App Command Error Handling ---
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    guild = interaction.guild
    user_msg = "❌ Unexpected error."
    log_desc = "Unhandled app command error."
    err_log = error

    # Simplified error mapping
    if isinstance(error, app_commands.CommandNotFound): return # Ignore
    elif isinstance(error, (app_commands.MissingPermissions, app_commands.BotMissingPermissions)): perms=", ".join(f"`{p}`" for p in error.missing_permissions); actor="You lack" if isinstance(error,app_commands.MissingPermissions) else "I lack"; user_msg=f"❌ {actor} permissions: {perms}"; log_desc=f"{actor} perms ({perms})"; err_log=None
    elif isinstance(error, app_commands.CheckFailure): user_msg="❌ Requirements not met."; log_desc=f"CheckFailure ({type(error).__name__})"; err_log=None
    elif isinstance(error, app_commands.CommandInvokeError): err_log=error.original; user_msg=f"❌ Command error: `{type(err_log).__name__}`"; log_desc=f"Invoke Error"; print(f"InvokeErr/{interaction.command.name if interaction.command else '?'}: {err_log}")
    elif isinstance(error, app_commands.TransformerError): user_msg=f"❌ Invalid input: {error}"; log_desc="TransformerError"; err_log=error
    elif isinstance(error, app_commands.CommandOnCooldown): user_msg=f"⏳ Cooldown: Try in {error.retry_after:.1f}s."; log_desc="Cooldown"; err_log=None
    else: log_desc=f"Unknown AppError: `{type(error).__name__}`"

    await log_error(guild, log_desc, error=err_log, interaction=interaction)
    try:
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(user_msg, ephemeral=True)
    except Exception: pass # Ignore if sending response fails

# --- Modals ---
def create_embed(description: str, color: discord.Color = NERDY_YELLOW, title: Optional[str] = None) -> discord.Embed:
     return discord.Embed(title=title, description=description, color=color)

class BulkUpdateModal(Modal, title="Bulk Update IGNs"):
    """ Modal for bulk update (username#tag ➔ IGN)."""
    data = TextInput(label="Paste list (username#tag ➔ IGN)", style=discord.TextStyle.paragraph, placeholder="ExampleUser#1234 ➔ CoolIGN\n(One per line)", required=True, min_length=5, max_length=4000)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.guild; if not guild: return
        if not supabase: await interaction.followup.send(embed=create_embed("❌ DB unavailable.", discord.Color.red()), ephemeral=True); return

        lines = self.data.value.strip().splitlines()
        if not lines: await interaction.followup.send(embed=create_embed("⚠️ No data.", discord.Color.orange()), ephemeral=True); return

        try: # Pre-fetch members
            if not guild.chunked: await guild.chunk()
            members_name = {m.name.lower(): m for m in guild.members if not m.bot} # username#tag map
            members_id = {str(m.id): m for m in guild.members if not m.bot}
            members_display = {m.display_name.lower(): m for m in guild.members if not m.bot} # fallback
        except Exception as e: await log_error(guild, "Bulk member fetch fail", error=e); await interaction.followup.send(embed=create_embed("❌ Member fetch error.", discord.Color.red()), ephemeral=True); return

        succ, fail, nf = 0, 0, 0; log = []; payload = []
        for idx, line in enumerate(lines, 1):
            line = line.strip(); if not line: continue
            if "➔" not in line: fail+=1; log.append(('f', f"L{idx}: No '➔'")); continue
            try: ident, ign = map(str.strip, line.split("➔", 1)); ident_low = ident.lower()
            except ValueError: fail+=1; log.append(('f', f"L{idx}: Split error")); continue
            if not ident or not ign: fail+=1; log.append(('f', f"L{idx}: Missing data")); continue

            member = members_name.get(ident_low) or (members_id.get(ident) if ident.isdigit() else None) or members_display.get(ident_low)
            if not member: fail+=1; nf+=1; log.append(('f', f"L{idx}: User `{discord.utils.escape_markdown(ident)}` NF")); continue
            payload.append({"discord_id": str(member.id), "discord_name": member.name, "ingame_name": ign})

        # Upsert
        if payload:
            try: await run_supabase_sync(lambda: supabase.table("hc_members").upsert(payload, on_conflict="discord_id").execute()); succ = len(payload)
            except Exception as e: fail+=len(payload); log.append(('f', f"DB Error: {type(e).__name__}")); await log_error(guild, "Bulk DB Error", error=e)
        else: print("Bulk Update: No valid payload.")

        # Respond
        color = discord.Color.orange() if fail else NERDY_YELLOW
        embed = discord.Embed(title="Bulk Update Results", color=color)
        summary = f"Lines: {len(lines)} | ✅ OK: {succ} | ❌ Fail: {fail} (NF: {nf}, Err: {fail-nf})"
        embed.description = summary
        errors = "\n".join([r[1] for r in log if r[0]=='f'])
        if errors: embed.add_field(name="Issues", value=(errors[:1021]+'...') if len(errors)>1024 else errors, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_info(guild, f"Bulk update by `{interaction.user}`: OK:{succ}, Fail:{fail}.")
        if succ > 0: await update_hc_member_list(guild)


# --- Slash Commands ---

# --- Verify Command ---
@tree.command(name="verify", description="Verify a standard user (adds Verified, removes Unverified).")
@app_commands.describe(user="The user to verify.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    unverified_role, verified_role = guild.get_role(REMOVE_ROLE_ID), guild.get_role(ADD_ROLE_ID_VERIFY)
    actions, missing = [], []
    if not unverified_role: missing.append(f"Unverified ({REMOVE_ROLE_ID})")
    if not verified_role: missing.append(f"Verified ({ADD_ROLE_ID_VERIFY})")
    if missing: await interaction.response.send_message(f"❌ Setup error: Missing roles {', '.join(missing)}.", ephemeral=True); return
    if guild.me.top_role <= user.top_role and user.id != guild.owner_id: await interaction.response.send_message(f"❌ Hierarchy error.", ephemeral=True); return

    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        mod = False; reason = f"Verify by {interaction.user}"
        if unverified_role in user.roles: await user.remove_roles(unverified_role, reason=reason); actions.append(f"➖ `{unverified_role.name}`"); mod = True
        if verified_role not in user.roles: await user.add_roles(verified_role, reason=reason); actions.append(f"➕ `{verified_role.name}`"); mod = True
        if not mod: await interaction.followup.send("ℹ️ No changes needed.", ephemeral=True)
        else:
            await log_info(guild, f"`{interaction.user}` verified {user.mention}. {' '.join(actions)}.")
            pub_embed = create_embed(f"✅ **{user.display_name}** verified!\n" + "\n".join(actions), discord.Color.green())
            await interaction.followup.send("✅ Success!", ephemeral=True)
            try: await interaction.channel.send(embed=pub_embed)
            except Exception as e: await log_error(guild, "Failed public verify msg", error=e)
    except Exception as e: await log_error(guild, "/verify error", error=e, interaction=interaction); await interaction.followup.send("❌ Verify error.", ephemeral=True)

# --- Unverify Command ---
@tree.command(name="unverify", description="Revert a user to Unverified status.")
@app_commands.describe(user="The user to unverify.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True)
async def unverify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    verified_role, unverified_role = guild.get_role(ADD_ROLE_ID_VERIFY), guild.get_role(REMOVE_ROLE_ID)
    actions, missing = [], []
    if not verified_role: missing.append(f"Verified ({ADD_ROLE_ID_VERIFY})")
    if not unverified_role: missing.append(f"Unverified ({REMOVE_ROLE_ID})")
    if missing: await interaction.response.send_message(f"❌ Setup error: Missing roles {', '.join(missing)}.", ephemeral=True); return
    if guild.me.top_role <= user.top_role and user.id != guild.owner_id: await interaction.response.send_message(f"❌ Hierarchy error.", ephemeral=True); return

    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        mod = False; reason = f"Unverify by {interaction.user}"
        if verified_role in user.roles: await user.remove_roles(verified_role, reason=reason); actions.append(f"➖ `{verified_role.name}`"); mod = True
        if unverified_role not in user.roles: await user.add_roles(unverified_role, reason=reason); actions.append(f"➕ `{unverified_role.name}`"); mod = True
        if not mod: await interaction.followup.send("ℹ️ No changes needed.", ephemeral=True)
        else:
            await log_info(guild, f"`{interaction.user}` unverified {user.mention}. {' '.join(actions)}.")
            pub_embed = create_embed(f"✅ **{user.display_name}** unverified!\n" + "\n".join(actions), discord.Color.green())
            await interaction.followup.send("✅ Success!", ephemeral=True)
            try: await interaction.channel.send(embed=pub_embed)
            except Exception as e: await log_error(guild, "Failed public unverify msg", error=e)
    except Exception as e: await log_error(guild, "/unverify error", error=e, interaction=interaction); await interaction.followup.send("❌ Unverify error.", ephemeral=True)

# --- HC Verify Command ---
@tree.command(name="hcverify", description="Verify user into HC, store IGN, set nickname.")
@app_commands.describe(user="User to HC verify.", ingame_name="User's Florr IGN.")
@app_commands.checks.has_permissions(manage_roles=True, manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    await interaction.response.defer(thinking=True, ephemeral=False)
    guild = interaction.guild; if not supabase: await interaction.followup.send("❌ DB unavailable.", ephemeral=True); return
    r_rm, r_vfy, r_hc = guild.get_role(REMOVE_ROLE_ID), guild.get_role(ADD_ROLE_ID_VERIFY), guild.get_role(ADD_ROLE_ID_HC)
    logs, res, miss = [], [], []; reason = f"HC Verify by {interaction.user}"
    if not r_rm: miss.append("Unverified"); if not r_vfy: miss.append("Verified"); if not r_hc: miss.append("HC")
    if miss: await interaction.followup.send(f"❌ Setup error: Missing roles: {', '.join(miss)}.", ephemeral=True); return
    if guild.me.top_role <= user.top_role and user.id != guild.owner_id: await interaction.followup.send("❌ Hierarchy error.", ephemeral=True); return

    try:
        had_hc = r_hc in user.roles; add_roles = []; mod = False
        # Roles
        if r_rm in user.roles: await user.remove_roles(r_rm, reason=reason); logs.append("Rm UnVfy"); mod=True
        if r_vfy not in user.roles: add_roles.append(r_vfy)
        if r_hc not in user.roles: add_roles.append(r_hc)
        if add_roles: await user.add_roles(*add_roles, reason=reason); names = ', '.join(f"`{r.name}`" for r in add_roles); logs.append(f"Add {names}"); res.append(f"➕ Roles: {names}"); mod=True
        elif not mod: res.append("ℹ️ Roles OK.")
        # DB
        db_ok = False; try: await run_supabase_sync(lambda: supabase.table("hc_members").upsert({"discord_id": str(user.id),"discord_name": user.name,"ingame_name": ingame_name},"on_conflict").execute()); logs.append("Upsert IGN"); res.append(f"💾 IGN: `{discord.utils.escape_markdown(ingame_name)}`"); db_ok=True
        except Exception as e: logs.append("DB Fail"); res.append("⚠️ DB Fail!"); await log_error(guild,"DB upsert fail",e,interaction)
        # Nick
        nick_stat="OK"; trunc=False; target=ingame_name[:32]; if len(ingame_name)>32: trunc=True
        if user.nick != target: try: await user.edit(nick=target, reason=reason); msg=f"🏷️ Nick: `{discord.utils.escape_markdown(target)}`"+(" (trunc)"if trunc else ""); logs.append("Set Nick"); res.append(msg); nick_stat="Set"
            except discord.Forbidden: logs.append("Nick Perm Fail"); res.append("⚠️ Nick Fail (Perms)"); nick_stat="PermFail"
            except Exception as e: logs.append(f"Nick Err:{type(e).__name__}"); res.append("⚠️ Nick Fail (Err)"); nick_stat="Error"; await log_error(guild,"Nick fail",e,interaction)
        else: logs.append("Nick OK"); res.append("🏷️ Nick OK.")
        # Log & Respond
        await log_info(guild, f"`{interaction.user}` HCVerify `{user.display_name}`: {'; '.join(logs)}.")
        err = not db_ok or nick_stat in ["PermFail", "Error"]; title_sfx=" (issues)" if err else ""
        color = discord.Color.orange() if err else discord.Color.green()
        await interaction.followup.send(embed=create_embed(title=f"✅ HC Verified: {user.display_name}{title_sfx}", description="\n".join(res), color=color))
        # Update List
        if (r_hc in add_roles) or (had_hc and db_ok): await update_hc_member_list(guild)
    except Exception as e: await log_error(guild,"/hcverify error",e,interaction); await interaction.followup.send("❌ HCVerify error.", ephemeral=True)

# --- Un-HC-Verify Command ---
@tree.command(name="unhcverify", description="Remove HC role and reset nickname.")
@app_commands.describe(user="User to un-HC-verify.")
@app_commands.checks.has_permissions(manage_roles=True, manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True)
async def unhcverify(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(thinking=True, ephemeral=False)
    guild = interaction.guild; r_hc = guild.get_role(ADD_ROLE_ID_HC)
    logs, res = [], []; reason = f"Un-HCVerify by {interaction.user}"
    if not r_hc: await interaction.followup.send("❌ Setup error: Missing HC role.", ephemeral=True); return
    if guild.me.top_role <= user.top_role and user.id != guild.owner_id: await interaction.followup.send("❌ Hierarchy error.", ephemeral=True); return

    try:
        role_rm = False
        if r_hc in user.roles: await user.remove_roles(r_hc, reason=reason); logs.append("Rm HC Role"); res.append(f"➖ Role: `{r_hc.name}`"); role_rm = True
        else: await interaction.followup.send(f"ℹ️ {user.display_name} lacks `{r_hc.name}`.", ephemeral=True); return

        nick_stat="OK"
        if user.nick is not None: try: await user.edit(nick=None, reason=reason); logs.append("Reset Nick"); res.append("🏷️ Nick Reset"); nick_stat="Reset"
            except discord.Forbidden: logs.append("Nick Reset PermFail"); res.append("⚠️ Nick Reset Fail (Perms)"); nick_stat="PermFail"
            except Exception as e: logs.append(f"Nick Reset Err:{type(e).__name__}"); res.append("⚠️ Nick Reset Fail (Err)"); nick_stat="Error"; await log_error(guild,"Nick reset fail",e,interaction)
        else: logs.append("No nick"); res.append("🏷️ No Nick.")

        await log_info(guild, f"`{interaction.user}` UnHCVerify `{user.display_name}`: {'; '.join(logs)}.")
        err = nick_stat in ["PermFail", "Error"]; title_sfx = " (issues)" if err else ""
        color = discord.Color.orange() if err else discord.Color.green()
        await interaction.followup.send(embed=create_embed(title=f"✅ Un-HC-Verified: {user.display_name}{title_sfx}", description="\n".join(res), color=color))
        if role_rm: await update_hc_member_list(guild)
    except Exception as e: await log_error(guild,"/unhcverify error",e,interaction); await interaction.followup.send("❌ UnHCVerify error.", ephemeral=True)


# --- HC Members Interactive List ---
@tree.command(name="hcmembers", description="Show interactive list of [HC1] members (username#tag ➔ IGN).")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild; if not guild: await interaction.response.send_message("Use in server.", ephemeral=True); return
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS: allowed=[f"<#{c}>" for c in ALLOWED_CHANNEL_IDS if guild.get_channel(c)]; await interaction.response.send_message(f"❌ Use in: {', '.join(allowed) or 'N/A'}", ephemeral=True); return

    await interaction.response.defer(thinking=True, ephemeral=False)
    if not supabase: await interaction.followup.send(embed=create_embed("❌ DB unavailable.", discord.Color.red())); return

    try:
        member_data, total_count = await fetch_hc_member_data(guild) # Uses username sort & format
        if not member_data: role=guild.get_role(ADD_ROLE_ID_HC); role_n=f"`{role.name}`" if role else f"ID {ADD_ROLE_ID_HC}"; desc=f"No members with {role_n}."+(" DB err?" if total_count>0 else ""); await interaction.followup.send(embed=create_embed(f"{HC_LIST_EMBED_TITLE}\n{desc}", discord.Color.orange()))
        else: view = HCPagesView(member_data, total_count); embed = view.create_page_embed(); msg = await interaction.followup.send(embed=embed, view=view); view.message = msg; await log_info(guild, f"/hcmembers by `{interaction.user}`.")
    except Exception as e: await log_error(guild, "/hcmembers error", error=e, interaction=interaction); await interaction.followup.send(embed=create_embed("❌ List fetch error.", discord.Color.red()))


# --- Refresh Static List Command ---
@tree.command(name="refresh", description="Manually refresh static [HC1] list (username#tag ➔ IGN).")
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    guild = interaction.guild; if not guild: return
    if not supabase: await interaction.followup.send("❌ DB unavailable.", ephemeral=True); return
    chan = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not isinstance(chan, discord.TextChannel): await interaction.followup.send("❌ List channel invalid.", ephemeral=True); return

    try: await log_info(guild, f"Manual refresh triggered by `{interaction.user}`."); await update_hc_member_list(guild); await interaction.followup.send(f"✅ Refresh initiated for {chan.mention}.", ephemeral=True)
    except Exception as e: await log_error(guild, "/refresh error", error=e, interaction=interaction); await interaction.followup.send("❌ Refresh error.", ephemeral=True)


# --- Bulk Update Command ---
@tree.command(name="bulkupdate", description="Open form to bulk update IGNs (username#tag ➔ IGN).")
@app_commands.checks.has_permissions(manage_roles=True)
async def bulkupdate(interaction: discord.Interaction):
    try: await interaction.response.send_modal(BulkUpdateModal()); await log_info(interaction.guild, f"`{interaction.user}` opened bulk modal.")
    except Exception as e: await log_error(interaction.guild, "Bulk modal open error", error=e, interaction=interaction); if not interaction.response.is_done(): try: await interaction.response.send_message("❌ Form open error.", ephemeral=True) except Exception: pass


# --- Sync Nicknames Command ---
@tree.command(name="syncnicknames", description="Sync all HC members' nicknames with their stored IGNs.")
@app_commands.checks.has_permissions(manage_nicknames=True)
@app_commands.checks.bot_has_permissions(manage_nicknames=True)
async def syncnicknames(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    guild = interaction.guild; if not guild: return
    if not supabase: await interaction.followup.send("❌ DB unavailable.", ephemeral=True); return
    hc_role = guild.get_role(ADD_ROLE_ID_HC); if not hc_role: await interaction.followup.send("❌ HC Role invalid.", ephemeral=True); return

    start_time = discord.utils.utcnow()
    await log_info(guild, f"SyncNick started by `{interaction.user}`.")
    await interaction.edit_original_response(content="🔄 Fetching data...")

    # --- FIXED DATA FETCHING ---
    ign_data = {}
    try:
        resp = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").execute())
        if resp and hasattr(resp, 'data') and resp.data:
            # Filter only entries with both ID and IGN
            ign_data = {item['discord_id']: item['ingame_name']
                        for item in resp.data
                        if item.get('discord_id') and item.get('ingame_name')}
        print(f"SyncNick ({guild.name}): Fetched {len(ign_data)} IGN records.")
    except ConnectionError:
        await log_error(guild, "SyncNick DB Conn Fail", interaction=interaction)
        await interaction.edit_original_response(content="❌ DB Connection Fail."); return
    except Exception as e:
        await log_error(guild, "SyncNick DB Fetch Fail", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ DB Fetch Fail."); return
    # --- END FIX ---

    hc_members = [m for m in guild.members if hc_role in m.roles and not m.bot]
    total = len(hc_members); if total == 0: await interaction.edit_original_response(content="ℹ️ No HC members."); return
    await interaction.edit_original_response(content=f"🔄 Syncing {total} nicks...")

    counts = {'p': 0, 'u': 0, 'k': 0, 'ni': 0, 'h': 0, 'f': 0, 'o': 0}; bot_top = guild.me.top_role
    last_prog_update = asyncio.get_event_loop().time()

    for idx, m in enumerate(hc_members):
        counts['p'] += 1; mid = str(m.id)
        if bot_top <= m.top_role and m.id != guild.owner_id: counts['h'] += 1; continue # Hierarchy check
        ign = ign_data.get(mid); if not ign: counts['ni'] += 1; continue # No IGN check
        target = ign[:32]; if m.nick == target: counts['k'] += 1; continue # Skip if match

        try: await m.edit(nick=target, reason=f"Sync by {interaction.user}"); counts['u'] += 1; await asyncio.sleep(0.15) # Update
        except discord.Forbidden: counts['f'] += 1 # Permissions fail
        except Exception as e: counts['o'] += 1; if counts['o'] < 5: await log_error(guild, f"SyncNick Err: {m.name}", error=e, embed=None) # Other fail

        # Progress Update
        now = asyncio.get_event_loop().time()
        if now - last_prog_update > 5.0:
            try: await interaction.edit_original_response(content=f"🔄 Syncing... ({counts['p']}/{total})"); last_prog_update = now
            except Exception: break # Stop if interaction gone

    # Summary
    end_time = discord.utils.utcnow(); duration = (end_time - start_time).total_seconds()
    embed = discord.Embed(title="Nickname Sync Complete!", color=NERDY_YELLOW, timestamp=end_time)
    summary = f"Processed: {counts['p']}/{total} | ✅Upd: {counts['u']} | ℹ️Skip: {counts['k']} | ⚠️NoIGN: {counts['ni']}\n❌Fail (H): {counts['h']} | ❌Fail (P): {counts['f']} | ❌Fail (O): {counts['o']} | ⏱️ {duration:.1f}s"
    embed.description = summary
    try: await interaction.edit_original_response(content=None, embed=embed)
    except Exception: print(f"SyncNick ({guild.name}): Failed final summary.")
    await log_info(guild, "", embed=discord.Embed(title="Nickname Sync Finished", description=summary, color=NERDY_YELLOW).set_footer(text=f"By {interaction.user}"))


# --- Wither Command ---
@tree.command(name="wither", description="Temporarily remove all roles from a user (except @everyone).")
@app_commands.describe(user="User to wither.", time="Time in minutes (0.1 to 10, default 2).")
async def wither(interaction: discord.Interaction, user: discord.Member, time: app_commands.Range[float, 0.1, 10.0] = 2.0):
    guild = interaction.guild; invoker = interaction.user; bot_member = guild.me

    async def fail_log(reason: str, pub_msg: str, err: Optional[Exception] = None): # Simplified fail helper
        await log_error(guild, f"Wither Fail ({invoker.name} -> {user.name}): {reason}", error=err, interaction=interaction)
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        try: await send(embed=create_embed(pub_msg, discord.Color.red()), ephemeral=True)
        except Exception: pass

    # Checks
    if invoker.id not in ALLOWED_WITHER_IDS: await fail_log("No perm.", "❌ No permission."); return
    if user.id == invoker.id: await fail_log("Self-wither.", "🤨 Why?"); return
    if user.id == SELF_PROTECTED_ID and invoker.id != SELF_PROTECTED_ID: await fail_log("Protected.", "😨 Cannot wither Creator!"); return
    if user.id == BOT_ID: await fail_log("Target self.", "😭 Cannot wither me!"); return
    if user.bot: await fail_log("Target bot.", "🤖 Cannot wither bots."); return
    if user.id == guild.owner_id and invoker.id != guild.owner_id: await fail_log("Target owner.", "👑 Cannot wither owner!"); return
    if bot_member.top_role <= user.top_role: await fail_log("Bot hierarchy low.", "❌ Hierarchy error (Bot)."); return
    if invoker.top_role <= user.top_role and invoker.id != guild.owner_id: await fail_log("Invoker hierarchy low.", "❌ Hierarchy error (You)."); return

    await interaction.response.defer(thinking=True, ephemeral=False)
    original_roles = [r for r in user.roles if r != guild.default_role]
    if not original_roles: await interaction.followup.send(embed=create_embed(f"ℹ️ {user.display_name} has no roles.", discord.Color.orange())); return

    try:
        time_secs = int(time * 60); reason_w = f"Wither by {invoker.name} ({time:.1f}m)"
        await user.edit(roles=[], reason=reason_w)
        roles_str = (', '.join(f"`{r.name}`" for r in original_roles))[:1000]
        await interaction.followup.send(embed=create_embed(title="🌪️ Wither Cast! 🌪️", description=f"{user.mention} withered by {invoker.mention} for **{time:.1f} mins**!\nRemoved: {roles_str}", color=discord.Color.dark_purple()))
        await log_info(guild, f"`{user.name}` withered by `{invoker.name}` for {time:.1f}m.")

        await asyncio.sleep(time_secs) # Wait

        member_after = await guild.fetch_member(user.id) # Re-fetch
        if bot_member.top_role <= member_after.top_role: await fail_log(f"Bot hierarchy low on restore.", f"⚠️ Failed restore {member_after.mention} (hierarchy)."); return # Check hierarchy again
        await member_after.edit(roles=original_roles, reason=f"Wither ended ({time:.1f}m)")
        await interaction.followup.send(embed=create_embed(f"✨ {member_after.mention}'s roles restored!", color=NERDY_YELLOW))
        await log_info(guild, f"Restored roles for `{member_after.name}` after wither.")

    except discord.NotFound: await log_info(guild, f"`{user.name}` left before roles restored.")
    except Exception as e: phase="restore" if interaction.response.is_done() else "remove"; await fail_log(f"Error {phase}.", f"❌ Error during {phase}.", err=e)


# --- Nerd Help Command ---
@tree.command(name="nerdhelp", description="Show the list of available bot commands.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild; if not guild: await interaction.response.send_message("Use in server.", ephemeral=True); return
    embed = discord.Embed(title="🤓 Pingslave Bot Commands", description="Available commands:", color=NERDY_YELLOW)
    list_ch = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID); list_m = list_ch.mention if list_ch else f"ID {HC_MEMBER_LIST_CHANNEL_ID}"
    allow_ch = [f"<#{c}>" for c in ALLOWED_CHANNEL_IDS if guild.get_channel(c)]; allow_s = ", ".join(allow_ch) or "N/A"

    def add_help(n, v, p="Everyone", nt=None): fv=f"{v}\n**Perms:** `{p}`"+(f"\n**Note:** {nt}" if nt else ""); embed.add_field(name=n, value=fv, inline=False)

    embed.add_field(name="\u200B", value="**--- Verification ---**", inline=False)
    add_help("/verify `<user>`", "Verify user.", "Manage Roles")
    add_help("/unverify `<user>`", "Unverify user.", "Manage Roles")
    add_help("/hcverify `<user>` `<IGN>`", "Verify into HC.", "Manage Roles, Manage Nicknames", "Updates list.")
    add_help("/unhcverify `<user>`", "Remove from HC.", "Manage Roles, Manage Nicknames", "Updates list.")
    embed.add_field(name="\u200B", value="**--- HC List (username#tag ➔ IGN) ---**", inline=False)
    add_help("/hcmembers", "Interactive HC list.", "Everyone", f"Use in: {allow_s}.")
    add_help("/refresh", "Update static HC list.", "Manage Roles", f"Updates list in {list_m}.")
    embed.add_field(name="\u200B", value="**--- Utilities ---**", inline=False)
    add_help("/bulkupdate", "Bulk update IGNs.", "Manage Roles", "Format: `username#tag ➔ IGN`. Updates list.")
    add_help("/syncnicknames", "Sync HC nicks from IGNs.", "Manage Nicknames")
    add_help("/wither `<user>` `[time]`", "Temp remove roles.", "Special Permission", f"Max {MAX_WITHER_SECONDS/60:.0f}m.")
    add_help("/nerdhelp", "This help menu.", "Everyone")

    embed.set_footer(text="Bot by TheNerd"); bot_u=bot.user; if bot_u and bot_u.display_avatar: embed.set_thumbnail(url=bot_u.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=False)


# --- Bot Startup ---
if __name__ == "__main__":
    print("--- Initializing Pingslave Bot ---")
    if not TOKEN: print("CRITICAL: DISCORD_BOT_TOKEN missing.")
    elif not supabase: print("CRITICAL: Supabase client failed.")
    else:
        print("Token & Supabase OK."); print("Starting Keep Alive...")
        keep_alive()
        try: print("Starting Discord Bot run..."); bot.run(TOKEN, log_handler=None) # Use default discord.py logging
        except discord.LoginFailure: print("CRITICAL: Login Failure. Check Token.")
        except discord.PrivilegedIntentsRequired: print("CRITICAL: Privileged Intents (Members) missing.")
        except Exception as e: print(f"CRITICAL: Bot run failed: {e}"); print(traceback.format_exc())
    print("--- Bot process finished ---")
