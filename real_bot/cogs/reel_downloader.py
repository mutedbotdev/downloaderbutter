# real_bot/cogs/reel_downloader.py

import os
import time
import shutil
import tempfile
import asyncio
import discord
import traceback
import yt_dlp
from discord.ext import commands
from urllib.parse import urlparse
from discord.ext.commands import Converter, BadArgument

from real_bot.utils.embed_image import create_embed_image



# ✅ Local JSON storage helpers
from real_bot.storage import ensure_storage, get_channel_id as get_channel_id_json, set_channel_id as set_channel_id_json

# --- URL validation ---
def is_instagram_reel_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return host in ("www.instagram.com", "instagram.com", "m.instagram.com") and parsed.path.startswith("/reel/")
    except Exception:
        return False

class InstagramReelURL(Converter):
    async def convert(self, ctx, argument):
        if is_instagram_reel_url(argument):
            return argument
        raise BadArgument("Not a valid Instagram Reel URL.")

# --- Config ---
INVITE_LINK = (
    "https://discord.com/oauth2/authorize?client_id=1398552886182412329"
    "&scope=bot+applications.commands&permissions=8"
)
COOKIE_FILE = "real_bot/real_bot/cookies_instagram.txt"
FFMPEG_PATH = os.getenv("FFMPEG_PATH")  # optional override

# Limit concurrent downloads (env MAX_CONCURRENT, default 2)
REEL_SEMAPHORE = asyncio.Semaphore(int(os.getenv("MAX_CONCURRENT", "2")))

class QuietLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

class InviteButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="➕ Invite Bot", url=INVITE_LINK))

class ReelDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        ensure_storage()  # make sure JSON files exist

    def _allowed_channel_id(self, guild_id: int):
        cid = get_channel_id_json(guild_id)
        return int(cid) if cid is not None else None

    @commands.command(name="reel")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def download_reel(self, ctx, url: InstagramReelURL):
        """
        Download an Instagram Reel video.
        Usage: !reel <Instagram Reel URL>
        """
        # Try to delete invoking message if allowed
        if ctx.guild and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass

        status = await ctx.send("⏳ Waiting…")
        print(f"[DEBUG][Reel] User {ctx.author.id} invoked !reel with URL: {url!r}")

        # Channel restriction (JSON storage)
        if ctx.guild:
            allowed_id = self._allowed_channel_id(ctx.guild.id)
            if allowed_id is None or ctx.channel.id != allowed_id:
                correct = ctx.guild.get_channel(allowed_id) if allowed_id else None
                if correct:
                    return await status.edit(content=f"❌ Wrong channel — please use {correct.mention}")
                return await status.edit(content="❌ Download channel not configured. Use `!setup #channel`.")

        # Unique per-job folder
        job_dir = tempfile.mkdtemp(prefix="reel_")
        await status.edit(content="📥 Downloading reel…")
        start_time = time.time()

        try:
            ydl_opts = {
                "format": "best",
                "outtmpl": os.path.join(job_dir, "%(title).80B.%(ext)s"),
                "cookiefile": COOKIE_FILE,
                "quiet": True,
                "no_warnings": True,
                "logger": QuietLogger(),
            }
            if FFMPEG_PATH:
                ydl_opts["ffmpeg_location"] = FFMPEG_PATH

            # Heavy work off the loop + concurrency cap
            async with REEL_SEMAPHORE:
                def _run_dl():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        return ydl.prepare_filename(info)
                filename = await asyncio.to_thread(_run_dl)

            elapsed = time.time() - start_time
            print(f"[DEBUG][Reel] Downloaded to {filename!r} in {elapsed:.2f}s")

            if not os.path.exists(filename):
                return await status.edit(content="❌ Download failed: file not created.")

            # Avatar bytes
            try:
                avatar_bytes = await ctx.author.display_avatar.with_format('png').read()
            except Exception as av_err:
                print(f"[DEBUG][Reel] avatar.read() failed: {av_err}")
                avatar_bytes = b""

            # Build embed (BytesIO or path)
            try:
                image_obj = await create_embed_image(
                    user=ctx.author,
                    avatar_bytes=avatar_bytes,
                    title="Successfully downloaded reel!",
                    elapsed=elapsed,
                    timestamp=None,  # timestamp not shown anymore
                    mode="reel"
                )
            except Exception:
                print(f"[ERROR][Reel] create_embed_image failed:\n{traceback.format_exc()}")
                image_obj = None

            # DM video + embed
            try:
                await ctx.author.send(file=discord.File(filename))
            except discord.Forbidden:
                print("[WARNING][Reel] Unable to DM user (Forbidden), skipping file DM.")
            except Exception as dm_err:
                print(f"[WARNING][Reel] DM video failed: {dm_err}")

            # DM/channel embed
            try:
                if image_obj:
                    if hasattr(image_obj, "read"):  # BytesIO
                        await ctx.author.send(file=discord.File(image_obj, filename="reel.png"), view=InviteButton())
                        image_obj.seek(0)
                        await ctx.send(file=discord.File(image_obj, filename="reel.png"), view=InviteButton())
                    elif isinstance(image_obj, str) and os.path.exists(image_obj):
                        await ctx.author.send(file=discord.File(image_obj, filename="reel.png"), view=InviteButton())
                        await ctx.send(file=discord.File(image_obj, filename="reel.png"), view=InviteButton())
            except Exception as dm_embed_err:
                print(f"[DEBUG][Reel] DM/channel embed failed: {dm_embed_err}")

            # Done
            try:
                await status.delete()
            except Exception:
                pass

        except Exception:
            print(f"[ERROR][Reel] Unexpected failure:\n{traceback.format_exc()}")
            await status.edit(content="❌ Failed to download reel. Please try again later.")
        finally:
            # Remove only this job's files
            shutil.rmtree(job_dir, ignore_errors=True)

    @download_reel.error
    async def reel_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait `{round(error.retry_after, 1)}s` before using this command again.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Allow quick channel binding via '#channel' mention by admins only."""
        if message.author.bot or not message.guild:
            return
        if not message.channel_mentions:
            return
        # Only allow admins to set this
        if not message.author.guild_permissions.administrator:
            return

        ch = message.channel_mentions[0]
        # Save via JSON storage
        set_channel_id_json(message.guild.id, ch.id)

        # Confirm where the request was made (current channel),
        # but only if the bot can send messages here
        perms = message.channel.permissions_for(message.guild.me)
        if not perms.send_messages:
            return
        try:
            await message.channel.send(f"✅ {ch.mention} set as the command channel.")
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(ReelDownloader(bot))
