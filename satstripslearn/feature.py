"""
This module defines the Feature class and supporting variable(s).
"""


from .utils import replace, lift_atom, atom_to_str, is_lifted


FEATURE_TYPES = ["pre", "add", "del"]


class Feature:
    """
    Features are known as labeled predicates in our AAAI article. The name
    "Feature" comes from an analogy between our action unification work
    and Champin and Solnon's contribution (Measuring the similarity of labeled
    graphs, International Conference on Case-Based Reasoning, 2003). In the latter,
    they refer to node and edge labels as features. Pedicates, or atoms as we
    call them in our implementation, can be seen as labeled hyperedges
    connecting the planning objects. Thus we use the term "Feature" to
    denote labeled atoms.

    Features consist of a regular atom, the section of the action they
    belong to (i.e. either the precondition, the add list or the delete list),
    and a boolean variable telling whether the predicate is known to belong for
    sure to the action's section.

    Parameters
    ----------
    atom : tuple
        atomic formula or predicate represented as a tuple whose first member
        is the role of the atom (predicate name) and the rest are its arguments.
    certain : Bool
        whether this labeled predicate is known to belong with certainty to
        the action's section where it appears. Default value: True
    feature_type : str
        one of the values in the FEATURE_TYPES list defined globally
        in this module (i.e. either "pre", "add", or "del"). Default value: "pre"

    Attributes
    ----------
    atom : tuple
        same as the value passed as parameter
    certain : Bool
        same as the value passed as parameter
    feature_type : str
        same as the falue passed as parameter

    Raises
    ------
    ValueError
        If the feature type is not one from FEATURE_TYPES

    Example
    -------
    >>> Feature(("on", "X", "a"), certain=True, feature_type="pre")
    Feature{atom=on(X,a), certain=True, feature_type=pre}
    >>> Feature(("on", "X", "a"), certain=True, feature_type="pro")
    Traceback (most recent call last):
        ...
    ValueError: Unrecognized feature type: pro. The available types are defined in FEATURE_TYPES.
    """
    def __init__(self, atom, certain=True, feature_type="pre"):
        """
        See help(type(self)).
        """
        if feature_type not in FEATURE_TYPES:
            raise ValueError(f"Unrecognized feature type: {feature_type}. "
                             f"The available types are defined in FEATURE_TYPES.")
        self.atom = atom
        self.certain = certain
        self.feature_type = feature_type

    @property
    def head(self):
        """
        Shortcut for getting the atom's role (predicate name).

        Returns
        ------
        head : str
            self.atom[0]

        Example
        -------
        >>> f = Feature(("on", "a", "b"))
        >>> f.head
        'on'
        """
        return self.atom[0]

    @property
    def arguments(self):
        """
        Shortcut for getting the atom's arguments.

        Returns
        -------
        arguments : tuple
            self.atom[1:]

        Example
        -------
        >>> f = Feature(("on", "a", "b"))
        >>> f.arguments
        ('a', 'b')
        """
        return self.atom[1:]

    def replace(self, sigma):
        """
        Convenience method for constructing a new Feature based on self
        substituting all the object references from a given substitution.

        Parameters
        ----------
        sigma : dict
            A dictionary from objects (str) to objects (str). The key is the
            object to be replaced, and the value is the value to replace with.

        Returns
        -------
        repl_feat : Feature
            New feature with all the references that appear in sigma replaced
            with their corresponding value. The certainty and type of the feature
            are maintained.

        Example
        -------
        >>> f = Feature(("on", "X", "Y"), certain=False, feature_type="add")
        >>> sigma = {"X": "a", "Y": "b"}
        >>> f.replace(sigma)
        Feature{atom=on(a,b), certain=False, feature_type=add}
        """
        return Feature(replace(self.atom, sigma), self.certain, self.feature_type)

    def lift_atom(self, ref_dict):
        self.atom = lift_atom(self.atom, ref_dict)
        
    def is_ground(self):
        return not any(map(is_lifted, self.atom[1:]))

    def __hash__(self):
        return hash((self.atom,self.feature_type,self.certain))

    def __eq__(self, other):
        return (self.atom,self.feature_type,self.certain) == (other.atom,other.feature_type,other.certain)

    def __str__(self):
        ret = atom_to_str(self.atom)
        if not self.certain: ret += "?"
        return ret

    def __repr__(self):
        return f"Feature{{atom={atom_to_str(self.atom)}, certain={self.certain}, feature_type={self.feature_type}}}"


if __name__ == "__main__":
    import doctest
    doctest.testmod()
