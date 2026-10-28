// Run the CUDA library on its own, without Phlex: the quickest way to check the GPU works.
#include "my_gpu_hello.hpp"

#include <cstdio>
#include <exception>

int main()
{
  int const n_devices = examples::gpu::device_count();
  std::printf("CUDA devices visible: %d\n", n_devices);
  if (n_devices == 0) {
    std::printf("No GPU visible to this process. Nothing to launch.\n");
    return 1;
  }

  try {
    int const greeted = examples::gpu::say_hello(1); // a single GPU thread
    std::printf("Threads that said hello: %d\n", greeted);
    return greeted == 1 ? 0 : 1;
  }
  catch (std::exception const& e) {
    std::printf("CUDA error: %s\n", e.what());
    return 1;
  }
}
