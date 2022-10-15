import os
import sys
import discord
import logging
import dotenvy
import sqlalchemy
from discord.ext import commands
from dotenvy import load_env, read_file
import pathlib
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import models


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
    print(f'Logged in as: {client.user}')
    print('Joined to:')
    with Session(engine) as session:
        for guild in client.guilds:
            print(f'    {guild.name} - {guild.id}')
            for user in guild.members:
                print(user.name)
                instance = session.query(models.user.User).filter_by(username=user.name).first()
                if not instance:
                    session.add(models.user.User(user.name))
            session.commit()


@client.command()
async def project(ctx):
    await ctx.send("Pong")


if __name__ == '__main__':
    print("Versionsinfo:")
    print(f'    Python {sys.version} auf {sys.platform}')
    print(f'    Pycord {discord.__version__}')
    print(f'    SQLAlchemy {sqlalchemy.__version__}')
    print(f'    dotenvy {dotenvy.__version__}')
    print(f'Let me join: {os.environ.get("JOIN_LINK")}')
    client.run(os.environ.get("TOKEN"))


