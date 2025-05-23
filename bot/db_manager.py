from typing import List
from typing import Optional

import sqlalchemy
from sqlalchemy import Column, Integer, String, Table, ForeignKey, create_engine, select, Date, func, delete, asc, desc
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from datetime import date, timedelta, datetime
from numpy import cumsum

from errors import *

class Base(DeclarativeBase):
    pass


class Solve(Base):
    __tablename__ = "solves"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"), primary_key=True)
    date: Mapped[Date] = mapped_column(Date())
    user: Mapped["User"] = relationship(back_populates="challenges")
    challenge: Mapped["Challenge"] = relationship(back_populates="users")

    def __repr__(self) -> str:
        return f"Solve(user_id={self.user_id!r}, challenge_id={self.challenge_id!r}, date={self.date})"


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
        return f"Challenge(id={self.id!r}, title={self.title!r}, subtitle={self.subtitle!r}, score={self.score!r}, category={self.category!r}, difficuly={self.difficuly!r})"
    
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
            print(x)
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
        
    def getChallengesByName(self, name) -> Challenge:
        with Session(self.engine) as session:
            x = session.scalars(select(Challenge).where(Challenge.title.ilike(f"%{name}%"))).all()
        return x
        
    def getAllUsers(self) -> Users:
        with Session(self.engine) as session:
            x = session.scalars(select(User)).all()
        return x
    
    def getTodayScoreboard(self):
        with Session(self.engine) as session:
            # x = session.query(User.name, func.sum(Challenge.score)).join(Solve, Solve.user_id == User.id).join(Challenge, Solve.challenge_id == Challenge.id).filter(func.date(Solve.date) == date.today()).group_by(User.name).all()
            x = session.query(User.name, func.sum(Challenge.score)).join(Solve, Solve.user_id == User.id).join(Challenge, Solve.challenge_id == Challenge.id).filter(Solve.date == date.today()).group_by(User.name).all()
        return x
    
    def getLastSolvesByUser(self, user_id, n_days):
        start = date.today() - timedelta(days=n_days)
        with Session(self.engine) as session:
            user_last_solves = session.query(Solve.date, Challenge.title, Challenge.score).join(User, Solve.user_id == User.id).filter(Solve.challenge_id == Challenge.id).filter(User.id == user_id).filter(Solve.date >= start).order_by(desc(Solve.date)).all()
            return user_last_solves

    
    def getLastSolves(self, n_days):
        users_cum_score = []  # list of tuples, of the form (username, [cumulated earned points])
        start = date.today() - timedelta(days=n_days)
        users = self.getAllUsers()
        with Session(self.engine) as session:
            for u in users:
                solves_by_day = [0] * (n_days + 2)
                user_last_solves = session.query(Solve.date, Challenge.score).join(User, Solve.user_id == User.id).filter(Solve.challenge_id == Challenge.id).filter(User.id == u.id).filter(Solve.date >= start).order_by(asc(Solve.date)).all()
                for day, score in user_last_solves:
                    solves_by_day[(day-start).days+1] += score
                cumsolves = cumsum(solves_by_day).tolist()
                if cumsolves[-1] != 0:
                    users_cum_score.append((u.name, cumsum(solves_by_day).tolist()))
        return sorted(users_cum_score, key=lambda el: el[1][-1], reverse=True)[:10]
        
    def getChallengeById(self, chall_id) -> Challenge:
        x = self.execute(select(Challenge).where(Challenge.id == chall_id))
        if len(x) == 1:
            return x[0][0]
        elif len(x) == 0:
            return None
        else:
            raise Exception(f"Database corrupted: multiple challenges with id {chall_id}")
    
    def getChallengeByIdBatch(self, ids):
        return self.execute(select(Challenge).where(Challenge.id.in_(ids)))

    def deleteUserByName(self, name):
        with Session(self.engine) as session:
            user_to_delete = session.scalar(select(User).where(User.name == name))
            for solve in user_to_delete.challenges:
                session.delete(solve)
            
            session.delete(user_to_delete)
            session.commit()

    def new_solves(self, user_id, api_solves):
        for api_solve in api_solves:
            data_new_solve = self.add_solve_to_user(user_id, api_solve)
            if data_new_solve is not None:  # There is a new solve
                yield data_new_solve

    def add_solve_to_user(self, user_id, api_solve):
        # TODO: manage transition to the next hundred or thousand
        # TODO: cleared category
        with Session(self.engine) as session:
            session.expire_on_commit = False
            user = session.scalar(select(User).where(User.id == user_id))
            all_users = sorted(self.getAllUsers(), key=lambda u: u.score)
            db_solves_id = session.scalars(select(Solve.challenge_id).where(Solve.user_id == user_id)).all()
            if int(api_solve["id_challenge"]) in db_solves_id:
                return None  # challenge already solved by the user
            
            chall_obj = self.getChallengeById(api_solve["id_challenge"])
            if chall_obj is None:  # challenge not yet in db => return it
                return api_solve
            chall_obj = session.merge(chall_obj)
            print(f"new challenge solved by user {user_id}: {api_solve['titre']}")
            print(f"Adding solved challenge {chall_obj.title}")
            first_blood = (len(chall_obj.users) == 0)
            solve = Solve(user_id=user_id, date=datetime.strptime(api_solve['date'], "%Y-%m-%d %H:%M:%S"))
            session.add(solve)
            solve.challenge = chall_obj

            user.challenges.append(solve)
            next_users = [u for u in all_users if u.score > user.score]
            # Check for new completed step
            step = self.completed_step(user.score, chall_obj.score)
            user.score += chall_obj.score
            overtakens = []
            if not next_users:
                #  He is the first in the scoreboard
                data_new_solve = (user, chall_obj, None, None, first_blood, overtakens, step)
            else:
                while user.score > next_users[0].score:
                    overtakens.append(next_users[0].name)
                    next_users.pop(0)
                    if len(next_users) == 0:
                        next_user_name = None
                        points_to_next = None
                        break
                if next_users:
                    next_user = next_users[0]
                    points_to_next = next_user.score - user.score
                    next_user_name = next_user.name
                data_new_solve = (user, chall_obj, next_user_name, points_to_next, first_blood, overtakens, step)

            session.add(solve)
            session.commit()
            return data_new_solve
        
    def completed_step(self, user_score, chall_score):
        """
        Check for completed steps during chall validation
        (every 100 pts when < 1000 pts, then every 1000)
        """
        step = None
        if user_score < 1000:
            if user_score // 100 != (user_score + chall_score) // 100:
                step = ((user_score // 100) + 1) * 100
        else:
            if user_score // 1000 != (user_score + chall_score) // 1000:
                step = ((user_score // 1000) + 1) * 1000
        return step
    
    def who_solved(self, name):
        with Session(self.engine) as session:
            x = session.scalars(select(Challenge).where(Challenge.title.ilike(name))).all()
            if len(x) == 0:
                raise ChallengeNotFound(name, name=name)
            elif len(x) > 1:
                raise FoundMultipleChallenges(name, name=name)
            
            chall = x[0]
            solvers = []
            for s in chall.users:
                date = self.execute(select(Solve.date).where(Solve.challenge_id == select(Challenge.id).where(Challenge.title == chall.title)).where(Solve.user_id == select(User.id).where(User.name == s.user.name)))[0][0]
                solvers.append((s.user, date))
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
                
                solve = Solve(date=datetime.strptime(chall['date'], "%Y-%m-%d %H:%M:%S"))
                solve.challenge = chall_obj

                user.challenges.append(solve)

            session.add_all([user])
            session.commit()

    def newChallenge(self, chall_data):
        with Session(self.engine) as session:
            chall5 = Challenge(
                id = chall_data['id_trad'],
                title = chall_data['titre'].replace("&#8217;", "'").replace("&nbsp;", " ").replace("&amp;", "&"),
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