from .cluster_z3 import cluster
from .utils import inverse_map, Timer
from .action import Action


class OaruAlgorithm:
    def __init__(self, action_library=None, filter_features_kwargs=None):
        self.action_library = action_library or {}
        self.filter_features_kwargs = filter_features_kwargs
        self.wall_times = []
        self.cpu_times = []
        self.peak_z3_memory = 0

    def _action_from_transition(self, s, s_next):
        a = Action.from_transition(s, s_next)
        if self.filter_features_kwargs is not None:
            a = a.filter_features(**self.filter_features_kwargs)
        return a

    def action_recognition(self, s, s_next):
        timer = Timer()
        a = self._action_from_transition(s, s_next)
        replace_action = None
        found_u = None
        dist_found_u = float('inf')
        for a_lib in self.action_library.values():
            a_u = cluster(a_lib, a, True)
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
            updated = len(replace_action.features) != len(found_u.features) or \
                      len(replace_action.get_parameters()) != len(found_u.get_parameters())
            del self.action_library[replace_action.name]
            additional_info = found_u.parent.additional_info
            sigma = inverse_map(additional_info["sigma_right"])
            a_g = found_u.replace_references(sigma)
            self.action_library[found_u.name] = found_u
        else:
            a_g = self.action_library[a.name] = a
        elapsed_cpu, elapsed_wall = timer.toc()
        self.wall_times.append(round(elapsed_cpu*1000))
        self.cpu_times.append(round(elapsed_wall*1000))
        return a_g, updated
