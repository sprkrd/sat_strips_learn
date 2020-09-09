#!/usr/bin/env python3

import os
import shutil
import errno
import pickle as pkl

import gym
import pddlgym
import numpy as np
import random

import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from glob import glob
from itertools import cycle

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


FILTER_FEATURES_KWARGS = {"min_score": -0.5, "fn": lambda t: sum(t)/len(t) if t else 0}


def ensure_folder_exists(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def path_to_root(tree, node):
    path = []
    while node is not None:
        path.append(node)
        node = tree.get(node)
    return path


def generate_type_predicates(env, objects=None):
    objects = objects if objects is not None else env._problem.objects
    type_predicates = None
    if env._problem.uses_typing:
        type_predicates = set()
        type_hierarchy = {}
        for supertype,subtypes in env.domain.type_hierarchy.items():
            for subtype in subtypes:
                type_hierarchy[str(subtype)] = str(supertype)
        for obj in objects:
            obj_types = path_to_root(type_hierarchy, str(obj.var_type))
            for obj_type in obj_types:
                type_predicates.add( (obj_type, pddl_to_prolog(obj.name)) )
    return type_predicates


def get_state(env, type_predicates=None):
    obs = env.get_state()
    state = set(lit_as_tuple(lit) for lit in obs.literals)
    if type_predicates:
        state.update(type_predicates)
    return State(state)


def lit_as_tuple(lit):
    return (lit.predicate.name,) + tuple(pddl_to_prolog(arg.name if isinstance(arg, TypedEntity) else arg)
            for arg in lit.variables)


def action_from_pddlgym_operator(env, op):
    name = op.name
    features = []
    for lit in op.preconds.literals:
        if not env.operators_as_actions and lit.predicate.name in env.domain.actions:
            continue
        if lit.is_negative:
            continue
        feat = Feature(lit_as_tuple(lit), feature_type="pre", certain=True)
        features.append(feat)
    for lit in op.effects.literals:
        feature_type = "del" if lit.is_anti else "add"
        feat = Feature(lit_as_tuple(lit), feature_type=feature_type, certain=True)
        features.append(feat)
    parameters = [pddl_to_prolog(param.name) for param in op.params]
    type_preds = generate_type_predicates(env, op.params)
    if type_preds:
        for pred in type_preds:
            features.append(Feature(pred, feature_type="pre", certain=True))
    return Action(name, features, parameters_in_canonical_order=parameters)


def get_gmt_action_library(env):
    actions = [action_from_pddlgym_operator(env, op) for op in env.domain.operators.values()]
    action_lib = {action.name:action for action in actions}
    return action_lib


def get_plan_trajectory(env, verbose=False, seed=None, partial_observability=None):
    if seed is not None:
        env.seed(seed)

    obs, debug_info = env.reset()
    type_predicates = generate_type_predicates(env)
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

    state_trajectory = [get_state(env, type_predicates)]

    for action in actions:
        if verbose:
            print("Obs:", obs)
            print("Act:", action)

        obs, _, done, _ = env.step(action)
        # env.render()

        state_trajectory.append(get_state(env, type_predicates))

        if done:
            break

    if verbose:
        print("Final obs:", obs)
        print()

    env.close()
    if verbose:
        input("press enter to continue to next problem")

    if partial_observability:
        rng = random.Random(seed)
        # seen_atoms = set()
        # for state in state_trajectory:
            # seen_atoms.update(state.atoms)
        lo,hi = partial_observability
        for state in state_trajectory:
            n_selected = rng.randint(min(lo,len(state.atoms)),min(hi,len(state.atoms)))
            selected_atoms = rng.sample(state.atoms, n_selected)
            for atom in selected_atoms:
                state.atoms.remove(atom)
                state.uncertain_atoms.add(atom)

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
        prec_list, rec_list, updates_list):
    for i in trange(len(state_trajectory)-1):
        s_prev = state_trajectory[i]
        s = state_trajectory[i+1]
        a_g, updated = oaru.action_recognition(s_prev, s)
        updates_list.append(1 if updated else 0)
        a_g_gmt = action_trajectory[i]
        prec,rec = calculate_precision_and_recall(a_g_gmt, a_g)
        prec_list.append(prec)
        rec_list.append(rec)


def benchmark_env_aux(env_name, test, oaru, prec_list, rec_list, updates_list,
        problems, partial_observability=None, seed=None):
    env = gym.make("PDDLEnv{}-v0".format(env_name.capitalize() + ("Test" if test else "")))
    for idx in trange(problems):
        env.fix_problem_index(idx)
        state_trajectory, action_trajectory = get_plan_trajectory(env,
                partial_observability=partial_observability, seed=seed)
        process_trajectory(state_trajectory, action_trajectory, oaru, prec_list,
                rec_list, updates_list)



