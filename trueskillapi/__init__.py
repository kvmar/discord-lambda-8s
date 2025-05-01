""""
Copyright © Krypton 2019-2023 - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 6.1.0
"""
from trueskill import TrueSkill
from trueskill import Rating

from dao.PlayerDao import PlayerDao, PlayerRecord

player_dao = PlayerDao()


class TrueSkillAccessor:
    def __init__(self) -> None:
        self.env = TrueSkill(draw_probability=0, tau=0.5)

    def post_match(self, win_team: list, lose_team: list, guild_id: str):
        win_team_ratings = self.get_player_data(win_team, guild_id)
        lose_team_ratings = self.get_player_data(lose_team, guild_id)

        win_team_ratings_tuple = list()
        lose_team_ratings_tuple = list()
        for user in win_team_ratings:
            win_team_ratings_tuple.append(Rating(float(user.elo), float(user.sigma)))

        for user in lose_team_ratings:
            lose_team_ratings_tuple.append(Rating(float(user.elo), float(user.sigma)))

        new_ratings = self.env.rate([tuple(win_team_ratings_tuple), tuple(lose_team_ratings_tuple)], ranks=[0, 1])

        self.update_ratings(new_ratings, win_team_ratings, 0)
        self.update_ratings(new_ratings, lose_team_ratings, 1)


    def get_player_data(self, team: list, guild_id: str) -> list[PlayerRecord]:
        player_data_list = list()
        for user in team:
            player_data = player_dao.get_player(player_id=user, guild_id=guild_id)
            player_data_list.append(player_data)
            print(f'Got user_id: {player_data.player_id}, player_name: {player_data.player_name}, elo: {player_data.elo}, sigma: {player_data.sigma}')
        return player_data_list

    def update_ratings(self, new_ratings, team_ratings: list[PlayerRecord], tuple_idx: int):
        idx = 0
        lost = 0
        won = 0

        if tuple_idx == 0:
            won = won + 1
        else:
            lost = lost + 1

        for user in team_ratings:
            print("Updating streak for player_name: " + user.player_name + " , streak: " + str(user.streak))

            if tuple_idx == 0:
                if user.streak > 0:
                    user.streak = int(user.streak) + 1
                else:
                    user.streak = 1
            else:
                if user.streak < 0:
                    user.streak = int(user.streak) + (-1)
                else:
                    user.streak = -1

            user.mw = int(user.mw) + won
            user.ml = int(user.ml) + lost

            old_rating = user.get_rating()

            user.elo = float(new_ratings[tuple_idx][idx].mu)
            user.sigma = float(new_ratings[tuple_idx][idx].sigma)
            new_rating = user.get_rating()



            user.apply_rp_change(0)

            print(f"Writing player_data record to {user}")
            player_dao.put_player(user)
            idx = idx + 1





