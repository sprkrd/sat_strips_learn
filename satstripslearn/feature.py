# Author: Alejandro S.H.

"""
This module defines the Feature class and supporting variable(s).
"""


from .utils import replace, atom_to_str


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
    >>> Feature(("on", "?x", "a"), certain=True, feature_type="pre")
    Feature{atom=on(?x,a), certain=True, feature_type=pre}
    >>> Feature(("on", "?x", "a"), certain=True, feature_type="pro")
    Traceback (most recent call last):
        ...
    ValueError: Unrecognized feature type: pro. The available types are defined in FEATURE_TYPES.
    """
    def __init__(self, atom, certain=True, feature_type="pre"):
        """
        See help(type(self))
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
        >>> f = Feature(("on", "?x", "?y"), certain=False, feature_type="add")
        >>> sigma = {"?x": "a", "?y": "b"}
        >>> f.replace(sigma)
        Feature{atom=on(a,b), certain=False, feature_type=add}
        """
        return Feature(replace(self.atom, sigma), self.certain, self.feature_type)

    def __str__(self):
        return f"{{atom={atom_to_str(self.atom)}, certain={self.certain}, feature_type={self.feature_type}}}"

    def __repr__(self):
        return f"Feature{str(self)}"


if __name__ == "__main__":
    import doctest
    doctest.testmod()
