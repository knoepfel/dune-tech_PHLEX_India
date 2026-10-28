{
  driver: {
    cpp: 'generate_layers',
    layers: {
      event: { parent: 'job', total: 1, starting_number: 0 },
    },
  },
  sources: {
    // Python generator: provides a particle table (creator 'pygen', suffix 'particles')
    pygen: {
      py: 'my_tutorial_generator',
      layer: 'event',
      # You may add configuration here if you implement that within your generator
    },
  },
  modules: {
    // Particle table -> HepMC3::GenEvent (creator 'input', suffix 'genevent')
    assemble: {
      cpp: 'genevent_from_table',
      input_layer: 'event',
    },
    convert: {
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
