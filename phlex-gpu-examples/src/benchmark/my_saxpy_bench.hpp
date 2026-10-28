#ifndef MY_SAXPY_BENCH_HPP
#define MY_SAXPY_BENCH_HPP

// Plain C++ interface to the CUDA benchmark in my_saxpy_bench.cu. No CUDA types appear here, so
// the Phlex plugin that includes this header is compiled by the ordinary C++ compiler.

namespace examples::gpu {

  // Everything one benchmark measures. Plain numbers, so it can be a Phlex data product.
  struct saxpy_timing {
    long long n;          // number of elements in each vector
    int iterations;       // timed kernel launches that were averaged
    double h2d_ms;        // copy x and y host -> device
    double kernel_ms;     // one kernel launch (average over the iterations)
    double d2h_ms;        // copy z device -> host
    double cpu_ms;        // the same calculation on one CPU core
    double kernel_gbps;   // effective bandwidth of the kernel: 3 * n * sizeof(float) / kernel_ms
    float max_abs_error;  // largest |z_gpu - z_cpu|
  };

  // Number of CUDA devices this process can see (0 if there is no GPU or no driver).
  int device_count();

  // z = a * x + y on n floats, with the minimal CUDA benchmark pattern:
  // allocate, copy in (timed), warm up (not timed), time `iterations` launches with CUDA
  // events, check for errors, copy out (timed), verify against the CPU, free.
  // Throws std::runtime_error if any CUDA call fails.
  saxpy_timing benchmark_saxpy(long long n, int iterations);

}

#endif // MY_SAXPY_BENCH_HPP
