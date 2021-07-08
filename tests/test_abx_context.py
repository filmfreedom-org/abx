# test_abx_context.py


import unittest, os, collections

import yaml

# This is the most ridiculous work-around, but it seems to be necessary to
# get Python 3 to import the modules for testing 
import sys
print("__file__ = ", __file__)
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))

from abx import abx_context


class Test_ABX_Context(unittest.TestCase):
    
    TESTPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'testdata', 'myproject', 'Episodes', 'A.001-Pilot', 'Seq', 'LP-LastPoint', 'A.001-LP-1-BeginningOfEnd-anim.blend'))

    def test_abx_context_wo_file(self):
        bf = abx_context.ABX_Context()
        self.assertEqual(bf.filename, None)
        
    def test_abx_context_w_myproject(self):
        bf = abx_context.ABX_Context(self.TESTPATH)
        self.assertEqual(bf.filename, 'A.001-LP-1-BeginningOfEnd-anim.blend')
