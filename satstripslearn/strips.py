from io import StringIO
from itertools import chain


class ObjType:
    """An object type, as those used in PDDL to narrow down the sets of objects
    that can be used for predicate or action's arguments. This class allows
    to establush hierarchies of types.

    Parameters
    ----------
    name : str
        Name identifying the object.

    parent : ObjType
        Parent type, can be None.

    Attributes
    ----------
    name : str
        Same as input given parameter

    parent : ObjType
        Same as input given parameter
    """

    def __init__(self, name, parent=None):
        """
        See help(type(self)).
        """
        self.name = name
        self.parent = parent

    def get_path_from_root(self):
        path = []
        current = self
        while current is not None:
            path.append(current)
            current = current.parent
        path.reverse()
        return path

    def lca(self, other):
        path_to_self = self.get_path_from_root()
        path_to_other = other.get_path_from_root()
        lca = None
        for n1,n2 in zip(path_to_self, path_to_other):
            if n1 != n2:
                break
            lca = n1
        return lca

    def is_subtype(self, other):
        current = self
        while current is not None and current is not other:
            current = current.parent
        return current is other

    def is_supertype(self, other):
        return other.is_subtype(self)

    def to_pddl(self):
        return self.name + " - " + self.parent.name if self.parent else self.name

    def __str__(self):
        return self.to_pddl()

    def __repr__(self):
        return f"ObjType({self})"

    def __call__(self, arg):
        """
        Allows to use the ObjType in a functional way to create new objects of
        a given type.
        """
        return Object(arg, self)


ROOT_TYPE = ObjType("object")


class Object:
    """
    Represents a STRIPS object.

    Parameters
    ----------
    name : str
        Name identifying the object. If the name starts with a question mark
        ("?"), the object is a variable.
    objtype : str
        Type of this object. By default, it's "object" (the root type).

    Attributes
    ----------
    name : str
        Same as the value passed as parameter.
    objtype : str
        Same as the value passed as parameter.
    """

    def __init__(self, name, objtype=ROOT_TYPE):
        """
        See help(type(self)).
        """
        self._data = (name.lower(), objtype)

    @property
    def name(self):
        """
        Convenience method to extract the name from the internal data

        Return
        ------
        name : str
        """
        return self._data[0]

    @property
    def objtype(self):
        """
        Convenience method to extract the object type from the internal data

        Return
        ------
        obtype : str
        """
        return self._data[1]

    def is_compatible(self, other):
        return self.objtype.is_subtype(other.objtype)

    def replace(self, sigma):
        """
        Given a substitution, returns either the same object if it is not
        present as a key in the substitution, or the substituting object
        if it is.

        Parameters
        ----------
        sigma : dict
            A Object -> Object dictionary representing a substitution.
            This object (self) may or may not be present in this substitution
            as a key.

        Return
        ------
        obj : Object
            Either self, if self is not present in sigma, or sigma[self]

        Examples
        --------
        >>> _x, _y, a = Object("?x"), Object("?y"), Object("a")
        >>> _x.replace({_x: a})
        Object(a - object)
        >>> _x.replace({_y: a})
        Object(?x - object)
        """
        return sigma.get(self, self)

    def is_variable(self):
        """
        Returns True if this object is a variable, False if it's a constant.

        Return
        ------
        out : bool
        """
        return self.name[0] == "?"

    def to_pddl(self, include_type=True):
        """
        PDDL string representation of the object.

        Parameters
        ----------
        include_type: bool
            Whether to include the type of the object in the sting representation or not.
            In the PDDL format, the type is included as a dash followed by the type name.
            In the default format, the type is included after a colon.

        Return
        ------
        out : str

        Examples
        --------
        >>> blue = Object("blue", "color")
        >>> print(blue.to_pddl(include_type=True))
        blue - color
        >>> print(blue.to_pddl(include_type=False))
        blue
        """
        ret = self.name
        if include_type and self.objtype is not None:
            ret += " - " + self.objtype.name
        return ret

    def __eq__(self, other):
        return self._data == other._data

    def __hash__(self):
        return hash(self._data)

    def __str__(self):
        return self.to_pddl()

    def __repr__(self):
        return f"Object({self})"


