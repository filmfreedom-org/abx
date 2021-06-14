#!/usr/bin/env python3
"""
Test the file_context module.

This was written well after I wrote the module, and starts out as a conversion
from the doctests I had in the module already.
"""


import unittest, os
import yaml

import sys
print("__file__ = ", __file__)
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))

from abx import name_schema

from abx import ranks as ranks_mod

class FileContext_NameSchema_Interface_Tests(unittest.TestCase):
    """
    Test the interfaces presented by FieldSchema.
    
    FieldSchema is not really intended to be used from outside the
    file_context module, but it is critical to the behavior of the
    module, so I want to make sure it's working as expected.
    """    
    TESTDATA = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'testdata'))
    
    TESTPROJECTYAML = os.path.join(TESTDATA, 'myproject', 'myproject.yaml')
    
    TESTPATH = os.path.join(TESTDATA, 'myproject/Episodes/' +
                'A.001-Pilot/Seq/LP-LastPoint/' +
                'A.001-LP-1-BeginningOfEnd-anim.txt')

    
    # Normally from 'project_schema' in YAML
    TESTSCHEMA_LIST =[
                     {'rank': 'project', 'delimiter':'-', 'format':'{:s}', 'words':True},
                     {'rank': 'series',  'delimiter':'E', 'format':'{:2s}'},
                     {'rank': 'episode', 'delimiter':'-', 'format':'{!s:>02s}'},
                     {'rank': 'sequence','delimiter':'-', 'format':'{:2s}'},
                     {'rank': 'block',   'delimiter':'-', 'format':'{!s:1s}'},
                     {'rank': 'shot',    'delimiter':'-', 'format':'{!s:s}'},
                     {'rank': 'element', 'delimiter':'-', 'format':'{!s:s}'}]
    
    def test_NameSchema_create_single(self):
        ns = name_schema.FieldSchema(schema = self.TESTSCHEMA_LIST[0])
       
        # Test for ALL the expected properties:
        
        # Set by the test schema
        self.assertEqual(ns.rank, 'project')
        self.assertEqual(ns.delimiter, '-')
        self.assertEqual(ns.format, '{:s}')
        self.assertEqual(ns.words, True)
        self.assertEqual(ns.codetype, str)
        
        # Default values
        self.assertEqual(ns.pad, '0')
        self.assertEqual(ns.minlength, 1)
        self.assertEqual(ns.maxlength, 0)
        self.assertEqual(ns.default, None)
        
        # Candidates for removal:
        self.assertEqual(ns.irank, 0)   # Is this used at all?
        self.assertEqual(ns.parent, None)
        self.assertListEqual(list(ns.ranks),
            ['series', 'episode', 'sequence', 
             'block', 'camera', 'shot', 'element'])
        
    def test_NameSchema_load_chain_from_project_yaml(self):
        with open(self.TESTPROJECTYAML, 'rt') as yaml_file:
            data = yaml.safe_load(yaml_file)
        schema_dicts = data['project_schema']
        
        schema_chain = []
        last = None
        for schema_dict in schema_dicts:
            rank = schema_dict['rank']
            parent = last
            schema_chain.append(name_schema.FieldSchema(
                parent = parent,
                rank = rank,
                schema = schema_dict))
            last = schema_chain[-1]
            
        #print( schema_chain )
        
        self.assertEqual(len(schema_chain), 8)
        
        self.assertEqual(
            schema_chain[-1].parent.parent.parent.parent.parent.parent.parent.rank,
            'project')
        
        self.assertEqual(schema_chain[5].rank, 'camera')
        self.assertEqual(schema_chain[5].codetype[1], ('c2', 'c2', 'c2'))
        
    def test_FieldSchema_Branch_load_from_project_yaml(self):
        with open(self.TESTPROJECTYAML, 'rt') as yaml_file:
            data = yaml.safe_load(yaml_file)
        schema_dicts = data['project_schema']
        
        ranks = [s['rank'] for s in schema_dicts]
        
        branch = ranks_mod.Branch(
                    ranks_mod.Trunk,
                    data['project_unit'][-1]['code'],
                    1,
                    ranks)
        
        print("\nbranch = ", branch)
        
        print("\nbranch.rank('project') = ", repr(branch.rank('project')))
        
        self.assertTrue(False)
        
        
        
        
        