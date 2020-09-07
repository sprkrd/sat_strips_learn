#!/usr/bin/env python

import gym
import pddlgym


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


if __name__ == "__main__":
    print(environment_info(SELECTED_ENVIRONMENTS))
