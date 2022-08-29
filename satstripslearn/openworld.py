from .strips import Action as StripsAction, Predicate
from .utils import dict_leq


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
        if section not in ACTION_SECTIONS:
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

    def to_str(self, show_section=True):
        ret = self.atom.to_pddl(True)
        if not self.certain:
            ret = ret + "?"
        if show_section:
            ret = self.section + ":" + ret
        return ret


    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return f"LabeledAtom({self})"


def wrap_predicate(head, *args):
    predicate = Predicate(head, *args)
    def f(*args, section="pre", certain=True):
        return LabeledAtom(predicate(*args), section=section, certain=certain)
    return f


class State:
    """
    Represents a symbolic state, that is, a collection of atomic facts
    (instantiated predicates) that describe the world. Partially observability
    is supported (or, alternatively, one could think about open world states),
    so some atoms can be specified as "may be true".

    Parameters
    ----------
    atoms : set
        Collection of predicate variables (strips.Atom) that are known to hold
        for sure.
    uncertain_atoms : set
        Also predicate variables (strips.Atom). These are not guaranteed to be
        true. It is assumed that the atoms and uncertain_atoms are disjoint
        sets, because a fact cannot be known and unknown at the same time.
        The caller is responsible to enforce this.
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

    def is_uncertain(self):
        return bool(self.uncertain_atoms)

    def copy(self):
        return State(self.atoms.copy(), self.uncertain_atoms.copy())

    def __eq__(self, other):
        if not isinstance(other, State):
            return NotImplemented
        return self.atoms == other.atoms and self.uncertain_atoms == other.uncertain_atoms

    def __str__(self):
        fst_part = ",".join(map(str, self.atoms))
        snd_part = ",".join(map(str, self.uncertain_atoms))
        return f"{{ {fst_part}; maybe {snd_part} }}"


class Action:
    """
    Represents an open world action.

    Parameters
    ----------
    name : str
        Name identifying the action
    parameters: list
        List of strips.Object, all of them variables, representing the parameters
        of the action. If set to None, the parameters are extracted from the
        labeled atoms.
    atoms : list
        List of LabeledAtom objects, each one representing a labeled predicate
        (i.e. a predicate that appears in the add list, the delete list,
        or the precondition of this action)

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

    def __init__(self, name, parameters=None, atoms=None):
        """
        See help(type(self)).
        """
        self.name = name
        self.atoms = atoms or []
        if parameters is None:
            self.parameters = [obj for obj in self.get_referenced_objects() if obj.is_variable()]
        else:
            self.parameters = parameters
            self._verify()

    def _verify(self):
        for param in self.parameters:
            if not param.is_variable():
                assert ValueError("Parameters must be variables")
        for atom in self.atoms:
            for arg in atom.atom.args:
                if arg.is_variable() and arg not in self.parameters:
                    raise ValueError(f"Variable {arg} is not present in the list of parameters")

    def to_strips(self, keep_uncertain=True):
        name = self.name
        parameters = self.parameters
        precondition = [atom.atom for atom in self.get_atoms_in_section(["pre"], keep_uncertain)]
        add_list = [atom.atom for atom in self.get_atoms_in_section(["add"], keep_uncertain)]
        del_list = [atom.atom for atom in self.get_atoms_in_section(["del"], keep_uncertain)]
        return StripsAction(name, parameters, precondition, add_list, del_list)

    def get_atoms_in_section(self, sections=None, include_uncertain=True):
        sections = sections or ACTION_SECTIONS
        return [atom for atom in self.atoms if atom.section in sections
                and (atom.certain or include_uncertain)]

    def get_referenced_objects(self, sections=None, include_uncertain=True, as_list=False):
        """
        Extracts the set of objects referenced by this action.

        Parameters
        ----------
        sections : iterable or None
            A (sub)set of ACTION_SECTIONS, the type(s) of the features where this
            method must look into in the search for objects.
        include_uncertain : bool
            Whether to include uncertain LabeledAtom's
        as_list : bool
            Indicates whether to return the result as a list (True) or as a set (False)

        Returns
        -------
        objects : set
            Set containing the Object instances found in the specified section's
            labeled atoms
        """
        objects = set()
        for atom in self.get_atoms_in_section(sections, include_uncertain):
            objects.update(atom.atom.args)
        if as_list:
            objects = list(objects)
        return objects

    @staticmethod
    def from_strips(strips_action):
        name = strips_action.name
        parameters = strips_action.parameters
        atoms = [LabeledAtom(atom, section="pre")
                for atom in strips_action.precondition]
        atoms += [LabeledAtom(atom, section="add")
                for atom in strips_action.add_list]
        atoms += [LabeledAtom(atom, section="del")
                for atom in strips_action.del_list]
        return Action(name, parameters, atoms)

    @staticmethod
    def from_transition(name, s, s_next, lifted=False):
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
        >>> from satstripslearn.strips import Predicate
        >>> A, B, C, D, E, F = [Predicate(p) for p in "abcdef"]
        >>> s1 = State({A(), B()}, {C(), D(), E()})
        >>> s2 = State({A(), D(), F()}, {C(), E()})
        >>> action = Action.from_transition("a", s1, s2)
        >>> action.atoms.sort(key=lambda atom: atom.atom.head)
        >>> print(action)
        Action{
          name = a,
          parameters = [],
          precondition = [(a), (b), (c)?, (d)?, (e)?],
          add list = [(c)?, (d)?, (e)?, (f)],
          del list = [(b), (c)?, (e)?]
        }
        """
        add_certain = s_next.difference(s)
        del_certain = s.difference(s_next)
        add_uncertain = s_next.difference(s, False)
        del_uncertain = s.difference(s_next, False)
        atoms = []
        for atom in s.atoms:
            atoms.append(LabeledAtom(atom, section="pre"))
        for atom in s.uncertain_atoms:
            atoms.append(LabeledAtom(atom, section="pre", certain=False))
        for atom in add_certain:
            atoms.append(LabeledAtom(atom, section="add"))
        for atom in add_uncertain:
            atoms.append(LabeledAtom(atom, section="add", certain=False))
        for atom in del_certain:
            atoms.append(LabeledAtom(atom, section="del"))
        for atom in del_uncertain:
            atoms.append(LabeledAtom(atom, section="del", certain=False))
        return Action(name, None, atoms)

    def __str__(self):
        name = self.name
        par_str = ", ".join(str(param) for param in self.parameters)
        pre_str = ", ".join(atom.to_str(False) for atom in self.get_atoms_in_section("pre"))
        add_str = ", ".join(atom.to_str(False) for atom in self.get_atoms_in_section("add"))
        del_str = ", ".join(atom.to_str(False) for atom in self.get_atoms_in_section("del"))
        return  "Action{\n"\
               f"  name = {name},\n"\
               f"  parameters = [{par_str}],\n"\
               f"  precondition = [{pre_str}],\n"\
               f"  add list = [{add_str}],\n"\
               f"  del list = [{del_str}]\n"\
                "}"

    def __repr__(self):
        return f"Action{{name={self.name}, {len(self.features)} features}}"

    def to_latex(self):
        name = self.name
        par_str = ", ".join(str(param) for param in self.parameters)
        pre_str = ", ".join(atom.to_str(False) for atom in self.get_atoms_in_section("pre"))
        add_str = ", ".join(atom.to_str(False) for atom in self.get_atoms_in_section("add"))
        del_str = ", ".join(atom.to_str(False) for atom in self.get_atoms_in_section("del"))
        lines = [
                r"\begin{flushleft}",
                fr"\underline{{{name.capitalize()}({par_str}):}}\\",
                fr"\texttt{{Pre:}} \nohyphens{{{pre_str}}}\\",
                fr"\texttt{{Add:}} \nohyphens{{{add_str}}}\\",
                fr"\texttt{{Del:}} \nohyphens{{{del_str}}}\\",
                r"\end{flushleft}"
        ]
        return "\n".join(lines)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
