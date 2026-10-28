# Phlex on a GPU

Two Jupyter notebooks that run CUDA code from Phlex algorithms. They follow on from
[phlex-first-steps](https://github.com/gavinsdavies/phlex-first-steps) and use the same layout as
[Framework-R-D/phlex-examples](https://github.com/Framework-R-D/phlex-examples): the GPU code lives in a
framework-agnostic SHARED library, and a thin MODULE plugin registers it with Phlex.

| Notebook | What it covers |
|---|---|
| `gpu-hello-world.ipynb` | One GPU thread prints `Hello World from GPU thread 0!` from inside a Phlex transform; an observer checks that the thread ran. CUDA basics, a C++/CUDA `CMakeLists.txt`, `concurrency::serial` for the GPU |
| `gpu-benchmark.ipynb` | The minimal CUDA benchmark pattern (warm-up, CUDA-event timing, averaging, error checks, verification, separate transfer timing) on SAXPY. One spill per problem size, results to CSV, plots of time and bandwidth |

Both notebooks open with the hub's **PHA India (Apptainer)** kernel (kernelspec name `phaindia`; change
`KERNELSPEC` in `build_nb.py` if yours differs). That kernel must see a GPU (`--nv`) and the CUDA toolkit.
Every shell cell stops with a clear message if the notebook is on another kernel, such as Python 3. They work in
`~/phlex-work/phlex-gpu-examples`, next to the other tutorials' folders.

## Layout

```
phlex-gpu-examples/
├── gpu-hello-world.ipynb         <- generated, don't edit by hand
├── gpu-benchmark.ipynb           <- generated, don't edit by hand
├── build_nb.py                   <- the notebook text; reads the code from src/
├── make_gpu_kernel.py            <- per-user copy of the phaindia kernel with --nv
└── src/
    ├── hello/
    │   ├── CMakeLists.txt
    │   ├── my_gpu_hello.hpp      plain C++ interface (no CUDA types)
    │   ├── my_gpu_hello.cu       the kernel and its host wrapper (nvcc)
    │   ├── hello_standalone.cpp  the library without Phlex
    │   ├── n_threads_source.cpp  provider: how many GPU threads to launch
    │   ├── gpu_hello_and_verify.cpp  transform (GPU, serial) + observer
    │   └── gpu-hello-workflow.jsonnet
    └── benchmark/
        ├── CMakeLists.txt
        ├── my_saxpy_bench.hpp    plain C++ interface and the saxpy_timing product
        ├── my_saxpy_bench.cu     the benchmark pattern (nvcc)
        ├── bench_standalone.cpp  the library without Phlex
        ├── problem_size_source.cpp   provider: one problem size per spill
        ├── saxpy_bench_and_record.cpp  transform (GPU, serial) + observer writing a CSV
        └── gpu-benchmark-workflow.jsonnet
```

`src/` is the single source of truth. Each notebook writes these files with `%%writefile` cells that
`build_nb.py` fills from `src/`, so the notebooks and the files can't drift apart.

## Editing

Edit the cells in `build_nb.py` or the code in `src/`, then regenerate (needs `nbformat`):

```bash
python3 build_nb.py
```

Cell IDs are fixed, so an unchanged rebuild gives byte-identical notebooks. Cells are tagged for RISE
slides with the same rules as `tag_slides.py` in phlex-first-steps.

## Building `src/` by hand

Each directory is a standalone CMake project. From an environment with Phlex and CUDA:

```bash
cmake -S src/hello -B build-hello -DCMAKE_BUILD_TYPE=Release   # add -DCMAKE_CUDA_ARCHITECTURES=... if no GPU is visible
cmake --build build-hello -j 4
export PHLEX_PLUGIN_PATH=$PWD/build-hello:$PHLEX_PLUGIN_PATH
phlex -c src/hello/gpu-hello-workflow.jsonnet --stage gpu
```

## Tested with

Phlex v0.4.3, GCC 15.3, CUDA 13.4 (nvcc), CMake 3.31: both projects configure and build with
`-Wall -Wpedantic -Werror` on the C++ side, and both Phlex workflows run with CPU stand-ins for the
two CUDA libraries. The GPU code itself still needs a first run on a machine with a GPU.

## Credits and license

Built on the structure of phlex-first-steps by Gavin S. Davies and on phlex-examples by the Phlex
team. Apache License 2.0, like other DUNE software.
