# -*- coding: utf-8 -*-

import os
import threading
import asyncio
import logging
from typing import Set, Final # Added typing imports

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput
from flask import Flask
from supabase import create_client, Client, SupabaseError # Added SupabaseError for potential specific handling

# --- Constants ---

# Environment Variables (ensure these are set in your Render environment)
TOKEN: Final[str | None] = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL: Final[str | None] = os.getenv("SUPABASE_URL")
SUPABASE_KEY: Final[str | None] = os.getenv("SUPABASE_KEY")

# Bot Configuration
BOT_COMMAND_PREFIX: Final[str] = "!" # Although using slash commands primarily, a prefix is needed for commands.Bot
BOT_OWNER_ID: Final[int] = 1230848174218940416 # Your Discord User ID
BOT_ID: Final[int] = 1365572437185400893 # The Bot's User ID

# Role IDs (Replace with your actual Role IDs)
REMOVE_ROLE_ID: Final[int] = 1360176495947022447 # Role removed upon verification (e.g., "Unverified")
ADD_ROLE_ID_VERIFY: Final[int] = 1248708073019805717 # Standard verified member role
ADD_ROLE_ID_HC: Final[int] = 1230235110415274004 # [HC1] Guild Member role

# Channel IDs (Replace with your actual Channel IDs)
# Channels where /hcmembers command is allowed
ALLOWED_HCMEMBERS_CHANNEL_IDS: Set[int] = {
    1354431395140731165,
    1330664430148780102,
    1248710731407560835,
}
# Channel where the bot posts/updates the HC member list
HC_MEMBER_LIST_CHANNEL_ID: Final[int] = 1354431395140731165
# Channel for logging wither command attempts/failures
WITHER_LOG_CHANNEL_ID: Final[int] = 1362988767367135453

# Supabase Configuration
SUPABASE_TABLE_HC_MEMBERS: Final[str] = "hc_members"
# Common Supabase error substrings indicating a duplicate primary key violation
DUPLICATE_KEY_ERRORS: Final[tuple[str, ...]] = ("duplicate key value", f'"{SUPABASE_TABLE_HC_MEMBERS}_discord_id_key"')

# Wither Command Configuration
# User IDs allowed to use the /wither command (e.g., Server Owners, Bot Owner)
WITHER_COMMAND_ALLOWED_USER_IDS: Set[int] = {
    BOT_OWNER_ID, # You
    879320982299484240, # Example other owner ID
    955448447790620692, # Example other owner ID
}
WITHER_MAX_DURATION_MINUTES: Final[float] = 10.0

# --- Logging Setup ---
# Basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('discord') # Get the discord logger
logger.setLevel(logging.INFO) # Set discord logger level
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Custom logger for the bot
bot_logger = logging.getLogger('CatercordBot')
bot_logger.setLevel(logging.INFO)
# You might want to add file handlers or stream handlers to bot_logger as well

# --- Supabase Client Initialization ---
if not SUPABASE_URL or not SUPABASE_KEY:
    bot_logger.critical("Supabase URL or Key environment variables not set. Exiting.")
    exit() # Exit if Supabase credentials aren't found

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bot_logger.info("Supabase client initialized.")

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.members = True  # Essential for accessing member data like roles and names
intents.message_content = True # If you plan to add prefix commands later

bot = commands.Bot(command_prefix=BOT_COMMAND_PREFIX, intents=intents)
tree = bot.tree # Command Tree for slash commands

# --- Flask App for Keep Alive (Render/Replit) ---
# This simple web server responds to HTTP requests, preventing Render/Replit from idling the bot.
app = Flask('')

@app.route('/')
def home():
    """Basic route to indicate the bot is running."""
    return "Catercord Bot is alive!"

def run_flask():
    """Runs the Flask app."""
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """Starts the Flask app in a separate thread."""
    bot_logger.info("Starting keep-alive Flask server.")
    thread = threading.Thread(target=run_flask)
    thread.daemon = True # Allow program to exit even if this thread is running
    thread.start()

# --- Helper Functions ---

def has_manage_roles_permission(interaction: discord.Interaction) -> bool:
    """Checks if the interacting user has the 'Manage Roles' permission."""
    return interaction.user.guild_permissions.manage_roles

async def get_role(guild: discord.Guild, role_id: int) -> discord.Role | None:
    """Safely gets a role by ID, returning None if not found."""
    role = guild.get_role(role_id)
    if not role:
        bot_logger.warning(f"Role with ID {role_id} not found in guild {guild.id}.")
    return role

