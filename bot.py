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

# --- CONTEXT FOR FUTURE LLMS ---
# (Please do not remove this comment block)
#
# Bot Name: TheNerd's Pingslave
# Owner: Vibhor / TheNerd / sweet_honey (Discord ID: 1230848174218940416)
# Target Server: Catercord (This bot is intended for use only in this specific server)
# Primary Purpose: Manage verification and information related to the "[HC1]" guild within the game Florr.io.
#   - "[HC1]" is a guild in Florr.io, originally named "HC". Members can be HC or non-HC.
#   - The bot verifies members, stores their in-game names (IGNs) in Supabase,
#     maintains a static public list of HC members in a dedicated channel,
#     provides an interactive paginated list via /hcmembers, and offers utility commands.
# Hosting Environment:
#   - Code Files: `bot.py` (this file), `requirements.txt` (listing discord, supabase, flask)
#   - Platform: Render (Free Tier) via a private GitHub repository.
#   - Keep-Alive: Uses a basic Flask web server (`keep_alive` function) monitored by an external
#     service (like Uptime Robot) hitting the Flask endpoint to prevent Render's free instance from sleeping.
#   - Environment Variables: DISCORD_BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY are set directly in Render's environment settings.
# Database: Supabase (PostgreSQL) used to store HC member IGNs linked to Discord IDs.
# Key Features: /verify, /hcverify (stores IGN), static list updates, /hcmembers (interactive list), /syncnicknames, /wither.
# --- END CONTEXT ---

# --- Configuration ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
REMOVE_ROLE_ID = 1360176495947022447
ADD_ROLE_ID_VERIFY = 1248708073019805717
ADD_ROLE_ID_HC = 1230235110415274004
ALLOWED_CHANNEL_IDS = {1354431395140731165, 1330664430148780102, 1248710731407560835}
HC_MEMBER_LIST_CHANNEL_ID = 1354431395140731165
HC_LIST_EMBED_TITLE = "**\[HC1\] Guild Members**"
ALLOWED_WITHER_IDS = {879320982299484240, 1230848174218940416, 955448447790620692}
SELF_PROTECTED_ID = 1230848174218940416
BOT_ID = 1365572437185400893
MAX_WITHER_SECONDS = 600
INFO_LOG_CHANNEL_ID = 1317943895606165579
ERROR_LOG_CHANNEL_ID = 1362988767367135453
MEMBERS_PER_PAGE = 50
NERDY_YELLOW = discord.Color.gold()

# --- Supabase Client ---
if SUPABASE_URL and SUPABASE_KEY:
    try: supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY); print("Supabase client created.")
    except Exception as e: print(f"CRITICAL: Supabase client failed: {e}"); supabase = None
else: print("CRITICAL: Supabase credentials missing."); supabase = None

# --- Discord Setup ---
intents = discord.Intents.default(); intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents); tree = bot.tree

# --- Flask App ---
# *** Corrected Flask Setup ***
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    try:
        # Use a larger port if 8080 causes issues in your environment
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        print(f"Flask server failed to start: {e}")

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.start()
    print("Keep alive thread started.")
# *** End Corrected Flask Setup ***

# --- Utility Functions ---
async def run_supabase_sync(func):
    try: return await bot.loop.run_in_executor(None, func)
    except APIError as api_err: print(f"Supabase API Error: {api_err}"); raise
    except Exception as e: print(f"Executor Error: {e}"); raise

# --- Logging ---
async def log_to_channel(channel_id: int, guild: discord.Guild, message: str = None, embed: discord.Embed = None):
    if not guild: print(f"Log Error: No guild for channel {channel_id}. Msg: {message or 'Embed'}") ; return
    log_channel = guild.get_channel(channel_id)
    if log_channel:
        try:
            if embed: await log_channel.send(embed=embed)
            elif message: await log_channel.send(message[:1997] + "..." if len(message) > 2000 else message)
        except discord.Forbidden: print(f"Log Error: Perms missing for channel {channel_id} ({guild.name}).")
        except discord.HTTPException as http_err: print(f"Log Error: Discord HTTP error {channel_id} ({guild.name}): {http_err.status} {http_err.code} - {http_err.text}")
        except Exception as e: print(f"Log Error: Send fail {channel_id} ({guild.name}): {e}")
    else: print(f"Log Error: Channel {channel_id} not found in {guild.name}.")
async def log_info(guild: discord.Guild, message: str, embed: discord.Embed = None):
    if not embed: embed = discord.Embed(description=message, color=NERDY_YELLOW)
    await log_to_channel(INFO_LOG_CHANNEL_ID, guild, embed=embed)
