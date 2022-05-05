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

At = dom.declare_predicate("at", _agent, _from)
Adjacent = dom.declare_predicate("adjacent", _from, _to)

Move = dom.declare_action("move", [_agent, _from, _to],
    [At(_agent, _from), Adjacent(_from, _to)],
    [At(_agent, _to)],
    [At(_agent, _from)]
)

state = {At(robot, Location("a1")), Adjacent(Location("a1"), Location("a2")), Adjacent(Location("a1"), Location("b1")),
         Adjacent(Location("b1"), Location("b2")), Adjacent(Location("a2"), Location("b2"))}
         
objects = [robot, Location("a1"), Location("a2"), Location("b1"), Location("b2")]

groundings = list(Move.all_groundings(objects, state))

print(groundings[0].apply(state))

print(groundings)

print(dom)
