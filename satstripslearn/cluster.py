import z3

from itertools import product

from .openworld import Action, ACTION_SECTIONS
from .utils import dict_leq


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


class Variable:
    def __init__(self, z3ref, *args):
        self.z3ref = z3ref
        self.args = args

    @property
    def prefix(self):
        return self.args[0]

    @property
    def indices(self):
        return self.args[1:]


class VariableStorage:
    def __init__(self):
        self._storage = {}

    def __len__(self):
        return len(self._storage)

    def __iter__(self):
        return iter(self._storage)

    def __call__(self, *args):
        var = self._storage.get(args)
        if var is None:
            varname = "_".join(map(str,args))
            var = self._storage[args] = Variable(z3.Bool(varname), args)
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
        Whether or not to count uncertain atoms.

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
    >>> from .openworld import wrap_predicate
    >>> from .strips import Object, ROOT_TYPE
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
    # TODO Which option is more appropriate? Leaving this functionality
    # as a method of Action or putting it as a standalone function?
    if not dict_leq(left.get_role_count(("add",),False), right.get_role_count(("add",))):
        return False
    if not dict_leq(left.get_role_count(("del",),False), right.get_role_count(("del",))):
        return False
    if not dict_leq(left.get_role_count(("add",),False), right.get_role_count(("add",))):
        return False
    if not dict_leq(left.get_role_count(("del",),False), right.get_role_count(("del",))):
        return False
    return True


def get_grouped_latoms(action):
    result = {section: [] for section in ACTION_SECTIONS}
    for idx, latom in enumerate(action.atoms):
        result[latom.section].append((idx, latom))
    return result


