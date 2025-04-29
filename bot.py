# --- hcverify function ---
# [...] previous code

# Hierarchy checks (Corrected)
bot_member = guild.me
# Compare position integers, not Role objects directly with integers
if bot_member.top_role.position <= user.top_role.position \
   or bot_member.top_role.position <= role_verified.position \
   or bot_member.top_role.position <= role_hc.position \
   or (role_unverified and bot_member.top_role.position <= role_unverified.position):
     await interaction.followup.send("❌ Hierarchy Error: I cannot manage roles for this user or the required roles (my top role is not high enough).", ephemeral=True)
     await log_error(guild, f"HCVerify failed: Bot hierarchy too low for {user.mention} or roles.", interaction=interaction)
     return
# Check invoker hierarchy (remains the same logic)
if interaction.user.top_role <= user.top_role and interaction.user.id != guild.owner_id:
     await interaction.followup.send("❌ Hierarchy Error: You cannot manage roles/nicknames for this user.", ephemeral=True)
     return
# Check bot hierarchy for nickname (remains the same logic - compares Role to Role which is okay, but using .position is clearer)
# Optional clarification: use .position here too for consistency, though Role <= Role works
# if bot_member.top_role.position <= user.top_role.position:
if bot_member.top_role <= user.top_role:
     await interaction.followup.send("❌ Hierarchy Error: I cannot change the nickname for this user (my top role is not high enough).", ephemeral=True)
     await log_error(guild, f"HCVerify failed: Bot hierarchy too low to change nick for {user.mention}.", interaction=interaction)
     return

# [...] rest of the hcverify command
