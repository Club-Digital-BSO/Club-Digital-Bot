import colorsys
import datetime
import pathlib
from typing import List

import discord
import pandas
from discord.ext import commands, tasks
from prometheus_client import Gauge
from loguru import logger

from ClubDigital.metrics import PROCESS_TIME

LATENCY = Gauge('bot_latency_gauge', 'The latency reported by pycord')


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ping_stats: List[dict] = []
        self.ping_timeout = 0
        logger.info('Cog "Stats" has been initialized.')

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Started Ping collection")
        if not self.collect_ping_metric.is_running():
            self.collect_ping_metric.start()

    # update interval: 42 seconds
    @tasks.loop(seconds=1)
    async def collect_ping_metric(self):
        latency = round(self.bot.latency * 1000, 3)
        if len(self.ping_stats) < 1:
            self.ping_stats.append({'value': latency, 'timestamp': datetime.datetime.now()})
            LATENCY.set(self.bot.latency)
            ping_timeout = 0
        elif self.ping_stats[-1]["value"] != latency:
            self.ping_stats.append({'value': latency, 'timestamp': datetime.datetime.now()})
            LATENCY.set(self.bot.latency)
        else:
            self.ping_timeout += 1
        if self.ping_timeout == 42:
            self.ping_stats.append({'value': latency, 'timestamp': datetime.datetime.now()})
            LATENCY.set(self.bot.latency)
            ping_timeout = 0
        while len(self.ping_stats) > 100:
            self.ping_stats.pop(0)

    @commands.command()
    async def ping(self, ctx):
        """Zeigt die aktuelle Latenz des Bots zusammen mit ein paar verwandten Statistiken an."""
        with PROCESS_TIME.time():
            ping = round(ctx.bot.latency * 1000, 1)
            ping_int = int(ping)
            hue = max(0, 120 - (ping_int // 5))
            color = int("".join([f'{hex(int(i * 255))[2:]:02}' for i in colorsys.hsv_to_rgb(hue / 360, 1, 1)]), 16)

            ts = pandas.DataFrame(self.ping_stats)
            ts.set_index('timestamp', inplace=True)

            message = discord.Embed(title='Pong', color=color)
            message.add_field(name="Latenz", value=f'{ping} ms')
            message.add_field(name="Minimum", value=f'{round(ts.min()["value"], 1)} ms')
            message.add_field(name="Mittelwert", value=f'{round(ts.median()["value"], 3)} ms')
            message.add_field(name="Maximum", value=f'{round(ts.max()["value"], 1)} ms')

            if len(self.ping_stats) > 1:
                logger.debug(ts)
                ts.cumsum()

                plot = ts.plot(legend=False)

                fig = plot.get_figure()
                fig.savefig("ping.png", dpi=100, transparent=False)
                fig.clf()

                image = discord.File("ping.png", filename="ping.png")
                message.set_image(url='attachment://ping.png')

                await ctx.send(embed=message, file=image)
                pathlib.Path("ping.png").unlink()
            else:
                await ctx.send(f'{ping} ms', embed=message)

    # @commands.command()
    # async def count(self, ctx):
    #     ctx.send(f'Es wurden seit dem Letzten neustart {self.bot.}')


def setup(bot):
    for cog in [Stats]:
        logger.info(f'Registering {cog.__name__} ...')
        bot.add_cog(cog(bot))