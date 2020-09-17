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

from tqdm import tqdm, trange

from satstripslearn.oaru import OaruAlgorithm, STANDARD_FILTERS

from benchmark_environments import SELECTED_ENVIRONMENTS as ENVIRONMENTS,\
        create_latex_tabular, get_plan_trajectory, ensure_folder_exists,\
        get_gmt_action_library, load_environment, fix_problem_index
# from benchmark_environments import ENVIRONMENTS


FILTER_FEATURES_KWARGS = None #{"min_score": -1, "fn": lambda t: min(t, default=0)}


NUMBER_OF_OBSERVATIONS = 10000
TIMEOUT = 2000 # timeout for AU in ms


def load_checkpoint(path, default=None):
    try:
        with open(path, "rb") as f:
            data = pkl.load(f)
    except FileNotFoundError:
        data = default
    return data


def save_checkpoint(path, checkpoint):
    with open(path, "wb") as f:
        pkl.dump(checkpoint, f)


def calculate_precision_and_recall(a_g_gmt, a_g):
    features_a_g_gmt = set(a_g_gmt.features)
    features_a_g = set(a_g.features)
    tp = len(features_a_g_gmt & features_a_g)
    fn = len(features_a_g_gmt - features_a_g)
    fp = len(features_a_g - features_a_g_gmt)
    prec = tp / (tp+fp)
    rec = tp / (tp+fn)
    return prec,rec


def process_observation(observation, oaru, prec_list, rec_list, updates_list):
    s, a_g_gmt, s_next = observation
    a_g, updated = oaru.action_recognition(s, s_next)
    updates_list.append(1 if updated else 0)
    prec,rec = calculate_precision_and_recall(a_g_gmt, a_g)
    prec_list.append(prec)
    rec_list.append(rec)


def accumulate_observations(env_name, observations, problems, partial_observability=None, seed=None):
    env = load_environment(env_name)
    # for idx in tqdm(PROBLEMS_SORTED_BY_DIFFICULTY[env_name][:problems]):
    for idx in trange(problems):
        env = fix_problem_index(env, idx)
        state_trajectory, action_trajectory = get_plan_trajectory(env,
                partial_observability=partial_observability, seed=seed)
        for s, a, s_next in zip(state_trajectory, action_trajectory, state_trajectory[1:]):
            observations.append( (s,a,s_next) )


def benchmark_env(env_name, seed=None, partial_observability=None):
    print(env_name)
    print("-----------")
    rng = random.Random(seed)
    oaru = OaruAlgorithm(filters=STANDARD_FILTERS, timeout=TIMEOUT)
    observations = []
    accumulate_observations(env_name, observations, 8, partial_observability,
            seed=rng.randint(0,2**32-1))
    prec_list = []
    rec_list = []
    updates_list = []
    with tqdm(total=NUMBER_OF_OBSERVATIONS) as pbar:
        obs_iter = cycle(observations)
        while len(updates_list) < NUMBER_OF_OBSERVATIONS:
            # obs = rng.choice(observations)
            obs = next(obs_iter)
            process_observation(obs, oaru, prec_list, rec_list, updates_list)
            pbar.update(1)

    result = {
            "updates": updates_list,
            "precision": prec_list,
            "recall": rec_list,
            "cpu": oaru.cpu_times
    }
    return result
    

# STYLES = ["-","--",":",".","-.","h","H"]
# def plot_update_cumsum(update_curves, domains, filename):
    # plt.figure(figsize=(3.5,3.5))
    # BIG_SIZE = 12
    # plt.rc('font', size=BIG_SIZE)          # controls default text sizes

    # ax = plt.subplot()
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    # plot_domains = domains
    # for dom,style in zip(plot_domains, cycle(STYLES)):
        # plt.plot(np.cumsum(update_curves[dom]),"k"+style)
    # plt.xlabel("Step")
    # plt.ylabel("#Updates")
    # if len(domains) > 1:
        # plt.legend(plot_domains)
    # plt.grid(True)
    # plt.tight_layout()
    # plt.savefig("out/" + filename)
    # plt.close()


def plot_results(results, path):
    row_headers = {
            "updates": "#Updates",
            "precision": "Precision",
            "recall": "Recall",
            "cpu": "CPU time (ms)",
    }
    x_values = np.arange(1,NUMBER_OF_OBSERVATIONS+1)
    for entry in results.values():
        entry["updates"] = np.cumsum(entry["updates"])
        entry["cpu"] = np.cumsum(entry["cpu"]) / x_values
        entry["precision"] = np.cumsum(entry["precision"]) / x_values
        entry["recall"] = np.cumsum(entry["recall"]) / x_values
    fig, axes = plt.subplots(nrows=4, ncols=3, figsize=(12,8), sharex="col", sharey="row")
    for col, env_tuple in enumerate(zip(ENVIRONMENTS[0::3], ENVIRONMENTS[1::3], ENVIRONMENTS[2::3])):
        for row, metric in enumerate(("updates", "cpu", "precision", "recall")):
            ax = axes[row, col]
            for env in env_tuple:
                if metric == "cpu":
                    ax.semilogy(x_values, results[env][metric])
                else:
                    ax.plot(x_values, results[env][metric])
            ax.grid(True)
            if row == 3:
                ax.legend(env_tuple, loc="lower right")
                ax.set_xlabel("#Steps")
            if col == 0:
                ax.set_ylabel(row_headers[metric], size="large")

    fig.subplots_adjust(hspace=0, wspace=0.05)

    # fig.tight_layout()
    plt.savefig(path)


def main():
    ensure_folder_exists("out")
    checkpoint_path = "out/observation_sampling_checkpoint.pkl"

    checkpoint = {
            "type": "partial_observability",
            "env_idx": 0,
            "full_observability": {},
            "partial_observability": {},
    }
    checkpoint = load_checkpoint(checkpoint_path, default=checkpoint)

    if checkpoint["type"] == "partial_observability":
        print("Partial observability")
        print("---------------------")
        for env_idx, env_name in enumerate(ENVIRONMENTS[checkpoint["env_idx"]:],
                checkpoint["env_idx"]):
            results = benchmark_env(env_name, 42, (0,5))
            checkpoint["partial_observability"][env_name] = results
            checkpoint["env_idx"] = env_idx + 1
            save_checkpoint(checkpoint_path, checkpoint)
        checkpoint["type"] = "full_observability"
        checkpoint["env_idx"] = 0
        save_checkpoint(checkpoint_path, checkpoint)

    if checkpoint["env_idx"] < len(ENVIRONMENTS):
        print("Full observability")
        print("------------------")
        for env_idx, env_name in enumerate(ENVIRONMENTS[checkpoint["env_idx"]:],
                checkpoint["env_idx"]):
            results = benchmark_env(env_name, 42)
            checkpoint["full_observability"][env_name] = results
            checkpoint["env_idx"] = env_idx + 1
            save_checkpoint(checkpoint_path, checkpoint)

    plot_results(checkpoint["full_observability"], "out/observation_sampling_full_obs_plot.pdf")
    plot_results(checkpoint["partial_observability"], "out/observation_sampling_partial_obs_plot.pdf")

    # plot_from_pkl = False
    # ensure_folder_exists("out")
    # domains_updates_cumsum = ("elevator", "depot", "sokoban")
    # full_obs_experiment( domains_updates_cumsum, plot_from_pkl )
    # partial_obs_experiment( domains_updates_cumsum, plot_from_pkl )


if __name__ == "__main__":
    main()

