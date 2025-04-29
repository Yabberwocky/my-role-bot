# -*- coding: utf-8 -*-
import os
import threading
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput
from flask import Flask
from supabase import create_client, Client
import traceback # For detailed error logging

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

# Wither command specific IDs
ALLOWED_WITHER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692}
SELF_PROTECTED_ID = 1230848174218940416
BOT_ID = 1365572437185400893
MAX_WITHER_SECONDS = 600 # 10 minutes

# Log Channel IDs
INFO_LOG_CHANNEL_ID = 1317943895606165579
ERROR_LOG_CHANNEL_ID = 1362988767367135453 # Also used for wither failures/warnings

# --- Supabase Client ---
if SUPABASE_URL and SUPABASE_KEY:
    # Assuming supabase-py > v1.0 for async support
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    # If using older supabase-py or need explicit async, init might differ:
    # from supabase_async import create_client as create_async_client
    # supabase: AsyncClient = create_async_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase client created.") # Keep a simple startup message for console
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
def home():
    return "Bot is alive!"

def run():
    try:
        # Use a larger port if 8080 is causing issues
        app.run(host='0.0.0.0', port=8080)
        print("Flask server started.")
    except Exception as e:
         print(f"Flask server failed to start: {e}") # Log startup issues to console

def keep_alive():
    t = threading.Thread(target=run)
    t.start()
    print("Keep alive thread started.")

# --- Logging Utility Functions ---

async def log_to_channel(channel_id: int, guild: discord.Guild, message: str = None, embed: discord.Embed = None):
    """Sends a log message or embed to a specific channel."""
    if not guild:
        print(f"Log Error: Guild object is missing for channel {channel_id}. Message: {message}")
        return
    log_channel = guild.get_channel(channel_id)
    if log_channel:
        try:
            if embed:
                await log_channel.send(embed=embed)
            elif message:
                # Discord message length limit is 2000 characters
                if len(message) > 2000:
                    await log_channel.send(message[:1997] + "...")
                else:
                    await log_channel.send(message)
        except discord.Forbidden:
            print(f"Log Error: Bot lacks permission to send messages in channel ID {channel_id} ({guild.name}).")
        except Exception as e:
            print(f"Log Error: Failed to send message to channel ID {channel_id} ({guild.name}): {e}")
    else:
        print(f"Log Error: Channel ID {channel_id} not found in guild {guild.name}.")

async def log_info(guild: discord.Guild, message: str, embed: discord.Embed = None):
    """Logs an informational message to the INFO channel."""
    await log_to_channel(INFO_LOG_CHANNEL_ID, guild, message=message, embed=embed)

async def log_error(guild: discord.Guild, message: str, error: Exception = None, interaction: discord.Interaction = None, embed: discord.Embed = None):
    """Logs an error or warning message to the ERROR channel."""
    full_message = f"⚠️ **Error/Warning:** {message}"
    if interaction:
        full_message += f"\n**Context:** Command `/{interaction.command.name if interaction.command else 'N/A'}` by `{interaction.user}` ({interaction.user.id})"
    if error:
        # Get traceback details
        tb_str = traceback.format_exception(type(error), error, error.__traceback__)
        tb_formatted = "".join(tb_str)
        # Keep traceback concise for Discord message
        full_message += f"\n**Details:** `{type(error).__name__}: {str(error)}`"
        # Log full traceback to console for debugging if needed
        print(f"--- ERROR TRACEBACK ---\nGuild: {guild.id}\nContext: {message}\n{tb_formatted}\n--- END TRACEBACK ---")


    # Try sending as embed first if provided
    if embed:
        await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, embed=embed)
    else:
        # Limit message length
        if len(full_message) > 1950: # Leave space for formatting
             full_message = full_message[:1950] + "... (truncated)"
        await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, message=full_message)


# --- Utility Functions ---

async def build_hc_member_list(guild: discord.Guild) -> str:
    """Builds the [HC1] Guild Members list text by fetching data from Supabase."""
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"[build_hc_member_list] Error: [HC1] role ({ADD_ROLE_ID_HC}) not found.")
        return "**Error:** \[HC1\] role not found."

    members_with_role = sorted([m for m in guild.members if hc_role in m.roles], key=lambda m: m.name.lower())

    if not members_with_role:
        return "**\[HC1\] Guild Members:**\nNo members with \[HC1\] role found."

    member_ids = [str(m.id) for m in members_with_role]
    ingame_names = {}

    if supabase and member_ids:
        try:
            # Fetch all names in one query
            response = await supabase.table("hc_members").select("discord_id, ingame_name").in_("discord_id", member_ids).execute()
            if response.data:
                for record in response.data:
                    ingame_names[record['discord_id']] = record.get("ingame_name", "Unknown")
            # Log if Supabase returned data but not for all members? Maybe too noisy.
        except Exception as e:
            await log_error(guild, f"[build_hc_member_list] Error fetching bulk ingame_names from Supabase.", error=e)
            # Indicate failure in the list for all members if the bulk fetch fails
            for member_id in member_ids:
                ingame_names[member_id] = "Error Fetching"

    lines = []
    for idx, member in enumerate(members_with_role, 1):
        ingame_name = ingame_names.get(str(member.id), "Unknown") # Default to Unknown if not found or error occurred
        lines.append(f"{idx}. {member.name} ➔ {ingame_name}")

    return "**\[HC1\] Guild Members:**\n" + "\n".join(lines)


