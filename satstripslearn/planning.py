import os
import subprocess
import time
import math

from collections import deque
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

    def __init__(self, problem, depth_limit=1000, timeout=None, initial_state=None):
        self.problem = problem
        self.depth_limit = depth_limit
        self.timeout = math.inf if timeout is None else timeout
        self._search_end = False
        self._timeout_triggered = False
        self._start = None
        self._elapsed = None
        self._initial_state = initial_state or problem.get_initial_state()

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

    def set_depth_limit(self, depth_limit):
        self.depth_limit = depth_limit
        return self

    def set_timeout(self, timeout):
        self.timeout = timeout
        return self

    def set_initial_state(self, initial_state):
        self._initial_state = initial_state
        return self

    def get_elapsed(self):
        return self._elapsed


class IDSSolver(Solver):

    def __init__(self, *args, start_max_depth=1, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_max_depth = start_max_depth

    def find_all_optimum_plans(self):
        self.setup()
        plans = []
        while not self._timeout_triggered and not self._search_end:
            if self.do_iter():
                plans.append(self._plan)
            self._elapsed = time.time() - self._start
            self._timeout_triggered = self._elapsed >= self.timeout
        return plans

    def setup(self):
        super().setup()
        self._max_depth = self._start_max_depth
        self._stk = [(0, None, self._initial_state)]
        self._running_plan = []
        self._visited_states = [self._initial_state]

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
                stk.append((0, None, self._initial_state))
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setup(self):
        super().setup()
        self._parent = {}
        self._closed_set = set()
        self._open_set = deque()
        self._open_set.append((0, self._initial_state))

    def _reconstruct_plan(self, state):
        DEFAULT = (None, None)
        parent = self._parent
        plan = []
        action, state = parent.get(state, DEFAULT)
        while state is not None:
            plan.append(action)
            action, state = parent.get(state, DEFAULT)
        plan.reverse()
        return plan

    def do_iter(self):
        open_set = self._open_set
        closed_set = self._closed_set
        parent = self._parent
        problem = self.problem

        if not open_set:
            self._search_end = True
            return False
        
        depth, state = open_set.popleft()

        closed_set.add(state)

        if state.satisfies_condition(problem.goal):
            self._plan = self._reconstruct_plan(state)
            return True

        if depth >= self.depth_limit:
            return False

        for action in problem.domain.all_groundings(state):
            next_state = action.apply(state)
            if next_state not in closed_set:
                parent[next_state] = (action, state)
                open_set.append((depth+1, next_state))

        return False


def every_optimal_action(problem, time_budget=None, method="bfs"):
    if method == "bfs":
        Solver = BFSSolver
    else:
        Solver = IDSSolver
    
    if time_budget is None:
        time_budget = math.inf
    
    solver = Solver(problem,  timeout=time_budget)
    actions = []
    plan = solver.solve()

    if not plan: # plan is None or empty plan (already at goal)
        return actions

    optimum = plan[0]

    solver.set_depth_limit(len(plan)-1)

    actions.append(optimum)

    time_budget = time_budget - solver.get_elapsed()
    initial_state = problem.get_initial_state()
    for action in problem.domain.all_groundings(initial_state):
        if action != optimum:
            state = action.apply(initial_state)
            solver.set_initial_state(action.apply(initial_state)).set_timeout(time_budget)
            plan = solver.solve()
            if plan is not None:
                actions.append(action)
            time_budget -= solver.get_elapsed()
            if time_budget <= 0:
                break

    return actions
    

# def every_optimal_action(problem, cleanup=True, timeout=None,
        # all_groundings=None, max_num_of_actions=1000):
    # p = plan(problem, cleanup, timeout)
    # if p is None:
        # return None, -1
    # elif len(p) == 0:
        # return [], 0 # already at goal
    # optimal_length = len(p)
    # options = [p[0]]
    # initial_state = problem.get_initial_state()
    # if all_groundings is None:
        # all_groundings = problem.domain.all_groundings(initial_state)
    # for grounding in all_groundings:
        # if grounding == options[0]:
            # avoids calling the planner one time
            # continue
        # ctx = grounding.apply(initial_state)
        # modified_problem = Problem(problem.name, problem.domain,
                # problem.objects, ctx.atoms, problem.goal)
        # p = plan(modified_problem, cleanup, timeout,
                # bound=optimal_length)
        # if p:
            # assert len(p) == optimal_length-1
            # options.append(grounding)
        # if len(options) == max_num_of_actions:
            # break
    # return options, optimal_length


