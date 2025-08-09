# real_bot/cogs/short_downloader.py

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
from real_bot.storage import ensure_storage, get_channel_id as get_channel_id_json

# --- URL validation ---
def is_youtube_shorts_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return host in ("www.youtube.com", "youtube.com", "m.youtube.com") and parsed.path.startswith("/shorts/")
    except Exception:
        return False

class YouTubeShortsURL(Converter):
    async def convert(self, ctx, argument):
        if is_youtube_shorts_url(argument):
            return argument
        raise BadArgument("Not a valid YouTube Shorts URL.")

# --- Config ---
INVITE_LINK = (
    "https://discord.com/oauth2/authorize?client_id=1398552886182412329"
    "&scope=bot+applications.commands&permissions=8"
)
COOKIE_FILE = "real_bot/real_bot/cookies_youtube.txt"
FFMPEG_PATH = os.getenv("FFMPEG_PATH")  # optional

# Limit concurrent downloads (env MAX_CONCURRENT, default 2)
SHORT_SEMAPHORE = asyncio.Semaphore(int(os.getenv("MAX_CONCURRENT", "2")))

class InviteButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="➕ Invite Bot", url=INVITE_LINK))

class QuietLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

class ShortDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        ensure_storage()  # make sure JSON files exist

    def _allowed_channel_id(self, guild_id: int):
        cid = get_channel_id_json(guild_id)
        return int(cid) if cid is not None else None

    @commands.command(name="short")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def download_short(self, ctx, url: YouTubeShortsURL):
        """
        Download a YouTube Shorts video.
        Usage: !short <YouTube Shorts URL>
        """
        # Attempt to delete invoking message if bot has permission
        if ctx.guild and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass

        status = await ctx.send("⏳ Waiting…")
        print(f"[DEBUG][Short] User {ctx.author.id} invoked !short with URL: {url!r}")

        # Channel restriction (JSON storage)
        if ctx.guild:
            allowed_id = self._allowed_channel_id(ctx.guild.id)
            if allowed_id is None or ctx.channel.id != allowed_id:
                correct = ctx.guild.get_channel(allowed_id) if allowed_id else None
                if correct:
                    return await status.edit(content=f"❌ Wrong channel — please use {correct.mention}")
                return await status.edit(content="❌ Download channel not configured. Use `!setup #channel`.")

        # Unique per-job directory
        job_dir = tempfile.mkdtemp(prefix="short_")
        await status.edit(content="🔄 Downloading YouTube Short…")
        start_time = time.time()

        try:
            ydl_opts = {
                'format': 'mp4',
                'outtmpl': os.path.join(job_dir, "%(title).80B.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
                'cookiefile': COOKIE_FILE,
                'logger': QuietLogger(),
            }
            if FFMPEG_PATH:
                ydl_opts['ffmpeg_location'] = FFMPEG_PATH

            # Run heavy work off the event loop + concurrency cap
            async with SHORT_SEMAPHORE:
                def _run_dl():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        return ydl.prepare_filename(info)
                filename = await asyncio.to_thread(_run_dl)

            elapsed = time.time() - start_time
            print(f"[DEBUG][Short] Downloaded to {filename!r} in {elapsed:.2f}s")

            if not os.path.exists(filename):
                return await status.edit(content="❌ Download failed: file not created.")

            # Read avatar as PNG
            try:
                avatar_bytes = await ctx.author.display_avatar.with_format('png').read()
            except Exception as av_err:
                print(f"[DEBUG][Short] avatar.read() failed: {av_err!r}")
                avatar_bytes = b""

            # Build embed (BytesIO or path; timestamp ignored by renderer)
            try:
                image_obj = await create_embed_image(
                    user=ctx.author,
                    avatar_bytes=avatar_bytes,
                    title="YouTube Short downloaded!",
                    elapsed=elapsed,
                    timestamp=None,
                    mode="short"
                )
            except Exception:
                print(f"[ERROR][Short] create_embed_image failed:\n{traceback.format_exc()}")
                image_obj = None

            # DM video
            try:
                await ctx.author.send(file=discord.File(filename))
            except discord.Forbidden:
                print("[WARNING][Short] Could not DM video file.")
            except Exception as dm_err:
                print(f"[WARNING][Short] DM failed: {dm_err}")

            # DM + channel embed (works with BytesIO or filepath)
            try:
                if image_obj:
                    if hasattr(image_obj, "read"):  # BytesIO
                        await ctx.author.send(file=discord.File(image_obj, filename="short.png"), view=InviteButton())
                        image_obj.seek(0)
                        await ctx.send(file=discord.File(image_obj, filename="short.png"), view=InviteButton())
                    elif isinstance(image_obj, str) and os.path.exists(image_obj):
                        await ctx.author.send(file=discord.File(image_obj, filename="short.png"), view=InviteButton())
                        await ctx.send(file=discord.File(image_obj, filename="short.png"), view=InviteButton())
            except Exception as dm_embed_err:
                print(f"[DEBUG][Short] DM/channel embed failed: {dm_embed_err}")

            # Done
            try:
                await status.delete()
            except Exception:
                pass

        except Exception:
            print(f"[ERROR][Short] Unexpected error:\n{traceback.format_exc()}")
            await status.edit(content="❌ Failed to download the YouTube Short. Please try again later.")
        finally:
            # Cleanup only this job's files
            shutil.rmtree(job_dir, ignore_errors=True)

async def setup(bot):
    await bot.add_cog(ShortDownloader(bot))
