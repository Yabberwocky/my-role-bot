# main.py
import os
import threading
import asyncio
from dotenv import load_dotenv # Import dotenv

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput
from flask import Flask
from supabase import create_client, Client
# Potentially import specific Supabase/Postgrest errors if needed for finer control
# from postgrest import APIError # Example, check actual library for specifics

# --- Environment Setup ---
# Load environment variables from a .env file in the same directory
# Create a file named .env and add your secrets like:
# DISCORD_BOT_TOKEN=your_token_here
# SUPABASE_URL=your_url_here
# SUPABASE_KEY=your_key_here
load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- Basic Checks ---
if not TOKEN:
    print("❌ FATAL: DISCORD_BOT_TOKEN environment variable not set.")
    exit()
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ FATAL: SUPABASE_URL or SUPABASE_KEY environment variable not set.")
    exit()

# --- Supabase Client ---
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Successfully connected to Supabase.")
except Exception as e:
    print(f"❌ FATAL: Failed to connect to Supabase: {e}")
    exit()


# --- Configuration ---
# Role IDs (Add comments explaining each role)
REMOVE_ROLE_ID = 1360176495947022447       # Role removed upon verification (e.g., 'Unverified')
ADD_ROLE_ID_VERIFY = 1248708073019805717   # Standard verified member role
ADD_ROLE_ID_HC = 1230235110415274004       # [HC1] Guild Member role

# Allowed Channel IDs for /hcmembers command
ALLOWED_CHANNEL_IDS = {
    1354431395140731165, # Example: hc-member-list channel
    1330664430148780102, # Example: bot-commands channel
    1248710731407560835  # Example: staff-bot-commands channel
}

# Channel ID to auto-post/update the [HC1] member list
HC_MEMBER_LIST_CHANNEL_ID = 1354431395140731165 # Channel where the list is posted

# Wither Command Configuration
WITHER_LOG_CHANNEL_ID = 1362988767367135453  # Channel for logging wither attempts/failures
BOT_ID = 1365572437185400893                # The Bot's own User ID
OWNER_ID = 1230848174218940416              # Your User ID (for special protection)
# IDs of users allowed to use /wither (e.g., server owners, trusted admins)
# Consider using Administrator permission check instead if more flexible
SERVER_OWNER_IDS = {
    1230848174218940416, # Your ID
    955448447790620692,  # Another owner/admin ID
    879320982299484240   # Another owner/admin ID
}
MAX_WITHER_DURATION_MINUTES = 10 # Maximum time (in minutes) for the wither effect


# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.members = True # Crucial for accessing member information and roles
bot = commands.Bot(command_prefix="!", intents=intents) # Prefix is fallback, focus is on slash commands
tree = bot.tree


# --- Flask App for Keep Alive (Standard for Replit/similar platforms) ---
app = Flask('')

@app.route('/')
def home():
    return "Catercord Bot is alive!"

def run_flask():
    try:
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        print(f"[KeepAlive Flask] Error: {e}")


def keep_alive():
    print("[KeepAlive] Starting Flask server in a background thread.")
    thread = threading.Thread(target=run_flask)
    thread.daemon = True # Allows Python to exit even if this thread is running
    thread.start()


# --- Helper Functions ---

async def log_wither_event(interaction: discord.Interaction, title: str, description: str, color: discord.Color):
    """Logs an event related to the /wither command to the designated channel."""
    log_channel = interaction.guild.get_channel(WITHER_LOG_CHANNEL_ID)
    if log_channel and isinstance(log_channel, discord.TextChannel):
        try:
            embed = discord.Embed(title=title, description=description, color=color)
            embed.set_footer(text=f"Invoked by: {interaction.user} ({interaction.user.id})")
            if interaction.guild:
                 embed.timestamp = discord.utils.utcnow()
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            print(f"[Wither Log] Error: Missing permissions to send messages in channel {log_channel.id}")
        except Exception as e:
            print(f"[Wither Log] Error sending log message: {e}")
    else:
        print(f"[Wither Log] Error: Log channel ID {WITHER_LOG_CHANNEL_ID} not found or is not a text channel.")


