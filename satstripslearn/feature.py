from .utils import replace


FEATURE_TYPES = ["pre", "add", "del"]


class Feature:
    def __init__(self, atom, certain=True, feature_type="pre"):
        if feature_type not in FEATURE_TYPES:
            raise ValueError(f"Unrecognized feature type: {feature_type}. "
                             f"The available featres are: {', '.join(FEATURE_TYPES)}")
        self.atom = atom
        self.certain = certain
        self.feature_type = feature_type

    @property
    def head(self):
        return self.atom[0]

    @property
    def args(self):
        return self.atom[1:]

    def replace(self, sigma):
        return Feature(replace(self.atom, sigma), self.certain, self.feature_type)

    def __str__(self):
        return f"(({' '.join(self.atom)})   , certain={self.certain}, feature_type={self.feature_type})"

    def __repr__(self):
        return f"Feature({str(self)})"


if __name__ == "__main__":
    feat0 = Feature(("on", "a", "b"), certain=False, feature_type="pro")
    print(feat0)
    print(feat0.replace({"a": "?x1"}))
