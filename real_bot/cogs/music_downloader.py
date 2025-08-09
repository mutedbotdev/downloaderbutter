# real_bot/cogs/music_downloader.py

import os
import time
import shutil
import tempfile
import asyncio
import discord
from discord.ext import commands
import yt_dlp
import traceback
from urllib.parse import urlparse, parse_qs
from discord.ext.commands import Converter, BadArgument

from real_bot.utils.embed_image import create_embed_image


# ✅ Local JSON storage
from real_bot.storage import ensure_storage, get_channel_id as get_channel_id_json

# ----- URL validation -----
def is_youtube_video_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host in ("www.youtube.com", "youtube.com", "m.youtube.com") and parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            return bool(qs.get("v", [None])[0])
        if host == "youtu.be" and parsed.path.strip("/"):
            return True
        return False
    except Exception:
        return False

class YouTubeVideoURL(Converter):
    async def convert(self, ctx, argument):
        if is_youtube_video_url(argument):
            return argument
        raise BadArgument("Not a valid YouTube video URL.")

# ----- Config -----
INVITE_LINK = (
    "https://discord.com/oauth2/authorize?client_id=1398552886182412329"
    "&scope=bot+applications.commands&permissions=8"
)
COOKIE_FILE = "real_bot/real_bot/cookies_youtube.txt"
FFMPEG_PATH = os.getenv("FFMPEG_PATH")  # optional override

# Limit concurrent downloads (env MAX_CONCURRENT, default 2)
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(int(os.getenv("MAX_CONCURRENT", "2")))

class InviteButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="➕ Invite Bot", url=INVITE_LINK))

class QuietLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

class MusicDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        ensure_storage()  # make sure JSON files exist

    def _allowed_channel_id(self, guild_id: int):
        """Read from local JSON storage."""
        cid = get_channel_id_json(guild_id)
        return int(cid) if cid is not None else None

    @commands.command(name="music")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def music(self, ctx, url: YouTubeVideoURL):
        """
        Download YouTube audio (prefers M4A; falls back to MP3 if needed; max 6 minutes).
        Usage: !music <YouTube URL>
        """
        # Try to delete invoking message if allowed
        if ctx.guild and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass

        status = await ctx.send("⏳ Waiting…")
        print(f"[DEBUG] (Music) User {ctx.author.id} invoked !music with URL: {url!r}")

        # --- Probe metadata (duration gate) ---
        probe_opts = {'quiet': True, 'no_warnings': True, 'logger': QuietLogger()}
        try:
            with yt_dlp.YoutubeDL(probe_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                duration_sec = info.get('duration', 0) or 0
        except Exception as e:
            print(f"[ERROR] (Music) Metadata fetch failed: {e}")
            return await status.edit(content="❌ Could not retrieve video info. Please check your URL and try again.")

        if duration_sec > 360:  # 6 minutes
            return await status.edit(content="❌ Video is too long. Maximum allowed length is 6 minutes (360 seconds).")

        # --- Channel gate (JSON storage) ---
        if ctx.guild:
            allowed_id = self._allowed_channel_id(ctx.guild.id)
            if allowed_id is None or ctx.channel.id != allowed_id:
                correct = ctx.guild.get_channel(allowed_id) if allowed_id else None
                if correct:
                    return await status.edit(content=f"❌ Wrong channel — please use {correct.mention}")
                return await status.edit(content="❌ Download channel not configured. Use `!setup #channel`.")

        # --- Unique job directory ---
        job_dir = tempfile.mkdtemp(prefix="music_")
        await status.edit(content="🔄 Downloading music…")
        start_time = time.time()

        try:
            final_audio = None

            # 1) Prefer native M4A (no transcode)
            ydl_opts_m4a = {
                'format': 'bestaudio[ext=m4a]/bestaudio',
                'outtmpl': f"{job_dir}/%(title).80B.%(ext)s",
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'cookiefile': COOKIE_FILE,
                'logger': QuietLogger(),
                'merge_output_format': 'm4a',
            }
            if FFMPEG_PATH:
                ydl_opts_m4a['ffmpeg_location'] = FFMPEG_PATH

            async with DOWNLOAD_SEMAPHORE:
                def _run_m4a():
                    with yt_dlp.YoutubeDL(ydl_opts_m4a) as ydl:
                        info = ydl.extract_info(url, download=True)
                        return ydl.prepare_filename(info)
                try:
                    m4a_out = await asyncio.to_thread(_run_m4a)
                    if os.path.exists(m4a_out):
                        final_audio = m4a_out
                except Exception as first_err:
                    print("[WARN][Music] M4A fetch failed, will try MP3:", first_err)

            # 2) Fallback to MP3 (requires ffmpeg with mp3 codec)
            if not final_audio:
                ydl_opts_mp3 = {
                    'format': 'bestaudio/best',
                    'outtmpl': f"{job_dir}/%(title).80B.%(ext)s",
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                    'cookiefile': COOKIE_FILE,
                    'logger': QuietLogger(),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192'
                    }],
                }
                if FFMPEG_PATH:
                    ydl_opts_mp3['ffmpeg_location'] = FFMPEG_PATH

                async with DOWNLOAD_SEMAPHORE:
                    def _run_mp3():
                        with yt_dlp.YoutubeDL(ydl_opts_mp3) as ydl:
                            info = ydl.extract_info(url, download=True)
                            base = os.path.splitext(ydl.prepare_filename(info))[0]
                            return base + ".mp3"
                    final_audio = await asyncio.to_thread(_run_mp3)

            elapsed = time.time() - start_time
            print(f"[DEBUG] (Music) Download finished: {final_audio!r} in {elapsed:.2f}s")

            if not final_audio or not os.path.exists(final_audio):
                return await status.edit(content="❌ Download failed: file not found after download.")

            # Avatar bytes
            try:
                avatar_bytes = await ctx.author.display_avatar.with_format('png').read()
            except Exception as avatar_err:
                print(f"[DEBUG] (Music) avatar.read() failed: {avatar_err}")
                avatar_bytes = b""

            # Build embed image (returns BytesIO)
            image_obj = await create_embed_image(
                user=ctx.author,
                avatar_bytes=avatar_bytes,
                title="Your music was successfully downloaded",
                elapsed=elapsed,
                timestamp=None,  # timestamp not shown anymore
                mode="music"
            )

            # DM audio
            try:
                await ctx.author.send(file=discord.File(final_audio))
            except Exception as dm_err:
                print(f"[DEBUG] (Music) DM audio failed: {dm_err}")

            # DM + channel embed
            try:
                if image_obj:
                    if hasattr(image_obj, "read"):  # BytesIO
                        await ctx.author.send(file=discord.File(image_obj, filename="music.png"), view=InviteButton())
                        image_obj.seek(0)
                        await ctx.send(file=discord.File(image_obj, filename="music.png"), view=InviteButton())
                    elif isinstance(image_obj, str) and os.path.exists(image_obj):
                        await ctx.author.send(file=discord.File(image_obj, filename="music.png"), view=InviteButton())
                        await ctx.send(file=discord.File(image_obj, filename="music.png"), view=InviteButton())
            except Exception as dm_embed_err:
                print(f"[DEBUG] (Music) DM/channel embed failed: {dm_embed_err}")

            # Done
            try:
                await status.delete()
            except Exception:
                pass

        except Exception:
            print(f"[ERROR] (Music) Unexpected failure:\n{traceback.format_exc()}")
            await status.edit(content="❌ Failed to download the music. Please try again later.")
        finally:
            shutil.rmtree(job_dir, ignore_errors=True)

    @music.error
    async def music_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait `{round(error.retry_after, 1)}s` before using this command again.")

async def setup(bot):
    await bot.add_cog(MusicDownloader(bot))
