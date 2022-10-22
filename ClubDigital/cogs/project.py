import logging
import sys
from enum import Enum

import discord
import typing
from discord.ext import commands, pages
from prometheus_client import Gauge
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ClubDigital import models
from loguru import logger


DATABASE_CONNECTED = Gauge('bot_project_cog_database_connected', "State of database connection for the project cog")


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
        DATABASE_CONNECTED.set(1)

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
            DATABASE_CONNECTED.set(0)

    @commands.Cog.listener()
    async def on_connect(self):
        logger.debug("Project cog connect listener.")
        if not self.session.is_active:
            self.session = Session(self.engine)
            logger.info("Opening a new database connection for Project cog.")
            DATABASE_CONNECTED.set(1)

    @commands.Cog.listener()
    async def on_resumed(self):
        logger.debug("Project cog resumed listener.")
        if not self.session.is_active:
            self.session = Session(self.engine)
            logger.info("Opening a new database connection for Project cog.")
            DATABASE_CONNECTED.set(1)

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
                message = "Projektliste:"
                embeds = []
                for project in data:
                    embed = discord.Embed(title=project.name, description=project.description, color=project.color)
                    if len(project.repository) > 0:
                        embed.add_field(name=f"Repository{'s' if len(project.repository) > 1 else ''}",
                                        value='\n'.join([f'{i.label}: http://{i.link}' for i in project.repository]))
                    if len(project.users) > 0:
                        embed.add_field(name=f'Mitglied{"er" if len(project.users) > 1 else ""}',
                                        value='\n'.join([i.name for i in project.users]))
                    if project.leader:
                        leader: models.User = self.session.query(models.User).filter_by(id=project.leader)
                        embed.add_field(name="Leiter", value=leader.username)
                    embeds.append(embed)
                await ctx.send(message, embeds=embeds)

    @project.command(name="add")
    async def add(self, ctx, name: str, description: str):
        """Legt ein neues Projekt an."""
        with ctx.typing():
            instance = self.session.query(models.project.Project).filter_by(name=name).first()
            if not instance:
                role = await ctx.guild.create_role(name=name, hoist=True, mentionable=True,
                                            reason="Project was created, so the fitting role has to be created too.")
                lr = await ctx.guild.create_role(name=f'{name}-Lead', mentionable=True,
                                            reason="A project needs a leader, so it needs to be created.")

                self.session.add(models.project.Project(name, description, role.id, lr.id))
                self.session.commit()
                await ctx.send(f'Added a project called "{name}".')
            else:
                await ctx.send(f'This Project already exists!')
            logger.info("Creating roles")

    @project.command(name="rm")
    async def delete(self, ctx, name: str):
        """Entfernt Projekte."""
        with ctx.typing():
            instance = self.session.query(models.Project).filter_by(name=name).first()
            if instance:
                prj_role = ctx.guild.get_role(instance.role)
                if not prj_role:
                    logger.info(f"Project role for {instance.name} was already absent.")
                else:
                    await prj_role.delete(reason="This is no longer needed.")
                prl_role = ctx.guild.get_role(instance.leader_role)
                if not prl_role:
                    logger.info(f'Project-Leader role for {instance.name} was already absent.')
                else:
                    await prl_role.delete(reason="This is no longer needed.")
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
                usr: models.User = self.session.query(models.User).filter_by(dc_id=user.id).first()
                proj: models.Project = self.session.query(models.Project).filter_by(name=prj).first()
                if all([usr, proj]):
                    if usr.project_id is None:
                        message += f'Benutzer {usr.username} zu {prj} hinzugefügt.\n'
                    else:
                        old = self.session.query(models.Project).filter_by(id=usr.project_id).first()
                        message += f'Benutzer {usr.username} wurde von {old.name} zu {proj.name} verschoben.\n'
                        if old.role in user.roles:
                            await user.remove_roles(old.role)
                        if old.leader_role in user.roles:
                            await user.remove_roles(old.leader_role)
                    usr.project_id = proj.id
                    await user.add_roles(ctx.guild.get_role(proj.role))
            self.session.commit()
            await ctx.send(message)

    @project.command(name="leave")
    async def leave(self, ctx, *users: typing.Optional[discord.Member]):
        """Entfernt Benutzer aus einem Projekt."""
        with ctx.typing():
            message = ""
            users = list(users)
            if len(users) == 0:
                users.append(ctx.message.author)
            for user in users:
                usr = self.session.query(models.User).filter_by(dc_id=user.id).first()
                if usr:
                    logger.debug(usr)
                    prj = self.session.query(models.Project).filter_by(id=usr.project_id).first()
                    message += f'Benutzer {usr.username} wurde aus {prj.name} entfernt.\n'
                    usr.project_id = None
                    if prj.role in user.roles:
                        await user.remove_roles(prj.role)
                    if prj.leader_role in user.roles:
                        await user.remove_roles(prj.leader_role)
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
        await ctx.send(f"{label} wurde erfolgreich zum Projekt \"{project}\" hinzugefügt.")

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
