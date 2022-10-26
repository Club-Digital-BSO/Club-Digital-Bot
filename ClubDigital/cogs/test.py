from typing import Optional

import discord
from discord.ext import commands
from loguru import logger


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def test(self, ctx, param: Optional[str]):
        logger.debug(f'test ({param})')
        logger.debug([i.name for i in self.test.walk_commands()])
        if param in [i.name for i in self.test.walk_commands()]:
            await self.test.get_command(param).invoke(ctx)

    @test.command()
    async def eins(self, ctx, param: Optional[str]):
        logger.debug(f'test.eins ({param})')


def setup(bot: discord.Bot):
    bot.add_cog(Test(bot))