def cluster(left, right, timeout=None):
    timer = Timer()

    if not broadphase_test(right):
        return None

    objects_left = left.get_referenced_objects(as_list=True)
    objects_right = right.get_referenced_objects(as_list=True)
    W_soft_preserve =  min(len(objects_left), len(objects_right)) + 1

    grouped_latoms_left = get_grouped_latoms(left)
    grouped_latoms_right = get_grouped_latoms(right)

    #############
    # VARIABLES #
    #############

    # It's not necessary to create all the variables beforehand, but's it's nice
    # to have them indexed in a dict for reference. Maybe we will need this
    # at some point?

    variables = {} # index of variables

    # some cached data for speeding up the generation of the constraints later.
    latom_left_potential_matches = {}
    latom_right_potential_matches = {}

    hard_preserve_left = []
    hard_preserve_right = []
    soft_preserve_left = []
    soft_preserve_right = []

    # Create x variables (relations between objects in left and objects in right)
    for obj_l, obj_r in product(objects_left, objects_right):
        x_l_r = varname("x", obj_l, obj_r)
        variables[x_l_r] = Bool(x_l_r)

    # Create y variables (relations between latoms in left and latoms in right)
    # and identify which latoms can be matched
    for latom_type, latoms_left in grouped_latoms_left.items():
        latoms_right = grouped_latoms_right[latom_type]
        for (l,latom_left), (r,latom_right) in product(latoms_left, latoms_right):
            if latom_left.head == latom_right.head:
                latom_left_potential_matches.setdefault(l,[]).append(r)
                latom_right_potential_matches.setdefault(r,[]).append(l)
                y_l_r = varname("y", l, r)
                variables[y_l_r] = Bool(y_l_r)

    # Create z variables, which are preservation variables. Identify which are
    # needed to be true, and which are needed to be false
    for i, latom in enumerate(left.latoms):
        if latom.latom_type == "pre" or not latom.certain:
            soft_preserve_left.append(i)
        else:
            hard_preserve_left.append(i)
        z_0_i = varname("z", 0, i)
        variables[z_0_i] = Bool(z_0_i)
    for i, latom in enumerate(right.latoms):
        if latom.latom_type == "pre" or not latom.certain:
            soft_preserve_right.append(i)
        else:
            hard_preserve_right.append(i)
        z_1_i = varname("z", 1, i)
        variables[z_1_i] = Bool(z_1_i)

    ###############
    # CONSTRAINTS #
    ###############

    # Cached data

    latom_left_potential_matches = [[] for _ in range(len(left.atoms))]
    latom_right_potential_matches = [[] for _ in range(len(left.atoms))]

    object_left_potential_matches = {o:set() for o in objects_left}
    object_right_potential_matches = {o:set() for o in objects_right}

    hard_preserve_left = []
    hard_preserve_right = []
    soft_preserve_left = []
    soft_preserve_right = []

    for section in ACTION_SECTIONS:
        p = product(grouped_latoms_left[section]. grouped_latoms_right[section])
        for (idx1,latom1), (idx2,latom2) in p:
            if latom1.atom.head != latom2.atom.head:
                break
            latom_left_potential_matches[idx1].append(idx2)
            latom_right_potential_matches[idx2].append(idx1)
            for o1,o2 in zip(latom1.atom.args, latom2.atom.args):
                object_left_potential_matches[o1].add(o2)
                object_right_potential_matches[o2].add(o1)

    for latom in left.atoms:
        if




    hard_constraints = []
    soft_constraints = []

    # (H1) partial injective mapping
    for obj_l in objects_left:
        hard_constraints += amo([variables[varname("x", obj_l, obj_r)]
            for obj_r in objects_right])
    for obj_r in objects_right:
        hard_constraints += amo([variables[varname("x", obj_l, obj_r)]
            for obj_l in objects_left])

    # (H2) Features match iff arguments match
    for l, potential_matches in latom_left_potential_matches.items():
        for r in potential_matches:
            latom_l = left.latoms[l]
            latom_r = right.latoms[r]
            lhs = variables[varname("y", l, r)]
            rhs = []
            for obj_l, obj_r in zip(latom_l.arguments, latom_r.arguments):
                rhs.append(variables[varname("x", obj_l, obj_r)])
            rhs = And(*rhs)
            hard_constraints.append(lhs == rhs)

    # (H3) A latom is preserved iff is matched with at least another latom
    for l in range(len(left.latoms)):
        lhs = variables[varname("z", 0, l)]
        rhs = []
        for r in latom_left_potential_matches.get(l, []):
            rhs.append(variables[varname("y", l, r)])
        rhs = Or(*rhs)
        hard_constraints.append(lhs == rhs)
    for r in range(len(right.latoms)):
        lhs = variables[varname("z", 1, r)]
        rhs = []
        for l in latom_right_potential_matches.get(r, []):
            rhs.append(variables[varname("y", l, r)])
        rhs = Or(*rhs)
        hard_constraints.append(lhs == rhs)

    # (H4) All "sure" effects are preserved
    for l in hard_preserve_left:
        hard_constraints.append(variables[varname("z", 0, l)])
    for r in hard_preserve_right:
        hard_constraints.append(variables[varname("z", 1, r)])

    # (S1) Try not to match constants with different name (a.k.a. avoid lifting)
    for obj_l, obj_r in product(objects_left, objects_right):
        if not is_lifted(obj_l) and not is_lifted(obj_r) and obj_l!=obj_r:
            soft_const = Not(variables[varname("x", obj_l, obj_r)])
            soft_constraints.append( (1, soft_const) )

    # (S2) Try to preserve predicates and uncertain effects
    for l in soft_preserve_left:
        soft_const = variables[varname("z", 0, l)]
        soft_constraints.append( (W_soft_preserve, soft_const) )
    for r in soft_preserve_right:
        soft_const = variables[varname("z", 1, r)]
        soft_constraints.append( (W_soft_preserve, soft_const) )

    o = Optimize()
    o.add(*hard_constraints)
    for weight, soft_const in soft_constraints:
        o.add_soft(soft_const, weight)

    if timeout:
        o.set("timeout", timeout)

    result = o.check()
    if result == unknown:
        raise TimeoutError(f"timeout: {timeout}ms")

    if result == unsat:
        return None

    model = o.model()
    objectives = o.objectives()[0]
    dist = model.eval(o.objectives()[0]).as_long() / W_soft_preserve
    if normalize_distance:
        len_pre_left = len(grouped_latoms_left["pre"])
        len_pre_right = len(grouped_latoms_right["pre"])
        min_dist = abs(len_pre_left - len_pre_right)
        max_dist = len_pre_left + len_pre_right + (W_soft_preserve-1)/W_soft_preserve
        dist = (dist - min_dist) / max_dist

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
    for l, latom_l in enumerate(left.latoms):
        preserved_var = variables[varname("z", 0, l)]
        if not model[preserved_var]:
            continue
        for r in latom_left_potential_matches[l]:
            related_var = variables[varname("y", l, r)]
            if model[related_var]:
                latom_r = right.latoms[r]
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
