#!/usr/bin/env python3

from satstripslearn.strips import *


dom = Domain("hey")

Agent = dom.declare_type("agent")
Location = dom.declare_type("location")

_agent = Agent("?agent")
_from = Location("?from")
_to = Location("?to")

robot = Agent("robot")
src = Location("src")
dst = Location("dst")

a1 = Location("a1")
a2 = Location("a2")
b1 = Location("b1")
b2 = Location("b2")

At = dom.declare_predicate("at", Agent, Location)
Adjacent = dom.declare_predicate("adjacent", Location, Location)

Move = dom.declare_action("move", [_agent, _from, _to],
    [At(_agent, _from), Adjacent(_from, _to)],
    [At(_agent, _to)],
    [At(_agent, _from)]
)

state = {At(robot, a1),
         Adjacent(a1, a2),
         Adjacent(a2, a1),
         Adjacent(a1, b1),
         Adjacent(b1, a1),
         Adjacent(b1, b2),
         Adjacent(b2, b1),
         Adjacent(a2, b2),
         Adjacent(b2, a2)
}

objects = [robot, a1, a2, b1, b2]

groundings = list(Move.all_groundings(objects, state))

print(groundings[0].apply(state))

print(groundings)

print(dom)

problem = Problem("myproblem", dom, set(objects), list(state), [At(robot, b2)])

print(problem)
