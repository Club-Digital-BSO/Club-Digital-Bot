import logging
import os
import pathlib
import sys

import aiohttp.client_exceptions
import discord
import dotenvy
import matplotlib.pyplot as plt
import sqlalchemy
from discord.ext import commands
from dotenvy import load_env, read_file
from loguru import logger
from prometheus_client import start_http_server, Gauge, Counter

from bot import ProjektBot, ONLINE_STATE
import cogs


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


bot = ProjektBot(command_prefix=commands.when_mentioned_or("!"), intents=intents)
bot.load_extensions(*[f'cogs.{item.stem}' for item in pathlib.Path(cogs.__file__).parent.iterdir() if item.is_file() and not item.stem.startswith("__")])


COMMAND_EXECUTION_TIME_PING = Gauge('command_execution_time_ping', 'The time that the ping command takes to execute')
START_TIME = Gauge('bot_start_time', 'The timestamp when the bot was last started')
EXCEPTION_COUNT = Counter("bot_exception_count", "Numerof exceptions from the Bot.")


if __name__ == '__main__':
    logger.info("Versionsinfo:")
    logger.info(f'    Python {sys.version} auf {sys.platform}')
    logger.info(f'    Pycord {discord.__version__}')
    logger.info(f'    SQLAlchemy {sqlalchemy.__version__}')
    logger.info(f'    dotenvy {dotenvy.__version__}')
    logger.info(f'Let me join: {os.environ.get("JOIN_LINK")}')
    start_http_server(9910)
    START_TIME.set_to_current_time()
    try:
        with EXCEPTION_COUNT.count_exceptions():
            bot.run(os.environ.get("TOKEN"))
            ONLINE_STATE.state('stopped')
    except aiohttp.client_exceptions.ClientConnectionError as e:
        logger.error(f'Cound not connect to {e.host}:{e.port} {e.ssl} - {e.os_error}')
