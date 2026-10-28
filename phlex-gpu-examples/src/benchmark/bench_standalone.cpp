// Run the CUDA benchmark library on its own, without Phlex.
//   ./bench_standalone [log2_n] [iterations]     (defaults: 24, 100)
#include "my_saxpy_bench.hpp"

#include <cstdio>
#include <cstdlib>
#include <exception>

int main(int argc, char** argv)
{
  int const log2_n = argc > 1 ? std::atoi(argv[1]) : 24;
  int const iterations = argc > 2 ? std::atoi(argv[2]) : 100;

  if (examples::gpu::device_count() == 0) {
    std::printf("No GPU visible to this process.\n");
    return 1;
  }

  try {
    auto const t = examples::gpu::benchmark_saxpy(1LL << log2_n, iterations);
    std::printf("n            = 2^%d = %lld floats\n", log2_n, t.n);
    std::printf("copy in      = %9.3f ms\n", t.h2d_ms);
    std::printf("kernel       = %9.3f ms  (average of %d, %.1f GB/s)\n",
                t.kernel_ms,
                t.iterations,
                t.kernel_gbps);
    std::printf("copy out     = %9.3f ms\n", t.d2h_ms);
    std::printf("CPU, 1 core  = %9.3f ms\n", t.cpu_ms);
    std::printf("max |error|  = %g\n", static_cast<double>(t.max_abs_error));
    return t.max_abs_error < 1e-5f ? 0 : 1;
  }
  catch (std::exception const& e) {
    std::printf("CUDA error: %s\n", e.what());
    return 1;
  }
}
