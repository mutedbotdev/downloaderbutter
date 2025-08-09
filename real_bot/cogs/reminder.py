# real_bot/real_bot/cogs/reminder.py

import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio

class Reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = []  # stores (user_id, channel_id, date, message)
        self.check_reminders.start()

    @commands.command(name="remindme")
    async def remindme(self, ctx, date_str: str):
        """Set a reminder: !remindme YYYY-MM-DD"""
        try:
            reminder_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            notify_date = reminder_date - timedelta(days=2)

            # Static user & channel
            user_id = 1081471425443008592
            channel_id = 1398955725920665600

            self.reminders.append((user_id, channel_id, notify_date))
            await ctx.send(f"⏰ Got it! You’ll be reminded 2 days before {reminder_date}.")
        except ValueError:
            await ctx.send("⚠️ Use format: YYYY-MM-DD (e.g. 2025-07-29)")

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        today = datetime.utcnow().date()
        to_remove = []

        for user_id, channel_id, notify_date in self.reminders:
            if notify_date <= today:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(f"<@{user_id}> ⏳ Reminder for your event in 2 days!")
                to_remove.append((user_id, channel_id, notify_date))

        self.reminders = [r for r in self.reminders if r not in to_remove]

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Reminder(bot))
