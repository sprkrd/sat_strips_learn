# sat_strips_learn


## Preparation steps

```
sudo apt install python3-dev
```

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
`FF_PATH` env variable to the path of the Fast Downward executable.
You can also add the following to your `~/.bashrc`

```
export FF_PATH=/path/to/ff/executable
```

