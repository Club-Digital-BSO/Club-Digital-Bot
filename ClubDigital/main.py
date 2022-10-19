import colorsys
import os
import sys
import typing

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

load_env(read_file(pathlib.Path("../.env")))
logging.basicConfig(level=logging.DEBUG)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = commands.Bot(command_prefix="!", intents=intents)
client.load_extension('cogs.project')
engine = create_engine('sqlite:///../db.sqlite3')
models.base.setup(engine)

ping_stats = []


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
                instance = session.query(models.user.User).filter_by(username=user.name).first()
                if not instance:
                    logger.info(f'Enlisted {user.name}#{user.id} into user database.')
                    session.add(models.user.User(user.name, user.id))
            session.commit()
    logging.info("Started Ping collection")
    collect_ping_metric.start()


@client.event
async def on_disconnect():
    logger.error('Bot disconnected unexpectedly.')


@client.event
async def on_member_joined(member):
    with Session(engine) as session:
        instance = session.query(models.User).filter_by(username=member.name).first()
        if not instance:
            logger.info(f'Enlisted {member.name}#{member.id} into user database.')
            session.add(models.User(member.name, member.id))
        session.commit()


@client.event
async def on_resumed():
    logger.info('Bot resumed normal operation')


# update interval: 42 seconds
@tasks.loop(seconds=42)
async def collect_ping_metric():
    ping_stats.append(round(client.latency * 1000, 3))
    while len(ping_stats) > 10:
        ping_stats.pop(0)


@client.command()
async def ping(ctx):
    ping = round(ctx.bot.latency * 1000, 1)
    ping_int = int(ping)
    hue = max(0, 120 - (ping_int // 5))
    color = int("".join([f'{hex(int(i * 255))[2:]:02}' for i in colorsys.hsv_to_rgb(hue / 360, 1, 1)]), 16)

    ts = pandas.Series(ping_stats, index=range(len(ping_stats)))

    message = discord.Embed(title='Pong', color=color)
    message.add_field(name="Latenz", value=f'{ping} ms')
    message.add_field(name="Mittelwert", value=f'{round(ts.median(), 3)} ms')

    if len(ping_stats) > 1:
        logger.debug(ts)
        ts.cumsum()

        plot = ts.plot()

        fig = plot.get_figure()
        fig.savefig("ping.png", dpi=100, transparent=False)
        fig.clf()

        image = discord.File("ping.png", filename="ping.png")
        message.set_image(url='attachment://ping.png')

        await ctx.send(embed=message, file=image)
        pathlib.Path("ping.png").unlink()
    else:
        await ctx.send(embed=message)


if __name__ == '__main__':
    logging.info("Versionsinfo:")
    logging.info(f'    Python {sys.version} auf {sys.platform}')
    logging.info(f'    Pycord {discord.__version__}')
    logging.info(f'    SQLAlchemy {sqlalchemy.__version__}')
    logging.info(f'    dotenvy {dotenvy.__version__}')
    logging.info(f'Let me join: {os.environ.get("JOIN_LINK")}')
    try:
        client.run(os.environ.get("TOKEN"))
    except aiohttp.client_exceptions.ClientConnectionError as e:
        logger.error(f'Cound not connect to {e.host}:{e.port} {e.ssl} - {e.os_error}')
    except aiohttp.client_exceptions.ClientConnectorError:
        pass
