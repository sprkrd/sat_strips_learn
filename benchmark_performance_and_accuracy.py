#!/usr/bin/env python3

import os
import shutil
import errno

import gym
import pddlgym
import numpy as np

from glob import glob

from PIL import Image

from tqdm import trange

from pddlgym.structs import TypedEntity
# from pddlgym.utils import VideoWrapper
from pddlgym.parser import parse_plan_step
from pddlgym.planning import run_planner

from satstripslearn.oaru import OaruAlgorithm
from satstripslearn.viz import draw_cluster_graph
from satstripslearn.state import State
from satstripslearn.action import Action
from satstripslearn.feature import Feature
from satstripslearn.utils import pddl_to_prolog

from benchmark_environments import SELECTED_ENVIRONMENTS as ENVIRONMENTS, create_latex_tabular
# from benchmark_environments import ENVIRONMENTS


def ensure_folder_exists(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def get_state(env):
    obs = env.get_state()
    state = set(lit_as_tuple(lit) for lit in obs.literals)
    if env._problem.uses_typing:
        for obj in env._problem.objects:
            state.add((str(obj.var_type), obj.name))
    return State(state)


def lit_as_tuple(lit):
    return (lit.predicate.name,) + tuple(pddl_to_prolog(arg.name if isinstance(arg, TypedEntity) else arg)
            for arg in lit.variables)


def action_from_pddlgym_operator(op):
    name = op.name
    features = []
    for lit in op.preconds.literals:
        feat = Feature(lit_as_tuple(lit), feature_type="pre", certain=True)
        features.append(feat)
    for lit in op.effects.literals:
        feature_type = "del" if lit.is_anti else "add"
        feat = Feature(lit_as_tuple(lit), feature_type=feature_type, certain=True)
        features.append(feat)
    parameters = []
    for param in op.params:
        if isinstance(param, TypedEntity):
            param_name = pddl_to_prolog(param.name)
            feat = Feature((str(param.var_type), param_name), feature_type="pre", certain=True)
            features.append(feat)
        else:
            param_name = pddl_to_prolog(str(param))
        parameters.append(param_name)
    return Action(name, features, parameters_in_canonical_order=parameters)


def get_gmt_action_library(env):
    actions = list(map(action_from_pddlgym_operator, env.domain.operators.values()))
    action_lib = {action.name:action for action in actions}
    return action_lib


def get_plan_trajectory(env, verbose=False, seed=None):
    if seed is not None:
        env.seed(seed)

    obs, debug_info = env.reset()
    plan = run_planner(debug_info['domain_file'], debug_info['problem_file'], "ff")

    a_lib_gmt = get_gmt_action_library(env)

    action_trajectory = [a_lib_gmt[a_name].instantiate(a_args)
        for a_name,*a_args in map(str.split, plan)]

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

    state_trajectory = [get_state(env)]

    for action in actions:
        if verbose:
            print("Obs:", obs)
            print("Act:", action)

        obs, _, done, _ = env.step(action)
        # env.render()

        state_trajectory.append(get_state(env))

        if done:
            break

    if verbose:
        print("Final obs:", obs)
        print()

    env.close()
    if verbose:
        input("press enter to continue to next problem")
    return state_trajectory, action_trajectory


def calculate_precision_and_recall(a_g_gmt, a_g):
    features_a_g_gmt = set(a_g_gmt.features)
    features_a_g = set(a_g.features)
    tp = len(features_a_g_gmt & features_a_g)
    fn = len(features_a_g_gmt - features_a_g)
    fp = len(features_a_g - features_a_g_gmt)
    prec = tp / (tp+fp)
    rec = tp / (tp+fn)
    return prec,rec


def process_trajectory(state_trajectory, action_trajectory, oaru,
        prec_list, rec_list, transition_idx=0, last_update_idx=0):
    for i in trange(len(state_trajectory)-1):
        s_prev = state_trajectory[i]
        s = state_trajectory[i+1]
        a_g, updated = oaru.action_recognition(s_prev, s)
        a_g_gmt = action_trajectory[i]
        prec,rec = calculate_precision_and_recall(a_g_gmt, a_g)
        prec_list.append(prec)
        rec_list.append(rec)
        if updated:
            last_update_idx = transition_idx + i
    transition_idx += len(state_trajectory)-1
    return (transition_idx, last_update_idx)


def benchmark_env(env_name, table):
    print(env_name)
    env = gym.make("PDDLEnv{}-v0".format(env_name.capitalize()))
    oaru = OaruAlgorithm(filter_features_kwargs={"take_min": True, "min_score": -1})
    transition_idx = 0
    last_update_idx = 0
    prec_list = []
    rec_list = []
    for idx in trange(5):
        env.fix_problem_index(idx)
        state_trajectory, action_trajectory = get_plan_trajectory(env)
        transition_idx, last_update_idx = process_trajectory(
            state_trajectory, action_trajectory, oaru, prec_list, rec_list,
            transition_idx, last_update_idx)

    row = [
            env_name,
            len(oaru.action_library),
            last_update_idx,
            fr"${np.mean(oaru.cpu_times):.0f} \pm {np.std(oaru.cpu_times):.0f}$",
            fr"{oaru.peak_z3_memory:.02}",
            fr"${np.mean(prec_list)*100:.0f} \pm {np.std(prec_list)*100:.0f}$",
            fr"${np.mean(rec_list)*100:.0f} \pm {np.std(rec_list)*100:.0f}$"]
    table.append(row)

    # print("|A|:", len(oaru.action_library))
    # print("Number of transitions:", transition_idx)
    # print("L:", last_update_idx)
    # print("Avg. CPU time:", np.mean(oaru.cpu_times), "+-", np.std(oaru.cpu_times), "ms")
    # print("Avg. Wall time:", np.mean(oaru.wall_times), "+-", np.std(oaru.wall_times), "ms")
    # print("Peak Z3 memory:", oaru.peak_z3_memory, "MB")
    # print("Precision:", np.mean(prec_list), "+-", np.std(prec_list))
    # print("Recall:", np.mean(rec_list), "+-", np.std(rec_list))
    print("--------------")
    print()


# benchmark_env("gripper")

# env = gym.make("PDDLEnvBlocks-v0")
# alibgmt = get_gmt_action_library(env)
#
# for a in alibgmt.values():
#     print(a)

# \textbf{Domain} & $\boldsymbol{|\mathcal{A}|}$ &      \textbf{L} & \textbf{T (ms)} & \textbf{M (MB)} & \textbf{Prec.} & \textbf{Rec.}
header = [
    r"\textbf{Domain}",
    r"$\boldsymbol{|\mathcal{A}|}$",
    r"\textbf{L}",
    r"\textbf{T (ms)}",
    r"\textbf{M (MB)}",
    r"\textbf{Prec. (\%)}",
    r"\textbf{Rec.(\%)}"
]
table = [header]

for env_name in ENVIRONMENTS:
    benchmark_env(env_name, table)
print(create_latex_tabular(table))
#     print(env_name)
#     print("-----------")
#     env = gym.make("PDDLEnv{}-v0".format(env_name.capitalize()))
#     env.fix_problem_index(4)
#     states = get_plan_trajectory(env, False)
#     print(len(states)-1, "step(s)")
#     print()
