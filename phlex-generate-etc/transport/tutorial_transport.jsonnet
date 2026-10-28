{
  driver: {
    cpp: 'generate_layers',
    layers: {
      event: { parent: 'job', total: 4, starting_number: 1 },
    },
  },

  modules: {
    // Particle table -> HepMC3::GenEvent (creator 'input', suffix 'genevent')
    assemble: {
      cpp: 'genevent_from_table',
      input_layer: 'event',
    },
    edep_sim_tracking: {
      cpp: 'esp_tracking',
      input_layer: 'event',
      gdml: 'gdml/pdhd_like.gdml',
      ## This turns off the CPU-heavy photon simulation
      macro: '/process/optical/scintillation/setStackPhotons false\n',
    },
    edep_observables: {
     cpp: 'esp_observables',
     input_layer: 'event',
     input_from: 'edep_sim_tracking',  // consumes the TG4Event
    },
    hdf_out: {
     cpp: 'phlex_arrow_hdf_output',
     output_file: 'tutorial_obs.h5',  // writes all Arrow-typed products
    },
  },
}