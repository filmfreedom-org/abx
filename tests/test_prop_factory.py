# test_prop_factory
"""
Test custom Blender property-group factory module.
"""

import unittest, os, textwrap, io

# This is the most ridiculous work-around, but it seems to be necessary to
# get Python 3 to import the modules for testing 
import sys
print("__file__ = ", __file__)
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))

import yaml

import bpy

from abx import prop_factory


class TestPropertyGroupFactory(unittest.TestCase):    
    SIMPLE = textwrap.dedent("""\
        ---
        my_custom_property_group:
            - code: prop1
              name: prop1
              type: str
              maxlen: 20
              default: default
              desc: My test property.
        """)
    
    SAMPLER = textwrap.dedent("""\
        ---
        sampler:
            - code: str_prop
              name: MyString
              type: str
              maxlen: 20
              default: str_prop
              desc: A string property example.
              
            - code: int_prop
              name: MyInteger
              type: int
              min: 0
              max: 100
              soft_min: 0
              soft_max: 10
              default: 1
              desc: An integer property example.
              
            - code: float_prop
              name: MyFloat
              type: float
              min: -10.0
              max: 10.0
              soft_min: 0.0
              soft_max: 1.0
              precision: 3
              unit: 'LENGTH'
              default: 1.0
              desc: A float property example.
              
            - code: bool_prop
              name: MyBoolean
              type: bool
              default: False
              desc: A boolean property example.
              
            - code: enum_prop1
              name: MyEnum1
              type: enum
              items_from: enum1_list
              default: 'unknown'
              desc: An enumerated property using a list reference.
              
            - code: enum_prop2
              name: MyEnum2
              type: enum
              items:
                  - op1
                  - op2
                  - op3
              default: op1
              desc: An enumerated property using a direct list of strings.
              
            - code: enum_prop3
              name: MyEnum3
              items:
                  - op1
                  - ('op2', 'Option2')
                  - ('op3', 'Option3', 'Option Three')
              default: op1
              desc: An enumerated property using direct list with mixed types.
              
        enum1_list:
            - unknown
            - option1
            - option2
        """)        
    
    def assertHasAttr(self, ob, attr):
        self.assertTrue(hasattr(ob,attr),
            msg="Object %s has no attribute %s." % (ob, attr))
    
    def test_creating_simple_yaml_example(self):
        schema = yaml.safe_load(io.StringIO(self.SIMPLE))
        cpg = prop_factory.PropertyGroupFactory(
            'my_custom_property_group', schema)
        
        self.assertHasAttr(cpg, 'prop1')
        
    def test_attach_simple_yaml_to_scene(self):
        schema = yaml.safe_load(io.StringIO(self.SIMPLE))
        cpg = prop_factory.PropertyGroupFactory(
            'my_custom_property_group', schema)
        
        bpy.types.Scene.my_custom_property_group = bpy.props.PointerProperty(type=cpg)
        
        self.assertEqual(
            bpy.context.scene.my_custom_property_group.prop1, 
            'default')
        
    def test_creating_and_attaching_complex_sampler(self):
        schema = yaml.safe_load(io.StringIO(self.SAMPLER))
        sampler = prop_factory.PropertyGroupFactory(
            'sampler', schema)
        bpy.types.Scene.sampler = bpy.props.PointerProperty(type=sampler)
        
        self.assertEqual(bpy.context.scene.sampler.str_prop, 'str_prop')
        self.assertEqual(bpy.context.scene.sampler.int_prop, 1)
        self.assertEqual(bpy.context.scene.sampler.float_prop, 1.0)
        self.assertEqual(bpy.context.scene.sampler.bool_prop, False)
        self.assertEqual(bpy.context.scene.sampler.enum_prop1, 'unknown')
        self.assertEqual(bpy.context.scene.sampler.enum_prop2, 'op1')
        self.assertEqual(bpy.context.scene.sampler.enum_prop3, 'op1')
        
        bpy.context.scene.sampler.str_prop = 'my string'
        bpy.context.scene.sampler.int_prop = 2
        bpy.context.scene.sampler.float_prop = 0.7
        bpy.context.scene.sampler.bool_prop = True
        bpy.context.scene.sampler.enum_prop1 = 'option1'
        bpy.context.scene.sampler.enum_prop2 = 'op2'
        bpy.context.scene.sampler.enum_prop3 = 'op3'
        
        self.assertEqual(bpy.context.scene.sampler.str_prop, 'my string')
        self.assertEqual(bpy.context.scene.sampler.int_prop, 2)
        self.assertAlmostEqual(bpy.context.scene.sampler.float_prop, 0.7)
        self.assertEqual(bpy.context.scene.sampler.bool_prop, True)
        self.assertEqual(bpy.context.scene.sampler.enum_prop1, 'option1')
        self.assertEqual(bpy.context.scene.sampler.enum_prop2, 'op2')
        self.assertEqual(bpy.context.scene.sampler.enum_prop3, 'op3')
        
        
        
        
        
        
        