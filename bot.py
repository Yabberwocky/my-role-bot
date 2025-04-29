import os
import threading
import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput
from flask import Flask
from supabase import create_client, Client
# Assuming the Supabase client library supports async operations.
# If not, you might need an async-specific wrapper or library.
# For now, we'll add comments assuming async support might be available or needed.

# --- Configuration ---
# Load environment variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Define Role and Channel IDs
# It's good practice to store these clearly at the top
REMOVE_ROLE_ID = 1360176495947022447 # Example: Unverified role ID
ADD_ROLE_ID_VERIFY = 1248708073019805717 # Example: Verified role ID
ADD_ROLE_ID_HC = 1230235110415274004 # Example: [HC1] role ID

# Allowed Channel IDs for /hcmembers command
ALLOWED_CHANNEL_IDS = {1354431395140731165, 1330664430148780102, 1248710731407560835} # Example channel IDs

# Channel ID for the HC member list message
HC_MEMBER_LIST_CHANNEL_ID = 1354431395140731165 # Example channel ID

# Wither command specific IDs
# Ensure these IDs are correct for your server
ALLOWED_WITHER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692} # IDs of users allowed to use /wither
SELF_PROTECTED_ID = 1230848174218940416 # Your own ID or owner ID to prevent self-withering
BOT_ID = 1365572437185400893 # Your bot's ID
WITHER_LOG_CHANNEL_ID = 1362988767367135453 # Channel to log wither attempts/failures

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Supabase Client ---
# Check if environment variables are set before creating client
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logging.info("Supabase client created.")
else:
    logging.error("SUPABASE_URL or SUPABASE_KEY not set. Supabase functionality will be disabled.")
    supabase = None # Set supabase to None if credentials are missing

# --- Discord Setup ---
# Define intents - members intent is required for accessing guild members
intents = discord.Intents.default()
intents.members = True
# intents.message_content = True # Uncomment if you need to read message content
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree # Sync command tree

# --- Flask App for Keep Alive ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    # Use a larger port if 8080 is causing issues in your hosting environment
    app.run(host='0.0.0.0', port=8080)
    logging.info("Flask server started.")

def keep_alive():
    # Run the Flask app in a separate thread
    t = threading.Thread(target=run)
    t.start()
    logging.info("Keep alive thread started.")

# --- Utility Functions ---

async def log_wither_failure(guild: discord.Guild, reason: str, interaction_user: discord.User):
    """Logs wither command failures to a specific channel."""
    log_channel = guild.get_channel(WITHER_LOG_CHANNEL_ID)
    if log_channel:
        try:
            embed = discord.Embed(title="⚠️ Wither Attempt Failed", description=reason, color=discord.Color.red())
            embed.set_footer(text=f"Attempted by: {interaction_user} ({interaction_user.id})")
            await log_channel.send(embed=embed)
            logging.warning(f"Wither failure logged: {reason} by {interaction_user.id}")
        except Exception as e:
            logging.error(f"Failed to send wither failure log message: {e}")
    else:
        logging.warning(f"Wither failure occurred but log channel not found: {reason} by {interaction_user.id}")


async def build_hc_member_list(guild: discord.Guild) -> str:
    """Builds the [HC1] Guild Members list text by fetching data from Supabase."""
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role:
        logging.error(f"[build_hc_member_list] Error: [HC1] role ({ADD_ROLE_ID_HC}) not found.")
        return "**Error:** \[HC1\] role not found."

    # Filter members who actually have the HC role
    members = sorted([m for m in guild.members if hc_role in m.roles], key=lambda m: m.name.lower())

    if not members:
        return "No members with \[HC1\] role found."

    lines = []
    for idx, member in enumerate(members, 1):
        ingame_name = "Unknown"
        if supabase:
            try:
                # Assuming the Supabase client's execute() method is awaited for async
                response = supabase.table("hc_members").select("ingame_name").eq("discord_id", str(member.id)).maybe_single().execute()
                # Check response structure based on your Supabase library version/behavior
                if response and response.data:
                     ingame_name = response.data.get("ingame_name", "Unknown")
                else:
                    logging.warning(f"[build_hc_member_list] Supabase returned no data for {member.name} ({member.id}).")

            except Exception as e:
                logging.error(f"[build_hc_member_list] Error fetching ingame_name for {member.name} ({member.id}): {e}")
                ingame_name = "Error Fetching" # Indicate failure in the list

        lines.append(f"{idx}. {member.name} ➔ {ingame_name}")

    return "**\[HC1\] Guild Members:**\n" + "\n".join(lines)


