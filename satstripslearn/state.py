from .utils import atom_to_str 


class State:
    """
    Represents a symbolic state, that is, a collection of atomic facts 
    (instantiated predicates) that describe the world. Partially observability
    is supported (or, alternatively, one could think about open world states),
    so some atoms can be specified as "may be true".

    Parameters
    ----------
    atoms : set
        Collection of facts (string tuples where the first member is the name
        of the role or predicate, and the rest is the arguments that instantiate
        it) that are known for sure.
    uncertain_atoms : set
        Same structure as atoms, but these are not guaranteed to be true. It
        is assumed that the atoms and uncertain_atoms are disjoint sets, because
        a fact cannot be known and unknown at the same time. The caller
        is responsible to enforce this.
    """

    def __init__(self, atoms, uncertain_atoms=None):
        """
        See help(type(self)).
        """
        self.atoms = atoms
        self.uncertain_atoms = uncertain_atoms or set()

    def difference(self, other, certain=True):
        """
        Computes the predicates that should be added to another given state to
        become this one.

        The difference can be computed in two modalities: (1) with full
        certainty, i.e. atoms that must be added for sure; and (2) with
        uncertainty, i.e. atoms that might have to be added.

        Parameters
        ----------
        other : State
            state that is compared to self
        certain : Bool
            if true, only the certain additions are returned, otherwise, only
            the uncertain additions are returned.

        Return
        ------
        out: set
            the set of atoms that should be added to make other equal to self
            (or that should be removed from other to become self).
        """
        if not certain:
            return (self.atoms&other.uncertain_atoms) |\
                   (self.uncertain_atoms-other.atoms)
        return self.atoms - other.atoms - other.uncertain_atoms

    def __str__(self):
        fst_part = ",".join(map(atom_to_str, self.atoms))
        snd_part = ",".join(map(atom_to_str, self.uncertain_atoms))
        return f"{{ {fst_part}; maybe {snd_part} }}"


if __name__ == "__main__":
    state1 = State({("a",), ("b",)}, {("c",), ("d",), ("e",)})
    state2 = State({("a",), ("d",), ("f",)}, {("c",), ("e",)})
    print(state1)
    print(state2)
    print(state2.difference(state1))
    print(state2.difference(state1, certain=False))
    print(state1.difference(state2))
    print(state1.difference(state2, certain=False))

