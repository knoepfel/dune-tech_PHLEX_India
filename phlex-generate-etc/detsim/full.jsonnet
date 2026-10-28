{
  driver: {
    cpp: 'generate_layers',
    layers: {
      event: { parent: 'job', total: 1, starting_number: 1 },
    },
  },
  sources: {
    pygen: { /// <--- Our generator serves as a source for this job
      py: 'ccqe_generator',
      layer: 'event',
      muon_angle: 45,
      positions: ['-180 300 115']
    },
  },
  modules: {
   from_table: { /// <--- We convert the flat table created in the generator to a HepMC3::GenEvent
     cpp: 'genevent_from_table',
     input_layer: 'event',
   },
    edep_sim_tracking: {
      cpp: 'esp_tracking',
      input_layer: 'event',
      gdml: 'gdml/pdhd_like.gdml',
      // edep-sim's preamble leaves optical photons unstacked (killed) on the
      // CPU; turn scintillation stacking on so photons are tracked to the
      // photon-detector shell and land in TG4Event.PhotonDetectors.  (This is
      // the CPU optical path; the GPU plugin path is ddm-p5j.7.)
      macro: '/process/optical/scintillation/setStackPhotons false\n',
    },
    edep_observables: {
      cpp: 'esp_observables',
      input_layer: 'event',
      input_from: 'edep_sim_tracking',  // consumes the TG4Event
    },
    // --- Convert the edep observables' segments to a WCT TrackSegmentSet ---
    segments_to_tracksegmentset: {
      cpp: 'wire_cell_phlex_arrow_edep_segments',
      input_layer: 'event',
    },
    // --- Sample point depos from the segments -----------------------------
    // Ideal lines carry n_electrons directly, so use quanta mode (no recombination).
    sampler: {
      cpp: 'wcph_tracksegmentset_to_deposet',
      inputs: [{ creator: 'segments_to_tracksegmentset', layer: 'event', suffix: 'tracksegmentset' }],
      outputs: [{ suffix: 'deposet' }],
      wct_config: 'tracksegmentset-sampler.jsonnet',
      wct_plugins: ['WireCellGen', 'WireCellPgraph'],
      wct_tla: { ionization: 'recombination' },
    },

    drift: {
      cpp: 'wcph_deposet_filter',
      inputs: [{ creator: 'sampler', layer: 'event', suffix: 'deposet' }],
      outputs: [{ suffix: 'deposet' }],
      wct_config: 'dune/wct/job/drift.jsonnet',
      wct_plugins: ['WireCellGen', 'WireCellAux', 'WireCellPgraph'],
      wct_tla: { detector: 'pdhd', anode_index: '0', input: 'deposet' },
    },
    sim: {
      cpp: 'wcph_deposet_to_frame',
      inputs: [{ creator: 'drift', layer: 'event', suffix: 'deposet' }],
      outputs: [{ suffix: 'frame' }],
      wct_config: 'wc-cfg/sim.jsonnet',
      wct_plugins: ['WireCellGen', 'WireCellSigProc', 'WireCellAux', 'WireCellPgraph'],
      wct_tla: { detector: 'pdhd', anode_index: '0', input: 'drifted' },
    },
    
    sp: {
      cpp: 'wcph_frame_filter',
      inputs: [{ creator: 'sim', layer: 'event', suffix: 'frame' }],
      outputs: [{ suffix: 'frame' }],
      wct_config: 'wc-cfg/sigproc.jsonnet',
      wct_plugins: ['WireCellSigProc', 'WireCellAux', 'WireCellPgraph'],
      wct_tla: { detector: 'pdhd', anode_index: '0' },
    },
//
    // --- CHAIN B: DepoFluxSplat "true" signal (pre-drifted) ---------------
    splat: {
      cpp: 'wcph_deposet_to_frame',
      inputs: [{ creator: 'drift', layer: 'event', suffix: 'deposet' }],
      outputs: [{ suffix: 'frame' }],
      wct_config: 'dune/wct/job/splat.jsonnet',
      // FieldResponse (used by DepoFluxSplat for origin/drift-speed) is a
      // WireCellSigProc factory, so that plugin is required here too.
      wct_plugins: ['WireCellGen', 'WireCellSigProc', 'WireCellAux', 'WireCellPgraph'],
      wct_tla: { detector: 'pdhd', anode_index: '0', input: 'drifted' },
    },
    a_sampled: {
      cpp: 'wire_cell_phlex_arrow_convert',
      input_layer: 'event',
      input_creator: 'sampler',
      types: ['deposet'],
    },
    a_drifted: {
      cpp: 'wire_cell_phlex_arrow_convert',
      input_layer: 'event',
      input_creator: 'drift',
      types: ['deposet'],
    },
    a_sim: {
      cpp: 'wire_cell_phlex_arrow_convert',
      input_layer: 'event',
      input_creator: 'sim',
      types: ['frame'],
    },
    a_sp: {
      cpp: 'wire_cell_phlex_arrow_convert',
      input_layer: 'event',
      input_creator: 'sp',
      types: ['frame'],
    },
    a_splat: {
      cpp: 'wire_cell_phlex_arrow_convert',
      input_layer: 'event',
      input_creator: 'splat',
      types: ['frame'],
    },
    hdf_out: {
      cpp: 'phlex_arrow_hdf_output',
      output_file: 'obs.h5',  // writes all Arrow-typed products
    },
  },
}
