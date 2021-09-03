from state import State
from action import Action


def main():
    state = State(set(
        ("on", "a", "b"), ("on", "b", "c"), ("ontable", "c"), ("clear", "a"),
        ("ontable", "d"), ("clear", "d"), ("on", "e", "f"), ("ontable", "f"),
        ("clear", "e"), ("handempty",)
    ))
    unstack = Action("unstack", )
    pass
    
if __name__ == "__main__":
    main()
