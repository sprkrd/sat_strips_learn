# Action Unification and OARU


## Preparation steps


This project uses pddlgym as a submodule. To clone, use

```
git clone --recurse-submodules https://github.com/sprkrd/sat_strips_learn.git
```

If you've already cloned the repository and you want to fetch the submodules
too, use

```
git submodule update --init --recursive
```

More info [here](https://git-scm.com/book/en/v2/Git-Tools-Submodules).

In order for PDDLGym to work with planner support, you must set the
`FF_PATH` env variable to the path of the [Fast Forward executable](https://fai.cs.uni-saarland.de/hoffmann/metric-ff.html).
You can also add the following to your `~/.bashrc`
```
export FF_PATH=/path/to/ff/executable
```

We recommend setting up a virtual environment for installing the dependencies:
```
virtualenv sat_strips_learn_venv -p python3
source sat_strips_learn_venv/bin/activate
pip install -r requirements.txt
```

## Run experiments

Run the following to see a small demo of OARU in the `sokoban` domain (the
same example used in Figure 1 of the paper):
```
demo_with_pddlgym.py
```
This will create an `out` folder, with several `transxxx` subfolder showing
how each transition is processed. Each subfolder contains: (1) a coarse
view of the Action Unification tree; (2) a detailed view of the same tree;
(3) two images representing the states before and after the transition.
Also, in `out` an animated GIF showing the whole execution can be found.

To view the characteristics of the benchmark domains and problems (Tables 1,
2 and 3 from the supplement), please run:
```
./benchmark_environments.py
```
The tables will be directly printed on the terminal. This shouldn't take much
time (around 10s).

To run the performance and accuracy experiments (Tables 1 and 2 and Figure 2
from the paper), and obtain the action libraries presented in the
supplement, run:
```
./benchmark_performance_and_accuracy.py
```
The two tables and the plots can be found in the newly created `out` folder, as
`tabular_full_obs.tex`, `tabular_partial_obs.tex`, `full_obs_updates.pdf`,
and `partial_obs_updates`. The action libraries sit under the `partial_observability`
and `full_observability` folders, also in `out`.

The plot from Figure 2, in the supplement, may be generated running:
```
./benchmark_observation_sampling.py
```
Two figures will be generated in the `out` folder:
`observation_sampling_partial_obs_plot.pdf` and
`observation_sampling_full_obs_plot.pdf`.

Our implementation contains many additional features that, for lack of space,
could not be detailed in the paper. The most important ones are two: (1) an Action
Unification broadphase to discard clearly non-unifiable actions before resorting
to the WPMS machinery; and (2) a labeled predicate filter to discard clearly
unrelated predicates in a TGA and ease the Action Unification process. The
source code for Action Unification and OARU can be found inside the
`satstripslearn` package.


