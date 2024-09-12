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


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    score: Mapped[int]
    challenges: Mapped[List["Solve"]] = relationship(back_populates="user")
    
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"

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
    


class DBManager():
    def __init__(self) -> None:
        self.engine = create_engine("sqlite:///test.db", echo=False)
        Base.metadata.create_all(self.engine)

    def getUserById(self, idx):
        x = self.execute(select(User).where(User.id == idx))
        if len(x) == 1:
            return x[0]
        elif len(x) == 0:
            return None
        else:
            raise Exception(f"Database corrupted: multiple users with id {idx}")
        
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

if __name__ == "__main__":
    pass