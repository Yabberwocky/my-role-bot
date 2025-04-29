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
from postgrest import APIError # Import for specific error handling
import traceback
import math # For pagination calculation

# --- Configuration ---
# Load environment variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Define Role and Channel IDs
REMOVE_ROLE_ID = 1360176495947022447 # Unverified role ID
ADD_ROLE_ID_VERIFY = 1248708073019805717 # Verified role ID
ADD_ROLE_ID_HC = 1230235110415274004 # [HC1] role ID

# Allowed Channel IDs for /hcmembers command
ALLOWED_CHANNEL_IDS = {1354431395140731165, 1330664430148780102, 1248710731407560835}

# Channel ID for the HC member list message
HC_MEMBER_LIST_CHANNEL_ID = 1354431395140731165
HC_LIST_EMBED_TITLE = "**\[HC1\] Guild Members**" # Use to find the message

# Wither command specific IDs
ALLOWED_WITHER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692}
SELF_PROTECTED_ID = 1230848174218940416
BOT_ID = 1365572437185400893
MAX_WITHER_SECONDS = 600 # 10 minutes

# Log Channel IDs
INFO_LOG_CHANNEL_ID = 1317943895606165579
ERROR_LOG_CHANNEL_ID = 1362988767367135453

# Pagination Settings
MEMBERS_PER_PAGE = 25 # Reduced from 50 for better embed readability

# --- Supabase Client ---
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase client created.")
    except Exception as e:
        print(f"CRITICAL: Failed to create Supabase client: {e}")
        supabase = None
else:
    print("CRITICAL: SUPABASE_URL or SUPABASE_KEY not set. Supabase functionality will be disabled.")
    supabase = None

# --- Discord Setup ---
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# --- Flask App for Keep Alive ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive!"
def run_flask():
    try: app.run(host='0.0.0.0', port=8080)
    except Exception as e: print(f"Flask server failed to start: {e}")
def keep_alive():
    t = threading.Thread(target=run_flask)
    t.start()
    print("Keep alive thread started.")

# --- Utility Functions ---

# Helper to run synchronous Supabase calls in executor
async def run_supabase_sync(func):
    """Runs a synchronous Supabase function using the bot's event loop executor."""
    try:
        # loop.run_in_executor defaults the executor to None, which is the thread pool executor.
        result = await bot.loop.run_in_executor(None, func)
        return result
    except APIError as api_err:
        # Catch specific Supabase errors here if needed for global handling,
        # but usually better to handle them in the calling function.
        print(f"Supabase API Error occurred in executor: {api_err}")
        raise # Re-raise the error to be caught by the calling context
    except Exception as e:
        print(f"Error running Supabase function in executor: {e}")
        raise # Re-raise other exceptions

# --- Logging Utility Functions ---
async def log_to_channel(channel_id: int, guild: discord.Guild, message: str = None, embed: discord.Embed = None):
    # (Same as before)
    if not guild:
        print(f"Log Error: Guild object missing for channel {channel_id}. Message: {message or 'Embed present'}")
        return
    log_channel = guild.get_channel(channel_id)
    if log_channel:
        try:
            # Ensure message length doesn't exceed limit even for embeds (description etc.)
            # Though send() should handle embed limits, be cautious with text length.
            if embed:
                await log_channel.send(embed=embed)
            elif message:
                if len(message) > 2000:
                    await log_channel.send(message[:1997] + "...")
                else:
                    await log_channel.send(message)
        except discord.Forbidden:
            print(f"Log Error: Bot lacks permission for channel ID {channel_id} ({guild.name}).")
        except discord.HTTPException as http_err:
            # Log Discord API errors more specifically
            print(f"Log Error: Discord API error sending to {channel_id} ({guild.name}): {http_err.status} {http_err.code} - {http_err.text}")
        except Exception as e:
            print(f"Log Error: Failed to send to channel ID {channel_id} ({guild.name}): {e}")
    else:
        print(f"Log Error: Channel ID {channel_id} not found in guild {guild.name}.")

async def log_info(guild: discord.Guild, message: str, embed: discord.Embed = None):
    # Use an embed for info logs for consistency
    if not embed:
        embed = discord.Embed(description=message, color=discord.Color.blue())
    await log_to_channel(INFO_LOG_CHANNEL_ID, guild, embed=embed)

async def log_error(guild: discord.Guild, message: str, error: Exception = None, interaction: discord.Interaction = None, embed: discord.Embed = None):
    # Use embeds for errors
    if not embed:
        embed = discord.Embed(title="⚠️ Error / Warning", description=message, color=discord.Color.red())
        if interaction:
            context = f"Command: `/{interaction.command.name if interaction.command else 'N/A'}`"
            if interaction.guild: context += f" in #{interaction.channel.name}"
            context += f"\nUser: `{interaction.user}` ({interaction.user.id})"
            embed.add_field(name="Context", value=context, inline=False)
        if error:
            error_details = f"**Type:** `{type(error).__name__}`\n"
            error_details += f"**Message:** `{str(error)}`\n"
            # Limit traceback length for embed field
            tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__, limit=5))
            if len(tb_str) > 1000: tb_str = tb_str[:1000] + "..."
            error_details += f"**Traceback:**\n```py\n{tb_str}\n```"
            embed.add_field(name="Error Details", value=error_details, inline=False)
            # Still print full traceback to console
            print(f"--- ERROR TRACEBACK ---\nGuild: {guild.id if guild else 'N/A'}\nContext: {message}\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}\n--- END TRACEBACK ---")

    await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, embed=embed)


