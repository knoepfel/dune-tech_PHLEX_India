#include "my_gpu_hello.hpp"

#include <cuda_runtime.h>

#include <cstdio>
#include <stdexcept>
#include <string>

namespace {

  // The kernel: runs on the GPU, once per thread.
  __global__ void hello_kernel(int* greeted)
  {
    printf("Hello World from GPU thread %d!\n", threadIdx.x);
    atomicAdd(greeted, 1); // count the threads that ran
  }

  void check(cudaError_t const err, char const* what)
  {
    if (err != cudaSuccess) {
      throw std::runtime_error(std::string{what} + " failed: " + cudaGetErrorString(err));
    }
  }

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

  int say_hello(int const n_threads)
  {
    if (n_threads < 1 || n_threads > 1024) {
      throw std::invalid_argument("say_hello: one block holds 1 to 1024 threads, got " +
                                  std::to_string(n_threads));
    }

    int* d_greeted = nullptr;
    check(cudaMalloc(&d_greeted, sizeof(int)), "cudaMalloc");
    check(cudaMemset(d_greeted, 0, sizeof(int)), "cudaMemset");

    // <<<blocks, threads per block>>>: one block of n_threads threads
    hello_kernel<<<1, n_threads>>>(d_greeted);
    check(cudaGetLastError(), "kernel launch"); // bad launch configuration, no device, ...

    // Kernel launches are asynchronous. Waiting here also flushes the device-side printf buffer.
    check(cudaDeviceSynchronize(), "kernel execution");
    std::fflush(stdout);

    int greeted = 0;
    check(cudaMemcpy(&greeted, d_greeted, sizeof(int), cudaMemcpyDeviceToHost), "cudaMemcpy");
    check(cudaFree(d_greeted), "cudaFree");
    return greeted;
  }

}
