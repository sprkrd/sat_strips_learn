from .cluster_z3 import cluster
from .utils import inverse_map, Timer
from .action import Action

from .viz import draw_cluster_graph, draw_coarse_cluster_graph


STANDARD_FILTERS = [
    None,
    {"min_score": -1, "fn": max},
    {"min_score": -1, "fn": min},
    {"min_score": -1, "fn": sum},
    {"min_score": -0.5, "fn": lambda t: sum(t) / len(t) if t else 0},
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
    def __init__(self, action_library=None, filters=None, timeout=None):
        self.action_library = action_library or {}
        self.filters = filters or [None]
        self._current_filter_level = 0
        self.timeout = timeout
        self.wall_times = []
        self.cpu_times = []
        self.peak_z3_memory = 0

    def _action_from_transition(self, s, s_next):
        a = Action.from_transition(s, s_next)
        feature_filter = self.filters[self._current_filter_level]
        if feature_filter is not None:
            a = a.filter_features(**feature_filter)
        return a

    def _action_recognition(self, s, s_next):
        a = self._action_from_transition(s, s_next)
        replace_action = None
        found_u = None
        dist_found_u = float('inf')
        for a_lib in self.action_library.values():
            a_u = cluster(a_lib, a, True, self.timeout)
            dist_u = float('inf') if a_u is None else a_u.parent.distance
            if dist_u < dist_found_u:
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

    def action_recognition(self, s, s_next, logger=None):
        timer = Timer()
        a_g, updated = None, None
        while a_g is None:
            try:
                a_g, updated = self._action_recognition(s, s_next)
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
        
    def add_negative_example(self, pre_state, post_state):
        assert not (pre_state.is_uncertain() or post_state.is_uncertain()), "This feature only works with fully observable states"
        # TODO
        # ~ a_g = self._action_from_transition(pre_state, post_state)
        # ~ review_actions = list(self.action_library)
        # ~ while review_actions:
            # ~ next_set_of_review_actions = []
            # ~ for a_lib in review_actions:
                # ~ a_u = cluster(a_g, a_lib)
                # ~ if not check_updated(a_u, a_lib):
                    # ~ # a_lib allows the transition pre_state -> post_state, so it has to be split
                    # ~ # to disallow the negative example
                    # ~ del 
        
        raise NotImplementedError()

    def draw_graph(self, outdir, coarse=False, view=False, cleanup=True,
            filename="g.gv", format="pdf", **kwargs):
        if coarse:
            g = draw_coarse_cluster_graph(list(self.action_library.values()), **kwargs)
        else:
            g = draw_cluster_graph(list(self.action_library.values()), **kwargs)
        g.render(outdir+"/"+filename, view=view, cleanup=cleanup, format=format)
