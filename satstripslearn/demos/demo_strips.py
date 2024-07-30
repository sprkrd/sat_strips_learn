from ..strips import *
from ..planning import plan, every_optimal_action

dom = Domain("visitall")

Agent = dom.declare_type("agent")
Location = dom.declare_type("location")

At = dom.declare_predicate("at", Agent, Location)
Adjacent = dom.declare_predicate("adjacent", Location, Location)

_agent = Agent("?agent")
_from = Location("?from")
_to = Location("?to")

Move = dom.declare_action("move",               # Action name
    [_agent, _from, _to],                       # Parameters
    [At(_agent, _from), Adjacent(_from, _to)],  # Precondition
    [At(_agent, _to)],                          # Add list
    [At(_agent, _from)]                         # Delete list
)

prob = Problem("myproblem", dom)

a1 = prob.add_object(Location("a1"))
a2 = prob.add_object(Location("a2"))
b1 = prob.add_object(Location("b1"))
b2 = prob.add_object(Location("b2"))
robot = prob.add_object(Agent("robot"))

prob.add_init_atom(At(robot,a1))
prob.add_init_atom(Adjacent(a1, a2))
prob.add_init_atom(Adjacent(a1, b1))
prob.add_init_atom(Adjacent(b1, a1))
prob.add_init_atom(Adjacent(b1, b2))
prob.add_init_atom(Adjacent(a2, a1))
prob.add_init_atom(Adjacent(a2, b2))
prob.add_init_atom(Adjacent(b2, a2))
prob.add_init_atom(Adjacent(b2, b1))

prob.add_goal_atom(At(robot,b2))

ctx = prob.get_initial_state()

print("static predicates:", dom.get_static_predicates())
print("ctx:", ctx)

groundings = list(Move.all_groundings(ctx))

print(groundings)
print(groundings[0].apply(ctx))
print(dom)
print(prob)

for op in plan(prob, cleanup=False):
    print(op)

print(every_optimal_action(prob, cleanup=False))

input()