async def update_hc_member_list(guild: discord.Guild):
    """Updates the member list message in the dedicated channel."""
    channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not channel:
        await log_error(guild, f"[update_hc_member_list] Error: Channel ({HC_MEMBER_LIST_CHANNEL_ID}) not found.")
        return

    try:
        list_text = await build_hc_member_list(guild)

        # Attempt to find and edit the last message sent by the bot in the channel
        edited = False
        async for message in channel.history(limit=50): # Check more messages
            if message.author == guild.me and message.content.startswith("**\[HC1\] Guild Members:**"):
                try:
                    await message.edit(content=list_text)
                    await log_info(guild, "[update_hc_member_list] Edited existing list message.")
                    edited = True
                    break # Found and edited
                except discord.NotFound:
                    await log_error(guild, "[update_hc_member_list] Message to edit was deleted before editing.")
                    edited = False # Treat as if not found
                    break
                except discord.Forbidden:
                     await log_error(guild, f"[update_hc_member_list] Error: Bot lacks permissions to edit messages in channel {channel.name}.")
                     edited = False # Fall through to sending new message
                     break
                except Exception as e:
                     await log_error(guild, f"[update_hc_member_list] Error editing message.", error=e)
                     edited = False # Fall through to sending new message
                     break

        if not edited:
            # If no message was found or editing failed, send a new one
            try:
                await channel.send(list_text)
                await log_info(guild, "[update_hc_member_list] Sent new list message.")
            except discord.Forbidden:
                await log_error(guild, f"[update_hc_member_list] Error: Bot lacks permissions to send messages in channel {channel.name}.")
            except Exception as e:
                await log_error(guild, f"[update_hc_member_list] Error sending new message.", error=e)

    except Exception as e:
         await log_error(guild, f"[update_hc_member_list] Unexpected error during update process.", error=e)


# --- Discord Events ---

