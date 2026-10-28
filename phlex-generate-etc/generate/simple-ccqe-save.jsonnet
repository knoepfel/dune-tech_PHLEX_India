{
  driver: {
    cpp: 'generate_layers',
    layers: {
      event: { parent: 'job', total: 1, starting_number: 0 },
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
    assemble: { /// <--- We convert the flat table created in the generator to a HepMC3::GenEvent
      cpp: 'genevent_from_table',
      input_layer: 'event',
    },
    convert: { /// <--- This step converts the HepMC3::GenEvent into a HepMC3::GenEventData
      cpp: 'convert_hepmcevent_to_data',
      input_layer: 'event',
    },
    // Write data product to output file
    output: {
      cpp: 'form_module',
      products: ['converted'],
    },
  },
}
