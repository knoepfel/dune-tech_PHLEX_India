{
  driver: {
    // No extra layers: the job is the only data cell, so the kernel is launched once.
    cpp: 'generate_layers',
  },
  sources: {
    n_threads_source: {
      cpp: 'n_threads_source',
      layer: 'job',
      n_threads: 1,  // a single GPU thread
    },
  },
  modules: {
    hello: {
      cpp: 'gpu_hello_and_verify',
      layer: 'job',
    },
  },
}
