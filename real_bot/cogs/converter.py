# real_bot/cogs/converter.py

import os
import io
import time
import traceback
from PIL import Image
import discord
from discord.ext import commands

from real_bot.utils.embed_image import create_embed_image
from real_bot.storage import ensure_storage, get_channel_id

DOWNLOAD_PATH = "real_bot/real_bot/downloads"
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

INVITE_LINK = (
    "https://discord.com/oauth2/authorize?client_id=1398552886182412329"
    "&scope=bot+applications.commands&permissions=8"
)

class InviteButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="➕ Invite Bot", url=INVITE_LINK))

class ConverterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        ensure_storage()  # make sure JSON files exist

    @commands.command(name="convert")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def convert(self, ctx):
        """
        Convert a JPEG image to PNG.
        Usage: `!convert` (attach a .jpg/.jpeg file to the message)
        """
        # Attempt to delete invoking message if bot has permission
        if ctx.guild and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass

        # Channel restriction (from local JSON store)
        if ctx.guild:
            allowed_id = get_channel_id(ctx.guild.id)
            try:
                allowed_id_int = int(allowed_id) if allowed_id is not None else None
            except (TypeError, ValueError):
                allowed_id_int = None

            if allowed_id_int is None or ctx.channel.id != allowed_id_int:
                correct = ctx.guild.get_channel(allowed_id_int) if allowed_id_int else None
                if correct:
                    return await ctx.send(f"❌ Wrong channel — please use {correct.mention}")
                return await ctx.send("❌ Download channel not configured. Use `!setup #channel`.")

        # Ensure there's an attachment
        if not ctx.message.attachments:
            return await ctx.send("📎 Please attach a JPEG image to convert.")

        attachment = ctx.message.attachments[0]

        # Accept by extension OR content type
        is_jpeg_ext = attachment.filename.lower().endswith((".jpeg", ".jpg"))
        is_jpeg_ct = (attachment.content_type or "").lower().startswith("image/jpeg")
        if not (is_jpeg_ext or is_jpeg_ct):
            return await ctx.send("❌ Only JPEG images are supported. Please use a .jpg or .jpeg file.")

        status = await ctx.send("🔄 Converting image to PNG...")
        start_time = time.perf_counter()

        try:
            async with ctx.typing():
                data = await attachment.read()
                img = Image.open(io.BytesIO(data)).convert("RGB")

                png_buffer = io.BytesIO()
                img.save(png_buffer, format="PNG")
                png_buffer.seek(0)

                elapsed = time.perf_counter() - start_time
                print(f"[DEBUG][Convert] Converted {attachment.filename} in {elapsed:.2f}s")

                # Read avatar as PNG
                try:
                    avatar_bytes = await ctx.author.display_avatar.with_format('png').read()
                except Exception as av_err:
                    print(f"[DEBUG][Convert] avatar.read() failed: {av_err!r}")
                    avatar_bytes = b""

                # Build the embed image (returns BytesIO)
                try:
                    embed_io = await create_embed_image(
                        user=ctx.author,
                        avatar_bytes=avatar_bytes,
                        title="Your image was successfully converted to PNG",
                        elapsed=elapsed,
                        timestamp=None,   # renderer ignores timestamp now
                        mode="convert"
                    )
                except Exception:
                    print(f"[ERROR][Convert] create_embed_image failed:\n{traceback.format_exc()}")
                    embed_io = None

                # DM the converted image and the embed
                try:
                    await ctx.author.send(file=discord.File(png_buffer, filename="converted.png"))
                    if embed_io:
                        try:
                            embed_io.seek(0)
                        except Exception:
                            pass
                        await ctx.author.send(
                            file=discord.File(embed_io, filename="embed.png"),
                            view=InviteButton()
                        )
                except discord.Forbidden:
                    print("[WARNING][Convert] Unable to DM user, skipping.")

                # Send embed in channel
                if embed_io:
                    try:
                        embed_io.seek(0)
                    except Exception:
                        pass
                    await ctx.send(file=discord.File(embed_io, filename="embed.png"), view=InviteButton())

        except Exception:
            print(f"[ERROR][Convert] Unexpected failure:\n{traceback.format_exc()}")
            await ctx.send("❌ Failed to convert image. Please try again later.")

        finally:
            # Delete status message if bot has permission
            try:
                if 'status' in locals() and status and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                    await status.delete()
            except Exception:
                pass
            # Cleanup (nothing created on disk here, but keep sweep in case)
            for f in os.listdir(DOWNLOAD_PATH):
                try:
                    os.remove(os.path.join(DOWNLOAD_PATH, f))
                except:
                    pass

    @convert.error
    async def convert_error(self, ctx, error):
        from discord.ext.commands import CommandOnCooldown
        if isinstance(error, CommandOnCooldown):
            await ctx.send(f"⏳ Please wait `{round(error.retry_after,1)}s` before using `!convert` again.")
        else:
            raise error

async def setup(bot):
    await bot.add_cog(ConverterCog(bot))
