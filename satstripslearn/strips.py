from io import StringIO
from itertools import chain 


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
    
    def __init__(self, name, objtype="object"):
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
        Object(a: object)
        >>> _x.replace({_y: a})
        Object(X: object)
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
        
    def to_pddl(self, include_type=False):
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
        >>> print(blue.to_str(include_type=True))
        blue - color
        >>> print(blue.to_str(include_type=False))
        blue
        """
        ret = self.name
        if include_type:
            ret += " - " + self.objtype
        return ret

    def __eq__(self, other):
        return self._data == other._data

    def __hash__(self):
        return hash(self._data)

    def __str__(self):
        return self.to_pddl(include_type=True)

    def __repr__(self):
        return f"Object({self})"
        
        
def _typed_objlist_to_pddl(objlist, break_lines=False):
    lines = []
    current_line = []
    last_type = None
    for obj in objlist:
        if last_type is not None and last_type != obj.objtype:
            current_line.append("-")
            current_line.append(last_type)
            lines.append(" ".join(current_line))
            current_line = []
        current_line.append(obj.name)
        last_type = obj.objtype
    if current_line:
        current_line.append("-")
        current_line.append(last_type)
        lines.append(" ".join(current_line)
    sep = "\n" if break_lines else " "
    return sep.join(lines)
        

class Atom:
    def __init__(self, head, *args):
        self._data = (head, *args)

    @property
    def head(self):
        return self._data[0]

    @property
    def args(self):
        return self._data[1:]
        
    def get_signature(self):
        return (self.head,) + tuple(arg.objtype for arg in self.args)

    def arity(self):
        return len(self._data) - 1

    def replace(self, sigma):
        replaced_args = (arg.replace(sigma) for arg in self.args)
        return Atom(self.head, *replaced_args)
        
    def is_lifted(self):
        return any(arg.is_variable() for arg in self.args)
        
    def to_pddl(self, include_types=False):
        args_str = [arg.to_pddl(include_types) for arg in self.args]
        return "(" + " ".join([self.head] + args_str) + ")"

    def __eq__(self, other):
        return self._data == other._data

    def __hash__(self):
        return hash(self._data)

    def __str__(self):
        return self.to_str(include_types=True)

    def __repr__(self):
        return f"Atom({self})"
        

class GroundedAction:
    
    def __init__(self, schema, parameters):
        self.schema = schema
        self.parameters = parameters
        self._sigma = dict(zip(schema.parameters, parameters))
        
    def is_applicable(self, state):
        sigma = self._sigma
        precondition = self.schema.precondition
        return all(atom.replace(sigma) in state for atom in precondition)
        
    def apply(self, state):
        next_state = None
        if self.is_applicable(state):
            next_state = state.copy()
            for atom in self.schema.add_list:
                next_state.add(atom.replace(self._sigma))
            for atom in self.schema.del_list:
                next_state.discard(atom.replace(self._sigma))
        return next_state
    
    def __str__(self):
        return self.schema.name + "(" + ",".join(obj.name for obj in self.parameters) + ")"
        
    def __repr__(self):
        return f"GroundedAction({self})"


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


class ActionSchema:
    
    def __init__(self, name, parameters=None, precondition=None, add_list=None, del_list=None, domain=None, verify=False):
        self.name = name
        self.parameters = parameters or []
        self.precondition = precondition or []
        self.add_list = add_list or []
        self.del_list = del_list or []
        self.domain = domain
        if domain and verify:
            self._verify()
        
    def get_signature(self):
        return (self.name,) + tuple(param.objtype for param in self.parameters)
        
    def arity(self):
        return len(self.parameters)
        
    def _verify(self):
        for param in self.parameters:
            if not param.is_variable():
                raise ValueError(f"Parameter {param} is not a variable")
        for atom in chain(self.precondition, self.add_list, self.del_list):
            atom_signature = atom.get_signature()
            if not any(atom_signature == pred.get_signature() for pred in self.)
            for arg in atom.args:
                if arg.is_variable() and arg not in self.parameters:
                    raise ValueError(f"Free variable {arg} is not present in the list of parameters")
                    
    def _all_groundings_aux1(self, state):
        pre = self.precondition
        stack = [(0,{})]
        while stack:
            idx, sigma = stack.pop()
            if idx == len(pre):
                yield sigma
                continue
            atom = pre[idx].replace(sigma)
            if atom.is_lifted():
                for refatom in state:
                    sigma_new = _match_unify(refatom, atom, sigma)
                    if sigma_new is not None:
                        stack.append((idx+1,sigma_new))
            elif atom in state:
                stack.append((idx+1, sigma))
                
    def _all_groundings_aux2(self, objects, sigma0):
        dom = self.domain
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
                        if dom.is_subtype(obj.objtype, param.objtype):
                            sigma_new = sigma.copy()
                            sigma_new[param] = obj
                            stack.append((param_idx+1,sigma_new))
                    
    def all_groundings(self, objects, state):
        if self._domain is None:
            raise ValueError("A domain must be specified first")
        for sigma in self._all_groundings_aux1(state):
            yield from self._all_groundings_aux2(objects, sigma)
        
    def ground(self, *parameters):
        dom = self.domain
        if len(parameters) != self.arity():
            raise ValueError("Invalid number of parameters")
        if any(param.is_variable() for param in parameters):
            raise ValueError("Parameters cannot be free variables")
        if not all(dom.is_subtype(p1.objtype,p2.objtype) for p1,p2 in zip(parameters,self.parameters)):
            raise ValueError("Type mismatch")
        return GroundedAction(self, parameters)
        
    def to_pddl(self, typing=True):
        lines = []
        lines.append("(:action " + self.name)
        if self.parameters:
            params = " ".join(param.to_str(include_type=typing) for param in self.parameters)
            lines.append(f" :parameters ({params})")
        if self.precondition:
            precondition = " ".join(["and"] + [atom.to_str(include_types=False) for atom in self.precondition])
            lines.append(f" :precondition ({precondition})")
        if self.add_list or self.del_list:
            effect = ["and"]
            for atom in self.add_list:
                effect.append(atom.to_str(include_types=False))
            for atom in self.del_list:
                effect.append(f"(not {atom.to_str(include_types=False)})")
            effect = " ".join(effect)
            lines.append(f" :effect ({effect})")
        lines.append(")")
        return "\n".join(lines)
        
    def __str__(self):
        return self.to_str(typing=True)


class _ObjectFactory:
    def __init__(self, typename):
        self.typename = typename
    
    def __call__(self, objname):
        return Object(objname, self.typename)
        

class _AtomFactory:
    def __init__(self, atom_template, domain=None):
        self.atom_template = atom_template
        self._domain = domain
        
    def __call__(self, *args):
        if len(args) != self.atom_template.arity():
            raise ValueError("Wrong number of arguments")
        dom = self._domain
        if dom and not all(dom.is_subtype(arg1.objtype,arg2.objtype) for arg1,arg2 in zip(args, self.atom_template.args)):
            raise ValueError("Type mismatch")
        return Atom(self.atom_template.head, *args)


def _toposort(hierarchy):
    remaining_nodes = set(hierarchy)
    sorted_nodes = []
    while remaining_nodes:
        temporary_mark = set()
        node = next(iter(remaining_nodes))
        tail = []
        while node in remaining_nodes:
            if node in temporary_mark:
                raise ValueError("Not a DAG")
            temporary_mark.add(node)
            tail.append(node)
            remaining_nodes.remove(node)
            node = hierarchy[node]
        sorted_nodes += reversed(tail)
    return sorted_nodes


class Domain:

    def __init__(self, name, predicates=None, types=None, actions=None):
        self.name = name
        self.predicates = predicates or []
        self.types = types
        self.actions = actions or []
        
    def declare_type(self, typename, parent="object"):
        if self.types is None:
            self.types = {}
        if callable(parent):
            parent = parent.typename
        if parent != "object" and parent not in self.types:
            raise ValueError(f"Type {parent} not declared")
        self.types[typename] = parent
        return _ObjectFactory(typename)
        
    def declare_predicate(self, head, *args):
        if not all(a.is_variable() for a in args):
            raise ValueError("All the arguments must be variables")
        atom = Atom(head, *args)
        self.predicates.append(atom)
        return _AtomFactory(atom, self)
        
    def declare_action(self, name, params, pre, add_list, del_list):
        action = ActionSchema(name, params, pre, add_list, del_list, self)
        self.actions.append(action)
        return action
        
    def is_subtype(self, typename1, typename2):
        types = self.types
        if types is None:
            raise ValueError("Domain is not typed")
        current = typename1
        while typename1 is not None and typename1 != typename2:
            typename1 = self.types.get(typename1)
        return typename1 is not None and typename1 == typename2
        
    
    def dump_pddl(self, out):
        typing = self.types is not None
        
        out.write(f"(define (domain {self.name})\n\n")
        
        if self.types is not None:
            out.write("(:requirements :strips)\n\n")
        else:
            out.write("(:requirements :strips :typing)\n\n")
            
        if typing:
            sorted_types = _toposort(self.types)
            out.write("(:types\n")
            for t in sorted_types:
                parent = self.types[t]
                out.write(f"{t} - {parent}\n")
            out.write(")\n\n")
            
        out.write("(:predicates\n")
        for predicate in self.predicates:
            out.write(predicate.to_str("pddl", typing) + "\n")
        out.write(")\n\n")
        
        for action in self.actions:
            out.write(action.to_str("pddl", typing) + "\n\n")
            
        out.write(")\n")
        
    def __str__(self):
        with StringIO() as out:
            self.dump_pddl(out)
            ret = out.getvalue()
        return ret
        
        
class Problem:
    def __init__(self, name, domain, objects=None, init=None, goal=None):
        self.name = name
        self.domain = domain
        self.objects = objects or set()
        self.init = init or []
        self.goal = goal or []
        
    def add_object(self, obj):
        if obj.is_variable():
            raise ValueError("Cannot add variable to object list")
        self.objects.add(obj)
        
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
        out.write(f"(define (problem {self.name}) (:domain {self.domain.name})\n")
        out.write("(:objects\n")
        for obj in self.objects:
            out.write(obj.to_str(include_type=True))
            out.write("\n")
        out.write(")\n")
        out.write("(:init\n")
        for atom in self.init:
            out.write(atom.to_str(include_type=False))
            out.write("\n")
        out.write(")\n")
        out.write("(:goal (and\n")
        for atom in goal:
            out.write(atom.to_str(include_type=False))
            out.write("\n")
        out.write("))\n)\n")
        
    def __str__(self):
        with StringIO() as out:
            self.dump_pddl(out)
            ret = out.getvalue()
        return ret


if __name__ == "__main__":
    import doctest
    doctest.testmod()
