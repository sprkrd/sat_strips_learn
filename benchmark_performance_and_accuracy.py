#!/usr/bin/env python3

import os
import shutil
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

from itertools import cycle

from tqdm import trange

from satstripslearn.oaru import OaruAlgorithm

from benchmark_environments import SELECTED_ENVIRONMENTS as ENVIRONMENTS, create_latex_tabular, get_plan_trajectory, ensure_folder_exists
# from benchmark_environments import ENVIRONMENTS


FILTER_FEATURES_KWARGS = {"min_score": -0.5, "fn": lambda t: sum(t)/len(t) if t else 0}



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
            len(updates_list),
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
            len(updates_list),
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
    r"$|\mathcal{O}|$",
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
    plot_from_pkl = False
    ensure_folder_exists("out")
    domains_updates_cumsum = ("elevator", "depot", "sokoban")
    full_obs_experiment( domains_updates_cumsum, plot_from_pkl )
    partial_obs_experiment( domains_updates_cumsum, plot_from_pkl )


if __name__ == "__main__":
    main()

