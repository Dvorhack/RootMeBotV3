from typing import List
from typing import Optional

import sqlalchemy
from sqlalchemy import Column, Integer, String, Table, ForeignKey, create_engine, select, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session



class Base(DeclarativeBase):
    pass


class Solve(Base):
    __tablename__ = "solves"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"), primary_key=True)
    date: Mapped[str]
    user: Mapped["User"] = relationship(back_populates="challenges")
    challenge: Mapped["Challenge"] = relationship(back_populates="users")

association_scoreboard_users = Table(
    "association_scoreboard_users",
    Base.metadata,
    Column("scoreboard_id", ForeignKey("scoreboards.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    score: Mapped[int]
    challenges: Mapped[List["Solve"]] = relationship(back_populates="user")
    
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.score!r})"

class Challenge(Base):
    __tablename__ = "challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    subtitle: Mapped[str]
    score: Mapped[int]
    category: Mapped[str]
    difficuly: Mapped[str]
    users: Mapped[List["Solve"]] = relationship(back_populates="challenge")
    def __repr__(self) -> str:
        return f"Challenge(id={self.id!r}, title={self.title!r})"


class Scoreboard(Base):
    __tablename__ = "scoreboards"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    users: Mapped[List["User"]] = relationship(secondary=association_scoreboard_users)
    def __repr__(self) -> str:
        return f"Scoreboard(id={self.id!r}, title={self.title!r}, {[x.name for x in self.users]})"

class DBManager():
    def __init__(self, db_name) -> None:
        self.engine = create_engine(f"sqlite:///{db_name}", echo=False)
        Base.metadata.create_all(self.engine)

    def getUserById(self, idx):
        x = self.execute(select(User).where(User.id == idx))
        if len(x) == 1:
            return x[0]
        elif len(x) == 0:
            return None
        else:
            raise Exception(f"Database corrupted: multiple users with id {idx}")
        
    def getUserByName(self, name):
        x = self.execute(select(User).where(User.name.ilike(f"%{name}%")))
        return x
    
    def getScoreboardByName(self, name):
        x = self.execute(select(Scoreboard).where(Scoreboard.title.ilike(f"%{name}%")))
        return x
        
    def getAllUsers(self):
        return self.execute(select(User.name, User.score))
        
    def getChallengeById(self, idx):
        x = self.execute(select(Challenge).where(Challenge.id == idx))
        if len(x) == 1:
            return x[0][0]
        elif len(x) == 0:
            return None
        else:
            raise Exception(f"Database corrupted: multiple challenges with id {idx}")
    
    def getChallengeByIdBatch(self, ids):
        return self.execute(select(Challenge).where(Challenge.id.in_(ids)))
    
    def execute(self, stmt: sqlalchemy.sql.expression.Select) -> sqlalchemy.engine.CursorResult:
        with Session(self.engine) as session:
            x = session.execute(stmt).all()
        return x
    

    def newUser(self, user_data):
        if self.getUserById(user_data['id_auteur']) is not None:
            return

        with Session(self.engine) as session:
            user = User(
                id = user_data['id_auteur'],
                score = user_data['score'],
                name = user_data['nom'],
                challenges = []
            )

            for chall in user_data['validations']:
                chall_obj = self.getChallengeById(chall['id_challenge'])
                if chall_obj is None:
                    raise Exception(f"Challenge {chall} solved by {user} doesn't exist in db")
                
                solve = Solve(date=chall['date'])
                solve.challenge = chall_obj

                user.challenges.append(solve)

            session.add_all([user])
            session.commit()

    def newChallenge(self, chall_data):
        with Session(self.engine) as session:
            chall5 = Challenge(
                id = chall_data['id_trad'],
                title = chall_data['titre'],
                subtitle = chall_data['soustitre'],
                score = chall_data['score'],
                category = chall_data['rubrique'],
                difficuly = chall_data['difficulte'],
                users = [] # Filled when fetching users
            )

            session.add_all([chall5])
            session.commit()

    def createScoreboard(self, name):
        with Session(self.engine) as session:
            sc = Scoreboard(
                title = name
            )

            session.add_all([sc])
            session.commit()
    
    def addUserToScoreboard(self, user_name, scoreboard_name):

        with Session(self.engine) as session:
            stmt = select(User).where(User.name.ilike(f"%{user_name}%"))
            u = session.execute(stmt).first()[0]

            stmt = select(Scoreboard).where(Scoreboard.title.ilike(f"%{scoreboard_name}%"))
            sc = session.execute(stmt).first()[0]
            sc.users.append(u)
            print(u, sc)

    
if __name__ == "__main__":
    db = DBManager('test2.db')
    
    db.newUser({'id_auteur':'2345' , 'score':'14050','nom':'dvorhack', 'validations': []})
    db.newUser({'id_auteur':'2346' , 'score':'14050','nom':'sdvsdvdvo', 'validations': []})

    db.createScoreboard('global')


    db.addUserToScoreboard('dvo', 'global')