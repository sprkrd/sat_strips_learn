import gym
import pddlgym

from pddlgym.planning import run_planner
from pddlgym.parser import parse_plan_step
from PIL import Image

from collections import defaultdict

import itertools
import numpy as np
import os
import imageio


if os.path.isdir('images') == False :
	os.mkdir('images')

env = gym.make("PDDLEnvSokoban-v0")
env.fix_problem_index( 2 )
        
obs, debug_info = env.reset()

print( "\n".join(str(sorted(obs))[1:-1].split(", " ) ) )

plan = run_planner(debug_info['domain_file'], debug_info['problem_file'], 'ff')

#print( plan )

transition_counter = 0
sample_frequency = 1

transitions = []

#while done == False: # random walks
	#action = env.action_space.sample( obs ) 
for raw_action in plan: # goal-oriented trace
	action = parse_plan_step( raw_action, env.domain.operators.values(), env.action_predicates, debug_info['objects'], operators_as_actions=env.operators_as_actions )
	transition = []
	if( transition_counter % sample_frequency == 0 ):
		transition.append( obs )
	obs, reward, done, debug_info = env.step( action )
	if( transition_counter % sample_frequency == 0 ):
		transition.append( obs )
		transitions.append( transition )
		img = env.render()
		imageio.imsave("images/frame{}.png".format(transition_counter//sample_frequency ), img )
	transition_counter = transition_counter + 1
	#obs, reward, done, debug_info = env.step(action)

print( transitions )
print( len(transitions) )

env.close()
