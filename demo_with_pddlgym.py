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
from satstripslearn.oaru import OaruAlgorithm, STANDARD_FILTERS
from satstripslearn.viz import draw_cluster_graph 

from benchmark_environments import ensure_folder_exists, get_state, generate_type_predicates, get_gmt_action_library


DOMAIN = "sokoban"
PROBLEM_IDX = 0


def record_transition(prv, nxt, oaru, output_folder="out"):
    folders = glob(output_folder+"/trans*")
    current_trans = len(folders)
    trans_folder = output_folder+f"/trans{current_trans}"
    ensure_folder_exists(trans_folder)
    prev_img = Image.fromarray(prv[0], "RGBA")
    next_img = Image.fromarray(nxt[0], "RGBA")
    prev_img.save(trans_folder+"/prev.png")
    next_img.save(trans_folder+"/next.png")
    a_g, updated = oaru.action_recognition(prv[1], nxt[1])
    if updated:
        tqdm.tqdm.write(f"Update at transition {current_trans}")
    oaru.draw_graph(trans_folder, view=False, cleanup=False, format="svg", line_len=35,
            atom_limit_middle=1000, rankdir="LR", highlight_last_actions=True)
    oaru.draw_graph(trans_folder, coarse=True, view=False, cleanup=True,
            highlight_top=True, filename="g_coarse.gv", format="svg", rankdir="LR",
            highlight_last_actions=True)


def run_planning_agent_demo(env, oaru, outdir="out", fps=3, verbose=False, seed=None,
        planner_name="ff"):
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

    tqdm.tqdm.write("Planning...")
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

    tqdm.tqdm.write("Generating state trajectory...")

    state_trajectory = [ (env.render(), get_state(env.unwrapped, type_predicates)) ]

    tot_reward = 0
    for action in tqdm.tqdm(actions):
        if verbose:
            # tqdm.write(f"Obs: {list(obs}")
            tqdm.tqdm.write(f"Act: {action}")

        obs, reward, done, _ = env.step(action)
        # env.render()
        state_trajectory.append( (env.render(), get_state(env, type_predicates)) )
        record_transition(state_trajectory[-2], state_trajectory[-1], oaru, outdir)
        tot_reward += reward
        if verbose:
            tqdm.tqdm.write(f"Rew: {reward}")

        if done:
            break

    with open(f"{outdir}/domain.pddl", "w") as f:
        oaru.dump_pddl_domain(f)

    if verbose:
        # print("Final obs:", obs)
        tqdm.tqdm.write(f"Total reward: {tot_reward}")

    env.close()


def main():
    outdir = "out"
    ensure_folder_exists(outdir)
    for folder in glob(f"{outdir}/trans*"):
        shutil.rmtree(folder)
    oaru = OaruAlgorithm(filters=[STANDARD_FILTERS[-1]], timeout=1000)
    regular_problems = 1
    test_problems = 0
    env = gym.make(f"PDDLEnv{DOMAIN.capitalize()}-v0")
    env.reset()
    actions_gmt = list(get_gmt_action_library(env).values())
    g = draw_cluster_graph(actions_gmt, line_len=40, rankdir="LR")
    g.render(f"{outdir}/{DOMAIN}-actions.gv", view=True, cleanup=True, format="svg")

    for idx in tqdm.trange(regular_problems):
        env.fix_problem_index(idx)
        run_planning_agent_demo(env, outdir=outdir, verbose=True, oaru=oaru)
    env = gym.make(f"PDDLEnv{DOMAIN.capitalize()}Test-v0")
    for idx in tqdm.trange(test_problems):
        env.fix_problem(idx)
        run_planning_agent_demo(env, outdir=outdir, verbose=True, oaru=oaru)
    for action in oaru.action_library.values():
        print(action.to_pddl())


if __name__ == "__main__":
    main()


