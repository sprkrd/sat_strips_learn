#!/usr/bin/env python3


from .state import State
from .utils import get_memory_usage
from .oaru import OaruAlgorithm

from pprint import pprint


s0 = State({
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-2", "loc-1-1", "left"),
    ("adj", "loc-1-2", "loc-2-2", "down"), ("adj", "loc-2-2", "loc-1-2", "up"),
    ("adj", "loc-2-2", "loc-2-1", "left"), ("adj", "loc-2-1", "loc-2-2", "right"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-1-1", "loc-2-1", "down")}, {("at", "loc-1-1"),})

s1 = State({
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-2", "loc-1-1", "left"),
    ("adj", "loc-1-2", "loc-2-2", "down"), ("adj", "loc-2-2", "loc-1-2", "up"),
    ("adj", "loc-2-2", "loc-2-1", "left"), ("adj", "loc-2-1", "loc-2-2", "right"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-1-1", "loc-2-1", "down")}, {("at", "loc-1-2"),})

s2 = State({("at", "loc-2-2"),
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-2", "loc-1-1", "left"),
    ("adj", "loc-1-2", "loc-2-2", "down"), ("adj", "loc-2-2", "loc-1-2", "up"),
    ("adj", "loc-2-2", "loc-2-1", "left"), ("adj", "loc-2-1", "loc-2-2", "right"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-1-1", "loc-2-1", "down")})

s3 = State({("at", "loc-2-1"),
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-2", "loc-1-1", "left"),
    ("adj", "loc-1-2", "loc-2-2", "down"), ("adj", "loc-2-2", "loc-1-2", "up"),
    ("adj", "loc-2-2", "loc-2-1", "left"), ("adj", "loc-2-1", "loc-2-2", "right"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-1-1", "loc-2-1", "down")})

s4 = State({("at", "loc-2-2"),
    ("adj", "loc-1-1", "loc-1-2", "right"), ("adj", "loc-1-2", "loc-1-1", "left"),
    ("adj", "loc-1-2", "loc-2-2", "down"), ("adj", "loc-2-2", "loc-1-2", "up"),
    ("adj", "loc-2-2", "loc-2-1", "left"), ("adj", "loc-2-1", "loc-2-2", "right"),
    ("adj", "loc-2-1", "loc-1-1", "up"), ("adj", "loc-1-1", "loc-2-1", "down")})



if __name__ == "__main__":
    oaru = OaruAlgorithm(filter_features_kwargs={"min_score": 0, "take_min": False})
    print(oaru.action_recognition(s0, s1))
    print(oaru.action_recognition(s1, s2))
    print(oaru.action_recognition(s2, s1))
    print(oaru.action_recognition(s1, s0))

    print(oaru.wall_times)
    print(oaru.cpu_times)
    print(oaru.peak_z3_memory)

    #
    #
    # action0 = Action.from_transition(s0, s1, lifted=False).filter_features(0, take_min=False)
    # action1 = Action.from_transition(s1, s2, lifted=False).filter_features(0, take_min=False)
    # action2 = Action.from_transition(s2, s1, lifted=False).filter_features(0, take_min=False)
    # action3 = Action.from_transition(s1, s0, lifted=False).filter_features(0, take_min=False)
    # print(action0)
    # print(action1)
    # action_u1 = cluster(action0, action1, include_additional_info=True)
    # print(action_u1)
    # print(action_u1.parent.distance)
    # pprint(action_u1.parent.additional_info)
    #
    # print(action2)
    # print(action3)
    # action_u2 = cluster(action2, action3, include_additional_info=True)
    # print(action_u2)
    # pprint(action_u2.parent.additional_info)
    #
    # action_u3 = cluster(action_u1, action_u2, include_additional_info=True)
    # print(action_u3)
    # pprint(action_u3.parent.additional_info)
