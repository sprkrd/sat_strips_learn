
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
    Represents an open world action.

    Parameters
    ----------
    name : str
        Name identifying the action
    atoms : list
        List of LabeledAtom objects, each one representing a labeled predicate
        (i.e. a predicate that appears in the add list, the delete list,
        or the precondition of this action)
    parent : ActionCluster
        Should this Action be the result of merging two actions, this parameter
        must point to the cluster that represents the parents (see ActionCluster).
        Usually this is not filled by the user, but by the cluster method.
    parameters: list
        List of strips.Object, all of them variables, representing the parameters
        of the action. If set to None, the parameters are extracted from the
        labeled atoms.

    Attributes
    ----------
    name : str
        same as the value passed as parameter
    atoms : list
        same as the value passed as parameter
    parent : ActionCluster
        same as the value passed as parameter
    parameters : list
        List of parameters of this action
    """

    def __init__(self, name, atoms, parent=None, parameters=None):
        """
        See help(type(self)).
        """
        self.name = name
        self.atoms = atoms
        self.parent = parent
        if parameters is None:
            parameters = set()
            for atom in atoms:
                parameters.update(atom.atom.args)
            parameters = list(parameters)
        self.parameters = parameters

    def get_referenced_objects(self, sections=None):
        """
        Extracts the set of objects referenced by this action.

        Parameters
        ----------
        sections : iterable or None
            A (sub)set of ACTION_SECTIONS, the type(s) of the features where this
            method must look into in the search for objects.
        as_set : bool
            Indicates whether to return the result as a set (True) or as a list (False)

        Returns
        -------
        objects : set
            Set containing the Object instances found in the specified section's
            labeled atoms
        """
        sections = sections or ACTION_SECTIONS
        objects = set()
        for atom in self.atoms:
            if atom.section in sections:
                objects.update(atom.atom.args)
        return objects

    def get_role_count(self, sections=None, include_uncertain=True):
        """
        Count the number of occurrences of each atom *role* (i.e. the head
        of the atom) of the given section(s).

        Parameters
        ----------
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
        for atom in self.atoms:
            if atom.section in sections and (atom.certain or include_uncertain):
                head = atom.atom.head
                role_count[head] = role_count.get(head, 0) + 1
        return role_count

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