async def log_error(guild: discord.Guild, message: str, error: Exception = None, interaction: discord.Interaction = None, embed: discord.Embed = None):
    if not embed:
        embed = discord.Embed(title="⚠️ Error / Warning", description=message, color=discord.Color.red())
        if interaction:
            context = f"Cmd: `/{interaction.command.name if interaction.command else 'N/A'}`"
            if interaction.guild: context += f" in #{interaction.channel.name}"
            context += f"\nUser: `{interaction.user}` ({interaction.user.id})"
            embed.add_field(name="Context", value=context, inline=False)
        if error:
            err_details = f"**Type:** `{type(error).__name__}`\n**Msg:** `{str(error)}`\n"
            tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__, limit=5))
            err_details += f"**Traceback:**\n```py\n{tb_str[:1000]}{'...' if len(tb_str)>1000 else ''}\n```"
            embed.add_field(name="Error Details", value=err_details, inline=False)
            print(f"--- ERROR TRACEBACK ---\nGuild: {guild.id if guild else 'N/A'}\nCtx: {message}\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}\n--- END ---")
    await log_to_channel(ERROR_LOG_CHANNEL_ID, guild, embed=embed)

# --- Embed Pagination View ---
class HCPagesView(View):
    def __init__(self, data: list, total_members: int, timeout=300.0):
        super().__init__(timeout=timeout)
        self.data = data
        self.total_members = total_members
        self.current_page = 0
        self.total_pages = math.ceil(len(self.data) / MEMBERS_PER_PAGE) if data else 1
        self.message = None # Store message for timeout editing

        self.update_buttons()

    def create_page_embed(self) -> discord.Embed:
        start_index = self.current_page * MEMBERS_PER_PAGE
        end_index = start_index + MEMBERS_PER_PAGE
        page_data = self.data[start_index:end_index]
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, color=NERDY_YELLOW)
        desc_lines = []
        idx = start_index + 1
        for member, ingame_name in page_data:
            safe_user = discord.utils.escape_markdown(member.name) # Discord Username
            safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
            desc_lines.append(f"{idx}. {safe_user} ➔ {safe_ign}")
            idx += 1
        embed.description = "\n".join(desc_lines) if desc_lines else "No members on this page."
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} | Total HC Members: {self.total_members}")
        return embed

    def update_buttons(self):
        if hasattr(self, 'children') and len(self.children) > 1: # Ensure buttons exist
            self.children[0].disabled = self.current_page == 0 # Previous
            self.children[1].disabled = self.current_page >= self.total_pages - 1 # Next

    @button(label="Previous", style=discord.ButtonStyle.blurple, custom_id="hc_prev_interactive")
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_page_embed()
            try: await interaction.response.edit_message(embed=embed, view=self)
            except discord.NotFound: await log_error(interaction.guild, "Paginated msg edit fail (NF)", interaction=interaction)
            except discord.HTTPException as e: await log_error(interaction.guild, f"Paginated msg edit fail (HTTP {e.status})", error=e, interaction=interaction)
        else: await interaction.response.defer()

    @button(label="Next", style=discord.ButtonStyle.blurple, custom_id="hc_next_interactive")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_page_embed()
            try: await interaction.response.edit_message(embed=embed, view=self)
            except discord.NotFound: await log_error(interaction.guild, "Paginated msg edit fail (NF)", interaction=interaction)
            except discord.HTTPException as e: await log_error(interaction.guild, f"Paginated msg edit fail (HTTP {e.status})", error=e, interaction=interaction)
        else: await interaction.response.defer()

    async def on_timeout(self):
        if self.message:
            try:
                for item in self.children: item.disabled = True
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException, AttributeError):
                 print(f"Pagination View: Failed to disable buttons on timeout (message ID: {self.message.id if self.message else 'Unknown'}).")
            except Exception as e:
                 print(f"Pagination View: Unexpected error disabling buttons on timeout - {e}")


# --- Core HC List Logic ---
async def fetch_hc_member_data(guild: discord.Guild) -> tuple[list[tuple[discord.Member, str]], int]:
    hc_role = guild.get_role(ADD_ROLE_ID_HC)
    if not hc_role: await log_error(guild, f"Role {ADD_ROLE_ID_HC} not found."); return [], 0
    members_unsorted = [m for m in guild.members if hc_role in m.roles]
    total_count = len(members_unsorted)
    members_sorted = sorted(members_unsorted, key=lambda m: m.name.lower()) # Sort by username
    member_tuples = []
    member_ids = [str(m.id) for m in members_sorted]
    ign_map = {}
    if supabase and member_ids:
        try:
            resp = await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").in_("discord_id", member_ids).execute())
            if resp and resp.data: ign_map = {r['discord_id']: r.get("ingame_name", "Unknown") for r in resp.data}
        except Exception as e: await log_error(guild, "Failed bulk IGN fetch.", error=e); ign_map = {mid: "Err" for mid in member_ids}
    for member in members_sorted: member_tuples.append((member, ign_map.get(str(member.id), "Unknown")))
    return member_tuples, total_count

