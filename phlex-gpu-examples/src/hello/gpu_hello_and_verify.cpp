#include "my_gpu_hello.hpp"

#include "phlex/module.hpp"

#include <cassert>

PHLEX_REGISTER_ALGORITHMS(m, config)
{
  using namespace phlex;

  auto const layer = config.get<std::string>("layer");

  // Transform: n_threads in, number of threads that greeted out. The operator is an ordinary
  // C++ function from the CUDA library. concurrency::serial because there is one GPU: one
  // launch at a time keeps the printed lines of different launches from mixing.
  m.transform("gpu_hello", examples::gpu::say_hello, concurrency::serial)
    .input_family(product_selector{.creator = "input", .layer = layer, .suffix = "n_threads"})
    .output_product_suffixes("greetings");

  // Observer: every thread that was launched must have said hello.
  m.observe(
     "verify_greetings",
     [](int const n_threads, int const greetings) { assert(greetings == n_threads); },
     concurrency::unlimited)
    .input_family(product_selector{.creator = "input", .layer = layer, .suffix = "n_threads"},
                  product_selector{.creator = "gpu_hello", .layer = layer, .suffix = "greetings"});
}
