#!/usr/bin/env python

import os
import errno
import gym
import pddlgym
import random

from tqdm import tqdm, trange

from pddlgym.structs import TypedEntity
# from pddlgym.utils import VideoWrapper
from pddlgym.parser import parse_plan_step
from pddlgym.planning import run_planner

from satstripslearn.state import State
from satstripslearn.feature import Feature
from satstripslearn.utils import pddl_to_prolog, prolog_to_pddl
from satstripslearn.action import Action


ALL_ENVIRONMENTS = [
    "gripper",
    "onearmedgripper",
    "rearrangement",
    "sokoban",
    "minecraft",
    "depot",
    "baking",
    "blocks",
    "travel",
    "doors",
    "hanoi",
    "tsp",
    "slidetile",
    "elevator",
    "ferry",
    "meetpass",
]
ALL_ENVIRONMENTS.sort()

SELECTED_ENVIRONMENTS = [
    "blocks",
    "depot",
    "elevator",
    "gripper",
    "minecraft",
    "onearmedgripper",
    "rearrangement",
    "sokoban",
    "travel"
]



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


def get_random_walk(env, length, verbose=False, seed=None, partial_observability=None):
    if seed is not None:
        env.seed(seed)
        env.action_space.seed(seed)

    obs, debug_info = env.reset()
    type_predicates = generate_type_predicates(env)

    a_lib_gmt = get_gmt_action_library(env)

    state_trajectory = [get_state(env, type_predicates)]
    action_trajectory = []

    while len(action_trajectory) < length:
        print(len(action_trajectory))
        action = env.action_space.sample(obs)
        operator, assignment = env._select_operator(obs, action)
        if operator is None:
            continue
        assignment = { pddl_to_prolog(str(k.name)):str(v.name) for k,v in assignment.items() }
        action_ours = a_lib_gmt[operator.name]
        action_ours = action_ours.instantiate( [assignment[param] for param in action_ours.get_parameters()] )
        if verbose:
            print(action_ours)
        obs, reward, done, _ = env.step(action)
        state_trajectory.append(get_state(env, type_predicates))
        action_trajectory.append(action_ours)

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


def create_latex_tabular(table):
    header, *rows = table
    ncolumns = len(header)
    padding = [max(len(str(row[j])) for row in table) for j in range(ncolumns)]
    latex_table = [
        r"\begin{tabular}{"+"r"*ncolumns+"}",
        r"\toprule",
        " & ".join(f"{field:>{pad}}" for field,pad in zip(header,padding)) + r"\\ \midrule"
    ]
    for row in rows:
        latex_table.append(" & ".join(f"{field:>{pad}}" for field,pad in zip(row,padding)) + r"\\")
    latex_table.append(r"\bottomrule")
    latex_table.append(r"\end{tabular}")
    return "\n".join(latex_table)


def environment_info(environments):
    header = [
        r"\textbf{Domain}",
        r"$\boldsymbol{|\mathcal{A}_{\mathit{GMT}}|}$",
        r"\textbf{Max. Act. Arity}",
        r"\textbf{Max. Pred. Arity}"
    ]
    table = [header]
    for env_name in environments:
        env = gym.make("PDDLEnv{}-v0".format(env_name.capitalize()))
        n_operators = len(env.domain.operators)
        max_action_arity = max(len(op.params) for op in env.domain.operators.values())
        max_predicate_arity = max(pred.arity for pred in env.domain.predicates.values())
        table.append([env_name, n_operators, max_action_arity, max_predicate_arity])
    return create_latex_tabular(table)


def state_size_stats(state_sizes):
    state_sizes = sorted(state_sizes)
    min_state_size = state_sizes[0]
    median_state_size = state_sizes[len(state_sizes)//2]
    max_state_size = state_sizes[-1]
    return f"{min_state_size}/{median_state_size}/{max_state_size}"



def problem_info_aux(env, problems, all_state_sizes, row1, row2):
    for idx in trange(problems):
        env.fix_problem_index(idx)
        state_trajectory, action_trajectory = get_plan_trajectory(env)
        row1.append(len(env._problem.objects))
        state_sizes = [len(s.atoms) for s in state_trajectory]
        all_state_sizes += state_sizes
        row2.append(state_size_stats(state_sizes))


def problem_info(environments):
    header_1 = [
            r"\textbf{Domain}",
            *(fr"\textbf{{ {i} }}" for i in range(1,9)),
    ]
    header_2 = [
            r"\textbf{Domain}",
            *(fr"\textbf{{ {i} }}" for i in range(1,9)),
            r"\textbf{All}"
    ]
    table_1 = [header_1]
    table_2 = [header_2]
    for env_name in tqdm(environments):
        row1 = [env_name]
        row2 = [env_name]
        env = gym.make("PDDLEnv{}-v0".format(env_name.capitalize()))
        all_state_sizes = []
        problem_info_aux(env, 5, all_state_sizes, row1, row2)
        env = gym.make("PDDLEnv{}Test-v0".format(env_name.capitalize()))
        problem_info_aux(env, 3, all_state_sizes, row1, row2)
        row2.append(state_size_stats(all_state_sizes))
        table_1.append(row1)
        table_2.append(row2)
    return create_latex_tabular(table_1), create_latex_tabular(table_2)


if __name__ == "__main__":
    env_info_table = environment_info(SELECTED_ENVIRONMENTS)
    table_objects, table_states = problem_info(SELECTED_ENVIRONMENTS)
    print(env_info_table)
    print()
    print(table_objects)
    print()
    print(table_states)
    
    # env = gym.make("PDDLEnvSokoban-v0")
    # env.fix_problem_index(0)
    # get_random_walk(env, 30, seed=42, verbose=True)