# --- Embed Pagination View ---
class HCPagesView(View):
    def __init__(self, data: list, total_members: int, timeout=180.0):
        super().__init__(timeout=timeout)
        self.data = data # List of (discord.Member, ingame_name_str) tuples
        self.total_members = total_members
        self.current_page = 0
        self.total_pages = math.ceil(len(self.data) / MEMBERS_PER_PAGE)

        # Initial button state
        self.update_buttons()

    def create_page_embed(self) -> discord.Embed:
        """Creates the embed for the current page."""
        start_index = self.current_page * MEMBERS_PER_PAGE
        end_index = start_index + MEMBERS_PER_PAGE
        page_data = self.data[start_index:end_index]

        embed = discord.Embed(
            title=HC_LIST_EMBED_TITLE,
            color=discord.Color.teal()
        )

        description_lines = []
        current_index = start_index + 1
        for member, ingame_name in page_data:
            # Ensure names don't break formatting
            safe_member_name = discord.utils.escape_markdown(member.name)
            safe_ingame_name = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
            description_lines.append(f"{current_index}. {safe_member_name} ➔ {safe_ingame_name}")
            current_index += 1

        if not description_lines:
            embed.description = "No members found for this page." # Should not happen if data exists
        else:
            embed.description = "\n".join(description_lines)

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} | Total HC Members: {self.total_members}")
        return embed

    def update_buttons(self):
        """Disables/Enables buttons based on current page."""
        self.children[0].disabled = self.current_page == 0 # Previous button
        self.children[1].disabled = self.current_page >= self.total_pages - 1 # Next button

    @button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="hc_prev")
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_page_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Should be disabled, but handle anyway
            await interaction.response.defer()

    @button(label="Next", style=discord.ButtonStyle.blurple, custom_id="hc_next")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_page_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Should be disabled, but handle anyway
            await interaction.response.defer()

    async def on_timeout(self):
        # Optional: Disable buttons on timeout
        for item in self.children:
            item.disabled = True
        # Need the original message to edit it on timeout
        # This requires passing the message reference or fetching it.
        # Simpler: just let it time out naturally. The buttons will fail if clicked later.


# --- Core HC List Logic ---

async def fetch_hc_member_data(guild: discord.Guild) -> tuple[list[tuple[discord.Member, str]], int]:
    """Fetches HC members and their IGNs. Returns (list_of_tuples, total_hc_members_count)."""
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"[fetch_hc_member_data] Error: [HC1] role ({ADD_ROLE_ID_HC}) not found.")
        return [], 0

    # Get members with the role first
    members_with_role_unsorted = [m for m in guild.members if hc_role in m.roles]
    total_hc_members_count = len(members_with_role_unsorted)

    # Sort members by name (case-insensitive)
    members_with_role = sorted(members_with_role_unsorted, key=lambda m: m.display_name.lower())


    member_data_tuples = [] # Store as (member_object, ingame_name_str)
    member_ids = [str(m.id) for m in members_with_role]
    ingame_names = {} # Map discord_id (str) -> ingame_name (str)

    if supabase and member_ids:
        try:
            # Fetch all names in one query using run_in_executor
            response = await run_supabase_sync(
                lambda: supabase.table("hc_members").select("discord_id, ingame_name").in_("discord_id", member_ids).execute()
            )

            if response and response.data:
                for record in response.data:
                    ingame_names[record['discord_id']] = record.get("ingame_name", "Unknown")
            else:
                 # Log if Supabase returned no data for existing members?
                 await log_info(guild, f"[fetch_hc_member_data] Supabase returned no IGN data for {len(member_ids)} members requested.")


        except Exception as e:
            await log_error(guild, f"[fetch_hc_member_data] Error fetching bulk ingame_names from Supabase.", error=e)
            # Mark all as error fetching if bulk fails
            for member_id in member_ids:
                ingame_names[member_id] = "Error Fetching"

    # Combine member objects with fetched names
    for member in members_with_role:
        ingame_name = ingame_names.get(str(member.id), "Unknown") # Default if not found or error
        member_data_tuples.append((member, ingame_name))

    return member_data_tuples, total_hc_members_count