def generate_hc_list_embeds(data: list[tuple[discord.Member, str]], total_members: int) -> list[discord.Embed]:
    embeds = []
    total_pages = math.ceil(len(data) / MEMBERS_PER_PAGE) if data else 1
    for page_num in range(total_pages):
        start_index = page_num * MEMBERS_PER_PAGE
        end_index = start_index + MEMBERS_PER_PAGE
        page_data = data[start_index:end_index]
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, color=NERDY_YELLOW)
        desc_lines = []
        idx = start_index + 1
        for member, ingame_name in page_data:
            safe_user = discord.utils.escape_markdown(member.name) # Discord Username
            safe_ign = discord.utils.escape_markdown(ingame_name if ingame_name else "Unknown")
            desc_lines.append(f"{idx}. {safe_user} ➔ {safe_ign}")
            idx += 1
        embed.description = "\n".join(desc_lines) if desc_lines else "No members found."
        embed.set_footer(text=f"Page {page_num + 1}/{total_pages} | Total HC Members: {total_members}")
        embeds.append(embed)
    if not data and total_pages == 1:
        embed = discord.Embed(title=HC_LIST_EMBED_TITLE, description="No members found.", color=discord.Color.orange())
        embed.set_footer(text="Page 1/1 | Total HC Members: 0")
        return [embed]
    return embeds

async def update_hc_member_list(guild: discord.Guild): # Static list update
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    if not list_channel: await log_error(guild, f"Static list channel {HC_MEMBER_LIST_CHANNEL_ID} not found."); return

    try:
        member_data, total_count = await fetch_hc_member_data(guild)
        new_embeds = generate_hc_list_embeds(member_data, total_count)
        num_new_pages = len(new_embeds)

        existing_messages = []
        try:
            # Increase limit slightly to ensure we catch both pages if they exist
            async for message in list_channel.history(limit=15):
                if message.author == guild.me and message.embeds and message.embeds[0].title == HC_LIST_EMBED_TITLE:
                    existing_messages.append(message)
            existing_messages.sort(key=lambda m: m.created_at) # Sort oldest first
        except discord.Forbidden: await log_error(guild, f"Cannot read history in {list_channel.name}."); return
        except Exception as e: await log_error(guild, "Error searching history.", error=e); return

        num_existing = len(existing_messages)

        # Update/Send Messages
        for i in range(num_new_pages):
            embed_to_use = new_embeds[i]
            if i < num_existing:
                try: await existing_messages[i].edit(embed=embed_to_use); await asyncio.sleep(0.5)
                except Exception as e: await log_error(guild, f"Failed edit static list msg {i+1} (ID: {existing_messages[i].id}).", error=e)
            else:
                try: await list_channel.send(embed=embed_to_use); await asyncio.sleep(0.5)
                except Exception as e: await log_error(guild, f"Failed send static list page {i+1}.", error=e)

        # Delete Extra Old Messages
        if num_existing > num_new_pages:
            for msg_to_delete in existing_messages[num_new_pages:]:
                try: await msg_to_delete.delete(); await log_info(guild, f"Deleted surplus static list msg (ID: {msg_to_delete.id})."); await asyncio.sleep(0.5)
                except Exception as e: await log_error(guild, f"Failed delete surplus msg (ID: {msg_to_delete.id}).", error=e)

        await log_info(guild, f"Static HC list update complete ({num_new_pages} pages).")

    except Exception as e: await log_error(guild, "Overall static list update error.", error=e)


# --- Discord Events ---
@bot.event async def on_ready(): print(f"Logged in as {bot.user}"); try: synced = await tree.sync(); print(f"Synced {len(synced)} cmds."); [await log_info(g, f"Bot Ready ({len(synced)} cmds)."), await update_hc_member_list(g), await asyncio.sleep(1)] for g in bot.guilds; except Exception as e: print(f"Sync fail: {e}"); try: await log_error(bot.guilds[0], "Sync fail.", error=e) except: pass
@bot.event async def on_member_update(b: discord.Member, a: discord.Member): g=a.guild; r=g.get_role(ADD_ROLE_ID_HC); if not r: return; bh,ah=(r in b.roles),(r in a.roles); if bh!=ah: act="added" if ah else "removed"; await log_info(g,"",embed=discord.Embed(description=f"HC role `{r.name}` {act} user `{a.name}`. Updating static list.",color=discord.Color.purple())); await update_hc_member_list(g) # Update static list only
@tree.error async def on_app_command_error(i: discord.Interaction, e: app_commands.AppCommandError): err_msg="❌ Err"; log_desc="Unhandled"; log_err=e; g=i.guild; if not g: print(f"Err outside guild: {e}"); return; if isinstance(e,app_commands.MissingPermissions): mp=", ".join(e.missing_permissions); err_msg=f"❌ Perms: `{mp}`"; log_desc=f"User `{i.user}` lacked perms ({mp})."; log_err=None; elif isinstance(e,app_commands.CheckFailure): err_msg="❌ Check fail."; log_desc=f"User `{i.user}` failed checks."; log_err=None; elif isinstance(e,app_commands.CommandNotFound): print(f"Cmd not found: {i.command.name if i.command else 'N/A'}"); return; elif isinstance(e,app_commands.CommandInvokeError): orig=e.original; err_msg=f"❌ Cmd Err: `{type(orig).__name__}`"; log_desc="Cmd invoke err."; log_err=orig; else: err_msg="❌ Unknown err."; log_desc=f"Unhandled type: `{type(e).__name__}`"; log_err=e; await log_error(g,log_desc,error=log_err,interaction=i); if not i.response.is_done(): try: await i.response.send_message(err_msg,ephemeral=True) except: pass; else: try: await i.followup.send(err_msg,ephemeral=True) except: pass

