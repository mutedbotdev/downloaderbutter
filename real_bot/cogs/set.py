# real_bot/cogs/set.py

import discord
from discord.ext import commands

# ✅ Use your local JSON storage helpers
from real_bot.storage import ensure_storage, set_channel_id

class ChannelSetter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        ensure_storage()  # make sure the JSON files exist

    @commands.command(name="setchannel", aliases=["set"])
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.user)  # ⏳ 1 use per 10s per user
    async def set_command_channel(self, ctx, channel: discord.TextChannel | None = None):
        """Set the designated command channel for this server.
        Usage: !setchannel #channel
        """
        # Try to delete the invoking message if allowed (keeps channels clean)
        if ctx.guild and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass

        # Allow either typed arg or plain mention in the message
        if channel is None and ctx.message.channel_mentions:
            channel = ctx.message.channel_mentions[0]

        if channel is None:
            return await ctx.send("❓ Please mention the channel you want me to use. Example: `!setchannel #bot-commands`")

        # Validate it's a text channel we can talk in
        if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.ForumChannel, discord.StageChannel, discord.VoiceChannel)):
            return await ctx.send("❌ That doesn't look like a text channel I can use.")

        perms = channel.permissions_for(ctx.guild.me)
        if not perms.send_messages:
            return await ctx.send(f"❌ I don't have permission to send messages in {channel.mention}. Please adjust channel permissions and try again.")

        # Save to local JSON storage
        try:
            set_channel_id(ctx.guild.id, channel.id)
        except Exception as e:
            await ctx.send("⚠️ Failed to save the setting. Please try again.")
            raise e

        await ctx.send(f"✅ Channel {channel.mention} is now the designated command channel.")

    @set_command_channel.error
    async def set_command_channel_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Administrator** permission to use this command.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait `{round(error.retry_after, 1)}s` before trying again.")
        else:
            await ctx.send("⚠️ An unexpected error occurred.")
            raise error  # still log it

async def setup(bot):
    await bot.add_cog(ChannelSetter(bot))
