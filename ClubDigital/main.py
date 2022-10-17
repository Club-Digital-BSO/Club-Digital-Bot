import os
import sys
import typing

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
                if user.name == 'Club-Digital':
                    continue
                instance = session.query(models.user.User).filter_by(username=user.name).first()
                if not instance:
                    logger.info(f'Enlisted {user.name}#{user.id} into user database.')
                    session.add(models.user.User(user.name, user.id))
            session.commit()


@client.event
async def on_disconnect():
    logger.error('Bot disconnected unexpectedly.')


@client.event
async def on_member_joined(member):
    with Session(engine) as session:
        instance = session.query(models.user.User).filter_by(username=member.name).first()
        if not instance:
            logger.info(f'Enlisted {member.name}#{member.id} into user database.')
            session.add(models.user.User(member.name, member.id))
        session.commit()


@client.event
async def on_resumed():
    logger.info('Bot resumed normal operation')


@client.group()
async def project(ctx):
    """Verwaltet die Projekte der AG."""
    pass


@project.command(name="list")
async def list_projects(ctx):
    """Listet alle pekannten Projekte auf."""
    with Session(engine) as session:
        data = session.query(models.project.Project).all()
        message = "**Projects**\n"
        for project in data:
            message += f'*{project.name}:* {project.description}\n'
        await ctx.send(message)


@project.command(name="add")
async def add_project(ctx, name: str, description: str):
    """Legt ein neues Projekt an."""
    with Session(engine) as session:
        instance = session.query(models.project.Project).filter_by(name=name).first()
        if not instance:
            session.add(models.project.Project(name, description))
            session.commit()
            await ctx.send(f'Added a project called "{name}".')
        else:
            await ctx.send(f'This Project already exists!')


@project.command(name="rm")
async def delete_project(ctx, name: str):
    """Entfernt Projekte."""
    with Session(engine) as session:
        instance = session.query(models.Project).filter_by(name=name).first()
        if instance:
            session.delete(instance)
            session.commit()
            await ctx.send(f'Projekt "{instance.name}" wurde entfernt.')
        else:
            await ctx.send(f'Projekt existiert nicht.')


@project.command(name="join")
async def join_project(ctx, prj: str, *users: typing.Optional[discord.Member]):
    """Fügt einen User einem Projekt hinzu."""
    logger.debug(users)
    message = ""
    users = list(users)
    if len(users) == 0:
        users.append(ctx.message.author)

    with Session(engine) as session:
        for user in users:
            usr = session.query(models.User).filter_by(dc_id=user.id).first()
            proj = session.query(models.Project).filter_by(name=prj).first()
            if all([usr, proj]):
                if usr.project_id is None:
                    message += f'Benutzer {usr.username} zu {prj} hinzugefügt.\n'
                else:
                    old = session.query(models.Project).filter_by(id=usr.project_id).first()
                    message += f'Benutzer {usr.username} wurde von {old.name} zu {proj.name} verschoben.\n'
                usr.project_id = proj.id
        session.commit()
        await ctx.send(message)


@project.command(name="leave")
async def leave_project(ctx, *users: typing.Optional[discord.Member]):
    """Entfernt Benutzer aus einem Projekt."""
    with Session(engine) as session:
        message = ""
        for user in users:
            usr = session.query(models.User).filter_by(dc_id=user.id).first()
            if usr:
                logger.debug(usr)
                prj = session.query(models.Project).filter_by(id=usr.project_id).first()
                message += f'Benutzer {usr.username} wurde aus {prj.name} entfernt.\n'
                usr.project_id = None
        session.commit()
        await ctx.send(message)


@project.command(name="info")
async def info_project(ctx, proj: str):
    """Git Detailinformationen über ein spezielles Projekt."""
    with Session(engine) as session:
        prj = session.query(models.Project).filter_by(name=proj).first()
        message = f'**Projektname:** {prj.name}\n\n' \
                  f'**Projektbeschreibung:**\n{prj.description}\n\n**Mitglieder:**\n'
        for user in session.query(models.User).filter_by(project_id=prj.id):
            message += f'{user.username}\n'
        await ctx.send(message)


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
