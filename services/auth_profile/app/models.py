from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    token_version = Column(Integer, nullable=False, default=0)

    profile = relationship("Profile", back_populates="user", uselist=False)
    consents = relationship("Consents", back_populates="user", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    first_name = Column(String(255))
    last_name = Column(String(255))

    user = relationship("User", back_populates="profile")


class Consents(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    marketing = Column(Boolean, nullable=False, default=False)
    terms = Column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="consents")
