# command.py

import discord
from discord.ext import commands
import os

IMAGE_PATH = "real_bot/real_bot/mneu BOT.png"


class CommandHelp(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="commands", aliases=["cmds", "cmd",])
    @commands.cooldown(
        1, 10, commands.BucketType.user)  # ⏳ 1 use every 10 seconds per user
    async def show_commands_image(self, ctx):
        if not os.path.exists(IMAGE_PATH):
            await ctx.send("❌ Command image not found.")
            return

        await ctx.send(file=discord.File(IMAGE_PATH))

    @show_commands_image.error
    async def show_commands_image_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏳ Please wait `{round(error.retry_after, 1)}s` before using `!commands` again."
            )
        else:
            raise error


async def setup(bot):
    await bot.add_cog(CommandHelp(bot))
