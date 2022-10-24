from discord import ApplicationCommand
from discord.ext import commands
from loguru import logger
from prometheus_client import Enum, Gauge
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ClubDigital import models

engine = create_engine('sqlite:///../db.sqlite3')
models.base.setup(engine)


ONLINE_STATE = Enum('bot_online_state', 'Is the Bot online', states=['starting', 'online', 'offline', 'stopping', 'stopped'])
ONLINE_STATE.state('starting')
DATABASE_CONNECTED = Gauge('bot_main_database_connected', 'Databse connection status for the main bot.')


class ProjektBot(commands.Bot):
    async def register_command(self, command: ApplicationCommand, force: bool = True,
                               guild_ids: list[int] | None = None) -> None:
        await super().register_command(command, force, guild_ids)

    async def on_ready(self):
        logger.info(f'Logged in as: {self.user}')
        logger.info('Joined to:')
        with Session(engine) as session:
            DATABASE_CONNECTED.set(1)
            for guild in self.guilds:
                logger.info(f'    {guild.name} - {guild.id}')
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