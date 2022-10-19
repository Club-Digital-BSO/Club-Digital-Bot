import discord
import typing
from discord.ext import commands, tasks
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ClubDigital import models
from loguru import logger


class Project(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        engine = create_engine('sqlite:///../db.sqlite3')
        self.session = Session(engine)

    @commands.group()
    async def project(self, ctx):
        """Verwaltet die Projekte der AG."""
        pass

    @project.command(name="list")
    async def list_projects(self, ctx):
        """Listet alle bekannten Projekte auf."""
        with ctx.typing():
            data = self.session.query(models.Project).all()
            message = "**Projects**\n"
            for project in data:
                message += f'*{project.name}:* {project.description}\n'
            await ctx.send(message)

    @project.command(name="add")
    async def add_project(self, ctx, name: str, description: str):
        """Legt ein neues Projekt an."""
        with ctx.typing():
            instance = self.session.query(models.project.Project).filter_by(name=name).first()
            if not instance:
                self.session.add(models.project.Project(name, description))
                self.session.commit()
                await ctx.send(f'Added a project called "{name}".')
            else:
                await ctx.send(f'This Project already exists!')

    @project.command(name="rm")
    async def delete_project(self, ctx, name: str):
        """Entfernt Projekte."""
        with ctx.typing():
            instance = self.session.query(models.Project).filter_by(name=name).first()
            if instance:
                self.session.delete(instance)
                self.session.commit()
                await ctx.send(f'Projekt "{instance.name}" wurde entfernt.')
            else:
                await ctx.send(f'Projekt existiert nicht.')

    @project.command(name="join")
    async def join_project(self, ctx, prj: str, *users: typing.Optional[discord.Member]):
        """Fügt einen User einem Projekt hinzu."""
        logger.debug(users)
        message = ""
        users = list(users)
        if len(users) == 0:
            users.append(ctx.message.author)

        with ctx.typing():
            for user in users:
                usr = self.session.query(models.User).filter_by(dc_id=user.id).first()
                proj = self.session.query(models.Project).filter_by(name=prj).first()
                if all([usr, proj]):
                    if usr.project_id is None:
                        message += f'Benutzer {usr.username} zu {prj} hinzugefügt.\n'
                    else:
                        old = self.session.query(models.Project).filter_by(id=usr.project_id).first()
                        message += f'Benutzer {usr.username} wurde von {old.name} zu {proj.name} verschoben.\n'
                    usr.project_id = proj.id
            self.session.commit()
            await ctx.send(message)

    @project.command(name="leave")
    async def leave_project(self, ctx, *users: typing.Optional[discord.Member]):
        """Entfernt Benutzer aus einem Projekt."""
        with ctx.typing():
            message = ""
            for user in users:
                usr = self.session.query(models.User).filter_by(dc_id=user.id).first()
                if usr:
                    logger.debug(usr)
                    prj = self.session.query(models.Project).filter_by(id=usr.project_id).first()
                    message += f'Benutzer {usr.username} wurde aus {prj.name} entfernt.\n'
                    usr.project_id = None
            self.session.commit()
            await ctx.send(message)

    @project.command(name="info")
    async def info_project(self, ctx, proj: str):
        """Git Detailinformationen über ein spezielles Projekt."""
        prj = self.session.query(models.Project).filter_by(name=proj).first()
        message = f'**Projektname:** {prj.name}\n\n' \
                  f'**Projektbeschreibung:**\n{prj.description}\n\n**Mitglieder:**\n'
        for user in self.session.query(models.User).filter_by(project_id=prj.id):
            message += f'{user.username}\n'
        await ctx.send(message)


def setup(bot: discord.Bot):
    bot.add_cog(Project(bot))
