#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Transform nanopubs

"""
import os
import json
import yaml
import click
from typing import MutableMapping, Any, Iterator
import gzip
import re
from time import sleep

from bel import BEL
import bel.nanopub.files
import bel.nanopub.pubmed
import bel.nanopub.validate
import bel.nanopub.belscripts
import bel.nanopub.nanopubs

import bel.lang.migrate_1_2

from nptool.log_setup import get_logger

log = get_logger()

belapi_url = os.getenv('BELAPI_URL', 'https://api.bel.bio')

Nanopub = MutableMapping[str, Any]
bo = BEL()

np_hashes = {}

schema_fn = '/Users/william/belbio/schemas/schemas/nanopub_bel-1.0.0.yaml'

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
        "SpeciesNames": "Species",
    }
}


def typo_check(fn):

    if re.search('gz$', fn):
        f = gzip.open(fn, 'rt')
    else:
        try:
            f = click.open_file(fn, mode='rt')
        except Exception as e:
            log.info(f'Can not open file {fn}  Error: {e}')
            quit()

    flag = 0
    for line in f:
        if re.search('\)[-=][>|]\w+\(', line):
            print('Bad BELScript line', line)
            flag = 1
        elif re.search('\)\s+[-=][>|]\w+\(', line):
            print('Bad BELScript line', line)
            flag = 1
        elif re.search('\)[-=][>|]\s+\w+\(', line):
            print('Bad BELScript line', line)
            flag = 1

    if flag:
        quit()


def belscript(fn: str) -> Iterator[Nanopub]:
    """Convert belscript to nanopubs"""

    typo_check(fn)

    try:
        if re.search('gz$', fn):
            f = gzip.open(fn, 'rt')
        else:
            try:
                f = click.open_file(fn, mode='rt')
            except Exception as e:
                log.info(f'Can not open file {fn}  Error: {e}')
                quit()

        for nanopub in bel.nanopub.belscripts.parse_belscript(f):

            # print(json.dumps(nanopub, indent=4))

            yield nanopub

    except Exception as e:
        log.info(f'Could not process belscript {fn} {e}')
        quit()


def migrate1to2(nanopub: Nanopub) -> Nanopub:
    """Convert Nanopub to BEL 2.0.0 from BEL 1"""

    if 'nanopub' in nanopub:
        for idx, assertion in enumerate(nanopub['nanopub']['assertions']):

            belstr = f'{assertion["subject"]} {assertion["relation"]} {assertion["object"]}'

            try:
                nanopub['nanopub']['assertions'][idx] = bel.lang.migrate_1_2.migrate_into_components(belstr)
            except Exception as e:
                log.warning(f'Could not migrate {belstr}:  e')

        nanopub['nanopub']['type']['name'] = 'BEL'
        nanopub['nanopub']['type']['version'] = '2.0.0'

    return nanopub


def add_pubmed_info(nanopub: Nanopub) -> Nanopub:
    """Process Nanopub and add Pubmed info to it if possible"""

    # sleep for 10th of a second as Pubmed (with the api_key - see belbio_conf.yml) only allows 10 requests/sec
    sleep(0.5)

    # print(json.dumps(nanopub, indent=4))

    if 'nanopub' in nanopub:
        if 'citation' in nanopub['nanopub'] and nanopub['nanopub']['citation']:
            if 'database' in nanopub['nanopub']['citation']:
                if nanopub['nanopub']['citation']['database']['name'].lower() == 'pubmed':

                    pmid = nanopub['nanopub']['citation']['database']['id']
                    if pmid:
                        pubmed = bel.nanopub.pubmed.get_pubmed(pmid)
                        if pubmed:
                            if pubmed.get('authors'):
                                nanopub['nanopub']['citation']['authors'] = pubmed.get('authors')
                            if pubmed.get('title'):
                                nanopub['nanopub']['citation']['title'] = pubmed.get('title')
                            if pubmed.get('journal_title'):
                                nanopub['nanopub']['citation']['source_name'] = pubmed.get('journal_title')
                            if pubmed.get('pub_date'):
                                nanopub['nanopub']['citation']['date_published'] = pubmed.get('pub_date')

    return nanopub


def reformat_assertions(nanopub: Nanopub, fmt: str) -> Nanopub:
    """Reformat Assertions to short, medium or long form"""

    if 'nanopub' in nanopub:
        for idx, assertion in enumerate(nanopub['nanopub']['assertions']):
            s = assertion['subject']
            r = assertion.get('relation', '')
            o = assertion.get('object', '')

            triple = bo.parse(f'{s} {r} {o}').to_triple(fmt=fmt)
            if not triple.get('subject', False):
                log.info(f'S: {s}  R: {r}  O: {o}   Triple: {triple}')
                log.info('Skipping assertion')
                continue

            nanopub['nanopub']['assertions'][idx]['subject'] = triple['subject']
            if 'relation' in triple:
                nanopub['nanopub']['assertions'][idx]['relation'] = triple.get('relation')
                nanopub['nanopub']['assertions'][idx]['object'] = triple.get('object')

    return nanopub


def update_bel_ns(bel, ns_mappings):
    """Update Namespace Prefixes in BEL strings"""

    matches = re.findall('([A-Z]+):\S', bel)
    for match in matches:
        if match in ns_mappings['namespaces']:
            bel = bel.replace(match, ns_mappings['namespaces'][match])
    return bel


def remap_namespaces(nanopub: Nanopub, ns_mappings) -> Nanopub:
    """Process Nanopub and update Namespace prefixes and Annotation types"""

    if 'nanopub' in nanopub:
        for idx, anno in enumerate(nanopub['nanopub']['annotations']):
            anno_type = nanopub['nanopub']['annotations'][idx]['type']
            if anno_type in ns_mappings['annotations']:
                nanopub['nanopub']['annotations'][idx]['type'] = ns_mappings['annotations'][anno_type]
            if 'id' in nanopub['nanopub']['annotations'][idx]:
                nanopub['nanopub']['annotations'][idx]['id'] = update_bel_ns(nanopub['nanopub']['annotations'][idx]['id'], ns_mappings)

        for idx, assertion in enumerate(nanopub['nanopub']['assertions']):
            nanopub['nanopub']['assertions'][idx]['subject'] = update_bel_ns(nanopub['nanopub']['assertions'][idx]['subject'], ns_mappings)
            if 'object' in nanopub['nanopub']['assertions'][idx]:
                nanopub['nanopub']['assertions'][idx]['object'] = update_bel_ns(nanopub['nanopub']['assertions'][idx]['object'], ns_mappings)

    return nanopub


def update_bel_annotation(annotation):
    """Update BEL Annotations"""

    if not belapi_url:
        log.error('No BEL API defined in the environment - required to update BEL annotations')
        raise SystemExit

    url = f'{belapi_url}/terms/completions/{annotation["label"]}?annotation_types={annotation["type"]}&size=1'
    resp = bel.utils.get_url(url)

    if resp.status_code == 200:
        result = resp.json()
        if len(result['completions']) > 0:
            annotation['id'] = result['completions'][0]['id']
            if annotation['type'] == 'Species':
                annotation['label'] = result['completions'][0]['label']
        else:
            annotation['id'] = annotation['label']
    else:
        annotation['id'] = annotation['label']

    return annotation


def fix_annotations(nanopub: Nanopub) -> Nanopub:
    """Process Nanopub and update Namespace prefixes and Annotation types"""

    if 'nanopub' in nanopub:
        for idx, anno in enumerate(nanopub['nanopub']['annotations']):
            update_bel_annotation(anno)

            nanopub['nanopub']['annotations'][idx]['type'] = anno['type']
            nanopub['nanopub']['annotations'][idx]['id'] = anno.get('id', None)
            nanopub['nanopub']['annotations'][idx]['label'] = anno['label']

    return nanopub


def update_metadata(nanopub, metadata, del_md):

    if 'nanopub' in nanopub:
        # Delete metadata first
        for md_key in del_md:
            try:
                del nanopub['nanopub']['metadata'][md_key]
            except Exception:
                pass

        for key in metadata:
            if metadata[key] in ['False', 'false']:
                nanopub['nanopub']['metadata'][key] = False
            elif metadata[key] in ['True', 'true']:
                nanopub['nanopub']['metadata'][key] = True
            else:
                nanopub['nanopub']['metadata'][key] = metadata[key]

    return nanopub


def dedupe_nanopubs(nanopub: Nanopub) -> bool:
    """Check to see if duplicate Nanopub - return True if already seen"""

    if 'nanopub' in nanopub:
        np_hash = bel.nanopub.nanopubs.hash_nanopub(nanopub)
        if np_hash in np_hashes:
            return True
        np_hashes[np_hash] = 1
        return False
    else:
        return False


def validate_nanopub(nanopub):
    """Validate nanopub"""

    if 'nanopub' in nanopub:
        results = bel.nanopub.validate.validate(nanopub)
        if results['ERROR']['STRUCTURE'] or results['ERROR']['ASSERTION'] or results['ERROR']['ANNOTATION']:
            log.error(f'Nanopub Validation error: {json.dumps(results)}')
            if 'metadata' in nanopub:
                nanopub['nanopub']['metadata']['validation_errors'] = results
            else:
                nanopub['nanopub']['metadata'] = {'validation_errors': results}

    return nanopub


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--input_fn', '-i', default='-', help='See input_fn options above')
@click.option('--output_fn', '-o', default='-', help='See output_fn options above')
@click.option('--bel1', is_flag=True, default=False, help='Convert BEL1 to BEL 2.0.0')
@click.option('--pubmed', is_flag=True, default=False, help='Add pubmed info to nanopubs')
@click.option('--fmt', type=click.Choice(['short', 'medium', 'long']), help='Reformat to BEL Assertions to short, medium or long form')
@click.option('--remap_fn', help='Namespace prefixes/Annotation types input YAML file - otherwise use builtin defaults, see example format above')
@click.option('--remap', is_flag=True, default=False, help='Re-map namespace prefixes and annotation types - see default mappings above')
@click.option('--fix_anno', is_flag=True, default=False, help='Enhance annotations - set ID and Label if a match is found')
@click.option('--add_md_fn', help='Add metadata from file - see example YAML format above')
@click.option('--add_md', multiple=True, help='Add e.g. --add_md project=Test, can add multiple --add_md options')
@click.option('--del_md', multiple=True, help='Delete given metadata key from nanopub, e.g. --del_md project, can add multiple --del_md options, delete metadata happens before adding metadata')
@click.option('--dedupe', is_flag=True, default=False, help='Deduplicate nanopubs based on a hash of core nanopub fields')
@click.option('--validate', is_flag=True, default=False, help='Validate nanopubs, assertions, annotations, structure')
def main(input_fn, output_fn, bel1, pubmed, fmt, remap_fn, remap, fix_anno, add_md_fn, add_md, del_md, validate, dedupe):
    """Transform nanopubs

    np_transform.py

    \b
    input_fn:
        If input fn is '-', will read JSONLines from STDIN
        If input fn has *.gz, will read as a gzip file
        If input fn has *.jsonl*, will read as a JSONLines file
        IF input fn has *.json*, will be read as a JSON file with an array of Nanopubs
        If input fn has *.yaml* or *.yml*,  read be written as a YAML file
        If input fn has *.belscript* will read as a BELScript file

    \b
    output_fn:
        If output fn is '-', will write JSONLines to STDOUT
        If output fn has *.gz, will written as a gzip file
        If output fn has *.jsonl*, will written as a JSONLines file
        IF output fn has *.json*, will be written as a JSON file
        If output fn has *.yaml* or *.yml*,  will be written as a YAML file

    \b
    bel1to2: Convert BEL1 to BEL 2.0.0
    add_pubmed_info: Enhance nanopub with additional pubmed information