def _typed_objlist_to_pddl(objlist, break_lines=False):
    lines = []
    current_line = []
    last_type = None
    for obj in objlist:
        if last_type is not None and last_type is not obj.objtype:
            current_line.append("-")
            current_line.append(last_type.name)
            lines.append(" ".join(current_line))
            current_line = []
        current_line.append(obj.name)
        last_type = obj.objtype
    if current_line:
        current_line.append("-")
        current_line.append(last_type.name)
        lines.append(" ".join(current_line))
    sep = "\n" if break_lines else " "
    return sep.join(lines)


def _untyped_objlist_to_pddl(objlist):
    return " ".join(obj.name for obj in objlist)


def _typelist_to_pddl(typelist, break_lines=False):
    lines = []
    current_line = []
    last_parent = None
    for type_ in typelist:
        if last_parent is not None and last_parent is not type_.parent:
            current_line.append("-")
            current_line.append(last_parent.name)
            lines.append(" ".join(current_line))
            current_line = []
        current_line.append(type_.name)
        last_parent = type_.parent
    if current_line:
        current_line.append("-")
        current_line.append(last_parent.name)
        lines.append(" ".join(current_line))
    sep = "\n" if break_lines else " "
    return sep.join(lines)


class Predicate:
    def __init__(self, head, *args):
        if 1 <= len(args) <= 2 and isinstance(args[0],int):
            t = args[1] if len(args) == 2 else ROOT_TYPE
            arity = args[0]
            args = (t,)*arity
        self.head = head
        self.argtypes = args

    def has_generated(self, atom):
        return atom.head == self.head and atom.arity() == self.arity() and\
               all(a1.objtype.is_subtype(a2)
                   for a1,a2 in zip(atom.args,self.argtypes))

    def arity(self):
        return len(self.argtypes)

    def __call__(self, *args):
        if len(args) != len(self.argtypes):
            raise ValueError("Invalid number of arguments")
        if not all(o.objtype.is_subtype(t) for o,t in zip(args,self.argtypes)):
            raise ValueError("Cannot instantiate atom: invalid signature")
        return Atom(self.head, *args)

    def to_pddl(self, include_types=True):
        dummy_objects = [t(f"?x{i}") for i,t in enumerate(self.argtypes)]
        atom = Atom(self.head, *dummy_objects)
        return atom.to_pddl(include_types=True)

    def __str__(self):
        return self.to_pddl()

    def __repr__(self):
        return f"Predicate({self})"


class Atom:
    """
    A predicate variable consisting of a head and a list of arguments.

    Parameters
    ----------
    head : str
        Predicate name
    *args : [str...]
        List of arguments of this atom
    """

    def __init__(self, head, *args):
        self._data = (head, *args)

    @property
    def head(self):
        return self._data[0]

    @property
    def args(self):
        return self._data[1:]

    def get_signature(self):
        return (self.head, self.arity())

    def arity(self):
        return len(self._data) - 1

    def replace(self, sigma):
        replaced_args = (arg.replace(sigma) for arg in self.args)
        return Atom(self.head, *replaced_args)

    def is_lifted(self):
        return any(arg.is_variable() for arg in self.args)

    def to_pddl(self, include_types=True):
        args = self.args
        if args:
            args_str = _typed_objlist_to_pddl(args) if include_types\
                    else _untyped_objlist_to_pddl(args)
            return "(" + self.head + " " + args_str + ")"
        return "(" + self.head + ")"

    def __eq__(self, other):
        return self._data == other._data

    def __hash__(self):
        return hash(self._data)

    def __str__(self):
        return self.to_pddl(include_types=True)

    def __repr__(self):
        return f"Atom({self})"


