# tests_myproject_library.py
"""
Tests that use the 'myproject' test article and its 'library' to test features of loading
project files.
"""

import unittest, os
import yaml

import sys
print("__file__ = ", __file__)
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))

from abx import file_context


class TestLoadingSchemaHierarchies(unittest.TestCase):
    TESTDATA = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'testdata'))
    
    TESTPROJECTYAML = os.path.join(TESTDATA, 'myproject', 'myproject.yaml')
    
    TESTPATH = os.path.join(TESTDATA, 'myproject/Episodes/' +
                'A.001-Pilot/Seq/LP-LastPoint/' +
                'A.001-LP-1-BeginningOfEnd-anim.txt')
    
    TESTLIBPATH = os.path.join(TESTDATA, 'myproject/Library/' +
                'models/props/MyProp-By-me_here-prop.blend')
    
    def test_not_implemented_yet(self):
        print("Library schema override not implemented yet")
        self.assertTrue(True)
    
    # def test_load_std_schema_from_shotfile(self):
    #     # Probably duplicates test_file_context
    #     fc = file_context.FileContext(self.TESTPATH)
    #     print("\n")
    #     print( fc.schemas)    
    #     self.assertEqual(fc.schemas,
    #         None)
        
        
        
        
    