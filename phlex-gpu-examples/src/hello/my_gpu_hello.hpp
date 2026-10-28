#ifndef MY_GPU_HELLO_HPP
#define MY_GPU_HELLO_HPP

// Plain C++ interface to the CUDA code in my_gpu_hello.cu.
//
// Nothing in this header is CUDA-specific, so the Phlex plugin that includes it is compiled by the
// ordinary C++ compiler (C++23, Phlex headers) and never by nvcc. Only my_gpu_hello.cu is compiled
// by nvcc. This is the same split as my_add.hpp / my_add.cpp in phlex-examples: a
// framework-agnostic library, plus a thin plugin that registers it with Phlex.

namespace examples::gpu {

  // Number of CUDA devices this process can see (0 if there is no GPU or no driver).
  int device_count();

  // Launch one block of n_threads GPU threads. Each thread prints
  //   Hello World from GPU thread <threadIdx.x>!
  // and increments a counter in device memory. Returns the counter, copied back to the host,
  // so the caller can check that every thread really ran.
  // Throws std::runtime_error if any CUDA call fails.
  int say_hello(int n_threads);

}

#endif // MY_GPU_HELLO_HPP
