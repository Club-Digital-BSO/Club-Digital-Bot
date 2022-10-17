from .base import Base
from sqlalchemy.orm import relationship

from sqlalchemy import Column, Integer, String, ForeignKey


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer(), autoincrement=True, unique=True, nullable=True, primary_key=True)
    username = Column(String(), unique=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    # project = relationship("Project", back_populates="users")
    dc_id = Column(String(), unique=True)

    def __init__(self, username, id):
        self.username = username
        self.dc_id = id
