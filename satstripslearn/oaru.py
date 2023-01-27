from .cluster import cluster, Cluster
from .utils import Timer, get_memory_usage
from .openworld import Action
from .viz import draw_cluster_graph, draw_coarse_cluster_graph
from .strips import Domain


def action_from_transition(s, s_next, latom_filter=None):
    a = Action.from_transition(s, s_next)
    if latom_filter is not None:
        a = latom_filter(a)
    return Cluster(a)


class Operation:
    def __init__(self):
        self.id = None
        self.name = None
        self.description = None
        self.new_actions = None
        self.removed_actions = None
        self.wall_time = None
        self.cpu_time = None
        self.max_mem = None

    def __str__(self):
        new_str = ", ".join(action.name for action in self.new_actions)
        removed_str = ", ".join(action.name for action in self.removed_actions)
        return f"{self.id}: {self.name}. {self.description}. Added actions [{new_str}]. "\
               f"Removed actions: [{removed_str}]. "\
               f"Wall time (ms): {self.wall_time*1000}. "\
               f"CPU time (ms): {self.cpu_time*1000}. "\
               f"Peak memory (MB): {self.max_mem}"


class OaruAlgorithm:
    def __init__(self, double_filtering=False, cluster_opts=None, add_non_novel=True):
        self._next_action_id = 1
        self._cluster_cache = {}
        self._transitions = []
        self.action_library = {}
        self.negative_examples = []
        self.history = []
        self.double_filtering = double_filtering
        self.cluster_opts = cluster_opts or {}
        self.add_non_novel = add_non_novel

    def undo_last_action(self):
        if not self.history:
            raise IndexError("Empty history, cannot undo last action")
        last_operation = self.history.pop()
        for action_cluster in last_operation.added_actions:
            del self.action_library[action_cluster.name]
        for action_cluster in last_operation.removed_actions:
            self.action_library[action_cluster.name] = action_cluster
        if last_operation.name == "new_negative_example":
            self.negative_examples.pop()

    def _rename(self, action):
        if action.name == "unnamed":
            action.action.name = f"action-{self._next_action_id}"
            self._next_action_id += 1

    def _cluster(self, a, tga, latom_filter=None):
        try:
            new_cluster = self._cluster_cache[(a.name, tga.name)]
        except KeyError:
            new_cluster = cluster(a, tga, **self.cluster_opts)
            if latom_filter is not None and self.double_filtering:
                new_cluster.action = latom_filter(new_cluster.action)
            self._cluster_cache[(a.name, tga.name)] = new_cluster
        return new_cluster

    def _action_recognition(self, tga, latom_filter=None):
        timer = Timer()
        replaced_action = None
        updated_action = None
        dist_updated = float('inf')
        for a_lib in self.action_library.values():
            new_cluster = self._cluster(a_lib, tga, latom_filter)
            dist_cluster = float('inf') if new_cluster is None else new_cluster.distance
            if dist_cluster < dist_updated and not self._allows_negative(new_cluster):
                replaced_action = a_lib
                updated_action = new_cluster
                dist_updated = dist_cluster

        op = Operation()
        op.id = len(self.history)
        op.name = "new_demonstration"
        library_updated = False
        if updated_action is None:
            self.action_library[tga.name] = tga
            a_g = tga.action
            library_updated = True
            op.description = f"Added TGA {tga.name}"
            op.new_actions = [tga]
            op.removed_actions = []
        elif updated_action.updates_left() or self.add_non_novel:
            sigma = updated_action.additional_info["sigma_right"]
            self._rename(updated_action)
            self.action_library[updated_action.name] = updated_action
            del self.action_library[replaced_action.name]
            a_g = updated_action.action.ground(sigma)
            library_updated = True
            op.description = f"Action {replaced_action.name} upgraded to {updated_action.name}"
            op.new_actions = [updated_action]
            op.removed_actions = [replaced_action]
        else:
            sigma = updated_action.additional_info["tau"]
            a_g = replaced_action.action.ground(sigma)
            op.description = f"No updates, action {replaced_action.name} "\
                             f"already explains the demonstration)"
            op.new_actions = []
            op.removed_actions = []

        elapsed_cpu, elapsed_wall = timer.toc()
        memuse = get_memory_usage()

        op.wall_time = elapsed_wall
        op.cpu_time = elapsed_cpu
        op.max_mem = memuse["vmpeak"]
        return a_g, library_updated, op

    def action_recognition(self, s, s_next, latom_filter=None):
        tga = action_from_transition(s, s_next, latom_filter)
        self._rename(tga)
        self._transitions.append((tga, latom_filter))
        a_g, library_updated, op = self._action_recognition(tga, latom_filter)
        self.history.append(op)
        return a_g, library_updated

    def _can_produce_transition(self, action, tga):
        updated_action = cluster(action, tga, **self.cluster_opts)
        return updated_action is not None and not updated_action.updates_left()

    def _allows_negative(self, action):
        return any(self._can_produce_transition(action, n) for n in self.negative_examples)

    def strips_domain(self, domain_template):
        domain = Domain(domain_template.name,
                domain_template.predicates,
                domain_template.types)
        for action in self.action_library.values():
            domain.add_action(action.action.to_strips())
        return domain

    # def _refactor(self, action, neg_example):
        # unchecked_actions = [action]
        # while unchecked_actions:
            # unchecked_actions_next = []
            # for a in unchecked_actions:
                # if not self._can_produce_transition(a, neg_example):
                    # continue
                # if a.is_tga():
                    # raise ValueError("Cannot undo TGA!")
                # parent_left = a.left_parent
                # parent_right = a.right_parent
                # unchecked_actions_next.append(parent_left)
                # unchecked_actions_next.append(parent_right)
                # del self.action_library[a.name]
                # self.action_library[parent_left.name] = parent_left
                # self.action_library[parent_right.name] = parent_right
            # unchecked_actions = unchecked_actions_next

    # def _remerge(self):
        # cluster_cache = self._cluster_cache
        # action_list = list(self.action_library.values())

        # min_dist = float('inf')
        # candidate_1 = None
        # candidate_2 = None
        # updated_action = None

        # for i, action_1 in enumerate(action_list):
            # for action_2 in action_list[i+1:]:
                # try:
                    # new_cluster = cluster_cache[(action_1.name, action_2.name)]
                # except KeyError:
                    # new_cluster = cluster(action_1, action_2, **self.cluster_opts)
                    # cluster_cache[(action_1.name, action_2.name)] = new_cluster
                    # cluster_cache[(action_2.name, action_1.name)] = new_cluster
                # if new_cluster is None:
                    # continue
                # if self._allows_negative(new_cluster):
                    # continue
                # dist_cluster = new_cluster.distance
                # if dist_cluster < min_dist:
                    # candidate_1 = action_1
                    # candidate_2 = action_2
                    # updated_action = new_cluster

        # if updated_action is not None:
            # del self.action_library[candidate_1.name]
            # del self.action_library[candidate_2.name]
            # self._new_action(updated_action)
            # return True

        # return False

    # def add_negative_example(self, pre_state, post_state):
        # timer = Timer()

        # neg_example = action_from_transition(pre_state, post_state)
        # neg_example.action.name = f"negative-example-{len(self.negative_examples)+1}"
        # self.negative_examples.append(neg_example)

        # actions_before_operation = set(self.action_library.values())

        # for action in list(self.action_library.values()):
            # self._refactor(action, neg_example)

        # updated = True
        # while updated:
            # updated = self._remerge()

        # actions_after_operation = set(self.action_library.values())

        # elapsed_cpu, elapsed_wall = timer.toc()
        # memuse = get_memory_usage()

        # op = Operation()
        # op.id = len(self.history)
        # op.name = "new_negative_example"
        # op.description = f"Added negative example {neg_example.name}"
        # op.new_actions = list(actions_after_operation - actions_before_operation)
        # op.removed_actions = list(actions_before_operation - actions_after_operation)
        # op.wall_time = elapsed_wall
        # op.cpu_time = elapsed_cpu
        # op.max_mem = memuse["vmpeak"]
        # self.history.append(op)

    def add_negative_example(self, pre_state, post_state):
        timer = Timer()

        neg_example = action_from_transition(pre_state, post_state)
        neg_example.action.name = f"negative-example-{len(self.negative_examples)+1}"
        self.negative_examples.append(neg_example)

        actions_before_operation = set(self.action_library.values())

        self.action_library.clear()
        for tga, latom_filter in self._transitions:
            self._action_recognition(tga, latom_filter)

        actions_after_operation = set(self.action_library.values())

        elapsed_cpu, elapsed_wall = timer.toc()
        memuse = get_memory_usage()

        op = Operation()
        op.id = len(self.history)
        op.name = "new_negative_example"
        op.description = f"Added negative example {neg_example.name}"
        op.new_actions = list(actions_after_operation - actions_before_operation)
        op.removed_actions = list(actions_before_operation - actions_after_operation)
        op.wall_time = elapsed_wall
        op.cpu_time = elapsed_cpu
        op.max_mem = memuse["vmpeak"]
        self.history.append(op)

    def draw_graph(self, outdir, coarse=False, view=False, cleanup=True,
            filename="g.gv", format="pdf", **kwargs):
        if coarse:
            g = draw_coarse_cluster_graph(list(self.action_library.values()), **kwargs)
        else:
            g = draw_cluster_graph(list(self.action_library.values()), **kwargs)
        g.render(outdir+"/"+filename, view=view, cleanup=cleanup, format=format)


def count_features(action):
    feat_count = {}
    for latom in action.atoms:
        key = (latom.atom.head,latom.section,latom.certain)
        count = feat_count.get(key, 0)
        feat_count[key] = count + 1
    return feat_count


def equal_libraries(lib1, lib2):
    if len(lib1) != len(lib2):
        return False

    lib2 = lib2.copy()

    feat_count_lib1 = {a:count_features(a.action) for a in lib1.values()}
    feat_count_lib2 = {a:count_features(a.action) for a in lib2.values()}

    for a1 in lib1.values():
        found = None
        feat_count_a1 = feat_count_lib1[a1]
        for a2 in lib2.values():
            if len(a1.action.parameters) != len(a2.action.parameters):
                continue
            elif feat_count_a1 != feat_count_lib2[a2]:
                continue
            else:
                c = cluster(a1, a2, amo_encoding="pseudoboolean")
                if c is None or c.distance > 0:
                    continue
            found = a2
            break
        if found is None:
            return False
        del lib2[a2.name]

    return True

