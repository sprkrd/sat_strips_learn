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
                objects.update(predicate[1:])
    static_predicates = predicate_signatures.copy()
    for trace in traces:
        for state, state_next in zip(trace, trace[1:]):
            changed = state.symmetric_difference(state_next)
            for predicate in changed:
                static_predicates.discard((predicate[0], len(predicate)-1))
    print("Predicate signatures")
    for pred,arity in predicate_signatures:
        print("{}/{}".format(pred,arity))
    print("Static predicates")
    for pred,arity in static_predicates:
        print("{}/{}".format(pred,arity))
    print(objects)
    print(generateAllPredicates(predicate_signatures, objects))


def main():
    from example_traces import traces
    setProblem(traces)


if __name__ == "__main__":
    main()





