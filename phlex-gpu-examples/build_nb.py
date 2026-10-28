"""Build the two GPU notebooks from the cell lists below and the sources in src/.

Edit the cells here and the code in src/, not the notebooks, then regenerate (needs nbformat):

    python3 build_nb.py            # writes gpu-hello-world.ipynb and gpu-benchmark.ipynb

The C++, CUDA, CMake and Jsonnet files are read from src/ and written into %%writefile cells, so
src/ is the single source of truth: what you can build by hand from src/ is exactly what the
notebooks build. Cell IDs are fixed, so an unchanged rebuild gives byte-identical notebooks.
"""

import pathlib
import sys

import nbformat as nbf

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "src"

# The notebooks open with the hub's phaindia kernel (/opt/tljh/user/share/jupyter/kernels/phaindia),
# which runs inside the image with --nv. Change this if your kernel has another name.
KERNEL_DISPLAY = "PHA India (Apptainer)"
KERNELSPEC = {"name": "phaindia", "display_name": KERNEL_DISPLAY, "language": "python"}

# Stops a shell cell early when the notebook runs on the wrong kernel (outside the container)
KERNEL_GUARD = (
    'command -v phlex >/dev/null || { echo "⚠️  phlex not found: this is not the '
    + KERNEL_DISPLAY
    + ' kernel. Pick it (top right), then run Section 0 again."; exit 1; }'
)

# RISE settings, as in phlex-first-steps (Alex Booth's ND tutorial settings)
RISE = {
    "autolaunch": False,
    "enable_chalkboard": True,
    "height": "100%",
    "scroll": True,
    "theme": "solarized",
    "transition": "slide",
    "width": "100%",
}

# Where the notebooks put the code on the hub
WORK_DIR = "~/phlex-work/phlex-gpu-examples"


class Notebook:
    def __init__(self, prefix):
        self.prefix = prefix
        self.cells = []

    def md(self, text):
        self.cells.append(nbf.v4.new_markdown_cell(text.strip("\n")))

    def code(self, text):
        text = text.strip("\n")
        # Every shell cell here needs the container (cmake, phlex, nvcc): stop early on the wrong kernel
        if text.startswith("%%bash\n"):
            text = text.replace("%%bash\n", "%%bash\n" + KERNEL_GUARD + "\n", 1)
        self.cells.append(nbf.v4.new_code_cell(text))

    def writefile(self, rel):
        """A %%writefile cell with the contents of src/<rel>, written to WORK_DIR/<rel>."""
        body = (SRC / rel).read_text()
        self.cells.append(nbf.v4.new_code_cell(f"%%writefile {WORK_DIR}/{rel}\n{body}".rstrip("\n")))

    def write(self, path):
        nb = nbf.v4.new_notebook()
        nb.cells = self.cells
        for i, cell in enumerate(nb.cells):
            cell.id = f"{self.prefix}-{i:02d}"
            cell.metadata["slideshow"] = {"slide_type": slide_type(cell)}
        nb.metadata["kernelspec"] = KERNELSPEC
        nb.metadata["language_info"] = {"name": "python"}
        nb.metadata["rise"] = RISE
        nbf.validate(nb)
        nbf.write(nb, str(path))
        print(f"wrote {path.name}: {len(nb.cells)} cells")


def slide_type(cell):
    """Same rules as tag_slides.py in phlex-first-steps."""
    first = next((l.strip() for l in cell.source.splitlines() if l.strip() and not l.startswith("%%")), "")
    if cell.cell_type == "markdown":
        if first.startswith("# "):
            return "slide"
        if first.startswith("## "):
            return "subslide"
        return "fragment"
    if first.lower().startswith(("# catch-up", "# solution")):
        return "skip"
    return "fragment"


# ------------------------------------------------------------------------------------------------
# Shared pieces
# ------------------------------------------------------------------------------------------------

