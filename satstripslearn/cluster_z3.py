from itertools import product

from z3 import *

from .action import Action, ActionCluster
from .utils import *


def mapvar(n0,n1):
    return f"m({n0},{n1})"


def used(action,n):
    return f"used{action}({n})"


def featmatchvar(feat0, feat1):
    return f"match({tuple_to_str(feat0)},{tuple_to_str(feat1)})"


def takefeatvar(action, feat):
    return f"take{action}({tuple_to_str(feat)})"


def amo(*variables):
    """
    Construct a list of SAT clauses in Z3 that represents the "at most once"
    constraint using the quadratic encoding.
    Parameters
    ----------
    *variables: z3.BoolRef
        a number of Z3 variables of the Boolean sort
    Return
    ------
    out: list
        a list of Z3 Boolean expressions that, in conjunction, represents
        that at most one of the given variables can be assigned to True.
        The size of such list is N*(N-1)/2, where N = len(variables)
    """
    constraints = []
    for idx, u in enumerate(variables):
        for v in variables[idx+1:]:
            constraints.append(Or(Not(u), Not(v)))
    return constraints


def cluster(action0, action1):
    if not action0.cluster_broadphase(action1):
        return None
    feat0 = list(action0.get_features())
    nodes0 = action0.get_referenced_objects()
    feat1 = list(action1.get_features())
    nodes1 = action1.get_referenced_objects()

    feat0_potential_matches = {}
    feat1_potential_matches = {}

    variables = {}
    for n0,n1 in product(nodes0,nodes1):
        varname = mapvar(n0,n1)
        variables[varname] = Bool(varname)
    for f0,f1 in product(feat0,feat1):
        if f0[0] == f1[0]:
            feat0_potential_matches.setdefault(f0,[]).append(f1)
            feat1_potential_matches.setdefault(f1,[]).append(f0)
            varname = featmatchvar(f0,f1)
            variables[varname] = Bool(varname)
    for f0 in feat0:
        varname = takefeatvar(0,f0)
        variables[varname] = Bool(varname)
    for f1 in feat1:
        varname = takefeatvar(1,f1)
        variables[varname] = Bool(varname)

    constraints = []
    soft_constraints = []

    # nodes cannot be matched to more than one node from the other action (hard)
    for n0 in nodes0:
        constraints += amo(*(variables[mapvar(n0,n1)] for n1 in nodes1))
    for n1 in nodes1:
        constraints += amo(*(variables[mapvar(n0,n1)] for n0 in nodes0))

    # two features match iff there is a map between the objects represented
    # in said features (hard)
    for f0 in feat0:
        for f1 in feat0_potential_matches.get(f0, []):
            lhs = variables[featmatchvar(f0,f1)]
            rhs = []
            for n0,n1 in zip(f0[1:],f1[1:]):
                rhs.append(variables[mapvar(n0,n1)])
            rhs = And(*rhs)
            constraints.append(lhs == rhs)

    # a feature is taken iff there is at least one match for it (hard)
    for f0 in feat0:
        lhs = variables[takefeatvar(0,f0)]
        rhs = []
        for f1 in feat0_potential_matches.get(f0, []):
            rhs.append(variables[featmatchvar(f0,f1)])
        rhs = Or(*rhs)
        constraints.append(lhs == rhs)
    for f1 in feat1:
        lhs = variables[takefeatvar(1,f1)]
        rhs = []
        for f0 in feat1_potential_matches.get(f1, []):
            rhs.append(variables[featmatchvar(f0,f1)])
        rhs = Or(*rhs)
        constraints.append(lhs == rhs)

    # try to match the least possible amount of nodes with different name (soft)
    for n0,n1 in product(nodes0,nodes1):
        if n0 != n1:
            soft_constraints.append( (Not(variables[mapvar(n0,n1)]),1) )

    # take all effect features (hard)/take as many pre features as possible (soft)
    W_large = len(nodes0)*len(nodes1)
    for f0 in feat0:
        if not f0[0].startswith("pre_"):
            constraints.append(variables[takefeatvar(0,f0)])
        else:
            soft_constraints.append( (variables[takefeatvar(0,f0)], W_large) )
    for f1 in feat1:
        if not f1[0].startswith("pre_"):
            constraints.append(variables[takefeatvar(1,f1)])
        else:
            soft_constraints.append( (variables[takefeatvar(1,f1)], W_large) )

    o = Optimize()
    o.add(*constraints)
    for soft_const in soft_constraints:
        o.add_soft(*soft_const)

    if o.check() != sat:
        return None

    model = o.model()

    mapping_from_0_to_1 = {}
    for n0,n1 in product(nodes0,nodes1):
        var = variables[mapvar(n0,n1)]
        if model[var]: # or model[var] is None: # (is it needed to check for None?)
            mapping_from_0_to_1[n0] = n1
    for k,v in mapping_from_0_to_1.items():
        print(k, "<->", v)

    mapping_from_0_to_new = {}
    for n0,n1 in product(nodes0,nodes1):
        var = variables[mapvar(n0,n1)]
        if model[var] and n0 != n1: # or model[var] is None: # (is it needed to check for None?)
            mapping_from_0_to_new[n0] = variable_id_gen()

    name = action_id_gen()
    pre_list = []
    add_list = []
    del_list = []

    for f0 in feat0:
        var = variables[takefeatvar(0,f0)]
        if model[var]:
            section, atom_name = f0[0].split("_",1)
            atom = replace((atom_name, *f0[1:]), mapping_from_0_to_new)
            if section == "pre":
                pre_list.append(atom)
            elif section == "add":
                add_list.append(atom)
            else: # section == "del"
                del_list.append(atom)
    new_action = Action(name, pre_list, add_list, del_list)
    new_cluster = ActionCluster(action0, action1, new_action, 0)
    new_action.up = new_cluster
    return new_action
