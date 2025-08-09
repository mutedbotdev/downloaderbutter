# real_bot/cogs/removed.py

import os
import re
import json
import discord
from discord.ext import commands

STORAGE_DIR = os.getenv("STORAGE_DIR", "real_bot/data")
GUILDS_JSON = os.path.join(STORAGE_DIR, "guilds.json")

def _ensure_storage():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    if not os.path.exists(GUILDS_JSON):
        with open(GUILDS_JSON, "w", encoding="utf-8") as f:
            json.dump({}, f)

def _load_guild_map() -> dict:
    _ensure_storage()
    try:
        with open(GUILDS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _save_guild_map(data: dict) -> None:
    _ensure_storage()
    with open(GUILDS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _extract_digits(s: str) -> str:
    # Pull out the first long number (works with mentions like <#123...>)
    m = re.search(r"\d{5,}", s or "")
    return m.group(0) if m else ""

class RemoveDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="removedb", aliases=["cleardb", "unsetchannel"])
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def remove_db(self, ctx, *, ident: str):
        """
        Remove stored channel mapping(s).
        Usage:
          - !removedb #channel
          - !removedb 123456789012345678   (channel ID)
          - !removedb guild:987654321098765432  (guild ID)
        """
        _ensure_storage()
        guild_map = _load_guild_map()
        if not guild_map:
            return await ctx.send("📭 No stored mappings found.")

        ident = ident.strip()
        deleted_keys = []

        # Support "guild:<id>" to remove a mapping by guild ID
        if ident.lower().startswith("guild:"):
            gid = _extract_digits(ident)
            if gid and gid in guild_map:
                del guild_map[gid]
                deleted_keys.append(gid)
        else:
            # Otherwise treat as channel mention/ID and remove any guilds pointing to it
            ch_id = _extract_digits(ident)
            if ch_id:
                to_delete = [gid for gid, saved_ch in guild_map.items() if str(saved_ch) == ch_id]
                for gid in to_delete:
                    del guild_map[gid]
                deleted_keys.extend(to_delete)

        if deleted_keys:
            _save_guild_map(guild_map)
            await ctx.send(f"🗑️ Removed {len(deleted_keys)} mapping(s): `{', '.join(deleted_keys)}`.")
        else:
            await ctx.send("❌ Nothing matched. Provide a valid channel mention/ID or `guild:<id>`.")

    @remove_db.error
    async def remove_db_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Administrator** permissions to use this command.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait `{round(error.retry_after, 1)}s` before trying again.")
        else:
            await ctx.send("⚠️ An unexpected error occurred.")
            raise error

async def setup(bot):
    await bot.add_cog(RemoveDB(bot))