def setup_cells(nb, name, src_var, build_var):
    kernel = KERNEL_DISPLAY
    nb.md(f"""
# Section 0: Software setup

You need **phlex**, **CMake 3.31 or later**, a C++ compiler, the **CUDA toolkit** (`nvcc`) and a
**GPU** that the kernel can see.

**Check the kernel name at the top right: it should say "PHA India (Apptainer)".** If it says
**Python 3**, switch with **Kernel → Change Kernel…**. The Python 3 kernel runs outside the
container, where there is no phlex or cmake. The PHA India kernel runs inside the image, so every
`!` and `%%bash` cell below can see phlex, and it starts the container with `--nv`, so it can see the GPU.

Run the next cell to check that the tools and the GPU are visible. Run it again if you restart the kernel.
""")
    nb.code("""
!which phlex cmake c++ nvcc nvidia-smi
!cmake --version | head -1
!nvcc --version | tail -2
!phlex --version
!nvidia-smi -L || echo "nvidia-smi found no GPU"
""")
    nb.md("""
What you should see:

- a path for every tool, and a `release` line from `nvcc`
- at least one line like `GPU 0: NVIDIA A100 ...` from `nvidia-smi -L`

If something is missing, you can still read the code below, but not run it on a GPU. There are two
separate things to check:

- **`nvidia-smi` missing or no GPU listed: the kernel was started without `--nv`.** The GPU driver and
  `nvidia-smi` come from the host, and apptainer only passes them into the container when it is
  started with `--nv`. You cannot add that flag from inside a notebook, because the kernel *is* the
  container: it has to be in the kernel's start command. Use the **PHA India (Apptainer) (GPU)** kernel if
  the kernel menu has one. If not, make your own copy of the kernel with `--nv`, once, in a terminal
  outside the container, from the folder this notebook is in:

  💻 **Terminal, outside the container** (prompt `jupyter-you@dune-tech`)
  ```bash
  python3 make_gpu_kernel.py
  ```

  Then reload this page, choose **PHA India (Apptainer) (GPU)** (top right) and run the cell above again.
  To check by hand first: `apptainer shell --nv --cleanenv <image>.sif`, then `nvidia-smi -L`.
- **`nvcc` missing: the image has no CUDA toolkit.** `--nv` does not help here: it brings the driver,
  not the compiler. The image needs CUDA added (see **Troubleshooting** at the end).

## Paths

You work in `~/phlex-work`, the same folder as the other Phlex tutorials, in a new
`phlex-gpu-examples` directory. The build directory sits next to the source directory, as in the
phlex-examples README:

```
~/phlex-work/phlex-gpu-examples/
""" + f"""├── {name}/          <- source: the CUDA library, the Phlex plugins, CMakeLists.txt, the configuration
└── build-{name}/    <- CMake build directory
```

Each `!` cell runs in a new shell, so `cd` or `export` in one cell does not carry over to the next.
The next cell sets the paths as environment variables of the kernel, which every later cell inherits.
It also chooses which GPU architecture to compile for. Run it again if you restart the kernel.
""")
    nb.code(f"""
import os
import shutil
import subprocess
from pathlib import Path

WORK = Path.home() / "phlex-work" / "phlex-gpu-examples"
{src_var} = WORK / "{name}"
{build_var} = WORK / "build-{name}"
{src_var}.mkdir(parents=True, exist_ok=True)
{build_var}.mkdir(parents=True, exist_ok=True)

os.environ["{src_var}"] = str({src_var})
os.environ["{build_var}"] = str({build_var})

# phlex finds plugins (MODULE libraries) through PHLEX_PLUGIN_PATH. Put the build directory first
# and keep what the kernel already has (that is where phlex's own plugins, like generate_layers, are).
entries = os.environ.get("PHLEX_PLUGIN_PATH", "").split(":")
if str({build_var}) not in entries:
    os.environ["PHLEX_PLUGIN_PATH"] = ":".join([str({build_var})] + [e for e in entries if e])

# Compile the plugins with the g++ on PATH: the compiler Phlex was built with, and the one nvcc uses
# as its host compiler. Without this, CMake follows a CXX variable from the image, which can name
# a different compiler (such as clang++).
gxx = shutil.which("g++")
if gxx:
    os.environ["CXX"] = gxx

# Find nvcc: on PATH already, or in a CUDA toolkit mounted into the container at /usr/local/cuda*
if not shutil.which("nvcc"):
    for candidate in sorted(Path("/usr/local").glob("cuda*/bin/nvcc"), reverse=True):
        os.environ["PATH"] = f"{{candidate.parent}}:{{os.environ['PATH']}}"
        break
nvcc = shutil.which("nvcc")

# CUDA 12 refuses GCC 15 as nvcc's host compiler. If this CUDA is older than 13 and the image's
# compiler is GCC 15 or newer, let nvcc use the operating system's g++ for the .cu files instead.
# The Phlex plugins are still compiled by the image's GCC 15.
os.environ.setdefault("CUDA_CMAKE_ARGS", "")
if nvcc and not os.environ["CUDA_CMAKE_ARGS"]:
    release = subprocess.run([nvcc, "--version"], capture_output=True, text=True).stdout
    cuda_major = int(release.split("release ")[1].split(".")[0]) if "release " in release else 0
    gcc_major = int(subprocess.run(["c++", "-dumpversion"], capture_output=True, text=True).stdout.split(".")[0] or 0)
    system_gxx = Path("/usr/bin/g++")
    if cuda_major and cuda_major < 13 and gcc_major >= 15 and system_gxx.exists():
        os.environ["CUDA_CMAKE_ARGS"] = f"-DCMAKE_CUDA_HOST_COMPILER={{system_gxx}}"

# Which GPU architecture should nvcc compile for?
#   - a GPU is visible: 'native', the exact GPU(s) in this machine
#   - no GPU visible:   a list of common ones, so that the code at least compiles
gpus = ""
if shutil.which("nvidia-smi"):
    gpus = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True).stdout.strip()
os.environ["CUDA_ARCH"] = "native" if gpus.startswith("GPU") else "75;80;86;89;90"

# To pass other CMake arguments for CUDA, set CUDA_CMAKE_ARGS before running this cell, for example
#   os.environ["CUDA_CMAKE_ARGS"] = "-DCMAKE_CUDA_FLAGS=-allow-unsupported-compiler"

for var in ["{src_var}", "{build_var}", "PHLEX_PLUGIN_PATH", "CXX", "CUDA_ARCH", "CUDA_CMAKE_ARGS"]:
    print(f"{{var:18}} {{os.environ.get(var, '')}}")
print(f"{{'nvcc':18}} {{nvcc or '⚠️  not found: the image has no CUDA toolkit, so the GPU code cannot be built'}}")
print()
print(gpus or "⚠️  No GPU visible: you can build, but running the GPU code will fail.")
if not shutil.which("phlex"):
    print("⚠️  phlex not found: this notebook is not on the {kernel} kernel. Switch to it (top right) and run this cell again.")
""")


