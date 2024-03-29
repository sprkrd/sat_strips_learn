#!/usr/bin/env python3


from ..strips import Predicate, ObjType, ROOT_TYPE
from ..utils import get_memory_usage
from ..cluster import Cluster, cluster
from ..latom_filter import BasicObjectFilter, ObjectGraphFilter
from ..openworld import Context, Action

from pprint import pprint

Column = ObjType("column", ROOT_TYPE)
Row = ObjType("row", ROOT_TYPE)
Agent = ObjType("agent", ROOT_TYPE)

Right = Predicate("right", Column, Column)
# Left = Predicate("left", Column, Column)
Up = Predicate("up", Row, Row)
# Down = Predicate("down", Row, Row)
At = Predicate("at", Agent, Column, Row)

row_1 = Row("1")
row_2 = Row("2")
row_3 = Row("3")
row_4 = Row("4")

col_a = Column("A")
col_b = Column("B")
col_c = Column("C")
col_d = Column("D")
col_e = Column("E")

static_predicates = {
        Right(col_a, col_b), Right(col_b, col_c), Right(col_c, col_d), Right(col_d, col_e),
        Up(row_1, row_2), Up(row_2, row_3), Up(row_3, row_4)
}

robot = Agent("robot")

objects = [row_1, row_2, row_3, row_4, col_a, col_b, col_c, col_d, col_e, robot]

s0 = Context(objects, static_predicates | {At(robot, col_a, row_1)})
s1 = Context(objects, static_predicates | {At(robot, col_a, row_2)})
s2 = Context(objects, static_predicates | {At(robot, col_a, row_3)})


# Location = ObjType("location", ROOT_TYPE)
# Direction = ObjType("direction", ROOT_TYPE)
# Agent = ObjType("agent", ROOT_TYPE)

# Adjacent = Predicate("adjacent", Location, Location, Direction)
# At = Predicate("at", Agent, Location)

# loc_1_1 = Location("loc-1-1")
# loc_1_2 = Location("loc-1-2")
# loc_2_1 = Location("loc-2-1")
# loc_2_2 = Location("loc-2-2")

# left = Direction("left")
# right = Direction("right")
# up = Direction("up")
# down = Direction("down")
# directions = [left, right, up, down]

# robot = Agent("robot")

# objects = [loc_1_1, loc_1_2, loc_2_1, loc_2_2, left, right, up, down, robot]

# s0 = Context(objects, {
    # Adjacent(loc_1_1, loc_1_2, right), Adjacent(loc_1_2, loc_1_1, left),
    # Adjacent(loc_1_2, loc_2_2, down), Adjacent(loc_2_2, loc_1_2, up),
    # Adjacent(loc_2_2, loc_2_1, left), Adjacent(loc_2_1, loc_2_2, right),
    # Adjacent(loc_2_1, loc_1_1, up), Adjacent(loc_1_1, loc_2_1, down),
    # At(robot, loc_1_1)})

# s1 = Context(objects, {
    # Adjacent(loc_1_1, loc_1_2, right), Adjacent(loc_1_2, loc_1_1, left),
    # Adjacent(loc_1_2, loc_2_2, down), Adjacent(loc_2_2, loc_1_2, up),
    # Adjacent(loc_2_2, loc_2_1, left), Adjacent(loc_2_1, loc_2_2, right),
    # Adjacent(loc_2_1, loc_1_1, up), Adjacent(loc_1_1, loc_2_1, down),
    # At(robot, loc_1_2)})

# s2 = Context(objects, {
    # Adjacent(loc_1_1, loc_1_2, right), Adjacent(loc_1_2, loc_1_1, left),
    # Adjacent(loc_1_2, loc_2_2, down), Adjacent(loc_2_2, loc_1_2, up),
    # Adjacent(loc_2_2, loc_2_1, left), Adjacent(loc_2_1, loc_2_2, right),
    # Adjacent(loc_2_1, loc_1_1, up), Adjacent(loc_1_1, loc_2_1, down),
    # At(robot, loc_1_1)})


def main():
    # f = BasicObjectFilter(directions)
    f = BasicObjectFilter()

    action1 = Cluster(f(Action.from_transition(s0, s1, "action1")))
    action2 = Cluster(f(Action.from_transition(s1, s2, "action2")))

    print(action1.action)
    print(action2.action)

    action_u = cluster(action1, action2)

    print(action_u.action)
    pprint(action_u.additional_info)

    # for a in oaru.action_library.values():
        # print(a.action)
    
    # print(oaru.wall_times)
    # print(oaru.cpu_times)
    # print(oaru.peak_z3_memory)
    # z3_opts = {
            # "amo_encoding": "pseudoboolean",
            # "maxsat_engine": "wmax",
            # "optsmt_engine": "symba",
            # "timeout": 10
    # }

    # filt = ObjectGraphFilter(0, min)
    # filt = basic_object_filter # ObjectGraphFilter(0, min)


    # action0 = filt(Action.from_transition(s0, s1))#.filter_features(0, take_min=False)
    # action1 = filt(Action.from_transition(s1, s2))#.filter_features(0, take_min=False)
    # action2 = filt(Action.from_transition(s2, s3))#.filter_features(0, take_min=False)
    # action3 = filt(Action.from_transition(s3, s4))#.filter_features(0, take_min=False)
    # print(action0)
    # print(action1)
    # action_u1 = cluster(ActionCluster(action0), ActionCluster(action3), **z3_opts)
    # print(action_u1.action)
    # action_u2 = cluster(action_u1, ActionCluster(action2), **z3_opts)
    # print(action_u2.action)
    # action_u3 = cluster(action_u2, ActionCluster(action3), **z3_opts)
    # print(action_u3.action)




    # print(action_u1.action)
    # print(action_u1.additional_info["number_of_variables"])
    # print(action_u1.additional_info["elapsed_cpu_ms"])
    # print(action_u1.additional_info["z3_stats"])
    # print(get_memory_usage())
    # print(action_u1)
    # print(action_u1.parent.distance)
    # pprint(action_u1.parent.additional_info)

    # print(action2)
    # print(action3)
    # action_u2 = cluster(action2, action3, include_additional_info=True)
    # print(action_u2)
    # pprint(action_u2.parent.additional_info)

    # action_u3 = cluster(action_u1, action_u2, include_additional_info=True)
    # print(action_u3)
    # pprint(action_u3.parent.additional_info)


if __name__ == "__main__":
    main()
