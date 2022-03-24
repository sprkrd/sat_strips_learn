from .cluster_z3 import cluster
from .utils import inverse_map, Timer, atom_to_pddl
from .action import Action
from .feature_filter import FeatureFilter
from .viz import draw_cluster_graph, draw_coarse_cluster_graph


# STANDARD_FILTERS = [
    # None,
    # {"min_score": -1, "fn": max},
    # {"min_score": -1, "fn": min},
    # {"min_score": -1, "fn": sum},
    # {"min_score": -0.5, "fn": lambda t: sum(t) / len(t) if t else 0},
# ]

STANDARD_FILTERS = [
    None,
    FeatureFilter(1),
    FeatureFilter(0),
]


def action_digest(a):
    count_certain = 0
    count_uncertain = 0
    arity = len(a.get_parameters())
    for f in a.features:
        if f.certain:
            count_certain += 1
        else:
            count_uncertain += 1
    return (count_certain, count_uncertain, arity)


def check_updated(a0, a1):
    return action_digest(a0) != action_digest(a1)


class OaruAlgorithm:
    def __init__(self, action_library=None, filters=None, timeout=None, normalize_dist=False, double_filtering=False):
        self.action_library = action_library or {}
        self.filters = filters or [None]
        self._current_filter_level = 0
        self.timeout = timeout
        self.normalize_dist = normalize_dist
        self.double_filtering = double_filtering
        self.wall_times = []
        self.cpu_times = []
        self.peak_z3_memory = 0
        self.negative_examples = []

    def _action_from_transition(self, s, s_next, force_filter):
        a = Action.from_transition(s, s_next)
        feature_filter = force_filter or self.filters[self._current_filter_level]
        if feature_filter is not None:
            a = feature_filter(a)
        return a

    def _action_recognition(self, s, s_next, force_filter):
        a = self._action_from_transition(s, s_next, force_filter)
        replace_action = None
        found_u = None
        dist_found_u = float('inf')
        for a_lib in self.action_library.values():
            a_u = cluster(a_lib, a, True, self.timeout, self.normalize_dist)
            feature_filter = force_filter or self.filters[self._current_filter_level]
            if a_u is not None and feature_filter is not None and self.double_filtering:
                # a_u = a_u.filter_features(**feature_filter)
                a_u = feature_filter(a_u)
            dist_u = float('inf') if a_u is None else a_u.parent.distance
            if dist_u < dist_found_u and not self._allows_negative_example(a_u):
                additional_info = a_u.parent.additional_info
                mem_z3 = additional_info["z3_stats"]["memory"]
                self.peak_z3_memory = max(self.peak_z3_memory, mem_z3)
                replace_action = a_lib
                found_u = a_u
                dist_found_u = dist_u
        updated = True
        if found_u is not None:
            updated = check_updated(replace_action, found_u)
            del self.action_library[replace_action.name]
            additional_info = found_u.parent.additional_info
            sigma = inverse_map(additional_info["sigma_right"])
            a_g = found_u.replace_references(sigma)
            self.action_library[found_u.name] = found_u
        else:
            a_g = self.action_library[a.name] = a
        return a_g, updated

    def increase_filter_level(self):
        if self._current_filter_level < len(self.filters)-1:
            self._current_filter_level += 1
            filter_features = self.filters[self._current_filter_level]
            action_library = [a.filter_features(**filter_features)
                    for a in self.action_library.values()]
            self.action_library = {a.name:a for a in action_library}
            return True
        return False

    def action_recognition(self, s, s_next, logger=None, force_filter=None):
        timer = Timer()
        a_g, updated = None, None
        while a_g is None:
            try:
                a_g, updated = self._action_recognition(s, s_next, force_filter)
            except TimeoutError:
                increased_lever = self.increase_filter_level()
                if not increased_lever:
                    self.timeout = None
                    if logger:
                        logger("Timeout! Cannot increase filter level further. No more timeouts.")
                elif logger:
                    logger(f"Timeout! Increased filter level to {self._current_filter_level}.")
        elapsed_cpu, elapsed_wall = timer.toc()
        self.wall_times.append(round(elapsed_cpu*1000))
        self.cpu_times.append(round(elapsed_wall*1000))
        return a_g, updated

    def _refactor(self, action, neg_example):
        unchecked_actions = [action]
        while unchecked_actions:
            unchecked_actions_next = []
            for a in unchecked_actions:
                if a.can_produce_transition(*neg_example):
                    assert a.parent is not None, "Cannot undo cluster!"
                    parent_left = a.parent.left_parent
                    parent_right = a.parent.right_parent
                    unchecked_actions_next.append(parent_left)
                    unchecked_actions_next.append(parent_right)
                    del self.action_library[a.name]
                    self.action_library[parent_left.name] = parent_left
                    self.action_library[parent_right.name] = parent_right
            unchecked_actions = unchecked_actions_next

    def _allows_negative_example(self, action):
        for neg_example in self.negative_examples:
            if action.can_produce_transition(*neg_example):
                return True
        return False

    def _remerge(self, already_checked=None):
        already_checked = already_checked or set()
        action_list = list(self.action_library.values())
        for i, action_1 in enumerate(action_list):
            for action_2 in action_list[i+1:]:
                if (action_1,action_2) in already_checked or (action_2,action_1) in already_checked:
                    continue
                already_checked.add((action_1, action_2))
                a_u = cluster(action_1, action_2, False, self.timeout, self.normalize_dist)
                if a_u is not None and not self._allows_negative_example(a_u):
                    del self.action_library[action_1.name]
                    del self.action_library[action_2.name]
                    self.action_library[a_u.name] = a_u
                    return True, already_checked
        return False, already_checked


    def add_negative_example(self, pre_state, post_state):
        assert not (pre_state.is_uncertain() or post_state.is_uncertain()), "This feature only works with fully observable states"

        neg_example = (pre_state, post_state)
        self.negative_examples.append(neg_example)

        for action in list(self.action_library.values()):
            self._refactor(action, neg_example)

        merged, already_checked = self._remerge()
        while merged:
            merged, already_checked = self._remerge(already_checked)

    def get_all_predicate_signatures(self):
        predicate_signatures = set()
        for action in self.action_library.values():
            for feat in action.features:
                predicate_signatures.add(feat.get_signature())
        return predicate_signatures

    def dump_pddl_domain(self, out, domain_name="oaru_domain"):
        out.write(f"(define (domain {domain_name})\n\n")
        out.write("(:requirements :strips)\n\n")
        out.write("(:predicates\n")
        for predicate_symbol, arity in self.get_all_predicate_signatures():
            generic_predicate = (predicate_symbol,) + tuple(f"X{i}" for i in range(arity))
            out.write(atom_to_pddl(generic_predicate))
            out.write("\n")
        out.write(")")
        for action in self.action_library.values():
            out.write("\n\n")
            out.write(action.to_pddl())
        out.write(f"\n)")

    def draw_graph(self, outdir, coarse=False, view=False, cleanup=True,
            filename="g.gv", format="pdf", **kwargs):
        if coarse:
            g = draw_coarse_cluster_graph(list(self.action_library.values()), **kwargs)
        else:
            g = draw_cluster_graph(list(self.action_library.values()), **kwargs)
        g.render(outdir+"/"+filename, view=view, cleanup=cleanup, format=format)
