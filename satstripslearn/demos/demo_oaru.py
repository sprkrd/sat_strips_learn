#!/usr/bin/env python3

from ..oaru import OaruAlgorithm
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
Left = Predicate("left", Column, Column)
Up = Predicate("up", Row, Row)
Down = Predicate("down", Row, Row)
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
s3 = Context(objects, static_predicates | {At(robot, col_b, row_3)})
s4 = Context(objects, static_predicates | {At(robot, col_c, row_3)})
s5 = Context(objects, static_predicates | {At(robot, col_d, row_3)})
s6 = Context(objects, static_predicates | {At(robot, col_d, row_2)})
s7 = Context(objects, static_predicates | {At(robot, col_d, row_1)})
s8 = Context(objects, static_predicates | {At(robot, col_c, row_1)})
s9 = Context(objects, static_predicates | {At(robot, col_b, row_1)})
s10 = Context(objects, static_predicates | {At(robot, col_a, row_1)})
s11 = Context(objects, static_predicates | {At(robot, col_b, row_1)})
s12 = Context(objects, static_predicates | {At(robot, col_c, row_1)})
s13 = Context(objects, static_predicates | {At(robot, col_d, row_1)})
s14 = Context(objects, static_predicates | {At(robot, col_d, row_2)})
s15 = Context(objects, static_predicates | {At(robot, col_d, row_3)})
s16 = Context(objects, static_predicates | {At(robot, col_c, row_3)})
s17 = Context(objects, static_predicates | {At(robot, col_b, row_3)})
s18 = Context(objects, static_predicates | {At(robot, col_a, row_3)})
s19 = Context(objects, static_predicates | {At(robot, col_a, row_2)})
s20 = Context(objects, static_predicates | {At(robot, col_a, row_1)})

n11 = Context(objects, static_predicates | {At(robot, col_d, row_1)})
n12 = Context(objects, static_predicates | {At(robot, col_d, row_4)})

n21 = Context(objects, static_predicates | {At(robot, col_a, row_1)})
n22 = Context(objects, static_predicates | {At(robot, col_e, row_1)})

n31 = Context(objects, static_predicates | {At(robot, col_a, row_3)})
n32 = Context(objects, static_predicates | {At(robot, col_c, row_3)})


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

    oaru = OaruAlgorithm(add_non_novel=False)

    f = BasicObjectFilter()

    a_g, updated = oaru.action_recognition(s0, s1, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s1, s2, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s2, s3, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s3, s4, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s4, s5, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s5, s6, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s6, s7, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s7, s8, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s8, s9, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s9, s10, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s10, s11, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s11, s12, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s12, s13, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s13, s14, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s14, s15, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s15, s16, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s16, s17, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s17, s18, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s18, s19, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s19, s20, f)
    print(a_g, updated)

    oaru.draw_graph("output", filename="before_negative_examples", view=True, coarse=False, highlight_last_actions=True, dim_non_updated=True)

    oaru.add_negative_example(n11, n12)
    oaru.add_negative_example(n21, n22)
    oaru.add_negative_example(n31, n32)
    a_g, updated = oaru.action_recognition(s0, s1, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s1, s2, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s2, s3, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s3, s4, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s4, s5, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s5, s6, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s6, s7, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s7, s8, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s8, s9, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s9, s10, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s10, s11, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s11, s12, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s12, s13, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s13, s14, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s14, s15, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s15, s16, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s16, s17, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s17, s18, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s18, s19, f)
    print(a_g, updated)

    a_g, updated = oaru.action_recognition(s19, s20, f)
    print(a_g, updated)

    oaru.draw_graph("output", filename="after_negative_examples", view=True, coarse=False, highlight_last_actions=True, dim_non_updated=True)

    for op in oaru.history:
        print(op)



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