def troubleshooting(nb):
    nb.md("""
## Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| `nvidia-smi` missing, or `No devices were found` | The kernel's container was started without `--nv` | Choose the **(GPU)** kernel, or run `python3 make_gpu_kernel.py` in a terminal outside the container (Section 0), reload the page and choose the new kernel |
| `which nvcc` prints nothing, even with the GPU kernel, or CMake says `Failed to find nvcc` | The image has no CUDA toolkit; `--nv` only brings the driver | Ask your hub admin to add CUDA to the image, or to mount the host's CUDA toolkit into the kernel at `/usr/local/cuda*` (the setup cell finds it there). CUDA 13 or later works with the image's GCC 15 and needs a 580-series or newer driver; with CUDA 12 the setup cell makes nvcc use the system g++ |
| cmake stops because no GPU was detected for `CMAKE_CUDA_ARCHITECTURES` `native` | You ran cmake without a visible GPU | Rerun the setup cell (it then picks a list of architectures), or fix the GPU visibility first |
| `unsupported GNU version! gcc versions later than ... are not supported` | Your C++ compiler is newer than this CUDA release supports | Point nvcc at an older g++ with `-DCMAKE_CUDA_HOST_COMPILER=/path/to/g++-14`, or, at your own risk, `-DCMAKE_CUDA_FLAGS=-allow-unsupported-compiler`. Put it in `CUDA_CMAKE_ARGS` in the setup cell, delete the build directory and configure again |
| `CUDA driver version is insufficient for CUDA runtime version` | No driver is visible, or the driver is older than the toolkit | Check `nvidia-smi` in this notebook. If it works, the toolkit is newer than the driver: use a matching toolkit |
| `no kernel image is available for execution on the device` | The code was compiled for another GPU architecture | Configure again with a visible GPU (`native`), or add your GPU's architecture to `CMAKE_CUDA_ARCHITECTURES` |
| `Could not locate library with specification '...'` | phlex cannot find a plugin | Run the setup cell again: it puts the build directory on `PHLEX_PLUGIN_PATH` |
| `No stage name was specified` | Current phlex needs a stage | Keep `--stage gpu` on the `phlex` command line |
""")


# ------------------------------------------------------------------------------------------------
# Notebook 1: Hello World from the GPU
# ------------------------------------------------------------------------------------------------

