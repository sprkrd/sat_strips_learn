from ..strips import *
from ..planning import plan, every_optimal_action, IDSSolver, BFSSolver

# dom = Domain("visitall")

# Agent = dom.declare_type("agent")
# Location = dom.declare_type("location")

# At = dom.declare_predicate("at", Agent, Location)
# Adjacent = dom.declare_predicate("adjacent", Location, Location)

# _agent = Agent("?agent")
# _from = Location("?from")
# _to = Location("?to")

# Move = dom.declare_action("move",               # Action name
    # [_agent, _from, _to],                       # Parameters
    # [At(_agent, _from), Adjacent(_from, _to)],  # Precondition
    # [At(_agent, _to)],                          # Add list
    # [At(_agent, _from)]                         # Delete list
# )

# prob = Problem("myproblem", dom)

# a1 = prob.add_object(Location("a1"))
# a2 = prob.add_object(Location("a2"))
# b1 = prob.add_object(Location("b1"))
# b2 = prob.add_object(Location("b2"))
# robot = prob.add_object(Agent("robot"))

# prob.add_init_atom(At(robot,a1))
# prob.add_init_atom(Adjacent(a1, a2))
# prob.add_init_atom(Adjacent(a1, b1))
# prob.add_init_atom(Adjacent(b1, a1))
# prob.add_init_atom(Adjacent(b1, b2))
# prob.add_init_atom(Adjacent(a2, a1))
# prob.add_init_atom(Adjacent(a2, b2))
# prob.add_init_atom(Adjacent(b2, a2))
# prob.add_init_atom(Adjacent(b2, b1))

# prob.add_goal_atom(At(robot,b2))


dom = Domain("blocks")

Block = dom.declare_type("block")

On = dom.declare_predicate("on", Block, Block)
OnTable = dom.declare_predicate("ontable", Block)
Clear = dom.declare_predicate("clear", Block)
Holding = dom.declare_predicate("holding", Block)
HandEmpty = dom.declare_predicate("handempty")


_x = Block("?x")
_y = Block("?y")


Pick = dom.declare_action("pick",
    [_x],
    [OnTable(_x), Clear(_x), HandEmpty()],
    [Holding(_x)],
    [OnTable(_x), Clear(_x), HandEmpty()]
)

Place = dom.declare_action("place",
    [_x],
    [Holding(_x)],
    [OnTable(_x), Clear(_x), HandEmpty()],
    [Holding(_x)]
)

Unstack = dom.declare_action("unstack",
    [_x, _y],
    [On(_x, _y), Clear(_x), HandEmpty()],
    [Holding(_x), Clear(_y)],
    [On(_x, _y), Clear(_x), HandEmpty()]
)

Unstack = dom.declare_action("stack",
    [_x, _y],
    [Holding(_x), Clear(_y)],
    [On(_x, _y), Clear(_x), HandEmpty()],
    [Holding(_x), Clear(_y)],
)

prob = Problem("myproblem", dom)

a = prob.add_object(Block("a"))
b = prob.add_object(Block("b"))
c = prob.add_object(Block("c"))
d = prob.add_object(Block("d"))
e = prob.add_object(Block("e"))
f = prob.add_object(Block("f"))
g = prob.add_object(Block("g"))

prob.add_init_atom(OnTable(a))
prob.add_init_atom(On(b, a))
prob.add_init_atom(On(c, b))
prob.add_init_atom(OnTable(d))
prob.add_init_atom(On(e, d))
prob.add_init_atom(OnTable(f))
prob.add_init_atom(On(g, f))
prob.add_init_atom(Clear(c))
prob.add_init_atom(Clear(e))
prob.add_init_atom(Clear(g))
prob.add_init_atom(HandEmpty())

# prob.add_goal_atom(OnTable(a))
# prob.add_goal_atom(OnTable(b))
# prob.add_goal_atom(OnTable(c))
# prob.add_goal_atom(OnTable(d))
# prob.add_goal_atom(OnTable(e))
# prob.add_goal_atom(OnTable(f))
# prob.add_goal_atom(OnTable(g))

prob.add_goal_atom(On(a, b))
prob.add_goal_atom(On(b, c))
prob.add_goal_atom(On(c, d))
prob.add_goal_atom(On(d, e))
prob.add_goal_atom(On(e, f))
prob.add_goal_atom(On(f, g))


ctx = prob.get_initial_state()

print("static predicates:", dom.get_static_predicates())
print("ctx:", ctx)

groundings = list(dom.all_groundings(ctx))

print(groundings)
print(groundings[0].apply(ctx))
print(dom)
print(prob)

solver = BFSSolver(prob, timeout=60)
# solver = IDSSolver(prob)

plan = solver.solve()

print(solver.get_elapsed(), "seconds")

for action in plan:
    print(action)


# plans = solver.find_all_optimum_plans()
# for plan in plans:
    # print(plan)


opt_actions = every_optimal_action(prob)

print(opt_actions, 60)
