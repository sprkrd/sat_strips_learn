#!/usr/bin/env python3


from z3 import *
from threading import Lock


s0 = set([("at", "loc-1-1"),
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-1", "loc-2-1", "down"),
    ("adj", "loc-1-2", "loc-1-1", "left"), ("adj", "loc-1-2", "loc-2-2", "down"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-2-1", "loc-2-2", "right")])

s1 = set([("at", "loc-1-2"),
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-1", "loc-2-1", "down"),
    ("adj", "loc-1-2", "loc-1-1", "left"), ("adj", "loc-1-2", "loc-2-2", "down"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-2-1", "loc-2-2", "right")])

s2 = set([("at", "loc-2-2"),
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-1", "loc-2-1", "down"),
    ("adj", "loc-1-2", "loc-1-1", "left"), ("adj", "loc-1-2", "loc-2-2", "down"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-2-1", "loc-2-2", "right")])


class SequentialUUIDGenerator:
    def __init__(self):
        self._uuid = 0
        self._mtx = Lock()

    def __call__(self):
        with self._mtx:
            uuid = self._uuid
            self._uuid += 1
        return uuid


SEQ_UUID_GEN = SequentialUUIDGenerator()


def tuple_to_str(t):
    return f"({' '.join(t)})"


def replace(t, sigma):
    return (t[0],*(sigma.get(a,a) for a in t))


def lift_atom(atom):
    head,*tail = atom
    return (head,*(arg if arg.startswith("?") else "?"+arg for arg in tail))


class Action:
    def __init__(self, name, pre_list, add_list, delete_list):
        self.name = name
        self.pre_list = pre_list
        self.add_list = add_list
        self.delete_list = delete_list

    def get_referenced_objects(self):
        objects = set()
        for f in self.get_features():
            objects.update(f[1:])
        return sorted(objects)

    def get_features(self):
        for section in ["pre", "add", "delete"]:
            for head,*tail in getattr(self, f"{section}_list"):
                yield (f"{section}_{head}",*tail)

    def get_effect_label_count(self):
        effect_label_count = {}
        for label,*_ in self.get_features():
            if not label.startswith("pre_"):
                effect_label_count[label] = effect_label_count.get(label,0) + 1
        return effect_label_count

    @staticmethod
    def from_transition(s, s_next, lifted=False):
        name = f"action-{SEQ_UUID_GEN()}"
        pre = s
        add_eff = s_next.difference(s)
        del_eff = s.difference(s_next)
        if lifted:
            pre = map(lift_atom, pre)
            add_eff = map(lift_atom, add_eff)
            del_eff = map(lift_atom, del_eff)
        return Action(name, list(pre), list(add_eff), list(del_eff))

    def __str__(self):
        name = self.name
        pre_str = ", ".join(map(tuple_to_str, self.pre_list))
        add_str = ", ".join(map(tuple_to_str, self.add_list))
        del_str = ", ".join(map(tuple_to_str, self.delete_list))
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
    """simply compare the number of predicates of each type in the effects of
    action0 and action1 to make sure that they can be joined"""
    return action0.get_effect_label_count() == action1.get_effect_label_count()


def cluster(action0, action1):
    if not cluster_broadphase(action0, action1):
        return None
    feat0 = list(action0.get_features())
    nodes0 = action0.get_referenced_objects()
    feat1 = list(action0.get_features())
    nodes1 = action1.get_referenced_objects()

    feat0_potential_matches = {}
    feat1_potential_matches = {}

    variables = {}
    for n0 in nodes0:
        for n1 in nodes1:
            varname = mapvar(n0,n1)
            variables[varname] = Bool(varname)
    for f0 in feat0:
        for f1 in feat1:
            if f0[0] == f1[0]:
                feat0_potential_matches.get(f0,[]).append(f1)
                feat1_potential_matches.get(f1,[]).append(f0)
                varname = featmatchvar(f0,f1)
                variables[varname] = Bool(varname)
    for f0 in feat0:
        varname = takefeatvar(0,f0)
        variables[varname] = Bool(varname)
    for f1 in feat1:
        varname = takefeatvar(1,f1)
        variables[varname] = Bool(varname)

    constraints = []
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
    for f1 in feat1:
        if not f1[0].startswith("pre_"):
            constraints.append(variables[takefeatvar(1,f1)])

    for k in variables:
        print(k)

    for const in constraints[:100]:
        print(const)

    s = Solver()
    s.add(*constraints)

    print(len(variables))
    print(len(constraints))
    print(s.check())
    # print(s.model())


if __name__ == "__main__":
    action0 = Action.from_transition(s0, s1)
    action1 = Action.from_transition(s1, s2)



    print(list(action0.get_features()))
    print(action0)
    print(action1)
    print(cluster_broadphase(action0, action1))
    cluster(action0, action1)


