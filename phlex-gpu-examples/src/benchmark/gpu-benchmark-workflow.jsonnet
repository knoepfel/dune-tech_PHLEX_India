local first_log2_n = 12;  // smallest problem: 2^12 = 4096 floats
local n_sizes = 14;  // so the largest is 2^25 = 33.5 million floats (128 MB per vector)

{
  driver: {
    cpp: 'generate_layers',
    layers: {
      // One spill per problem size, numbered 0 to n_sizes - 1
      spill: { parent: 'job', total: n_sizes },
    },
  },
  sources: {
    sizes: {
      cpp: 'problem_size_source',
      layer: 'spill',
      first_log2_n: first_log2_n,
    },
  },
  modules: {
    bench: {
      cpp: 'saxpy_bench_and_record',
      layer: 'spill',
      iterations: 50,
      csv_file: 'saxpy_benchmark.csv',
    },
  },
}
