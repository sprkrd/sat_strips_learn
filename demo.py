#!/usr/bin/env python3

from z3 import *

from itertools import permutations


def generateAllPredicates(predicate_signatures, objects):
    predicates = []
    for pred, arity in predicate_signatures:
        for args in permutations(objects, arity):
            predicates.append((pred, *args))
    return predicates


def setProblem(traces):
    predicate_signatures = set()
    objects = set()
    for trace in traces:
        for state in trace:
            for predicate in state:
                predicate_signatures.add((predicate[0], len(predicate)-1))
                for obj in predicate[1:]:
                    objects.add(obj)
    for pred,arity in predicate_signatures:
        print("{}/{}".format(pred,arity))
    print(objects)
    print(generateAllPredicates(predicate_signatures, objects))


def main():
    from example_traces import traces
    setProblem(traces)


if __name__ == "__main__":
    main()





