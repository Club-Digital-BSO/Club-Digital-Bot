from sqlalchemy import Column, String, Integer, ForeignKey
from .base import Base
from sqlalchemy.orm import relationship


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    leader = Column(Integer)
    role = Column(Integer, nullable=False, unique=True, default=0)
    leader_role = Column(Integer, nullable=False, unique=True, default=0)
    color = Column(String, default="10ff10")

    repository = relationship("Repo")
    users = relationship("User")

    def __init__(self, name: str, description: str, role: int, lr: int):
        super(Project, self).__init__()
        self.name = name
        self.description = description
        self.role = role
        self.leader_role = lr


class Repo(Base):
    __tablename__ = "repos"
    id = Column(Integer, primary_key=True)
    project = Column(ForeignKey("projects.id"))
    label = Column(String, nullable=False)
    link = Column(String, nullable=False)

    def __init__(self, project, label, link):
        self.project = project
        self.link = link
        self.label = label
