#!/usr/bin/env python3


import os

import gym
import pddlgym

from pddlgym.structs import TypedEntity
from pddlgym.utils import VideoWrapper

from .action import Action
from .cluster_z3 import cluster


def lit_as_tuple(lit):
    return (lit.predicate.name,) + tuple(arg.name if isinstance(arg, TypedEntity) else arg
            for arg in lit.variables)


def get_type_predicates(env):
    type_preds = set()
    if env._problem.uses_typing:
        for obj in env._problem.objects:
            type_preds.add((str(obj.var_type), obj.name))
    return type_preds


def run_random_agent_demo(env, outdir='/tmp', max_num_steps=20, fps=3, 
                          verbose=False, seed=None):
    if outdir is None:
        outdir = "/tmp/{}".format(env_cls.__name__)
        if not os.path.exists(outdir):
            os.makedirs(outdir)

    if env._render:
        video_path = os.path.join(outdir, 'random_{}_demo.gif'.format(env.spec.id))
        env = VideoWrapper(env, video_path, fps=fps)

    if seed is not None:
        env.seed(seed)

    states = []
    obs, _ = env.reset()
    try:
        type_preds = get_type_predicates(env)
    except AttributeError:
        type_preds = get_type_predicates(env.unwrapped)
    if verbose:
        print("Type preds:", type_preds)
    obs = set(lit_as_tuple(lit) for lit in obs)
    obs.update(type_preds)
    states.append(obs)


    if seed is not None:
        env.action_space.seed(seed)

    for t in range(max_num_steps):
        if verbose:
            print("Obs:", obs)
    
        action = env.action_space.sample()
        if verbose:
            print("Act:", action)

        obs, reward, done, _ = env.step(action)
        obs = set(lit_as_tuple(lit) for lit in obs)
        obs.update(type_preds)
        states.append(obs)
        env.render()
        if verbose:
            print("Rew:", reward)
        if done:
            break
    if verbose:
        print("Final obs:", obs)
        print()
    env.close()
    return states


def demo_random(env_name, render=True, problem_index=0, verbose=True):
    env = gym.make("PDDLEnv{}-v0".format(env_name.capitalize()))
    if not render: env._render = None
    env.fix_problem_index(problem_index)
    return run_random_agent_demo(env, verbose=verbose, seed=0)


states = demo_random("blocks_operator_actions", verbose=False)

actions = []
for trans, (s,snext) in enumerate(zip(states, states[1:])):
    a = Action.from_transition(s, snext)
    merge_found = False
    for idx, a_other in enumerate(actions):
        a_merge = cluster(a, a_other)
        if a_merge is not None:
            print(f"Merging {a.name} and {a_other.name} into {a_merge.name}")
            del actions[idx]
            actions.append(a_merge)
            merge_found = True
            break
    if not merge_found:
        print(f"Adding {a.name} to repertoire")
        actions.append(a)
    print("-------- Current action repertoire (transition {trans}) --------")
    for a in actions:
        print(a)

