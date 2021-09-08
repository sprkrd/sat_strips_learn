from .state import State
from .action import Action
from .feature import Feature


def main():
    state = State(set([
        ("on", "a", "b"), ("on", "b", "c"), ("ontable", "c"), ("clear", "a"),
        ("ontable", "d"), ("clear", "d"), ("on", "e", "f"), ("ontable", "f"),
        ("clear", "e"), ("handempty",)]
    ))
    unstack = Action("unstack", [
        Feature(("on", "X", "Y"), True, "pre"),
        Feature(("clear", "X"), True, "pre"),
        Feature(("handempty",), True, "pre"),
        Feature(("on", "X", "Y"), True, "del"),
        Feature(("clear", "X"), True, "del"),
        Feature(("handempty",), True, "del"),
        Feature(("holding", "X"), True, "add"),
        Feature(("clear", "Y"), True, "add")
    ])
    print(unstack.to_pddl())

    for a_inst in unstack.all_instantiations(state):
        print(a_inst.to_pddl())
    
if __name__ == "__main__":
    main()
