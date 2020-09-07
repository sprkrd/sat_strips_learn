#!/usr/bin/env python3

import os
import shutil
import errno

import gym
import pddlgym

from glob import glob

from PIL import Image

from pddlgym.structs import TypedEntity
from pddlgym.utils import VideoWrapper

from .action import Action
from .cluster_z3 import cluster
from .viz import draw_cluster_graph


def ensure_folder_exists(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def lit_as_tuple(lit):
    return (lit.predicate.name,) + tuple(arg.name if isinstance(arg, TypedEntity) else arg
            for arg in lit.variables)


def get_type_predicates(env):
    type_preds = set()
    if env._problem.uses_typing:
        for obj in env._problem.objects:
            type_preds.add((str(obj.var_type), obj.name))
    return type_preds


def record_transition(prv, nxt, actions, output_folder="out"):
    folders = glob(output_folder+"/trans*")
    current_trans = len(folders)
    trans_folder = output_folder+f"/trans{current_trans}"
    ensure_folder_exists(trans_folder)

    prev_img = Image.fromarray(prv[0], "RGBA")
    next_img = Image.fromarray(nxt[0], "RGBA")

    prev_img.save(trans_folder+"/prev.png")
    next_img.save(trans_folder+"/next.png")

    a = Action.from_transition(prv[1], nxt[1])
    merge_found = False
    with open(trans_folder + "/log.txt", "a") as f:
        for idx, a_other in enumerate(actions):
            a_merge = cluster(a, a_other)
            if a_merge is not None:
                log_msg = f"Merging {a.name} and {a_other.name} into {a_merge.name}"
                print(log_msg, file=f)
                del actions[idx]
                actions.append(a_merge)
                merge_found = True
                break
        if not merge_found:
            log_msg = f"Adding {a.name} to repertoire"
            print(log_msg, file=f)
            actions.append(a)
        print("-------- Action repertoire --------", file=f)
        for a in actions:
            print(a.to_pddl(), file=f)


def run_random_agent_demo(env, outdir="out", max_num_steps=20, fps=3,
                          verbose=False, seed=None):

    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)

    if env._render:
        video_path = os.path.join(outdir, 'random_{}_demo.gif'.format(env.spec.id))
        env = VideoWrapper(env, video_path, fps=fps)

    if seed is not None:
        env.seed(seed)

    states = []
    actions = []
    obs_prev, _ = env.reset()
    try:
        type_preds = get_type_predicates(env)
    except AttributeError:
        type_preds = get_type_predicates(env.unwrapped)
    if verbose:
        print("Type preds:", type_preds)
    obs_prev = set(lit_as_tuple(lit) for lit in obs_prev)
    obs_prev.update(type_preds)
    states.append(obs_prev)
    img_prev = env.render()

    if seed is not None:
        env.action_space.seed(seed)

    for t in range(max_num_steps):
        if verbose:
            print("Obs:", obs)

        action = env.action_space.sample()
        print(type(action))
        if verbose:
            print("Act:", action)

        obs_next, reward, done, _ = env.step(action)
        obs_next = set(lit_as_tuple(lit) for lit in obs_next)
        obs_next.update(type_preds)
        states.append(obs_next)
        img_next = env.render()
        record_transition((img_prev,obs_prev), (img_next,obs_next), actions,
                output_folder=outdir)
        img_prev, obs_prev = img_next, obs_next
        if verbose:
            print("Rew:", reward)
        if done:
            break
    if verbose:
        print("Final obs:", obs)
        print()
    env.close()
    g = draw_cluster_graph(actions)
    g.render("g.gv", format="png", cleanup=True, view=True)


def demo_random(env_name, render=True, problem_index=0, verbose=True):
    env = gym.make("PDDLEnv{}-v0".format(env_name.capitalize()))
    if not render: env._render = None
    env.fix_problem_index(problem_index)
    return run_random_agent_demo(env, verbose=verbose, seed=0)




state0 = set([("block", "A"), ("block", "B"), ("block", "C"), ("block", "D"),
        ("ontable", "A"), ("ontable", "B"), ("ontable", "C"),
        ("clear", "A"), ("clear", "B"), ("clear", "C"),
        ("handfull", "robot"), ("holding", "D")])
state1 = set([("block", "A"), ("block", "B"), ("block", "C"), ("block", "D"),
        ("ontable", "A"), ("ontable", "B"), ("ontable", "C"), ("on", "D", "B"),
        ("clear", "A"), ("clear", "C"), ("clear", "D"), 
        ("handempty", "robot")])

state2 = set([("block", "A"), ("block", "B"), ("block", "C"), ("block", "D"),
        ("ontable", "B"), ("ontable", "C"), ("on", "D", "B"),
        ("clear", "C"), ("clear", "D"), 
        ("handfull", "robot"), ("holding", "A")])
state3 = set([("block", "A"), ("block", "B"), ("block", "C"), ("block", "D"),
        ("ontable", "B"), ("ontable", "C"), ("on", "D", "B"), ("on", "A", "D"),
        ("clear", "A"), ("clear", "C"),
        ("handempty", "robot")])

act1 = Action.from_transition(state0, state1)
act2 = Action.from_transition(state2, state3)
act3 = cluster(act1, act2).filter_preconditions(0)
print(act1)
print(act2)
print(act3)

g = draw_cluster_graph([act3], atom_limit_middle=1000, bottom_top=False)
g.render("teaser_b", format="pdf", cleanup=True, view=True)