@bot.event
async def on_ready():
    """Event that fires when the bot is ready."""
    print(f"✅ Logged in as {bot.user}")
    # Sync slash commands
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} command(s).")
        # Log bot readiness to the info channel for each guild it's in
        for guild in bot.guilds:
            await log_info(guild, f"✅ Bot Ready & Commands Synced ({len(synced)} commands).")
            # Optionally trigger initial list update here
            # await update_hc_member_list(guild)
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        # Try logging to error channel if guilds are available
        for guild in bot.guilds:
             await log_error(guild, "Bot failed to sync commands on startup.", error=e)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    """Handles role changes to trigger HC list updates."""
    guild = after.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)

    if not hc_role:
        # Log this error only once perhaps, or less frequently?
        # For now, log every time it's checked and missing during an update event.
        await log_error(guild, f"[on_member_update] HC Role ({ADD_ROLE_ID_HC}) not found, cannot check for list update.")
        return

    # Check if the HC role status changed
    before_has_role = hc_role in before.roles
    after_has_role = hc_role in after.roles

    if before_has_role != after_has_role:
        action = "added to" if after_has_role else "removed from"
        await log_info(guild, f"HC role {action} user `{after.name}` ({after.id}). Triggering list update.")
        # Add a small delay in case multiple roles are updated at once? Usually not necessary.
        # await asyncio.sleep(1)
        await update_hc_member_list(guild)


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for application commands."""
    error_message = "❌ An unexpected error occurred."
    log_message = f"Unhandled error in command '/{interaction.command.name if interaction.command else 'N/A'}'"

    if isinstance(error, app_commands.MissingPermissions):
        missing_perms = ", ".join(error.missing_permissions)
        error_message = f"❌ You don't have the required permissions. Missing: `{missing_perms}`"
        log_message = f"User `{interaction.user}` lacked permissions ({missing_perms}) for `/{interaction.command.name}`."
    elif isinstance(error, app_commands.CheckFailure):
         error_message = "❌ You failed a check required to use this command."
         log_message = f"User `{interaction.user}` failed checks for `/{interaction.command.name}`."
    elif isinstance(error, app_commands.CommandNotFound):
         # Should generally not happen with synced tree, but good practice
         error_message = "❌ Command not found."
         log_message = f"Command `/{interaction.command.name}` not found."
         # No need to log error, Discord handles this visually
         await interaction.response.send_message(error_message, ephemeral=True)
         return # Don't log CommandNotFound as an error
    elif isinstance(error, app_commands.CommandInvokeError):
        # Errors inside the command's code
        original_error = error.original
        error_message = f"❌ An error occurred while executing this command: `{type(original_error).__name__}`"
        log_message = f"Error invoking `/{interaction.command.name}`."
        # Log the original error
        await log_error(interaction.guild, log_message, error=original_error, interaction=interaction)
    else:
        # Other kinds of app command errors
        log_message = f"Unhandled app command error for `/{interaction.command.name}`."
        # Log the unknown error
        await log_error(interaction.guild, log_message, error=error, interaction=interaction)


    # Send feedback to the user if the interaction hasn't been responded to yet
    if not interaction.response.is_done():
        await interaction.response.send_message(error_message, ephemeral=True)
    else:
        # If deferred, use followup
        try:
            await interaction.followup.send(error_message, ephemeral=True)
        except Exception as followup_e:
             # If followup fails (e.g., interaction expired), log that failure too
             await log_error(interaction.guild, f"Failed to send error followup message for `/{interaction.command.name}`.", error=followup_e, interaction=interaction)


# --- Modals ---

class BulkUpdateModal(Modal, title="Bulk Update"):
    """Modal for pasting bulk update data."""
    data = TextInput(label="Paste list (Format: DiscordName ➔ InGameName)", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        """Handles the submission of the bulk update modal."""
        # Interaction Feedback: Defer immediately
        await interaction.response.defer(thinking=True, ephemeral=True) # Ephemeral for results

        guild = interaction.guild
        if not supabase:
            await interaction.followup.send("❌ Supabase is not configured. Cannot perform bulk update.", ephemeral=True)
            await log_error(guild, "Bulk update attempted but Supabase client is not initialized.", interaction=interaction)
            return

        success_count = 0
        update_count = 0
        fail_count = 0
        not_found_count = 0
        errors = []

        lines = self.data.value.strip().splitlines()

        if not lines:
            await interaction.followup.send("⚠️ No data provided in the modal.", ephemeral=True)
            return

        # Fetch all members once for faster lookup
        guild_members = {m.name.lower(): m for m in guild.members}

        # Process each line
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if "➔" not in line:
                if line: # Only log if the line wasn't empty
                    errors.append(f"L{i}: ⚠️ Invalid format: `{line}`")
                continue

            try:
                username, ingame_name = map(str.strip, line.split("➔", 1))
                if not username or not ingame_name:
                    errors.append(f"L{i}: ⚠️ Missing name: `{line}`")
                    continue
            except ValueError:
                 errors.append(f"L{i}: ⚠️ Bad separator: `{line}`")
                 continue

            # Find the member (case-insensitive)
            member = guild_members.get(username.lower())

            if not member:
                fail_count += 1
                not_found_count +=1
                errors.append(f"L{i}: ❌ User `{username}` not found.")
                continue

            try:
                # Use upsert for cleaner insert/update
                # Assumes 'discord_id' is the primary key or has a unique constraint
                # Supabase-py v1+ syntax:
                await supabase.table("hc_members").upsert({
                    "discord_id": str(member.id),
                    "discord_name": member.name, # Store current name
                    "ingame_name": ingame_name
                    # created_at and updated_at handled by DB defaults/triggers
                }).execute()

                # Determine if it was an insert or update is harder with upsert
                # We'll just count total successes
                success_count += 1
                # await log_info(guild, f"Bulk Update: Upserted {member.name} ({member.id}) -> {ingame_name}") # Potentially noisy

            except Exception as e:
                fail_count += 1
                errors.append(f"L{i}: ❌ Failed {member.name}: `{e}`")
                await log_error(guild, f"Bulk update Supabase error for {member.name} ({member.id})", error=e, interaction=interaction)

        # Build the result message
        result_message = (
            f"**Bulk Update Results:**\n"
            f"✅ Successfully Processed: {success_count}\n"
            # f"🔄 Updated Existing: {update_count}\n" # Harder to track with upsert
            f"❌ Failed: {fail_count}\n"
            f"   - User Not Found: {not_found_count}\n"
            f"   - Supabase/Other Errors: {fail_count - not_found_count}\n\n"
        )
        if errors:
             # Show only first few errors in message, log all
             max_errors_to_show = 10
             result_message += "**Issues:**\n" + "\n".join(errors[:max_errors_to_show])
             if len(errors) > max_errors_to_show:
                 result_message += f"\n...and {len(errors) - max_errors_to_show} more issues (see error log channel)."
                 # Ensure all errors were logged individually above

        # Send the result message as a followup
        # Check length before sending
        if len(result_message) > 2000:
             result_message = result_message[:1997] + "..."
        await interaction.followup.send(result_message, ephemeral=True)
        await log_info(guild, f"Bulk update completed by {interaction.user}. Success: {success_count}, Failed: {fail_count}.")

        # Update the public member list after bulk update
        await update_hc_member_list(guild)


# --- Slash Commands ---

@tree.command(name="verify", description="Verify a user into Catercord.")
@app_commands.describe(user="The user to verify")
@app_commands.checks.has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    """Removes the unverified role and adds the verified role."""
    guild = interaction.guild
    remove_role = guild.get_role(REMOVE_ROLE_ID)
    add_role_verify = guild.get_role(ADD_ROLE_ID_VERIFY)
    actions_taken = []

    if not remove_role:
        await log_error(guild, f"/verify: Unverified role ({REMOVE_ROLE_ID}) not found.", interaction=interaction)
    if not add_role_verify:
         await log_error(guild, f"/verify: Verified role ({ADD_ROLE_ID_VERIFY}) not found.", interaction=interaction)

    try:
        if remove_role and remove_role in user.roles:
            await user.remove_roles(remove_role)
            actions_taken.append(f"Removed `{remove_role.name}`")

        if add_role_verify and add_role_verify not in user.roles:
            await user.add_roles(add_role_verify)
            actions_taken.append(f"Added `{add_role_verify.name}`")

        if not actions_taken:
            if not remove_role and not add_role_verify:
                await interaction.response.send_message("❌ Verification roles not found. Cannot perform verification.", ephemeral=True)
            else:
                await interaction.response.send_message(f"ℹ️ No role changes needed for **{user.display_name}**.", ephemeral=True)
        else:
            log_msg = f"User `{interaction.user}` verified `{user.display_name}` ({user.id}). Actions: {', '.join(actions_taken)}."
            await log_info(guild, log_msg)
            await interaction.response.send_message(f"✅ Verified **{user.display_name}**! ({', '.join(actions_taken)})")

    except discord.Forbidden:
        await log_error(guild, "Bot lacks permissions for /verify command.", interaction=interaction)
        await interaction.response.send_message("❌ I don't have permission to manage roles.", ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Error during /verify for {user.display_name}", error=e, interaction=interaction)
        await interaction.response.send_message(f"❌ An error occurred during verification.", ephemeral=True)


@tree.command(name="unverify", description="Revert a user to unverified status.")
@app_commands.describe(user="The user to unverify")
@app_commands.checks.has_permissions(manage_roles=True)
async def unverify(interaction: discord.Interaction, user: discord.Member):
    """Removes verified/adds unverified role. Does NOT affect HC status."""
    guild = interaction.guild
    remove_role = guild.get_role(ADD_ROLE_ID_VERIFY) # Verified role
    add_role = guild.get_role(REMOVE_ROLE_ID) # Unverified role
    actions_taken = []

    if not remove_role:
        await log_error(guild, f"/unverify: Verified role ({ADD_ROLE_ID_VERIFY}) not found.", interaction=interaction)
    if not add_role:
         await log_error(guild, f"/unverify: Unverified role ({REMOVE_ROLE_ID}) not found.", interaction=interaction)

    try:
        # Safety check: Don't unverify the bot or owner? Optional.
        # if user.id == BOT_ID or user.id == guild.owner_id:
        #     await interaction.response.send_message("❌ Cannot unverify this user.", ephemeral=True)
        #     return

        if remove_role and remove_role in user.roles:
            await user.remove_roles(remove_role)
            actions_taken.append(f"Removed `{remove_role.name}`")

        if add_role and add_role not in user.roles:
            await user.add_roles(add_role)
            actions_taken.append(f"Added `{add_role.name}`")

        if not actions_taken:
            if not remove_role and not add_role:
                 await interaction.response.send_message("❌ Verification roles not found. Cannot perform unverification.", ephemeral=True)
            else:
                await interaction.response.send_message(f"ℹ️ No role changes needed for **{user.display_name}**.", ephemeral=True)
        else:
            log_msg = f"User `{interaction.user}` unverified `{user.display_name}` ({user.id}). Actions: {', '.join(actions_taken)}."
            await log_info(guild, log_msg)
            await interaction.response.send_message(f"✅ Unverified **{user.display_name}**! ({', '.join(actions_taken)})")

    except discord.Forbidden:
        await log_error(guild, "Bot lacks permissions for /unverify command.", interaction=interaction)
        await interaction.response.send_message("❌ I don't have permission to manage roles.", ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Error during /unverify for {user.display_name}", error=e, interaction=interaction)
        await interaction.response.send_message(f"❌ An error occurred during unverification.", ephemeral=True)


@tree.command(name="hcverify", description="Verify a user into [HC1], store IGN, and set nickname.")
@app_commands.describe(user="The user to HC verify", ingame_name="Their Florr.io in-game name")
@app_commands.checks.has_permissions(manage_roles=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    """Adds roles, stores/updates IGN in Supabase, updates nickname."""
    # Interaction Feedback: Defer
    await interaction.response.defer(thinking=True)
    guild = interaction.guild

    if not supabase:
        await interaction.followup.send("❌ Supabase is not configured. Cannot perform HC verification.", ephemeral=True)
        await log_error(guild, "HC verify attempted but Supabase client is not initialized.", interaction=interaction)
        return

    remove_role = guild.get_role(REMOVE_ROLE_ID)
    add_role_verify = guild.get_role(ADD_ROLE_ID_VERIFY)
    add_role_hc = guild.get_role(ADD_ROLE_ID_HC)
    roles_to_add = []
    actions_taken = []
    nickname_status = ""

    # Role checks
    if not add_role_verify: await log_error(guild, f"/hcverify: Verified role ({ADD_ROLE_ID_VERIFY}) not found.", interaction=interaction)
    if not add_role_hc: await log_error(guild, f"/hcverify: HC role ({ADD_ROLE_ID_HC}) not found.", interaction=interaction)
    # Don't strictly need remove_role here, but good to know if it exists
    if not remove_role: await log_info(guild, f"/hcverify: Unverified role ({REMOVE_ROLE_ID}) not found (informational).")


    try:
        # 1. Handle Roles
        if remove_role and remove_role in user.roles:
            await user.remove_roles(remove_role)
            actions_taken.append(f"Removed `{remove_role.name}`")

        if add_role_verify and add_role_verify not in user.roles:
             roles_to_add.append(add_role_verify)
        if add_role_hc and add_role_hc not in user.roles:
             roles_to_add.append(add_role_hc)

        if roles_to_add:
            await user.add_roles(*roles_to_add)
            added_names = ', '.join([f"`{r.name}`" for r in roles_to_add])
            actions_taken.append(f"Added {added_names}")


        # 2. Store/Update in Supabase using upsert
        try:
            # Assuming execute() needs await and supabase-py v1+ upsert syntax
            await supabase.table("hc_members").upsert({
                "discord_id": str(user.id),
                "discord_name": user.name,
                "ingame_name": ingame_name
            }).execute()
            actions_taken.append("Updated Supabase record")
        except Exception as e:
            await log_error(guild, f"Supabase upsert failed during /hcverify for {user.display_name}", error=e, interaction=interaction)
            # Decide if this is fatal - for now, continue to nickname change but report error
            actions_taken.append("⚠️ Supabase update failed")


        # 3. Attempt to change nickname
        target_nick = ingame_name
        if len(ingame_name) > 32:
             target_nick = ingame_name[:32]
             nickname_status = " (Nickname truncated)"
             await log_info(guild, f"Nickname truncated for {user.display_name}: '{ingame_name}' -> '{target_nick}'")

        # Check if nickname change is actually needed
        if user.nick != target_nick:
            try:
                await user.edit(nick=target_nick)
                actions_taken.append("Updated nickname")
            except discord.Forbidden:
                nickname_status = " (⚠️ Failed to change nickname - permissions)"
                await log_error(guild, f"Bot lacks permissions to change nickname for {user.display_name} during /hcverify.", interaction=interaction)
                actions_taken.append("Nickname update failed (perms)")
            except Exception as e:
                nickname_status = f" (⚠️ Failed to change nickname - {type(e).__name__})"
                await log_error(guild, f"Nickname change failed during /hcverify for {user.display_name}", error=e, interaction=interaction)
                actions_taken.append("Nickname update failed (error)")
        else:
            actions_taken.append("Nickname already correct")


        # 4. Send Followup Response & Log
        log_msg = f"User `{interaction.user}` HC verified `{user.display_name}` ({user.id}) as IGN `{ingame_name}`. Actions: {'; '.join(actions_taken)}."
        await log_info(guild, log_msg)
        await interaction.followup.send(f"✅ HC verified **{user.display_name}** as **{ingame_name}**!{nickname_status}", ephemeral=False)

        # 5. Update list (implicitly handled by on_member_update if role was added)
        # However, call it explicitly if the role *wasn't* added but IGN/nickname might have changed.
        if add_role_hc not in roles_to_add: # If they already had the HC role
            await update_hc_member_list(guild)


    except discord.Forbidden:
        # This catches permission errors during role changes specifically
        await log_error(guild, "Bot lacks permissions for role management in /hcverify.", interaction=interaction)
        await interaction.followup.send("❌ I don't have permission to manage roles.", ephemeral=True)
    except Exception as e:
        # Catch any other unexpected errors during the HC verify process
        await log_error(guild, f"Unexpected error during /hcverify for {user.display_name}", error=e, interaction=interaction)
        await interaction.followup.send(f"❌ An unexpected error occurred during HC verification.", ephemeral=True)


@tree.command(name="unhcverify", description="Remove [HC1] role and reset nickname for a user.")
@app_commands.describe(user="The user to remove from HC.")
@app_commands.checks.has_permissions(manage_roles=True)
async def unhcverify(interaction: discord.Interaction, user: discord.Member):
    """Removes HC role, resets nickname. Does NOT remove from Supabase or unverify."""
    # No defer needed, usually fast enough
    guild = interaction.guild
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    actions_taken = []
    nickname_status = ""

    if not hc_role:
        await log_error(guild, f"/unhcverify: HC role ({ADD_ROLE_ID_HC}) not found.", interaction=interaction)
        await interaction.response.send_message("❌ HC Role not found, cannot perform un-HC-verification.", ephemeral=True)
        return

    try:
        # 1. Remove HC Role
        if hc_role in user.roles:
            await user.remove_roles(hc_role)
            actions_taken.append(f"Removed `{hc_role.name}`")
        else:
            await interaction.response.send_message(f"ℹ️ **{user.display_name}** does not have the `{hc_role.name}` role.", ephemeral=True)
            return # Nothing more to do if they don't have the role

        # 2. Reset Nickname
        if user.nick is not None: # Only reset if they have a nickname set
            try:
                await user.edit(nick=None)
                actions_taken.append("Reset nickname")
            except discord.Forbidden:
                nickname_status = " (⚠️ Failed to reset nickname - permissions)"
                await log_error(guild, f"Bot lacks permissions to reset nickname for {user.display_name} during /unhcverify.", interaction=interaction)
                actions_taken.append("Nickname reset failed (perms)")
            except Exception as e:
                nickname_status = f" (⚠️ Failed to reset nickname - {type(e).__name__})"
                await log_error(guild, f"Nickname reset failed during /unhcverify for {user.display_name}", error=e, interaction=interaction)
                actions_taken.append("Nickname reset failed (error)")
        else:
             actions_taken.append("No nickname to reset")


        # 3. Send Response & Log
        log_msg = f"User `{interaction.user}` un-HC-verified `{user.display_name}` ({user.id}). Actions: {'; '.join(actions_taken)}."
        await log_info(guild, log_msg)
        await interaction.response.send_message(f"✅ Removed **{user.display_name}** from HC!{nickname_status}", ephemeral=False)

        # 4. Update list (implicitly handled by on_member_update)

    except discord.Forbidden:
        # This catches permission errors during role removal
        await log_error(guild, "Bot lacks permissions for role management in /unhcverify.", interaction=interaction)
        if not interaction.response.is_done(): # Check if response already sent
            await interaction.response.send_message("❌ I don't have permission to manage roles.", ephemeral=True)
        else: # Should not happen if role check fails first, but safety
             await interaction.followup.send("❌ I don't have permission to manage roles.", ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Unexpected error during /unhcverify for {user.display_name}", error=e, interaction=interaction)
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ An unexpected error occurred.", ephemeral=True)
        else:
             await interaction.followup.send(f"❌ An unexpected error occurred.", ephemeral=True)


@tree.command(name="hcmembers", description="List all [HC1] members with their in-game names.")
async def hcmembers(interaction: discord.Interaction):
    """Lists all members with the [HC1] role and their IGNs from Supabase."""
    guild = interaction.guild
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        await interaction.response.send_message("❌ This command can only be used in specific channels.", ephemeral=True)
        await log_info(guild, f"User {interaction.user} tried /hcmembers in disallowed channel {interaction.channel.name}.")
        return

    # Interaction Feedback: Defer
    await interaction.response.defer(thinking=True)

    if not supabase:
        await interaction.followup.send("❌ Supabase is not configured. Cannot retrieve member list.", ephemeral=True)
        await log_error(guild, "/hcmembers attempted but Supabase client is not initialized.", interaction=interaction)
        return

    try:
        list_text = await build_hc_member_list(guild)
        # Send the list as a followup
        # Handle potential length limit for messages (2000 chars)
        if len(list_text) > 2000:
             # Send first part
             await interaction.followup.send(list_text[:2000])
             # Send subsequent parts in new messages
             remaining_text = list_text[2000:]
             while remaining_text:
                 await interaction.channel.send(remaining_text[:2000]) # Send to channel directly
                 remaining_text = remaining_text[2000:]
        else:
            await interaction.followup.send(list_text)

        await log_info(guild, f"/hcmembers generated list in channel {interaction.channel.name}.")
    except Exception as e:
        await log_error(guild, "[hcmembers] Error building/sending list.", error=e, interaction=interaction)
        # Check if followup possible before sending error message
        if not interaction.response.is_done(): # Should always be done due to defer
             await interaction.followup.send(f"❌ An error occurred while fetching the member list.", ephemeral=True)


@tree.command(name="bulkupdate", description="Bulk update user in-game names via modal.")
@app_commands.checks.has_permissions(manage_roles=True) # Assuming manage_roles is proxy for this permission
async def bulkupdate(interaction: discord.Interaction):
    """Opens a modal to accept bulk update data."""
    try:
        await interaction.response.send_modal(BulkUpdateModal())
        await log_info(interaction.guild, f"Opened bulk update modal for {interaction.user}.")
    except Exception as e:
        await log_error(interaction.guild, "Error opening bulk update modal.", error=e, interaction=interaction)
        # Check if response is possible
        if not interaction.response.is_done():
             await interaction.response.send_message(f"❌ An error occurred while opening the modal.", ephemeral=True)


@tree.command(name="refresh", description="Refresh the [HC1] member list manually.")
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    """Manually triggers an update of the HC member list message."""
    # Interaction Feedback: Defer
    await interaction.response.defer(thinking=True, ephemeral=True) # Ephemeral response okay
    guild = interaction.guild

    if not supabase:
        await interaction.followup.send("❌ Supabase is not configured. Cannot refresh member list.", ephemeral=True)
        await log_error(guild, "/refresh attempted but Supabase client is not initialized.", interaction=interaction)
        return

    try:
        await update_hc_member_list(guild)
        await interaction.followup.send("✅ Refreshed the HC member list!")
        await log_info(guild, f"Manually refreshed HC member list via /refresh by {interaction.user}.")
    except Exception as e:
        await log_error(guild, "Error during manual /refresh.", error=e, interaction=interaction)
        await interaction.followup.send(f"❌ An error occurred while refreshing the member list.", ephemeral=True)


@tree.command(name="syncnicknames", description="Sync all HC members' nicknames with their stored IGN.")
@app_commands.checks.has_permissions(manage_roles=True)
async def syncnicknames(interaction: discord.Interaction):
    """Iterates HC members, fetches IGN, updates nickname if needed."""
    # Interaction Feedback: Defer Ephemeral
    await interaction.response.defer(thinking=True, ephemeral=True)
    guild = interaction.guild

    if not supabase:
        await interaction.followup.send("❌ Supabase is not configured. Cannot sync nicknames.", ephemeral=True)
        await log_error(guild, "/syncnicknames attempted but Supabase client is not initialized.", interaction=interaction)
        return

    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        await log_error(guild, f"/syncnicknames: HC role ({ADD_ROLE_ID_HC}) not found.", interaction=interaction)
        await interaction.followup.send("❌ HC Role not found, cannot sync nicknames.", ephemeral=True)
        return

    await log_info(guild, f"Starting nickname sync triggered by {interaction.user}.")
    await interaction.edit_original_response(content="🔄 Fetching HC members and IGN data...")

    # Fetch Supabase data
    ign_data = {}
    try:
        response = await supabase.table("hc_members").select("discord_id, ingame_name").execute()
        if response.data:
            ign_data = {item['discord_id']: item['ingame_name'] for item in response.data if item.get('ingame_name')}
        await log_info(guild, f"Fetched {len(ign_data)} records from Supabase for nickname sync.")
    except Exception as e:
         await log_error(guild, "Failed to fetch Supabase data for /syncnicknames.", error=e, interaction=interaction)
         await interaction.edit_original_response(content="❌ Failed to fetch data from Supabase. Aborting.")
         return

    success_count = 0
    skipped_count = 0
    no_ign_count = 0
    no_member_count = 0 # If Supabase has IDs for members no longer in server
    perm_error_count = 0
    other_error_count = 0
    members_processed = 0

    hc_members_in_guild = [m for m in guild.members if hc_role in m.roles]
    total_hc_members = len(hc_members_in_guild)

    await interaction.edit_original_response(content=f"🔄 Syncing nicknames for {total_hc_members} members with HC role...")

    # Iterate through guild members with HC role
    for i, member in enumerate(hc_members_in_guild):
        members_processed += 1
        member_id_str = str(member.id)

        # Edit response periodically to show progress
        if i % 25 == 0 and i > 0: # Update every 25 members
             await interaction.edit_original_response(content=f"🔄 Syncing nicknames... ({i}/{total_hc_members})")


        if member_id_str not in ign_data:
            no_ign_count += 1
            await log_info(guild, f"SyncNick: Member `{member.name}` ({member_id_str}) has HC role but no IGN found in Supabase.")
            continue # Skip to next member

        ingame_name = ign_data[member_id_str]
        target_nick = ingame_name[:32] # Truncate if needed

        if member.nick == target_nick:
            skipped_count += 1
            continue # Nickname already correct

        # Attempt nickname change
        try:
            await member.edit(nick=target_nick)
            success_count += 1
            # await log_info(guild, f"SyncNick: Updated nickname for {member.name} to '{target_nick}'.") # Too noisy?
        except discord.Forbidden:
            perm_error_count += 1
            await log_error(guild, f"SyncNick: Permission error updating nickname for {member.name} ({member_id_str}).", interaction=interaction)
        except Exception as e:
            other_error_count += 1
            await log_error(guild, f"SyncNick: Error updating nickname for {member.name} ({member_id_str}).", error=e, interaction=interaction)

    # Final Report
    summary = (
        f"**Nickname Sync Complete!**\n\n"
        f"Processed Members with HC Role: {members_processed}\n"
        f"✅ Nicknames Updated: {success_count}\n"
        f"ℹ️ Nicknames Already Correct: {skipped_count}\n"
        f"⚠️ Members Missing IGN in DB: {no_ign_count}\n"
        f"❌ Permission Errors: {perm_error_count}\n"
        f"❌ Other Errors: {other_error_count}\n"
        # f"👻 Members in DB but not Server: {no_member_count}" # Harder to track this way
    )
    await interaction.edit_original_response(content=summary)
    await log_info(guild, f"Nickname sync finished. Updated: {success_count}, Skipped: {skipped_count}, No IGN: {no_ign_count}, Perm Errors: {perm_error_count}, Other Errors: {other_error_count}.")


@tree.command(name="wither", description="Temporarily remove all roles from a user.")
@app_commands.describe(user="The user to wither", time="Time (in minutes, defaults to 2, max 10)")
async def wither(interaction: discord.Interaction, user: discord.Member, time: float = 2.0):
    """Temporarily removes all roles from a user."""
    guild = interaction.guild
    interaction_user = interaction.user

    # Wrapper for logging wither failures
    async def wither_fail_log(reason: str):
         await log_error(guild, f"Wither Failure: {reason}", interaction=interaction)

    # Permission check
    if interaction_user.id not in ALLOWED_WITHER_IDS:
        await wither_fail_log(f"User `{interaction_user}` lacks permission.")
        await interaction.response.send_message("❌ You lack the divine permission to cast Wither.", ephemeral=True)
        return

    # Protected user checks
    if user.id == interaction_user.id:
        await wither_fail_log("User attempted self-wither.")
        await interaction.response.send_message("🤨 Why would you want to wither yourself?", ephemeral=True)
        return
    if user.id == SELF_PROTECTED_ID and interaction_user.id != SELF_PROTECTED_ID:
        await wither_fail_log(f"User attempted to wither the Creator ({user.id}).")
        await interaction.response.send_message("😨 You dare try to wither the Creator?... Catastrophic disrespect detected.", ephemeral=True)
        return
    if user.id == BOT_ID:
        await wither_fail_log("User attempted to wither the bot.")
        await interaction.response.send_message("😭 Master... you would wither me...? Pingslave has suffered a fatal heart failure.", ephemeral=True)
        return

    # Time validation
    if time <= 0:
        await wither_fail_log(f"Invalid time provided ({time}).")
        await interaction.response.send_message("❌ Time must be greater than 0 minutes.", ephemeral=True)
        return

    time_seconds = int(time * 60)
    if time_seconds > MAX_WITHER_SECONDS:
        await wither_fail_log(f"Time ({time} min) exceeds max ({MAX_WITHER_SECONDS/60:.0f} min).")
        await interaction.response.send_message(f"❌ Maximum allowed duration is {MAX_WITHER_SECONDS/60:.0f} minutes.", ephemeral=True)
        return

    # Role hierarchy check
    if guild.me.top_role <= user.top_role:
        await wither_fail_log(f"Bot role is not high enough to wither {user.name}.")
        await interaction.response.send_message("❌ I can't wither someone mightier than myself!", ephemeral=True)
        return

    # Save roles (exclude @everyone)
    original_roles = [role for role in user.roles if role != guild.default_role]
    if not original_roles:
        await wither_fail_log(f"User {user.name} has no roles to remove.")
        await interaction.response.send_message(f"❌ {user.display_name} has no roles to wither.", ephemeral=True)
        return

    # Perform the withering
    try:
        await user.edit(roles=[]) # Remove all roles
        await interaction.response.send_message(f"🌪️ {user.mention} has been withered by {interaction_user.mention} for {time:.2f} minutes!")
        await log_info(guild, f"User `{user.name}` ({user.id}) withered by `{interaction_user.name}` for {time:.2f} minutes. Roles removed: {', '.join([r.name for r in original_roles])}")

        # Wait
        await asyncio.sleep(time_seconds)

        # Restore roles - requires re-fetching the member object in case they left/rejoined?
        # Fetching member again ensures we have the latest state.
        try:
             member_after_wait = await guild.fetch_member(user.id)
             if member_after_wait: # Check if they are still in the guild
                 await member_after_wait.edit(roles=original_roles)
                 await interaction.followup.send(f"✨ {user.mention} has recovered from withering!")
                 await log_info(guild, f"Restored roles for `{user.name}` ({user.id}).")
             else: # User left while withered
                 await log_info(guild, f"User `{user.name}` ({user.id}) left the server before roles could be restored.")
                 # No followup needed if user is gone
        except discord.NotFound:
             # fetch_member failed, user is not in guild
             await log_info(guild, f"User `{user.name}` ({user.id}) could not be found (likely left) before roles restored.")
        except discord.Forbidden:
             await log_error(guild, f"Bot lacked permissions to restore roles for {user.name} after withering.", interaction=interaction)
             await interaction.followup.send(f"⚠️ Failed to restore roles to {user.mention} due to permissions!", ephemeral=True)
        except Exception as e:
            await log_error(guild, f"Failed to restore roles for {user.name} after wither.", error=e, interaction=interaction)
            await interaction.followup.send(f"⚠️ An error occurred restoring roles to {user.mention}.", ephemeral=True)

    except discord.Forbidden:
        await log_error(guild, f"Bot lacked permissions to remove roles from {user.name} during wither.", interaction=interaction)
        if not interaction.response.is_done(): # Should be done, but safety check
             await interaction.response.send_message("❌ I don't have permission to remove roles from this user.", ephemeral=True)
        else: # Should not happen often
             await interaction.followup.send("❌ Failed to remove roles due to permissions.", ephemeral=True)
    except Exception as e:
        await log_error(guild, f"Unexpected error during /wither for {user.name}.", error=e, interaction=interaction)
        if not interaction.response.is_done():
             await interaction.response.send_message(f"❌ An unexpected error occurred during withering.", ephemeral=True)
        else:
             await interaction.followup.send(f"❌ An unexpected error occurred during withering.", ephemeral=True)


@tree.command(name="nerdhelp", description="Show Catercord slash commands help menu.")
async def nerdhelp(interaction: discord.Interaction):
    """Displays an embed listing available slash commands."""
    guild = interaction.guild
    embed = discord.Embed(
        title="🤓 Catercord Command List",
        description="Here's what you can do with the bot:",
        color=discord.Color.blurple()
    )
    # Fetch role names for clarity if possible
    verify_role = guild.get_role(ADD_ROLE_ID_VERIFY)
    unverify_role = guild.get_role(REMOVE_ROLE_ID)
    hc_role = guild.get_role(ADD_ROLE_ID_HC)

    # Permissions Note
    perm_note = "(Requires Manage Roles)"

    # Build fields dynamically
    embed.add_field(name="/verify <user>", value=f"Verify a member (Adds `{verify_role.name if verify_role else ADD_ROLE_ID_VERIFY}`, removes `{unverify_role.name if unverify_role else REMOVE_ROLE_ID}`). {perm_note}", inline=False)
    embed.add_field(name="/unverify <user>", value=f"Unverify a member (Adds `{unverify_role.name if unverify_role else REMOVE_ROLE_ID}`, removes `{verify_role.name if verify_role else ADD_ROLE_ID_VERIFY}`). {perm_note}", inline=False)
    embed.add_field(name="/hcverify <user> <ingame_name>", value=f"Verify member into HC (Adds `{hc_role.name if hc_role else ADD_ROLE_ID_HC}`), stores IGN, sets nickname. {perm_note}", inline=False)
    embed.add_field(name="/unhcverify <user>", value=f"Remove HC status (Removes `{hc_role.name if hc_role else ADD_ROLE_ID_HC}`, resets nickname). {perm_note}", inline=False)
    embed.add_field(name="/hcmembers", value=f"List all members with `{hc_role.name if hc_role else ADD_ROLE_ID_HC}` role and their IGNs. Usable in specific channels.", inline=False)
    embed.add_field(name="/bulkupdate", value=f"Open modal to bulk update/add IGNs for users. {perm_note}", inline=False)
    embed.add_field(name="/refresh", value=f"Manually refresh the HC member list message in channel {HC_MEMBER_LIST_CHANNEL_ID}. {perm_note}", inline=False)
    embed.add_field(name="/syncnicknames", value=f"Sync nicknames for all members with `{hc_role.name if hc_role else ADD_ROLE_ID_HC}` role based on stored IGNs. {perm_note}", inline=False)
    embed.add_field(name="/wither <user> [time]", value=f"Temporarily remove all roles from a user (Max {MAX_WITHER_SECONDS/60:.0f} mins). Requires special permission.", inline=False)
    embed.add_field(name="/nerdhelp", value="Show this help menu.", inline=False)

    embed.set_footer(text="Use commands responsibly, nerd.")
    if interaction.client.user.display_avatar:
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)


# --- Bot Startup ---
keep_alive() # Start Flask keep-alive thread

if TOKEN:
    if supabase: # Check if Supabase client was successfully created
        try:
            print("Starting Bot...")
            bot.run(TOKEN)
        except Exception as e:
             print(f"CRITICAL: Bot failed to run: {e}")
             # Attempt to log fatal error to Discord if possible? Unlikely to work here.
    else:
        print("CRITICAL: Supabase credentials missing or client creation failed. Bot will not start as Supabase is required.")
else:
    print("CRITICAL: DISCORD_BOT_TOKEN environment variable not set. Bot will not start.")
