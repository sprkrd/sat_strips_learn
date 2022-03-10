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
        self.previous_token = "none"
        self.previous_destination = "none"
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
        self.previous_token = token
        self.previous_destination = destination
        
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
        for i in range(50):
            predicates.add(("timestep", f"t{i}"))
        for i in range(1,50):
            predicates.add(("next-timestep", f"t{i-1}", f"t{i}"))
        # predicates.add(("previous-token", self.previous_token))
        # predicates.add(("previous-destination", self.previous_destination))
        predicates.add(("current-timestep", f"t{self.time_step}"))
        return State(predicates)


def propose_example(game, oaru, history_updates, history_proposals, min_non_updated, min_no_proposals, rng=random):
    crit1 = len(history_updates) >= min_non_updated and True not in history_updates[-min_non_updated:]
    crit2 = len(history_proposals) >= min_no_proposals and True not in history_proposals[-min_no_proposals:]
    if not crit1 or not crit2:
        return None
    prev_state = game.get_state()
    actions = []
    for action in oaru.action_library.values():
        actions += list(action.all_instantiations(prev_state))
    if not actions:
        return None
    return rng.choice(actions)
        

def main():
    from satstripslearn.oaru import OaruAlgorithm
    from itertools import count
    random.seed(100)
    game_name = input("Game? ")
    seed = int(input("Seed? "))
    ask_frequency = int(input("Example frequency? "))
            
    
    game = Game(game_name, seed)
    oaru = OaruAlgorithm(filters=[{"min_score": -1, "fn": min}], normalize_dist=False, double_filtering=True)
    
    history_updates = []
    history_proposals = []
    
    for i in count(0):
        print("Timestep ", game.time_step)
        print("---------------")
        print(game)
        
        if ask_frequency == 2:
            example = propose_example(game, oaru, [False], [False], 1, 1)
        elif ask_frequency == 1:
            example = propose_example(game, oaru, history_updates, history_proposals, 3, 3)
        else:
            example = None
            
        if example is not None:    
            print("Proposing following example...")
            print(example)
            negative_example = input("Is it a valid example? (y/n) ") == "n"
            if negative_example:
                prev_state = game.get_state()
                next_state = example.apply(prev_state)
                assert next_state is not None
                oaru.add_negative_example(prev_state, next_state)
                oaru.draw_graph("terminal_demo", filename=f"demo_{i}_neg.gv", view=True)
                print(f"{len(oaru.action_library)} action(s) after negative example")
        
        move = input("Next move? ").strip()
        if move == "restart":
            seed = seed+1
            game = Game(game_name, seed)
            continue
        elif move == "quit":
            break
        s_prev = game.get_state()
        game.pick_and_place(*move.split())
        s_next = game.get_state()
        a_g, updated = oaru.action_recognition(s_prev, s_next)
        oaru.draw_graph("terminal_demo", filename=f"demo_{i}.gv", view=True)
        print(f"{len(oaru.action_library)} action(s) after demonstration")
        
        history_updates.append(updated)
        history_proposals.append(example is not None)
        print()
        
            
if __name__ == "__main__":
    main()
