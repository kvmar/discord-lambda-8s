""""
Copyright © Krypton 2019-2023 - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 6.1.0
"""
from trueskill import TrueSkill
from trueskill import Rating


class PlayerData:

    def __init__(self, user, rating, mp, mw, ml):
        self.user = user
        self.rating = rating
        self.mp = int(mp)
        self.mw = int(mw)
        self.ml = int(ml)
        self.delta = None

    def get_mp(self):
        return self.mp

    def get_mw(self):
        return self.mw

    def get_ml(self):
        return self.ml

    def update_delta(self, new_rating):
        self.delta = new_rating - self.rating.mu


class TrueSkillAccessor:
    def __init__(self, database) -> None:
        self.database = database
        self.env = TrueSkill(draw_probability=0)

    async def sign_up_player(
        self, user_id: str, user_name: str):
        player_data = await self.database.get_player_data(user_id)
        if len(player_data) > 0:
            print("Player " + user_name + " already signed up")
            return

        await self.database.add_player_data(user_id, user_name)

    async def post_match(self, win_team: list, lose_team: list):
        win_team_ratings = await self.get_ratings(win_team)
        lose_team_ratings = await self.get_ratings(lose_team)

        win_team_ratings_tuple = list()
        lose_team_ratings_tuple = list()
        for person in win_team_ratings:
            win_team_ratings_tuple.append(person.rating)

        for person in lose_team_ratings:
            lose_team_ratings_tuple.append(person.rating)

        new_ratings = self.env.rate([tuple(win_team_ratings_tuple), tuple(lose_team_ratings_tuple)], ranks=[0, 1])

        await self.update_ratings(new_ratings, win_team, win_team_ratings, 0)
        await self.update_ratings(new_ratings, lose_team, lose_team_ratings, 1)

    async def get_ratings(self, team: list):
        ratings = list()

        for user in team:
            player_data = await self.database.get_player_data(user)
            user = player_data[0][1]
            elo = player_data[0][5]
            sigma = player_data[0][6]

            mp = player_data[0][2]
            mw = player_data[0][3]
            ml = player_data[0][4]
            ratings.append(PlayerData(user, Rating(float(elo), float(sigma)), mp, mw, ml))
        return tuple(ratings)

    async def update_ratings(self, new_ratings, team, team_ratings, tuple_idx):
        idx = 0
        lost = 0
        won = 0

        if tuple_idx == 0:
            won = won + 1
        else:
            lost = lost + 1

        for user in team:
            team_ratings[idx].update_delta(new_ratings[tuple_idx][idx].mu)
            await self.database.update_player_data(user, new_ratings[tuple_idx][idx].mu, new_ratings[tuple_idx][idx].sigma, str(team_ratings[idx].get_mp() + 1),
                                                   str(team_ratings[idx].get_mw() + won), str(team_ratings[idx].get_ml() + lost), str(team_ratings[idx].delta))


            idx = idx + 1




