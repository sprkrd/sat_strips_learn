from .cluster import cluster, ActionCluster
from .utils import Timer
from .openworld import Action
# from .viz import draw_cluster_graph, draw_coarse_cluster_graph


def action_from_transition(s, s_next, latom_filter=None):
    a = Action.from_transition(s, s_next)
    if latom_filter is not None:
        a = latom_filter(a)
    return ActionCluster(a)


def action_digest(a):
    count_certain = 0
    count_uncertain = 0
    arity = len(a.parameters)
    for latom in a.atoms:
        if latom.certain:
            count_certain += 1
        else:
            count_uncertain += 1
    return (count_certain, count_uncertain, arity)


def check_updated(a0, a1):
    return action_digest(a0) != action_digest(a1)


class Operation:
    def __init__(self, op_num, op_id, op_info, wall_time, cpu_time, max_mem):
        self.op_num = op_num
        self.op_id = op_id
        self.op_info = op_info
        self.wall_time = wall_time
        self.cpu_time = cpu_time
        self.max_mem = max_mem
    

class OaruAlgorithm:
    def __init__(self, action_library=None, double_filtering=False, **cluster_opts):
        self.last_operation = None
        self.action_library = action_library or {}
        self.negative_examples = []
        self.double_filtering = double_filtering
        self.cluster_opts = cluster_opts

    def action_recognition(self, s, s_next, latom_filter=None):
        timer = Timer()
        max_mem = 0
        a = action_from_transition(s, s_next, latom_filter)
        replaced_action = None
        found_u = None
        dist_found_u = float('inf')
        for a_lib in self.action_library.values():
            a_u = cluster(a_lib, a, **self.cluster_opts)
            if a_u is not None and latom_filter and self.double_filtering:
                a_u.action = feature_filter(a_u.action)
            dist_u = float('inf') if a_u is None else a_u.distance
            if dist_u < dist_found_u: #and not self._allows_negative_example(a_u.action):
                mem_z3 = a_u.additional_info["z3_stats"]["memory"]
                max_mem = max(max_mem, mem_z3)
                replaced_action = a_lib
                found_u = a_u
                dist_found_u = dist_u
        updated = True
        if found_u is not None:
            updated = check_updated(replaced_action.action, found_u.action)
            if updated:
                del self.action_library[replaced_action.action.name]
                self.action_library[found_u.action.name] = found_u
                sigma = found_u.additional_info["sigma_right"]
                a_g = found_u.action.replace(sigma)
            else:
                sigma = found_u.additional_info["sigma_left"]
                a_g = replaced_action.action.replace(sigma)
        else:
            self.action_library[a.action.name] = a
            a_g = a.action

        elapsed_cpu, elapsed_wall = timer.toc()

        op_num = (self.last_operation.op_num+1) if self.last_operation else 0
        op_id = "positive_example"
        op_info = {
            "updated": updated,
            "schema": a_g.name if updated else found_u.action.name
        }

        self.last_operation = Operation(op_num, op_id, op_info, elapsed_wall, elapsed_cpu, max_mem)

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
