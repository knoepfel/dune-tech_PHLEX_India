#include "my_saxpy_bench.hpp"

#include <cuda_runtime.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

  // z[i] = a * x[i] + y[i]. A grid-stride loop, so any grid size covers any n.
  __global__ void saxpy_kernel(long long const n,
                               float const a,
                               float const* __restrict__ x,
                               float const* __restrict__ y,
                               float* __restrict__ z)
  {
    long long const stride = static_cast<long long>(blockDim.x) * gridDim.x;
    for (long long i = static_cast<long long>(blockIdx.x) * blockDim.x + threadIdx.x; i < n;
         i += stride) {
      z[i] = a * x[i] + y[i];
    }
  }

  void check(cudaError_t const err, char const* what)
  {
    if (err != cudaSuccess) {
      throw std::runtime_error(std::string{what} + " failed: " + cudaGetErrorString(err));
    }
  }

  // Milliseconds between two recorded events. Waits for `stop` to complete first.
  float elapsed_ms(cudaEvent_t const start, cudaEvent_t const stop)
  {
    check(cudaEventSynchronize(stop), "cudaEventSynchronize");
    float ms = 0.f;
    check(cudaEventElapsedTime(&ms, start, stop), "cudaEventElapsedTime");
    return ms;
  }

  constexpr float a = 2.0f;
  constexpr int threads_per_block = 256;

}

namespace examples::gpu {

  int device_count()
  {
    int n = 0;
    if (cudaGetDeviceCount(&n) != cudaSuccess) {
      return 0;
    }
    return n;
  }

  saxpy_timing benchmark_saxpy(long long const n, int const iterations)
  {
    if (n < 1 || iterations < 1) {
      throw std::invalid_argument("benchmark_saxpy: n and iterations must be positive");
    }
    auto const n_elements = static_cast<std::size_t>(n);
    std::size_t const bytes = n_elements * sizeof(float);

    // 1. Host data, with values that are easy to check
    std::vector<float> x(n_elements), y(n_elements), z(n_elements), z_cpu(n_elements);
    for (std::size_t i = 0; i < n_elements; ++i) {
      x[i] = static_cast<float>(i % 1000) / 1000.f;
      y[i] = 1.f - x[i];
    }

    // 2. Device buffers and timing events
    float *d_x = nullptr, *d_y = nullptr, *d_z = nullptr;
    check(cudaMalloc(&d_x, bytes), "cudaMalloc x");
    check(cudaMalloc(&d_y, bytes), "cudaMalloc y");
    check(cudaMalloc(&d_z, bytes), "cudaMalloc z");
    cudaEvent_t start, stop;
    check(cudaEventCreate(&start), "cudaEventCreate");
    check(cudaEventCreate(&stop), "cudaEventCreate");

    saxpy_timing result{};
    result.n = n;
    result.iterations = iterations;

    // 3. Copy in (timed)
    check(cudaEventRecord(start), "cudaEventRecord");
    check(cudaMemcpy(d_x, x.data(), bytes, cudaMemcpyHostToDevice), "cudaMemcpy x");
    check(cudaMemcpy(d_y, y.data(), bytes, cudaMemcpyHostToDevice), "cudaMemcpy y");
    check(cudaEventRecord(stop), "cudaEventRecord");
    result.h2d_ms = elapsed_ms(start, stop);

    long long const blocks_needed = (n + threads_per_block - 1) / threads_per_block;
    auto const blocks = static_cast<unsigned int>(std::min<long long>(blocks_needed, 1LL << 20));

    // 4. Warm-up launch (not timed): the first launch pays one-off costs such as loading the
    //    kernel onto the device, which would make the first timing too slow.
    saxpy_kernel<<<blocks, threads_per_block>>>(n, a, d_x, d_y, d_z);
    check(cudaGetLastError(), "warm-up launch");
    check(cudaDeviceSynchronize(), "warm-up execution");

    // 5. Timed launches. Events are recorded in the GPU's own stream, so they measure GPU time,
    //    not the time the CPU spends queueing launches. Average over many launches.
    check(cudaEventRecord(start), "cudaEventRecord");
    for (int it = 0; it < iterations; ++it) {
      saxpy_kernel<<<blocks, threads_per_block>>>(n, a, d_x, d_y, d_z);
    }
    check(cudaEventRecord(stop), "cudaEventRecord");
    check(cudaGetLastError(), "timed launches");
    result.kernel_ms = elapsed_ms(start, stop) / iterations;

    // Effective bandwidth: each element reads x and y and writes z
    result.kernel_gbps = 3.0 * static_cast<double>(bytes) / (result.kernel_ms * 1.0e6);

    // 6. Copy out (timed)
    check(cudaEventRecord(start), "cudaEventRecord");
    check(cudaMemcpy(z.data(), d_z, bytes, cudaMemcpyDeviceToHost), "cudaMemcpy z");
    check(cudaEventRecord(stop), "cudaEventRecord");
    result.d2h_ms = elapsed_ms(start, stop);

    // 7. The same calculation on the CPU: a reference for the answer and for the time
    auto const cpu_start = std::chrono::steady_clock::now();
    for (std::size_t i = 0; i < n_elements; ++i) {
      z_cpu[i] = a * x[i] + y[i];
    }
    auto const cpu_stop = std::chrono::steady_clock::now();
    result.cpu_ms = std::chrono::duration<double, std::milli>(cpu_stop - cpu_start).count();

    // 8. Verify. A GPU may fuse a * x + y into one instruction, so allow a rounding difference.
    float max_err = 0.f;
    for (std::size_t i = 0; i < n_elements; ++i) {
      max_err = std::max(max_err, std::fabs(z[i] - z_cpu[i]));
    }
    result.max_abs_error = max_err;

    // 9. Clean up
    check(cudaEventDestroy(start), "cudaEventDestroy");
    check(cudaEventDestroy(stop), "cudaEventDestroy");
    check(cudaFree(d_x), "cudaFree x");
    check(cudaFree(d_y), "cudaFree y");
    check(cudaFree(d_z), "cudaFree z");
    return result;
  }

}
