from typing import List
from typing import Optional

import sqlalchemy
from sqlalchemy import Column, Integer, String, Table, ForeignKey, create_engine, select, Date, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from datetime import date

from errors import *

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
    # id: Mapped[int]
    name: Mapped[str] = mapped_column(String(30))
    score: Mapped[int]
    challenges: Mapped[List["Solve"]] = relationship(back_populates="user")
    # challenges: Mapped[List["Solve"]] = mapped_column(ForeignKey("challenge.id"), primary_key=True)
    
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, score={self.score!r})"

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

Users = List[User]
Challenges = List[Challenge]
Solves = List[Solve]

class DBManager():
    def __init__(self, db_name) -> None:
        self.engine = create_engine(f"sqlite:///{db_name}", echo=False)
        Base.metadata.create_all(self.engine)

    def getUserById(self, idx) -> User:
        x = self.execute(select(User).where(User.id == idx))
        if len(x) == 1:
            return x[0]
        elif len(x) == 0:
            return None
        else:
            raise Exception(f"Database corrupted: multiple users with id {idx}")
        
    def getUserByName(self, name) -> User:
        with Session(self.engine) as session:
            x = session.scalars(select(User).where(User.name.ilike(f"%{name}%"))).all()
        return x
    
    def getChallengeByName(self, name) -> Challenge:
        with Session(self.engine) as session:
            x = session.scalars(select(Challenge).where(Challenge.title.ilike(f"%{name}%"))).all()
        if len(x) == 1:
            return x[0]
        elif len(x) == 0:
            raise ChallengeNotFound(name, name=name)
        else:
            raise FoundMultipleChallenges(name, name=name)
        
    def getAllUsers(self) -> Users:
        with Session(self.engine) as session:
            x = session.scalars(select(User)).all()
        return x
    
    def getTodayScoreboard(self):
        with Session(self.engine) as session:
            x = session.query(User.name, func.sum(Challenge.score)).join(Solve, Solve.user_id == User.id).join(Challenge, Solve.challenge_id == Challenge.id).filter(func.date(Solve.date) == date.today()).group_by(User.name).all()
        return x
        
    def getChallengeById(self, idx) -> Challenge:
        x = self.execute(select(Challenge).where(Challenge.id == idx))
        if len(x) == 1:
            return x[0][0]
        elif len(x) == 0:
            return None
        else:
            raise Exception(f"Database corrupted: multiple challenges with id {idx}")
    
    def getChallengeByIdBatch(self, ids):
        return self.execute(select(Challenge).where(Challenge.id.in_(ids)))
    
    def new_solves(self, idx, api_solves):
        data_new_solves = []  # list of tuples of form: (user, chall, next_user, points_to_next, is_first_blood)
        with Session(self.engine) as session:
            session.expire_on_commit = False
            user = session.scalar(select(User).where(User.id == idx))
            all_users = sorted(self.getAllUsers(), key=lambda u: u.score)
            print(all_users)
            db_solves_id = session.scalars(select(Solve.challenge_id).where(Solve.user_id == idx)).all()
            for api_solve in reversed(api_solves):  # sort from oldest to newest
                if int(api_solve["id_challenge"]) not in db_solves_id:
                    print(f"new challenge solved by user {idx}: {api_solve['titre']}")
                    chall_obj = self.getChallengeById(api_solve["id_challenge"])
                    chall_obj = session.merge(chall_obj)
                    print(f"Adding solved challenge {chall_obj.title}")
                    first_blood = (len(chall_obj.users) == 0)
                    solve = Solve(user_id=idx, date=api_solve["date"])
                    session.add(solve)
                    solve.challenge = chall_obj

                    user.challenges.append(solve)
                    user.score += chall_obj.score
                    next_user = [u for u in all_users if u.score > user.score]
                    if not next_user:
                        #  He is the first in the scoreboard
                        data_new_solves.append((user, chall_obj, None, None, first_blood))
                    else:
                        next_user = next_user[0]
                        points_to_next = next_user.score - user.score
                        data_new_solves.append((user, chall_obj, next_user.name, points_to_next, first_blood))
                        # print(f"{data_new_solves = }")
                    session.add(solve)
            session.commit()
        return data_new_solves
    
    def who_solved(self, name):
        with Session(self.engine) as session:
            x = session.scalars(select(Challenge).where(Challenge.title.ilike(f"%{name}%"))).all()
            if len(x) == 0:
                raise ChallengeNotFound(name, name=name)
            elif len(x) > 1:
                raise FoundMultipleChallenges(name, name=name)
            
            chall = x[0]
            solvers = []
            for s in chall.users:
                solvers.append(s.user)
        return chall.title, solvers

    def getStats(self, user_id):
        with Session(self.engine) as session:
            user_stats = session.query(Challenge.category, func.count(Challenge.id), func.sum(Challenge.score)).join(Solve, Challenge.id == Solve.challenge_id).filter(Solve.user_id == user_id).group_by(Challenge.category).all()
            global_stats = session.query(Challenge.category, func.count(Challenge.id)).group_by(Challenge.category).all()

        res = {category: {} for category,_ in global_stats}
        for category, tot_chall in global_stats:
            try:
                solved_chall = next((solved_chall for chall, solved_chall, points in user_stats if chall == category), None)
                points = next((points for chall, solved_chall, points in user_stats if chall == category), None)
                rate = round(solved_chall/tot_chall*100)
                res[category].update({"tot_chall" : tot_chall, 
                                    "solved_chall" : solved_chall,
                                    "points" : points,
                                    "rate" : rate})
            except TypeError: 
                res[category].update({"tot_chall" : tot_chall, 
                                    "solved_chall" : 0,
                                    "points" : 0,
                                    "rate" : 0})
        return res
    
    def execute(self, stmt: sqlalchemy.sql.expression.Select) -> sqlalchemy.engine.CursorResult:
        with Session(self.engine) as session:
            x = session.execute(stmt).all()
        return x
    
    async def newUser(self, user_data):
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
                print(f"Adding solved challenge {chall_obj.title}")
                
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
    db = DBManager('test2.db')
    
    # db.newUser({'id_auteur':'2345' , 'score':'14050','nom':'dvorhack', 'validations': []})
    # db.newUser({'id_auteur':'2346' , 'score':'14050','nom':'sdvsdvdvo', 'validations': []})

    # db.createScoreboard('global')

    # print(db.getScoreboardByName('glo'))

    users = db.getAllUsers()

    for u in users.sort(key=lambda x: x.score, reverse=True):
        print(u)


    # db.addUserToScoreboard('dvo', 'global')