def _match_unify(refatom, atom, sigma=None):
    """
    Finds, if possible, a substitution from variables to constants,
    making a atom equal to a reference atom.

    Parameters
    ----------
    refatom : Atom
        Reference atom (i.e. predicate variable). It must be grounded.
    atom : Atom
        An atom (possibly with lifted variables). Free variables must
        not be present in sigma.
    sigma : dict or None
        An Object->Object dictionary, from variables to constants.
        By default, it's None, meaning that no partial or total substitution should
        be considered by this function.

    Return
    ------
    out : dict
        A dictionary that represents a substitution from variables to
        constants s.t. refatom equals atom. If matching is not possible,
        None is returned instead. If sigma, in the parameters, was set
        to anything different from None, all the substitutions not forced
        by the matching process are retained.

    Examples
    --------
    >>> a = Object("a")
    >>> b = Object("b")
    >>> c = Object("c")
    >>> _x = Object("?x")
    >>> _y = Object("?y")
    >>> _z = Object("?z")
    >>> _match_unify(Atom("on", a, b), Atom("on", _x, _y)) == {_x: a, _y: b}
    True
    >>> _match_unify(Atom("on", a, b), Atom("on", _x, _x)) is None
    True
    >>> _match_unify(Atom("on", a, b), Atom("on", _x, _y), {_z: c}) == {_x: a, _y: b, _z: c}
    True
    >>> _match_unify(Atom("dummy"), Atom("dummy")) == {}
    True
    >>> _match_unify(Atom("dummy"), Atom("ducky")) is None
    True
    """
    if refatom.head != atom.head or refatom.arity() != atom.arity():
        return None
    sigma = sigma.copy() if sigma is not None else {}
    for ref_obj, obj in zip(refatom.args, atom.args):
        obj = sigma.get(obj, obj)
        if obj.is_variable():
            sigma[obj] = ref_obj
        elif obj != ref_obj:
            return None
    return sigma


