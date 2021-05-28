#!/usr/bin/env python3
"""
Test the render_profile module.

This has to be run from within Blender.
See:
    TestInBlender.py        (injector script - call this to run the tests)
    TestInBlender_bpy.py    (injected test-runner script)
"""


import unittest, os, textwrap
import yaml

import sys
print("__file__ = ", __file__)
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))

TESTDATA = os.path.join(os.path.abspath(__file__), '..', 'testdata')

TESTPATH = os.path.join(TESTDATA, 'myproject', 'Episodes', 'A.001-Pilot',
                        'Seq', 'LP-LastPoint', 'A.001-LP-1-BeginningOfEnd-anim.txt') 

import bpy

import abx
from abx import file_context
from abx import render_profile

class TestRenderProfile_Utils(unittest.TestCase):
    def test_bpy_is_present(self):
        self.assertTrue(abx.blender_present)
        
class TestRenderProfile_Implementation(unittest.TestCase):
    
    TESTDATA = os.path.abspath(os.path.join(__file__, '..', 'testdata'))
    
    TESTPATH = os.path.join(TESTDATA, 'myproject', 'Episodes', 'A.001-Pilot',
                'Seq', 'LP-LastPoint', 'A.001-LP-1-BeginningOfEnd-anim.blend')
    
    
    def setUp(self):
        self.fc0 = file_context.FileContext(bpy.data.filepath)
        self.fc1 = file_context.FileContext(self.TESTPATH)
        self.scene = bpy.context.scene
            
    def test_blendfile_context(self):
        self.assertEqual(self.fc0.filename, None)
        self.assertEqual(self.fc1.filename, 
                         'A.001-LP-1-BeginningOfEnd-anim.blend')
        
    def test_abx_data_retrieved_defaults(self):
        self.assertIn('render_profiles', self.fc0.abx_fields)
        
    def test_abx_data_retrieved_file(self):
        self.assertIn('render_profiles', self.fc1.abx_fields)
        
    def test_abx_data_default_full_profile_correct(self):
        FullProfile = render_profile.RenderProfile(
                        self.fc0.abx_fields['render_profiles']['full'])
        FullProfile.apply(self.scene)
        
        self.assertEqual(self.scene.render.fps, 30)
        self.assertEqual(self.scene.render.fps_base, 1.0)
        self.assertTrue(self.scene.render.use_motion_blur)
        self.assertTrue(self.scene.render.use_antialiasing)
        self.assertEqual(self.scene.render.antialiasing_samples, '8')
        self.assertEqual(self.scene.render.resolution_percentage, 100)
        self.assertEqual(self.scene.render.image_settings.compression, 50)
        
    
        
        
        