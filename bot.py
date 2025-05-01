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
import datetime

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
# Key Features: /verify, /hcverify (stores IGN), static list updates, /hcmembers (interactive list), /syncnicknames, /wither, /nerdhelp.
# (Check /nerdhelp's code for latest list of features. This list might be outdated.)
# --- END CONTEXT ---

# --- Configuration ---
load_dotenv()  # harmless in production; only loads if a .env file exists
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
REMOVE_ROLE_ID = 1360176495947022447 # "Unverified" role
ADD_ROLE_ID_VERIFY = 1248708073019805717 # "Verified" role
ADD_ROLE_ID_HC = 1230235110415274004 # "HC" role
ALLOWED_CHANNEL_IDS = {1354431395140731165, 1330664430148780102, 1248710731407560835, 1367362849122549801} # Channels for /hcmembers
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

async def check_supabase_available(interaction: discord.Interaction) -> bool:
    """
    Checks if Supabase client is initialized. If not, sends an ephemeral error
    response/followup to the interaction and logs the error. Returns True if available, False otherwise.
    """
    if supabase:
        return True
    else:
        # Supabase client is None (failed initialization or not configured)
        error_message_user = "❌ Database connection unavailable. This feature cannot be used right now."
        log_description = f"Command '/{interaction.command.name if interaction.command else 'Unknown'}' failed: Supabase client is not available."

        # Log the error internally
        await log_error(interaction.guild, log_description, interaction=interaction)

        # Try to inform the user ephemerally
        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_message_user, ephemeral=True)
            else:
                # If not deferred/responded yet, respond directly
                await interaction.response.send_message(error_message_user, ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded, discord.HTTPException) as e:
             # Log if sending the user message fails, but the function still returns False
             print(f"Error sending Supabase check failure message to user (InteractionID: {interaction.id}): {type(e).__name__} - {e}")
        except Exception as e_send:
            print(f"Unexpected Error sending Supabase check failure message (InteractionID: {interaction.id}): {e_send}")

        return False # Indicate Supabase is not available

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
    """ Paginated view for HC members (formatted table, mobile-friendly)."""
    def __init__(self, data: List[Tuple[Optional[discord.Member], str]], total_members: int, timeout=300.0):
        super().__init__(timeout=timeout)
        self.data = data
        self.total_members = total_members
        self.current_page = 0
        self.total_pages = math.ceil(len(self.data) / MEMBERS_PER_PAGE) if self.data else 1
        self.message: Optional[discord.Message] = None
        # Ensure buttons are updated after initialization
        self.update_buttons() # <--- This call needs the method below to exist

    # --- THIS METHOD NEEDS TO EXIST ---
    def update_buttons(self):
        """Disables buttons based on the current page."""
        # Check if children exist and have at least 2 elements before accessing
        # Assumes Previous is children[0] and Next is children[1]
        if hasattr(self, 'children') and len(self.children) >= 2:
            # It's safer to access by custom_id if possible, but index works if order is fixed
            prev_button = self.children[0]
            next_button = self.children[1]
            if isinstance(prev_button, Button):
                prev_button.disabled = self.current_page == 0
            if isinstance(next_button, Button):
                next_button.disabled = self.current_page >= self.total_pages - 1
        else:
            # Log or handle the case where buttons aren't found as expected
            print(f"Warning: Could not find Previous/Next buttons in HCPagesView children to update state.")

    # --- UPDATED create_page_embed ---
    def create_page_embed(self) -> discord.Embed:
        # --- Define Column Widths (Mobile Optimized) ---
        IDX_WIDTH = 3   # "99."
        NAME_WIDTH = 15 # Reduced for mobile
        IGN_WIDTH = 15  # Reduced for mobile
        ABC_WIDTH = 4   # Reduced for mobile ("abc ")

        # Calculate total expected width for separator
        TOTAL_WIDTH = IDX_WIDTH + NAME_WIDTH + IGN_WIDTH + ABC_WIDTH

        start = self.current_page * MEMBERS_PER_PAGE
        page_data = self.data[start : start + MEMBERS_PER_PAGE]

        # --- Create Header ---
        header = (
            f"{'#':<{IDX_WIDTH}}"
            f"{'Discord':<{NAME_WIDTH}}"        # Shorter title
            f"{'In-Game':<{IGN_WIDTH}}"         # Shorter title
            f"{'abc':<{ABC_WIDTH}}"
        )
        separator = "-" * TOTAL_WIDTH

        # --- Build Description within Code Block ---
        desc_lines = [f"```", header, separator] # Use plain code block
        idx = start + 1
        for member, ign in page_data: # <--- Use the same loop structure
            # Prepare display strings
            if member: # Check if it's a discord.Member object
                user_display = f"{member.name}#{member.discriminator}" if member.discriminator != '0' else member.name
                is_discord_member = True
            else:
                # This is a non-Discord entry (member is None)
                user_display = "[No Discord]" # Or "---", or ""
                is_discord_member = False

            ign_display = str(ign) if ign else "Unknown"
            abc_val = "1" # Keep your 'abc' column logic if needed

            # Truncate aggressively with ellipsis (apply to placeholder too if needed)
            if len(user_display) > NAME_WIDTH:
                user_display = user_display[:NAME_WIDTH-1] + "…"
            if len(ign_display) > IGN_WIDTH:
                ign_display = ign_display[:IGN_WIDTH-1] + "…"

            # Format the line (ensure alignment still works)
            line = (
                f"{str(idx)+'.':<{IDX_WIDTH}}"
                f"{user_display:<{NAME_WIDTH}}"
                f"{ign_display:<{IGN_WIDTH}}"
                f"{abc_val:<{ABC_WIDTH}}"
            )
            desc_lines.append(line)
            idx += 1

        if not page_data:
            desc_lines = ["```\nNo members on this page.\n```"] # Plain code block
        else:
             desc_lines.append("```") # Close the code block

        # --- Create Embed ---
        embed = discord.Embed(
            title=HC_LIST_EMBED_TITLE,
            description="\n".join(desc_lines),
            color=NERDY_YELLOW
        )
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} | Total: {self.total_members}")
        embed.timestamp = discord.utils.utcnow()
        return embed

    # --- edit_message ---
    async def edit_message(self, interaction: discord.Interaction):
        embed = self.create_page_embed()
        self.update_buttons() # Update button states before editing
        try:
            # Check if interaction is already responded to or deferred
            if interaction.response.is_done():
                 # If we have the message object, edit it
                 if self.message:
                     await self.message.edit(embed=embed, view=self)
                 else:
                     # If message is somehow None after response is done, log and maybe followup
                     print(f"Warning: edit_message called but self.message is None (Interaction ID: {interaction.id})")
                     await interaction.followup.send("Error updating view (message not found).", ephemeral=True)
            else:
                 # If not responded/deferred yet, use edit_message on the response
                 await interaction.response.edit_message(embed=embed, view=self)

        except discord.NotFound:
            print(f"Paginator edit fail: Original message {self.message.id if self.message else 'Unknown'} not found or interaction expired.")
            # Disable buttons on the view instance if message is gone
            for item in self.children:
                if isinstance(item, Button): item.disabled = True
            self.stop() # Stop the view as well
        except discord.HTTPException as e:
            guild = interaction.guild or (self.message.guild if self.message else None)
            await log_error(guild, "Paginator edit fail (HTTP)", error=e, interaction=interaction)
        except Exception as e:
            guild = interaction.guild or (self.message.guild if self.message else None)
            await log_error(guild, "Paginator edit fail (General)", error=e, interaction=interaction)

    # --- previous_button ---
    @button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="hc_prev_interactive", row=0)
    async def previous_button(self, interaction: discord.Interaction, b: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.edit_message(interaction)
        else:
            # Acknowledge button press even if no action is taken
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer()
            except discord.InteractionResponded: pass
            except discord.NotFound: print("Previous Button: Interaction expired before defer.")
            except Exception as e: await log_error(interaction.guild, "Previous Button Defer Error", e, interaction)


    # --- next_button ---
    @button(label="Next", style=discord.ButtonStyle.blurple, custom_id="hc_next_interactive", row=0)
    async def next_button(self, interaction: discord.Interaction, b: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.edit_message(interaction)
        else:
            # Acknowledge button press even if no action is taken
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer()
            except discord.InteractionResponded: pass
            except discord.NotFound: print("Next Button: Interaction expired before defer.")
            except Exception as e: await log_error(interaction.guild, "Next Button Defer Error", e, interaction)

    # --- on_timeout ---
    async def on_timeout(self):
        if self.message:
            try:
                # Create a new view instance based on the message state to disable buttons
                view_copy = View.from_message(self.message)
                if view_copy: # Ensure view_copy was successfully created
                    for item in view_copy.children:
                        if isinstance(item, Button):
                            item.disabled = True
                    await self.message.edit(view=view_copy)
                    print(f"Paginator timeout: Disabled buttons on message {self.message.id}")
                else:
                    # Fallback if from_message fails, attempt edit with None view
                    await self.message.edit(view=None)
                    print(f"Paginator timeout: Cleared view on message {self.message.id} (from_message failed)")
            except discord.NotFound: print(f"Paginator timeout edit fail: Message {self.message.id} not found.")
            except discord.HTTPException as e:
                 guild = self.message.guild
                 # Avoid logging 404 again if it was caught above
                 if e.status != 404:
                     await log_error(guild, f"Paginator timeout edit HTTP fail on message {self.message.id}", error=e)
            except Exception as e:
                 guild = self.message.guild
                 await log_error(guild, f"Paginator timeout edit general fail on message {self.message.id}", error=e)
        self.stop() # Stop the view logic regardless of message edit success

# --- REVISED fetch_hc_member_data ---
async def fetch_hc_member_data(guild: discord.Guild) -> Tuple[List[Tuple[Optional[discord.Member], str]], int]:
    """
    Fetches HC members from Discord and Supabase.
    Returns a list combining [(discord_member, ign), ..., (None, ign_only_in_db), ...], sorted with Discord members first.
    """
    print(f"Fetch HC Data ({guild.name}): Starting fetch...")
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"HC Role {ADD_ROLE_ID_HC} not found during fetch.")
        return [], 0

    # 1. Fetch ALL entries from Supabase
    all_db_members_map: Dict[str, Dict] = {} # discord_id -> {'ign': ign, 'processed': False}
    non_discord_db_members: List[Tuple[None, str]] = [] # [(None, ign)]
    try:
        if not supabase:
            raise ConnectionError("Supabase client unavailable.")
        print(f"Fetch HC Data ({guild.name}): Fetching all from Supabase hc_members table...")
        # Fetch in chunks if table might be very large (though unlikely needed here)
        resp = await run_supabase_sync(
            lambda: supabase.table("hc_members")
                            .select("discord_id, ingame_name")
                            # .limit(1000) # Add limit/pagination if table is huge
                            .execute()
        )
        if resp and hasattr(resp, 'data') and resp.data:
            for entry in resp.data:
                ign = entry.get("ingame_name") or "Unknown DB IGN"
                d_id = entry.get("discord_id") # This can now be None
                if d_id:
                    # Store entries with discord_id in a map for quick lookup
                    all_db_members_map[str(d_id)] = {"ign": ign, "processed": False}
                else:
                    # Store entries without discord_id directly in the non-discord list
                    non_discord_db_members.append((None, ign))
            print(f"Fetch HC Data ({guild.name}): Found {len(all_db_members_map)} DB entries with Discord ID, {len(non_discord_db_members)} without.")
        else:
             print(f"Fetch HC Data ({guild.name}): No data returned from Supabase.")

    except (ConnectionError, APIError, Exception) as e:
        await log_error(guild, "Failed to fetch all data from Supabase", error=e)
        # Return empty or potentially partial data based on what was fetched before error?
        # For simplicity, return empty on critical DB failure
        return [], 0

    # 2. Get Discord members with the HC role
    discord_hc_members: List[discord.Member] = []
    try:
        if not guild.chunked:
            print(f"Fetch HC Data ({guild.name}): Chunking guild...")
            await guild.chunk(cache=True)
        discord_hc_members = [m for m in guild.members if hc_role in m.roles and not m.bot]
        print(f"Fetch HC Data ({guild.name}): Found {len(discord_hc_members)} Discord members with HC role.")
    except Exception as e:
        await log_error(guild, "Guild chunking/member fetch failed", error=e)
        # Continue with potentially empty list, Supabase entries might still exist

    # 3. Correlate Discord members with DB data and build the final lists
    discord_members_data: List[Tuple[discord.Member, str]] = []

    for member in discord_hc_members:
        member_id_str = str(member.id)
        db_entry = all_db_members_map.get(member_id_str)
        ign = "Unknown" # Default if not found in DB map
        if db_entry:
            ign = db_entry["ign"]
            db_entry["processed"] = True # Mark as processed
        else:
             # This member has the HC role but isn't in our DB map (or DB failed)
             # Log this potential inconsistency?
             await log_info(guild, f"Fetch HC Data Warning: Discord member {member.mention} (`{member.id}`) has HC role but no matching DB entry found.")
             # Decide if you want to show them with 'Unknown' IGN or skip them. Showing them seems better.

        discord_members_data.append((member, ign))

    # 4. Add remaining DB entries (those whose Discord members lost the role or left) to non_discord_list
    for d_id, entry_data in all_db_members_map.items():
        if not entry_data["processed"]:
            # This DB entry had a discord_id, but the corresponding member doesn't have the HC role anymore (or left)
            non_discord_db_members.append((None, entry_data["ign"]))
            # Log this change?
            # print(f"Fetch HC Data Note: DB entry for ID {d_id} (IGN: {entry_data['ign']}) no longer matches active HC Discord member.")

    # 5. Sort the lists
    # Sort Discord members by username#discriminator (case-insensitive)
    discord_members_data.sort(key=lambda item: (item[0].name.lower(), item[0].discriminator))
    # Sort non-Discord members by IGN (case-insensitive)
    non_discord_db_members.sort(key=lambda item: item[1].lower())

    # 6. Combine and return
    final_data = discord_members_data + non_discord_db_members
    total_members = len(final_data)
    print(f"Fetch HC Data ({guild.name}): Finished. Total members for list: {total_members} ({len(discord_members_data)} Discord, {len(non_discord_db_members)} non-Discord).")
    return final_data, total_members

def generate_hc_list_embeds(data: List[Tuple[Optional[discord.Member], str]], total: int) -> List[discord.Embed]:
    """ Generates static list embeds (formatted table, mobile-friendly).""" # Updated docstring

    # --- Define Column Widths (Mobile Optimized - MUST MATCH HCPagesView) ---
    IDX_WIDTH = 3
    NAME_WIDTH = 15
    IGN_WIDTH = 15
    ABC_WIDTH = 4
    TOTAL_WIDTH = IDX_WIDTH + NAME_WIDTH + IGN_WIDTH + ABC_WIDTH # For separator

    if not data:
        embed = discord.Embed(
            title=HC_LIST_EMBED_TITLE,
            # Use plain code block
            description="```\nNo HC members found.\n```", # <--- Plain code block for empty case
            color=discord.Color.orange()
        )
        embed.set_footer(text="Page 1/1 | Total: 0")
        embed.timestamp = discord.utils.utcnow()
        return [embed]

    embeds = []
    pages = math.ceil(len(data) / MEMBERS_PER_PAGE)

    # --- Create Header and Separator (once) ---
    header = (
        f"{'#':<{IDX_WIDTH}}"
        f"{'Discord':<{NAME_WIDTH}}"        # Shorter title
        f"{'In-Game':<{IGN_WIDTH}}"         # Shorter title
        f"{'abc':<{ABC_WIDTH}}"
    )
    separator = "-" * TOTAL_WIDTH

    for page in range(pages):
        start = page * MEMBERS_PER_PAGE
        page_data = data[start : start + MEMBERS_PER_PAGE]

        # --- Build Description for this page ---
         # Use plain code block ``` instead of ```md
        desc_lines = [f"```", header, separator] # <--- Plain code block start
        idx = start + 1
        for member, ign in page_data: # <--- Use the same loop structure
            # Prepare display strings
            if member: # Check if it's a discord.Member object
                user_display = f"{member.name}#{member.discriminator}" if member.discriminator != '0' else member.name
                is_discord_member = True
            else:
                # This is a non-Discord entry (member is None)
                user_display = "[No Discord]" # Or "---", or ""
                is_discord_member = False

            ign_display = str(ign) if ign else "Unknown"
            abc_val = "1" # Keep your 'abc' column logic if needed

            # Truncate aggressively with ellipsis (apply to placeholder too if needed)
            if len(user_display) > NAME_WIDTH:
                user_display = user_display[:NAME_WIDTH-1] + "…"
            if len(ign_display) > IGN_WIDTH:
                ign_display = ign_display[:IGN_WIDTH-1] + "…"

            # Format the line (ensure alignment still works)
            line = (
                f"{str(idx)+'.':<{IDX_WIDTH}}"
                f"{user_display:<{NAME_WIDTH}}"
                f"{ign_display:<{IGN_WIDTH}}"
                f"{abc_val:<{ABC_WIDTH}}"
            )
            desc_lines.append(line)
            idx += 1

        desc_lines.append("```") # Close code block
        full_desc = "\n".join(desc_lines)

        # Description limit check (same as before)
        if len(full_desc) > 4096:
            print(f"Warning: Embed description length ({len(full_desc)}) exceeded 4096 chars on page {page+1}. Truncating.")
            full_desc = full_desc[:4093] + "..."

        # --- Create Embed for the page ---
        e = discord.Embed(
            title=HC_LIST_EMBED_TITLE,
            description=full_desc,
            color=NERDY_YELLOW
        )
        e.set_footer(text=f"Page {page+1}/{pages} | Total: {total}")
        e.timestamp = discord.utils.utcnow()
        embeds.append(e)

    return embeds

async def _fetch_existing_list_messages(channel: discord.TextChannel, bot_user_id: int) -> List[discord.Message]:
    """Fetches existing messages from the bot in the channel with the correct title."""
    existing = []
    try:
        # Fetch a reasonable number of recent messages based on expected max pages + buffer
        fetch_limit = max(MEMBERS_PER_PAGE // 5, 15) + 10 # Heuristic limit
        print(f"Static List: Fetching up to {fetch_limit} messages from {channel.mention} for history.")
        async for msg in channel.history(limit=fetch_limit):
             # Ensure message is from the bot and has the specific embed title
             if msg.author and msg.author.id == bot_user_id and msg.embeds:
                  # Check embed structure carefully before accessing attributes
                  if len(msg.embeds) > 0 and msg.embeds[0].title == HC_LIST_EMBED_TITLE:
                       existing.append(msg)
    except discord.Forbidden:
        # Let the caller handle logging the Forbidden error
        print(f"Static List: Forbidden error fetching history in {channel.mention}.")
        raise
    except Exception as e:
        # Log other history fetch errors
        print(f"Static List: Error fetching history in {channel.mention}: {e}") # Simple console log
        raise # Re-raise to be handled by caller
    # Sort existing messages chronologically (oldest first) for consistent editing
    existing.sort(key=lambda m: m.created_at)
    print(f"Static List: Found {len(existing)} relevant existing messages.")
    return existing

async def _update_or_send_list_pages(channel: discord.TextChannel, existing_messages: List[discord.Message], new_embeds: List[discord.Embed], guild_for_log: discord.Guild):
    """Edits existing messages or sends new ones for the list pages, returning error counts."""
    num_new = len(new_embeds)
    num_exist = len(existing_messages)
    tasks = []
    edit_errors = 0
    send_errors = 0
    # Use a slightly longer delay for edits/sends to be safer with rate limits
    delay = 1.5

    for i in range(num_new):
        await asyncio.sleep(delay) # Apply delay before each Discord API action
        if i < num_exist:
            action_desc = f"Editing message {existing_messages[i].id} (Page {i+1})"
            print(f"  {action_desc}")
            tasks.append(existing_messages[i].edit(embed=new_embeds[i]))
        else:
            action_desc = f"Sending new message (Page {i+1})"
            print(f"  {action_desc}")
            tasks.append(channel.send(embed=new_embeds[i]))

    # Execute edits/sends concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and log errors
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            action = "Edit" if i < num_exist else "Send"
            msg_id = existing_messages[i].id if i < num_exist and i < len(existing_messages) else "New"
            error_log_msg = f"Static list {action} failed for Page {i+1} (MsgID: {msg_id})"

            if action == "Edit": edit_errors += 1
            else: send_errors += 1

            # Log the error using the bot's standard logging
            await log_error(guild_for_log, error_log_msg, error=res)

    return edit_errors, send_errors # Return error counts

async def _delete_surplus_list_pages(channel: discord.TextChannel, messages_to_delete: List[discord.Message], guild_for_log: discord.Guild):
    """Deletes surplus list messages, attempting bulk delete first, returning error count."""
    delete_errors = 0
    if not messages_to_delete:
        return delete_errors

    num_to_delete = len(messages_to_delete)
    print(f"Static List: Attempting to delete {num_to_delete} surplus message(s).")
    # Use a slightly longer delay for delete operations as well
    delay = 1.5
    # Ensure bot member object is valid before checking permissions
    bot_member = channel.guild.me
    if not bot_member:
        print("Static List Error: Cannot get bot member to check permissions for deletion.")
        # Indicate potential failure without ability to check/perform delete
        return num_to_delete # Assume all deletions will fail if bot object isn't found

    perms = channel.permissions_for(bot_member)
    can_bulk_delete = perms.manage_messages and num_to_delete > 1

    if can_bulk_delete:
        try:
            # Check if messages are too old for bulk delete (older than 14 days)
            fourteen_days_ago = discord.utils.utcnow() - datetime.timedelta(days=14)
            valid_for_bulk = [m for m in messages_to_delete if m.created_at > fourteen_days_ago]
            invalid_for_bulk = [m for m in messages_to_delete if m not in valid_for_bulk]

            if valid_for_bulk:
                 await asyncio.sleep(delay) # Delay before bulk action
                 await channel.delete_messages(valid_for_bulk)
                 print(f"  Bulk deleted {len(valid_for_bulk)} recent surplus messages.")
                 messages_to_delete = invalid_for_bulk # Update list to only contain old messages
            else:
                 print("  Skipping bulk delete: All surplus messages are too old.")
                 can_bulk_delete = False # Proceed to individual deletion for old messages

        except discord.HTTPException as e:
            # Handle potential 400 Bad Request if mix of old/new messages caused issues
            print(f"  Bulk delete failed (HTTP {e.status}): {e.text}. Falling back to individual deletion.")
            # Fallback required, keep original messages_to_delete list
            messages_to_delete = messages_to_delete # Ensure we process all if bulk fails
            can_bulk_delete = False # Force fallback
        except discord.Forbidden:
            print(f"  Bulk delete failed: Forbidden. Falling back.")
            await log_error(guild_for_log, "Static list bulk delete failed (Forbidden)")
            can_bulk_delete = False
        except Exception as e:
            print(f"  Bulk delete failed unexpectedly: {e}. Falling back.")
            await log_error(guild_for_log, "Static list bulk delete failed (Unknown)", error=e)
            can_bulk_delete = False

    # Fallback to individual deletion if bulk failed, wasn't possible, or messages were old
    if messages_to_delete: # Check if there are still messages needing deletion
         print(f"  Attempting individual deletion for {len(messages_to_delete)} remaining/old messages.")
         for msg_del in messages_to_delete:
            await asyncio.sleep(delay) # Delay each individual delete
            try:
                await msg_del.delete()
                print(f"  Individually deleted surplus message {msg_del.id}")
            except discord.NotFound:
                print(f"  Skipped deleting message {msg_del.id} (already gone).")
            except discord.Forbidden:
                delete_errors += 1
                await log_error(guild_for_log, f"Failed to delete surplus message {msg_del.id} (Forbidden)")
                # Stop trying if forbidden, likely a persistent issue
                print("  Stopping further individual deletes due to Forbidden error.")
                break # Exit the loop for individual deletes
            except Exception as e:
                delete_errors += 1
                await log_error(guild_for_log, f"Failed to delete surplus message {msg_del.id}", error=e)

    return delete_errors

# --- REFACTORED update_hc_member_list ---
async def update_hc_member_list(guild: discord.Guild):
    """ Updates static HC list (username#tag ➔ IGN format using helper functions)."""
    list_channel_id = HC_MEMBER_LIST_CHANNEL_ID
    chan = guild.get_channel(list_channel_id)
    if not isinstance(chan, discord.TextChannel):
        await log_error(guild, f"Static list channel {list_channel_id} invalid or not found.")
        return

    # Ensure bot object is ready
    if not bot or not bot.user:
        await log_error(guild, "Cannot update static list: Bot user object not available.", guild=guild)
        return
    bot_user_id = bot.user.id

    # Simplified Permission Check (as per user context - assumes bot has high roles)
    # Basic check for sending capability is still wise.
    bot_mem = guild.me
    if not bot_mem:
        try:
            bot_mem = await guild.fetch_member(bot_user_id) # Attempt fetch if not cached
        except (discord.NotFound, discord.HTTPException):
             await log_error(guild, f"Cannot update static list: Failed to get bot member object in guild {guild.name}.")
             return
    if not bot_mem: # Check again after fetch attempt
         await log_error(guild, f"Cannot update static list: Bot member object unavailable in {guild.name}.")
         return

    perms = chan.permissions_for(bot_mem)
    if not perms.send_messages or not perms.embed_links:
         await log_error(guild, f"Bot missing Send Messages or Embed Links in {chan.mention} for static list.")
         # Consider returning here as these are fundamental
         return
    # Log warnings if other perms needed for efficiency are missing
    if not perms.read_message_history:
         await log_info(guild, f"Warning: Bot missing Read Message History in {chan.mention}. List update might be inefficient.")
    if not perms.manage_messages:
         await log_info(guild, f"Warning: Bot missing Manage Messages in {chan.mention}. Surplus message cleanup may fail or be slow.")


    try:
        await log_info(guild, f"Starting static list update in {chan.mention}...")

        # 1. Fetch member data and generate new embeds
        data, total = await fetch_hc_member_data(guild)
        new_embeds = generate_hc_list_embeds(data, total)
        num_new = len(new_embeds)

        # 2. Fetch existing messages using helper
        try:
             existing_messages = await _fetch_existing_list_messages(chan, bot_user_id)
             num_exist = len(existing_messages)
             print(f"Static List Update ({guild.name}): Found {num_exist} existing bot messages, Need {num_new} pages.")
        except discord.Forbidden:
             # Specific logging for forbidden on history read
             await log_error(guild, f"Static list update failed: Bot lacks Read Message History permission in {chan.mention}.")
             return # Cannot proceed reliably without history
        except Exception as e:
             # General error during history fetch
             await log_error(guild, "Error fetching message history for static list update", error=e)
             return # Stop if history fetch fails critically

        # 3. Update/Send pages using helper
        # Pass guild object for logging context within the helper
        edit_errors, send_errors = await _update_or_send_list_pages(chan, existing_messages, new_embeds, guild)

        # 4. Delete surplus pages using helper
        messages_to_delete = existing_messages[num_new:] if num_exist > num_new else []
        # Pass guild object for logging context within the helper
        delete_errors = await _delete_surplus_list_pages(chan, messages_to_delete, guild)

        # 5. Log final status
        total_errors = edit_errors + send_errors + delete_errors
        status_msg = f"Static list update complete ({num_new} pages displayed)."
        if total_errors > 0:
            status_msg += f" Encountered {total_errors} error(s) during update (Edit:{edit_errors}, Send:{send_errors}, Delete:{delete_errors}). Check error logs."
        else:
             status_msg += " No errors encountered."

        # Log as error if any step had issues, otherwise info
        log_level = log_error if total_errors > 0 else log_info
        await log_level(guild, status_msg)

    except Exception as e:
        # Catch-all for unexpected errors in the main orchestration logic
        await log_error(guild, "Unhandled error during the main static list update process", error=e)

# --- Discord Events ---
@bot.event
async def on_ready():
    print("--- on_ready event started ---")
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
        # Sync globally. Consider syncing per-guild if commands are guild-specific
        synced_commands = await tree.sync() # Global sync
        print(f"Synced {len(synced_commands)} application commands globally.")

        command_ids.clear() # Clear old IDs before populating

        # --- CORRECTED LOOP ---
        # Iterate through the AppCommand objects returned by tree.sync()
        # These objects directly have .name and .id attributes.
        for cmd in synced_commands:
            # Check if it's a command object with name and id (should generally be true)
            if hasattr(cmd, 'name') and hasattr(cmd, 'id'):
                command_ids[cmd.name] = cmd.id
                print(f"  Stored ID for /{cmd.name}: {cmd.id}")
            else:
                # Log if we encounter something unexpected in the synced list
                print(f"  Skipped storing ID for an item during sync (type: {type(cmd)}, name: {getattr(cmd, 'name', 'N/A')})")
        # --- END CORRECTED LOOP ---

        # Check if the dictionary is populated after the loop
        if command_ids:
            print(f"Stored command IDs: {command_ids}")
        else:
             # This warning should now only appear if sync returned nothing or encountered issues
             print("Warning: command_ids dictionary is empty after sync. Help command may not show clickable links.")

    except discord.HTTPException as e:
        print(f"Command Sync failed (HTTPException): {e}")
        first_guild = bot.guilds[0] if bot.guilds else None
        if first_guild:
            # Avoid await in except block if it causes issues, log directly
            print(f"Error logged for Guild {first_guild.id}: Command Sync failed (HTTPException).")
            # Consider a non-async logging mechanism here if needed
            # await log_error(first_guild, "Application Command Sync failed on startup (HTTPException).", error=e)
    except Exception as e:
        print(f"Command Sync failed (Unexpected Error): {e}\n{traceback.format_exc()}")
        first_guild = bot.guilds[0] if bot.guilds else None
        if first_guild:
            print(f"Error logged for Guild {first_guild.id}: Command Sync failed (Exception).")
            # await log_error(first_guild, "Application Command Sync failed on startup (Exception).", error=e)

    # Ensure the bot has guilds before proceeding with guild-specific setup
    if not bot.guilds:
        print("Bot is not currently in any guilds. Skipping guild setup.")
        print("--- on_ready event finished (no guilds) ---")
        return

    print(f"Performing initial setup for {len(bot.guilds)} guild(s)...")
    # Process guilds one by one to avoid potential rate limits on setup tasks
    guilds_to_process = list(bot.guilds) # Create a copy
    for guild in guilds_to_process:
        print(f"  Processing guild: {guild.name} (ID: {guild.id})")
        try:
            # Ensure member cache is populated for this guild if necessary
            if not guild.chunked and guild.member_count is not None and guild.member_count > 1000: # Optional: Only chunk larger guilds
                 print(f"    Attempting to chunk guild {guild.name} (Members: {guild.member_count})...")
                 try:
                     await guild.chunk(cache=True)
                     print(f"    Successfully chunked guild {guild.name}.")
                 except Exception as chunk_e:
                     print(f"    Warning: Guild chunking failed for {guild.name}: {chunk_e}")
                     # Log this error using your logger if needed
                     # await log_error(guild, "Guild chunking failed during on_ready setup", error=chunk_e)


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
    if not await check_supabase_available(interaction):
        # If check fails, helper sends ephemeral msg & logs.
        try:
             # Check if we actually deferred before trying to edit
             if interaction.response.is_done():
                  await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        except (discord.NotFound, discord.HTTPException):
             pass # Ignore errors editing the deferred message
        return # Stop the command here
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
    if not await check_supabase_available(interaction):
        # If check fails, helper sends ephemeral msg & logs.
        try:
             # Check if we actually deferred before trying to edit
             if interaction.response.is_done():
                  await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        except (discord.NotFound, discord.HTTPException):
             pass # Ignore errors editing the deferred message
        return # Stop the command here
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
    if not await check_supabase_available(interaction):
        # If check fails, helper sends ephemeral msg & logs.
        try:
             # Check if we actually deferred before trying to edit
             if interaction.response.is_done():
                  await interaction.edit_original_response(content="❌ Operation cancelled: Database unavailable.", embed=None, view=None)
        except (discord.NotFound, discord.HTTPException):
             pass # Ignore errors editing the deferred message
        return # Stop the command here
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


# --- Sync Nicknames Command (Optimized DB Query) ---
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
    loading_emoji = "🔄" # Simple fallback emoji
    await interaction.edit_original_response(content=f"{loading_emoji} Fetching members...")

    # 1. Get all members with the HC role first
    hc_members: List[discord.Member] = []
    try:
        # Ensure members are cached
        if not guild.chunked:
            print(f"Chunking guild {guild.name} for sync nicknames...")
            await guild.chunk(cache=True)
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

    # Get IDs of members with the HC role
    hc_member_ids = [str(m.id) for m in hc_members]

    # 2. Fetch IGNs *only* for these specific members from Supabase
    await interaction.edit_original_response(content=f"{loading_emoji} Fetching IGN data for {total_hc_members} members...")
    ign_data = {} # discord_id (str) -> ingame_name (str)
    try:
        # Chunk the query if there are many members (e.g., > 500)
        chunk_size = 500
        for i in range(0, len(hc_member_ids), chunk_size):
            id_chunk = hc_member_ids[i:i+chunk_size]
            print(f"SyncNick ({guild.name}): Fetching IGNs for chunk {i//chunk_size + 1}/{math.ceil(len(hc_member_ids)/chunk_size)}")
            resp = await run_supabase_sync(
                lambda: supabase.table("hc_members")
                                .select("discord_id, ingame_name")
                                .in_("discord_id", id_chunk)
                                .execute()
            )
            if resp and hasattr(resp, 'data') and resp.data:
                ign_data.update({str(item['discord_id']): item['ingame_name']
                                 for item in resp.data
                                 if item.get('discord_id') and item.get('ingame_name')})
            await asyncio.sleep(0.1) # Small delay between chunks

        print(f"SyncNick ({guild.name}): Fetched {len(ign_data)} relevant IGNs from database.")
    except ConnectionError as e:
        await log_error(guild, "SyncNick: Database connection failed during IGN fetch.", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Database connection failed. Cannot proceed.")
        return
    except APIError as e:
        await log_error(guild, "SyncNick: Database API error during IGN fetch.", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Database API error. Cannot proceed.")
        return
    except Exception as e:
        await log_error(guild, "SyncNick: Database fetch failed (unexpected)", error=e, interaction=interaction)
        await interaction.edit_original_response(content="❌ Database fetch failed. Cannot proceed.")
        return

    # 3. Iterate and Update Nicknames
    await interaction.edit_original_response(content=f"{loading_emoji} Syncing {total_hc_members} members...")
    counts = {'proc': 0, 'upd': 0, 'skip_match': 0, 'skip_no_ign': 0, 'skip_empty': 0, 'skip_hier': 0, 'fail_forbid': 0, 'fail_http': 0, 'fail_other': 0}
    bot_member = guild.me # Get bot member once
    bot_pos = bot_member.top_role.position
    last_prog_update_time = asyncio.get_event_loop().time()
    update_interval = 5.0 # Update progress every 5 seconds

    for idx, member in enumerate(hc_members):
        counts['proc'] += 1
        member_id_str = str(member.id)

        # Hierarchy check: Bot must be higher than the member to change nick
        # Still important even if bot has admin, as owner/higher roles can exist
        if bot_pos <= member.top_role.position:
            counts['skip_hier'] += 1
            continue

        # Get stored IGN from the data we fetched
        stored_ign = ign_data.get(member_id_str)
        if not stored_ign:
            counts['skip_no_ign'] += 1
            continue # Skip if no IGN stored for this specific member

        target_nick = stored_ign.strip()
        if not target_nick:
            counts['skip_empty'] += 1
            continue # Skip if stored IGN is empty/whitespace

        target_nick = target_nick[:32] # Truncate

        if member.nick == target_nick:
            counts['skip_match'] += 1
            continue # Skip if nickname already matches

        # Attempt nickname update
        try:
            await member.edit(nick=target_nick, reason=f"Nickname Sync initiated by {interaction.user.id}")
            counts['upd'] += 1
            await asyncio.sleep(0.2) # Keep delay to avoid rate limits
        except discord.Forbidden:
            counts['fail_forbid'] += 1
        except discord.HTTPException as e_http:
            counts['fail_http'] += 1
            if e_http.status == 429: print(f"SyncNick ({guild.name}): Rate limit hit!") # Log rate limits
        except Exception as e_other:
            counts['fail_other'] += 1
            await log_error(guild, f"SyncNick: Unexpected error updating nick for {member.mention}", error=e_other, interaction=interaction)

        # Update progress periodically
        now = asyncio.get_event_loop().time()
        if (now - last_prog_update_time > update_interval) or (counts['proc'] == total_hc_members):
             if interaction.is_expired(): # Check if interaction expired before editing
                  print(f"SyncNick ({guild.name}): Interaction expired, cannot update progress.")
                  last_prog_update_time = now + 999 # Prevent further attempts
                  continue
             try:
                await interaction.edit_original_response(content=f"{loading_emoji} Syncing... ({counts['proc']}/{total_hc_members})")
                last_prog_update_time = now
             except (discord.NotFound, discord.HTTPException):
                print(f"SyncNick ({guild.name}): Progress update failed. Continuing sync...")
                last_prog_update_time = now + 999 # Prevent further attempts

    # 4. Send Final Summary (Same as before)
    end_time = discord.utils.utcnow()
    duration = (end_time - start_time).total_seconds()
    summary_embed = discord.Embed(title="✅ Nickname Sync Complete!", color=NERDY_YELLOW, timestamp=end_time)
    total_skipped = counts['skip_match'] + counts['skip_no_ign'] + counts['skip_empty'] + counts['skip_hier']
    total_failed = counts['fail_forbid'] + counts['fail_http'] + counts['fail_other']
    summary_lines = [
        f"⏱️ **Duration:** {duration:.2f} seconds",
        f"👥 **Total HC Members Found:** {total_hc_members}",
        f"📊 **Relevant IGNs Fetched:** {len(ign_data)}", # Added relevant fetch count
        f"🔄 **Members Processed:** {counts['proc']}",
        f"✅ **Nicknames Updated:** {counts['upd']}",
        f"ℹ️ **Skipped (No Change/Hierarchy/No IGN):** {total_skipped}",
        f"   - Already Matched: {counts['skip_match']}",
        f"   - No/Empty IGN Stored: {counts['skip_no_ign'] + counts['skip_empty']}",
        f"   - Bot Hierarchy Too Low: {counts['skip_hier']}",
        f"❌ **Failed Updates:** {total_failed}",
        f"   - Permissions Error: {counts['fail_forbid']}",
        f"   - API/HTTP Error: {counts['fail_http']}",
        f"   - Other Errors: {counts['fail_other']}"
    ]
    summary_embed.description = "\n".join(summary_lines)

    # Try edit first, then followup
    try:
        if not interaction.is_expired():
            await interaction.edit_original_response(content=None, embed=summary_embed)
        else:
            print(f"SyncNick ({guild.name}): Interaction expired before final summary edit. Attempting followup.")
            await interaction.followup.send(embed=summary_embed, ephemeral=True)
    except (discord.NotFound, discord.HTTPException) as e_edit:
        print(f"SyncNick ({guild.name}): Final summary edit failed ({e_edit}). Attempting followup.")
        try: await interaction.followup.send(embed=summary_embed, ephemeral=True)
        except Exception as e_followup: print(f"SyncNick ({guild.name}): Final followup send also failed: {e_followup}")
        await log_error(guild, "SyncNick: Could not send final summary to user.", embed=summary_embed, interaction=interaction) # Log summary if user notification failed
    except Exception as e_outer:
        print(f"SyncNick ({guild.name}): Unknown error sending final summary: {e_outer}")
        await log_error(guild, "SyncNick: Unknown error sending final summary.", error=e_outer, embed=summary_embed, interaction=interaction)

    # Log detailed summary internally
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


# --- MODIFIED Nerd Help Command (Added Spacing) ---
@tree.command(name="nerdhelp", description="Show the list of available bot commands.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return
    # Ensure bot object and user are available
    if not bot or not bot.user:
        print("Error: Bot object not available in nerdhelp command.")
        await interaction.response.send_message("Bot is not fully ready, cannot generate help. Please try again shortly.", ephemeral=True)
        return

    # Check if command_ids dictionary is populated (important for clickable links)
    if not command_ids:
        print("Warning: command_ids dictionary is empty during nerdhelp execution! Links may not be clickable.")
        # Optionally inform user if needed, but fallback will still show command name

    embed = discord.Embed(
        title="🤓 Pingslave Bot Commands",
        color=NERDY_YELLOW
    )

    # --- ADDED EMPTY FIELD FOR SPACING ---
    embed.add_field(name="\u200B", value="\u200B", inline=False)
    # --- END ADDED FIELD ---

    # --- Build Embed Fields (Command + Description in Name, Value is empty) ---

    # Section: Verification & HC Management
    embed.add_field(name="🔑 Verification & HC Management", value="\u200B", inline=False) # Section Title remains separate
    embed.add_field(name=f"{get_cmd_mention('verify')}  · Verify a standard user.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('unverify')}  · Revert a user to unverified.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('hcverify')}  · Verify a user into HC.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('unhcverify')}  · Remove a user from HC.", value="\u200B", inline=False)

    # Section: [HC1] Member List
    embed.add_field(name="\u200B\n📊 [HC1] Member List", value="\u200B", inline=False) # Section Title
    embed.add_field(name=f"{get_cmd_mention('hcmembers')}  · Show interactive HC member list.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('refresh')}  · Refresh the static HC member list.", value="\u200B", inline=False)

    # Section: Utilities
    embed.add_field(name="\u200B\n⚙️ Utilities", value="\u200B", inline=False) # Section Title
    embed.add_field(name=f"{get_cmd_mention('syncnicknames')}  · Sync HC nicknames to stored IGNs.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('wither')}  · Temporarily remove user roles.", value="\u200B", inline=False)
    embed.add_field(name=f"{get_cmd_mention('nerdhelp')}  · Shows this help message.", value="\u200B", inline=False)

    # --- Footer and Thumbnail ---
    embed.set_footer(text="Bot by TheNerd | sweet_honey")
    if bot.user and bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)

    # --- Send Response ---
    try:
        await interaction.response.send_message(embed=embed, ephemeral=False) # Keep it public
    except Exception as e:
        print(f"Error sending nerdhelp response: {e}")
        await log_error(guild, "Failed to send nerdhelp response", error=e, interaction=interaction)
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