class Action:

    def __init__(self, name, parameters=None, precondition=None, add_list=None, del_list=None):
        self.name = name
        self.parameters = parameters or []
        self.precondition = precondition or []
        self.add_list = add_list or []
        self.del_list = del_list or []
        self._verify()

    def _verify(self):
        for param in self.parameters:
            if not param.is_variable():
                raise ValueError(f"Parameter {param} is not a variable")
        for atom in chain(self.precondition, self.add_list, self.del_list):
            for arg in atom.args:
                if arg.is_variable() and arg not in self.parameters:
                    raise ValueError(f"Free variable {arg} is not present in the list of parameters")

    def get_signature(self):
        return (self.name,) + tuple(param.objtype for param in self.parameters)

    def arity(self):
        return len(self.parameters)

    # def _all_groundings_aux1(self, state):
    #     pre = self.precondition
    #     stack = [(0,{})]
    #     while stack:
    #         idx, sigma = stack.pop()
    #         if idx == len(pre):
    #             yield sigma
    #             continue
    #         atom = pre[idx].replace(sigma)
    #         if atom.is_lifted():
    #             for refatom in state:
    #                 sigma_new = _match_unify(refatom, atom, sigma)
    #                 if sigma_new is not None:
    #                     stack.append((idx+1,sigma_new))
    #         elif atom in state:
    #             stack.append((idx+1, sigma))

    def _variables_in_preconditions(self):
        variables = set()
        for atom in self.precondition:
            variables.update(arg for arg in atom.args if arg.is_variable())
        return variables

    def _all_groundings_aux1(self, state):
        grouped_state = {}
        for atom in state:
            grouped_state.setdefault(atom.head, []).append(atom)
        pre = self.precondition
        stack = [(0,{})]
        while stack:
            idx, sigma = stack.pop()
            if idx == len(pre):
                yield sigma
                continue
            atom = pre[idx].replace(sigma)
            if atom.is_lifted():
                for refatom in grouped_state.get(atom.head, []):
                    sigma_new = _match_unify(refatom, atom, sigma)
                    if sigma_new is not None:
                        stack.append((idx+1,sigma_new))
            elif atom in state:
                stack.append((idx+1, sigma))

    def _all_groundings_aux2(self, objects, sigma0):
        stack = [(0,sigma0)]
        while stack:
            param_idx, sigma = stack.pop()
            if param_idx == self.arity():
                yield self.ground(*(sigma[param] for param in self.parameters))
            else:
                param = self.parameters[param_idx]
                if param in sigma:
                    stack.append((param_idx+1,sigma))
                else:
                    for obj in objects:
                        if obj.is_compatible(param):
                            sigma_new = sigma.copy()
                            sigma_new[param] = obj
                            stack.append((param_idx+1,sigma_new))

    def all_groundings(self, objects, state):
        if len(self._variables_in_preconditions()) == len(self.parameters):
            print("Case #1")
            for sigma in self._all_groundings_aux1(state):
                yield self.ground(*(sigma[param] for param in self.parameters))
        else:
            print("Case #2")
            for sigma in self._all_groundings_aux1(state):
                yield from self._all_groundings_aux2(objects, sigma)

    def ground(self, *parameters):
        if len(parameters) != self.arity():
            raise ValueError("Invalid number of parameters")
        if any(param.is_variable() for param in parameters):
            raise ValueError("Parameters cannot be free variables")
        if not all(p1.is_compatible(p2) for p1,p2 in zip(parameters,self.parameters)):
            raise ValueError("Type mismatch")
        return GroundedAction(self, parameters)

    def to_pddl(self, typing=True):
        lines = []
        lines.append("(:action " + self.name)
        if self.parameters:
            params = _typed_objlist_to_pddl(self.parameters) if typing\
                    else _untyped_objlist_to_pddl(self.parameters)
            lines.append(f" :parameters ({params})")
        if self.precondition:
            precondition = " ".join(["and"] + [atom.to_pddl(include_types=False)
                for atom in self.precondition])
            lines.append(f" :precondition ({precondition})")
        if self.add_list or self.del_list:
            effect = ["and"]
            for atom in self.add_list:
                effect.append(atom.to_pddl(include_types=False))
            for atom in self.del_list:
                effect.append(f"(not {atom.to_pddl(include_types=False)})")
            effect = " ".join(effect)
            lines.append(f" :effect ({effect})")
        lines.append(")")
        return "\n".join(lines)

    def __str__(self):
        return self.to_pddl(typing=True)


class GroundedAction:

    def __init__(self, schema, parameters):
        self.schema = schema
        self.parameters = parameters
        self.sigma = dict(zip(schema.parameters, parameters))

    def is_applicable(self, state):
        precondition = self.schema.precondition
        return all(atom.replace(self.sigma) in state for atom in precondition)

    def apply(self, state):
        next_state = None
        if self.is_applicable(state):
            next_state = state.copy()
            for atom in self.schema.add_list:
                next_state.add(atom.replace(self.sigma))
            for atom in self.schema.del_list:
                next_state.discard(atom.replace(self.sigma))
        return next_state

    def __str__(self):
        return self.schema.name + "(" + ",".join(obj.name for obj in self.parameters) + ")"

    def __repr__(self):
        return f"GroundedAction({self})"


