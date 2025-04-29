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
