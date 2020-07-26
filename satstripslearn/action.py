from .undirected_graph import UndirectedGraph
from .utils import *
from .features import *


class Action:
    """
    Represents a STRIPS action. The class presents several utility method to
    facilitate clustering.

    Parameters
    ----------
    name: str
        name identifying the action
    pre_list: list
        precondition of the action, as list of tuples that represents a conjunction
        of atoms. Each tuple represents such an atom, which in turn is an instantiated predicate.
        The first element of the tuple is the name of the predicate, while the rest is the list
        of arguments names. Arguments with a ? character in front of its name are
        variables, prone to be substituted during action grounding. This representational
        convention is the same for the add list and for the delete list.
    add_list: list
        add effect of the action, as a list of tuples. See description of pre_list.
    del_list: list
        delete effect of the action, as a list of tuples. See description of pre_list.
    up: ActionCluster
        should this action be the result of merging two actions, this parameter must point
        to the cluster that represents this union (see ActionCluster).
    """

    def __init__(self, name, features):
        """
        See help(type(self)) for accurate signature.
        """
        self.name = name
        self.features = features
        self.up = up

    def get_grouped_features(self):
        grouped = {feat_type: [] for feat_type in FEATURE_TYPES}
        for feat in self.features:
            grouped[feat.feature_type].append(feat)
        return grouped

    def filter_features(self, feature_type=None, certainty=None):
        feature_type = feature_type or ["pre", "del", "add"]
        certainty = certainty or [False, True]
        return [feat for feat in self.features if feat.feature_type in feature_type and feat.certain in certainty]

    def replace_references(self, sigma):
        name = action_id_gen()
        pre_list = [replace(a,sigma) for a in self.pre_list]
        add_list = [replace(a,sigma) for a in self.add_list]
        del_list = [replace(a,sigma) for a in self.del_list]
        return Action(name, pre_list, add_list, del_list)

    def get_object_graph(self):
        """
        Constructs a directed graph in which the referenced objects act as
        vertices. Two objects are connected through an edge if they appear together
        in at least one feature (i.e. an atom from the precondition, the add list or the
        delete list). This graph gives an idea on how "distant" objects are from each other.

        Return
        ------
        out: UndirectedGraph
            an udirected graph G = <V,E> in which V is the set of objects referenced by
            this action and E is the set of all (u,v) pairs s.t. u,v appear together
            in at least one atom.
        """
        nodes = self.get_referenced_objects()
        edges = []
        for f in self.get_features():
            for idx,u in enumerate(f[1:], 1):
                for v in f[idx+1:]:
                    edges.append((u,v))
        return UndirectedGraph(nodes, edges)

    def get_precondition_scores(self):
        """
        Calculates a score for each atom in the precondition that gives an idea of
        how "distant" or unrelated they are to the effects.

        Return
        ------
        out: list
            the list of scores (Int) assigned to the preconditions, in order of
            appearance. The larger the score, the more unrelated the precondition
            atom is to the effect.
        """
        effect_objects = self.get_referenced_objects(sections=["add", "del"])
        object_graph = self.get_object_graph()
        object_scores = object_graph.bfs(effect_objects)
        return [min(object_scores[o] for o in f[1:]) for f in self.pre_list]

    def get_referenced_objects(self, sections=None):
        """
        Objects referenced by this action.

        Parameters
        ----------
        sections: list or None
            The sections to check for objects.

        Return
        ------
        out: list
            list of strings, the names of the objects represented by this action.
        """
        sections = sections or ["pre", "add", "del"]
        objects = set()
        for f in self.get_features(sections=sections):
            objects.update(f[1:])
        return list(objects)

    def get_parameters(self):
        """
        List of lifted objects referenced by this action (i.e. those that are meant
        to be substituted by ground objects).

        Return
        ------
        out: list
            list of strings containing the lifted objects.
        """
        # we sort the parameters so there is some canonical ordering
        parameters = sorted(filter(is_lifted, self.get_referenced_objects()))
        return parameters

    def get_features(self, sections=None):
        """
        Joins together all the atoms present in the precondition, the add list and the
        delete list, prefixing "pre_", "add_" or "del_", accordingly, to the head of
        the atom (i.e. the name of the predicate).

        Parameters
        ----------
        sections: list
            The list of sections to join. If None, all the sections are checked.
            If a list is provided, it should contain "pre", "add", "del".
        """
        sections = sections or ["pre", "add", "del"]
        for section in sections:
            for head,*tail in getattr(self, f"{section}_list"):
                yield (f"{section}_{head}",*tail)

    def filter_preconditions(self, max_pre_score, pre_scores=None):
        """
        Computes an new action with the same effect as this one, but with
        some atoms from the precondition filtered out.

        Parameters
        ----------
        max_pre_score: Int
            Score threshold. Retain atoms whose score is less than or equal to
            this value. See get_precondition_scores to learn more about the scores.
        pre_scores: list or None
            Score vector. If the scores have already been calculated via
            get_precondition_scores, they can be provided here to avoid recomputing them.
            If None is given, get_precondition_scores is called internally.

        Return
        ------
        out: Action
            New action with same effects and filtered preconditions.
        """
        pre_scores = pre_scores or self.get_precondition_scores()
        name = action_id_gen()
        pre_list = [f for s,f in zip(pre_scores, self.pre_list) if s <= max_pre_score]
        add_list = self.add_list[:] # copy added atoms
        del_list = self.del_list[:] # copy deleted atoms
        return Action(name, pre_list, add_list, del_list)


    def get_effect_label_count(self):
        """
        Count the number of occurrences of each predicate in the add and delete lists.

        Return
        ------
        out: dict
            A dict from string to Int that maps add/delete feature name to
            the number of occurrences in the effects.
        """
        effect_label_count = {}
        for label,*_ in self.get_features(["add", "del"]):
            effect_label_count[label] = effect_label_count.get(label,0) + 1
        return effect_label_count

    @staticmethod
    def from_transition(s, s_next, lifted=False):
        """
        Static constructor that takes two states that are interpreted as successive
        and builds an action that describes the transition.

        Parameters
        ----------
        s: set
            State represented as a collection of tuples (atom). Each tuple is a fact
            or fluent that holds in the situation represented by the state.
        s_next: set
            State after the transition
        lifted: Bool
            If True, then all the objects involved in the transition are lifted. That is,
            the referenced objects are replaced by a lifted variable of the form ?x[id].
        """
        name = action_id_gen()
        pre = list(s)
        add_eff = list(s_next.difference(s))
        del_eff = list(s.difference(s_next))
        if lifted:
            ref_dict = {}
            pre = [lift_atom(a, ref_dict) for a in pre]
            add_eff = [lift_atom(a,ref_dict) for a in add_eff]
            del_eff = [lift_atom(a, ref_dict) for a in del_eff]
        return Action(name, pre, add_eff, del_eff)

    def cluster_broadphase(self, other):
        """
        Simply compares the number of predicates of each type in the effects of
        action0 and action1 to make sure that they can be joined
        """
        return self.get_effect_label_count() == other.get_effect_label_count()

    def __str__(self):
        name = self.name
        par_str = " ".join(self.get_parameters())
        pre_str = ", ".join(map(tuple_to_str, self.pre_list))
        add_str = ", ".join(map(tuple_to_str, self.add_list))
        del_str = ", ".join(map(tuple_to_str, self.del_list))
        return  "Action {\n"\
               f"  name: {name}\n"\
               f"  parameters: {par_str}\n"\
               f"  precondition: {pre_str}\n"\
               f"  add list: {add_str}\n"\
               f"  del list: {del_str}\n"\
                "}"

    def to_pddl(self):
        name = self.name
        par_str = " ".join(self.get_parameters())
        pre_str = " ".join(map(tuple_to_str, self.pre_list))
        add_str = " ".join(map(tuple_to_str, self.add_list))
        del_str = ")(not ".join(map(tuple_to_str, self.del_list))
        return f"(:action {name}\n"\
               f"  parameters: ({par_str})\n"\
               f"  precondition: (and {pre_str})\n"\
               f"  effect: (and {add_str} (not {del_str}) )\n"\
                ")"


class ActionCluster:
    """
    Represents the union of two actions.

    Parameters
    ----------
    left: Action
        first action in the merging operation
    right: Action
        second action in the merging operation
    down: Action
        result of the union
    distance: numeric (i.e. int, float)
        score that measures how distant left is from right
    """

    def __init__(self, left, right, down, distance):
        self.name = cluster_id_gen()
        self.left = left
        self.right = right
        self.down = down
        self.distance = distance