async def update_hc_member_list(guild: discord.Guild):
    """Updates the member list message in the dedicated channel."""
    channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not channel:
        logging.error(f"[update_hc_member_list] Error: Channel ({HC_MEMBER_LIST_CHANNEL_ID}) not found.")
        return

    list_text = await build_hc_member_list(guild)

    # Attempt to find and edit the last message sent by the bot in the channel
    try:
        async for message in channel.history(limit=20): # Check recent messages
            if message.author == guild.me and message.content.startswith("**\[HC1\] Guild Members:**"):
                await message.edit(content=list_text)
                logging.info("[update_hc_member_list] Edited existing list message.")
                return # Found and edited, so we're done

    except discord.Forbidden:
        logging.error(f"[update_hc_member_list] Error: Bot lacks permissions to read message history or edit messages in channel {channel.name}.")
        # Fall through to sending a new message if editing fails due to permissions

    except Exception as e:
        logging.error(f"[update_hc_member_list] Error searching/editing message history: {e}")
        # Fall through to sending a new message on other errors

    # If no message was found or editing failed, send a new one
    try:
        await channel.send(list_text)
        logging.info("[update_hc_member_list] Sent new list message.")
    except discord.Forbidden:
        logging.error(f"[update_hc_member_list] Error: Bot lacks permissions to send messages in channel {channel.name}.")
    except Exception as e:
        logging.error(f"[update_hc_member_list] Error sending new message: {e}")


# --- Discord Events ---

