# cogs/help.py
import discord
from discord.ext import commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Map each command to its usage text:
        self.usage = {
            "music":      "!music <YouTube URL>  – Download audio as MP3 (max 6m)",
            "reel":       "!reel <Instagram Reel URL>  – Download a reel video",
            "short":      "!short <YouTube Shorts URL>  – Download a Shorts video",
            "convert":    "!convert <.jpg attachment>  – Convert JPEG→PNG",
            # …add the rest…
        }

    @commands.command(name="help")
    async def help(self, ctx, *, cmd: str = None):
        """Show general help or detailed usage for one command."""
        if cmd:
            key = cmd.lower()
            text = self.usage.get(key)
            if not text:
                return await ctx.send(f"❌ I don’t know `{cmd}`. Try `!help` for the list.")
            return await ctx.send(f"**Usage for `{key}`**\n```{text}```")

        # no specific command → list them all
        embed = discord.Embed(
            title="Available Commands",
            color=discord.Color.blurple()
        )
        for name, text in self.usage.items():
            embed.add_field(name=f"`{name}`", value=text, inline=False)
        embed.set_footer(text="Type !help <command> for details.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