async def update_hc_member_list(guild: discord.Guild):
    """Fetches data and updates the paginated embed list message."""
    channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not channel:
        await log_error(guild, f"[update_hc_member_list] Error: Target Channel ({HC_MEMBER_LIST_CHANNEL_ID}) not found.")
        return

    try:
        member_data, total_count = await fetch_hc_member_data(guild)

        if not member_data and total_count == 0: # Handle case where role exists but no members have it
            list_text = f"{HC_LIST_EMBED_TITLE}\nNo members currently have the \[HC1\] role."
            embed_to_send = discord.Embed(description=list_text, color=discord.Color.orange())
            view_to_send = None # No pages needed
        elif not member_data and total_count > 0: # Error fetching data case
             list_text = f"{HC_LIST_EMBED_TITLE}\nError fetching member data or IGNs."
             embed_to_send = discord.Embed(description=list_text, color=discord.Color.red())
             view_to_send = None
        else:
            # Create the initial view and embed
            view_to_send = HCPagesView(member_data, total_count)
            embed_to_send = view_to_send.create_page_embed() # Gets page 0

        # --- Find and Edit or Send New ---
        edited = False
        try:
            async for message in channel.history(limit=50):
                if message.author == guild.me and message.embeds:
                    # Check if the first embed's title matches our expected title
                    if message.embeds[0].title == HC_LIST_EMBED_TITLE:
                        try:
                            await message.edit(embed=embed_to_send, view=view_to_send)
                            await log_info(guild, "[update_hc_member_list] Edited existing list message.")
                            edited = True
                            break # Found and edited
                        except discord.NotFound:
                            await log_error(guild, "[update_hc_member_list] Message to edit was deleted.")
                            edited = False; break # Treat as not found
                        except discord.Forbidden:
                             await log_error(guild, f"[update_hc_member_list] Error: Bot lacks permissions to edit messages in {channel.name}.")
                             edited = False; break # Fall through
                        except discord.HTTPException as http_err:
                             await log_error(guild, f"[update_hc_member_list] Error editing message (HTTP {http_err.status}).", error=http_err)
                             edited = False; break # Fall through
                        except Exception as e:
                             await log_error(guild, f"[update_hc_member_list] Error editing message.", error=e)
                             edited = False; break # Fall through
            # End of history search loop

        except discord.Forbidden:
             await log_error(guild, f"[update_hc_member_list] Error: Bot lacks permissions to read message history in {channel.name}.")
             # Fall through to sending a new message if possible

        if not edited:
            # Send a new message if not found or editing failed
            try:
                await channel.send(embed=embed_to_send, view=view_to_send)
                await log_info(guild, "[update_hc_member_list] Sent new list message.")
            except discord.Forbidden:
                await log_error(guild, f"[update_hc_member_list] Error: Bot lacks permissions to send messages in {channel.name}.")
            except discord.HTTPException as http_err:
                await log_error(guild, f"[update_hc_member_list] Error sending new message (HTTP {http_err.status}).", error=http_err)
            except Exception as e:
                await log_error(guild, f"[update_hc_member_list] Error sending new message.", error=e)

    except Exception as e:
         await log_error(guild, f"[update_hc_member_list] Unexpected error during update process.", error=e)


# --- Discord Events ---
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} command(s).")
        for guild in bot.guilds:
            await log_info(guild, f"✅ Bot Ready & Commands Synced ({len(synced)} commands).")
            # Update list on startup for each guild
            await update_hc_member_list(guild)
            await asyncio.sleep(1) # Avoid rate limits if many guilds
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        # Attempt to log startup error
        try:
            # Use the first guild found for logging if multiple exist
            await log_error(bot.guilds[0], "Bot failed to sync commands on startup.", error=e)
        except Exception as log_e:
            print(f"Could not log sync failure to Discord: {log_e}")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # (Same as before, but will call the updated update_hc_member_list)
    guild = after.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role: return # Error logged in fetch_hc_member_data if needed

    before_has_role = hc_role in before.roles
    after_has_role = hc_role in after.roles

    if before_has_role != after_has_role:
        action = "added to" if after_has_role else "removed from"
        log_embed = discord.Embed(
            description=f"HC role `{hc_role.name}` {action} user `{after.name}` ({after.id}). Triggering list update.",
            color=discord.Color.purple()
        )
        await log_info(guild, "", embed=log_embed)
        await update_hc_member_list(guild)

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # (Largely the same, but uses log_error which now creates embeds)
    error_message = "❌ An unexpected error occurred."
    log_title = f"App Command Error: /{interaction.command.name if interaction.command else 'N/A'}"
    guild = interaction.guild # May be None for DMs, handle gracefully

    if not guild: # Basic handling if interaction is not in a guild
         print(f"App command error outside of guild: {error}")
         if not interaction.response.is_done():
             try: await interaction.response.send_message("An error occurred.", ephemeral=True)
             except: pass # Ignore if sending fails
         return

    log_description = "An unhandled error occurred."
    log_error_obj = error # Default to passing the original error

    if isinstance(error, app_commands.MissingPermissions):
        missing_perms = ", ".join(error.missing_permissions)
        error_message = f"❌ You lack permissions: `{missing_perms}`"
        log_description = f"User `{interaction.user}` lacked permissions ({missing_perms})."
        log_error_obj = None # Don't log traceback for permission errors
    elif isinstance(error, app_commands.CheckFailure):
         error_message = "❌ You failed a required check."
         log_description = f"User `{interaction.user}` failed checks."
         log_error_obj = None
    elif isinstance(error, app_commands.CommandNotFound):
         # Should generally not happen, handled by Discord mostly
         print(f"Command not found: {interaction.command.name if interaction.command else 'N/A'}")
         return # Don't log or respond
    elif isinstance(error, app_commands.CommandInvokeError):
        original_error = error.original
        error_message = f"❌ Error executing command: `{type(original_error).__name__}`"
        log_description = f"Error invoking command logic."
        log_error_obj = original_error # Log the underlying error
    else:
        error_message = "❌ An unknown error occurred."
        log_description = f"Unhandled app command error type: `{type(error).__name__}`"
        log_error_obj = error

    # Log the error using the error logging channel
    await log_error(guild, log_description, error=log_error_obj, interaction=interaction)

    # Send feedback to the user
    if not interaction.response.is_done():
        try: await interaction.response.send_message(error_message, ephemeral=True)
        except Exception: pass # Ignore response errors
    else:
        try: await interaction.followup.send(error_message, ephemeral=True)
        except Exception: pass # Ignore followup errors


