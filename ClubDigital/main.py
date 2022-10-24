import datetime
import logging
import os
import pathlib
import sys

import aiohttp.client_exceptions
import discord
import dotenvy
import matplotlib.pyplot as plt
import sqlalchemy
from discord import ApplicationCommand
from discord.ext import commands
from dotenvy import load_env, read_file
from loguru import logger
from prometheus_client import start_http_server, Gauge, Enum
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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


class ProjektBot(commands.Bot):
    async def register_command(self, command: ApplicationCommand, force: bool = True,
                               guild_ids: list[int] | None = None) -> None:
        await super().register_command(command, force, guild_ids)

    async def on_ready(self):
        logging.info(f'Logged in as: {bot.user}')
        logging.info('Joined to:')
        with Session(engine) as session:
            DATABASE_CONNECTED.set(1)
            for guild in bot.guilds:
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
            DATABASE_CONNECTED.set(0)
        ONLINE_STATE.state('online')

    async def on_disconnect(self):
        logger.error('Bot disconnected unexpectedly.')
        ONLINE_STATE.state('offline')

    async def on_resumed(self):
        logger.info('Bot resumed normal operation')
        ONLINE_STATE.state('online')


bot = ProjektBot(command_prefix=commands.when_mentioned_or("!"), intents=intents)
bot.load_extensions('cogs.project', 'cogs.stats', 'cogs.test')

engine = create_engine('sqlite:///../db.sqlite3')
models.base.setup(engine)

ONLINE_STATE = Enum('bot_online_state', 'Is the Bot online', states=['starting', 'online', 'offline', 'stopping', 'stopped'])
COMMAND_EXECUTION_TIME_PING = Gauge('command_execution_time_ping', 'The time that the ping command takes to execute')
DATABASE_CONNECTED = Gauge('bot_main_database_connected', 'Databse connection status for the main bot.')
START_TIME = Gauge('bot_start_time', 'The timestamp when the bot was last started')

ONLINE_STATE.state('starting')


if __name__ == '__main__':
    logger.info("Versionsinfo:")
    logger.info(f'    Python {sys.version} auf {sys.platform}')
    logger.info(f'    Pycord {discord.__version__}')
    logger.info(f'    SQLAlchemy {sqlalchemy.__version__}')
    logger.info(f'    dotenvy {dotenvy.__version__}')
    logger.info(f'Let me join: {os.environ.get("JOIN_LINK")}')
    start_http_server(9910)
    START_TIME.set(datetime.datetime.now().timestamp())
    try:
        bot.run(os.environ.get("TOKEN"))
        ONLINE_STATE.state('stopped')
    except aiohttp.client_exceptions.ClientConnectionError as e:
        logger.error(f'Cound not connect to {e.host}:{e.port} {e.ssl} - {e.os_error}')
