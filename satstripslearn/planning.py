import os
import subprocess
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