# --- Modals ---
class BulkUpdateModal(Modal, title="Bulk Update"):
    data = TextInput(label="Paste list (Format: DiscordName ➔ InGameName)", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.guild

        if not supabase:
            embed = discord.Embed(description="❌ Supabase is not configured.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            await log_error(guild, "Bulk update: Supabase not configured.", interaction=interaction)
            return

        success_count, fail_count, not_found_count = 0, 0, 0
        results = [] # Store tuples of (status, message)

        lines = self.data.value.strip().splitlines()
        if not lines:
            embed = discord.Embed(description="⚠️ No data provided.", color=discord.Color.orange())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        guild_members = {m.name.lower(): m for m in guild.members}

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if "➔" not in line:
                if line: results.append(('fail', f"L{i}: ⚠️ Invalid format: `{line}`"))
                continue
            try:
                username, ingame_name = map(str.strip, line.split("➔", 1))
                if not username or not ingame_name:
                    results.append(('fail', f"L{i}: ⚠️ Missing name: `{line}`"))
                    continue
            except ValueError:
                 results.append(('fail', f"L{i}: ⚠️ Bad separator: `{line}`"))
                 continue

            member = guild_members.get(username.lower())
            if not member:
                fail_count += 1; not_found_count += 1
                results.append(('fail', f"L{i}: ❌ User `{username}` not found."))
                continue

            try:
                # Use run_in_executor for upsert with on_conflict
                await run_supabase_sync(
                    lambda: supabase.table("hc_members").upsert({
                        "discord_id": str(member.id),
                        "discord_name": member.name,
                        "ingame_name": ingame_name
                    }, on_conflict="discord_id").execute() # Specify conflict column
                )
                success_count += 1
                # results.append(('success', f"L{i}: ✅ Processed {member.name}")) # Too verbose for report

            except Exception as e:
                fail_count += 1
                results.append(('fail', f"L{i}: ❌ Failed {member.name}: `{type(e).__name__}`"))
                await log_error(guild, f"Bulk update Supabase error for {member.name} ({member.id})", error=e, interaction=interaction)

        # Build the result embed
        embed = discord.Embed(title="Bulk Update Results", color=discord.Color.blue())
        summary = (
            f"✅ Successfully Processed: {success_count}\n"
            f"❌ Failed: {fail_count}\n"
            f"   - User Not Found: {not_found_count}\n"
            f"   - Supabase/Other Errors: {fail_count - not_found_count}"
        )
        embed.description = summary

        error_details = "\n".join([r[1] for r in results if r[0] == 'fail'])
        if error_details:
            if len(error_details) > 1024: error_details = error_details[:1021] + "..."
            embed.add_field(name="Issues", value=error_details, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)
        log_embed = discord.Embed(
            description=f"Bulk update completed by `{interaction.user}`. Success: {success_count}, Failed: {fail_count}.",
            color=discord.Color.blue()
        )
        await log_info(guild, "", embed=log_embed)

        await update_hc_member_list(guild) # Update list after bulk changes

# --- Slash Commands (Embedified Responses) ---

# Helper for creating simple response embeds
def create_embed(description: str, color: discord.Color = discord.Color.blue(), title: str = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)

@tree.command(name="verify", description="Verify a user into Catercord.")
@app_commands.describe(user="The user to verify")
@app_commands.checks.has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    remove_role = guild.get_role(REMOVE_ROLE_ID)
    add_role_verify = guild.get_role(ADD_ROLE_ID_VERIFY)
    actions_taken = []
    log_messages = []

    if not remove_role: log_messages.append(f"Unverified role ({REMOVE_ROLE_ID}) not found.")
    if not add_role_verify: log_messages.append(f"Verified role ({ADD_ROLE_ID_VERIFY}) not found.")
    if log_messages:
        await log_error(guild, f"/verify setup issue: {'; '.join(log_messages)}", interaction=interaction)

    try:
        if remove_role and remove_role in user.roles:
            await user.remove_roles(remove_role); actions_taken.append(f"Removed `{remove_role.name}`")
        if add_role_verify and add_role_verify not in user.roles:
            await user.add_roles(add_role_verify); actions_taken.append(f"Added `{add_role_verify.name}`")

        if not actions_taken:
            if not remove_role and not add_role_verify:
                embed = create_embed("❌ Verification roles not found.", discord.Color.red())
            else:
                embed = create_embed(f"ℹ️ No role changes needed for **{user.display_name}**.", discord.Color.orange())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            log_msg = f"Verified `{user.display_name}` ({user.id}). Actions: {', '.join(actions_taken)}."
            await log_info(guild, f"User `{interaction.user}` triggered: {log_msg}")
            embed = create_embed(f"✅ Verified **{user.display_name}**!\n" + "\n".join(actions_taken), discord.Color.green())
            await interaction.response.send_message(embed=embed)

    except discord.Forbidden:
        await log_error(guild, "Bot lacks permissions for /verify.", interaction=interaction)
        embed = create_embed("❌ I don't have permission to manage roles.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Error during /verify for {user.display_name}", error=e, interaction=interaction)
        embed = create_embed("❌ An error occurred during verification.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="unverify", description="Revert a user to unverified status.")
@app_commands.describe(user="The user to unverify")
@app_commands.checks.has_permissions(manage_roles=True)
async def unverify(interaction: discord.Interaction, user: discord.Member):
    guild = interaction.guild
    remove_role = guild.get_role(ADD_ROLE_ID_VERIFY) # Verified
    add_role = guild.get_role(REMOVE_ROLE_ID)     # Unverified
    actions_taken = []
    log_messages = []

    if not remove_role: log_messages.append(f"Verified role ({ADD_ROLE_ID_VERIFY}) not found.")
    if not add_role: log_messages.append(f"Unverified role ({REMOVE_ROLE_ID}) not found.")
    if log_messages:
        await log_error(guild, f"/unverify setup issue: {'; '.join(log_messages)}", interaction=interaction)

    try:
        if remove_role and remove_role in user.roles:
            await user.remove_roles(remove_role); actions_taken.append(f"Removed `{remove_role.name}`")
        if add_role and add_role not in user.roles:
            await user.add_roles(add_role); actions_taken.append(f"Added `{add_role.name}`")

        if not actions_taken:
            if not remove_role and not add_role:
                embed = create_embed("❌ Verification roles not found.", discord.Color.red())
            else:
                embed = create_embed(f"ℹ️ No role changes needed for **{user.display_name}**.", discord.Color.orange())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            log_msg = f"Unverified `{user.display_name}` ({user.id}). Actions: {', '.join(actions_taken)}."
            await log_info(guild, f"User `{interaction.user}` triggered: {log_msg}")
            embed = create_embed(f"✅ Unverified **{user.display_name}**!\n" + "\n".join(actions_taken), discord.Color.green())
            await interaction.response.send_message(embed=embed)

    except discord.Forbidden:
        await log_error(guild, "Bot lacks permissions for /unverify.", interaction=interaction)
        embed = create_embed("❌ I don't have permission to manage roles.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Error during /unverify for {user.display_name}", error=e, interaction=interaction)
        embed = create_embed("❌ An error occurred during unverification.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="hcverify", description="Verify a user into [HC1], store IGN, and set nickname.")
@app_commands.describe(user="The user to HC verify", ingame_name="Their Florr.io in-game name")
@app_commands.checks.has_permissions(manage_roles=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    await interaction.response.defer(thinking=True) # Defer as it involves DB + API calls
    guild = interaction.guild
    if not supabase:
        embed = create_embed("❌ Supabase is not configured.", discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_error(guild, "HC verify: Supabase not configured.", interaction=interaction)
        return

    remove_role = guild.get_role(REMOVE_ROLE_ID)
    add_role_verify = guild.get_role(ADD_ROLE_ID_VERIFY)
    add_role_hc = guild.get_role(ADD_ROLE_ID_HC)
    roles_to_add = []
    actions_log = [] # Detailed log
    response_details = [] # User-facing summary

    # Role checks
    setup_errors = []
    if not add_role_verify: setup_errors.append(f"Verified role ({ADD_ROLE_ID_VERIFY}) missing")
    if not add_role_hc: setup_errors.append(f"HC role ({ADD_ROLE_ID_HC}) missing")
    if setup_errors: await log_error(guild, f"/hcverify setup issue: {'; '.join(setup_errors)}", interaction=interaction)

    try:
        # 1. Handle Roles
        original_hc_status = add_role_hc and add_role_hc in user.roles
        if remove_role and remove_role in user.roles:
            await user.remove_roles(remove_role); actions_log.append("Removed Unverified")
        if add_role_verify and add_role_verify not in user.roles:
            roles_to_add.append(add_role_verify)
        if add_role_hc and add_role_hc not in user.roles:
            roles_to_add.append(add_role_hc)
        if roles_to_add:
            await user.add_roles(*roles_to_add)
            added_names = ', '.join([f"`{r.name}`" for r in roles_to_add])
            actions_log.append(f"Added roles: {added_names}")
            response_details.append(f"➕ Added Roles: {added_names}")

        # 2. Store/Update in Supabase
        supabase_updated = False
        try:
            await run_supabase_sync(
                lambda: supabase.table("hc_members").upsert({
                    "discord_id": str(user.id),
                    "discord_name": user.name,
                    "ingame_name": ingame_name
                }, on_conflict="discord_id").execute() # Specify conflict column
            )
            actions_log.append("Upserted Supabase IGN")
            response_details.append(f"💾 Set IGN: `{ingame_name}`")
            supabase_updated = True
        except Exception as e:
            await log_error(guild, f"Supabase upsert failed during /hcverify for {user.display_name}", error=e, interaction=interaction)
            actions_log.append("Supabase upsert FAILED")
            response_details.append("⚠️ Supabase update failed!")

        # 3. Attempt Nickname Change
        target_nick = ingame_name[:32] # Auto-truncate
        nickname_status_msg = ""
        if user.nick != target_nick:
            try:
                await user.edit(nick=target_nick)
                actions_log.append(f"Set nickname to '{target_nick}'")
                response_details.append(f"🏷️ Set Nickname: `{target_nick}`")
                if target_nick != ingame_name: nickname_status_msg = " (truncated)"
            except discord.Forbidden:
                actions_log.append("Nickname change FAILED (Forbidden)")
                response_details.append("⚠️ Failed to set nickname (Permissions)")
                nickname_status_msg = " (nickname failed)"
            except Exception as e:
                await log_error(guild, f"Nickname change failed during /hcverify for {user.display_name}", error=e, interaction=interaction)
                actions_log.append(f"Nickname change FAILED ({type(e).__name__})")
                response_details.append("⚠️ Failed to set nickname (Error)")
                nickname_status_msg = " (nickname failed)"
        else:
            actions_log.append("Nickname already correct")
            response_details.append("🏷️ Nickname already correct")

        # 4. Send Followup & Log
        log_msg = f"User `{interaction.user}` HC verified `{user.display_name}`. Actions: {'; '.join(actions_log)}."
        await log_info(guild, log_msg)

        embed = create_embed(
            title=f"✅ HC Verified: {user.display_name}{nickname_status_msg}",
            description="\n".join(response_details) if response_details else "No actions performed.",
            color=discord.Color.green() if supabase_updated else discord.Color.orange() # Orange if DB failed
        )
        await interaction.followup.send(embed=embed, ephemeral=False) # Public response

        # 5. Update list if needed (event handles role add, manually call otherwise)
        # Call if HC role was added OR if they already had HC role but IGN/Nick might change
        newly_added_hc = add_role_hc and add_role_hc in roles_to_add
        if newly_added_hc or (original_hc_status and supabase_updated):
            await update_hc_member_list(guild)

    except discord.Forbidden as forbidden_err:
        await log_error(guild, "Bot lacks role permissions for /hcverify.", error=forbidden_err, interaction=interaction)
        embed = create_embed("❌ I lack permissions to manage roles.", discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Unexpected error during /hcverify for {user.display_name}", error=e, interaction=interaction)
        embed = create_embed("❌ An unexpected error occurred.", discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="unhcverify", description="Remove [HC1] role and reset nickname for a user.")
@app_commands.describe(user="The user to remove from HC.")
@app_commands.checks.has_permissions(manage_roles=True)
async def unhcverify(interaction: discord.Interaction, user: discord.Member):
    # This is usually fast, defer not strictly necessary unless server is huge/slow
    # await interaction.response.defer()
    guild = interaction.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    actions_log = []
    response_details = []

    if not hc_role:
        await log_error(guild, f"/unhcverify: HC role ({ADD_ROLE_ID_HC}) not found.", interaction=interaction)
        embed = create_embed("❌ HC Role not found.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        # 1. Remove HC Role
        if hc_role in user.roles:
            await user.remove_roles(hc_role)
            actions_log.append(f"Removed HC role ({hc_role.name})")
            response_details.append(f"➖ Removed Role: `{hc_role.name}`")
        else:
            embed = create_embed(f"ℹ️ **{user.display_name}** does not have the `{hc_role.name}` role.", discord.Color.orange())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return # Nothing more to do

        # 2. Reset Nickname
        nickname_status_msg = ""
        if user.nick is not None:
            try:
                await user.edit(nick=None)
                actions_log.append("Reset nickname")
                response_details.append("🏷️ Reset Nickname")
            except discord.Forbidden:
                actions_log.append("Nickname reset FAILED (Forbidden)")
                response_details.append("⚠️ Failed to reset nickname (Permissions)")
                nickname_status_msg = " (nickname failed)"
            except Exception as e:
                await log_error(guild, f"Nickname reset failed during /unhcverify for {user.display_name}", error=e, interaction=interaction)
                actions_log.append(f"Nickname reset FAILED ({type(e).__name__})")
                response_details.append("⚠️ Failed to reset nickname (Error)")
                nickname_status_msg = " (nickname failed)"
        else:
            actions_log.append("No nickname to reset")
            response_details.append("🏷️ No nickname to reset")

        # 3. Send Response & Log
        log_msg = f"User `{interaction.user}` un-HC-verified `{user.display_name}`. Actions: {'; '.join(actions_log)}."
        await log_info(guild, log_msg)

        embed = create_embed(
            title=f"✅ Un-HC-Verified: {user.display_name}{nickname_status_msg}",
            description="\n".join(response_details),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed) # Public response

        # 4. Update list (handled by on_member_update event)

    except discord.Forbidden as forbidden_err:
        await log_error(guild, "Bot lacks role permissions for /unhcverify.", error=forbidden_err, interaction=interaction)
        embed = create_embed("❌ I lack permissions to manage roles.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Unexpected error during /unhcverify for {user.display_name}", error=e, interaction=interaction)
        embed = create_embed("❌ An unexpected error occurred.", discord.Color.red())
        # Check if response already sent
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else: # Should not happen often here
            await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="hcmembers", description="List all [HC1] members with their in-game names.")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        embed = create_embed("❌ This command can only be used in specific channels.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_info(guild, f"User `{interaction.user}` tried /hcmembers in disallowed channel #{interaction.channel.name}.")
        return

    await interaction.response.defer(thinking=True) # List building can take time

    if not supabase:
        embed = create_embed("❌ Supabase is not configured.", discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_error(guild, "/hcmembers: Supabase not configured.", interaction=interaction)
        return

    try:
        member_data, total_count = await fetch_hc_member_data(guild)

        if not member_data and total_count == 0:
            embed = create_embed(f"{HC_LIST_EMBED_TITLE}\nNo members found with the \[HC1\] role.", discord.Color.orange())
            await interaction.followup.send(embed=embed)
        elif not member_data and total_count > 0: # Error case
             embed = create_embed(f"{HC_LIST_EMBED_TITLE}\nError fetching member data or IGNs.", discord.Color.red())
             await interaction.followup.send(embed=embed)
        else:
            # Send initial page with view
            view = HCPagesView(member_data, total_count)
            embed = view.create_page_embed()
            await interaction.followup.send(embed=embed, view=view)
            await log_info(guild, f"/hcmembers generated list in #{interaction.channel.name}.")

    except Exception as e:
        await log_error(guild, "[hcmembers] Error building/sending list.", error=e, interaction=interaction)
        embed = create_embed("❌ An error occurred fetching the member list.", discord.Color.red())
        # Check if followup possible before sending
        if not interaction.response.is_done(): # Should always be done due to defer
             await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="bulkupdate", description="Bulk update user in-game names via modal.")
@app_commands.checks.has_permissions(manage_roles=True)
async def bulkupdate(interaction: discord.Interaction):
    try:
        await interaction.response.send_modal(BulkUpdateModal())
        await log_info(interaction.guild, f"Opened bulk update modal for `{interaction.user}`.")
    except Exception as e:
        await log_error(interaction.guild, "Error opening bulk update modal.", error=e, interaction=interaction)
        if not interaction.response.is_done():
             embed = create_embed("❌ Error opening modal.", discord.Color.red())
             await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="refresh", description="Refresh the [HC1] member list manually.")
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    guild = interaction.guild

    if not supabase: # Check Supabase early
        embed = create_embed("❌ Supabase is not configured.", discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_error(guild, "/refresh: Supabase not configured.", interaction=interaction)
        return

    try:
        await update_hc_member_list(guild)
        embed = create_embed("✅ Refreshed the HC member list!", discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_info(guild, f"Manually refreshed HC list via /refresh by `{interaction.user}`.")
    except Exception as e:
        await log_error(guild, "Error during manual /refresh.", error=e, interaction=interaction)
        embed = create_embed("❌ Error refreshing the list.", discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="syncnicknames", description="Sync all HC members' nicknames with their stored IGN.")
@app_commands.checks.has_permissions(manage_roles=True)
async def syncnicknames(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    guild = interaction.guild

    if not supabase:
        embed = create_embed("❌ Supabase is not configured.", discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_error(guild, "/syncnicknames: Supabase not configured.", interaction=interaction)
        return

    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"/syncnicknames: HC role ({ADD_ROLE_ID_HC}) not found.", interaction=interaction)
        embed = create_embed("❌ HC Role not found.", discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    await log_info(guild, f"Starting nickname sync triggered by `{interaction.user}`.")
    await interaction.edit_original_response(content="🔄 Fetching HC members and IGN data...")

    ign_data = {}
    try:
        response = await run_supabase_sync(
             lambda: supabase.table("hc_members").select("discord_id, ingame_name").execute()
        )
        if response and response.data:
            ign_data = {item['discord_id']: item['ingame_name'] for item in response.data if item.get('ingame_name')}
        await log_info(guild, f"Fetched {len(ign_data)} records from Supabase for sync.")
    except Exception as e:
         await log_error(guild, "Failed to fetch Supabase data for /syncnicknames.", error=e, interaction=interaction)
         await interaction.edit_original_response(content="❌ Failed to fetch data from Supabase. Aborting.")
         return

    counts = {'success': 0, 'skipped': 0, 'no_ign': 0, 'perm_error': 0, 'other_error': 0, 'processed': 0}
    hc_members_in_guild = [m for m in guild.members if hc_role in m.roles]
    total_hc_members = len(hc_members_in_guild)

    await interaction.edit_original_response(content=f"🔄 Syncing nicknames for {total_hc_members} members...")

    for i, member in enumerate(hc_members_in_guild):
        counts['processed'] += 1
        if i % 25 == 0 and i > 0:
             await interaction.edit_original_response(content=f"🔄 Syncing nicknames... ({i}/{total_hc_members})")

        member_id_str = str(member.id)
        if member_id_str not in ign_data:
            counts['no_ign'] += 1; continue

        ingame_name = ign_data[member_id_str]
        target_nick = ingame_name[:32]

        if member.nick == target_nick:
            counts['skipped'] += 1; continue

        try:
            await member.edit(nick=target_nick); counts['success'] += 1
        except discord.Forbidden: counts['perm_error'] += 1
        except Exception as e:
            counts['other_error'] += 1
            await log_error(guild, f"SyncNick: Error updating {member.name}", error=e, interaction=interaction) # Log specific error

    # Final Report Embed
    embed = discord.Embed(title="Nickname Sync Complete!", color=discord.Color.blue())
    summary = (
        f"Processed Members: {counts['processed']}\n"
        f"✅ Updated: {counts['success']}\n"
        f"ℹ️ Already Correct: {counts['skipped']}\n"
        f"⚠️ Missing IGN in DB: {counts['no_ign']}\n"
        f"❌ Permission Errors: {counts['perm_error']}\n"
        f"❌ Other Errors: {counts['other_error']}"
    )
    embed.description = summary
    await interaction.edit_original_response(content=None, embed=embed) # Remove content text

    log_embed = discord.Embed(title="Nickname Sync Finished", description=summary, color=discord.Color.blue())
    log_embed.set_footer(text=f"Triggered by {interaction.user}")
    await log_info(guild, "", embed=log_embed)


@tree.command(name="wither", description="Temporarily remove all roles from a user.")
@app_commands.describe(user="The user to wither", time="Time (in minutes, defaults to 2, max 10)")
async def wither(interaction: discord.Interaction, user: discord.Member, time: float = 2.0):
    guild = interaction.guild
    interaction_user = interaction.user

    async def wither_fail_log(reason: str, error: Exception = None):
         await log_error(guild, f"Wither Failure: {reason}", error=error, interaction=interaction)

    # Use embeds for user responses
    if interaction_user.id not in ALLOWED_WITHER_IDS:
        await wither_fail_log(f"User `{interaction_user}` lacks permission.")
        await interaction.response.send_message(embed=create_embed("❌ You lack the divine permission.", discord.Color.red()), ephemeral=True)
        return
    if user.id == interaction_user.id:
        await wither_fail_log("User attempted self-wither.")
        await interaction.response.send_message(embed=create_embed("🤨 Why wither yourself?", discord.Color.orange()), ephemeral=True)
        return
    # Add other protected user checks similarly...

    time_seconds = int(time * 60)
    if time <= 0 or time_seconds > MAX_WITHER_SECONDS:
        await wither_fail_log(f"Invalid time: {time} mins.")
        await interaction.response.send_message(embed=create_embed(f"❌ Time must be > 0 and <= {MAX_WITHER_SECONDS/60:.0f} mins.", discord.Color.red()), ephemeral=True)
        return
    if guild.me.top_role <= user.top_role:
        await wither_fail_log(f"Bot role not high enough for {user.name}.")
        await interaction.response.send_message(embed=create_embed("❌ I can't wither someone mightier than myself!", discord.Color.red()), ephemeral=True)
        return

    original_roles = [role for role in user.roles if role != guild.default_role]
    if not original_roles:
        await wither_fail_log(f"{user.name} has no roles.")
        await interaction.response.send_message(embed=create_embed(f"❌ {user.display_name} has no roles to wither.", discord.Color.red()), ephemeral=True)
        return

    try:
        await user.edit(roles=[])
        role_names = ', '.join([f"`{r.name}`" for r in original_roles])
        embed = create_embed(
            title="🌪️ Wither Cast! 🌪️",
            description=f"{user.mention} has been withered by {interaction_user.mention} for **{time:.2f} minutes**!\n\nRoles removed: {role_names}",
            color=discord.Color.dark_purple()
        )
        await interaction.response.send_message(embed=embed)
        await log_info(guild, f"User `{user.name}` withered by `{interaction_user.name}` for {time:.2f} mins.")

        await asyncio.sleep(time_seconds)

        try:
             member_after_wait = await guild.fetch_member(user.id)
             if member_after_wait:
                 await member_after_wait.edit(roles=original_roles)
                 embed = create_embed(f"✨ {user.mention} has recovered from withering!", color=discord.Color.gold())
                 await interaction.followup.send(embed=embed)
                 await log_info(guild, f"Restored roles for `{user.name}`.")
             else: await log_info(guild, f"User `{user.name}` left before roles restored.")
        except discord.NotFound: await log_info(guild, f"User `{user.name}` not found for role restore.")
        except discord.Forbidden as fe:
            await wither_fail_log("Bot lacked permissions to restore roles.", error=fe)
            await interaction.followup.send(embed=create_embed(f"⚠️ Failed to restore roles to {user.mention} (Permissions).", discord.Color.red()), ephemeral=True)
        except Exception as e:
            await wither_fail_log("Failed to restore roles.", error=e)
            await interaction.followup.send(embed=create_embed(f"⚠️ Error restoring roles to {user.mention}.", discord.Color.red()), ephemeral=True)

    except discord.Forbidden as fe:
        await wither_fail_log("Bot lacked permissions to remove roles.", error=fe)
        if not interaction.response.is_done(): await interaction.response.send_message(embed=create_embed("❌ I lack permission to remove roles!", discord.Color.red()), ephemeral=True)
        else: await interaction.followup.send(embed=create_embed("❌ Failed removing roles (Permissions).", discord.Color.red()), ephemeral=True)
    except Exception as e:
        await wither_fail_log("Unexpected wither error.", error=e)
        if not interaction.response.is_done(): await interaction.response.send_message(embed=create_embed("❌ Unexpected wither error.", discord.Color.red()), ephemeral=True)
        else: await interaction.followup.send(embed=create_embed("❌ Unexpected wither error.", discord.Color.red()), ephemeral=True)


@tree.command(name="nerdhelp", description="Show Catercord slash commands help menu.")
async def nerdhelp(interaction: discord.Interaction):
    # (Help command remains largely the same, using embeds already)
    guild = interaction.guild
    embed = discord.Embed( title="🤓 Catercord Command List", description="Available slash commands:", color=discord.Color.blurple() )
    verify_role = guild.get_role(ADD_ROLE_ID_VERIFY)
    unverify_role = guild.get_role(REMOVE_ROLE_ID)
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    perm_note = "(Requires Manage Roles)"

    embed.add_field(name="/verify <user>", value=f"Verify member (Adds `{verify_role.name if verify_role else 'Verified'}`, removes `{unverify_role.name if unverify_role else 'Unverified'}`). {perm_note}", inline=False)
    embed.add_field(name="/unverify <user>", value=f"Unverify member (Adds `{unverify_role.name if unverify_role else 'Unverified'}`, removes `{verify_role.name if verify_role else 'Verified'}`). {perm_note}", inline=False)
    embed.add_field(name="/hcverify <user> <ingame_name>", value=f"Verify into HC (Adds `{hc_role.name if hc_role else 'HC'}`), stores IGN, sets nickname. {perm_note}", inline=False)
    embed.add_field(name="/unhcverify <user>", value=f"Remove HC status (Removes `{hc_role.name if hc_role else 'HC'}`, resets nickname). {perm_note}", inline=False)
    embed.add_field(name="/hcmembers", value=f"Paginated list of `{hc_role.name if hc_role else 'HC'}` members & IGNs. (Allowed channels only)", inline=False)
    embed.add_field(name="/bulkupdate", value=f"Bulk update/add IGNs via modal. {perm_note}", inline=False)
    embed.add_field(name="/refresh", value=f"Manually refresh the HC member list message. {perm_note}", inline=False)
    embed.add_field(name="/syncnicknames", value=f"Sync nicknames for all `{hc_role.name if hc_role else 'HC'}` members from stored IGNs. {perm_note}", inline=False)
    embed.add_field(name="/wither <user> [time]", value=f"Temporarily remove roles (Max {MAX_WITHER_SECONDS/60:.0f} mins). (Special permission needed)", inline=False)
    embed.add_field(name="/nerdhelp", value="Show this help menu.", inline=False)

    embed.set_footer(text="Use commands responsibly, nerd.")
    if interaction.client.user.display_avatar:
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True) # Make help ephemeral


# --- Bot Startup ---
if __name__ == "__main__":
    if TOKEN:
        if supabase:
            keep_alive() # Start Flask keep-alive thread only if essential config is present
            try:
                print("Starting Bot...")
                bot.run(TOKEN)
            except Exception as e:
                 print(f"CRITICAL: Bot failed to run: {e}")
                 # Maybe try a webhook or other notification here if bot start fails
        else:
            print("CRITICAL: Supabase client creation failed. Bot will not start.")
    else:
        print("CRITICAL: DISCORD_BOT_TOKEN not set. Bot will not start.")
