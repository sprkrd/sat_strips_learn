#!/usr/bin/env python3

from z3 import *

from collections import deque
from threading import Lock
from itertools import product


INF = (1<<31)-1


s0 = set([("at", "loc-1-1"),
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-2", "loc-1-1", "left"),
    ("adj", "loc-1-2", "loc-2-2", "down"), ("adj", "loc-2-2", "loc-1-2", "up"),
    ("adj", "loc-2-2", "loc-2-1", "left"), ("adj", "loc-2-1", "loc-2-2", "right"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-1-1", "loc-2-1", "down")])

s1 = set([("at", "loc-1-2"),
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-2", "loc-1-1", "left"),
    ("adj", "loc-1-2", "loc-2-2", "down"), ("adj", "loc-2-2", "loc-1-2", "up"),
    ("adj", "loc-2-2", "loc-2-1", "left"), ("adj", "loc-2-1", "loc-2-2", "right"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-1-1", "loc-2-1", "down")])

s2 = set([("at", "loc-2-2"),
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-2", "loc-1-1", "left"),
    ("adj", "loc-1-2", "loc-2-2", "down"), ("adj", "loc-2-2", "loc-1-2", "up"),
    ("adj", "loc-2-2", "loc-2-1", "left"), ("adj", "loc-2-1", "loc-2-2", "right"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-1-1", "loc-2-1", "down")])


class SequentialUUIDGenerator:
    def __init__(self):
        self._uuid = 0
        self._mtx = Lock()

    def __call__(self):
        with self._mtx:
            uuid = self._uuid
            self._uuid += 1
        return uuid


ACT_SEQ_UUID_GEN = SequentialUUIDGenerator()
VAR_SEQ_UUID_GEN = SequentialUUIDGenerator()


def tuple_to_str(t):
    return f"({' '.join(t)})"


def replace(t, sigma):
    return (t[0],*(sigma.get(a,a) for a in t[1:]))


def is_lifted(obj):
    return obj.startswith("?")


def lift_atom(atom, ref_dict):
    head,*tail = atom
    lifted_tail = []
    for arg in tail:
        if is_lifted(arg):
            lifted_tail.append(arg)
        else:
            if arg not in ref_dict:
                ref_dict[arg] = f"?x{VAR_SEQ_UUID_GEN()}"
            lifted_tail.append(ref_dict[arg])
    return (head,*lifted_tail)


def inverse_map(d):
    inv = {v:k for k,v in d.items()}
    return inv


class DirectedGraph:
    """
    Utility class that represents a directed graph.

    Parameters
    ----------
    nodes: list
        The set of nodes of this graph
    adjacency: dict
        A dictionary from nodes u to all the nodes v s.t. there's
        an edge u->v in the graph
    """

    def __init__(self, nodes, adjacency):
        """
        See help(type(self)) for accurate signature.
        """
        self.nodes = nodes
        self.adjacency = adjacency

    def bfs(self, startset):
        """
        Breadth First Search to calculate the distance from a set of starting
        nodes to the rest of nodes in the graph.

        Parameters
        ----------
        startset: any iterable
            the set of starting nodes

        Return
        ------
        out: dict
            A dictionary from nodes to the distance to these nodes from the
            starting set.
        """
        openset = deque((0,node) for node in startset)
        closedset = {}
        while openset:
            level,u = openset.popleft()
            if u not in closedset:
                closedset[u] = level
                for v in self.adjacency[u]:
                    openset.append((level+1, v))
        return closedset

    def __str__(self):
        lines = ["DirectedGraph {"]
        for u,adjacent in self.adjacency.items():
            lines.append(f"  {u} -> {', '.join(adjacent)}")
        lines.append("}")
        return "\n".join(lines)


class Action:
    """
    Represents a STRIPS action. The class presents several utility method to
    facilitate clustering.

    Parameters
    ----------
    name: str
        name identifying the action
    pre_list: list
        precondition of the action, as list of tuples that represents a conjunction
        of atoms. Each tuple represents such an atom, which in turn is an instantiated predicate.
        The first element of the tuple is the name of the predicate, while the rest is the list
        of arguments names. Arguments with a ? character in front of its name are
        variables, prone to be substituted during action grounding. This representational
        convention is the same for the add list and for the delete list.
    add_list: list
        add effect of the action, as a list of tuples. See description of pre_list.
    del_list: list
        delete effect of the action, as a list of tuples. See description of pre_list.
    """

    def __init__(self, name, pre_list, add_list, del_list):
        """
        See help(type(self)) for accurate signature.
        """
        self.name = name
        self.pre_list = pre_list
        self.add_list = add_list
        self.del_list = del_list

    def replace_references(self, sigma):
        name = f"action-{ACT_SEQ_UUID_GEN()}"
        pre_list = [replace(a,sigma) for a in self.pre_list]
        add_list = [replace(a,sigma) for a in self.add_list]
        del_list = [replace(a,sigma) for a in self.del_list]
        return Action(name, pre_list, add_list, del_list)

    def get_object_graph(self):
        """
        Constructs a directed graph in which the referenced objects act as
        vertices. Two objects are connected through an edge if they appear together
        in at least one feature (i.e. an atom from the precondition, the add list or the
        delete list). This graph gives an idea on how "distant" objects are from each other.

        Return
        ------
        out: DirectedGraph
            a directed graph G = <V,E> in which V is the set of objects referenced by
            this action and E is the set of all (u,v) pairs s.t. u,v appear together
            in at least one atom.
        """
        nodes = self.get_referenced_objects()
        adjacency = {}
        for f in self.get_features():
            for u,v in product(f[1:], f[1:]):
                if u != v:
                    adjacency.setdefault(u, []).append(v)
        return DirectedGraph(nodes, adjacency)

    def get_precondition_scores(self):
        """
        Calculates a score for each atom in the precondition that gives an idea of
        how "distant" or unrelated they are with respect to the effects.

        Return
        ------
        out: list
            the list of scores (Int) assigned to the preconditions, in order of
            appearance. The larger the score, the more unrelated the precondition
            atom is to the effect.
        """
        effect_objects = self.get_referenced_objects(sections=["add", "del"])
        object_graph = self.get_object_graph()
        object_scores = object_graph.bfs(effect_objects)
        return [min(object_scores[o] for o in f[1:]) for f in self.pre_list]

    def get_referenced_objects(self, sections=None):
        """
        Objects referenced by this action.

        Parameters
        ----------
        sections: list or None
            The sections to check for objects.

        Return
        ------
        out: list
            list of strings, the names of the objects represented by this action.
        """
        sections = sections or ["pre", "add", "del"]
        objects = set()
        for f in self.get_features(sections=sections):
            objects.update(f[1:])
        return list(objects)

    def get_parameters(self):
        """
        List of lifted objects referenced by this action (i.e. those that are meant
        to be substitute by ground objects).

        Return
        ------
        out: list
            list of strings containing the lifted objects.
        """
        # we sort the parameters so there is some canonical ordering
        parameters = sorted(filter(is_lifted, self.get_referenced_objects()))
        return parameters

    def get_features(self, sections=None):
        """
        Joins together all the atoms present in the precondition, the add list and the
        delete list, prefixing "pre_", "add_" or "del_", accordingly, to the head of
        the atom (i.e. the name of the predicate).

        Parameters
        ----------
        sections: list
            The list of sections to join. If None, all the sections are checked.
            If a list is provided, it should contain "pre", "add", "del".
        """
        sections = sections or ["pre", "add", "del"]
        for section in sections:
            for head,*tail in getattr(self, f"{section}_list"):
                yield (f"{section}_{head}",*tail)

    def filter_preconditions(self, max_pre_score, pre_scores=None):
        """
        Computes an new action with the same effect as this one, but with
        some atoms from the precondition filtered out.

        Parameters
        ----------
        max_pre_score: Int
            Score threshold. Retain atoms whose score is less than or equal to
            this value. See get_precondition_scores to learn more about the scores.
        pre_scores: list or None
            Score vector. If the scores have already been calculated via
            get_precondition_scores, they can be provided here to avoid recomputing them.
            If None is given, get_precondition_scores is called internally.

        Return
        ------
        out: Action
            New action with same effects and filtered preconditions.
        """
        pre_scores = pre_scores or self.get_precondition_scores()
        name = f"action-{ACT_SEQ_UUID_GEN()}"
        pre_list = [f for s,f in zip(pre_scores, self.pre_list) if s <= max_pre_score]
        add_list = self.add_list[:] # copy added atoms
        del_list = self.del_list[:] # copy deleted atoms
        return Action(name, pre_list, add_list, del_list)


    def get_effect_label_count(self):
        """
        Count the number of occurrences of each predicate in the add and delete lists.

        Return
        ------
        out: dict
            A dict from string to Int that maps add/delete feature name to
            the number of occurrences in the effects.
        """
        effect_label_count = {}
        for label,*_ in self.get_features(["add", "del"]):
            effect_label_count[label] = effect_label_count.get(label,0) + 1
        return effect_label_count

    @staticmethod
    def from_transition(s, s_next, lifted=False):
        """
        Static constructor that takes two states that are interpreted as successive
        and builds an action that describes the transition.

        Parameters
        ----------
        s: set
            State represented as a collection of tuples (atom). Each tuple is a fact
            or fluent that holds in the situation represented by the state.
        s_next: set
            State after the transition
        lifted: Bool
            If True, then all the objects involved in the transition are lifted. That is,
            the referenced objects are replaced by a lifted variable of the form ?x[id].
        """
        name = f"action-{ACT_SEQ_UUID_GEN()}"
        pre = list(s)
        add_eff = list(s_next.difference(s))
        del_eff = list(s.difference(s_next))
        if lifted:
            ref_dict = {}
            pre = [lift_atom(a, ref_dict) for a in pre]
            add_eff = [lift_atom(a,ref_dict) for a in add_eff]
            del_eff = [lift_atom(a, ref_dict) for a in del_eff]
        return Action(name, pre, add_eff, del_eff)

    def __str__(self):
        name = self.name
        pre_str = ", ".join(map(tuple_to_str, self.pre_list))
        add_str = ", ".join(map(tuple_to_str, self.add_list))
        del_str = ", ".join(map(tuple_to_str, self.del_list))
        return  "Action {\n"\
               f"  name: {name}\n"\
               f"  precondition: {pre_str}\n"\
               f"  add list: {add_str}\n"\
               f"  del list: {del_str}\n"\
                "}"


class ActionCluster:
    def __init__(self, action_result, child0, child1, cluster_score):
        self.action = action
        self.child0 = child0
        self.child1 = child1
        self.cluster_score = cluster_score

    # def __str__(self):
        # return "ActionCluster {\n"\
              # f"


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


def mapvar(n0,n1):
    return f"m({n0},{n1})"


def featmatchvar(feat0, feat1):
    return f"match({tuple_to_str(feat0)},{tuple_to_str(feat1)})"


def takefeatvar(action, feat):
    return f"take{action}({tuple_to_str(feat)})"


def cluster_broadphase(action0, action1):
    """
    Simply compares the number of predicates of each type in the effects of
    action0 and action1 to make sure that they can be joined
    """
    return action0.get_effect_label_count() == action1.get_effect_label_count()


def cluster(action0, action1):
    if not cluster_broadphase(action0, action1):
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
    for n0 in nodes0:
        constraints += amo(*(variables[mapvar(n0,n1)] for n1 in nodes1))
    for n1 in nodes1:
        constraints += amo(*(variables[mapvar(n0,n1)] for n0 in nodes0))
    for f0 in feat0:
        for f1 in feat0_potential_matches.get(f0, []):
            lhs = variables[featmatchvar(f0,f1)]
            rhs = []
            for n0,n1 in zip(f0[1:],f1[1:]):
                rhs.append(variables[mapvar(n0,n1)])
            rhs = And(*rhs)
            constraints.append(lhs == rhs)
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
    for f0 in feat0:
        if not f0[0].startswith("pre_"):
            constraints.append(variables[takefeatvar(0,f0)])
        else:
            soft_constraints.append(variables[takefeatvar(0,f0)])
    for f1 in feat1:
        if not f1[0].startswith("pre_"):
            constraints.append(variables[takefeatvar(1,f1)])
        else:
            soft_constraints.append(variables[takefeatvar(1,f1)])

    # print("VARIABLES")
    # for k in variables:
        # print(k)

    # print("CONSTRAINTS")
    # for const in constraints:
        # print(const)

    o = Optimize()
    o.add(*constraints)
    for soft_const in soft_constraints:
        o.add_soft(soft_const)

    if o.check() != sat:
        return None

    model = o.model()

    # mapping_from_0_to_1 = {}
    # for n0,n1 in product(nodes0,nodes1):
        # var = variables[mapvar(n0,n1)]
        # if model[var]: # or model[var] is None: # (is it needed to check for None?)
            # mapping_from_0_to_1[n0] = n1
    # for k,v in mapping_from_0_to_1.items():
        # print(k, "<->", v)

    mapping_from_0_to_new = {}
    for n0,n1 in product(nodes0,nodes1):
        var = variables[mapvar(n0,n1)]
        if model[var] and n0 != n1: # or model[var] is None: # (is it needed to check for None?)
            mapping_from_0_to_new[n0] = f"?x{VAR_SEQ_UUID_GEN()}"

    name = f"action-{ACT_SEQ_UUID_GEN()}"
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
    return new_action

    # print(len(variables))
    # print(len(constraints))
    # print(s.check())
    # print(s.model())


if __name__ == "__main__":
    action0 = Action.from_transition(s0, s1, lifted=False)
    action1 = Action.from_transition(s1, s2, lifted=False)

    print(action0)
    print(action1)

    # print(action0)
    # action0.filter_preconditions(1)
    # print(action0)


    # print(list(action0.get_features()))
    # print(action0)
    # print(action0.get_object_graph())
    # print(action0.get_object_graph().bfs(["loc-1-1", "loc-1-2"]))
    # print(action1)
    # print(cluster_broadphase(action0, action1))
    print(cluster(action0, action1))
