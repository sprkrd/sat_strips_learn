from threading import Lock
from time import process_time, time

class SequentialIdGenerator:
    def __init__(self, prefix="", state=0):
        self._count = state
        self._prefix = prefix
        self._mtx = Lock()

    def get_state(self):
        return self._count

    def __call__(self):
        with self._mtx:
            next_id = self._count
            self._count += 1
        return f"{self._prefix}{next_id}"


action_id_gen = SequentialIdGenerator("action-")
variable_id_gen = SequentialIdGenerator("X")
cluster_id_gen = SequentialIdGenerator("cluster-")


def get_memory_usage():
    """Parses /proc/self/status to extract relevant memory figures.

    Returns
    -------
    memuse : dict
        A dict from str (name of memory figure) to Int (size in KB)
    """
    memuse = {}
    with open("/proc/self/status") as status:
        # This is not very portable, only works in Unix-like systems (like Linux).
        for line in status:
            parts = line.split()
            if parts[0].startswith("Vm"):
                key = parts[0][2:-1].lower()
                memuse[key] = int(parts[1])
    return memuse


def try_parse_number(text):
    try:
        return float(text)
    except ValueError:
        pass
    return text


class Timer:
    def __init__(self):
        self.start = None
        self.tic()

    def tic(self):
        self.start = (process_time(), time())

    def toc(self):
        return (process_time()-self.start[0], time()-self.start[1])


def is_lifted(obj):
    return obj[0].isupper()


def prolog_to_pddl(obj):
    if is_lifted(obj):
        return f"?{obj.lower()}"
    return obj


def pddl_to_prolog(obj):
    if obj.startswith("?"):
        return obj[1:].capitalize()
    return obj


def atom_to_pddl(t):
    t_pddl = (t[0],) + tuple(map(prolog_to_pddl, t[1:]))
    return f"({' '.join(t_pddl)})"


def atom_to_str(t):
    return f"{t[0]}({','.join(t[1:])})"


def replace(t, sigma):
    return (t[0],*(sigma.get(a,a) for a in t[1:]))


def lift_atom(atom, ref_dict):
    """
    Substitutes every ground object in atom with a lifted object
    with unique id.
    """
    head,*tail = atom
    lifted_tail = []
    for arg in tail:
        if is_lifted(arg):
            lifted_tail.append(arg)
        else:
            if arg not in ref_dict:
                ref_dict[arg] = variable_id_gen()
            lifted_tail.append(ref_dict[arg])
    return (head,*lifted_tail)


def inverse_map(d):
    inv = {v:k for k,v in d.items()}
    return inv
    
    
def match_unify(refatom, atom, sigma=None):
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
    
    if sigma is None:
        sigma = {}
    if refatom[0] != atom[0] or len(refatom) != len(atom):
        return None
    for ref_obj, obj in zip(refatom[1:], atom[1:]):
        obj = sigma.get(obj, obj)
        if is_lifted(obj):
            sigma[obj] = ref_obj
        elif obj != ref_obj:
            return None
    return sigma
    
    
def goal_match(atoms, goal):
    """
    Tries to perform a Prolog-like query in which a goal pattern (a set
    of zero or more atoms) is matched against a database of atoms. 
    The objective of this function is to find all the substitutions from
    variables to constants s.t. the goal pattern is contained within the
    given set of atoms.
    
    Parameters
    ----------
    atoms : iterable
        A database of atoms. Every variable in those atoms should be
        ground.
    goal : list (or any 0-based indexable collection)
        A collection of atoms, possibly with variables, that constitute
        a pattern. This function's objective is to find a substitution
        from variables to constants s.t. goal is a subset of atoms.
    
    Return
    ------
    out : generator
        A generator of substitutions, each substitution being a dictionary
        representing the substitutions that must take place so goal is
        contained within atoms. If you want all the substitutions stored
        in a list, use list(goal_match(...)).
    
    Examples
    --------
    >>> atoms = [("on", "a", "b"), ("on", "b", "c"), ("ontable", "c"),
    ...          ("ontable", "d"), ("ontable", "e"), ("clear", "a"),
    ...          ("clear", "d"), ("clear", "e")]
    >>> sorted(sorted(d.items()) for d in goal_match(atoms, [("on", "X", "Y"), ("on", "Y", "Z"), ("ontable", "Z")]))
    [[('X', 'a'), ('Y', 'b'), ('Z', 'c')]]
    >>> sorted(sorted(d.items()) for d in goal_match(atoms, [("ontable", "X")]))
    [[('X', 'c')], [('X', 'd')], [('X', 'e')]]
    >>> sorted(sorted(d.items()) for d in goal_match(atoms, [("on", "X", "X")]))
    []
    """
    stack = [(0, {})]
    while stack:
        index, sigma = stack.pop()
        if index == len(goal):
            yield sigma
        else:
            for atom in atoms:
                sigma_new = match_unify(atom, goal[index], sigma.copy())
                if sigma_new is not None:
                    stack.append((index+1, sigma_new))
    

def dict_leq(d1, d2):
    for k, v in d1.items():
        if v > d2.get(k, 0):
            return False
    return True
    
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
