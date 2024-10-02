import aiohttp
import asyncio
import json
from db_manager import DBManager
from constants import DB_NAME

class RootMeAPI(aiohttp.ClientSession):

    def __init__(self, api_key: str):
        super().__init__()

        self.BASE_API = 'https://api.www.root-me.org/'
        self.api_key = api_key
        self.db = DBManager(DB_NAME)

    async def fetchChallenge(self, idx):
        chall = await self.fetch(f"{self.BASE_API}/challenges/{idx}")
        if isinstance(chall, list):
            chall = chall[0]
        return chall

    async def fetchUser(self, idx):
        user = await self.fetch(f"{self.BASE_API}/auteurs/{idx}")
        if isinstance(user, list):
            user = user[0]
        return user

    async def fetchUserByName(self, name):
        users =  await self.fetch(f"{self.BASE_API}/auteurs", params={'nom': name})
        if isinstance(users, list):
            users = users[0]
        if 'error' in users.keys():
            return []
        else:
            return users
    
    async def updateUser(self, user):
        user_data = await self.fetchUser(user.id)
        return self.db.new_solves(user.id, user_data["validations"])

    async def loadChallenge(self, idx):
        x = self.db.getChallengeById(idx)
        if x is not None:
            # print(f"{x} already loaded in db")
            return None

        chall_data = await self.fetchChallenge(idx)
        try:
            self.db.newChallenge(chall_data)
            return chall_data["titre"]
        except:
            print(f"{chall_data = }")

    async def loadAllChallenges(self):
        start = 0
        new_challs = []
        while True:
            data = await self.fetch(f"{self.BASE_API}/challenges/?debut_challenges={start}")
            challenges, next = data[0], data[-1]
            start = int(next['href'].split('=')[1])

            results = await asyncio.gather(*(self.loadChallenge(chall["id_challenge"]) for idx, chall in challenges.items()))
            new_challs.extend([c for c in results if c is not None])
            if next['rel'] == 'previous':
                break
        return new_challs

    async def loadUser(self, name = None, idx = None):
        if name is None and idx is None:
            raise Exception('loadUser with None name and idx')

        if idx is not None:
            user = await self.fetchUser(idx)
        else:
            user = await self.fetchUserByName(name)
            if len(user)>1:
                raise Exception(f'User {name} got multiple result')
            user = user['0']

        await self.db.newUser(user)

    async def fetch(self, url, params=None):
        cookies = {"api_key": self.api_key}
        headers = {
            'User-Agent': 'toto'
        }
        print(url)
        async with self.get(url, cookies=cookies, headers=headers, params=params) as response:
            text = await response.text()
            # print(text)
            return json.loads(text)

async def main():
    async with RootMeAPI('365797_298ddfe31e07546808d7714063b2c88e7f92237c5d9118279c65f345d0261162') as api:


        # await api.loadAllChallenges()
        # print('all challenges are loaded')

        print(await api.fetchChallenge(2928))

        # print(await api.loadUser('dvorhack'))

        # challenge5 = json.loads(await api.challenge(5))[0]
        # print(challenge5)

        # user = json.loads(await api.user(1))
        # print(user)

if __name__ == "__main__":        
    asyncio.run(main())