def hello_notebook():
    nb = Notebook("hello")
    nb.md("""
# Hello World from a GPU, inside a Phlex job

This notebook runs CUDA code from a Phlex algorithm. The CUDA part is the smallest GPU program
there is: launch **one GPU thread**, and that thread prints

```
Hello World from GPU thread 0!
```

When you finish, you will be able to:
- explain what a CUDA kernel, a thread and a launch configuration are
- put CUDA code in a library that Phlex code can call, without nvcc ever seeing a Phlex header
- write the `CMakeLists.txt` for a project that mixes C++ and CUDA
- run a Phlex job whose transform runs on the GPU, and check its result with an observer

## How this fits with the other workshop tutorials

- **Do `phlex-first-steps.ipynb` first**, and ideally `phlex-examples-tutorial.ipynb` up to Section 6.
  This notebook uses the ideas from there: providers, transforms, observers, `product_selector`,
  `PHLEX_PLUGIN_PATH`, and the **SHARED** versus **MODULE** library split.
- The key idea is the same one Kyle gave: **Phlex provides the higher-order functions; you provide
  the operators.** Here, the operator is an ordinary C++ function that happens to start work on a GPU.
- The companion notebook, `gpu-benchmark.ipynb`, uses the same structure to time real GPU work.

## The plan

```
 job ──► n_threads_source ──► n_threads ──► transform "gpu_hello" ──► greetings
                                  │              │ calls examples::gpu::say_hello()
                                  │              ▼ in libmy_gpu_hello.so (compiled by nvcc)
                                  │            GPU: "Hello World from GPU thread 0!"
                                  └──────────► observer "verify_greetings" ◄──┘
```

- **Provider:** `n_threads_source` provides how many GPU threads to launch (1) as a data product.
- **Transform:** `gpu_hello` calls the CUDA library, which launches the kernel and returns how many
  threads said hello.
- **Observer:** `verify_greetings` checks that every launched thread said hello.
""")
    setup_cells(nb, "hello", "GPU_SRC", "GPU_BUILD")

    nb.md("""
# Section 1: A GPU in five minutes

A CPU has a few fast cores. A GPU has thousands of simple ones, built to run the **same code on
many pieces of data at once**. You write that code as a **kernel**: a function marked `__global__`
that the CPU (the **host**) launches on the GPU (the **device**).

```cpp
__global__ void hello_kernel() { printf("Hello World from GPU thread %d!\\n", threadIdx.x); }

hello_kernel<<<1, 1>>>();   // <<<number of blocks, threads per block>>>
cudaDeviceSynchronize();    // wait for the GPU to finish
```

| Term | Meaning |
|---|---|
| **kernel** | A `__global__` function. One launch runs it once **per thread**. |
| **thread** | One copy of the kernel. `threadIdx.x` is its number inside its block. |
| **block** | A group of up to 1024 threads that run on the same part of the GPU. `blockIdx.x` numbers the blocks. |
| **launch configuration** | `<<<blocks, threads_per_block>>>`. `<<<1, 1>>>` is one block of one thread: a single GPU thread. |
| **asynchronous** | The launch returns at once, before the kernel has run. `cudaDeviceSynchronize()` waits. |

Two details matter for this example:

- `printf` on the GPU writes into a buffer on the device. The text reaches your screen only when the
  host **synchronizes** with the GPU. Forget `cudaDeviceSynchronize()` and the program can end before
  anything is printed.
- A kernel cannot return a value. To get an answer back, the kernel writes to **device memory**
  and the host copies it back with `cudaMemcpy`. Here each thread adds 1 to a counter, so the host
  can check that the thread really ran.

> 🧭 **Analogy:** the CPU is a lab manager and the GPU is a room of a thousand technicians. A kernel
> is one instruction sheet. The launch configuration says how many technicians get a copy. The manager
> hands out the sheets and goes back to work (asynchronous); to read the results, the manager has to
> wait for the room to finish (synchronize).

> 🔬 **In an analysis:** DUNE's optical photon simulation is a natural GPU job. Millions of photons
> follow the same rules independently, so each GPU thread can track one photon. The detector
> simulation chain on the CPU only sees the photons that reach a photon detector.
""")

    nb.md("""
# Section 2: The CUDA library

The CUDA code lives in a **framework-agnostic library**, like `my_add` in phlex-examples. Two files:

- `my_gpu_hello.hpp`: the interface. It is **plain C++**: no `__global__`, no CUDA types. Any
  C++ code can include it, including a Phlex plugin compiled as C++23.
- `my_gpu_hello.cu`: the implementation, compiled by **nvcc**. It never includes a Phlex header.

This split means the CUDA compiler never has to understand Phlex's C++23 headers, and the Phlex
plugin never has to know about CUDA.
""")
    nb.writefile("hello/my_gpu_hello.hpp")
    nb.writefile("hello/my_gpu_hello.cu")
    nb.md("""
What `say_hello` does, step by step:

| Step | Code | Why |
|---|---|---|
| Check the input | `n_threads < 1 \\|\\| n_threads > 1024` | One block holds at most 1024 threads |
| Allocate a counter on the GPU | `cudaMalloc`, `cudaMemset` | The kernel can only write to device memory |
| Launch | `hello_kernel<<<1, n_threads>>>(d_greeted)` | One block of `n_threads` threads |
| Check the launch | `cudaGetLastError()` | Catches a bad launch configuration, or no usable GPU |
| Wait | `cudaDeviceSynchronize()` | The kernel has finished, its errors are reported, and its `printf` text is printed |
| Copy the answer back | `cudaMemcpy(..., cudaMemcpyDeviceToHost)` | Now the host knows how many threads ran |

Every CUDA call returns an error code, and `check()` turns a failure into a C++ exception. A Phlex job
then stops and prints the error, instead of carrying on with a wrong answer.
""")

    nb.md("""
## Try the library without Phlex first

A tiny program calls the same function. If this works, the GPU, the driver and the toolkit are
fine, and any later problem is in the Phlex part. Testing the library on its own is the point of keeping
it framework-agnostic.
""")
    nb.writefile("hello/hello_standalone.cpp")

    nb.md("""
# Section 3: The Phlex plugins

Two MODULE libraries, the same pattern as `numbers_source` and `add_and_verify` in phlex-examples.

**The provider** makes the launch size a data product. It reads `n_threads` from the configuration
and provides it for every data cell of the configured layer.
""")
    nb.writefile("hello/n_threads_source.cpp")
    nb.md("""
**The algorithms.** Compare this with `add_and_verify.cpp`: it is the same shape. The only GPU-specific
choice is `concurrency::serial` on the transform.
""")
    nb.writefile("hello/gpu_hello_and_verify.cpp")
    nb.md("""
- `m.transform("gpu_hello", examples::gpu::say_hello, ...)` registers the CUDA library's function
  directly as the operator. Phlex reads its signature, `int(int)`, to know it takes one `int` and makes one.
- `concurrency::serial` lets only one call run at a time. There is one GPU, and two launches at once
  would mix their printed lines. The GPU is a **shared resource**, like a single output file.
- The observer takes **two** products from the same data cell: `n_threads` from the provider and
  `greetings` from the transform. Phlex calls it once both exist.

> 🧭 **Analogy:** `concurrency::serial` on the GPU transform is a booking sheet for the one big
> microscope in the lab. Everyone gets their turn; nobody shares the eyepiece.

> 🔬 **In an analysis:** with many data cells, `serial` means the GPU work of different events
> waits in line while the CPU work of other algorithms carries on in parallel. That is often what you
> want: the GPU stays busy, and the CPU threads do everything else.

**The configuration.** No extra layers: the job is the only data cell, so the kernel is launched
once, with one thread.
""")
    nb.writefile("hello/gpu-hello-workflow.jsonnet")

    nb.md("""
# Section 4: CMake for C++ and CUDA
""")
    nb.writefile("hello/CMakeLists.txt")
    nb.md("""
New things compared with the phlex-examples `CMakeLists.txt`:

| Line | What it does |
|---|---|
| `set(CMAKE_CUDA_ARCHITECTURES native)` before `project()` | Compile for the GPU in this machine. The setup cell passes `-DCMAKE_CUDA_ARCHITECTURES` explicitly, which overrides it |
| `project(... LANGUAGES CXX CUDA)` | CMake finds `nvcc` as well as the C++ compiler, and compiles `.cu` files with it |
| `set(CMAKE_CUDA_STANDARD 17)` | The `.cu` file is C++17. Only the plugins, compiled by g++, need C++23 |
| `find_package(CUDAToolkit REQUIRED)` | Provides the target `CUDA::cudart`, the CUDA runtime library |
| `$<$<COMPILE_LANGUAGE:CXX>:...>` | A **generator expression**: apply `-Wall -Wpedantic -Werror` to C++ files only. nvcc does not accept `-Wpedantic`, so phlex-examples' plain `add_compile_options` would break the CUDA build |
| `add_library(my_gpu_hello SHARED my_gpu_hello.cu)` | The CUDA library. CMake sees `.cu` and uses nvcc |
| `CUDA_RUNTIME_LIBRARY Shared` | Link the shared CUDA runtime, so every library in the process uses the same one |
| `target_link_libraries(gpu_hello_and_verify PRIVATE phlex::module my_gpu_hello)` | The plugin links the CUDA library, exactly like `add_and_verify` links `my_add` |
""")

    nb.md("""
# Section 5: Build
""")
    nb.code("""
%%bash
cd "$GPU_BUILD"
command -v nvcc >/dev/null || { echo "⚠️  nvcc not found. Run the setup cell in Section 0 and read its nvcc line."; exit 1; }
rm -f CMakeCache.txt  # configure from scratch, so the compilers chosen in Section 0 are used
cmake "$GPU_SRC" -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES="$CUDA_ARCH" $CUDA_CMAKE_ARGS
""")
    nb.md("""
Look for `The CUDA compiler identification is NVIDIA ...` near the top and `Build files have been
written to: …` at the end. If configure fails, see **Troubleshooting** at the end. Now build. The hub is
shared, so please use no more than 4 jobs.
""")
    nb.code("""
%%bash
cd "$GPU_BUILD"
cmake --build . -j 4
echo "=== Libraries and programs"
ls *.so hello_standalone
""")
    nb.md("""
`libmy_gpu_hello.so` was compiled by nvcc; the other two libraries are Phlex plugins compiled by
the C++ compiler.

# Section 6: Run

First the library on its own:
""")
    nb.code("""
%%bash
cd "$GPU_BUILD"
./hello_standalone
""")
    nb.md("""
Expected output:

```
CUDA devices visible: 1
Hello World from GPU thread 0!
Threads that said hello: 1
```

Now the same function inside a Phlex job. As in the other tutorials, pass a stage name with `--stage`.
""")
    nb.code("""
%%bash
cd "$GPU_BUILD"
phlex -c "$GPU_SRC/gpu-hello-workflow.jsonnet" --stage gpu -j 4
""")
    nb.md("""
You should see:

```
Using configuration file: .../gpu-hello-workflow.jsonnet
[...] [info] Number of worker threads: 4
Hello World from GPU thread 0!
[...] [info]
Seen layers:

  job
```

(Older Phlex releases print `Processed layers:` instead of `Seen layers:`.) The job ends with exit code
0, which means the observer's `assert(greetings == n_threads)` passed.

# Section 7: Things to try

## 7.1 More threads, no rebuild

`n_threads` is configuration, not code. Set it to 8 in `gpu-hello-workflow.jsonnet` and rerun the
job. The solution cell below makes a copy of the configuration with the change, so the original stays as it is.
""")
    nb.code("""
# Solution for 7.1: a copy of the configuration with 8 threads
cfg = GPU_SRC / "gpu-hello-workflow.jsonnet"
text = cfg.read_text()
assert "n_threads: 1," in text, "gpu-hello-workflow.jsonnet does not look like the original; edit it by hand"
(GPU_SRC / "gpu-hello-8-threads.jsonnet").write_text(text.replace("n_threads: 1,", "n_threads: 8,"))
print("Wrote gpu-hello-8-threads.jsonnet")
""")
    nb.code("""
%%bash
cd "$GPU_BUILD"
phlex -c "$GPU_SRC/gpu-hello-8-threads.jsonnet" --stage gpu -j 4 2>&1 | grep Hello
""")
    nb.md("""
Eight lines, threads 0 to 7. With 8 threads they usually come out in order, but nothing guarantees
it. Try 100: threads run in groups of 32 (a **warp**), and the order of the groups is up to the GPU.
Never rely on the order of GPU threads.

## 7.2 One launch per data cell

Give the job a `spill` layer with 3 spills, and run the provider and the algorithms on `spill`
instead of `job`. Phlex then calls the transform once per spill: three launches, still one at a
time because of `concurrency::serial`.
""")
    nb.code("""
%%writefile ~/phlex-work/phlex-gpu-examples/hello/gpu-hello-spills.jsonnet
{
  driver: {
    cpp: 'generate_layers',
    layers: {
      spill: { parent: 'job', total: 3 },
    },
  },
  sources: {
    n_threads_source: {
      cpp: 'n_threads_source',
      layer: 'spill',
      n_threads: 2,
    },
  },
  modules: {
    hello: {
      cpp: 'gpu_hello_and_verify',
      layer: 'spill',
    },
  },
}
""")
    nb.code("""
%%bash
cd "$GPU_BUILD"
phlex -c "$GPU_SRC/gpu-hello-spills.jsonnet" --stage gpu -j 4
""")
    nb.md("""
Six hello lines (3 spills × 2 threads), and `spill: 3` under `job`. No code changed, and nothing was
rebuilt.

> 🔬 **In an analysis:** this is the real pattern. A provider (or a FORM source) gives each event its
> data, the GPU transform works on one event at a time, and observers or later transforms use the
> result. The layer you choose is how much work each GPU launch gets: a whole trigger record, one
> APA, or one wire.

## 7.3 Break it on purpose

A block holds at most 1024 threads. Ask for 2000 and see how a CUDA failure reaches you through
Phlex. **This cell is supposed to fail.**
""")
    nb.code("""
%%bash
cd "$GPU_BUILD"
sed 's/n_threads: 1,/n_threads: 2000,/' "$GPU_SRC/gpu-hello-workflow.jsonnet" > gpu-hello-too-many.jsonnet
phlex -c gpu-hello-too-many.jsonnet --stage gpu -j 4 2>&1 | grep -E "error|Hello" | head -3
echo "phlex exit code: ${PIPESTATUS[0]}"
""")
    nb.md("""
The exception thrown by `say_hello` stops the job with a clear message and a non-zero exit code. Try
removing the `n_threads > 1024` check from `my_gpu_hello.cu`, rebuild and rerun: now the error comes
from `cudaGetLastError()` instead (`invalid configuration argument`). Without that check too, the
kernel would silently not run, and only the observer would notice. **Always check CUDA errors.**
Put the check back when you are done.
""")
    troubleshooting(nb)
    nb.md("""
## Summary

| Piece | File | Compiled by |
|---|---|---|
| Kernel and host wrapper | `my_gpu_hello.cu` | nvcc |
| Plain C++ interface | `my_gpu_hello.hpp` | included by both |
| Provider | `n_threads_source.cpp` | C++ compiler, C++23 |
| Transform and observer | `gpu_hello_and_verify.cpp` | C++ compiler, C++23 |
| Job | `gpu-hello-workflow.jsonnet` | read by phlex |

The rule to take away: **put the CUDA in a SHARED library with a plain C++ interface, and register
its functions from a thin MODULE**, exactly as phlex-examples does for CPU code. Mark the GPU
algorithm `concurrency::serial` unless you have a reason not to.

Next: `gpu-benchmark.ipynb` uses the same layout to **time** GPU work, and shows when moving work to
a GPU pays off and when it does not.
""")
    return nb


