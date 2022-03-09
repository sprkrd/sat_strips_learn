from itertools import product

from z3 import *

from .action import Action, ActionCluster
from .utils import *


def varname(name, *indices):
    return "_".join((name,*(str(i) for i in indices)))


def amo(variables):
    """
    Construct a list of SAT clauses in Z3 that represents the "at most once"
    constraint using the quadratic encoding.

    Parameters
    ----------
    variables : list
        a number of Z3 variables of the Boolean sort (z3.BoolRef, more specifically)

    Returns
    -------
    out : list
        a list of Z3 Boolean expressions that, in conjunction, represents
        that at most one of the given variables can be assigned to True.
        The size of such list is N*(N-1)/2, where N = len(variables)
    """
    constraints = []
    for idx, u in enumerate(variables):
        for v in variables[idx+1:]:
            constraints.append(Or(Not(u), Not(v)))
    return constraints


def cluster(left, right, include_additional_info=False, timeout=None, normalize_distance=False):
    # TODO this function is a bit too long! At some point we should break it into
    # smaller chunks.

    timer = Timer()

    if not left.cluster_broadphase(right):
        return None

    objects_left = left.get_referenced_objects()
    objects_right = right.get_referenced_objects()

    # ~ W_soft_preserve = 2*(min(len(objects_left), len(objects_right)) + 1)
    # W_soft_preserve = 2*min(len(objects_left), len(objects_right)) + 1
    W_soft_preserve = min(len(objects_left), len(objects_right)) + 1

    grouped_features_left = left.get_grouped_features()
    grouped_features_right = right.get_grouped_features()

    #############
    # VARIABLES #
    #############

    # It's not necessary to create all the variables beforehand, but's it's nice
    # to have them indexed in a dict for reference. Maybe we will need this
    # at some point?

    variables = {} # index of variables

    # some cached data for speeding up the generation of the constraints later.
    feat_left_potential_matches = {}
    feat_right_potential_matches = {}

    hard_preserve_left = []
    hard_preserve_right = []
    soft_preserve_left = []
    soft_preserve_right = []

    # Create x variables (relations between objects in left and objects in right)
    for obj_l, obj_r in product(objects_left, objects_right):
        x_l_r = varname("x", obj_l, obj_r)
        variables[x_l_r] = Bool(x_l_r)

    # Create y variables (relations between features in left and features in right)
    # and identify which features can be matched
    for feature_type, features_left in grouped_features_left.items():
        features_right = grouped_features_right[feature_type]
        for (l,feat_left), (r,feat_right) in product(features_left, features_right):
            if feat_left.head == feat_right.head:
                feat_left_potential_matches.setdefault(l,[]).append(r)
                feat_right_potential_matches.setdefault(r,[]).append(l)
                y_l_r = varname("y", l, r)
                variables[y_l_r] = Bool(y_l_r)

    # Create z variables, which are preservation variables. Identify which are
    # needed to be true, and which are needed to be false
    for i, feat in enumerate(left.features):
        if feat.feature_type == "pre" or not feat.certain:
            soft_preserve_left.append(i)
        else:
            hard_preserve_left.append(i)
        z_0_i = varname("z", 0, i)
        variables[z_0_i] = Bool(z_0_i)
    for i, feat in enumerate(right.features):
        if feat.feature_type == "pre" or not feat.certain:
            soft_preserve_right.append(i)
        else:
            hard_preserve_right.append(i)
        z_1_i = varname("z", 1, i)
        variables[z_1_i] = Bool(z_1_i)

    ###############
    # CONSTRAINTS #
    ###############

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
    for l, potential_matches in feat_left_potential_matches.items():
        for r in potential_matches:
            feat_l = left.features[l]
            feat_r = right.features[r]
            lhs = variables[varname("y", l, r)]
            rhs = []
            for obj_l, obj_r in zip(feat_l.arguments, feat_r.arguments):
                rhs.append(variables[varname("x", obj_l, obj_r)])
            rhs = And(*rhs)
            hard_constraints.append(lhs == rhs)

    # (H3) A feature is preserved iff is matched with at least another feature
    for l in range(len(left.features)):
        lhs = variables[varname("z", 0, l)]
        rhs = []
        for r in feat_left_potential_matches.get(l, []):
            rhs.append(variables[varname("y", l, r)])
        rhs = Or(*rhs)
        hard_constraints.append(lhs == rhs)
    for r in range(len(right.features)):
        lhs = variables[varname("z", 1, r)]
        rhs = []
        for l in feat_right_potential_matches.get(r, []):
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
        len_pre_left = len(grouped_features_left["pre"])
        len_pre_right = len(grouped_features_right["pre"])
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

    features_u = []
    for l, feat_l in enumerate(left.features):
        preserved_var = variables[varname("z", 0, l)]
        if not model[preserved_var]:
            continue
        for r in feat_left_potential_matches[l]:
            related_var = variables[varname("y", l, r)]
            if model[related_var]:
                feat_r = right.features[r]
                feat_u = feat_l.replace(sigma_left)
                feat_u.certain = feat_l.certain or feat_r.certain
                features_u.append(feat_u)

    cluster = ActionCluster(left, right, dist)
    name_u = action_id_gen()
    action_u = Action(name_u, features_u, parent=cluster)

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
