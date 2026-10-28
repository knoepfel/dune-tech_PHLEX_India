#include "phlex/configuration.hpp"
#include "phlex/model/data_cell_index.hpp"
#include "phlex/source.hpp"

using namespace phlex;

// Each spill gets one problem size: log2_n = first_log2_n + spill number.
// With first_log2_n = 12 and 14 spills (numbered 0 to 13), the job scans n = 2^12 ... 2^25.
PHLEX_REGISTER_PROVIDERS(m, config)
{
  auto const layer = config.get<std::string>("layer");
  auto const first_log2_n = config.get<int>("first_log2_n");

  m.provide("provide_log2_n",
            [first_log2_n](data_cell_index const& id) -> int {
              return first_log2_n + static_cast<int>(id.number());
            })
    .output_product("input", "log2_n", experimental::identifier{layer});
}
