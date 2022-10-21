import logging
import sys
from enum import Enum

import discord
import typing
from discord.ext import commands, pages
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ClubDigital import models
from loguru import logger


class ProjectSettings(Enum):
    ADD_REPO = "add_repo"


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


class Project(commands.Cog):
    """
    Alles, was mit Projekten und Schülern zu tun hat.
    """
    def __init__(self, bot):
        self.bot = bot
        self.engine = create_engine('sqlite:///../db.sqlite3')
        self.session = Session(self.engine)

    @commands.Cog.listener()
    async def on_member_joined(self, member):
        instance = self.session.query(models.User).filter_by(username=member.name).first()
        if not instance:
            logger.info(f'Enlisted {member.name}#{member.id} into user database.')
            self.session.add(models.User(member.name, member.id))
        self.session.commit()

    @commands.Cog.listener()
    async def on_disconnect(self):
        if self.session.is_active:
            self.session.close()
            logger.info("Closing the database connection for Project cog.")

    @commands.Cog.listener()
    async def on_connect(self):
        if not self.session.is_active:
            self.session = Session(self.engine)
            logger.info("Opening a new database connection for Project cog.")

    @commands.group()
    async def project(self, ctx):
        """Verwaltet die Projekte der AG."""
        pass

    @project.command(name="list")
    async def list(self, ctx):
        """Listet alle bekannten Projekte auf."""
        with ctx.typing():
            data = self.session.query(models.Project).all()
            if len(data) <= 10:
                message = "**Projects**\n"
                for project in data:
                    message += f'*{project.name}:*\n{project.description}\n\n'
                await ctx.send(message)

    @project.command(name="add")
    async def add(self, ctx, name: str, description: str):
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
    async def delete(self, ctx, name: str):
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
    async def join(self, ctx, prj: str, *users: typing.Optional[discord.Member]):
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
    async def leave(self, ctx, *users: typing.Optional[discord.Member]):
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
    async def info(self, ctx, proj: str):
        """Git Detailinformationen über ein spezielles Projekt."""
        prj: models.Project = self.session.query(models.Project).filter_by(name=proj).first()
        message = f'**Projektname:** {prj.name}\n\n'
        if len(prj.repository) > 0:
            message += f"**Repository{'s' if len(prj.repository) > 1 else ''}:**\n"
            for repo in prj.repository:
                message += f'http://{repo.link}\n'
            message += '\n'
        message += f'**Projektbeschreibung:**\n{prj.description}\n\n**Mitglieder:**\n'
        for user in self.session.query(models.User).filter_by(project_id=prj.id):
            message += f'{user.username}\n'
        await ctx.send(message)

    @project.group()
    async def repo(self, ctx):
        pass

    @repo.command(name="add")
    async def repo_add(self, ctx, project: str, label: str, link: str):
        prj = self.session.query(models.Project).filter_by(name=project).first()
        if not prj:
            await ctx.send("Dieses Projekt existiert nicht!\n"
                     "Bitte stelle sicher, dass du dich nicht vertippt hast.")
            return
        repo = self.session.query(models.Repo).filter_by(label=label, project=prj.id).first()
        if repo:
            await ctx.send("Dieses Repo existiert bereits und kann nicht mehr hinzugefügt werden!\n"
                     f"Bitte verwende `!project repo modify {project} {label} {link}`!")
            return
        self.session.add(models.Repo(prj.id, label, link))
        self.session.commit()
        await   ctx.send(f"{label} wurde erfolgreich zum Projekt \"{project}\" hinzugefügt.")

    @repo.command(name="rm")
    async def repo_remove(self, ctx, project:str, label: str):
        prj = self.session.query(models.Project).filter_by(name=project).first()
        if not prj:
            await ctx.send("Dieses Projekt existiert nicht!\n"
                     "Bitte stelle sicher, dass du dich nicht vertippt hast.")
            return
        repo = self.session.query(models.Repo).filter_by(label=label, project=prj.id).first()
        if not repo:
            await ctx.send(f"Das Repository {label} wurde nicht gefunden!\n"
                     f"Bitte stelle sicher, dass du dich nicht vertippt hast.")
            return
        self.session.delete(repo)
        self.session.commit()
        await ctx.send(f'Das Repository {label} wurde entfernt.')

    @repo.command(name="modify")
    async def repo_modify(self, ctx, project: str, label: str, link: str):
        prj = self.session.query(models.Project).filter_by(name=project).first()
        if not prj:
            await ctx.send("Dieses Projekt existiert nicht!\n"
                     "Bitte stelle sicher, dass du dich nicht vertippt hast.")
            return
        repo = self.session.query(models.Repo).filter_by(label=label, project=prj.id).first()
        if not repo:
            await ctx.send(f"Das Repository {label} wurde nicht gefunden!\n"
                     f"Bitte stelle sicher, dass du dich nicht vertippt hast.")
            return
        repo.link = link
        self.session.commit()
        await ctx.send(f"Das Repository {label} wurde erfolgreich aktualisiert.")


def setup(bot: discord.Bot):
    bot.add_cog(Project(bot))
