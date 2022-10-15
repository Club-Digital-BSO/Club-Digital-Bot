import os
import sys

import aiohttp.client_exceptions
import discord
import logging
import dotenvy
import sqlalchemy
from discord.ext import commands
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
engine = create_engine('sqlite:///../db.sqlite3')
models.base.setup(engine)


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
                instance = session.query(models.user.User).filter_by(username=user.name).first()
                if not instance:
                    logger.info(f'Enlisted {user.name}#{user.id} into user database.')
                    session.add(models.user.User(user.name, user.id))
            session.commit()


@client.event
async def on_disconnect():
    logger.error('Bot disconnected unexpectedly.')


# @client.event
# async def


@client.command()
async def project(ctx):
    await ctx.send("Pong")


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
