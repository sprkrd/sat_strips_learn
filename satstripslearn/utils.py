from threading import Lock


INF = float('inf')


class SequentialIdGenerator:
    def __init__(self, prefix=""):
        self._count = 0
        self._prefix = prefix
        self._mtx = Lock()

    def __call__(self):
        with self._mtx:
            next_id = self._count
            self._count += 1
        return f"{self._prefix}{next_id}"


action_id_gen = SequentialIdGenerator("action-")
variable_id_gen = SequentialIdGenerator("?x")
cluster_id_gen = SequentialIdGenerator("cluster-")


def atom_to_pddl(t):
    return f"({' '.join(t)})"

def atom_to_str(t):
    return f"{t[0]}({','.join(t[1:])})"

def replace(t, sigma):
    return (t[0],*(sigma.get(a,a) for a in t[1:]))


def is_lifted(obj):
    return obj.startswith("?")


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
