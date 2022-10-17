from sqlalchemy import Column, String, Integer, ForeignKey
from .base import Base
from sqlalchemy.orm import relationship


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    leader = Column(Integer)

    users = relationship("User")

    def __init__(self, name: str, description: str):
        super(Project, self).__init__()
        self.name = name
        self.description = description
