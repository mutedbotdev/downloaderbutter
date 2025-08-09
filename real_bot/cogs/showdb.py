# real_bot/cogs/showdb.py

import os
import io
import json
import glob
import discord
from discord.ext import commands

STORAGE_DIR = os.getenv("STORAGE_DIR", "real_bot/data")
GUILDS_JSON = os.path.join(STORAGE_DIR, "guilds.json")

def _load_all_json() -> dict:
    """Load all *.json files in STORAGE_DIR into a dict keyed by filename."""
    data = {}
    if not os.path.isdir(STORAGE_DIR):
        return data
    for path in glob.glob(os.path.join(STORAGE_DIR, "*.json")):
        name = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data[name] = json.load(f)
        except Exception as e:
            data[name] = f"<error reading: {e}>"
    return data

class ShowDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="showdb", aliases=["db"])
    async def show_db(self, ctx):
        """Show the stored configuration from local JSON files."""
        all_data = _load_all_json()
        if not all_data:
            return await ctx.send("📭 No local storage found yet.")

        # Prefer a friendly summary for guilds.json (guild_id -> channel_id)
        if os.path.exists(GUILDS_JSON):
            try:
                with open(GUILDS_JSON, "r", encoding="utf-8") as f:
                    guild_map = json.load(f)
            except Exception as e:
                guild_map = None
                await ctx.send(f"⚠️ Couldn't read `guilds.json`: {e}")

            if isinstance(guild_map, dict) and guild_map:
                lines = []
                for gid_str, ch_id in guild_map.items():
                    # Try to render a channel mention if we're in that guild
                    mention = f"<#{ch_id}>"
                    lines.append(f"**{gid_str}** → {mention} (`{ch_id}`)")
                text = "\n".join(lines)
                # If too long, attach as a file
                if len(text) > 1800:
                    buf = io.StringIO(text)
                    buf.seek(0)
                    return await ctx.send(
                        "📄 Guild → Channel mapping:",
                        file=discord.File(fp=io.BytesIO(buf.getvalue().encode("utf-8")), filename="guild_channel_map.txt")
                    )
                else:
                    return await ctx.send(text or "📭 No guild-channel mappings stored.")
            # If guild_map is empty, fall back to generic listing below

        # Generic listing of all JSON files (truncated to fit)
        pretty = []
        for name, content in all_data.items():
            try:
                body = json.dumps(content, indent=2, ensure_ascii=False)
            except Exception:
                body = str(content)
            header = f"📦 `{name}`"
            block = f"{header}\n```\n{body}\n```"
            pretty.append(block)

        message = "\n".join(pretty)
        if len(message) <= 1800:
            await ctx.send(message)
        else:
            # Too big — send a compact summary + attach full dump
            summary = "🧾 Stored JSON files:\n" + "\n".join([f"• {k}" for k in all_data.keys()])
            dump = json.dumps(all_data, indent=2, ensure_ascii=False)
            await ctx.send(
                summary,
                file=discord.File(fp=io.BytesIO(dump.encode("utf-8")), filename="storage_dump.json")
            )

async def setup(bot):
    await bot.add_cog(ShowDB(bot))
