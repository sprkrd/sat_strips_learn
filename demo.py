#!/usr/bin/env python3

from z3 import *

from itertools import permutations, product


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


def solvar(action_idx, section, predicate, *slots):
    var_name = "a{:02}_{}_{}".format(action_idx, section, predicate)
    if slots:
        var_name += "_" + "_".join("slot{}".format(s) for s in slots)
    return var_name


def slotvar(slot_idx, obj, trace_idx, time_step):
    return "slot{}_{}_tr{:02}_ts{:02}".format(slot_idx, obj, trace_idx, time_step)


def actvar(action_idx, trace_idx, time_step):
    return "exec_a{:02}_tr{:02}_ts{:02}".format(action_idx, trace_idx, time_step)


def setProblem(traces, action_v, timesteps):
    predicate_signatures, static_predicates, objects = extractInfo(traces)
    max_arity = max(action_v)

    # generate solution variables
    solution = [{} for _ in range(len(action_v))]
    for action_idx, action_arity in enumerate(action_v):
        for predicate, pred_arity in predicate_signatures:
            for section in ("pre", "add", "del"):
                for slots in permutations(range(action_arity), pred_arity):
                    var_name = solvar(action_idx, section, predicate, *slots)
                    solution[action_idx][var_name] = Bool(var_name)
    for action_idx, action in enumerate(solution):
        print("a{:02}:".format(action_idx))
        print("  "+"\n  ".join(sorted(action.keys())))

    # generate action variables (one per timestep)
    action_vars = {}
    for idx, tr, ts in product(range(len(action_v)), range(len(traces)), range(timesteps)):
        var_name = actvar(idx, tr, ts)
        action_vars[var_name] = Bool(var_name)
    print(sorted(action_vars.keys()))

    # generate slot variables
    slot_variables = {}
    for slot_idx, obj, tr, ts in product(range(max_arity), objects, range(len(traces)), range(timesteps)):
        var_name = slotvar(slot_idx, obj, tr, ts)
        slot_variables[var_name] = Bool(var_name)
    print(sorted(slot_variables.keys()))

    # for section in ("pre", "add"):
        # for (predicate, pred_arity), tr, ts in product(predicate_signatures, range(len(traces)), range(timesteps)):
            # for action_idx, act_arity in enumerate(action_v):





def main():
    from example_traces import traces
    setProblem(traces, [2, 2, 3], 10)


if __name__ == "__main__":
    main()





