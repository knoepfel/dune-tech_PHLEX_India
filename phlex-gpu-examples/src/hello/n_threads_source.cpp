#include "phlex/configuration.hpp"
#include "phlex/model/data_cell_index.hpp"
#include "phlex/source.hpp"

using namespace phlex;

// Provides the launch size as a data product: one "n_threads" for every data cell of the
// configured layer. With layer 'job' there is exactly one data cell, so one kernel launch.
PHLEX_REGISTER_PROVIDERS(m, config)
{
  auto const layer = config.get<std::string>("layer");
  auto const n_threads = config.get<int>("n_threads");

  m.provide("provide_n_threads", [n_threads](data_cell_index const&) -> int { return n_threads; })
    .output_product("input", "n_threads", experimental::identifier{layer});
}
