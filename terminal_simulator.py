#!/usr/bin/env python3

import random
from satstripslearn.strips import Predicate, ObjType, ROOT_TYPE
from satstripslearn.openworld import Context, Action
from satstripslearn.latom_filter import ObjectGraphFilter, BasicObjectFilter


# available object types
Row = ObjType("row", ROOT_TYPE)
Col = ObjType("col", ROOT_TYPE)
Token = ObjType("token", ROOT_TYPE)
NumberToken = ObjType("number-token", Token)


# available predicates
Up = Predicate("up", Row, Row)
Right = Predicate("right", Col, Col)
SmallerThan = Predicate("smaller-than", NumberToken, NumberToken)
At = Predicate("at", Token, Col, Row)
Empty = Predicate("empty", Col, Row)
GoalAchieved = Predicate("goal-achieved")


class Game:
    def __init__(self, game_name, seed=None):
        rng = random.Random(seed)
        assert game_name in ("king", "numbers")
        self.board = [[None]*5 for _ in range(4)]
        self.game_name = game_name
        self.time_step = 0
        self.previous_token = "none"
        self.previous_destination = "none"

        self.objects = []
        self.static_atoms = set()

        previous_row = None
        for i in range(1, 5):
            this_row = Row(f"row_{i}")
            self.objects.append(this_row)
            if previous_row:
                self.static_atoms.add(Up(previous_row, this_row))
            previous_row = this_row

        previous_col = None
        for c in "abcde":
            this_col = Col(f"col_{c}")
            self.objects.append(this_col)
            if previous_col:
                self.static_atoms.add(Right(previous_col, this_col))

        if game_name == "king":
            self.objects.append(Token("k"))

            row = rng.randint(0,3)
            col = rng.randint(0,4)
            self.board[row][col] = "k"
        else:
            numbers = list(range(10))
            for i, n in enumerate(numbers):
                self.objects.append(NumberToken(str(n)))
                for m in numbers[i+1:]:
                    self.static_atoms.add(SmallerThan(NumberToken(str(n)), NumberToken(str(m))))

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
        atoms = self.static_atoms.copy()
        for row_number, row in zip("4321", self.board):
            for col_id, cell in zip("abcde", row):
                col_obj = Col(f"col_{col_id}")
                row_obj = Row(f"row_{row_number}")
                if cell is None:
                    atoms.add(Empty(col_obj, row_obj))
                else:
                    tok_obj = Token(cell) if self.game_name == "king" else NumberToken(cell)
                    atoms.add(At(tok_obj, col_obj, row_obj))
        return Context(self.objects, atoms)


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


def edge_creator(atom, atom_type):
    edges = {}
    if atom_type != "deleted":
        if atom[0] == "at":
            edges[(atom[1],atom[2])] = 0
            edges[(atom[2],atom[1])] = 0
        elif atom[0] in ("left", "down", "right", "up"):
            edges[(atom[1],atom[2])] = 1
    return edges


def main():
    from satstripslearn.oaru import OaruAlgorithm
    from itertools import count
    random.seed(100)
    game_name = input("Game? ")
    seed = int(input("Seed? "))
    #ask_frequency = int(input("Example frequency? "))


    game = Game(game_name, seed)
    oaru = OaruAlgorithm(double_filtering=False)
    #f = BasicObjectFilter()
    f = ObjectGraphFilter(

    # oaru = OaruAlgorithm(filters=[{"min_score": -1, "fn": min}], normalize_dist=False, double_filtering=True)

    #history_updates = []
    #history_proposals = []

    #touched_tokens = set()

    for i in count(0):
        print("Timestep ", game.time_step)
        print("---------------")
        print(game)

        #if ask_frequency == 2:
        #    example = propose_example(game, oaru, [False], [False], 1, 1)
        #elif ask_frequency == 1:
        #    example = propose_example(game, oaru, history_updates, history_proposals, 3, 3)
        #else:
        #    example = None

        #if example is not None:
        #    print("Proposing following example...")
        #    print(example)
        #    negative_example = input("Is it a valid example? (y/n) ") == "n"
        #    if negative_example:
        #        prev_state = game.get_state()
        #        next_state = example.apply(prev_state)
        #        assert next_state is not None
        #        oaru.add_negative_example(prev_state, next_state)
        #        oaru.draw_graph("terminal_demo", filename=f"demo_{i}_neg.gv", view=True)
        #        print(f"{len(oaru.action_library)} action(s) after negative example")

        move = input("Next move? ").strip()
        if move == "restart":
            s_prev = game.get_state()
            s_next = game.get_state()
            s_next.atoms.add(GoalAchieved())
            a_g, updated = oaru.action_recognition(s_prev, s_next)
            seed = seed+1
            game = Game(game_name, seed)
            #touched_tokens = set()
            continue
        elif move == "quit":
            break
        token, dst = move.split()
        #touched_tokens.add(token)
        s_prev = game.get_state()
        game.pick_and_place(token, dst)
        s_next = game.get_state()
        a_g, updated = oaru.action_recognition(s_prev, s_next, f)
        oaru.draw_graph("terminal_demo", filename=f"demo_{i}.gv", view=True)
        print(f"{len(oaru.action_library)} action(s) after demonstration")

        #history_updates.append(updated)
        #history_proposals.append(example is not None)
        print()


if __name__ == "__main__":
    main()