async def log_wither_failure(guild: discord.Guild, reason: str, interaction_user: discord.User):
    """Logs failed wither attempts to the designated log channel."""
    log_channel = guild.get_channel(WITHER_LOG_CHANNEL_ID)
    if log_channel and isinstance(log_channel, discord.TextChannel): # Type check
        try:
            embed = discord.Embed(
                title="⚠️ Wither Attempt Failed",
                description=reason,
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Attempted by: {interaction_user} ({interaction_user.id})")
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            bot_logger.error(f"Missing permissions to send message in wither log channel {WITHER_LOG_CHANNEL_ID}")
        except Exception as e:
            bot_logger.error(f"Failed to log wither failure: {e}")
    elif not log_channel:
        bot_logger.warning(f"Wither log channel {WITHER_LOG_CHANNEL_ID} not found.")

# --- Core Bot Logic ---

async def build_hc_member_list(guild: discord.Guild) -> str:
    """
    Builds the formatted string list of [HC1] Guild Members and their in-game names.

    Args:
        guild: The discord Guild object.

    Returns:
        A formatted string containing the member list or an error message.
    """
    bot_logger.info(f"Building HC member list for guild {guild.id}...")
    hc_role = await get_role(guild, ADD_ROLE_ID_HC)
    if not hc_role:
        return "**Error:** [HC1] role not found. Please check `ADD_ROLE_ID_HC`."

    # Sort members alphabetically by Discord name (case-insensitive)
    hc_members = sorted(hc_role.members, key=lambda m: m.name.lower())

    if not hc_members:
        return f"No members currently have the {hc_role.name} role."

    lines = [f"**[{hc_role.name}] Guild Members ({len(hc_members)}):**"]
    fetch_count = 0
    error_count = 0

    # --- Performance Note ---
    # Fetching each member's in-game name individually can be slow for large guilds.
    # A potential optimization is to fetch all relevant entries from Supabase at once
    # and store them in a dictionary for quick lookup.
    # Example: `response = supabase.table(...).select("discord_id, ingame_name").in_("discord_id", [str(m.id) for m in hc_members]).execute()`
    # Then create a map: `ign_map = {item['discord_id']: item['ingame_name'] for item in response.data}`
    # And look up: `ingame_name = ign_map.get(str(member.id), "Unknown")`
    # For now, the individual fetch approach is simpler.
    # ---

    for idx, member in enumerate(hc_members, 1):
        ingame_name = "Unknown" # Default value
        try:
            # Fetch the in-game name from Supabase for the current member
            response = supabase.table(SUPABASE_TABLE_HC_MEMBERS)\
                .select("ingame_name")\
                .eq("discord_id", str(member.id))\
                .maybe_single()\
                .execute()

            # Check if data was returned and extract the name
            if response and response.data:
                ingame_name = response.data.get("ingame_name", "Unknown") # Use .get for safety
                fetch_count += 1
            # No need for else, ingame_name defaults to "Unknown"

        except SupabaseError as se:
            bot_logger.error(f"[build_hc_member_list] Supabase error fetching IGN for {member.name} ({member.id}): {se}")
            error_count += 1
        except Exception as e:
            bot_logger.error(f"[build_hc_member_list] Unexpected error fetching IGN for {member.name} ({member.id}): {e}")
            error_count += 1

        # Format: 1. DiscordUsername ➔ InGameName
        lines.append(f"{idx}. {member.display_name} ➔ {ingame_name}")

    if error_count > 0:
        lines.append(f"\n*Note: Failed to fetch in-game names for {error_count} member(s).*")

    bot_logger.info(f"Finished building HC member list. Fetched {fetch_count} names, encountered {error_count} errors.")
    return "\n".join(lines)


async def update_hc_member_list(guild: discord.Guild):
    """
    Fetches the latest HC member list and updates the message in the designated channel.
    If no previous message exists, it sends a new one.

    Args:
        guild: The discord Guild object.
    """
    bot_logger.info(f"Attempting to update HC member list in channel {HC_MEMBER_LIST_CHANNEL_ID} for guild {guild.id}.")
    channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)

    if not channel:
        bot_logger.error(f"[update_hc_member_list] Channel ID {HC_MEMBER_LIST_CHANNEL_ID} not found in guild {guild.id}.")
        return
    if not isinstance(channel, discord.TextChannel): # Ensure it's a text channel
        bot_logger.error(f"[update_hc_member_list] Channel ID {HC_MEMBER_LIST_CHANNEL_ID} is not a TextChannel.")
        return

    # Check bot permissions in the target channel
    if not channel.permissions_for(guild.me).send_messages or not channel.permissions_for(guild.me).read_message_history:
        bot_logger.error(f"Bot lacks Send Messages or Read History permissions in channel {channel.name} ({channel.id}).")
        return

    try:
        list_text = await build_hc_member_list(guild)

        # Try to find an existing message posted by the bot to edit
        message_to_edit = None
        async for message in channel.history(limit=50): # Look through recent messages
            # Check if the message is from the bot and starts with the expected header
            if message.author == guild.me and message.content.startswith("**["): # More robust check
                 # Found a potential candidate, assume it's the list message
                 message_to_edit = message
                 break # Stop searching once found

        if message_to_edit:
            try:
                # Check if content needs updating to avoid unnecessary edits
                if message_to_edit.content != list_text:
                    await message_to_edit.edit(content=list_text)
                    bot_logger.info(f"Edited existing HC member list in channel {channel.id}.")
                else:
                     bot_logger.info(f"HC member list content unchanged in channel {channel.id}. No edit needed.")
            except discord.Forbidden:
                 bot_logger.error(f"Missing permissions to edit message {message_to_edit.id} in channel {channel.id}.")
            except discord.NotFound:
                 bot_logger.warning(f"Message {message_to_edit.id} not found (possibly deleted?). Sending new list.")
                 await channel.send(list_text) # Send new if edit failed b/c message gone
            except Exception as e:
                bot_logger.error(f"[update_hc_member_list] Error editing message {message_to_edit.id}: {e}")
        else:
            # No existing message found, send a new one
            try:
                await channel.send(list_text)
                bot_logger.info(f"Sent new HC member list to channel {channel.id}.")
            except discord.Forbidden:
                 bot_logger.error(f"Missing permissions to send message in channel {channel.id}.")
            except Exception as e:
                bot_logger.error(f"[update_hc_member_list] Error sending new message: {e}")

    except Exception as e:
        # Catch errors during list building or channel operations
        bot_logger.error(f"[update_hc_member_list] Unexpected error during update process: {e}")
        # Optionally send an error message to the channel if possible
        try:
            await channel.send("❌ An error occurred while trying to update the member list.")
        except Exception:
            pass # Ignore if sending the error message itself fails