# ------------------------------------------------------------------------------------------------
# Notebook 2: the minimal CUDA benchmark pattern
# ------------------------------------------------------------------------------------------------

def benchmark_notebook():
    nb = Notebook("bench")
    nb.md("""
# Timing GPU work in a Phlex job: the minimal CUDA benchmark pattern

`gpu-hello-world.ipynb` showed how to call CUDA code from Phlex. This notebook **times** it. The
work is SAXPY, `z = a·x + y` on vectors of `n` floats: the "hello world" of GPU performance.

When you finish, you will be able to:
- write a GPU benchmark that gives numbers you can trust (the minimal benchmark pattern)
- tell kernel time, transfer time and CPU time apart, and compute an effective bandwidth
- use a Phlex layer to scan a parameter: here, one problem size per spill
- read the result: when a GPU helps, and when copying the data costs more than the GPU saves

Do `gpu-hello-world.ipynb` first. This notebook uses the same layout and the same setup.

## The minimal CUDA benchmark pattern

Timing a GPU is easy to get wrong. The pattern is a checklist:

| # | Rule | Why |
|---|---|---|
| 1 | **Warm up** with one untimed launch | The first launch pays one-off costs (loading the kernel onto the device, and more) |
| 2 | **Time with CUDA events**, not a CPU clock | Launches are asynchronous: a CPU clock measures how long it took to *queue* the work |
| 3 | **Average many launches** | One launch of a small kernel takes a few microseconds, close to the timer's resolution |
| 4 | **Check errors** after the launches | A kernel that failed to launch takes no time at all, and looks very fast |
| 5 | **Verify** the answer against the CPU | A fast wrong answer is worthless |
| 6 | **Time the copies separately** | Host↔device copies over PCIe are often slower than the kernel itself |
| 7 | **Report a meaningful rate** | GB/s for memory-bound kernels like SAXPY; FLOP/s for compute-bound ones |

and one rule from Phlex: **8. give the benchmark the GPU to itself.** Register the GPU algorithm with
`concurrency::serial`, so no other spill's work is on the GPU while you time.

> 🧭 **Analogy:** timing a GPU kernel with the CPU clock is like timing a courier from the moment you
> drop the parcel at the counter. The counter takes it in a second; the delivery takes a day. CUDA
> events are a tracking number that is scanned at the door.

## The plan

```
 spill ──► problem_size_source ──► log2_n ──► transform "saxpy_gpu" ──► timing ──► observer "record"
  (14 spills: n = 2^12 ... 2^25)                (serial, one size     (struct)     (serial: prints a line,
                                                 at a time on GPU)                   appends to a CSV)
```

Each **spill is one problem size**. The layer machinery that usually splits a run into events here
splits a scan into points: you get a parameter scan without writing a loop.
""")
    setup_cells(nb, "benchmark", "BENCH_SRC", "BENCH_BUILD")

    nb.md("""
# Section 1: The benchmark library

As before: a plain C++ header, and a `.cu` file compiled by nvcc. The header defines
`saxpy_timing`, a struct of plain numbers. A struct like this can be a Phlex data product, just like
`examples::geometry` in phlex-examples.
""")
    nb.writefile("benchmark/my_saxpy_bench.hpp")
    nb.md("""
The implementation follows the checklist. The numbered comments match the steps below.
""")
    nb.writefile("benchmark/my_saxpy_bench.cu")
    nb.md("""
| Step | Checklist rule | Note |
|---|---|---|
| 3. Copy in | 6 | Events around the two `cudaMemcpy` calls measure the PCIe transfer |
| 4. Warm-up | 1 | Launched and synchronized, never timed |
| 5. Timed launches | 2, 3, 4 | One pair of events around `iterations` launches; divide by `iterations` |
| Effective bandwidth | 7 | SAXPY reads `x` and `y` and writes `z`: 3 × 4 bytes per element |
| 6. Copy out | 6 | Timed like the copy in |
| 7. CPU reference | 5 | The same loop on one core, timed with `std::chrono` (the CPU *is* synchronous) |
| 8. Verify | 5 | The GPU may fuse `a*x + y` into one instruction (FMA), so allow a tiny rounding difference |

The kernel uses a **grid-stride loop**: each thread handles element `i`, then `i + stride`, and so
on. Any number of blocks then covers any `n`, which is why the launch can cap the grid size.

## Run it without Phlex

The standalone program takes `log2_n` and the number of iterations.
""")
    nb.writefile("benchmark/bench_standalone.cpp")

    nb.md("""
# Section 2: The Phlex plugins

**The provider** turns the spill number into a problem size: `log2_n = first_log2_n + spill number`.
""")
    nb.writefile("benchmark/problem_size_source.cpp")
    nb.md("""
**The algorithms.** The transform returns a `saxpy_timing`, a product Phlex has never heard of; it does
not need to. The observer writes one CSV row per spill.
""")
    nb.writefile("benchmark/saxpy_bench_and_record.cpp")
    nb.md("""
Two `concurrency::serial`s, for two different reasons:

- the **transform**: rule 8. With `unlimited`, Phlex would run several sizes on the GPU at the same
  time, and each timing would include the others' work.
- the **observer**: every call writes to the same file (the checkout-lane rule from the deep dive).

The lambda captures `csv`, a `std::shared_ptr<std::ofstream>`: the file is opened once, when the plugin
is loaded, and stays open for the whole job.

**The configuration.** Jsonnet `local` variables keep the scan's two numbers together at the top.
""")
    nb.writefile("benchmark/gpu-benchmark-workflow.jsonnet")
    nb.md("""
At the largest size each vector is 128 MB, so one call uses about 0.4 GB on the GPU and 0.5 GB on
the host. The hub is shared; please don't raise `n_sizes` much further.

# Section 3: Build
""")
    nb.writefile("benchmark/CMakeLists.txt")
    nb.md("""
This is the `CMakeLists.txt` from the hello notebook with the names changed, plus one line: a benchmark
defaults to a `Release` build, because timing unoptimized code tells you nothing.
""")
    nb.code("""
%%bash
cd "$BENCH_BUILD"
command -v nvcc >/dev/null || { echo "⚠️  nvcc not found. Run the setup cell in Section 0 and read its nvcc line."; exit 1; }
rm -f CMakeCache.txt  # configure from scratch, so the compilers chosen in Section 0 are used
cmake "$BENCH_SRC" -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES="$CUDA_ARCH" $CUDA_CMAKE_ARGS
cmake --build . -j 4
echo "=== Libraries and programs"
ls *.so bench_standalone
""")

    nb.md("""
# Section 4: Run

The GPU may be shared with other people on the hub, and their work changes your timings. Check
before you measure: `nvidia-smi` lists the processes using each GPU and how busy it is.
""")
    nb.code("""
!nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv
""")
    nb.md("""
First the library on its own, for one size: 2^24 floats, 100 timed launches.
""")
    nb.code("""
%%bash
cd "$BENCH_BUILD"
./bench_standalone 24 100
""")
    nb.md("""
Now the whole scan as a Phlex job:
""")
    nb.code("""
%%bash
cd "$BENCH_BUILD"
phlex -c "$BENCH_SRC/gpu-benchmark-workflow.jsonnet" --stage gpu -j 4
""")
    nb.md("""
You should see one line per size and `spill: 14` under `job` at the end. The lines are not always in
order of size: Phlex makes no promise about the order in which spills finish, so the plot below sorts by `n`.

# Section 5: Plot the results
""")
    nb.code("""
import csv

import numpy as np

with open(BENCH_BUILD / "saxpy_benchmark.csv") as f:
    rows = sorted(csv.DictReader(f), key=lambda r: int(r["n"]))
n = np.array([int(r["n"]) for r in rows])
col = {k: np.array([float(r[k]) for r in rows]) for k in ["h2d_ms", "kernel_ms", "d2h_ms", "cpu_ms", "kernel_gbps"]}
gpu_total = col["h2d_ms"] + col["kernel_ms"] + col["d2h_ms"]

print(f"{'n':>10} {'kernel ms':>10} {'GB/s':>8} {'GPU+copies ms':>14} {'CPU ms':>9} {'kernel speedup':>15} {'end-to-end':>11}")
for i in range(len(n)):
    print(f"{n[i]:>10} {col['kernel_ms'][i]:>10.4f} {col['kernel_gbps'][i]:>8.1f} {gpu_total[i]:>14.3f} "
          f"{col['cpu_ms'][i]:>9.3f} {col['cpu_ms'][i] / col['kernel_ms'][i]:>14.1f}x {col['cpu_ms'][i] / gpu_total[i]:>10.2f}x")

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("matplotlib is not available in this kernel; the table above is the result.")
else:
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter

    # Plain-text tick labels: sizes as 4K ... 16M, times as 0.001 ... 100 ms
    def size_label(v, _pos=None):
        for unit, scale in (("M", 2**20), ("K", 2**10)):
            if v >= scale:
                return f"{v / scale:g}{unit}"
        return f"{v:g}"

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for ax in axes:
        ax.set_xscale("log", base=2)
        ax.xaxis.set_major_locator(FixedLocator(n[::2]))
        ax.xaxis.set_major_formatter(FuncFormatter(size_label))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xlabel("n (floats per vector)")
        ax.grid(True, which="major", alpha=0.3)

    axes[0].plot(n, col["cpu_ms"], "o-", label="CPU, 1 core")
    axes[0].plot(n, col["kernel_ms"], "s-", label="GPU kernel only")
    axes[0].plot(n, gpu_total, "^-", label="GPU with copies in and out")
    axes[0].set_yscale("log")
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v, _pos: f"{v:g}"))
    axes[0].yaxis.set_minor_formatter(NullFormatter())
    axes[0].set_ylabel("time per call [ms]")
    axes[0].set_title("Time for z = a·x + y")
    axes[0].legend()

    axes[1].plot(n, col["kernel_gbps"], "s-", color="C1")
    axes[1].set_ylabel("effective bandwidth [GB/s]")
    axes[1].set_title("GPU kernel bandwidth")
    axes[1].set_ylim(bottom=0)

    fig.tight_layout()

    # Show the figure as SVG. SVG draws text from the font's outlines, while the default PNG output
    # rasterizes every glyph with FreeType, which fails in some images ("raster overflow").
    import io

    from IPython.display import SVG, display

    svg = io.StringIO()
    fig.savefig(svg, format="svg")
    plt.close(fig)
    display(SVG(svg.getvalue()))
    (BENCH_BUILD / "saxpy_benchmark.svg").write_text(svg.getvalue())
    print(f"Saved {BENCH_BUILD / 'saxpy_benchmark.svg'}")
""")
    nb.md("""
## Reading the plots

- **Small `n`**: the kernel time hardly changes with `n`. You are measuring the cost of a launch,
  a few microseconds, not the work. The bandwidth is low because there is too little work to keep the GPU busy.
- **Middle `n`**: the bandwidth can shoot up, far above what the GPU's memory can deliver. The 50
  timed launches reuse the same three vectors, and while all three fit in the GPU's **L2 cache** (48 MB
  on an NVIDIA L4, so up to about n = 2M here), the data never leaves the chip. You are measuring the
  cache, not the memory. A real workload that streams new data each time would not see this bump.
- **Large `n`**: the vectors no longer fit in the cache, the kernel time grows in proportion to `n`,
  and the bandwidth settles on a plateau close to the GPU's memory bandwidth (about 300 GB/s on an L4).
  SAXPY does one multiply and one add per 12 bytes moved, so it is **memory-bound**: its speed is set by
  memory bandwidth, and the GPU's advantage over one CPU core is roughly the ratio of the two bandwidths,
  a few times on an L4, more on GPUs with faster memory.
- **With copies**: the copies go over PCIe, which is far slower than the GPU's own memory. For SAXPY the
  "GPU with copies" curve is usually **slower than the CPU**: you spend more time moving the data than the
  GPU saves. The `end-to-end` column in the table shows it.

The lesson for real work: **a GPU pays off when the data stays on it for a lot of work.** Copy the
inputs once, do as much as possible on the device, and copy back only the results.

> 🔬 **In an analysis:** that is why optical photon simulation works so well on GPUs. The photons
> are created, propagated and stopped on the GPU, millions of them per event, and only the few that hit
> a photon detector come back to the host. A GPU transform that copied every photon back and forth
> would lose most of the gain.

# Section 6: Things to try

## 6.1 Break rule 8: share the GPU

Change the transform to `concurrency::unlimited`, rebuild and rerun. Phlex can now run several sizes
on the GPU at once. The solution cell makes the change, rebuilds, reruns and keeps the CSV under a
new name; the cell after it puts `serial` back.
""")
    nb.code("""
# Solution for 6.1: make the GPU transform concurrency::unlimited
plugin = BENCH_SRC / "saxpy_bench_and_record.cpp"
serial_gpu = "     },\\n     concurrency::serial)\\n    .input_family(product_selector{.creator = \\"input\\""
unlimited_gpu = serial_gpu.replace("serial", "unlimited")
text = plugin.read_text()
assert serial_gpu in text, "saxpy_bench_and_record.cpp does not look like the original; edit it by hand"
plugin.write_text(text.replace(serial_gpu, unlimited_gpu))
print("saxpy_gpu is now concurrency::unlimited.")
""")
    nb.code("""
%%bash
set -e  # stop at the first failure, so a failed job is not saved as a result
cd "$BENCH_BUILD"
cmake --build . -j 4 | tail -1
phlex -c "$BENCH_SRC/gpu-benchmark-workflow.jsonnet" --stage gpu -j 4
mv saxpy_benchmark.csv saxpy_benchmark_unlimited.csv
""")
    nb.md("""
Now put `concurrency::serial` back, rebuild, and run the serial scan again so `saxpy_benchmark.csv`
is the clean measurement:
""")
    nb.code("""
# Solution for 6.1: put concurrency::serial back
text = plugin.read_text()
plugin.write_text(text.replace(unlimited_gpu, serial_gpu))
print("saxpy_gpu is concurrency::serial again.")
""")
    nb.code("""
%%bash
cd "$BENCH_BUILD"
cmake --build . -j 4 | tail -1
phlex -c "$BENCH_SRC/gpu-benchmark-workflow.jsonnet" --stage gpu -j 4 > /dev/null && echo "Serial scan written to saxpy_benchmark.csv"
""")
    nb.md("""
Compare `saxpy_benchmark_unlimited.csv` with `saxpy_benchmark.csv`, for example by loading both into the
plotting cell. With `-j 4`, up to four sizes share the GPU, and some kernel times grow even though
the kernels did not change. (The CPU reference timings change too: they now share the CPU with the
other copies.) The benchmark is still "correct"; it just answers a different question.

## 6.2 Break rule 1: no warm-up

Comment out the warm-up launch in `my_saxpy_bench.cu`, set `iterations: 1` in the configuration, rebuild
and rerun. The first size to run now pays the one-off costs, and its point jumps off the curve. Put
both back afterwards.

## 6.3 Faster copies with pinned memory

`std::vector` uses ordinary (*pageable*) memory, which the driver must copy through a staging buffer.
Memory from `cudaMallocHost` is *pinned*: the GPU can read it directly, and copies are usually
faster. Replace the `x`, `y` and `z` vectors with `cudaMallocHost` buffers (free them with
`cudaFreeHost`) and compare `h2d_ms` and `d2h_ms`.

## 6.4 Threads per block

Change `threads_per_block` in `my_saxpy_bench.cu` to 32, 128 or 1024. For a memory-bound kernel the
bandwidth plateau hardly moves: the limit is the memory, not how you group the threads.

> 🔬 **In an analysis:** before you move an algorithm to a GPU, measure it like this. Count the bytes
> it must move to and from the GPU per event, and the work it does on them. If the copies cost more than
> the CPU time you save, keep it on the CPU, or move more of the chain to the GPU so the data stays there.
""")
    troubleshooting(nb)
    nb.md("""
## Summary

| Idea | Where you used it |
|---|---|
| Warm up, time with events, average, check errors, verify | `benchmark_saxpy` in `my_saxpy_bench.cu` |
| Kernel time vs transfer time vs CPU time | the `saxpy_timing` product, the table and the left plot |
| Effective bandwidth | `kernel_gbps`, the right plot |
| A parameter scan with a layer | one spill per size, from `problem_size_source` |
| A custom struct as a data product | `saxpy_timing`, made by the transform and read by the observer |
| `concurrency::serial` for a shared resource | the GPU (transform) and the CSV file (observer) |

The minimal benchmark pattern works for any kernel: keep the steps, swap the kernel, and change the
rate you report (GB/s for memory-bound work, FLOP/s for compute-bound work).
""")
    return nb


def main(out_dir=HERE):
    out_dir = pathlib.Path(out_dir)
    hello_notebook().write(out_dir / "gpu-hello-world.ipynb")
    benchmark_notebook().write(out_dir / "gpu-benchmark.ipynb")


if __name__ == "__main__":
    main(*sys.argv[1:])
