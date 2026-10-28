"""Phlex source for a generator created during the DUNE-TECH tutorial.
"""

import numpy as np
import numpy.typing as npt

import phlex_config
from phlex import Variant

from my_tutorial_generator import generate


def PHLEX_REGISTER_PROVIDERS(s, config):
    """Register the generator as a provider of the event table.

    Configuration:
        layer: data layer to provide events in.
        creator, suffix: product names (defaults "pygen", "particles").

        <----- FOR THE TUTORIAL:
            You may add other configurable parameters you might need 
            within the generator you create. Describe them here
        ------>         

    Args:
        s (internal): Phlex source representation.
        config (internal): Phlex configuration representation.

    Returns:
        None
    """

    """<----- FOR THE TUTORIAL:
        Optional area for the configuration parameters
    ------>"""

    def provide(di): #di is the data cell index -- think of this like the event number
        
        """<----- FOR THE TUTORIAL:
            You may have other parameters in your function: add them after di.number()
        ------>""" 
        return generate(di.number())

    f = Variant(
        provide,
        {"di": "data_cell_index", "return": npt.NDArray[np.float64]},
        "generate",
    )
    s.provide(
        f,
        {
            "creator": phlex_config.get(config, "creator", "pygen"),
            "layer": config["layer"],
            "suffix": phlex_config.get(config, "suffix", "particles"),
        },
    )
