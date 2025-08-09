# real_bot/cogs/guild_setup.py

import os
import asyncio
import discord
from discord.ext import commands

# ✅ Local JSON storage helpers
from real_bot.storage import ensure_storage, set_channel_id

IMAGE_PATH = "real_bot/real_bot/mneu BOT.png"

class GuildSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        ensure_storage()  # make sure JSON files exist

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        # Pick first text channel where the bot can speak
        channel = next(
            (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
            None
        )
        if not channel:
            return

        # Welcome message
        try:
            if os.path.exists(IMAGE_PATH):
                await channel.send(
                    content="👋 Thanks for adding me! Please use **!setup #channel** to choose where I should work.",
                    file=discord.File(IMAGE_PATH)
                )
            else:
                await channel.send("👋 Thanks for adding me! Please use **!setup #channel** to choose where I should work.")
        except discord.Forbidden:
            return  # can't speak here, nothing else to do

        # Quick interactive setup (optional)
        def check(m: discord.Message):
            return (
                m.author != self.bot.user and
                m.channel == channel and
                bool(m.channel_mentions)
            )

        try:
            msg = await self.bot.wait_for("message", timeout=60.0, check=check)
            chosen = msg.channel_mentions[0]

            # Verify we can actually send messages in the chosen channel
            perms = chosen.permissions_for(guild.me)
            if not perms.send_messages:
                await channel.send("⚠️ I don’t have permission to send messages in that channel. Please choose another or fix permissions.")
                return

            set_channel_id(guild.id, chosen.id)  # ✅ save to JSON storage
            await channel.send(f"✅ Channel {chosen.mention} registered!")
        except asyncio.TimeoutError:
            await channel.send("❌ Timed out. You can run `!setup #channel` anytime.")

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: discord.ext.commands.Context):
        """
        Set the channel where the bot will accept commands.
        Usage: !setup #channel
        """
        if not ctx.message.channel_mentions:
            await ctx.send("❓ Please mention the channel you want me to work in. Example: `!setup #bot-commands`")
            return

        chosen = ctx.message.channel_mentions[0]

        # Check perms before saving
        perms = chosen.permissions_for(ctx.guild.me)
        if not perms.send_messages:
            await ctx.send("⚠️ I can’t send messages in that channel. Please adjust its permissions or pick another.")
            return

        set_channel_id(ctx.guild.id, chosen.id)  # ✅ save to JSON storage
        await ctx.send(f"✅ Channel {chosen.mention} registered.")

    @setup.error
    async def setup_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Administrator** permission to use this command.")
        else:
            raise error

async def setup(bot):
    await bot.add_cog(GuildSetup(bot))
