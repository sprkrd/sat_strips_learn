from pddlgym.utils import run_planning_demo

import gym
import pddlgym

# See `pddl/sokoban.pddl` and `pddl/sokoban/problem3.pddl`.
env = gym.make("PDDLEnvSokoban-v0")
env.fix_problem_index(2)
run_planning_demo(env, 'ff', verbose=True)
