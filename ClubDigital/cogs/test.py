from typing import Optional

import discord
from discord.ext import commands
from loguru import logger


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def test(self, ctx, param: Optional[str]):
        logger.debug(param)

    @test.command()
    async def eins(self, ctx, param: str):
        logger.debug(param)


def setup(bot: discord.Bot):
    bot.add_cog(Test(bot))