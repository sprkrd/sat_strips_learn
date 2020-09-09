#!/usr/bin/env python3

import os
import shutil
import errno

import tqdm
import gym
import pddlgym

from glob import glob

from PIL import Image

from pddlgym.utils import VideoWrapper
from pddlgym.planning import run_planner
from pddlgym.parser import parse_plan_step

from satstripslearn.action import Action
from satstripslearn.oaru import OaruAlgorithm


from benchmark_performance_and_accuracy import ensure_folder_exists, get_state, generate_type_predicates


DOMAIN = "sokoban"
PROBLEM_IDX = 0


def mean(t):
    if t:
        return sum(t)/len(t)
    return 0


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


def record_transition(prv, nxt, oaru, output_folder="out"):
    folders = glob(output_folder+"/trans*")
    current_trans = len(folders)
    trans_folder = output_folder+f"/trans{current_trans}"
    ensure_folder_exists(trans_folder)
    prev_img = Image.fromarray(prv[0], "RGBA")
    next_img = Image.fromarray(nxt[0], "RGBA")
    prev_img.save(trans_folder+"/prev.png")
    next_img.save(trans_folder+"/next.png")
    oaru.action_recognition(prv[1], nxt[1])
    oaru.draw_graph(trans_folder, view=False, cleanup=True, line_len=31, rankdir="LR")
    oaru.draw_graph(trans_folder, coarse=True, view=False, cleanup=True,
            highlight_top=False, filename="g_coarse.gv", rankdir="LR")


def run_planning_agent_demo(env, outdir="out", fps=3, verbose=False, seed=None,
        planner_name="ff", oaru=None):
    oaru = oaru or OaruAlgorithm(filter_features_kwargs={"min_score": -0.5, "fn": mean})

    if seed is not None:
        env.seed(seed)

    if env._render:
        if env._problem_index_fixed:
            problem_idx = env._problem_idx
            video_path = os.path.join(outdir, 'planning_{}_{}_{}_demo.gif'.format(
                planner_name, env.spec.id, problem_idx))
        else:
            video_path = os.path.join(outdir, 'planning_{}_{}_demo.gif'.format(
                planner_name, env.spec.id))
        env = VideoWrapper(env, video_path, fps=fps)

    obs, debug_info = env.reset()
    type_predicates = generate_type_predicates(env.unwrapped)

    print("Planning...")
    plan = run_planner(debug_info['domain_file'], debug_info['problem_file'], "ff")

    actions = []
    for s in plan:
        a = parse_plan_step(
                s,
                env.domain.operators.values(),
                env.action_predicates,
                obs.objects,
                operators_as_actions=env.operators_as_actions
            )
        actions.append(a)

    print("Generating state trajectory...")

    state_trajectory = [ (env.render(), get_state(env.unwrapped, type_predicates)) ]

    tot_reward = 0
    for action in tqdm.tqdm(actions):
        if verbose:
            # tqdm.write(f"Obs: {list(obs}")
            tqdm.tqdm.write(f"Act: {action}")

        obs, reward, done, _ = env.step(action)
        # env.render()
        state_trajectory.append( (env.render(), get_state(env, type_predicates)) )
        record_transition(state_trajectory[-2], state_trajectory[-1], oaru)
        tot_reward += reward
        if verbose:
            tqdm.tqdm.write(f"Rew: {reward}")

        if done:
            break

    if verbose:
        # print("Final obs:", obs)
        print("Total reward:", tot_reward)
        print()

    env.close()


def main():
    regular_problems = 5
    test_problems = 3
    env = gym.make(f"PDDLEnv{DOMAIN.capitalize()}-v0")
    env.fix_problem_index(PROBLEM_IDX)
    run_planning_agent_demo(env, verbose=True)


if __name__ == "__main__":
    main()


