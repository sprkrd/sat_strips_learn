from itertools import islice


ATOM_TYPES = ["pre", "add", "del"]


class Object:
    def __init__(self, name, objtype="object"):
        self._data = (name.lower(), objtype)

    @property
    def name(self):
        return self._data[0]

    @property
    def objtype(self):
        return self._data[1]

    def replace(self, sigma):
        return sigma.get(self, self)

    def is_variable(self):
        return self.name[0] == "?"

    def to_str(self, fmt="pddl", include_type=False):
        ret = self.name
        if fmt == "prolog" and self.is_variable():
            ret = ret[1:].title()
        if include_type:
            ret += ": " if fmt == "prolog" else " - "
            ret += self.objtype
        return ret

    def __eq__(self, other):
        return self._data == other._data

    def __hash__(self):
        return hash(self._data)

    def __str__(self):
        return self.to_str(fmt="pddl", include_type=True)

    def __repr__(self):
        return f"Object({self})"


class Atom:
    def __init__(self, head, *args):
        self._data = (head, *args)

    @property
    def head(self):
        return self._data[0]

    @property
    def args(self):
        return self._data[1:]

    def arity(self):
        return len(self._data) - 1

    def replace(self, sigma):
        replaced_args = (arg.replace(sigma) for arg in self.args)
        return Atom(self.head, *replaced_args)

    def to_str(self, fmt="pddl", include_type=False):
        args_str = (arg.to_str(fmt, include_type) for arg in self.args)
        if fmt == "prolog":
            ret = self.head + "(" + ",".join(args_str) + ")"
        else:
            ret = "(" + " ".join((self.head,) + args_str) + ")"
        return ret

    def __eq__(self, other):
        return self._data == other._data

    def __hash__(self):
        return hash(self._data)

    def __str__(self):
        return self.to_str(fmt="pddl", include_type=True)

    def __repr__(self):
        return f"Atom({self})"


# class LabeledAtom:
    # def __init__(self, atom, certain=True, atom_type="pre"):
        # assert atom_type in ATOM_TYPES
        # self.atom = atom
        # self.certain = certain
        # self.atom_type = atom_typei




class Predicate:
    def __init__(self, head, *args, parent_domain=None):
        if len(args) == 1 and isinstance(args[0], int):
            arity, = args
            args = ("object",) * arity
        self.head = head
        self.args = args
        self.parent_domain = parent_domain

    def arity(self):
        return len(self.args)

    def to_str(self, fmt="pddl", include_type=False):
        atom = self(Object(f"?x{i}",objtype) for i,objtype in self.args)
        return atom.to_str(fmt, include_type)

    def __str__(self):
        return self.to_str(fmt="pddl", include_type=True)

    def __call__(self, *args):
        dom = self.parent_domain
        assert len(args) == self.arity()
        assert all(dom.is_subtype(obj.objtype, objtype)
                for obj, objtype in zip(args,self.args))
        return Atom(self.head, *args)


# class Action:
    
    # @staticmethod
    # def from_features(self, name, features):
        # parameters = set()
        # precondition = []
        # add_list = []
        # delete_list = []
        # for feat in features:
            # for arg in 

    # def __init__(self, name, parameters, precondition, add_list, delete_list):
        # self.name = name
        # self.parameters = parameters
        # self.precondition = precondition
        # self.add_list = add_list
        # self.delete_list = delete_list

    # def get_features(self):
        # pass



# class Domain:

    # def __init__(self, name, predicates=None, type_hierarchy=None, actions=None):
        # self.name = name
        # self.predicates = predicates or []
        # self.type_hierarchy = type_hierarchy
        # if self.type_hierarchy is not None:
            # self.type_hierarchy["object"] = None
        # self.actions = actions or []

    # def is_subtype(self, objtype1, objtype2):
        # while objtype1 and objtype1 != objtype2:
            # objtype1 = self.type_hierarchy[objtype1]
        # return objtype1 == objtype2

    # def is_supertype(self, objtype1, objtype2):
        # return self.is_subtype(objtype2, objtype1)

    # def dump(self, out):
        # out.write(f"(define (domain {self.name})\n\n")

        # out.write("(:requirements :strips)\n\n")

        # out.write("(:predicates\n")
        # for predicate_symbol, arity in self.get_all_predicate_signatures():
            # generic_predicate = (predicate_symbol,) + tuple(f"X{i}" for i in range(arity))
            # out.write(atom_to_pddl(generic_predicate))
            # out.write("\n")
        # out.write(")")

        # for action in self.action_library.values():
            # out.write("\n\n")
            # out.write(action.to_pddl())
        # out.write(f"\n)")


