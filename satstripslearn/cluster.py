import z3

from itertools import product

from .openworld import Action, ACTION_SECTIONS
from .utils import dict_leq, Timer


class ActionCluster:
    def __init__(self, action, additional_info=None):
        self.action = action
        self.additional_info = additional_info

    def is_tga(self):
        return self.additional_info is None

    @property
    def distance(self):
        return self.additional_info["distance"]

    @property
    def normalized_distance(self):
        return self.additional_info["normalized_distance"]

    @property
    def left_parent(self):
        return self.additional_info["left_parent"]

    @property
    def right_parent(self):
        return self.additional_info["right_parent"]


class VariableStorage:
    def __init__(self):
        self._storage = {}

    def __len__(self):
        return len(self._storage)

    def __iter__(self):
        return iter(self._storage.items())

    def __call__(self, *args):
        var = self._storage.get(args)
        if var is None:
            varname = "_".join(map(str,args))
            var = self._storage[args] = z3.Bool(varname)
        return var


def at_most_once(variables, encoding="quadratic"):
    """
    Construct a list of SAT clauses in Z3 that represents the "at most once"
    constraint using the specified encoding.

    Parameters
    ----------
    variables : list
        a number of Z3 variables of the Boolean sort (z3.BoolRef, more specifically)
    encoding : str
        the available encodings are "quadratic", "pseudoboolean", and "arithmetic"

    Returns
    -------
    out : list
        a list of Z3 expressions that, in conjunction, represents
        that at most one of the given variables can be assigned to True.
        The size of such list is N*(N-1)/2, where N = len(variables)
    """
    constraints = []
    if encoding == "quadratic":
        for idx, u in enumerate(variables):
            for v in variables[idx+1:]:
                constraints.append(z3.Or(z3.Not(u), z3.Not(v)))
    elif encoding == "pseudoboolean":
        constraints.append(z3.PbLe([(x,1) for x in variables], 1))
    elif encoding == "arithmetic":
        constraints.append(z3.Sum([z3.If(x,1,0) for x in variables]) <= 1)
    else:
        raise ValueError(f"Unknown encoding: {encoding}")
    return constraints


def get_role_count(action, sections=None, include_uncertain=True):
    """
    Count the number of occurrences of each atom *role* (i.e. the head
    of the atom) of the given section(s).

    Parameters
    ----------
    action : Action
        An open world action
    sections : iterable or None
        A (sub)set of ACTION_SECTIONS, the type(s) of the atom that this
        method should consider.
    include_uncertain : bool
        Whether to count uncertain atoms.

    Returns
    -------
    out : dict
        A dict from predicate symbols (str) to number of occurrences (int).
    """
    sections = sections or ACTION_SECTIONS
    role_count = {}
    for atom in action.get_atoms_in_section(sections, include_uncertain):
        head = atom.atom.head
        role_count[head] = role_count.get(head, 0) + 1
    return role_count


def broadphase_test(left, right):
    """
    Compares the number of predicates of each type in the effects of
    self and another action to make sure that they may be potentially
    clustered. This is a very easy check before resorting to more complex
    techniques.

    Examples
    --------
    >>> from satstripslearn.openworld import wrap_predicate
    >>> from satstripslearn.strips import Object, ROOT_TYPE
    >>> P = wrap_predicate("p", ROOT_TYPE)
    >>> x, y, s, t, u = [Object(obj) for obj in "xystu"]
    >>> a = Action("a", atoms=[
    ...     P(x, section="add", certain=True),
    ...     P(y, section="add", certain=False),
    ...     P(s, section="del", certain=True),
    ...     P(t, section="del", certain=True),
    ...     P(u, section="del", certain=False)])
    >>> b = Action("b", atoms=[
    ...     P(x, section="add", certain=True),
    ...     P(y, section="add", certain=True),
    ...     P(t, section="del", certain=False),
    ...     P(u, section="del", certain=False)])
    >>> c = Action("c", atoms=[
    ...     P(x, section="add", certain=True),
    ...     P(y, section="add", certain=True),
    ...     P(u, section="del", certain=False)])
    >>> broadphase_test(a, b)
    True
    >>> broadphase_test(a, c)
    False
    >>> broadphase_test(b, c)
    True
    """
    if not dict_leq(get_role_count(left, ("add",),False), get_role_count(right, ("add",))):
        return False
    if not dict_leq(get_role_count(left, ("del",),False), get_role_count(right, ("del",))):
        return False
    if not dict_leq(get_role_count(left, ("add",),False), get_role_count(right, ("add",))):
        return False
    if not dict_leq(get_role_count(left, ("del",),False), get_role_count(right, ("del",))):
        return False
    return True