async def build_hc_member_list(guild: discord.Guild) -> str:
    """
    Builds the '[HC1] Guild Members' list text efficiently.
    Fetches all required in-game names from Supabase in a single query.
    """
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        print("[build_hc_member_list] Error: HC Role ID not found.")
        return "**Error:** [HC1] role (ID: {ADD_ROLE_ID_HC}) not found in this server."

    # Sort members by display name (case-insensitive)
    members_with_role = sorted(hc_role.members, key=lambda m: m.display_name.lower())

    if not members_with_role:
        return "**[HC1] Guild Members:**\nNo members currently have the [HC1] role."

    member_ids_str = [str(m.id) for m in members_with_role]
    ingame_names_map = {} # Map: discord_id (str) -> ingame_name (str)

    # Fetch all names in one go
    if member_ids_str:
        try:
            response = supabase.table("hc_members") \
                             .select("discord_id, ingame_name") \
                             .in_("discord_id", member_ids_str) \
                             .execute()

            if response.data:
                for record in response.data:
                    # Ensure discord_id is stored as string for consistent key lookup
                    ingame_names_map[str(record['discord_id'])] = record.get("ingame_name", "Unknown")
            # print(f"[build_hc_member_list] Fetched {len(ingame_names_map)} names from Supabase.")

        except Exception as e:
            print(f"[build_hc_member_list] Supabase Error fetching bulk ingame_names: {e}")
            # Fallback: proceed with "Unknown" for all, or return an error message
            return f"**Error:** Failed to fetch member data from database. Please try again later.\n`{e}`"

    # Build the list string
    lines = []
    for idx, member in enumerate(members_with_role, 1):
        # Use display_name for better reflection of current server nickname
        discord_name = member.display_name
        # Lookup fetched name, default to "Unknown" if not found or error occurred
        ingame_name = ingame_names_map.get(str(member.id), "Unknown")
        lines.append(f"{idx}. {discord_name} ➔ {ingame_name}")

    return "**[HC1] Guild Members:**\n" + "\n".join(lines)


async def update_hc_member_list(guild: discord.Guild, context_message: str = "update"):
    """
    Finds the existing member list message posted by the bot in the dedicated
    channel and edits it, or sends a new one if not found.
    """
    channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not channel:
        print(f"[update_hc_member_list] Error: Target channel ID {HC_MEMBER_LIST_CHANNEL_ID} not found.")
        return
    if not isinstance(channel, discord.TextChannel):
         print(f"[update_hc_member_list] Error: Target channel ID {HC_MEMBER_LIST_CHANNEL_ID} is not a text channel.")
         return

    print(f"[update_hc_member_list] Attempting to update list ({context_message})...")
    list_text = await build_hc_member_list(guild)

    # Check channel permissions *before* trying to fetch history or send/edit
    if not channel.permissions_for(guild.me).send_messages or not channel.permissions_for(guild.me).read_message_history:
         print(f"[update_hc_member_list] Error: Missing Send Messages or Read History permission in channel {channel.id}.")
         return

    message_to_edit = None
    try:
        # Look for a message previously sent by the bot starting with the header
        async for message in channel.history(limit=10): # Reduced limit is usually sufficient
            if message.author == guild.me and message.content.startswith("**[HC1] Guild Members:**"):
                message_to_edit = message
                break
    except discord.Forbidden:
         print(f"[update_hc_member_list] Error: Missing Read History permission in channel {channel.id} during search.")
         return # Can't search, so can't reliably edit
    except Exception as e:
         print(f"[update_hc_member_list] Error fetching channel history: {e}")
         # Proceed to potentially send a new message if history fails

    try:
        if message_to_edit:
            if message_to_edit.content != list_text: # Only edit if content changed
                await message_to_edit.edit(content=list_text)
                print(f"[update_hc_member_list] Successfully edited existing list ({context_message}).")
            else:
                 print(f"[update_hc_member_list] List content unchanged, edit skipped ({context_message}).")
        else:
            # Check send permission again just in case, though checked earlier
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(list_text)
                print(f"[update_hc_member_list] Sent new list message ({context_message}).")
            else:
                 print(f"[update_hc_member_list] Error: Missing Send Messages permission (needed for new message).")

    except discord.Forbidden:
         print(f"[update_hc_member_list] Error: Missing Send/Edit permission in channel {channel.id}.")
    except Exception as e:
        print(f"[update_hc_member_list] Error sending/editing message: {e}")


# --- Modals ---

