#!/bin/bash
venv_name=${1:-"h5py_venv"}
if [ -d $venv_name ]; then
  echo "Venv already exists -- exiting"
fi
python -m venv $venv_name 

## Activate in a subshell to not put into user env
(
  source $venv_name/bin/activate
  pip install h5py matplotlib numpy

  if [ $? -eq 0 ]; then
    echo "Successfully created virtual environment and installed libraries."
    echo "If you want to activate the virtual env: source $venv_name"
    echo "Or you could use in-line with your command:"
  fi
)

