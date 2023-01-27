from ..openworld import Action as OpenWorldAction, LabeledAtom, wrap_predicate
from ..strips import Action as StripsAction, ObjType, Predicate

Agent = ObjType("agent")
Location = ObjType("location")

_agent = Agent("?agent")
_from = Location("?from")
_to = Location("?to")


At = wrap_predicate("at", Agent, Location)
Adjacent = wrap_predicate("adjacent", Location, Location)

openworld_action = OpenWorldAction("move",
    [_agent, _from, _to],
    [
        At(_agent, _from, section="pre"), Adjacent(_from, _to, section="pre"),
        At(_agent, _to, section="add"),
        At(_agent, _from, section="del")
    ],
)

print(openworld_action)

robot = Agent("robot")
a4 = Location("a4")
a3 = Location("a3")


print(openworld_action.to_latex())