# --- Modals ---
class BulkUpdateModal(Modal, title="Bulk Update"): data = TextInput(label="Paste list (Format: DiscordName ➔ InGameName)", style=discord.TextStyle.paragraph); async def on_submit(self, i: discord.Interaction): await i.response.defer(thinking=True,ephemeral=True); g=i.guild; if not supabase: await i.followup.send(embed=create_embed("❌ Supabase missing.", discord.Color.red()), ephemeral=True); await log_error(g,"Bulk: Supabase missing.", interaction=i); return; s,f,nf=0,0,0; res=[]; lines=self.data.value.strip().splitlines(); if not lines: await i.followup.send(embed=create_embed("⚠️ No data.",discord.Color.orange()), ephemeral=True); return; members={m.name.lower():m for m in g.members}; for idx, line in enumerate(lines,1): line=line.strip(); if "➔" not in line: if line: res.append(('f',f"L{idx}: Format")); continue; try: uname,ign=map(str.strip,line.split("➔",1)); if not uname or not ign: res.append(('f',f"L{idx}: Missing")); continue; except ValueError: res.append(('f',f"L{idx}: Separator")); continue; member=members.get(uname.lower()); if not member: f+=1; nf+=1; res.append(('f',f"L{idx}: User `{uname}` NF")); continue; try: await run_supabase_sync(lambda: supabase.table("hc_members").upsert({"discord_id":str(member.id),"discord_name":member.name,"ingame_name":ign},on_conflict="discord_id").execute()); s+=1; except Exception as e: f+=1; res.append(('f',f"L{idx}: Fail {member.name}: `{type(e).__name__}`")); await log_error(g,f"Bulk DB err {member.name}",error=e,interaction=i); embed=discord.Embed(title="Bulk Update Results",color=NERDY_YELLOW); summary=f"✅ OK: {s}\n❌ Fail: {f}\n - NF: {nf}\n - Err: {f-nf}"; embed.description=summary; err_details="\n".join([r[1] for r in res if r[0]=='f']); if err_details: embed.add_field(name="Issues",value=err_details[:1021]+"..." if len(err_details)>1024 else err_details,inline=False); await i.followup.send(embed=embed,ephemeral=True); log_embed=discord.Embed(description=f"Bulk by `{i.user}`. OK:{s}, Fail:{f}.",color=NERDY_YELLOW); await log_info(g,"",embed=log_embed); await update_hc_member_list(g) # Update static list after bulk

# --- Slash Commands ---
def create_embed(description: str, color: discord.Color = NERDY_YELLOW, title: str = None) -> discord.Embed: return discord.Embed(title=title, description=description, color=color)

