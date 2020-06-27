#!/usr/bin/env python3


from .action import Action
from .cluster_z3 import cluster



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

s3 = set([("at", "loc-2-1"),
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-2", "loc-1-1", "left"),
    ("adj", "loc-1-2", "loc-2-2", "down"), ("adj", "loc-2-2", "loc-1-2", "up"),
    ("adj", "loc-2-2", "loc-2-1", "left"), ("adj", "loc-2-1", "loc-2-2", "right"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-1-1", "loc-2-1", "down")])

s4 = set([("at", "loc-2-2"),
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-2", "loc-1-1", "left"),
    ("adj", "loc-1-2", "loc-2-2", "down"), ("adj", "loc-2-2", "loc-1-2", "up"),
    ("adj", "loc-2-2", "loc-2-1", "left"), ("adj", "loc-2-1", "loc-2-2", "right"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-1-1", "loc-2-1", "down")])



if __name__ == "__main__":
    # action0 = Action.from_transition(s0, s1, lifted=False)
    # action1 = Action.from_transition(s3, s4, lifted=False)

    # # action0 = action0.filter_preconditions(0)
    # # action1 = action1.filter_preconditions(0)

    # print(action0)
    # print(action1)

    # # print(action0)
    # # action0.filter_preconditions(1)
    # # print(action0)


    # # print(list(action0.get_features()))
    # # print(action0)
    # # print(action0.get_object_graph())
    # # print(action0.get_object_graph().bfs(["loc-1-1", "loc-1-2"]))
    # # print(action1)
    # # print(cluster_broadphase(action0, action1))
    # print(cluster(action0, action1))
    action0 = Action.from_transition(s0, s1, lifted=False).filter_preconditions(0)
    action1 = Action.from_transition(s1, s2, lifted=False).filter_preconditions(0)
    action2 = Action.from_transition(s2, s1, lifted=False).filter_preconditions(0)
    action3 = Action.from_transition(s1, s0, lifted=False).filter_preconditions(0)
    print(action0)
    print(action1)
    print("--------------")
    cluster_0_1 = cluster(action0, action1)
    print(cluster_0_1)
    print(action2)
    print("--------------")
    cluster_2_3 = cluster(action2, cluster_0_1)
    print(cluster_2_3)
    print(action3)
    print("--------------")
    cluster_4_5 = cluster(action3, cluster_2_3)
    print(cluster_4_5)
    # print(action0)
    # action0.filter_preconditions(1)
    # print(action0)


    # print(list(action0.get_features()))
    # print(action0)
    # print(action0.get_object_graph())
    # print(action0.get_object_graph().bfs(["loc-1-1", "loc-1-2"]))
    # print(action1)
    # print(cluster_broadphase(action0, action1))
    # print(cluster(action0, action1))
    # print(cluster(cluster(action0,action1),action2))
    # print(cluster(cluster(cluster(action0,action1),action2),action3))
