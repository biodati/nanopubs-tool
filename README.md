# nanopubs-tool

Tool to transform nanopubs (from BELscript), add pubmed info, add metadata, etc

## Setup

Make sure you are using Python 3.6+

Run following commands:

    git clone <nanopubs-tool repo>

    mv belbio_conf.yml.sample belbio_conf.yml

Edit belbio_conf.yml and update the XXX placeholders

    pip install pipenv

    pipenv install

    pipenv shell

    nptools.py --help


## Command help

    Usage: nptool.py [OPTIONS]

      Transform nanopubs

          np_transform.py

              input_fn:
                  If input fn is '-', will read JSONLines from STDIN
                  If input fn has *.gz, will read as a gzip file
                  If input fn has *.jsonl*, will read as a JSONLines file
                  IF input fn has *.json*, will be read as a JSON file with an array of Nanopubs
                  If input fn has *.yaml* or *.yml*,  read be written as a YAML file
                  If input fn has *.belscript* will read as a BELScript file

              output_fn:
                  If output fn is '-', will write JSONLines to STDOUT
                  If output fn has *.gz, will written as a gzip file
                  If output fn has *.jsonl*, will written as a JSONLines file
                  IF output fn has *.json*, will be written as a JSON file
                  If output fn has *.yaml* or *.yml*,  will be written as a YAML file

              bel1to2: Convert BEL1 to BEL 2.0.0
              add_pubmed_info: Enhance nanopub with additional pubmed information

      remap_fn YAML format:

      namespaces:
        GOCCID: GO
        MESHCS: MESH

      # Annotation maps
      annotations:
        MeSHAnatomy: Anatomy
        Organism: Species

      metadata YAML format:

      "gd:creator": "Selventa"
      "gd:published": true
      "project": "something"

      Namespace prefix and Annotation Type mappings:

      default_ns_mappings = {
          "namespaces": {
              "GOCCID": "GO",
              "GOBP": "GO",
              "GOCC": "GO",
              "GOBPID": "GO",
              "MESHCS": "MESH",
              "MESHPPID": "MESH",
              "MESHCID": "MESH",
              "MESHDID": "MESH",
              "MESHD": "MESH",
              "MESHPP": "MESH",
              "EGID": "EG",
              "DOID": "DO",
              "SPID": "SP",
              "CHEMBLID": "CHEMBL",
              "CHEBIID": "CHEBI",
          },
          "annotations": {
              "MeSHAnatomy": "Anatomy",
              "Organism": "Species",
              "SpeciesName": "Species",
          }
      }


    Options:
      -i, --input_fn TEXT        See input_fn options above
      -o, --output_fn TEXT       See output_fn options above
      --bel1                     Convert BEL1 to BEL 2.0.0
      --pubmed                   Add pubmed info to nanopubs
      --fmt [short|medium|long]  Reformat to BEL Assertions to short, medium or
                                 long form
      --remap_fn TEXT            Namespace prefixes/Annotation types input YAML
                                 file - otherwise use builtin defaults, see
                                 example format above
      --remap                    Re-map namespace prefixes and annotation types -
                                 see default mappings above
      --fix_anno                 Enhance annotations - set ID and Label if a match
                                 is found
      --add_md_fn TEXT           Add metadata from file - see example YAML format
                                 above
      --add_md TEXT              Add e.g. --add_md project=Test, can add multiple
                                 --add_md options
      --del_md TEXT              Delete given metadata key from nanopub, e.g.
                                 --del_md project, can add multiple --del_md
                                 options, delete metadata happens before adding
                                 metadata
      --dedupe                   Deduplicate nanopubs based on a hash of core
                                 nanopub fields
      --validate                 Validate nanopubs, assertions, annotations,
                                 structure
      --help                     Show this message and exit.