# Condensed command definitions remain the same
@tree.command(name="verify", description="Verify a user.") @app_commands.describe(user="User") @app_commands.checks.has_permissions(manage_roles=True)
async def verify(i: discord.Interaction, user: discord.Member): g=i.guild; rr,ar=g.get_role(REMOVE_ROLE_ID),g.get_role(ADD_ROLE_ID_VERIFY); act,log=[],[]; if not rr:log.append(f"Role {REMOVE_ROLE_ID} NF"); if not ar:log.append(f"Role {ADD_ROLE_ID_VERIFY} NF"); if log: await log_error(g,f"/verify setup: {';'.join(log)}",i); try: if rr and rr in user.roles: await user.remove_roles(rr);act.append(f"➖ `{rr.name}`"); if ar and ar not in user.roles: await user.add_roles(ar);act.append(f"➕ `{ar.name}`"); if not act: embed=create_embed("❌ Roles missing." if not rr and not ar else f"ℹ️ No changes for {user.display_name}.", discord.Color.red() if not rr and not ar else discord.Color.orange()); await i.response.send_message(embed=embed,ephemeral=True); else: log_msg=f"Verified `{user.display_name}`. {' '.join(act)}."; await log_info(g,f"`{i.user}`: {log_msg}"); embed=create_embed(f"✅ Verified **{user.display_name}**!\n"+"\n".join(act), discord.Color.green()); await i.response.send_message(embed=embed); except discord.Forbidden: await log_error(g,"/verify Forbidden.",i); await i.response.send_message(embed=create_embed("❌ Role Perms Missing.", discord.Color.red()),ephemeral=True); except Exception as e: await log_error(g,f"/verify error {user.display_name}",e,i); await i.response.send_message(embed=create_embed("❌ Verify error.", discord.Color.red()),ephemeral=True)
@tree.command(name="unverify", description="Unverify a user.") @app_commands.describe(user="User") @app_commands.checks.has_permissions(manage_roles=True)
async def unverify(i: discord.Interaction, user: discord.Member): g=i.guild; rr,ar=g.get_role(ADD_ROLE_ID_VERIFY),g.get_role(REMOVE_ROLE_ID); act,log=[],[]; if not rr:log.append(f"Role {ADD_ROLE_ID_VERIFY} NF"); if not ar:log.append(f"Role {REMOVE_ROLE_ID} NF"); if log: await log_error(g,f"/unverify setup: {';'.join(log)}",i); try: if rr and rr in user.roles: await user.remove_roles(rr);act.append(f"➖ `{rr.name}`"); if ar and ar not in user.roles: await user.add_roles(ar);act.append(f"➕ `{ar.name}`"); if not act: embed=create_embed("❌ Roles missing." if not rr and not ar else f"ℹ️ No changes for {user.display_name}.", discord.Color.red() if not rr and not ar else discord.Color.orange()); await i.response.send_message(embed=embed,ephemeral=True); else: log_msg=f"Unverified `{user.display_name}`. {' '.join(act)}."; await log_info(g,f"`{i.user}`: {log_msg}"); embed=create_embed(f"✅ Unverified **{user.display_name}**!\n"+"\n".join(act), discord.Color.green()); await i.response.send_message(embed=embed); except discord.Forbidden: await log_error(g,"/unverify Forbidden.",i); await i.response.send_message(embed=create_embed("❌ Role Perms Missing.", discord.Color.red()),ephemeral=True); except Exception as e: await log_error(g,f"/unverify error {user.display_name}",e,i); await i.response.send_message(embed=create_embed("❌ Unverify error.", discord.Color.red()),ephemeral=True)
@tree.command(name="hcverify", description="HC Verify user, store IGN, set nickname.") @app_commands.describe(user="User", ingame_name="Florr IGN") @app_commands.checks.has_permissions(manage_roles=True)
async def hcverify(i: discord.Interaction, user: discord.Member, ingame_name: str): await i.response.defer(thinking=True); g=i.guild; if not supabase: await i.followup.send(embed=create_embed("❌ Supabase missing.", discord.Color.red()),ephemeral=True); return; rr,arv,arh=g.get_role(REMOVE_ROLE_ID),g.get_role(ADD_ROLE_ID_VERIFY),g.get_role(ADD_ROLE_ID_HC); roles_add=[]; log,resp=[],[]; errs=[]; if not arv:errs.append(f"Role {ADD_ROLE_ID_VERIFY} NF"); if not arh:errs.append(f"Role {ADD_ROLE_ID_HC} NF"); if errs: await log_error(g,f"/hcverify setup: {'; '.join(errs)}",i); try: orig_hc=arh and arh in user.roles; if rr and rr in user.roles: await user.remove_roles(rr);log.append("Rm Unverified"); if arv and arv not in user.roles: roles_add.append(arv); if arh and arh not in user.roles: roles_add.append(arh); if roles_add: await user.add_roles(*roles_add); names=', '.join([f"`{r.name}`" for r in roles_add]); log.append(f"Add: {names}"); resp.append(f"➕ Roles: {names}"); db_ok=False; try: await run_supabase_sync(lambda: supabase.table("hc_members").upsert({"discord_id":str(user.id),"discord_name":user.name,"ingame_name":ingame_name},on_conflict="discord_id").execute()); log.append("Upsert IGN"); resp.append(f"💾 IGN: `{ingame_name}`"); db_ok=True; except Exception as e: await log_error(g,f"DB upsert fail {user.display_name}",e,i); log.append("DB FAILED"); resp.append("⚠️ DB Failed!"); nick_msg=""; target_nick=ingame_name[:32]; if user.nick!=target_nick: try: await user.edit(nick=target_nick); log.append(f"Set nick: '{target_nick}'"); resp.append(f"🏷️ Nick: `{target_nick}`"); if target_nick!=ingame_name: nick_msg=" (trunc)"; except discord.Forbidden: log.append("Nick FAIL (Perms)"); resp.append("⚠️ Nick Fail (Perms)"); nick_msg=" (nick fail)"; except Exception as e: await log_error(g,f"Nick fail {user.display_name}",e,i); log.append(f"Nick FAIL ({type(e).__name__})"); resp.append("⚠️ Nick Fail (Err)"); nick_msg=" (nick fail)"; else: log.append("Nick OK"); resp.append("🏷️ Nick OK"); log_m=f"`{i.user}` HC verified `{user.display_name}`. {'; '.join(log)}."; await log_info(g,log_m); embed=create_embed(title=f"✅ HC Verified: {user.display_name}{nick_msg}",description="\n".join(resp) if resp else "No actions.",color=discord.Color.green() if db_ok else discord.Color.orange()); await i.followup.send(embed=embed,ephemeral=False); new_hc=arh and arh in roles_add; if new_hc or (orig_hc and db_ok): await update_hc_member_list(g); except discord.Forbidden as fe: await log_error(g,"/hcverify Role Perms",fe,i); await i.followup.send(embed=create_embed("❌ Role Perms Missing.",discord.Color.red()),ephemeral=True); except Exception as e: await log_error(g,f"/hcverify Err {user.display_name}",e,i); await i.followup.send(embed=create_embed("❌ HCVerify Err.",discord.Color.red()),ephemeral=True)
@tree.command(name="unhcverify", description="Remove HC role and reset nickname.") @app_commands.describe(user="User") @app_commands.checks.has_permissions(manage_roles=True)
async def unhcverify(i: discord.Interaction, user: discord.Member): g=i.guild; arh=g.get_role(ADD_ROLE_ID_HC); log,resp=[],[]; if not arh: await log_error(g,f"/unhcverify Role {ADD_ROLE_ID_HC} NF",i); await i.response.send_message(embed=create_embed("❌ HC Role missing.", discord.Color.red()),ephemeral=True); return; try: if arh in user.roles: await user.remove_roles(arh); log.append("Rm HC role"); resp.append(f"➖ Role: `{arh.name}`"); else: await i.response.send_message(embed=create_embed(f"ℹ️ {user.display_name} lacks `{arh.name}`.",discord.Color.orange()),ephemeral=True); return; nick_msg=""; if user.nick is not None: try: await user.edit(nick=None); log.append("Reset nick"); resp.append("🏷️ Reset Nick"); except discord.Forbidden: log.append("Nick reset FAIL (Perms)"); resp.append("⚠️ Nick Reset Fail (Perms)"); nick_msg=" (nick fail)"; except Exception as e: await log_error(g,f"Nick reset fail {user.display_name}",e,i); log.append(f"Nick reset FAIL ({type(e).__name__})"); resp.append("⚠️ Nick Reset Fail (Err)"); nick_msg=" (nick fail)"; else: log.append("No nick"); resp.append("🏷️ No Nick"); log_m=f"`{i.user}` un-HC-verified `{user.display_name}`. {'; '.join(log)}."; await log_info(g,log_m); embed=create_embed(title=f"✅ Un-HC-Verified: {user.display_name}{nick_msg}",description="\n".join(resp),color=discord.Color.green()); await i.response.send_message(embed=embed); except discord.Forbidden as fe: await log_error(g,"/unhcverify Role Perms",fe,i); await i.response.send_message(embed=create_embed("❌ Role Perms Missing.",discord.Color.red()),ephemeral=True); except Exception as e: await log_error(g,f"/unhcverify Err {user.display_name}",e,i); if not i.response.is_done(): await i.response.send_message(embed=create_embed("❌ UnHCVerify Err.",discord.Color.red()),ephemeral=True); else: await i.followup.send(embed=create_embed("❌ UnHCVerify Err.",discord.Color.red()),ephemeral=True)

