
ACTION_SECTIONS = ["pre", "add", "del"]


class LabeledAtom:
    """
    Labeled atoms are known as labeled predicates in our AAAI article.

    A LabeledAtom consist of (1) a regular strips.Atom; (2) the section of the
    action it belongs to (i.e. either the precondition, the add list or the delete list),
    and a boolean flag 

    Parameters
    ----------
    atom : Atom
        STRIPS predicate variable (from the .strips module)
    certain : bool
        Whether this labeled predicate is known to belong with certainty to
        the specified action section.
    section : str
        one of the values in the ACTION_SECTIONS list defined globally
        in this module (i.e. either "pre", "add", or "del"). Default value: "pre"

    Attributes
    ----------
    atom : Atom
        same as the value passed as parameter
    certain : Bool
        same as the value passed as parameter
    section : str
        same as the falue passed as parameter

    Raises
    ------
    ValueError
        If the LabeledAtom type is not one from sectionS

    """
    def __init__(self, atom, certain=True, section="pre"):
        """
        See help(type(self)).
        """
        if section not in sectionS:
            raise ValueError(f"Unrecognized LabeledAtom type: {section}. "
                             f"The available types are defined in sectionS.")
        self.atom = atom
        self.certain = certain
        self.section = section

    def replace(self, sigma):
        """
        Convenience method for constructing a new LabeledAtom based on self
        substituting all the object references from a given substitution.

        Parameters
        ----------
        sigma : dict
            An Object->Object dictionary. The key is the
            object to be replaced, and the value is the value to replace with.

        Returns
        -------
        repl_atom : LabeledAtom
            New LabeledAtom with all the references that appear in sigma replaced
            with their corresponding value. The certain flag and the section of
            the LabeledAtom are maintained.

        """
        return LabeledAtom(self.atom.replace(sigma), self.certain, self.section)
        
    def to_str(self, fmt="default", typing=True):
        ret = self.atom.to_str(fmt, typing)
        if not self.certain:
            ret = "?" + ret
        ret = self.section + ":" + ret
        return ret

    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return f"LabeledAtom({self})"


