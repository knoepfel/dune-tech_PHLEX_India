#!/bin/bash

cd "$(dirname "$0")"

git clone -b phlex-workshop-updates https://github.com/calcuttj/phlex-examples.git 
ret=$?

if [[ ret -ne 0 ]]; then
    echo "Could not clone from git"
    exit $ret
fi

mkdir build-phlex-examples && cd build-phlex-examples
cmake ../phlex-examples -G Ninja && ninja -j${ncores:-12}
ret=$?

if [[ ret -ne 0 ]]; then
    echo "Could not build"
    exit $ret
fi