# /hcmembers updated
@tree.command(name="hcmembers", description="Show an interactive list of [HC1] members.")
async def hcmembers(interaction: discord.Interaction):
    guild = interaction.guild
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        embed = create_embed("❌ Use this command in allowed channels.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(thinking=True) # Public response

    if not supabase:
        await interaction.followup.send(embed=create_embed("❌ Supabase missing.", discord.Color.red()))
        return

    try:
        member_data, total_count = await fetch_hc_member_data(guild)

        if not member_data:
            embed = create_embed(f"{HC_LIST_EMBED_TITLE}\nNo members found or error fetching.", discord.Color.orange())
            await interaction.followup.send(embed=embed)
        else:
            view = HCPagesView(member_data, total_count)
            embed = view.create_page_embed()
            message = await interaction.followup.send(embed=embed, view=view)
            view.message = message # Assign message to view for timeout handling
            await log_info(guild, f"/hcmembers interactive list generated by `{interaction.user}`.")

    except Exception as e:
        await log_error(guild, "[hcmembers] Error generating interactive list.", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Error fetching list.", discord.Color.red()))

# /refresh updates static list
@tree.command(name="refresh", description="Refresh the static [HC1] member list.")
@app_commands.checks.has_permissions(manage_roles=True)
async def refresh(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    guild = interaction.guild
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)

    if not supabase: await interaction.followup.send(embed=create_embed("❌ Supabase missing.", discord.Color.red()), ephemeral=True); return
    if not list_channel: await interaction.followup.send(embed=create_embed("❌ List channel missing.", discord.Color.red()), ephemeral=True); return

    try:
        await update_hc_member_list(guild) # Updates the static list
        embed = create_embed(f"✅ Refreshed static HC list in {list_channel.mention}!", discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_info(guild, f"Manual refresh static list by `{interaction.user}`.")
    except Exception as e:
        await log_error(guild, "Error during manual /refresh.", error=e, interaction=interaction)
        await interaction.followup.send(embed=create_embed("❌ Error refreshing list.", discord.Color.red()), ephemeral=True)

# Condensed command definitions remain the same
@tree.command(name="bulkupdate", description="Bulk update IGNs via modal.") @app_commands.checks.has_permissions(manage_roles=True)
async def bulkupdate(i: discord.Interaction): try: await i.response.send_modal(BulkUpdateModal()); await log_info(i.guild, f"Opened bulk modal for `{i.user}`."); except Exception as e: await log_error(i.guild, "Err opening bulk modal.",e,i); if not i.response.is_done(): await i.response.send_message(embed=create_embed("❌ Err opening modal.",discord.Color.red()),ephemeral=True)
@tree.command(name="syncnicknames", description="Sync all HC nicks with stored IGNs.") @app_commands.checks.has_permissions(manage_roles=True)
async def syncnicknames(i: discord.Interaction): await i.response.defer(thinking=True,ephemeral=True); g=i.guild; if not supabase: await i.followup.send(embed=create_embed("❌ Supabase missing.", discord.Color.red()),ephemeral=True); return; arh=g.get_role(ADD_ROLE_ID_HC); if not arh: await i.followup.send(embed=create_embed("❌ HC Role missing.", discord.Color.red()),ephemeral=True); return; await log_info(g,f"SyncNick started by `{i.user}`."); await i.edit_original_response(content="🔄 Fetching..."); ign_data={}; try: resp=await run_supabase_sync(lambda: supabase.table("hc_members").select("discord_id, ingame_name").execute()); if resp and resp.data: ign_data={item['discord_id']: item['ingame_name'] for item in resp.data if item.get('ingame_name')}; except Exception as e: await log_error(g,"SyncNick DB Fetch Fail",e,i); await i.edit_original_response(content="❌ DB Fail."); return; counts={'s':0,'k':0,'ni':0,'p':0,'o':0,'pr':0}; members=[m for m in g.members if arh in m.roles]; total=len(members); await i.edit_original_response(content=f"🔄 Syncing {total}..."); for idx, m in enumerate(members): counts['pr']+=1; if idx%25==0 and idx>0: await i.edit_original_response(content=f"🔄 Syncing... ({idx}/{total})"); mid=str(m.id); if mid not in ign_data: counts['ni']+=1; continue; ign=ign_data[mid]; target=ign[:32]; if m.nick==target: counts['k']+=1; continue; try: await m.edit(nick=target); counts['s']+=1; except discord.Forbidden: counts['p']+=1; except Exception as e: counts['o']+=1; await log_error(g,f"SyncNick Err: {m.name}",e,i); embed=discord.Embed(title="Nickname Sync Complete!",color=NERDY_YELLOW); summary=f"Processed:{counts['pr']}|✅Upd:{counts['s']}|ℹ️Skip:{counts['k']}|⚠️NoIGN:{counts['ni']}|❌Perm:{counts['p']}|❌Other:{counts['o']}"; embed.description=summary; await i.edit_original_response(content=None,embed=embed); log_embed=discord.Embed(title="Nickname Sync Finished",description=summary,color=NERDY_YELLOW).set_footer(text=f"By {i.user}"); await log_info(g,"",embed=log_embed)

# /wither command (restored version)
@tree.command(name="wither", description="Temporarily remove all roles from a user.")
@app_commands.describe(user="The user to wither", time="Time (in minutes, defaults to 2, max 10)")
async def wither(interaction: discord.Interaction, user: discord.Member, time: float = 2.0):
    guild = interaction.guild
    interaction_user = interaction.user

    async def wither_fail_log(reason: str, error: Exception = None):
         await log_error(guild, f"Wither Failure: {reason}", error=error, interaction=interaction)

    if interaction_user.id not in ALLOWED_WITHER_IDS:
        await wither_fail_log(f"User `{interaction_user}` lacks permission.")
        await interaction.response.send_message(embed=create_embed("❌ You lack the divine permission.", discord.Color.red()), ephemeral=True); return

    if user.id == interaction_user.id:
        await wither_fail_log("User attempted self-wither.")
        await interaction.response.send_message(embed=create_embed("🤨 Why wither yourself?", discord.Color.orange()), ephemeral=True); return

    if user.id == SELF_PROTECTED_ID and interaction_user.id != SELF_PROTECTED_ID:
        await wither_fail_log(f"User attempted to wither the Creator ({user.id}).")
        await interaction.response.send_message(embed=create_embed("😨 You dare try to wither the Creator?", discord.Color.red()), ephemeral=True); return

    if user.id == BOT_ID:
        await wither_fail_log("User attempted to wither the bot.")
        await interaction.response.send_message(embed=create_embed("😭 Master... you would wither me...?", discord.Color.blue()), ephemeral=True); return

    time_seconds = int(time * 60)
    if time <= 0 or time_seconds > MAX_WITHER_SECONDS:
        await wither_fail_log(f"Invalid time provided ({time} minutes).")
        await interaction.response.send_message(embed=create_embed(f"❌ Time must be > 0 and <= {MAX_WITHER_SECONDS/60:.0f} minutes.", discord.Color.red()), ephemeral=True); return

    if guild.me.top_role <= user.top_role:
        await wither_fail_log(f"Bot role is not high enough to wither {user.name}.")
        await interaction.response.send_message(embed=create_embed("❌ I can't wither someone mightier!", discord.Color.red()), ephemeral=True); return

    original_roles = [role for role in user.roles if role != guild.default_role]
    if not original_roles:
        await wither_fail_log(f"User {user.name} has no roles.")
        await interaction.response.send_message(embed=create_embed(f"❌ {user.display_name} has no roles.", discord.Color.orange()), ephemeral=True); return

    try:
        await user.edit(roles=[]) # Remove roles
        role_names = ', '.join([f"`{r.name}`" for r in original_roles])
        embed = create_embed(title="🌪️ Wither Cast! 🌪️", description=f"{user.mention} withered by {interaction_user.mention} for **{time:.2f} mins**!\nRemoved: {role_names}", color=discord.Color.dark_purple())
        await interaction.response.send_message(embed=embed) # Public response
        await log_info(guild, f"`{user.name}` ({user.id}) withered by `{interaction_user.name}` for {time:.2f}m.")

        await asyncio.sleep(time_seconds) # Wait

        try: # Restore roles
             member_after_wait = await guild.fetch_member(user.id)
             if member_after_wait:
                 await member_after_wait.edit(roles=original_roles)
                 await interaction.followup.send(embed=create_embed(f"✨ {user.mention} recovered!", color=NERDY_YELLOW)) # Public followup
                 await log_info(guild, f"Restored roles for `{user.name}` ({user.id}).")
             else: await log_info(guild, f"`{user.name}` ({user.id}) left before roles restored.")
        except discord.NotFound: await log_info(guild, f"`{user.name}` ({user.id}) not found for restore.")
        except discord.Forbidden as fe:
             await wither_fail_log("Restore roles Forbidden.", error=fe)
             await interaction.followup.send(embed=create_embed(f"⚠️ Failed role restore (Perms).", discord.Color.red()), ephemeral=True) # Ephemeral failure notice
        except Exception as e:
            await wither_fail_log("Restore roles failed.", error=e)
            await interaction.followup.send(embed=create_embed(f"⚠️ Error restoring roles.", discord.Color.red()), ephemeral=True) # Ephemeral failure notice

    except discord.Forbidden as fe:
        await wither_fail_log("Remove roles Forbidden (initial).", error=fe)
        if not interaction.response.is_done(): await interaction.response.send_message(embed=create_embed("❌ Lacked perms to remove roles!", discord.Color.red()), ephemeral=True)
    except Exception as e:
        await wither_fail_log("Unexpected wither error.", error=e)
        if not interaction.response.is_done(): await interaction.response.send_message(embed=create_embed("❌ Unexpected wither error.", discord.Color.red()), ephemeral=True)

# /nerdhelp definition (public)
@tree.command(name="nerdhelp", description="Show Catercord slash commands help menu.")
async def nerdhelp(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title="🤓 Catercord Command List", description="Use these commands:", color=NERDY_YELLOW)
    list_channel = guild.get_channel(HC_MEMBER_LIST_CHANNEL_ID)
    def add_help_field(name: str, value: str, permissions: str = None, notes: str = None): full_value = value; full_value += f"\n**Permissions:** `{permissions}`" if permissions else ""; full_value += f"\n**Note:** {notes}" if notes else ""; embed.add_field(name=name, value=full_value, inline=False)
    add_help_field("/verify <user>", "Verify standard member.", "Manage Roles")
    add_help_field("/unverify <user>", "Revert member to unverified.", "Manage Roles")
    add_help_field("/hcverify <user> <IGN>", "Verify into HC, store IGN, set nick.", "Manage Roles")
    add_help_field("/unhcverify <user>", "Remove HC role, reset nick.", "Manage Roles")
    add_help_field("/hcmembers", "Show interactive HC member list.", notes="Usable in allowed channels.")
    add_help_field("/bulkupdate", "Bulk update/add IGNs via modal.", "Manage Roles")
    add_help_field("/refresh", "Manually refresh the static HC list.", "Manage Roles", f"Updates list in {list_channel.mention if list_channel else 'list channel'}.")
    add_help_field("/syncnicknames", "Sync all HC nicks from stored IGNs.", "Manage Roles")
    add_help_field("/wither <user> [time]", "Temporarily remove all roles.", notes=f"Max {MAX_WITHER_SECONDS/60:.0f}m. Special permission needed.")
    add_help_field("/nerdhelp", "Show this help menu.")
    embed.set_footer(text="Stay nerdy!")
    if interaction.client.user.display_avatar: embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=False) # Public response

# --- Bot Startup ---
if __name__ == "__main__":
    if TOKEN:
        if supabase: keep_alive(); try: print("Starting Bot..."); bot.run(TOKEN); except Exception as e: print(f"CRITICAL: Bot run failed: {e}")
        else: print("CRITICAL: Supabase client failed.")
    else: print("CRITICAL: DISCORD_BOT_TOKEN not set.")
