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


def dict_leq(d1, d2):
    for k, v in d1.items():
        if v > d2.get(k, 0):
            return False
    return True
