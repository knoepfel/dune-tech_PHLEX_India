## Setup
In a terminal, run `apptainer exec /opt/images/phaindia-0.1-20261002.sif ./build.sh`.

This will checkout a fork/branch of phlex-examples from the author of the tutorial into this directory and
will build within build-phlex-examples.

The notebooks in `generate/`, `transport/`, and `drift/` will make use of that build directory.

The tutorials build off one another and should be completed in the following order
1. generate/
2. transport/
3. drift/