def benchmark_env(env_name, table, problems, problems_test):
    print(env_name)
    print("-----------")
    oaru = OaruAlgorithm(filter_features_kwargs=FILTER_FEATURES_KWARGS)
    prec_list = []
    rec_list = []
    updates_list = []
    benchmark_env_aux(env_name, False, oaru, prec_list, rec_list, updates_list, problems)
    benchmark_env_aux(env_name, True, oaru, prec_list, rec_list, updates_list, problems_test)
    # a_lib_gmt = get_gmt_action_library(env)
    # for a in a_lib_gmt.values():
        # print(a)
    # print("<<<<>>>>")
    # for a in oaru.action_library.values():
        # print(a)
    row = [
            env_name,
            len(oaru.action_library),
            fr"${np.mean(oaru.cpu_times):.0f} \pm {np.std(oaru.cpu_times):.0f}$",
            fr"{oaru.peak_z3_memory:.02f}",
            fr"${np.mean(prec_list)*100:.0f} \pm {np.std(prec_list)*100:.0f}$",
            fr"${np.mean(rec_list)*100:.0f} \pm {np.std(rec_list)*100:.0f}$"]
    table.append(row)
    print()
    return updates_list
    

def benchmark_env_partial_obs(env_name, table, problems, problems_test, n_reps,
        seed=None, partial_observability=(1,10)):
    print(env_name)
    print("-----------")
    rng = random.Random(seed)

    prec_list = []
    rec_list = []
    updates_list = None
    cpu_times = []
    peak_z3_memory = 0

    for i in trange(n_reps):
        updates_list = []
        oaru = OaruAlgorithm(filter_features_kwargs=FILTER_FEATURES_KWARGS)
        benchmark_env_aux(env_name, False, oaru, prec_list, rec_list, updates_list,
                problems, seed=rng.randint(0,2**32-1),
                partial_observability=partial_observability)
        benchmark_env_aux(env_name, True, oaru, prec_list, rec_list, updates_list,
                problems_test, seed=rng.randint(0,2**32-1),
                partial_observability=partial_observability)
        cpu_times += cpu_times
        peak_mem_z3 = max(peak_z3_memory, oaru.peak_z3_memory)

    row = [
            env_name,
            len(oaru.action_library),
            fr"${np.mean(oaru.cpu_times):.0f} \pm {np.std(oaru.cpu_times):.0f}$",
            fr"{oaru.peak_z3_memory:.02}",
            fr"${np.mean(prec_list)*100:.0f} \pm {np.std(prec_list)*100:.0f}$",
            fr"${np.mean(rec_list)*100:.0f} \pm {np.std(rec_list)*100:.0f}$"]
    table.append(row)
    print()
    return updates_list


HEADER = [
    r"\textbf{Domain}",
    r"$\boldsymbol{|\mathcal{A}|}$",
    r"\textbf{T (ms)}",
    r"\textbf{M (MB)}",
    r"\textbf{Prec. (\%)}",
    r"\textbf{Rec.(\%)}"
]


STYLES = ["-","--",":",".","-.","h","H"]
def plot_update_cumsum(update_curves, domains, filename):
    plt.figure(figsize=(3.5,3.5))
    BIG_SIZE = 12
    plt.rc('font', size=BIG_SIZE)          # controls default text sizes

    ax = plt.subplot()
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    plot_domains = domains
    for dom,style in zip(plot_domains, cycle(STYLES)):
        plt.plot(np.cumsum(update_curves[dom]),"k"+style)
    plt.xlabel("Step")
    plt.ylabel("#Updates")
    if len(domains) > 1:
        plt.legend(plot_domains)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("out/" + filename)
    plt.close()


def full_obs_experiment(domains_updates_cumsum, plot_from_pkl=False):
    if plot_from_pkl:
        with open("out/full_obs_updates.pkl", "rb") as f:
            update_curves = pkl.load(f)
    else:
        update_curves = {}
        table = [HEADER]
        for env_name in ENVIRONMENTS:
            updates_list = benchmark_env(env_name, table, 5, 3)
            update_curves[env_name] = updates_list
        with open("out/tabular_full_obs.tex", "w") as f:
            print(create_latex_tabular(table), file=f)
        with open("out/full_obs_updates.pkl", "wb") as f:
            pkl.dump(update_curves, f) 
    plot_update_cumsum(update_curves, domains_updates_cumsum, "full_obs_updates.pdf")


def partial_obs_experiment(domain_updates_cumsum, plot_from_pkl=False):
    if plot_from_pkl:
        with open("out/partial_obs_updates.pkl", "rb") as f:
            update_curves = pkl.load(f)
    else:
        update_curves = {}
        table = [HEADER]
        for env_name in ENVIRONMENTS:
            # if env_name in ("depot", "sokoban"):
                # table.append([env_name, "-", "-", "-", "-", "-"])
                # continue
            updates_list = benchmark_env_partial_obs(env_name, table, 5, 3,
                    n_reps=5, seed=42, partial_observability=(0,5))
            update_curves[env_name] = updates_list
        with open("out/tabular_partial_obs.tex", "w") as f:
            print(create_latex_tabular(table), file=f)
        with open("out/partial_obs_updates.pkl", "wb") as f:
            pkl.dump(update_curves, f)
    plot_update_cumsum(update_curves, domain_updates_cumsum, "partial_obs_updates.pdf")


def main():
    plot_from_pkl = True
    ensure_folder_exists("out")
    domains_updates_cumsum = ("elevator", "depot", "sokoban")
    full_obs_experiment( domains_updates_cumsum, plot_from_pkl )
    partial_obs_experiment( domains_updates_cumsum, plot_from_pkl )


if __name__ == "__main__":
    main()