remap_fn YAML format:

\b
namespaces:
  GOCCID: GO
  MESHCS: MESH

\b
# Annotation maps
annotations:
  MeSHAnatomy: Anatomy
  Organism: Species

metadata YAML format:

\b
"project": "Project ABC"
"gd:creator": "Selventa"
"gd:published": true  # true or false - if missing defaults to false
"gd:validation": ""

Namespace prefix and Annotation Type mappings:

\b
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
    """

    cnt = 0
    batches = 100

    (out_fh, yaml_flag, jsonl_flag, json_flag) = bel.nanopub.files.create_nanopubs_fh(output_fn)
    # bad_nanopubs_fh = open('bad_nanopubs.json', 'wt')

    if yaml_flag or json_flag:
        docs = []

    # Collect namespace and annotation mappings
    ns_mappings = {}
    if remap_fn:
        ns_mappings = yaml.load(remap_fn)
        remap = True
    elif remap:
        ns_mappings = default_ns_mappings

    # Collect metadata
    metadata = {}
    if add_md_fn:
        metadata = yaml.load(add_md_fn)
    if add_md:
        for md in add_md:
            (key, val) = md.split('=')
            metadata[key] = val

    if 'belscript' in input_fn:
        for np in belscript(input_fn):
            if 'nanopub' in np:
                cnt += 1

            if cnt % batches == 0:
                log.info(f'Processed {cnt} nanopubs')

            if bel1:
                np = migrate1to2(np)
            if pubmed:
                np = add_pubmed_info(np)
            if fmt:
                np = reformat_assertions(np, fmt)
            if ns_mappings:
                np = remap_namespaces(np, ns_mappings)
            if fix_anno:
                np = fix_annotations(np)
            if metadata or del_md:
                np = update_metadata(np, metadata, del_md)
            if dedupe and dedupe_nanopubs(np):
                continue
            if validate:
                np = validate_nanopub(np)

            print('NP', json.dumps(np, indent=4))

            if yaml_flag or json_flag:
                docs.append(np)
            else:
                out_fh.write("{}\n".format(json.dumps(np)))

            # if cnt > 5:
            #     break
    else:
        for np in bel.nanopub.files.read_nanopubs(input_fn):
            if 'nanopub' in np:
                cnt += 1

            if cnt % batches == 0:
                log.info(f'Processed {cnt} nanopubs')

            if bel1:
                np = migrate1to2(np)
            if pubmed:
                np = add_pubmed_info(np)
            if fmt:
                np = reformat_assertions(np, fmt)
            if ns_mappings:
                np = remap_namespaces(np, ns_mappings)
            if fix_anno:
                np = fix_annotations(np)
            if metadata or del_md:
                np = update_metadata(np, metadata, del_md)

            if dedupe and dedupe_nanopubs(np):
                print('Skipping nanopub as it is a duplicate')
                continue
            if validate:
                np = validate_nanopub(np)

            if yaml_flag or json_flag:
                docs.append(np)
            else:
                out_fh.write("{}\n".format(json.dumps(np)))

    if yaml_flag:
        yaml.dump(docs, out_fh)

    elif json_flag:
        json.dump(docs, out_fh, indent=4)

    print(f'Processed {cnt} nanopubs')

    out_fh.close()


if __name__ == '__main__':
    main()