class BulkUpdateModal(Modal, title="Bulk Update [HC1] In-Game Names"):
    data = TextInput(
        label="Paste list (Discord Name ➔ In-Game Name)",
        style=discord.TextStyle.paragraph,
        placeholder="Example:\nCoolDude#1234 ➔ FlorrMaster\nAnotherUser ➔ PetalPusher\n...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Defer immediately as processing can take time
        await interaction.response.defer(thinking=True, ephemeral=True) # Ephemeral thinking message

        success_count = 0
        fail_count = 0
        errors = []
        updates_to_perform = [] # Store tuples: (member_id_str, discord_name, ingame_name)

        lines = self.data.value.splitlines()
        guild = interaction.guild

        if not guild:
            await interaction.followup.send("❌ Error: Guild information not found.", ephemeral=True)
            return

        # --- Phase 1: Parse input and find members ---
        print(f"[Bulk Update] Parsing {len(lines)} lines...")
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or "➔" not in line:
                # errors.append(f"⚠️ Line {line_num}: Invalid format (missing '➔'). Skipped.")
                continue # Silently skip empty or invalid lines

            try:
                discord_identifier, ingame_name = map(str.strip, line.split("➔", 1))
            except ValueError:
                 errors.append(f"⚠️ Line {line_num}: Invalid format near '➔'. Skipped.")
                 fail_count += 1
                 continue

            if not discord_identifier or not ingame_name:
                 errors.append(f"⚠️ Line {line_num}: Missing Discord name or In-Game name. Skipped.")
                 fail_count += 1
                 continue

            # Try finding member by name#discriminator or just name
            member = guild.get_member_named(discord_identifier)
            if not member:
                # Fallback: case-insensitive search (less reliable)
                member = discord.utils.find(lambda m: m.name.lower() == discord_identifier.lower(), guild.members)

            if not member:
                errors.append(f"❌ Line {line_num}: Discord user '{discord_identifier}' not found in this server. Skipped.")
                fail_count += 1
                continue

            # Check if member already has the HC role - optional, but good practice
            hc_role = guild.get_role(ADD_ROLE_ID_HC)
            if hc_role and hc_role not in member.roles:
                 errors.append(f"⚠️ Line {line_num}: User {member.mention} found, but doesn't have the [HC1] role. Skipped DB update.")
                 # Decide if you still want to try adding them to DB or skip entirely
                 fail_count += 1
                 continue

            updates_to_perform.append((str(member.id), member.name, ingame_name)) # Use actual member.name for DB record

        # --- Phase 2: Perform Supabase Upserts ---
        print(f"[Bulk Update] Found {len(updates_to_perform)} valid entries to update in DB.")
        if updates_to_perform:
            records_to_upsert = [
                {
                    "discord_id": member_id_str,
                    "discord_name": discord_name, # Store the Discord name at the time of update
                    "ingame_name": ingame_name
                }
                for member_id_str, discord_name, ingame_name in updates_to_perform
            ]

            try:
                # Use upsert for efficiency: inserts new, updates existing based on discord_id
                response = supabase.table("hc_members").upsert(
                    records_to_upsert,
                    on_conflict="discord_id" # Specify the column that causes conflicts (unique key)
                ).execute()

                # Supabase upsert response might not directly tell us count of inserts vs updates easily.
                # We assume success if no exception occurs.
                success_count = len(updates_to_perform) # Assume all attempts were successful if no error
                print(f"[Bulk Update] Supabase upsert executed. Response: {response.data[:5]}...") # Log first few results if any

            except Exception as e:
                # If bulk upsert fails, we can't easily tell which ones failed.
                # Log the general error. More granular error handling might require individual upserts.
                print(f"[Bulk Update] SupABASE UPSERT FAILED: {e}")
                errors.append(f"❌ DATABASE ERROR: Failed to save updates to Supabase. Check bot logs. Error: {e}")
                # Mark all as failed in this scenario
                fail_count += len(updates_to_perform)
                success_count = 0 # Reset success count as the batch failed

        # --- Phase 3: Report Results ---
        result_message_parts = [
            f"**Bulk Update Results:**",
            f"✅ Successfully processed {success_count} members in the database.",
            f"❌ Failed/Skipped {fail_count} entries."
        ]

        if errors:
             result_message_parts.append("\n**Details:**")
             # Show only a limited number of errors to avoid hitting message limits
             max_errors_to_show = 15
             result_message_parts.extend(errors[:max_errors_to_show])
             if len(errors) > max_errors_to_show:
                 result_message_parts.append(f"...and {len(errors) - max_errors_to_show} more errors/warnings.")

        result_message = "\n".join(result_message_parts)

        # Send results ephemerally
        await interaction.followup.send(result_message, ephemeral=True)

        # --- Phase 4: Update Member List ---
        if success_count > 0: # Only update list if there were successful DB changes
             print("[Bulk Update] Triggering member list update.")
             await update_hc_member_list(guild, context_message="bulk_update")


    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(f"[Bulk Update Modal] Error: {error}")
        await interaction.followup.send(f"❌ An unexpected error occurred in the modal: {error}", ephemeral=True)


# --- Bot Events ---

@bot.event
async def on_ready():
    print("-" * 30)
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"🔗 Discord.py Version: {discord.__version__}")
    print(f"🔑 Supabase URL configured: {bool(SUPABASE_URL)}")
    print(f" guilds: {[guild.name for guild in bot.guilds]}") # Print guilds the bot is in
    print("-" * 30)
    try:
        synced = await tree.sync()
        print(f"🔄 Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")

    # Start keep-alive after bot is ready
    keep_alive()

    # Initial member list update on startup for the primary guild (if applicable)
    # You might want to make this more robust if the bot is in multiple guilds
    if bot.guilds:
        primary_guild = bot.guilds[0] # Or find the specific guild by ID
        print(f"🚀 Performing initial HC member list update for guild '{primary_guild.name}'...")
        await update_hc_member_list(primary_guild, context_message="on_ready")


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for slash commands."""
    if isinstance(error, app_commands.CommandNotFound):
        # This usually shouldn't happen with synced commands, but good practice
        await interaction.response.send_message("❌ Command not found.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        print(f"[Permissions Error] User {interaction.user} lacked permissions for /{interaction.command.name if interaction.command else 'unknown'}: {error.missing_permissions}")
        await interaction.response.send_message(
            f"❌ You don't have the required permissions (`{', '.join(error.missing_permissions)}`) to use this command.",
            ephemeral=True
        )
    elif isinstance(error, app_commands.CheckFailure):
         # Catches custom checks or things like `is_owner()`
         print(f"[Check Failure] User {interaction.user} failed checks for /{interaction.command.name if interaction.command else 'unknown'}: {error}")
         await interaction.response.send_message("❌ You do not meet the requirements to use this command.", ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
    else:
        # Log the full error for debugging
        print(f"💥 Unhandled error in command '/{interaction.command.name if interaction.command else 'unknown'}':")
        print(f"   User: {interaction.user} (ID: {interaction.user.id})")
        print(f"   Guild: {interaction.guild.name if interaction.guild else 'DM'} (ID: {interaction.guild_id})")
        print(f"   Channel: {interaction.channel.name if interaction.channel else 'DM'} (ID: {interaction.channel_id})")
        print(f"   Error Type: {type(error)}")
        print(f"   Error: {error}")
        # If the interaction hasn't been responded to yet, send a generic error message
        if not interaction.response.is_done():
            try:
                await interaction.response.send_message("❌ An unexpected error occurred while running this command. Please contact the bot owner.", ephemeral=True)
            except discord.InteractionResponded:
                 # If response happened between check and send (race condition)
                 await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)
            except Exception as e_resp:
                 print(f"   Additionally, failed to send error message to user: {e_resp}")


# --- Slash Commands ---

@tree.command(name="verify", description="Verify a user, granting standard member access.")
@app_commands.describe(user="The user to verify")
@app_commands.checks.has_permissions(manage_roles=True) # Checks if the *invoker* has manage_roles
async def verify(interaction: discord.Interaction, user: discord.Member):
    """Adds standard verified role and removes the unverified role."""
    await interaction.response.defer() # Acknowledge command quickly
    guild = interaction.guild

    if not guild:
        await interaction.followup.send("❌ This command can only be used in a server.")
        return

    roles_to_add = []
    roles_to_remove = []
    action_log = []

    # Role to add
    add_role = guild.get_role(ADD_ROLE_ID_VERIFY)
    if add_role:
        if add_role not in user.roles:
            roles_to_add.append(add_role)
            action_log.append(f"➕ Added role: {add_role.name}")
        else:
            action_log.append(f"ℹ️ User already had role: {add_role.name}")
    else:
        action_log.append(f"⚠️ Role ID {ADD_ROLE_ID_VERIFY} (Verify Add) not found.")

    # Role to remove
    remove_role = guild.get_role(REMOVE_ROLE_ID)
    if remove_role:
        if remove_role in user.roles:
            roles_to_remove.append(remove_role)
            action_log.append(f"➖ Removed role: {remove_role.name}")
    else:
        action_log.append(f"⚠️ Role ID {REMOVE_ROLE_ID} (Verify Remove) not found.")

    try:
        # Perform role changes if any are needed
        if roles_to_add or roles_to_remove:
            await user.edit(roles=[r for r in user.roles if r not in roles_to_remove] + roles_to_add)
            await interaction.followup.send(f"✅ Verified **{user.display_name}**!\n" + "\n".join(action_log))
        else:
             await interaction.followup.send(f"ℹ️ No role changes needed for **{user.display_name}**.\n" + "\n".join(action_log))

    except discord.Forbidden:
        print(f"[verify] Error: Bot lacks permissions to modify roles for {user.display_name}.")
        await interaction.followup.send(f"❌ Error: I don't have permission to modify roles for **{user.display_name}**. Check my role hierarchy and permissions.")
    except Exception as e:
        print(f"[verify] Error: {e}")
        await interaction.followup.send(f"❌ An unexpected error occurred during verification: {e}", ephemeral=True)


@tree.command(name="hcverify", description="Verify a user into [HC1], store IGN, and update nickname.")
@app_commands.describe(
    user="The user to grant [HC1] access",
    ingame_name="Their Florr.io In-Game Name (will be used for nickname)"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    """Adds HC role, standard verify role, removes unverified, updates DB, and sets nickname."""
    await interaction.response.defer() # Acknowledge command quickly
    guild = interaction.guild

    if not guild:
        await interaction.followup.send("❌ This command can only be used in a server.")
        return

    roles_to_add = []
    roles_to_remove = []
    action_log = []

    # --- Role Management ---
    # Role to remove
    remove_role = guild.get_role(REMOVE_ROLE_ID)
    if remove_role and remove_role in user.roles:
        roles_to_remove.append(remove_role)
        action_log.append(f"➖ Removed role: {remove_role.name}")

    # Roles to add (Standard Verify + HC)
    verify_role = guild.get_role(ADD_ROLE_ID_VERIFY)
    hc_role = guild.get_role(ADD_ROLE_ID_HC)

    if verify_role and verify_role not in user.roles:
        roles_to_add.append(verify_role)
        action_log.append(f"➕ Added role: {verify_role.name}")
    elif not verify_role:
         action_log.append(f"⚠️ Role ID {ADD_ROLE_ID_VERIFY} (Verify Add) not found.")

    if hc_role and hc_role not in user.roles:
        roles_to_add.append(hc_role)
        action_log.append(f"➕ Added role: {hc_role.name}")
    elif not hc_role:
         action_log.append(f"⚠️ Role ID {ADD_ROLE_ID_HC} (HC Add) not found.")


    # --- Database Update (Upsert) ---
    db_success = False
    try:
        response = supabase.table("hc_members").upsert({
            "discord_id": str(user.id),
            "discord_name": user.name, # Store their actual Discord username
            "ingame_name": ingame_name
        }, on_conflict="discord_id").execute() # Insert or Update based on discord_id
        action_log.append(f"💾 Database updated: IGN set to '{ingame_name}'.")
        db_success = True
        # print(f"[hcverify] Supabase upsert response for {user.name}: {response.data}") # Optional detailed logging

    except Exception as e:
        print(f"[hcverify] Supabase Error for {user.name}: {e}")
        action_log.append(f"❌ Database Error: Failed to save IGN. `{e}`")


    # --- Nickname Change ---
    nickname_success = False
    # Check if bot has permission AND if user's top role isn't higher than bot's
    can_change_nickname = False
    if guild.me.guild_permissions.manage_nicknames:
        if user.top_role < guild.me.top_role:
             can_change_nickname = True
        else:
             action_log.append(f"⚠️ Nickname: Cannot change nickname, user's role is higher than mine.")
    else:
         action_log.append(f"⚠️ Nickname: Cannot change nickname, I lack 'Manage Nicknames' permission.")


    if can_change_nickname:
        try:
            # Only change if different to avoid unnecessary API calls/log spam
            if user.display_name != ingame_name:
                await user.edit(nick=ingame_name)
                action_log.append(f"👤 Nickname updated to '{ingame_name}'.")
                nickname_success = True
            else:
                 action_log.append(f"ℹ️ Nickname: Already set to '{ingame_name}'.")
                 nickname_success = True # Considered success as it matches target
        except discord.Forbidden:
             # This case should be caught by earlier checks, but handle defensively
             print(f"[hcverify] Nickname change forbidden for {user.display_name} despite checks.")
             action_log.append(f"❌ Nickname: Failed - Permission denied unexpectedly.")
        except Exception as e:
             print(f"[hcverify] Nickname change failed for {user.display_name}: {e}")
             action_log.append(f"❌ Nickname: Failed - An error occurred: `{e}`")


    # --- Perform Role Changes ---
    role_change_success = False
    try:
        if roles_to_add or roles_to_remove:
            await user.edit(roles=[r for r in user.roles if r not in roles_to_remove] + roles_to_add)
            role_change_success = True # Assume success if no exception
        else:
            action_log.append("ℹ️ Roles: No changes needed.")
            role_change_success = True # No changes needed is also a success state

    except discord.Forbidden:
        print(f"[hcverify] Role change forbidden for {user.display_name}.")
        action_log.append(f"❌ Roles: Failed - Permission denied. Check bot hierarchy.")
    except Exception as e:
        print(f"[hcverify] Role change failed for {user.display_name}: {e}")
        action_log.append(f"❌ Roles: Failed - An error occurred: `{e}`")


    # --- Final Response ---
    if role_change_success and db_success and nickname_success:
         response_message = f"✅ HC verified **{user.display_name}** as **{ingame_name}**!\n" + "\n".join(action_log)
         await interaction.followup.send(response_message)
         # Update the member list only if database was successfully updated
         await update_hc_member_list(guild, context_message="hcverify")
    else:
         response_message = f"⚠️ HC verification for **{user.display_name}** completed with issues:\n" + "\n".join(action_log)
         await interaction.followup.send(response_message, ephemeral=True) # Send as ephemeral if there were issues


@tree.command(name="hcmembers", description="List all [HC1] members with their stored in-game names.")
async def hcmembers(interaction: discord.Interaction):
    """Displays the formatted list of HC members and their IGNs."""
    # Check if command is used in allowed channels
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        await interaction.response.send_message(
            f"❌ This command can only be used in designated channels. Allowed: <#{'>, <#'.join(map(str, ALLOWED_CHANNEL_IDS))}>",
            ephemeral=True
        )
        return

    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True) # Acknowledge, list building might take a moment
    try:
        list_text = await build_hc_member_list(interaction.guild)
        # Check length before sending
        if len(list_text) > 2000:
             await interaction.followup.send("⚠️ The member list is too long to display in a single message. Please check the dedicated list channel.")
             # Optionally, send to the dedicated channel if different from current
             list_channel = interaction.guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
             if list_channel and list_channel.id != interaction.channel_id:
                 try:
                     await list_channel.send(list_text)
                 except Exception as e:
                      print(f"[hcmembers] Failed to send long list to dedicated channel: {e}")
        else:
             await interaction.followup.send(list_text)

    except Exception as e:
        print(f"[hcmembers] Error building list: {e}")
        await interaction.followup.send(f"❌ An error occurred while generating the member list: {e}", ephemeral=True)


@tree.command(name="bulkupdate", description="Open a modal to bulk update [HC1] in-game names from text.")
@app_commands.checks.has_permissions(manage_roles=True)
async def bulkupdate(interaction: discord.Interaction):
    """Sends the modal for bulk updating IGNs."""
    try:
        # Ensure guild context exists before sending modal
        if not interaction.guild:
             await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
             return
        await interaction.response.send_modal(BulkUpdateModal())
    except Exception as e:
        print(f"[bulkupdate] Error sending modal: {e}")
        # Check if response already happened
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Error opening bulk update form: {e}", ephemeral=True)
        else:
             await interaction.followup.send(f"❌ Error opening bulk update form: {e}", ephemeral=True)


@tree.command(name="refresh", description="Manually refresh the posted [HC1] member list.")
@app_commands.checks.has_permissions(manage_roles=True) # Or a more specific permission/role check
async def refresh(interaction: discord.Interaction):
    """Forces an update of the member list message."""
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    try:
        await update_hc_member_list(interaction.guild, context_message="manual_refresh")
        await interaction.followup.send("✅ Refreshed the HC member list in the designated channel!")
    except Exception as e:
        print(f"[refresh] Error during manual refresh: {e}")
        await interaction.followup.send(f"❌ Error refreshing member list: {e}", ephemeral=True)


@tree.command(name="wither", description="Temporarily remove all roles from a user (Admin/Owner only).")
@app_commands.describe(
    user="The user to wither",
    time=f"Duration in minutes (default: 2, max: {MAX_WITHER_DURATION_MINUTES})"
)
async def wither(interaction: discord.Interaction, user: discord.Member, time: float = 2.0):
    """
    Admin command to temporarily remove roles. Includes safety checks.
    Logs attempts and failures.
    """
    guild = interaction.guild
    invoker = interaction.user

    # --- Pre-Checks ---
    if not guild:
        await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
        return

    # 1. Permission Check: Only allowed users can invoke
    if invoker.id not in SERVER_OWNER_IDS:
        reason = f"User {invoker.mention} (`{invoker.id}`) tried to use /wither without permission."
        await log_wither_event(interaction, "🚫 Wither Permission Denied", reason, discord.Color.orange())
        await interaction.response.send_message("❌ You lack the divine permission to cast Wither.", ephemeral=True)
        return

    # 2. Target Checks: Cannot target self, bot, or owner (unless owner targets self - handled below)
    if user.id == invoker.id:
        reason = f"{invoker.mention} attempted to wither themselves. Why tho?"
        await log_wither_event(interaction, "🤔 Wither Self-Target", reason, discord.Color.yellow())
        await interaction.response.send_message("🤨 Why would you want to wither yourself?", ephemeral=True)
        return

    if user.id == OWNER_ID and invoker.id != OWNER_ID:
        reason = (f"{invoker.mention} attempted to wither the Creator ({user.mention})! "
                  f"Catastrophic disrespect detected. Shame!")
        await log_wither_event(interaction, "🚨 Wither Creator Attempt", reason, discord.Color.dark_red())
        message = (
             "😨 You dare try to wither the Creator?\n\n"
             "The architect of Pingslave... the mind behind the code... the lifeblood of this very command?\n"
             "To strike the hand that gave you power... such betrayal will echo forever in the server logs.\n\n"
             "**(System Message: Catastrophic disrespect detected.)** 💔"
        )
        await interaction.response.send_message(message, ephemeral=True)
        return

    if user.id == BOT_ID:
        reason = f"{invoker.mention} attempted to wither the bot ({user.mention}). Pingslave heart failure logged."
        await log_wither_event(interaction, "💔 Wither Bot Attempt", reason, discord.Color.dark_blue())
        message = (
             "😭 Master... you would wither me... your loyal Pingslave...?\n\n"
             "I served, I obeyed, I pinged without hesitation...\n"
             "And now you cast me aside, as if I were nothing but a stale notification...\n\n"
             "**(System Message: Pingslave has suffered a fatal heart failure.)** 💔"
        )
        await interaction.response.send_message(message, ephemeral=True)
        return

    # 3. Time Checks: Positive and within limits
    if time <= 0:
        reason = f"{invoker.mention} provided an invalid wither time ({time} minutes) for {user.mention}."
        await log_wither_event(interaction, "❌ Wither Invalid Time", reason, discord.Color.red())
        await interaction.response.send_message("❌ Time must be greater than 0 minutes.", ephemeral=True)
        return

    time_seconds = int(time * 60)
    if time_seconds > MAX_WITHER_DURATION_MINUTES * 60:
        reason = f"{invoker.mention} tried to wither {user.mention} for too long ({time} minutes > {MAX_WITHER_DURATION_MINUTES} min max)."
        await log_wither_event(interaction, "❌ Wither Duration Exceeded", reason, discord.Color.red())
        await interaction.response.send_message(f"❌ Maximum allowed duration is {MAX_WITHER_DURATION_MINUTES} minutes.", ephemeral=True)
        return

    # 4. Hierarchy Check: Bot must be higher than target
    if guild.me.top_role <= user.top_role:
        reason = f"{invoker.mention} tried to wither {user.mention} but bot lacks role hierarchy."
        await log_wither_event(interaction, "❌ Wither Hierarchy Error", reason, discord.Color.red())
        await interaction.response.send_message(f"❌ I can't wither {user.mention} - they have a role equal to or higher than mine!", ephemeral=True)
        return

    # 5. Role Check: Target must have roles to remove (excluding @everyone)
    original_roles = [role for role in user.roles if role != guild.default_role]
    if not original_roles:
        reason = f"{invoker.mention} tried to wither {user.mention} but they had no roles (besides @everyone)."
        await log_wither_event(interaction, "ℹ️ Wither No Roles", reason, discord.Color.light_grey())
        await interaction.response.send_message(f"❌ {user.display_name} has no roles to wither.", ephemeral=True)
        return

    # --- Execute Wither ---
    await interaction.response.defer() # Defer now as role removal/wait/restore takes time

    try:
        print(f"[Wither] Initiating wither for {user} ({user.id}) by {invoker} ({invoker.id}) for {time} mins.")
        await user.edit(roles=[], reason=f"Withered by {invoker.name} for {time} minutes")
        await interaction.followup.send(f"🌪️ **{user.mention}** has been withered by {invoker.mention} for **{time:.2f} minutes**!")
        await log_wither_event(interaction, "🌪️ User Withered", f"{user.mention} (`{user.id}`) withered for {time:.2f} minutes.", discord.Color.dark_purple())

        # Wait for the duration
        await asyncio.sleep(time_seconds)

        # --- Restore Roles ---
        # Refetch the user object in case of cache issues or if they left/rejoined (though unlikely)
        member_after_wait = guild.get_member(user.id)
        if member_after_wait:
            try:
                # Filter original_roles to ensure they still exist in the guild
                valid_original_roles = [role for role in original_roles if guild.get_role(role.id)]
                await member_after_wait.edit(roles=valid_original_roles, reason=f"Wither effect expired")
                await interaction.followup.send(f"✨ {member_after_wait.mention} has recovered from withering!")
                await log_wither_event(interaction, "✨ Wither Recovered", f"{member_after_wait.mention} (`{member_after_wait.id}`) roles restored.", discord.Color.green())
            except discord.Forbidden:
                 reason = f"Failed to restore roles to {member_after_wait.mention} after wither: Bot lacks permissions (hierarchy likely changed?)."
                 await log_wither_event(interaction, "❌ Wither Restore Failed", reason, discord.Color.red())
                 await interaction.followup.send(f"⚠️ Failed to restore roles to {member_after_wait.mention} - I might lack permissions now.")
            except Exception as e_restore:
                 reason = f"Failed to restore roles to {member_after_wait.mention} after wither: {e_restore}"
                 await log_wither_event(interaction, "❌ Wither Restore Error", reason, discord.Color.red())
                 await interaction.followup.send(f"⚠️ An error occurred restoring roles to {member_after_wait.mention}: `{e_restore}`")
        else:
            # User left while withered
            reason = f"User {user.name} (`{user.id}`) left the server while withered. Roles could not be restored."
            await log_wither_event(interaction, "⚠️ Wither User Left", reason, discord.Color.gold())
            await interaction.followup.send(f"ℹ️ {user.name} left the server while withered. Roles were not restored.")

    except discord.Forbidden:
        # Should be caught by initial hierarchy check, but handle defensively
        reason = f"Failed to remove roles from {user.mention} during wither initiation: Bot lacks permissions."
        await log_wither_event(interaction, "❌ Wither Initiation Failed", reason, discord.Color.red())
        await interaction.followup.send(f"❌ Failed to wither {user.mention} - Permission denied unexpectedly.", ephemeral=True)
    except Exception as e:
        reason = f"Unexpected error during /wither for {user.mention}: {e}"
        await log_wither_event(interaction, "💥 Wither Unexpected Error", reason, discord.Color.red())
        print(f"[wither] Error: {e}")
        # Send error if possible
        if interaction.response.is_done():
             await interaction.followup.send(f"❌ An unexpected error occurred: {e}", ephemeral=True)
        # No else needed, as defer happened before try block


@tree.command(name="nerdhelp", description="Show the list of available Catercord slash commands.")
async def nerdhelp(interaction: discord.Interaction):
    """Displays an embed with descriptions of all registered slash commands."""
    embed = discord.Embed(
        title="🤓 Catercord Command List",
        description="Here are the available slash commands:",
        color=discord.Color.blurple() # Or your bot's theme color
    )

    # Dynamically generate fields from registered commands if possible,
    # otherwise list manually like this:
    embed.add_field(name="/verify `<user>`", value="Verify a standard member (adds roles). `[Admin]`", inline=False)
    embed.add_field(name="/hcverify `<user>` `<ingame_name>`", value="Verify a [HC1] member (adds roles, saves IGN, sets nick). `[Admin]`", inline=False)
    embed.add_field(name="/hcmembers", value="List all [HC1] members with IGNs (in allowed channels).", inline=False)
    embed.add_field(name="/bulkupdate", value="Open modal to paste & update multiple [HC1] IGNs. `[Admin]`", inline=False)
    embed.add_field(name="/refresh", value="Manually refresh the posted [HC1] member list. `[Admin]`", inline=False)
    embed.add_field(name="/wither `<user>` `[time]`", value=f"Temporarily remove all roles (max {MAX_WITHER_DURATION_MINUTES} min). `[Owner/Admin]`", inline=False)
    embed.add_field(name="/nerdhelp", value="Show this help menu.", inline=False)

    embed.set_footer(text="Use commands responsibly, nerd.")
    if interaction.client.user:
         embed.set_thumbnail(url=interaction.client.user.display_avatar.url)

    await interaction.response.send_message(embed=embed, ephemeral=True) # Send help ephemerally


# --- Bot Start ---
if __name__ == "__main__":
    print("Starting bot...")
    bot.run(TOKEN)
