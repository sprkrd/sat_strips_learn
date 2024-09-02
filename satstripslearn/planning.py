import os
import subprocess
import time
import math
from tempfile import NamedTemporaryFile as TempFile, TemporaryDirectory

from .strips import Problem


TEMP_DIR = TemporaryDirectory(prefix="planning_")
FD_PATH = os.getenv("FD_PATH")


def plan(problem, cleanup=True, timeout=None, bound=None):
    if FD_PATH is None:
        raise Exception("Can't find FD executable. Please, set the "
                "FD_PATH environment variable to the path of "
                "the fast-downward.py script.")

    domain_file = TempFile(mode="w", delete=cleanup,
            dir=TEMP_DIR.name, prefix="domain_", suffix=".pddl")
    problem_file = TempFile(mode="w", delete=cleanup,
            dir=TEMP_DIR.name, prefix="problem_", suffix=".pddl")
    last_plan_file = os.path.join(TEMP_DIR.name, "last_plan")
    cmd = [FD_PATH, "--plan-file", last_plan_file]
    cmd += [domain_file.name, problem_file.name]
    cmd.append("--search")
    astar_options = ["lmcut()"]
    if timeout is not None:
        astar_options.append(f"max_time={timeout}")
    if bound is not None:
        astar_options.append(f"bound={bound}")
    cmd.append("astar(" + ", ".join(astar_options) + ")")
    with domain_file, problem_file:
        problem.domain.dump_pddl(domain_file)
        problem.dump_pddl(problem_file)
        domain_file.flush()
        problem_file.flush()
        try:
            process = subprocess.run(cmd, check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            return None
    object_index = problem.object_index
    action_index = problem.domain.action_index
    result = []
    with open(last_plan_file, "r") as f:
        for line in f:
            if line.startswith(";"):
                continue
            parts = line.strip("() \n\t").split()
            action = action_index[parts[0]]
            args = [object_index[arg] for arg in parts[1:]]
            result.append(action.ground(*args))
    return result


class Solver:

    def __init__(self, problem, depth_limit=1000, timeout=None):
        self.problem = problem
        self.depth_limit = depth_limit
        self.timeout = math.inf if timeout is None else timeout
        self._search_end = False
        self._timeout_triggered = False
        self._start = None
        self._elapsed = None

    def find_all_optimum_plans(self):
        self.setup()
        plans = []
        while not self._timeout_triggered and not self._search_end:
            if self.do_iter():
                plans.append(self._plan)
            self._elapsed = time.time() - self._start
            self._timeout_triggered = self._elapsed >= self.timeout
        return plans

    def solve(self, timeout=None):
        self.setup()
        while not self._timeout_triggered and not self._search_end:
            if self.do_iter():
                return self._plan
            self._elapsed = time.time() - self._start
            self._timeout_triggered = self._elapsed >= self.timeout
        return None

    def setup(self):
        self._start = time.time()
        self._elapsed = 0
        self._search_end = False
        self._timeout_triggered = False

    def do_iter(self):
        raise NotImplementedError()


class IDSSolver(Solver):

    def __init__(self, problem, depth_limit=1000):
        super().__init__(problem, depth_limit)

    def setup(self):
        super().setup()
        initial_state = self.problem.get_initial_state()
        self._max_depth = 1
        self._stk = [(0, None, initial_state)]
        self._running_plan = []
        self._visited_states = [initial_state]

    def do_iter(self):
        problem = self.problem
        stk = self._stk
        running_plan = self._running_plan
        visited_states = self._visited_states

        depth, action, state = -1, None, None
        while stk:
            depth, action, state = stk.pop()
            if depth == -1:
                running_plan.pop()
                visited_states.pop()
            else:
                break

        if depth == -1:
            if self._max_depth < self.depth_limit:
                self._max_depth += 1
                stk.append((0, None, problem.get_initial_state()))
            else:
                self._search_end = True
            return False
        
        if action is not None:
            running_plan.append(action)
            stk.append((-1, None, None))

            
        if state.satisfies_condition(problem.goal):
            self._plan = running_plan.copy()
            self.depth_limit = depth
            return True

        if depth >= self._max_depth:
            return False

        for action in problem.domain.all_groundings(state):
            next_state = action.apply(state)
            if next_state not in visited_states:
                visited_states.append(next_state)
                stk.append((depth+1, action, action.apply(state)))

        return False


class BFSSolver(Solver):
    # TODO
    pass


def every_optimal_action(problem, cleanup=True, timeout=None,
        all_groundings=None, max_num_of_actions=1000):
    p = plan(problem, cleanup, timeout)
    if p is None:
        return None, -1
    elif len(p) == 0:
        return [], 0 # already at goal
    optimal_length = len(p)
    options = [p[0]]
    initial_state = problem.get_initial_state()
    if all_groundings is None:
        all_groundings = problem.domain.all_groundings(initial_state)
    for grounding in all_groundings:
        if grounding == options[0]:
            # avoids calling the planner one time
            continue
        ctx = grounding.apply(initial_state)
        modified_problem = Problem(problem.name, problem.domain,
                problem.objects, ctx.atoms, problem.goal)
        p = plan(modified_problem, cleanup, timeout,
                bound=optimal_length)
        if p:
            assert len(p) == optimal_length-1
            options.append(grounding)
        if len(options) == max_num_of_actions:
            break
    return options, optimal_length


def is_suboptimal(problem, a_g, cleanup=True, timeout=None):
    p = plan(problem, cleanup, timeout)
    if p is None:
        return False, a_g
    initial_state = problem.get_initial_state()
    ctx = a_g.apply(initial_state)
    modified_problem = Problem(problem.name, problem.domain,
            problem.objects, ctx.atoms, problem.goal)
    p_alt = plan(modified_problem, cleanup, timeout, bound=len(p))
    if p_alt:
        assert len(p_alt) == len(p) - 1
        return False, p[0]
    return True, p[0]