class Domain:

    def __init__(self, name, predicates=None, types=None, actions=None):
        self.name = name
        self.predicates = predicates or []
        self.types = types or []
        self.actions = actions or []

    def declare_type(self, type_name, parent=None):
        parent = parent or ROOT_TYPE
        if type_name == ROOT_TYPE.name or any(type_name == type_.name for type_ in self.types):
            raise ValueError(f"Type with name {type_name} already declared")
        if parent is not ROOT_TYPE and parent not in self.types:
            raise ValueError(f"Parent type {parent} not declared")
        type_ = ObjType(type_name, parent)
        self.types.append(type_)
        return type_

    def declare_predicate(self, head, *parameter_types):
        if any(head == pred.head  for pred in self.predicates):
            raise ValueError(f"Predicate with name {head} already declared")
        if not all(type_ == ROOT_TYPE or type_ in self.types for type_ in parameter_types):
            raise ValueError("Type has not been declared")
        predicate = Predicate(head, *parameter_types)
        self.predicates.append(predicate)
        return predicate

    def declare_action(self, name, params, pre, add_list, del_list):
        action = Action(name, params, pre, add_list, del_list)
        self.add_action(action)
        return action

    def add_action(self, action):
        self._verify_action(action)
        self.actions.append(action)

    def _verify_action(self, action):
        if any(action.name == other.name for other in self.actions):
            raise ValueError(f"Action with name {action.name} already exists")
        for atom in chain(action.precondition, action.add_list, action.del_list):
            if not any(pred.has_generated(atom) for pred in self.predicates):
                raise ValueError(f"Non-existent predicate signature for {atom}")

    def dump_pddl(self, out):
        typing = bool(self.types)

        out.write(f"(define (domain {self.name})\n\n")

        if typing:
            out.write("(:requirements :strips :typing)\n\n")
        else:
            out.write("(:requirements :strips)\n\n")

        if typing:
            out.write("(:types\n")
            out.write(_typelist_to_pddl(self.types, break_lines=True))
            out.write("\n)\n\n")

        out.write("(:predicates\n")
        for predicate in self.predicates:
            out.write(predicate.to_pddl(typing) + "\n")
        out.write(")\n\n")

        for action in self.actions:
            out.write(action.to_pddl(typing) + "\n\n")

        out.write(")\n")

    def to_pddl(self):
        with StringIO() as out:
            self.dump_pddl(out)
            ret = out.getvalue()
        return ret

    def __str__(self):
        return self.to_pddl()


class Problem:
    def __init__(self, name, domain=None, objects=None, init=None, goal=None):
        self.name = name
        self.domain = domain
        self.objects = objects or set()
        self.init = init or []
        self.goal = goal or []

    def add_object(self, obj):
        if obj.is_variable():
            raise ValueError("Cannot add variable to object list")
        self.objects.append(obj)

    def _check_atom(self, atom):
        if atom.is_lifted():
            raise ValueError("Cannot add atoms with free variables to init section")
        if not all(arg in self.objects for arg in atom.args):
            raise ValueError("All the objects must be in the object list")

    def add_init_atom(self, atom):
        self._check_atom(atom)
        self.init.append(atom)

    def add_goal_atom(self, atom):
        self._check_atom(atom)
        self.goal.append(atom)

    def dump_pddl(self, out):
        typing = self.domain.types is not None
        out.write(f"(define (problem {self.name}) (:domain {self.domain.name})\n\n")
        out.write("(:objects\n")
        objects = sorted(self.objects, key=lambda o: (o.objtype.name, o.name))
        if typing:
            out.write(_typed_objlist_to_pddl(objects, break_lines=True))
        else:
            out.write(_untyped_objlist_to_pddl(objects))
        out.write("\n)\n\n")
        out.write("(:init\n")
        for atom in self.init:
            out.write(atom.to_pddl(include_types=False))
            out.write("\n")
        out.write(")\n\n")
        out.write("(:goal (and\n")
        for atom in self.goal:
            out.write(atom.to_pddl(include_types=False))
            out.write("\n")
        out.write("))\n)\n")

    def to_pddl(self):
        with StringIO() as out:
            self.dump_pddl(out)
            ret = out.getvalue()
        return ret

    def __str__(self):
        return self.to_pddl()


if __name__ == "__main__":
    import doctest
    doctest.testmod()
