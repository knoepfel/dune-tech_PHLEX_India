#include "my_saxpy_bench.hpp"

#include "phlex/module.hpp"

#include <cassert>
#include <cstdio>
#include <fstream>
#include <memory>
#include <string>

PHLEX_REGISTER_ALGORITHMS(m, config)
{
  using namespace phlex;
  using examples::gpu::saxpy_timing;

  auto const layer = config.get<std::string>("layer");
  auto const iterations = config.get<int>("iterations");
  auto const csv_file = config.get<std::string>("csv_file");

  // Transform: a problem size in, a saxpy_timing out. concurrency::serial gives each benchmark
  // the GPU to itself. With unlimited, several spills would share the GPU at once and every
  // timing would include the other benchmarks' work.
  m.transform(
     "saxpy_gpu",
     [iterations](int const log2_n) {
       return examples::gpu::benchmark_saxpy(1LL << log2_n, iterations);
     },
     concurrency::serial)
    .input_family(product_selector{.creator = "input", .layer = layer, .suffix = "log2_n"})
    .output_product_suffixes("timing");

  // Observer: check the answer, print a line and append a CSV row. serial, because every call
  // writes to the same file. Spills can finish in any order, so sort the CSV before plotting.
  auto csv = std::make_shared<std::ofstream>(csv_file);
  *csv << "n,iterations,h2d_ms,kernel_ms,d2h_ms,cpu_ms,kernel_gbps,max_abs_error\n";

  m.observe(
     "record",
     [csv](saxpy_timing const& t) {
       assert(t.max_abs_error < 1e-5f);
       *csv << t.n << ',' << t.iterations << ',' << t.h2d_ms << ',' << t.kernel_ms << ','
            << t.d2h_ms << ',' << t.cpu_ms << ',' << t.kernel_gbps << ',' << t.max_abs_error
            << '\n';
       csv->flush();
       double const gpu_total = t.h2d_ms + t.kernel_ms + t.d2h_ms;
       std::printf("n = %10lld | kernel %8.3f ms %7.1f GB/s | with copies %8.3f ms | "
                   "CPU %8.3f ms\n",
                   t.n,
                   t.kernel_ms,
                   t.kernel_gbps,
                   gpu_total,
                   t.cpu_ms);
     },
     concurrency::serial)
    .input_family(product_selector{.creator = "saxpy_gpu", .layer = layer, .suffix = "timing"});
}
