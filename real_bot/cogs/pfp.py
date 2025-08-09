import discord
from discord.ext import commands

class Pfp(commands.Cog):
    """
    Sends the profile picture of a user.
    Usage: !pfp [@user]
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pfp")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pfp(self, ctx, member: discord.Member = None):
        # Default to the command author if no member is specified
        target = member or ctx.author
        # Build embed with the user's avatar
        embed = discord.Embed(
            title=f"{target.display_name}'s Profile Picture",
            color=discord.Color.blurple()
        )
        embed.set_image(url=target.display_avatar.replace(size=1024).url)
        await ctx.send(embed=embed)

    @pfp.error
    async def pfp_error(self, ctx, error):
        from discord.ext.commands import CommandOnCooldown
        if isinstance(error, CommandOnCooldown):
            await ctx.send(f"⏳ Please wait `{round(error.retry_after, 1)}s` before using this command again.")
        else:
            raise error

async def setup(bot):
    await bot.add_cog(Pfp(bot))
