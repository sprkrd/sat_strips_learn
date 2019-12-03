#!/usr/bin/env python3

from z3 import *


def setProblem(traces):
    predicates = set()
    objects = set()
    for trace in traces:
        for state in trace:
            for predicate in state:
                predicates.add((predicate[0], len(predicate)-1))
                for obj in predicate:
                    objects.add(obj)
    for pred,arity in predicates:
        print("{}/{}".format(pred,arity))
    print(objects)


def main():
    from example_traces import traces
    setProblem(traces)


if __name__ == "__main__":
    main()





