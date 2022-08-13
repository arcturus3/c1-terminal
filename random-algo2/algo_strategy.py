import gamelib
import random
import math
import warnings
from sys import maxsize
import json
import numpy as np


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips:

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical
  board states. Though, we recommended making a copy of the map to preserve
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """
        Read in config and perform any initial setup here
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        # First, place basic defenses
        self.build_defense(game_state)


        #TODO: check how much resources we have, build defenses with 2/3 of what we have and attacks with 2/3 of what we have
        # TODO: Start with scouts to get some points early on then build some big boyz

        units_affordable = {}
        units_affordable['SCOUT'] = game_state.number_affordable(SCOUT)
        units_affordable['DEMOLISHER'] = game_state.number_affordable(DEMOLISHER)
        units_affordable['INTERCEPTOR'] = game_state.number_affordable(INTERCEPTOR)
        units_affordable['WALL'] = game_state.number_affordable(WALL)
        units_affordable['SUPPORT'] = game_state.number_affordable(SUPPORT)
        units_affordable['TURRET'] = game_state.number_affordable(TURRET)

        temp_att = 0
        temp_def = 0
        for defense, offense in zip(['WALL', 'SUPPORT', 'TURRET'], ['SCOUT', 'DEMOLISHER', 'INTERCEPTOR']):
            temp_def += units_affordable.get(defense)
            temp_att += units_affordable.get(offense)

        mean_defense = temp_def // 3
        mean_offense = temp_att // 3

        defense_to_deploy = np.floor(2/3 * mean_defense)
        offense_to_deploy = np.floor(2/3 * mean_offense)

        # todo : make this adaptive
        if game_state.get_resource(MP) >= 12:
            game_state.attempt_spawn(SCOUT, [5, 1], int(offense_to_deploy/3))
            # game_state.attempt_spawn(SUPPORT, [14, 0], offense_to_deploy//3)
            game_state.attempt_spawn(INTERCEPTOR, [10, 0], int(offense_to_deploy//3))
            game_state.attempt_spawn(DEMOLISHER, [5, 0], int(offense_to_deploy//3))
            # game_state.attempt_remove([(24, 11), (25, 12), (26, 13), (27, 13)])




    def build_defense(self, game_state):
        #TODO: place walls right in the middle and separate them by one edge so that interceptors can walk through
        #   xxxxxxxxxxxox
        #   xoxxxxxxxxxxx
        # where the attackers will go through the openings , 'o'
        #
        #

        # from 0,13 to 27,13 and keep 26,13 open walls otherwise
        # then at 1, 12 and at 26, 12 walls
        # from 2, 11 to 25, 11 walls except to openings at 3, 11 or 24, 11
        # and keep going

        # spawn walls along back lines
        # todo: order walls from outside in to prioritize protecting edges
        game_state.attempt_spawn(WALL, [[0, 13], [1, 13]])
        # if attack:
        #     game_state.attempt_spawn(SUPPORT, [(24, 11), (25, 12)])
        # else:
        #     game_state.attempt_spawn(WALL, [(26, 13), (27, 13)])
        for x in range(2, 26):
            y = 15 - x if x < 14 else x - 12
            game_state.attempt_spawn(WALL, [x, y])

        # game_state.attempt_spawn(SUPPORT, [(24, 11), (25, 12)])
        # spawn turrets where scored on
        # todo: where damage to structures is being done instead?
        for (x, y) in self.scored_on_locations:
            game_state.attempt_spawn(TURRET, [x, y + 1])

        # spawn turrets at back corner
        game_state.attempt_spawn(TURRET, [13, 1])
        game_state.attempt_spawn(TURRET, [14, 1])

        # NOTE: upgrade walls and turrets
        for (x, y) in self.scored_on_locations:
            game_state.attempt_upgrade([x, y + 1])

        for x in range(2, 26):
            y = 15 - x if x < 14 else x - 12
            game_state.attempt_upgrade([x, y])


    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly,
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