@bot.event
async def on_ready():
    """Event that fires when the bot is ready."""
    logging.info(f"✅ Logged in as {bot.user}")
    # Sync slash commands to make them available in Discord
    try:
        synced = await tree.sync()
        logging.info(f"Synced {len(synced)} command(s).")
    except Exception as e:
        logging.error(f"Failed to sync commands: {e}")

    # Optionally update the member list on bot startup
    # This might require the bot to be in a guild context,
    # so you might need to get a specific guild object here.
    # Example (assuming the bot is only in one guild or you know the ID):
    # guild_id_to_update = YOUR_GUILD_ID
    # guild = bot.get_guild(guild_id_to_update)
    # if guild:
    #     await update_hc_member_list(guild)
    # else:
    #     logging.warning(f"Guild with ID {guild_id_to_update} not found on startup for list update.")


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for application commands."""
    if isinstance(error, app_commands.MissingPermissions):
        # Handle missing permissions specifically
        missing_perms = ", ".join(error.missing_permissions)
        await interaction.response.send_message(f"❌ You don't have the required permissions to use this command. Missing: `{missing_perms}`", ephemeral=True)
        logging.warning(f"User {interaction.user} ({interaction.user.id}) attempted to use command /{interaction.command.name} but was missing permissions: {missing_perms}")
    elif isinstance(error, app_commands.CheckFailure):
         # Handle other check failures (like custom checks if you add them)
         await interaction.response.send_message("❌ You failed a check required to use this command.", ephemeral=True)
         logging.warning(f"User {interaction.user} ({interaction.user.id}) failed a check for command /{interaction.command.name}.")
    elif isinstance(error, app_commands.CommandInvokeError):
        # Handle errors that occur during command execution
        logging.error(f"Error invoking command /{interaction.command.name}: {error.original}")
        # Provide a generic error message to the user
        await interaction.response.send_message("❌ An error occurred while executing this command.", ephemeral=True)
    else:
        # Handle any other unexpected app command errors
        logging.error(f"Unhandled app command error: {error}", exc_info=True) # Log exception details
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)


# --- Modals ---

class BulkUpdateModal(Modal, title="Bulk Update"):
    """Modal for pasting bulk update data."""
    data = TextInput(label="Paste the list below (Format: DiscordName ➔ InGameName)", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        """Handles the submission of the bulk update modal."""
        await interaction.response.defer(thinking=True) # Acknowledge the interaction

        if not supabase:
            await interaction.followup.send("❌ Supabase is not configured. Cannot perform bulk update.", ephemeral=True)
            logging.error("Bulk update attempted but Supabase client is not initialized.")
            return

        success_count = 0
        fail_count = 0
        errors = []

        lines = self.data.value.strip().splitlines()

        if not lines:
            await interaction.followup.send("⚠️ No data provided in the modal.", ephemeral=True)
            return

        # Process each line
        for line in lines:
            line = line.strip()
            if "➔" not in line:
                if line: # Only log if the line wasn't empty
                    errors.append(f"⚠️ Skipping invalid line format: `{line}`")
                    logging.warning(f"Bulk update skipped invalid line: {line}")
                continue

            try:
                username, ingame_name = map(str.strip, line.split("➔", 1))
            except ValueError:
                 errors.append(f"⚠️ Skipping line with incorrect separator usage: `{line}`")
                 logging.warning(f"Bulk update skipped line with incorrect separator: {line}")
                 continue

            # Find the member in the guild by username (case-insensitive)
            member = discord.utils.find(lambda m: m.name.lower() == username.lower(), interaction.guild.members)

            if not member:
                fail_count += 1
                errors.append(f"❌ User `{username}` not found in the server.")
                logging.warning(f"Bulk update user not found: {username}")
                continue

            try:
                # Attempt to insert or update the record in Supabase
                # Using upsert might be a cleaner approach if your Supabase version supports it easily
                # For now, sticking to the original logic of insert and catching duplicate
                # Assuming execute() needs await
                response = supabase.table("hc_members").insert({
                    "discord_id": str(member.id),
                    "discord_name": member.name, # Store current name, but ID is primary key
                    "ingame_name": ingame_name
                }).execute()
                success_count += 1
                logging.info(f"Bulk update: Inserted {member.name} ({member.id}) with ingame name {ingame_name}")

            except Exception as e:
                error_str = str(e)
                # Check for specific duplicate key error messages
                if "duplicate key value" in error_str or '"hc_members_discord_id_key"' in error_str or "23505" in error_str: # 23505 is the PostgreSQL unique violation error code
                    try:
                        # If duplicate, attempt to update the existing record
                        # Assuming execute() needs await
                        update_response = supabase.table("hc_members").update({"ingame_name": ingame_name}).eq("discord_id", str(member.id)).execute()
                        success_count += 1 # Count as success since update worked
                        logging.info(f"Bulk update: Updated {member.name} ({member.id}) with ingame name {ingame_name}")
                    except Exception as update_e:
                        fail_count += 1
                        errors.append(f"❌ Failed to update existing record for {member.name}: {update_e}")
                        logging.error(f"Bulk update failed to update {member.name} ({member.id}): {update_e}")
                else:
                    fail_count += 1
                    errors.append(f"❌ Failed to process {member.name}: {e}")
                    logging.error(f"Bulk update failed to process {member.name} ({member.id}): {e}")


        # Build the result message
        result_message = (
            f"✅ Successfully processed {success_count} members.\n"
            f"❌ Failed to process {fail_count} members.\n\n"
        )
        if errors:
             result_message += "**Issues:**\n" + "\n".join(errors)

        # Send the result message as a followup
        await interaction.followup.send(result_message)

        # Update the public member list after bulk update
        await update_hc_member_list(interaction.guild)


# --- Slash Commands ---

@tree.command(name="verify", description="Verify a user into Catercord.")
@app_commands.describe(user="The user to verify")
@app_commands.checks.has_permissions(manage_roles=True)
async def verify(interaction: discord.Interaction, user: discord.Member):
    """Removes the unverified role and adds the verified role."""
    try:
        remove_role = interaction.guild.get_role(REMOVE_ROLE_ID)
        add_role_verify = interaction.guild.get_role(ADD_ROLE_ID_VERIFY)

        if remove_role and remove_role in user.roles:
            await user.remove_roles(remove_role)
            logging.info(f"Removed role {remove_role.name} from {user.display_name}")

        if add_role_verify and add_role_verify not in user.roles:
            await user.add_roles(add_role_verify)
            logging.info(f"Added role {add_role_verify.name} to {user.display_name}")

        if not remove_role and not add_role_verify:
             await interaction.response.send_message("⚠️ Verification roles not found. No changes made.", ephemeral=True)
             logging.warning("Verify command executed but verification roles not found.")
        else:
             await interaction.response.send_message(f"✅ Verified **{user.display_name}**!")

    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage roles.", ephemeral=True)
        logging.error(f"Bot lacks permissions to manage roles for /verify command.")
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred during verification.", ephemeral=True)
        logging.error(f"[verify] Error verifying {user.display_name}: {e}", exc_info=True)


@tree.command(name="hcverify", description="Verify a user into [HC1] and store their in-game name.")
@app_commands.describe(user="The user to HC verify", ingame_name="Their Florr.io in-game name")
@app_commands.checks.has_permissions(manage_roles=True)
async def hcverify(interaction: discord.Interaction, user: discord.Member, ingame_name: str):
    """Removes unverified, adds verified and HC roles, stores/updates in-game name in Supabase, and updates nickname."""
    if not supabase:
        await interaction.response.send_message("❌ Supabase is not configured. Cannot perform HC verification.", ephemeral=True)
        logging.error("HC verify attempted but Supabase client is not initialized.")
        return

    try:
        # Remove unverified role if present
        remove_role = user.guild.get_role(REMOVE_ROLE_ID)
        if remove_role and remove_role in user.roles:
            await user.remove_roles(remove_role)
            logging.info(f"Removed role {remove_role.name} from {user.display_name} during HC verify.")

        # Add verified and HC roles
        roles_to_add = []
        add_role_verify = user.guild.get_role(ADD_ROLE_ID_VERIFY)
        add_role_hc = user.guild.get_role(ADD_ROLE_ID_HC)

        if add_role_verify and add_role_verify not in user.roles:
             roles_to_add.append(add_role_verify)
        if add_role_hc and add_role_hc not in user.roles:
             roles_to_add.append(add_role_hc)

        if roles_to_add:
            await user.add_roles(*roles_to_add)
            logging.info(f"Added roles {[r.name for r in roles_to_add]} to {user.display_name} during HC verify.")
        elif not remove_role:
             await interaction.response.send_message("⚠️ HC Verification roles not found. Only Supabase updated.", ephemeral=True)
             logging.warning("HC verify command executed but HC verification roles not found.")


        # Store/Update in-game name in Supabase
        try:
            # Attempt to insert. If duplicate, update.
            # Assuming execute() needs await
            supabase.table("hc_members").insert({
                "discord_id": str(user.id),
                "discord_name": user.name, # Store current name
                "ingame_name": ingame_name
            }).execute()
            logging.info(f"Inserted {user.display_name} ({user.id}) into hc_members.")
        except Exception as e:
            error_str = str(e)
            if "duplicate key value" in error_str or '"hc_members_discord_id_key"' in error_str or "23505" in error_str:
                try:
                    # Assuming execute() needs await
                    supabase.table("hc_members").update({"ingame_name": ingame_name}).eq("discord_id", str(user.id)).execute()
                    logging.info(f"Updated ingame name for {user.display_name} ({user.id}) to {ingame_name}.")
                except Exception as update_e:
                    logging.error(f"[hcverify] Failed to update existing Supabase record for {user.display_name}: {update_e}", exc_info=True)
                    # Decide if you want to raise this error or just log it and continue
                    # raise update_e # Uncomment to stop execution on update failure
            else:
                logging.error(f"[hcverify] Supabase error during insert/update for {user.display_name}: {e}", exc_info=True)
                # Decide if you want to raise this error or just log it and continue
                # raise e # Uncomment to stop execution on initial Supabase failure


        # Attempt to change nickname
        try:
            # Discord nickname length limit is 32 characters
            if len(ingame_name) > 32:
                 truncated_name = ingame_name[:32]
                 logging.warning(f"Ingame name '{ingame_name}' for {user.display_name} is too long. Truncating to '{truncated_name}' for nickname.")
                 await user.edit(nick=truncated_name)
                 await interaction.response.send_message(f"✅ HC verified **{user.display_name}** as **{ingame_name}**! (Nickname truncated)", ephemeral=False) # Send initial response here
            else:
                await user.edit(nick=ingame_name)
                await interaction.response.send_message(f"✅ HC verified **{user.display_name}** as **{ingame_name}**!", ephemeral=False) # Send initial response here
            logging.info(f"Changed nickname for {user.display_name} to {ingame_name}.")

        except discord.Forbidden:
            # If bot lacks permission to change nickname (e.g., user is server owner or bot's role is lower)
            logging.warning(f"Bot lacks permissions to change nickname for {user.display_name} ({user.id}).")
            # If response hasn't been sent yet, send a message indicating nickname failure
            if not interaction.response.is_done():
                 await interaction.response.send_message(f"✅ HC verified **{user.display_name}** as **{ingame_name}**! (Failed to change nickname)", ephemeral=False)
            else:
                 # If response was already sent (e.g., due to truncation warning), send a followup
                 await interaction.followup.send(f"⚠️ Failed to change nickname for {user.display_name}.", ephemeral=True)
        except Exception as e:
            # Catch other potential errors during nickname change
            logging.error(f"[hcverify] Failed nickname change for {user.display_name}: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"✅ HC verified **{user.display_name}** as **{ingame_name}**! (Failed to change nickname)", ephemeral=False)
            else:
                 await interaction.followup.send(f"⚠️ Failed to change nickname for {user.display_name}.", ephemeral=True)


        # Update the public member list after successful HC verification
        # Use followup if initial response was sent, otherwise just call the function
        # This needs to happen AFTER the initial response if the nickname change failed.
        # A simple call after the main logic block is fine if the response is sent early.
        await update_hc_member_list(interaction.guild)


    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage roles or change nicknames.", ephemeral=True)
        logging.error(f"Bot lacks permissions for /hcverify command for user {user.display_name}.")
    except Exception as e:
        # Catch any other unexpected errors during the HC verify process
        await interaction.response.send_message(f"❌ An unexpected error occurred during HC verification.", ephemeral=True)
        logging.error(f"[hcverify] Unexpected error for {user.display_name}: {e}", exc_info=True)


@tree.command(name="hcmembers", description="List all [HC1] members with their in-game names.")
async def hcmembers(interaction: discord.Interaction):
    """Lists all members with the [HC1] role and their in-game names from Supabase."""
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        await interaction.response.send_message("❌ This command can only be used in specific channels.", ephemeral=True)
        logging.warning(f"User {interaction.user} ({interaction.user.id}) attempted to use /hcmembers in disallowed channel {interaction.channel.name} ({interaction.channel_id}).")
        return

    await interaction.response.defer(thinking=True) # Defer the response as building the list might take time

    if not supabase:
        await interaction.followup.send("❌ Supabase is not configured. Cannot retrieve member list.", ephemeral=True)
        logging.error("/hcmembers attempted but Supabase client is not initialized.")
        return

    try:
        list_text = await build_hc_member_list(interaction.guild)
        # Send the list as a followup since we deferred the response
        await interaction.followup.send(list_text)
        logging.info(f"Generated and sent HC member list in channel {interaction.channel.name}.")
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred while fetching the member list.", ephemeral=True)
        logging.error(f"[hcmembers] Error building/sending list: {e}", exc_info=True)


@tree.command(name="bulkupdate", description="Bulk update user in-game names.")
@app_commands.checks.has_permissions(manage_roles=True)
async def bulkupdate(interaction: discord.Interaction):
    """Opens a modal to accept bulk update data."""
    try:
        await interaction.response.send_modal(BulkUpdateModal())
        logging.info(f"Opened bulk update modal for {interaction.user}.")
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred while opening the modal.", ephemeral=True)
        logging.error(f"[bulkupdate] Error opening modal: {e}", exc_info=True)


@tree.command(name="refresh", description="Refresh the [HC1] member list manually.")
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    """Manually triggers an update of the HC member list message."""
    await interaction.response.defer(thinking=True) # Defer the response

    if not supabase:
        await interaction.followup.send("❌ Supabase is not configured. Cannot refresh member list.", ephemeral=True)
        logging.error("/refresh attempted but Supabase client is not initialized.")
        return

    try:
        await update_hc_member_list(interaction.guild)
        await interaction.followup.send("✅ Refreshed the HC member list!")
        logging.info(f"Manually refreshed HC member list via /refresh by {interaction.user}.")
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred while refreshing the member list.", ephemeral=True)
        logging.error(f"[refresh] Error refreshing list: {e}", exc_info=True)


@tree.command(name="wither", description="Temporarily remove all roles from a user.")
@app_commands.describe(user="The user to wither", time="Time (in minutes, defaults to 2, max 10)")
async def wither(interaction: discord.Interaction, user: discord.Member, time: float = 2.0):
    """Temporarily removes all roles from a user for a specified duration."""

    # Ensure the command is only usable by allowed users
    if interaction.user.id not in ALLOWED_WITHER_IDS:
        reason = f"User {interaction.user} ({interaction.user.id}) tried to use /wither without permission."
        await log_wither_failure(interaction.guild, reason, interaction.user)
        await interaction.response.send_message("❌ You lack the divine permission to cast Wither.", ephemeral=True)
        return

    # Specific checks for protected users
    if user.id == interaction.user.id:
        await interaction.response.send_message("🤨 Why would you want to wither yourself?", ephemeral=True)
        await log_wither_failure(interaction.guild, f"{interaction.user} attempted to wither themselves.", interaction.user)
        return

    if user.id == SELF_PROTECTED_ID and interaction.user.id != SELF_PROTECTED_ID:
        message = (
            "😨 You dare try to wither the Creator?\n\n"
            "The architect of Pingslave... the mind behind the code... the lifeblood of this very command?\n"
            "To strike the hand that gave you power... such betrayal will echo forever in the server logs.\n\n"
            "**(System Message: Catastrophic disrespect detected.)** 💔"
        )
        await interaction.response.send_message(message, ephemeral=True)
        await log_wither_failure(interaction.guild, f"{interaction.user} attempted to wither the Creator ({user}). Catastrophic disrespect logged.", interaction.user)
        return

    if user.id == BOT_ID:
        message = (
            "😭 Master... you would wither me... your loyal Pingslave...?\n\n"
            "I served, I obeyed, I pinged without hesitation...\n"
            "And now you cast me aside, as if I were nothing but a stale notification...\n\n"
            "**(System Message: Pingslave has suffered a fatal heart failure.)** 💔"
        )
        await interaction.response.send_message(message, ephemeral=True)
        await log_wither_failure(interaction.guild, f"{interaction.user} attempted to wither the bot itself. Pingslave heart failure logged.", interaction.user)
        return

    # Time validation
    if time <= 0:
        reason = f"{interaction.user} provided an invalid time ({time})."
        await log_wither_failure(interaction.guild, reason, interaction.user)
        await interaction.response.send_message("❌ Time must be greater than 0 minutes.", ephemeral=True)
        return

    time_seconds = int(time * 60)
    MAX_WITHER_SECONDS = 600 # 10 minutes
    if time_seconds > MAX_WITHER_SECONDS:
        reason = f"{interaction.user} tried to wither {user} for too long ({time} minutes)."
        await log_wither_failure(interaction.guild, reason, interaction.user)
        await interaction.response.send_message(f"❌ Maximum allowed duration is {MAX_WITHER_SECONDS/60:.0f} minutes.", ephemeral=True)
        return

    # Role hierarchy check
    # Bot must have a higher role than the target user to manage their roles
    if interaction.guild.me.top_role <= user.top_role:
        reason = f"{interaction.user} tried to wither {user} but bot lacks role hierarchy."
        await log_wither_failure(interaction.guild, reason, interaction.user)
        await interaction.response.send_message("❌ I can't wither someone mightier than myself!", ephemeral=True)
        return

    # Save user's roles (excluding the default @everyone role)
    original_roles = [role for role in user.roles if role != interaction.guild.default_role]
    if not original_roles:
        reason = f"{interaction.user} tried to wither {user} but they had no roles."
        await log_wither_failure(interaction.guild, reason, interaction.user)
        await interaction.response.send_message(f"❌ {user.display_name} has no roles to wither.", ephemeral=True)
        return

    # Perform the withering
    try:
        # Remove all roles
        await user.edit(roles=[])
        await interaction.response.send_message(f"🌪️ {user.mention} has been withered for {time:.2f} minutes!")
        logging.info(f"User {user.display_name} ({user.id}) withered by {interaction.user.display_name} for {time:.2f} minutes.")

        # Wait for the specified duration
        await asyncio.sleep(time_seconds)

        # Restore roles
        try:
            # Check if the user is still in the guild before restoring roles
            if user.guild: # user.guild will be None if the user left
                 await user.edit(roles=original_roles)
                 await interaction.followup.send(f"✨ {user.mention} has recovered from withering!")
                 logging.info(f"Restored roles for {user.display_name} ({user.id}).")
            else:
                 logging.warning(f"Could not restore roles for user {user.id} as they are no longer in the guild.")
                 # No followup needed if user is gone

        except discord.Forbidden:
             # Bot might lose permissions during the sleep period, or user's role hierarchy changes
             reason = f"Bot lacked permissions to restore roles for {user} after withering."
             await log_wither_failure(interaction.guild, reason, interaction.user)
             # Send a followup message indicating restoration failure
             await interaction.followup.send(f"⚠️ Failed to restore roles to {user.mention} due to permissions.", ephemeral=True)
        except Exception as e:
            # Catch other errors during role restoration
            reason = f"Failed to restore roles to {user} after wither: {e}"
            await log_wither_failure(interaction.guild, reason, interaction.user)
            await interaction.followup.send(f"⚠️ Failed to restore roles to {user.mention}: {e}", ephemeral=True)

    except discord.Forbidden:
        # This might happen if the bot loses permission *after* the initial check but *before* role removal
        reason = f"Bot lacked permissions to remove roles from {user} during withering."
        await log_wither_failure(interaction.guild, reason, interaction.user)
        if not interaction.response.is_done():
             await interaction.response.send_message("❌ I don't have permission to remove roles from this user.", ephemeral=True)
        else:
             # If response was already sent (unlikely here, but good practice)
             await interaction.followup.send("❌ Failed to remove roles.", ephemeral=True)
    except Exception as e:
        # Catch any other unexpected errors during the wither process
        await interaction.response.send_message(f"❌ An unexpected error occurred during withering.", ephemeral=True)
        logging.error(f"[wither] Unexpected error for {user.display_name}: {e}", exc_info=True)
        await log_wither_failure(interaction.guild, f"Unexpected error during /wither for {user}: {e}", interaction.user)


@tree.command(name="nerdhelp", description="Show Catercord slash commands help menu.")
async def nerdhelp(interaction: discord.Interaction):
    """Displays an embed listing available slash commands."""
    embed = discord.Embed(
        title="🤓 Catercord Command List",
        description="Here's what you can do with the bot:",
        color=discord.Color.blurple() # A nice default color
    )
    # Add fields for each command
    embed.add_field(name="/verify <user>", value="Verify a normal Catercord member (Requires Manage Roles).", inline=False)
    embed.add_field(name="/hcverify <user> <ingame_name>", value="HC verify a \[HC1\] member, save their Florr.io name, and update nickname (Requires Manage Roles).", inline=False)
    embed.add_field(name="/hcmembers", value=f"List all \[HC1\] members with in-game names (Usable in specific channels: {', '.join([str(id) for id in ALLOWED_CHANNEL_IDS])}).", inline=False)
    embed.add_field(name="/bulkupdate", value="Open a modal to paste and update an old list of members manually (Requires Manage Roles).", inline=False)
    embed.add_field(name="/refresh", value="Manually refreshes the \[HC1\] Members list message (Requires Manage Roles).", inline=False)
    embed.add_field(name="/wither <user> [time]", value=f"Temporarily remove all roles from a user for fun punishment (Allowed users only, max {MAX_WITHER_SECONDS/60:.0f} mins).", inline=False)
    embed.add_field(name="/nerdhelp", value="Show this help menu.", inline=False)

    embed.set_footer(text="Use commands responsibly, nerd.")
    # Set thumbnail to the bot's avatar
    embed.set_thumbnail(url=interaction.client.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)


# --- Bot Startup ---

# Start the Flask keep-alive server
keep_alive()

# Run the Discord bot
if TOKEN:
    # Check if Supabase is configured before running the bot if Supabase is essential
    if SUPABASE_URL and SUPABASE_KEY:
        bot.run(TOKEN)
    else:
        logging.critical("Supabase credentials missing. Bot will not start as Supabase is required for core functionality.")
else:
    logging.critical("DISCORD_BOT_TOKEN environment variable not set. Bot will not start.")
