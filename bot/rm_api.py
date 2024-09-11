import aiohttp
import asyncio
import json
from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Table, ForeignKey


class Base(DeclarativeBase):
    pass

user_challenge_association = Table(
    'user_challenge', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('challenge_id', Integer, ForeignKey('challenges.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    rang: Mapped[Optional[str]]
    challenges: Mapped[List["Challenge"]] = relationship('Challenge', secondary=user_challenge_association, back_populates='users')
    
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"

class Challenge(Base):
    __tablename__ = "challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    score: Mapped[int]
    users: Mapped[List["User"]] = relationship('User', secondary=user_challenge_association, back_populates='challenges')
    def __repr__(self) -> str:
        return f"Challenge(id={self.id!r}, email_address={self.email_address!r})"

class RootMeAPI(aiohttp.ClientSession):

    def __init__(self, api_key: str):
        super().__init__()

        self.BASE_API = 'https://api.www.root-me.org/'
        self.api_key = api_key
        self.db = create_engine("sqlite:///test.db", echo=True)
    
    async def challenge(self, idx):
        return await self.fetch(f"{self.BASE_API}/challenges/{idx}")
    
    async def user(self, idx):
        return await self.fetch(f"{self.BASE_API}/auteurs/{idx}")
    
    async def fetch(self, url):
        cookies = {"api_key": self.api_key}
        headers = {
            'User-Agent': 'toto'
        }
        async with self.get(url, cookies=cookies, headers=headers) as response:
            return await response.text()

async def main():
    async with RootMeAPI('365797_298ddfe31e07546808d7714063b2c88e7f92237c5d9118279c65f345d0261162') as api:

        Base.metadata.create_all(api.db)

        challenge5 = json.loads(await api.challenge(5))[0]
        print(challenge5)

        user = json.loads(await api.user(1))
        print(user)

        with Session(api.db) as session:
            user1 = User(
                id = user['id_auteur'],
                name = user['nom'],
                rang = user['rang'],
            )
            chall5 = Challenge(
                id = challenge5['id_trad'],
                title = challenge5['titre'],
                score = challenge5['score'],
            )

            user1.challenges.append(chall5)

            session.add_all([user1, chall5])
            session.commit()

asyncio.run(main())