from discord.ext import tasks, commands


class InitNotDone(commands.CheckFailure):
    pass


class PremiumChallenge(commands.CommandError):
    def __init__(self, message, name):
        super().__init__(message)
        self.name = name

class TooManyUsers(commands.CommandError):
    def __init__(self, message, name):            
        super().__init__(message)
        self.name = name

class ChallengeNotFound(commands.CommandError):
    def __init__(self, message, name):            
        super().__init__(message)
        self.name = name

class UserNotFound(commands.CommandError):
    def __init__(self, message, name):            
        super().__init__(message)
        self.name = name

class FoundMultipleChallenges(commands.CommandError):
    def __init__(self, message, name):            
        super().__init__(message)
        self.name = name