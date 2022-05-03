from io import StringIO
from itertools import chain 


class Object:
    def __init__(self, name, objtype="object"):
        objtype = objtype
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

    def to_str(self, fmt="default", include_type=False):
        ret = self.name
        if fmt == "default":
            if self.is_variable():
                ret = ret[1:].title()
            if include_type:
                ret += ": " + self.objtype
        elif fmt == "pddl":
            if include_type:
                ret += " - " + self.objtype
        else:
            raise ValueError(f"Unknown format: {fmt}")
        return ret

    def __eq__(self, other):
        return self._data == other._data

    def __hash__(self):
        return hash(self._data)

    def __str__(self):
        return self.to_str(fmt="default", include_type=True)

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
        
    def get_signature(self):
        return f"{self.head}/{self.arity()}"

    def arity(self):
        return len(self._data) - 1

    def replace(self, sigma):
        replaced_args = (arg.replace(sigma) for arg in self.args)
        return Atom(self.head, *replaced_args)
        
    def is_lifted(self):
        return any(arg.is_variable() for arg in self.args)

    def to_str(self, fmt="default", include_types=False):
        args_str = [arg.to_str(fmt, include_types) for arg in self.args]
        if fmt == "default":
            ret = self.head + "(" + ", ".join(args_str) + ")"
        elif fmt == "pddl":
            ret = "(" + " ".join([self.head] + args_str) + ")"
        else:
            raise ValueError(f"Unknown format: {fmt}")
        return ret

    def __eq__(self, other):
        return self._data == other._data

    def __hash__(self):
        return hash(self._data)

    def __str__(self):
        return self.to_str(fmt="default", include_types=True)

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


def _match_unify(refatom, atom, sigma):
    """
    Finds, if possible, a substitution from variables to constants,
    making a atom equal to a reference atom.

    Parameters
    ----------
    refatom : tuple
        A tuple of str that represents a compound atom (e.g. predicate
        or function). Every str after the first (which is interpreted
        as the head of the atom) must be a constant (i.e. is_lifted should
        return False on them).
    atom : tuple
        A tuple of str that should be matched with the reference atom.
        This atom may contain variables.
    sigma : dict
        A dictionary from variables to constants (both str). By default,
        it's None, meaning that no partial or total substitution should
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
    >>> match_unify(("on","a","b"), ("on", "X", "Y")) == {"X": "a", "Y": "b"}
    True
    >>> match_unify(("on","a","b"), ("on", "X", "X")) is None
    True
    >>> match_unify(("on","a","b"), ("on", "X", "Y"), {"Z": "c"}) == {"X": "a", "Y": "b", "Z": "c"}
    True
    >>> match_unify(("dummy",), ("dummy",)) == {}
    True
    >>> match_unify(("dummy",), ("ducky",)) is None
    True
    """
    if refatom.head != atom.head or refatom.arity() != atom.arity():
        return None
    sigma = sigma.copy()
    for ref_obj, obj in zip(refatom.args, atom.args):
        if obj.is_variable():
            sigma[obj] = ref_obj
        elif obj != ref_obj:
            return None
    return sigma


class ActionSchema:
    
    def __init__(self, name, parameters=None, precondition=None, add_list=None, del_list=None, domain=None):
        self.name = name
        self.parameters = parameters or []
        self.precondition = precondition or []
        self.add_list = add_list or []
        self.del_list = del_list or []
        self.domain = domain
        self._verify()
        
    def arity(self):
        return len(self.parameters)
        
    def _verify(self):
        for param in self.parameters:
            if not param.is_variable():
                raise ValueError(f"Parameter {param} is not a variable")
        for atom in chain(self.precondition, self.add_list, self.del_list):
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
        
    def to_str(self, fmt="default", typing=True):
        lines = []
        if fmt == "default":
            lines.append(self.name + " {")
            lines.append("    parameters: " + ", ".join(param.to_str(fmt="default", include_type=typing) for param in self.parameters) + ";")
            for group in ("precondition", "add_list", "del_list"):
                atoms = ", ".join(atom.to_str(fmt="default",include_types=False) for atom in getattr(self, group))
                lines.append(f"    {group}: {atoms};")
            lines.append("}")
        elif fmt == "pddl":
            lines.append("(:action " + self.name)
            if self.parameters:
                params = " ".join(param.to_str(fmt="pddl",include_type=typing) for param in self.parameters)
                lines.append(f" :parameters ({params})")
            if self.precondition:
                precondition = " ".join(["and"] + [atom.to_str(fmt="pddl",include_types=False) for atom in self.precondition])
                lines.append(f" :precondition ({precondition})")
            if self.add_list or self.del_list:
                effect = ["and"]
                for atom in self.add_list:
                    effect.append(atom.to_str(fmt="pddl", include_types=False))
                for atom in self.del_list:
                    effect.append(f"(not {atom.to_str(fmt='pddl', include_types=False)})")
                effect = " ".join(effect)
                lines.append(f" :effect ({effect})")
            lines.append(")")
        return "\n".join(lines)
        
    def __str__(self):
        return self.to_str(fmt="default", typing=True)


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
            out.write(obj.to_str(fmt="pddl", include_type=True))
            out.write("\n")
        out.write(")\n")
        out.write("(:init\n")
        for atom in self.init:
            out.write(atom.to_str(fmt="pddl", include_type=False))
            out.write("\n")
        out.write(")\n")
        out.write("(:goal (and\n")
        for atom in goal:
            out.write(atom.to_str(fmt="pddl", include_type=False))
            out.write("\n")
        out.write("))\n)\n")
        
    def __str__(self):
        with StringIO() as out:
            self.dump_pddl(out)
            ret = out.getvalue()
        return ret

