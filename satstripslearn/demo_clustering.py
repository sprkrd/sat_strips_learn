#!/usr/bin/env python3


from z3 import *


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


_UUID = 0
def get_seq_uuid():
    """non-atomic: single thread only!"""
    global _UUID
    uuid = _UUID
    _UUID += 1
    return uuid


def tuple_to_str(t):
    return f"({' '.join(t)})"


class Action:
    def __init__(self, name, pre_list, add_list, delete_list):
        self.name = name
        self.pre_list = pre_list
        self.add_list = add_list
        self.delete_list = delete_list

    @staticmethod
    def from_transition(s, s_next):
        name = f"action-{get_seq_uuid()}"
        pre = s
        add_eff = s_next.difference(s)
        del_eff = s.difference(s_next)
        return Action(name, pre, add_eff, del_eff)


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


def cluster_broadphase(action0, action1):
    """simply compare the number of predicates of each type in the effects of
    action0 and action1 to make sure that they can be joined"""
    count0_add = {}
    count0_del = {}
    count1_add = {}
    count1_del = {}
    for p,*_ in action0.add_list:
        count0_add[p] = count0_add.get(p, 0) + 1
    for p,*_ in action0.delete_list:
        count0_del[p] = count0_del.get(p, 0) + 1
    for p,*_ in action1.add_list:
        count1_add[p] = count1_add.get(p, 0) + 1
    for p,*_ in action1.delete_list:
        count1_del[p] = count1_del.get(p, 0) + 1
    return count0_add == count1_add and count0_del == count1_del


def cluster(action0, action1):
    if not cluster_broadphase(action0, action1):
        return None
    objects0 = set()
    objects1 = set()

    


if __name__ == "__main__":
    action0 = Action.from_transition(s0, s1)
    action1 = Action.from_transition(s1, s2)
    print(action0)
    print(action1)
    print(cluster_broadphase(action0, action1))