def get_grouped_latoms(action):
    result = {section: [] for section in ACTION_SECTIONS}
    for idx, latom in enumerate(action.atoms):
        result[latom.section].append((idx, latom))
    return result


def cluster(left_cluster, right_cluster, **kwargs):
    left = left_cluster.action
    right = right_cluster.action

    timeout = kwargs.get("timeout")
    amo_encoding = kwargs.get("amo_encoding", "quadratic")

    timer = Timer()

    if not broadphase_test(left, right):
        return None

    # Cached data

    objects_left = left.get_referenced_objects(as_list=True)
    objects_right = right.get_referenced_objects(as_list=True)
    w_soft_preserve = min(len(objects_left), len(objects_right)) + 1

    grouped_latoms_left = get_grouped_latoms(left)
    grouped_latoms_right = get_grouped_latoms(right)

    latom_left_potential_matches = [[] for _ in range(len(left.atoms))]
    latom_right_potential_matches = [[] for _ in range(len(right.atoms))]

    object_left_potential_matches = {o: set() for o in objects_left}
    object_right_potential_matches = {o: set() for o in objects_right}

    for section in ACTION_SECTIONS:
        p = product(grouped_latoms_left[section], grouped_latoms_right[section])
        for (l_idx, latom_l), (r_idx, latom_r) in p:
            if latom_l.atom.get_signature() != latom_r.atom.get_signature():
                break
            latom_left_potential_matches[l_idx].append(r_idx)
            latom_right_potential_matches[r_idx].append(l_idx)
            for o1, o2 in zip(latom_l.atom.args, latom_r.atom.args):
                object_left_potential_matches[o1].add(o2)
                object_right_potential_matches[o2].add(o1)

    ###############
    # CONSTRAINTS #
    ###############

    varstg = VariableStorage()

    hard_constraints = []
    soft_constraints = []

    # (H1) partial injective mapping
    for obj_l, potential_matches in object_left_potential_matches.items():
        hard_constraints += at_most_once([varstg("x", obj_l, obj_r) for obj_r in potential_matches], amo_encoding)
    for obj_r, potential_matches in object_right_potential_matches.items():
        hard_constraints += at_most_once([varstg("x", obj_l, obj_r) for obj_l in potential_matches], amo_encoding)

    # (H2) Features match iff arguments match
    for l_idx, potential_matches in enumerate(latom_left_potential_matches):
        for r_idx in potential_matches:
            latom_l = left.latoms[l_idx]
            latom_r = right.latoms[r_idx]
            lhs = varstg("y", l_idx, r_idx)
            rhs = []
            for obj_l, obj_r in zip(latom_l.arguments, latom_r.arguments):
                rhs.append(varstg("x", obj_l, obj_r))
            rhs = z3.And(*rhs)
            hard_constraints.append(lhs == rhs)

    # (H3) A latom is preserved iff it matches at least another latom
    for l_idx in range(len(left.latoms)):
        lhs = varstg("z", "left", l_idx)
        rhs = []
        for r_idx in latom_left_potential_matches[l_idx]:
            rhs.append(varstg("y", l_idx, r_idx))
        rhs = z3.Or(*rhs)
        hard_constraints.append(lhs == rhs)
    for r_idx in range(len(right.latoms)):
        lhs = varstg("z", "right", r_idx)
        rhs = []
        for l_idx in latom_right_potential_matches[r_idx]:
            rhs.append(varstg("y", l_idx, r_idx))
        rhs = z3.Or(*rhs)
        hard_constraints.append(lhs == rhs)

    # (H4) All "sure" effects are preserved
    for l_idx, latom in enumerate(left.atoms):
        if latom.section != "pre" and latom.certain:
            hard_constraints.append(varstg("z", "left", l_idx))
    for r_idx, latom in enumerate(right.atoms):
        if latom.section != "pre" and latom.certain:
            hard_constraints.append(varstg("z", "right", r_idx))

    # (S1) Try not to match constants with different name (a.k.a. avoid lifting)
    for obj_l, potential_matches in object_left_potential_matches.items():
        for obj_r in potential_matches:
            if not obj_l.is_variable() and not obj_r.is_variable() and obj_l != obj_r:
                soft_const = z3.Not(varstg("x", obj_l, obj_r))
                soft_constraints.append((1, soft_const))

    # (S2) Try to preserve predicates and uncertain effects
    for l_idx, latom in enumerate(left.atoms):
        if latom.section == "pre" or not latom.certain:
            soft_const = varstg("z", "left", l_idx)
            soft_constraints.append((w_soft_preserve, soft_const))
    for l_idx, latom in enumerate(left.atoms):
        if latom.section == "pre" or not latom.certain:
            soft_const = varstg("z", "left", l_idx)
            soft_constraints.append((w_soft_preserve, soft_const))

    o = z3.Optimize()
    o.add(*hard_constraints)
    for weight, soft_const in soft_constraints:
        o.add_soft(soft_const, weight)

    if timeout:
        o.set("timeout", timeout)

    result = o.check()
    if result == z3.unknown:
        raise TimeoutError(f"timeout: {timeout}ms")

    if result == z3.unsat:
        return None

    model = o.model()
    dist = model.eval(o.objectives()[0]).as_long() / w_soft_preserve

    len_pre_left = len(grouped_latoms_left["pre"])
    len_pre_right = len(grouped_latoms_right["pre"])
    min_dist = abs(len_pre_left - len_pre_right)
    max_dist = len_pre_left + len_pre_right + (w_soft_preserve-1)/w_soft_preserve
    norm_dist = (dist - min_dist) / max_dist

    sigma_left = {}
    sigma_right = {}
    for obj_l, obj_r in product(objects_left, objects_right):
        var = variables[varname("x", obj_l, obj_r)]
        if model[var]:
            if is_lifted(obj_l):
                obj_u = obj_l
            elif is_lifted(obj_r):
                obj_u = obj_r
            elif obj_l == obj_r:
                obj_u = obj_l
            else:
                obj_u = variable_id_gen()
            sigma_left[obj_l] = obj_u
            sigma_right[obj_r] = obj_u

    latoms_u = []
    for l_idx, latom_l in enumerate(left.latoms):
        preserved_var = variables[varname("z", 0, l_idx)]
        if not model[preserved_var]:
            continue
        for r_idx in latom_left_potential_matches[l_idx]:
            related_var = variables[varname("y", l_idx, r_idx)]
            if model[related_var]:
                latom_r = right.latoms[r_idx]
                latom_u = latom_l.replace(sigma_left)
                latom_u.certain = latom_l.certain or latom_r.certain
                latoms_u.append(latom_u)

    cluster = ActionCluster(left, right, dist)
    name_u = action_id_gen()
    action_u = Action(name_u, latoms_u, parent=cluster)

    if include_additional_info:
        additional_info = {}
        elapsed_cpu, elapsed_wall = timer.toc()
        additional_info["elapsed_cpu_ms"] = round(elapsed_cpu*1000)
        additional_info["elapsed_wall_ms"] = round(elapsed_wall*1000)
        tau = {}
        for obj_l, obj_r in product(objects_left, objects_right):
            var = variables[varname("x", obj_l, obj_r)]
            if model[var]:
                tau[obj_l] = obj_r
        additional_info["tau"] = tau
        additional_info["sigma_left"] = sigma_left
        additional_info["sigma_right"] = sigma_right
        z3_stats = {k.replace(" ","_"): try_parse_number(v) for k,v in o.statistics()}
        additional_info["z3_stats"] = z3_stats
        cluster.additional_info = additional_info

    return action_u