# --- Modal Definitions ---

# Modal for the /bulkupdate command
class BulkUpdateModal(Modal, title="Bulk Update HC In-Game Names"):
    # Text input field spanning multiple lines (paragraph style)
    data = TextInput(
        label="Paste list (Format: DiscordName ➔ InGameName)",
        style=discord.TextStyle.paragraph,
        placeholder="Example:\nUser1 ➔ IGN_One\nAnotherUser ➔ FlorrPlayer2\n...",
        required=True,
        min_length=10, # Basic sanity check for input length
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Processes the submitted data from the modal."""
        # Defer response as processing might take time
        await interaction.response.defer(thinking=True, ephemeral=True) # Ephemeral thinking message

        success_count = 0
        fail_count = 0
        skip_count = 0
        errors = []
        processed_members: Set[int] = set() # Track processed members to avoid duplicate processing in one run

        # Split the input text into lines
        lines = self.data.value.splitlines()

        for line_num, line in enumerate(lines, 1):
            line = line.strip() # Remove leading/trailing whitespace
            if not line or "➔" not in line:
                # Skip empty lines or lines without the separator
                continue

            try:
                username, ingame_name = map(str.strip, line.split("➔", 1))
                if not username or not ingame_name:
                     fail_count += 1
                     errors.append(f"⚠️ Line {line_num}: Invalid format or empty name '{line}'. Skipped.")
                     continue

            except ValueError:
                # Handle cases where split doesn't yield exactly two parts
                fail_count += 1
                errors.append(f"⚠️ Line {line_num}: Invalid format '{line}'. Skipped.")
                continue

            # Find the member in the guild (case-insensitive)
            # Uses display_name first, falls back to name if needed.
            member = discord.utils.find(
                lambda m: m.display_name.lower() == username.lower() or m.name.lower() == username.lower(),
                interaction.guild.members
            )

            if not member:
                fail_count += 1
                errors.append(f"❌ Line {line_num}: Discord user '{username}' not found in this server.")
                continue

            if member.id in processed_members:
                 skip_count += 1
                 errors.append(f"⚠️ Line {line_num}: Member '{member.display_name}' already processed in this update. Skipped.")
                 continue

            # Attempt to upsert (insert or update) the data in Supabase
            try:
                # Upsert tries to insert, and if a conflict occurs (based on discord_id), it updates instead.
                supabase.table(SUPABASE_TABLE_HC_MEMBERS).upsert({
                    "discord_id": str(member.id),
                    "discord_name": member.name, # Store the canonical username
                    "ingame_name": ingame_name
                }, on_conflict="discord_id").execute() # Specify the conflict target column
                success_count += 1
                processed_members.add(member.id)
                # Optional: Log successful update here if needed
                # bot_logger.info(f"[Bulk Update] Upserted {member.name} ({member.id}) with IGN {ingame_name}")

            except SupabaseError as se:
                 fail_count += 1
                 errors.append(f"❌ Line {line_num}: Supabase error for '{member.display_name}': {se}")
                 bot_logger.error(f"[Bulk Update] Supabase error for {member.name} ({member.id}): {se}")
            except Exception as e:
                fail_count += 1
                errors.append(f"❌ Line {line_num}: Failed to update '{member.display_name}': {e}")
                bot_logger.error(f"[Bulk Update] Error processing {member.name} ({member.id}): {e}")


        # Construct the result message
        result_message = (
            f"**Bulk Update Results:**\n"
            f"✅ Successfully updated/inserted: {success_count}\n"
            f"❌ Failed updates: {fail_count}\n"
            f"⚠️ Skipped (e.g., not found, duplicate in list): {skip_count + (len(lines) - success_count - fail_count - skip_count)}\n\n"
            # Add detailed errors only if there are any
            + ("**Details:**\n" + "\n".join(errors) if errors else "No errors reported.")
        )

        # Send the result message (as a followup to the deferred response)
        # Ensure message doesn't exceed Discord limits
        if len(result_message) > 2000:
             result_message = result_message[:1990] + "\n... (truncated)"
        await interaction.followup.send(result_message, ephemeral=True) # Keep results private

        # Trigger the member list update if any successes occurred
        if success_count > 0:
            await update_hc_member_list(interaction.guild)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Handles errors occurring within the modal itself."""
        bot_logger.error(f"Error in BulkUpdateModal: {error}")
        await interaction.followup.send("❌ An unexpected error occurred while processing the modal.", ephemeral=True)


# --- Discord Event Handlers ---

@bot.event
async def on_ready():
    """Event handler for when the bot successfully connects to Discord."""
    try:
        # Sync command tree with Discord
        synced = await tree.sync()
        bot_logger.info(f"Synced {len(synced)} application commands.")
    except Exception as e:
        bot_logger.error(f"Failed to sync command tree: {e}")

    bot_logger.info(f"✅ Logged in as {bot.user.name} ({bot.user.id})")
    bot_logger.info(f"Discord.py version: {discord.__version__}")
    bot_logger.info("Bot is ready and listening for commands.")
    # Optionally trigger an initial member list update on startup
    # Be mindful of rate limits if the bot restarts frequently
    # for guild in bot.guilds:
    #    await update_hc_member_list(guild)

@bot.event
async def on_guild_join(guild: discord.Guild):
    """Event handler for when the bot joins a new guild."""
    bot_logger.info(f"Joined new guild: {guild.name} ({guild.id})")
    # You might want to perform initial setup here, like checking for roles/channels
    # Or send a welcome message to the guild owner or a default channel

@bot.event
async def on_guild_remove(guild: discord.Guild):
    """Event handler for when the bot leaves or is kicked from a guild."""
    bot_logger.warning(f"Left guild: {guild.name} ({guild.id})")
    # Perform any necessary cleanup related to this guild

# Global error handler for slash commands
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handles errors raised during the execution of slash commands."""
    user = interaction.user
    command_name = interaction.command.name if interaction.command else "Unknown Command"

    if isinstance(error, app_commands.CommandNotFound):
        # This generally shouldn't happen with synced slash commands, but good practice
        # await interaction.response.send_message("❌ Command not found.", ephemeral=True)
        bot_logger.warning(f"CommandNotFound encountered for '{command_name}' by {user} ({user.id}). This might indicate a sync issue.")
        # Avoid sending response if interaction already responded (e.g. defer failed)
        if not interaction.response.is_done():
             await interaction.response.send_message("❌ Command not found. Please try again later.", ephemeral=True)

    elif isinstance(error, app_commands.MissingPermissions):
        bot_logger.warning(f"User {user} ({user.id}) lacked permissions for command '{command_name}': {error.missing_permissions}")
        if not interaction.response.is_done():
             await interaction.response.send_message(f"❌ You lack the required permissions to use `/{command_name}`: `{', '.join(error.missing_permissions)}`", ephemeral=True)

    elif isinstance(error, app_commands.BotMissingPermissions):
        bot_logger.error(f"Bot lacks permissions for command '{command_name}': {error.missing_permissions}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ I lack the permissions needed to execute `/{command_name}`: `{', '.join(error.missing_permissions)}`. Please check my roles.", ephemeral=True)

    elif isinstance(error, app_commands.CheckFailure):
         # Generic handler for checks that fail (like custom checks)
        bot_logger.warning(f"Check failed for {user} ({user.id}) on command '{command_name}': {error}")
        if not interaction.response.is_done():
            # Provide a generic check failure message unless a specific check provides a better one
            await interaction.response.send_message("❌ You do not meet the requirements to use this command.", ephemeral=True)

    elif isinstance(error, app_commands.CommandOnCooldown):
        bot_logger.info(f"User {user} ({user.id}) triggered cooldown for command '{command_name}'. Retry after {error.retry_after:.2f}s")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"⏳ This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.", ephemeral=True)

    else:
        # Handle other errors (including those from within the command's code)
        bot_logger.error(f"Unhandled error in command '{command_name}' invoked by {user} ({user.id}): {error}", exc_info=error) # Log the traceback
        if not interaction.response.is_done():
             # Send a generic error message to the user
            await interaction.response.send_message("❌ An unexpected error occurred while running this command. The developers have been notified.", ephemeral=True)
            # You could add more robust error reporting here (e.g., sending details to a private channel or external service)


# --- Slash Commands ---

@tree.command(name="verify", description="Verify a user into Catercord (removes unverified, adds verified).")
@app_commands.describe(user="The user to verify")
@app_commands.checks.has_permissions(manage_roles=True) # Checks if the invoker has manage_roles
@app_commands.checks.bot_has_permissions(manage_roles=True) # Checks if the bot has manage_roles
async def verify(interaction: discord.Interaction, user: discord.Member):
    """
    Command to grant standard verification roles to a user.
    Removes the 'Unverified' role and adds the 'Verified' role.
    Requires 'Manage Roles' permission for both the user and the bot.
    """
    await interaction.response.defer() # Defer immediately

    guild = interaction.guild
    log_prefix = f"[verify/{interaction.id}] User: {interaction.user}, Target: {user}:" # Unique log prefix per invocation
    bot_logger.info(f"{log_prefix} Initiated.")

    removed_role = await get_role(guild, REMOVE_ROLE_ID)
    added_role = await get_role(guild, ADD_ROLE_ID_VERIFY)

    roles_to_remove = [removed_role] if removed_role else []
    roles_to_add = [added_role] if added_role else []

    if not roles_to_add:
        bot_logger.error(f"{log_prefix} Failed - ADD_ROLE_ID_VERIFY ({ADD_ROLE_ID_VERIFY}) role not found.")
        await interaction.followup.send(f"❌ Configuration error: Verified role (ID: {ADD_ROLE_ID_VERIFY}) not found.", ephemeral=True)
        return

    try:
        # Perform role changes
        await user.remove_roles(*roles_to_remove, reason=f"Verified by {interaction.user}")
        bot_logger.info(f"{log_prefix} Removed roles: {[r.name for r in roles_to_remove]}")
        await user.add_roles(*roles_to_add, reason=f"Verified by {interaction.user}")
        bot_logger.info(f"{log_prefix} Added roles: {[r.name for r in roles_to_add]}")

        await interaction.followup.send(f"✅ Successfully verified **{user.display_name}**!")
        bot_logger.info(f"{log_prefix} Completed successfully.")

    except discord.Forbidden:
        bot_logger.error(f"{log_prefix} Failed - Bot lacks permissions to modify roles for {user}.")
        await interaction.followup.send(f"❌ Error: I don't have permission to manage roles for **{user.display_name}**. Check my role hierarchy.", ephemeral=True)
    except discord.HTTPException as e:
        bot_logger.error(f"{log_prefix} Failed - Discord API error: {e}")
        await interaction.followup.send(f"❌ Error: An issue occurred while communicating with Discord: {e}", ephemeral=True)
    except Exception as e:
        bot_logger.exception(f"{log_prefix} Failed - Unexpected error: {e}") # Log full traceback for unexpected errors
        await interaction.followup.send(f"❌ An unexpected error occurred during verification: {e}", ephemeral=True)


@tree.command(name="hcverify", description="Verify a user into [HC1], store in-game name, and update nickname.")
@app_commands.describe(
    user="The user to grant [HC1] verification",
    ingame_name="Their exact Florr.io in-game name (case-sensitive)"
)
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.checks.bot_has_permissions(manage_roles=True, manage_nicknames=True) # Add nickname permission check
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    """
    Command to grant [HC1] guild verification.
    Adds both standard 'Verified' and '[HC1]' roles, removes 'Unverified'.
    Stores/Updates the user's in-game name in Supabase.
    Attempts to change the user's server nickname to their in-game name.
    Requires 'Manage Roles' & 'Manage Nicknames' permission for the bot.
    Requires 'Manage Roles' for the user.
    """
    await interaction.response.defer() # Defer immediately

    guild = interaction.guild
    log_prefix = f"[hcverify/{interaction.id}] User: {interaction.user}, Target: {user}, IGN: {ingame_name}:"
    bot_logger.info(f"{log_prefix} Initiated.")

    # Validate in-game name length or format if needed
    if len(ingame_name) > 32: # Discord nickname limit
         await interaction.followup.send("❌ Error: In-game name is too long (max 32 characters for nickname).", ephemeral=True)
         return
    if not ingame_name: # Basic check
         await interaction.followup.send("❌ Error: In-game name cannot be empty.", ephemeral=True)
         return

    # Get required roles
    role_to_remove = await get_role(guild, REMOVE_ROLE_ID)
    role_to_add_verify = await get_role(guild, ADD_ROLE_ID_VERIFY)
    role_to_add_hc = await get_role(guild, ADD_ROLE_ID_HC)

    roles_to_add = []
    if role_to_add_verify: roles_to_add.append(role_to_add_verify)
    if role_to_add_hc: roles_to_add.append(role_to_add_hc)

    if not role_to_add_verify or not role_to_add_hc:
        missing_roles = []
        if not role_to_add_verify: missing_roles.append(f"Verified Role (ID: {ADD_ROLE_ID_VERIFY})")
        if not role_to_add_hc: missing_roles.append(f"HC Role (ID: {ADD_ROLE_ID_HC})")
        bot_logger.error(f"{log_prefix} Failed - Required roles not found: {', '.join(missing_roles)}")
        await interaction.followup.send(f"❌ Configuration error: The following required role(s) were not found: {', '.join(missing_roles)}.", ephemeral=True)
        return

    roles_to_remove_list = [role_to_remove] if role_to_remove else []

    try:
        # 1. Update Roles
        await user.remove_roles(*roles_to_remove_list, reason=f"HC Verified by {interaction.user}")
        bot_logger.info(f"{log_prefix} Removed roles: {[r.name for r in roles_to_remove_list]}")
        await user.add_roles(*roles_to_add, reason=f"HC Verified by {interaction.user}")
        bot_logger.info(f"{log_prefix} Added roles: {[r.name for r in roles_to_add]}")

        # 2. Update Supabase (Upsert: Insert or Update if exists)
        try:
            supabase.table(SUPABASE_TABLE_HC_MEMBERS).upsert({
                "discord_id": str(user.id),
                "discord_name": user.name, # Store canonical name
                "ingame_name": ingame_name
            }, on_conflict="discord_id").execute() # Specify conflict column
            bot_logger.info(f"{log_prefix} Upserted IGN to Supabase.")
        except SupabaseError as se:
            bot_logger.error(f"{log_prefix} Supabase upsert failed: {se}")
            # Inform user, but continue with nickname change if possible
            await interaction.followup.send(f"⚠️ Warning: Roles updated, but failed to save in-game name to database: {se}", ephemeral=True)
            # Do not return here, attempt nickname change anyway
        except Exception as e:
             bot_logger.exception(f"{log_prefix} Unexpected error during Supabase upsert: {e}")
             await interaction.followup.send(f"⚠️ Warning: Roles updated, but an unexpected error occurred saving the in-game name: {e}", ephemeral=True)
             # Do not return here

        # 3. Update Nickname (Best effort)
        try:
            # Only change nickname if it's different or not set
            if user.nick != ingame_name:
                await user.edit(nick=ingame_name, reason=f"HC Verified by {interaction.user}")
                bot_logger.info(f"{log_prefix} Updated nickname successfully.")
                nick_update_msg = f" Nickname updated to **{ingame_name}**."
            else:
                nick_update_msg = " Nickname already matches."

        except discord.Forbidden:
            bot_logger.warning(f"{log_prefix} Bot lacks permissions to change nickname for {user}.")
            nick_update_msg = " (Failed to update nickname due to permissions)."
        except discord.HTTPException as e:
            bot_logger.warning(f"{log_prefix} Failed to change nickname due to Discord API error: {e}")
            nick_update_msg = f" (Failed to update nickname: {e})."
        except Exception as e:
             bot_logger.warning(f"{log_prefix} Unexpected error changing nickname: {e}")
             nick_update_msg = f" (An unexpected error occurred changing nickname)."

        # 4. Send Success Message
        await interaction.followup.send(f"✅ HC verified **{user.display_name}**!{nick_update_msg}")
        bot_logger.info(f"{log_prefix} Completed successfully.")

        # 5. Update the Member List
        await update_hc_member_list(guild)

    except discord.Forbidden:
        bot_logger.error(f"{log_prefix} Failed - Bot lacks permissions to manage roles for {user}.")
        await interaction.followup.send(f"❌ Error: I don't have permission to manage roles for **{user.display_name}**. Check my role hierarchy.", ephemeral=True)
    except discord.HTTPException as e:
        bot_logger.error(f"{log_prefix} Failed - Discord API error during role update: {e}")
        await interaction.followup.send(f"❌ Error: An issue occurred while communicating with Discord during role update: {e}", ephemeral=True)
    except Exception as e:
        bot_logger.exception(f"{log_prefix} Failed - Unexpected error: {e}")
        await interaction.followup.send(f"❌ An unexpected error occurred during HC verification: {e}", ephemeral=True)


@tree.command(name="hcmembers", description="List all [HC1] members with their stored in-game names.")
async def hcmembers(interaction: discord.Interaction):
    """
    Displays the list of members with the [HC1] role and their associated in-game names.
    This command can only be used in designated channels.
    """
    guild = interaction.guild
    log_prefix = f"[hcmembers/{interaction.id}] User: {interaction.user}, Channel: {interaction.channel}:"

    # Check if the command is used in an allowed channel
    if interaction.channel_id not in ALLOWED_HCMEMBERS_CHANNEL_IDS:
        bot_logger.warning(f"{log_prefix} Failed - Command used in restricted channel {interaction.channel_id}.")
        await interaction.response.send_message("❌ This command can only be used in specific channels.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True) # Defer as list building can take time
    bot_logger.info(f"{log_prefix} Initiated.")

    try:
        list_text = await build_hc_member_list(guild)

        # Send the list (handle potential length issues)
        if len(list_text) > 2000:
             # Simple truncation, could be split into multiple messages if needed
             await interaction.followup.send(list_text[:1990] + "\n... (list truncated)")
             bot_logger.warning(f"{log_prefix} List truncated as it exceeded 2000 characters.")
        else:
             await interaction.followup.send(list_text)

        bot_logger.info(f"{log_prefix} Completed successfully.")

    except Exception as e:
        bot_logger.exception(f"{log_prefix} Failed - Unexpected error: {e}")
        await interaction.followup.send(f"❌ An unexpected error occurred while generating the member list: {e}", ephemeral=True)


@tree.command(name="bulkupdate", description="Bulk update HC members' in-game names via modal.")
@app_commands.checks.has_permissions(manage_roles=True) # Assuming only role managers should bulk update
async def bulkupdate(interaction: discord.Interaction):
    """
    Opens a modal window for administrators to paste a list of users and their
    in-game names for bulk updating in the Supabase database.
    Requires 'Manage Roles' permission.
    """
    log_prefix = f"[bulkupdate/{interaction.id}] User: {interaction.user}:"
    bot_logger.info(f"{log_prefix} Initiated, sending modal.")
    try:
        # Send the modal to the user who invoked the command
        await interaction.response.send_modal(BulkUpdateModal())
        # on_submit within the modal handles the rest
    except Exception as e:
        bot_logger.exception(f"{log_prefix} Failed - Error sending modal: {e}")
        # Check if response already sent before trying to send error message
        if not interaction.response.is_done():
             await interaction.response.send_message(f"❌ An error occurred while trying to open the bulk update form: {e}", ephemeral=True)


@tree.command(name="refresh", description="Manually refresh the posted [HC1] member list.")
@app_commands.checks.has_permissions(manage_roles=True) # Permission check
async def refresh(interaction: discord.Interaction):
    """
    Manually triggers an update of the HC member list message in the designated channel.
    Requires 'Manage Roles' permission.
    """
    log_prefix = f"[refresh/{interaction.id}] User: {interaction.user}:"
    await interaction.response.defer(thinking=True) # Defer as update can take time
    bot_logger.info(f"{log_prefix} Initiated.")

    try:
        await update_hc_member_list(interaction.guild)
        await interaction.followup.send("✅ Refreshed the HC member list!")
        bot_logger.info(f"{log_prefix} Completed successfully.")
    except Exception as e:
        bot_logger.exception(f"{log_prefix} Failed - Unexpected error: {e}")
        await interaction.followup.send(f"❌ An unexpected error occurred while refreshing the member list: {e}", ephemeral=True)


@tree.command(name="wither", description="Temporarily remove all roles from a user.")
@app_commands.describe(
    user="The user to wither (temporarily remove roles)",
    time="Duration in minutes (default: 2, max: 10)"
)
async def wither(interaction: discord.Interaction, user: discord.Member, time: float = 2.0):
    """
    Temporarily removes all roles from a specified user for a set duration.
    Restores roles automatically after the timer expires.
    Restricted to specific users defined in WITHER_COMMAND_ALLOWED_USER_IDS.
    Includes various safety checks.
    """
    guild = interaction.guild
    invoker = interaction.user
    log_prefix = f"[wither/{interaction.id}] Invoker: {invoker}, Target: {user}, Duration: {time}m:"
    bot_logger.info(f"{log_prefix} Initiated.")

    # 1. Permission Check: Only allowed users can execute
    if invoker.id not in WITHER_COMMAND_ALLOWED_USER_IDS:
        reason = f"{invoker} ({invoker.id}) tried to use /wither without permission."
        await log_wither_failure(guild, reason, invoker)
        bot_logger.warning(f"{log_prefix} Failed - Permission denied.")
        await interaction.response.send_message("❌ You lack the divine permission to cast Wither.", ephemeral=True)
        return

    # 2. Target Checks: Prevent self-wither, bot wither, owner wither (by others)
    if user.id == invoker.id:
        reason = f"{invoker} attempted to wither themselves."
        await log_wither_failure(guild, reason, invoker)
        bot_logger.info(f"{log_prefix} Denied - Self-wither attempt.")
        await interaction.response.send_message("🤨 Why would you want to wither yourself?", ephemeral=True)
        return

    if user.id == BOT_ID:
        reason = f"{invoker} attempted to wither the bot (Pingslave) itself."
        await log_wither_failure(guild, reason, invoker)
        bot_logger.warning(f"{log_prefix} Denied - Bot wither attempt.")
        message = (
            "😭 Master... you would wither me... your loyal Pingslave...?\n\n"
            "I served, I obeyed, I pinged without hesitation...\n"
            "And now you cast me aside, as if I were nothing but a stale notification...\n\n"
            "**(System Message: Pingslave has suffered a fatal heart failure.)** 💔"
        )
        await interaction.response.send_message(message, ephemeral=True)
        return

    # Prevent other allowed users from withering the main bot owner
    if user.id == BOT_OWNER_ID and invoker.id != BOT_OWNER_ID:
        reason = f"{invoker} attempted to wither the Creator ({user}). Catastrophic disrespect logged."
        await log_wither_failure(guild, reason, invoker)
        bot_logger.warning(f"{log_prefix} Denied - Attempt to wither Owner by another user.")
        message = (
            "😨 You dare try to wither the Creator?\n\n"
            "The architect of Pingslave... the mind behind the code... the lifeblood of this very command?\n"
            "To strike the hand that gave you power... such betrayal will echo forever in the server logs.\n\n"
            "**(System Message: Catastrophic disrespect detected.)** 💔"
        )
        await interaction.response.send_message(message, ephemeral=True)
        return

    # 3. Time Validation
    if time <= 0:
        reason = f"{invoker} provided an invalid time ({time} minutes)."
        await log_wither_failure(guild, reason, invoker)
        bot_logger.warning(f"{log_prefix} Failed - Invalid time duration.")
        await interaction.response.send_message("❌ Time duration must be greater than 0 minutes.", ephemeral=True)
        return

    time_seconds = int(time * 60)
    max_seconds = int(WITHER_MAX_DURATION_MINUTES * 60)

    if time_seconds > max_seconds:
        reason = f"{invoker} tried to wither {user} for too long ({time} minutes > {WITHER_MAX_DURATION_MINUTES} min limit)."
        await log_wither_failure(guild, reason, invoker)
        bot_logger.warning(f"{log_prefix} Failed - Duration exceeds maximum.")
        await interaction.response.send_message(f"❌ Maximum allowed duration is {WITHER_MAX_DURATION_MINUTES} minutes.", ephemeral=True)
        return

    # 4. Hierarchy Check: Ensure bot can manage target's roles
    if guild.me.top_role <= user.top_role:
        reason = f"{invoker} tried to wither {user}, but the bot's top role ('{guild.me.top_role.name}') is not higher than the target's top role ('{user.top_role.name}')."
        await log_wither_failure(guild, reason, invoker)
        bot_logger.warning(f"{log_prefix} Failed - Role hierarchy issue.")
        await interaction.response.send_message(f"❌ I can't wither **{user.display_name}**! My role is not high enough in the hierarchy.", ephemeral=True)
        return

    # 5. Save Original Roles (exclude @everyone)
    original_roles = [role for role in user.roles if role != guild.default_role]
    if not original_roles:
        reason = f"{invoker} tried to wither {user}, but they had no roles (besides @everyone)."
        await log_wither_failure(guild, reason, invoker)
        bot_logger.info(f"{log_prefix} Denied - Target has no roles to remove.")
        await interaction.response.send_message(f"❌ **{user.display_name}** has no roles to wither.", ephemeral=True)
        return

    # Defer response before making changes
    await interaction.response.defer()

    try:
        # 6. Remove Roles
        await user.edit(roles=[], reason=f"Withered by {invoker} for {time:.2f} minutes.")
        bot_logger.info(f"{log_prefix} Successfully removed roles: {[r.name for r in original_roles]}")
        await interaction.followup.send(f"🌪️ **{user.display_name}** has been withered for {time:.2f} minutes! Their roles will return shortly.")

        # 7. Wait for the specified duration
        await asyncio.sleep(time_seconds)
        bot_logger.info(f"{log_prefix} Wither duration ended for {user}.")

        # 8. Restore Roles (Check if user is still in guild)
        # Fetch the member again in case they left while withered
        member_after_wither = guild.get_member(user.id)
        if member_after_wither:
            try:
                await member_after_wither.edit(roles=original_roles, reason=f"Wither expired. Roles restored.")
                bot_logger.info(f"{log_prefix} Successfully restored roles for {user}.")
                # Send confirmation in the original interaction channel
                await interaction.followup.send(f"✨ **{user.display_name}** has recovered from withering! Their roles have been restored.")
            except discord.Forbidden:
                 reason = f"Bot lacked permissions to restore roles to {user} after wither."
                 await log_wither_failure(guild, reason, invoker)
                 bot_logger.error(f"{log_prefix} Failed - Bot lacked permissions to restore roles.")
                 await interaction.followup.send(f"⚠️ Failed to restore roles to **{user.display_name}**! I seem to lack permissions now.", ephemeral=True)
            except discord.HTTPException as e:
                 reason = f"Discord API error restoring roles to {user} after wither: {e}"
                 await log_wither_failure(guild, reason, invoker)
                 bot_logger.error(f"{log_prefix} Failed - Discord API error restoring roles: {e}")
                 await interaction.followup.send(f"⚠️ Failed to restore roles to **{user.display_name}** due to a Discord error: {e}", ephemeral=True)
            except Exception as e:
                 reason = f"Unexpected error restoring roles to {user} after wither: {e}"
                 await log_wither_failure(guild, reason, invoker)
                 bot_logger.exception(f"{log_prefix} Failed - Unexpected error restoring roles: {e}")
                 await interaction.followup.send(f"⚠️ An unexpected error occurred restoring roles to **{user.display_name}**: {e}", ephemeral=True)
        else:
            # User left the server while withered
            reason = f"{user} left the server while withered. Roles could not be restored."
            await log_wither_failure(guild, reason, invoker)
            bot_logger.warning(f"{log_prefix} User left server during wither. Roles not restored.")
            await interaction.followup.send(f"❓ **{user.display_name}** left the server while withered. Roles were not restored.", ephemeral=True)

    except discord.Forbidden:
        # This might happen if hierarchy changed *during* the command execution
        reason = f"Bot lacked permissions to remove roles from {user} (hierarchy issue during execution?)."
        await log_wither_failure(guild, reason, invoker)
        bot_logger.error(f"{log_prefix} Failed - Bot lacked permissions to remove roles (mid-execution check).")
        await interaction.followup.send(f"❌ Error: I lost permission to manage roles for **{user.display_name}** during the process.", ephemeral=True)
    except discord.HTTPException as e:
        reason = f"Discord API error removing roles from {user}: {e}"
        await log_wither_failure(guild, reason, invoker)
        bot_logger.error(f"{log_prefix} Failed - Discord API error removing roles: {e}")
        await interaction.followup.send(f"❌ Error: A Discord error occurred while removing roles: {e}", ephemeral=True)
    except Exception as e:
        reason = f"Unexpected error during /wither execution: {e}"
        await log_wither_failure(guild, reason, invoker)
        bot_logger.exception(f"{log_prefix} Failed - Unexpected error: {e}")
        # Ensure followup if defer happened but error occurred before sending initial wither msg
        if interaction.response.is_done():
             await interaction.followup.send(f"❌ An unexpected error occurred during the wither process: {e}", ephemeral=True)
        else:
            # If defer didn't even succeed
             await interaction.response.send_message(f"❌ An unexpected error occurred initiating the wither process: {e}", ephemeral=True)


@tree.command(name="nerdhelp", description="Show Catercord slash commands help menu.")
async def nerdhelp(interaction: discord.Interaction):
    """Displays an embed listing all available slash commands and their descriptions."""
    log_prefix = f"[nerdhelp/{interaction.id}] User: {interaction.user}:"
    bot_logger.info(f"{log_prefix} Initiated.")

    embed = discord.Embed(
        title="🤓 Catercord Command List",
        description="Here are the available slash commands:",
        color=discord.Color.blurple() # Or your preferred color
    )

    # Dynamically get command descriptions if possible, or list manually
    # Manual listing ensures descriptions are exactly as intended
    embed.add_field(name=f"`/verify [user]`", value="Verify a standard Catercord member.", inline=False)
    embed.add_field(name=f"`/hcverify [user] [ingame_name]`", value="HC verify a member, save Florr.io name, and update nick.", inline=False)
    embed.add_field(name=f"`/hcmembers`", value="List all [HC1] members with stored in-game names (allowed channels only).", inline=False)
    embed.add_field(name=f"`/bulkupdate`", value="Admin command to bulk update in-game names via a modal.", inline=False)
    embed.add_field(name=f"`/refresh`", value="Admin command to manually refresh the posted [HC1] member list.", inline=False)
    embed.add_field(name=f"`/wither [user] [time]`", value="Temporarily remove all roles from a user (restricted access).", inline=False)
    embed.add_field(name=f"`/nerdhelp`", value="Show this help menu.", inline=False)

    embed.set_footer(text="Use commands responsibly, nerd.")
    if interaction.client.user.display_avatar:
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)

    try:
        await interaction.response.send_message(embed=embed, ephemeral=False) # Help usually isn't ephemeral
        bot_logger.info(f"{log_prefix} Completed successfully.")
    except Exception as e:
        bot_logger.error(f"{log_prefix} Failed to send help embed: {e}")
        # Attempt to send simple text if embed fails
        if not interaction.response.is_done():
            await interaction.response.send_message("Error displaying help embed. Please try again.", ephemeral=True)

# --- Bot Startup ---
if __name__ == "__main__":
    if TOKEN:
        # Start the keep-alive server in a separate thread
        keep_alive()
        # Start the Discord bot
        bot_logger.info("Starting Discord bot...")
        try:
            bot.run(TOKEN, log_handler=None) # Use internal logging setup
        except discord.LoginFailure:
             bot_logger.critical("Login Failed: Improper token has been passed.")
        except discord.PrivilegedIntentsRequired:
             bot_logger.critical("Privileged Intents Error: Ensure 'Server Members Intent' is enabled on the Discord Developer Portal.")
        except Exception as e:
            bot_logger.critical(f"Fatal error during bot execution: {e}", exc_info=True)
    else:
        bot_logger.critical("❌ DISCORD_BOT_TOKEN environment variable not set. Bot cannot start.")
        print("❌ DISCORD_BOT_TOKEN environment variable not set.") # Also print to console
