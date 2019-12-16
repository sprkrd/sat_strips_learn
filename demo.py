#!/usr/bin/env python3

from z3 import *

from itertools import permutations


def generateAllPredicates(predicate_signatures, objects):
    predicates = []
    for pred, arity in predicate_signatures:
        for args in permutations(objects, arity):
            predicates.append((pred, *args))
    return predicates


def extractInfo(traces):
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
    return predicate_signatures, static_predicates, objects


def setProblem(traces, action_v, timesteps):
    predicate_signatures, static_predicates, objects = extractInfo(traces)
    max_arity = max(action_v)
    solution = []
    for action_idx, action_arity in enumerate(action_v):
        solution.append({})
        for predicate, pred_arity in predicate_signatures:
            for section in ("pre", "add", "del"):
                for slots in permutations(range(action_arity), pred_arity):
                    var_name = "a{:02}_{}_{}".format(action_idx, section, predicate)
                    if slots:
                        var_name += "_" + "_".join("slot{}".format(s) for s in slots)
                    solution[action_idx][var_name] = Bool(var_name)
    for action_idx, action in enumerate(solution):
        print("a{:02}:".format(action_idx))
        print("  "+"\n  ".join(sorted(action.keys())))

    # for predicate in generateAllPredicates(predicate_signatures, objects):
        # pass


def main():
    from example_traces import traces
    setProblem(traces, [2, 2, 3], 10)


if __name__ == "__main__":
    main()





