import dataclasses
import discord

@dataclasses.dataclass
class Player:
    id: int 
    miss: bool = dataclasses.field(default_factory=False)
    score: int = dataclasses.field(default_factory=0)

    def add_score(self, score):
        self.score += score
@dataclasses.dataclass
class Session:
    channelid: int = None
    players: list[Player] = dataclasses.field(default_factory=list)
    waits: list[int] = dataclasses.field(default_factory=list)

    def join_player(self, id):
        self.players.append(Player(id=id, miss=False, score=0))

    def remove_player(self, id):
        player = self.get_player(id)
        del self.players[self.players.index(player)]
        
    def add_waiting_players(self, id):
        self.waits.append(id)

    def remove_waiting_player(self, id):
        del self.waits[self.waits.index(id)]

    def refresh(self):
        for player in self.players:
            player.miss = False 

    def join_waiters(self):
        for id in self.waits:
            self.join_player(id)
        self.waits = []

    def player_joined_check(self, id):
        return id in self.get_player_ids()
     
    def get_player_ids(self):
        return [i.id for i in self.players]

    def get_player(self, id):
        for player in self.players:
            if player.id == id:
                return player
        return None

@dataclasses.dataclass
class SessionsGroup:
    sessions: dict[int, Session] = dataclasses.field(default_factory=dict)

    def add_session(self, guildid, channelid) -> Session:
        self.sessions[guildid] = Session(channelid=channelid)
        return self.sessions[guildid]
    def remove_session(self, guildid):
        del self.sessions[guildid]

    def get_session(self, guildid):
        if guildid in self.sessions:
            return self.sessions[guildid]
        else:
            return None