class Action:
    """
    Represents a STRIPS action. The class presents several utility method to
    facilitate clustering.

    Parameters
    ----------
    name : str
        name identifying the action
    features : list
        list of Feature objects, each one representing a labeled predicate
        (i.e. a predicate that appears in the add list, the delete list,
        or the precondition of this action)
    parent : ActionCluster
        should this Action be the result of merging two actions, this parameter
        must point to the cluster that represents this union (see ActionCluster).
        Usually this is not filled by the user, but by the cluster method.
    parameters_in_canonical_order : list
        If the parameters should appear in some particular order, this parameter
        should list them (as str) in the desired order.

    Attributes
    ----------
    name : str
        same as the value passed as parameter
    features : list
        same as the value passed as parameter
    parent : ActionCluster
        same as the value passed as parameter
    """

    def __init__(self, name, features, parent=None, parameters_in_canonical_order=None):
        """
        See help(type(self)).
        """
        self.name = name
        self.features = features
        self.parent = parent
        self._parameters_in_canonical_order = parameters_in_canonical_order
        self._cached_grouped_features = {feat_type: [] for feat_type in FEATURE_TYPES}
        for idx, feat in enumerate(features):
            self._cached_grouped_features[feat.feature_type].append((idx, feat))

    def get_features_of_type(self, feature_type):
        features = [feat for _,feat in self.get_grouped_features()[feature_type]]
        # we sort the features to have a canonical order
        features.sort(key=lambda feat: feat.atom)
        return features

    def get_grouped_features(self):
        """
        Returns features grouped by feature type and enumerated according to
        their position in self.features.

        Returns
        -------
        grouped_features : dict
            A dict from feature types (str) to lists. The lists contains
            (int, Feature) tuples. The Int is the position in which the feature
            appears in self.features (so it can be used to uniquely identify
            the feature *within* this action).
        """
        return self._cached_grouped_features

    def get_referenced_objects(self, feature_types=None, as_set=False):
        """
        Extracts the set of objects referenced by this action.

        Parameters
        ----------
        feature_types : iterable or None
            A (sub)set of FEATURE_TYPES, the type(s) of the features where this
            method must look into in the search for objects.
        as_set : bool
            Indicates whether to return the result as a set (True) or as a list (False)

        Returns
        -------
        objects : list or set
            List of strings, the names of the objects represented by this action.
        """
        feature_types = feature_types or FEATURE_TYPES
        grouped_features = self.get_grouped_features()
        objects = set()
        for feat_type in feature_types:
            for _, feat in grouped_features[feat_type]:
                objects.update(feat.arguments)
        return objects if as_set else list(objects)

    def get_parameters(self):
        """
        List of lifted objects referenced by this action (i.e. those that are meant
        to be substituted by constants when instantiating the action).

        Returns
        -------
        parameters : list
            list of strings containing the lifted objects.
        """
        if self._parameters_in_canonical_order is not None:
            return self._parameters_in_canonical_order
        # we sort the parameters so there is some canonical ordering
        parameters = sorted(filter(is_lifted, self.get_referenced_objects()))
        return parameters

    def get_role_count(self, feature_types=None, include_uncertain=True):
        """
        Count the number of occurrences of each feature *role* (i.e. the head
        of the feature) of the given feature_types.

        Parameters
        ----------
        feature_types : iterable or None
            A (sub)set of FEATURE_TYPES, the type(s) of the features that this
            method should consider.
        include_uncertain : Bool
            Whether or not to count uncertain_features

        Returns
        -------
        out : dict
            A dict from strings representing the name of the feature type to
            another dict. The value dict goes from strs (role name) to Ints
            (occurrence count).

        Examples
        --------
        >>> ex = Action("example", [
        ...     Feature(("p", "x", "y"), feature_type="pre"),
        ...     Feature(("p", "a", "b"), feature_type="add"),
        ...     Feature(("p", "s", "t"), feature_type="add"),
        ...     Feature(("p", "x", "y"), feature_type="del"),
        ...     Feature(("q",), feature_type="del")])
        >>> sorted(ex.get_role_count().items())
        [('p', 4), ('q', 1)]
        >>> sorted(ex.get_role_count(["pre", "add"]).items())
        [('p', 3)]
        """
        feature_types = feature_types or FEATURE_TYPES
        grouped_features = self.get_grouped_features()
        role_count = {}
        for feat_type in feature_types:
            for _, feat in grouped_features[feat_type]:
                if feat.certain or include_uncertain:
                    try:
                        role_count[feat.head] += 1
                    except KeyError:
                        role_count[feat.head] = 1
        return role_count

    def replace_references(self, sigma, name=None):
        """
        Creates and returns a new action with some objects replaced by others.

        Parameters
        ----------
        sigma : dict
            A substitution, represented as a dictionary from source objects
            (strs) to destination objects (also strs).
        name : str
            Name for the newly created action.
        """
        name = name or action_id_gen()
        features = [feat.replace(sigma) for feat in self.features]
        return Action(name, features, parent=self.parent)
        
    def can_produce_transition(self, pre_state, post_state):
        for action in self.all_instantiations(pre_state):
            state_after = action.apply(pre_state)
            if state_after == post_state:
                return True
        return False
            
    def apply(self, state):
        assert not state.is_uncertain(), "State must be completely certain"
        state = state.copy()
        for feat in self.features:
            assert feat.is_ground() and feat.certain, "Action must be completely ground, and all features must be certain, in order to be applicable"
            if feat.feature_type == "pre":
                if feat.atom not in state.atoms:
                    return None
            elif feat.feature_type == "add":
                state.atoms.add(feat.atom)
            else:
                state.atoms.discard(feat.atom)
        return state
        
    def all_instantiations(self, state):
        assert not state.is_uncertain() and all(feat.certain for feat in self.features), "This functionality only works with full certainty"
        grouped_features = self.get_grouped_features()
        pre = [feat.atom for _,feat in grouped_features["pre"]]
        for sigma in goal_match(state.atoms, pre):
            yield self.instantiate(sigma)
        
    def instantiate(self, args, include_uncertain=False):
        """
        Creates and returns a new action with some objects replaced by others.
        Maintains same name as self (as the resulting action is an instantiation
        of this one), and offers the possibility to include or not uncertain
        features.

        Parameters
        ----------
        args : iterable or dict
            Arguments. If an iterable is given, the arguments should appear in the same
            order as self.get_parameters().
        include_uncertain : bool
            Whether or not to include uncertain features
        """
        if isinstance(args, dict):
            sigma = args
        else:
            sigma = dict(zip(self.get_parameters(), args))
        features = [feat.replace(sigma) for feat in self.features if feat.certain or include_uncertain]
        return Action(self.name, features, parent=self.parent)

    def get_object_graph(self):
        """
        Constructs an undirected graph in which the referenced objects act as
        vertices. Two objects are connected through an edge if they appear
        together in at least one predicate (i.e. an atom from the precondition,
        the add list or the delete list). This graph gives an idea on how
        "distant" objects are from each other.

        Returns
        -------
        out : UndirectedGraph
            an undirected graph G = <V,E> in which V is the set of objects referenced by
            this action and E is the set of all (u,v) pairs s.t. u,v appear together
            in at least one atom.
        """
        nodes = self.get_referenced_objects()
        edges = set()
        for feat in self.features:
            for idx,u in enumerate(feat.arguments):
                for v in feat.arguments[idx+1:]:
                    if u < v:
                        edges.add((u,v))
                    elif v < u:
                        edges.add((v,u))
                    else:
                        # don't do self-edges!
                        pass
        return UndirectedGraph(nodes, edges)

    def get_object_scores(self):
        """
        Computes a score for each object (both parameters and constants)
        referenced by this action.

        Returns
        -------
        scores : dict
            a dict from strings (each representing an object) to ints (the score
            value). The score represents a sort of relevance of an
            object. The maximum possible score is 0. All affected objects (i.e.
            those in the effects) have a score of 0. The rest have a negative
            score based on the distance to the effect objects.
        """
        effect_objects = self.get_referenced_objects(feature_types=["add", "del"])
        object_graph = self.get_object_graph()
        object_scores = {k:-v for k,v in object_graph.bfs(effect_objects).items()}
        return object_scores

    def get_feature_scores(self, fn=sum, **kwargs):
        """
        Calculates a score for each feature that gives an idea of
        how "distant" or unrelated they are to the effects. It receives an
        aggregation function to combine the individual scores of each
        feature's arguments. See help(self.get_object_scores).

        Parameters
        ----------
        fn : callable
            Function that should map tuples of feature scores to a single
            scores (i.e. (int,int,...) -> int)
        **kwargs : any
            Additional parameters for the fn function.

        Returns
        -------
        out : list
            the list of scores (Ints), with out[i] being the score assigned to
            self.features[i]. The scores are either 0 for the effects and,
            possibly, some preconditions, and negative for the rest of
            preconditions.
        """
        object_scores = self.get_object_scores()
        return [fn(tuple(object_scores[o] for o in feat.arguments), **kwargs)
                 for feat in self.features]

    def filter_features(self, min_score, name=None, fn=sum, **kwargs):
        """
        Computes an new action with the same effect as this one, but with
        some atoms from the precondition filtered out.

        Parameters
        ----------
        min_score : int
            Score threshold. Retain atoms whose score is greater than or equal to
            this value. See get_feature_scores to learn more about the scores.
        name : list or None
            The name that will be given to the newly created action.
        fn : callable
            See help(self.get_feature_scores) to learn more about this parameter.
        **kwargs : any
            Additional parameters for the fn function.

        Returns
        -------
        out: Action
            New action with same effects and filtered preconditions.
        """
        name = name or action_id_gen()
        feat_scores = self.get_feature_scores(fn, **kwargs)
        features = [feat for feat,score in zip(self.features, feat_scores) if score >= min_score]
        return Action(name, features, parent=self.parent)

    def cluster_broadphase(self, other):
        """
        Simply compares the number of predicates of each type in the effects of
        self and another action to make sure that they may be potentially
        clustered. This is a very easy check before bringing the big guns
        and trying to cluster the actions.

        Examples
        --------
        >>> a = Action("a", [
        ...     Feature(("p","x"), feature_type="add", certain=True),
        ...     Feature(("p","y"), feature_type="add", certain=False),
        ...     Feature(("p","s"), feature_type="del", certain=True),
        ...     Feature(("p","t"), feature_type="del", certain=True),
        ...     Feature(("p","u"), feature_type="del", certain=False)])
        >>> b = Action("b", [
        ...     Feature(("p","x"), feature_type="add", certain=True),
        ...     Feature(("p","y"), feature_type="add", certain=True),
        ...     Feature(("p","t"), feature_type="del", certain=False),
        ...     Feature(("p","u"), feature_type="del", certain=False)])
        >>> c = Action("c", [
        ...     Feature(("p","x"), feature_type="add", certain=True),
        ...     Feature(("p","y"), feature_type="add", certain=True),
        ...     Feature(("p","u"), feature_type="del", certain=False)])
        >>> a.cluster_broadphase(b)
        True
        >>> a.cluster_broadphase(c)
        False
        >>> b.cluster_broadphase(c)
        True
        """
        # TODO Which option is more appropriate? Leaving this functionality
        # as a method of Action or putting it as a standalone function?
        if not dict_leq(self.get_role_count(("add",),False), other.get_role_count(("add",))):
            return False
        if not dict_leq(self.get_role_count(("del",),False), other.get_role_count(("del",))):
            return False
        if not dict_leq(other.get_role_count(("add",),False), self.get_role_count(("add",))):
            return False
        if not dict_leq(other.get_role_count(("del",),False), self.get_role_count(("del",))):
            return False
        return True

    @staticmethod
    def from_transition(s, s_next, lifted=False, name=None):
        """
        Static constructor that takes two states that are interpreted as successive
        and builds an action that describes the transition.

        Parameters
        ----------
        s : State
            State before the transition
        s_next : State
            State after the transition
        lifted : Bool
            If True, then all the objects involved in the transition are lifted. That is,
            the referenced objects are replaced by a lifted variable of the form ?x[id].

        Examples
        --------
        >>> s1 = State({("a",), ("b",)}, {("c",), ("d",), ("e",)})
        >>> s2 = State({("a",), ("d",), ("f",)}, {("c",), ("e",)})
        >>> print(Action.from_transition(s1, s2, name="a"))
        Action{
          name = a,
          parameters = [],
          precondition = [a(), b(), c()?, d()?, e()?],
          add list = [c()?, d()?, e()?, f()],
          del list = [b(), c()?, e()?]
        }
        """
        name = name or action_id_gen()
        add_certain = s_next.difference(s)
        del_certain = s.difference(s_next)
        add_uncertain = s_next.difference(s, False)
        del_uncertain = s.difference(s_next, False)
        features = []
        for atom in s.atoms:
            features.append(Feature(atom, feature_type="pre"))
        for atom in s.uncertain_atoms:
            features.append(Feature(atom, feature_type="pre", certain=False))
        for atom in add_certain:
            features.append(Feature(atom, feature_type="add"))
        for atom in add_uncertain:
            features.append(Feature(atom, feature_type="add", certain=False))
        for atom in del_certain:
            features.append(Feature(atom, feature_type="del"))
        for atom in del_uncertain:
            features.append(Feature(atom, feature_type="del", certain=False))
        if lifted:
            ref_dict = {}
            for feat in features:
                feat.lift_atom(ref_dict)
        return Action(name, features)

    def __str__(self):
        name = self.name
        grouped_features = self.get_grouped_features()
        par_str = ", ".join(self.get_parameters())
        pre_str = ", ".join(str(feat) for feat in self.get_features_of_type("pre"))
        add_str = ", ".join(str(feat) for feat in self.get_features_of_type("add"))
        del_str = ", ".join(str(feat) for feat in self.get_features_of_type("del"))
        return  "Action{\n"\
               f"  name = {name},\n"\
               f"  parameters = [{par_str}],\n"\
               f"  precondition = [{pre_str}],\n"\
               f"  add list = [{add_str}],\n"\
               f"  del list = [{del_str}]\n"\
                "}"

    def __repr__(self):
        return f"Action{{name={self.name}, {len(self.features)} features}}"

    def to_pddl(self, include_uncertain=True):
        name = self.name
        grouped_features = self.get_grouped_features()
        par_str = " ".join(map(prolog_to_pddl,self.get_parameters()))
        pre_str = " ".join(atom_to_pddl(feat.atom)
            for feat in self.get_features_of_type("pre") if feat.certain or include_uncertain)
        add_str = " ".join(atom_to_pddl(feat.atom)
            for feat in self.get_features_of_type("add") if feat.certain or include_uncertain)
        del_str = " ".join(f"(not {atom_to_pddl(feat.atom)})"
            for feat in self.get_features_of_type("del") if feat.certain or include_uncertain)
        return f"(:action {name}\n"\
               f"  parameters: ({par_str})\n"\
               f"  precondition: (and {pre_str})\n"\
               f"  effect: (and {add_str} {del_str})\n"\
                ")"

    def to_latex(self):
        name = self.name
        grouped_features = self.get_grouped_features()
        par_str = ", ".join(self.get_parameters())
        pre_str = ", ".join(str(feat) for feat in self.get_features_of_type("pre"))
        add_str = ", ".join(str(feat) for feat in self.get_features_of_type("add"))
        del_str = ", ".join(str(feat) for feat in self.get_features_of_type("del"))
        lines = [
                r"\begin{flushleft}",
                fr"\underline{{{name.capitalize()}({par_str}):}}\\",
                fr"\texttt{{Pre:}} \nohyphens{{{pre_str}}}\\",
                fr"\texttt{{Add:}} \nohyphens{{{add_str}}}\\",
                fr"\texttt{{Del:}} \nohyphens{{{del_str}}}\\",
                r"\end{flushleft}"
        ]
        return "\n".join(lines)

