import colorsys
import datetime
import os
import sys
from typing import List

import aiohttp.client_exceptions
import discord
import logging
import dotenvy
import sqlalchemy
import pandas
from discord.ext import commands
from discord.ext import tasks
from dotenvy import load_env, read_file
import pathlib
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from loguru import logger
import matplotlib.pyplot as plt
from prometheus_client import start_http_server, Gauge, Enum

import models


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
logging.basicConfig(level=logging.DEBUG)

load_env(read_file(pathlib.Path("../.env")))

plt.style.use("dark_background")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = commands.Bot(command_prefix="!", intents=intents)
client.load_extension('cogs.project')
engine = create_engine('sqlite:///../db.sqlite3')
models.base.setup(engine)

ping_stats: List[dict] = []
ping_timeout = 0

LATENCY = Gauge('bot_latency_gauge', 'The latency reported by pycord')
ONLINE_STATE = Enum('bot_online_state', 'Is the Bot online', states=['starting', 'online', 'offline', 'stopping', 'stopped'])
COMMAND_EXECUTION_TIME_PING = Gauge('command_execution_time_ping', 'The time that the ping command takes to execute')

ONLINE_STATE.state('starting')


@client.event
async def on_ready():
    logging.info(f'Logged in as: {client.user}')
    logging.info('Joined to:')
    with Session(engine) as session:
        for guild in client.guilds:
            logging.info(f'    {guild.name} - {guild.id}')
            for user in guild.members:
                # logging.info(f'        {user.name}')
                # print(user.__dir__())
                if user.name == 'Club-Digital':
                    continue
                instance = session.query(models.User).filter_by(username=user.name).first()
                if not instance:
                    logger.info(f'Enlisted {user.name}#{user.id} into user database.')
                    session.add(models.User(user.name, user.id))
            session.commit()
    logging.info("Started Ping collection")
    collect_ping_metric.start()
    ONLINE_STATE.state('online')


@client.event
async def on_disconnect():
    logger.error('Bot disconnected unexpectedly.')
    ONLINE_STATE.state('offline')


@client.event
async def on_resumed():
    logger.info('Bot resumed normal operation')
    ONLINE_STATE.state('online')


# update interval: 42 seconds
@tasks.loop(seconds=1)
async def collect_ping_metric():
    global ping_timeout
    latency = round(client.latency * 1000, 3)
    if len(ping_stats) < 1:
        ping_stats.append({'value': latency, 'timestamp': datetime.datetime.now()})
        LATENCY.set(client.latency)
        ping_timeout = 0
    elif ping_stats[-1]["value"] != latency:
        ping_stats.append({'value': latency, 'timestamp': datetime.datetime.now()})
        LATENCY.set(client.latency)
    else:
        ping_timeout += 1
    if ping_timeout == 42:
        ping_stats.append({'value': latency, 'timestamp': datetime.datetime.now()})
        LATENCY.set(client.latency)
        ping_timeout = 0
    while len(ping_stats) > 100:
        ping_stats.pop(0)


@client.command()
async def ping(ctx):
    """Zeigt die aktuelle Latenz des Bots zusammen mit ein paar verwandten Statistiken an."""
    ping = round(ctx.bot.latency * 1000, 1)
    ping_int = int(ping)
    hue = max(0, 120 - (ping_int // 5))
    color = int("".join([f'{hex(int(i * 255))[2:]:02}' for i in colorsys.hsv_to_rgb(hue / 360, 1, 1)]), 16)

    ts = pandas.DataFrame(ping_stats)
    ts.set_index('timestamp', inplace=True)

    message = discord.Embed(title='Pong', color=color)
    message.add_field(name="Latenz", value=f'{ping} ms')
    message.add_field(name="Minimum", value=f'{round(ts.min()["value"], 1)} ms')
    message.add_field(name="Mittelwert", value=f'{round(ts.median()["value"], 3)} ms')
    message.add_field(name="Maximum", value=f'{round(ts.max()["value"], 1)} ms')

    if len(ping_stats) > 1:
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


if __name__ == '__main__':
    logger.info("Versionsinfo:")
    logger.info(f'    Python {sys.version} auf {sys.platform}')
    logger.info(f'    Pycord {discord.__version__}')
    logger.info(f'    SQLAlchemy {sqlalchemy.__version__}')
    logger.info(f'    dotenvy {dotenvy.__version__}')
    logger.info(f'Let me join: {os.environ.get("JOIN_LINK")}')
    start_http_server(9910)
    try:
        client.run(os.environ.get("TOKEN"))
        ONLINE_STATE.state('stopped')
    except aiohttp.client_exceptions.ClientConnectionError as e:
        logger.error(f'Cound not connect to {e.host}:{e.port} {e.ssl} - {e.os_error}')
    except aiohttp.client_exceptions.ClientConnectorError:
        pass
