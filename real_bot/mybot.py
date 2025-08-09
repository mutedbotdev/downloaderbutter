# real_bot/mybot.py
import os
import shutil
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Quiet third-party logs a bit
logging.getLogger("discord").setLevel(logging.CRITICAL)
logging.getLogger("yt_dlp").setLevel(logging.CRITICAL)
logging.getLogger().setLevel(logging.INFO)

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    case_insensitive=True,
    help_command=None,
)

@bot.event
async def on_ready():
    print(f"🤖 Bot is online as {bot.user}")
    print(f"🔍 ffmpeg path: {shutil.which('ffmpeg') or 'not found'}")
    print(f"🔧 MAX_CONCURRENT: {os.getenv('MAX_CONCURRENT', '2')}")

    cogs = [
        "real_bot.cogs.music_downloader",
        "real_bot.cogs.reel_downloader",
        "real_bot.cogs.short_downloader",
        "real_bot.cogs.converter",
        "real_bot.cogs.guild_setup",
        "real_bot.cogs.set",
        "real_bot.cogs.command",
        "real_bot.cogs.help",
        "real_bot.cogs.pfp",
        "real_bot.cogs.removed",
        "real_bot.cogs.showdb",
    ]

    loaded, failed = 0, []
    for ext in cogs:
        try:
            await bot.load_extension(ext)
            loaded += 1
        except Exception as e:
            failed.append((ext, e))

    print(f"✅ Loaded {loaded} cogs | ⚠️ Failed {len(failed)}")
    for name, err in failed:
        print(f"❌ Failed to load {name}: {err!r}")

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="!help | !commands"),
    )

@bot.event
async def on_command_error(ctx, error):
    from discord.ext.commands import CommandNotFound, CommandOnCooldown, MissingRequiredArgument
    if isinstance(error, CommandNotFound):
        return
    if isinstance(error, CommandOnCooldown):
        await ctx.send(f"⏳ Please wait `{round(error.retry_after, 1)}s` before using this command again.")
        return
    if isinstance(error, MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`. Try `!help {ctx.command.name}`.")
        return
    await ctx.send("❌ Oops, something went wrong. Use `!help` to see available commands.")
    import traceback; print(f"[ERROR] in {getattr(ctx, 'command', None)}:", traceback.format_exc())

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set in your .env")
    bot.run(DISCORD_TOKEN)
