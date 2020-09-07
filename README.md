# sat_strips_learn


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
source sat_strips_learn/bin/activate
pip install -r requirements.txt
```

## Run experiments

To view the characteristics of the benchmark domains, run:
```
./benchmark_environments.py
```

To run the performance and accuracy experiments, run:
```
./benchmark_performance_and_accuracy.py
```

The source code for Action Unification and OARU can be found inside
the `satstripslearn` package.

