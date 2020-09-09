from .cluster_z3 import cluster
from .utils import inverse_map, Timer
from .action import Action

from .viz import draw_cluster_graph, draw_coarse_cluster_graph


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
            updated = check_updated(replace_action, found_u)
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

    def draw_graph(self, outdir, coarse=False, view=False, cleanup=True, filename="g.gv", **kwargs):
        if coarse:
            g = draw_coarse_cluster_graph(list(self.action_library.values()), **kwargs)
        else:
            g = draw_cluster_graph(list(self.action_library.values()), **kwargs)
        g.render(outdir+"/"+filename, view=view, cleanup=cleanup)
