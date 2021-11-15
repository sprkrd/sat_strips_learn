#!/usr/bin/env python3

import random
from satstripslearn.state import State


class Game:
    def __init__(self, game_name, seed=None):
        rng = random.Random(seed)
        assert game_name in ("king", "numbers")
        self.board = [[None]*5 for _ in range(4)]
        self.game_name = game_name
        self.time_step = 0
        if game_name == "king":
            row = rng.randint(0,3)
            col = rng.randint(0,4)
            self.board[row][col] = "k"
        else:
            numbers = list(range(10))
            rng.shuffle(numbers)
            for i, num in enumerate(numbers):
                row = 2 + i//5
                col = i%5
                self.board[row][col] = str(num)
        
    def __str__(self):
        lines = []
        for row_number, row in zip("4321", self.board):
            line = [row_number, " "]
            for cell in row:
                if cell is None:
                    line.append(".")
                else:
                    line.append(cell)
            lines.append("".join(line))
        lines.append("  ABCDE")
        return "\n".join(lines)
        
    def pick_and_place(self, token, destination):
        token = token.lower()
        destination = destination.lower()
        found = False
        for row in self.board:
            for j in range(5):
                if row[j] == token:
                    row[j] = None
                    found = True
                    break
        assert found
        row_index = 4 - int(destination[1])
        col_index = ord(destination[0]) - ord('a')
        assert self.board[row_index][col_index] is None
        self.board[row_index][col_index] = token
        self.time_step += 1
        
    def get_state(self):
        predicates = set()
        for row_number, row in zip("4321", self.board):
            for col_id, cell in zip("abcde", row):
                cell_id = col_id + row_number
                predicates.add(("location", cell_id))
                if row_number != "4":
                    row_up = str(int(row_number)+1)
                    predicates.add(("up", cell_id, col_id+row_up))
                if row_number != "1":
                    row_down = str(int(row_number)-1)
                    predicates.add(("down", cell_id, col_id+row_down))
                if col_id != "a":
                    col_left = chr(ord(col_id)-1)
                    predicates.add(("left", cell_id, col_left+row_number))
                if col_id != "e":
                    col_right = chr(ord(col_id)+1)
                    predicates.add(("right", cell_id, col_right+row_number))
                if cell is None:
                    predicates.add(("empty", cell_id))
                else:
                    predicates.add(("token", cell))
                    predicates.add(("at", cell, cell_id))
        if self.game_name == "numbers":
            for i in range(10):
                for j in range(i+1,10):
                    predicates.add(("less-than", str(i), str(j)))
        # ~ predicates.add(("time-step", str(self.time_step)))
        return State(predicates)


def main():
    from satstripslearn.oaru import OaruAlgorithm, STANDARD_FILTERS
    from satstripslearn.utils import goal_match
    # ~ oaru = OaruAlgorithm(filters=[{"min_score": 0, "fn": min}])
    oaru = OaruAlgorithm()
    game = Game("king", 73)
    print(game)
    state1 = game.get_state()
    game.pick_and_place("k", "B2")
    print(game)
    state2 = game.get_state()
    game.pick_and_place("k", "C3")
    state3 = game.get_state()
    print(game)
    oaru.action_recognition(state1, state2)
    oaru.action_recognition(state2, state3)
    a = next(iter(oaru.action_library.values()))
    oaru.draw_graph(".", view=True, atom_limit_middle=1000)
    print(a)
    
    # ~ print(a.can_produce_transition(state1, state2))
    


if __name__ == "__main__":
    main()
