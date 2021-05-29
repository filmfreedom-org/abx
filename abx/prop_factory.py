# blender_context.py
"""
Contextual metadata acquired from internal values in a Blender file.

This module must be invoked from within Blender to work, as it relies on the bpy Blender API
module and the currently-open Blender file's data graph in order to work.

It collects data about scenes, objects, groups, and other datablocks in the Blender file,
as well as data encoded in text blocks in different formats. Overall file data is incorporated
into a PropertyGroup attached to the "WindowManager" object identified as 'WinMan' (normally,
it appears there is only ever one of these in a Blender file, but if there is more than one, this
is the one that will be used).
"""

import io
import bpy, bpy.app, bpy.props, bpy.utils
from bpy.app.handlers import persistent
from .accumulate import UnionList, RecursiveDict
import yaml

def EnumFromList(schema, listname):
    return [(e, e.capitalize(), e.capitalize()) for e in schema[listname]]

def ExpandEnumList(schema, options):
    blender_options = []
    for option in options:
        if type(option) is str:
            blender_options.append((option, option, option))
        elif isinstance(option, tuple) or isinstance(option, list):
            option = tuple(option[0:3] + ([option[-1]]*(3-len(option))))
            blender_options.append(option)
    return blender_options

class PropertyGroupFactory(bpy.types.PropertyGroup):
    """
    Metadata property group factory for attachment to Blender object types.
    Definitions come from a YAML source (or default defined below).
    """
    # These values mirror the Blender documentation for the bpy.props types:
    prop_types = {
        'str':{
            'property': bpy.props.StringProperty,
            'keywords': { 'name', 'description', 'default', 'maxlen', 
                          'options', 'subtype'},
            'translate': {
                'desc': (None, 'description', None)}},
        'enum': {
            'property': bpy.props.EnumProperty,
            'keywords': { 'items', 'name', 'description', 'default', 'options'},
            'translate': {
                'desc': (None, 'description', None),
                'items_from': (EnumFromList, 'items'),
                'items': (ExpandEnumList, 'items')}},
        'int': {
            'property': bpy.props.IntProperty,
            'keywords': { 'name', 'description', 'default', 'min', 'max',
                          'soft_min', 'soft_max', 'step', 'options', 'subtype'},
            'translate': {
                'desc': (None, 'description')}},
        'float': {
            'property': bpy.props.FloatProperty,
            'keywords': { 'name', 'description', 'default', 'min', 'max',
                          'soft_min', 'soft_max', 'step', 'options', 
                          'subtype', 'precision', 'unit'},
            'translate': {
                'desc': (None, 'description')}},
        'bool': {
            'property': bpy.props.BoolProperty,
            'keywords': { 'name', 'description', 'default', 'options', 'subtype'},
            'translate': {
                'desc': (None, 'description')}}
        }
    
    def __new__(cls, name, schema):  
        class CustomPropertyGroup(bpy.types.PropertyGroup):
            pass                  
        for definition in schema[name]:
            # Translate and filter parameters
            try:
                propmap = cls.prop_types[definition['type']]
            except KeyError:
                # If no 'type' specified or 'type' not found, default to string:
                propmap = cls.prop_types['str']
                
            filtered = {}
            for param in definition:   
                if 'translate' in propmap and param in propmap['translate']:
                    translator = propmap['translate'][param][0]
                    if callable(translator):
                        # Filtered translation                        
                        filtered[propmap['translate'][param][1]] = translator(schema, definition[param])
                    else:
                        # Simple translation
                        filtered[propmap['translate'][param][1]] = definition[param]
                else:
                    filtered[param] = definition[param]
                        
            # Create the Blender Property object
            kwargs = dict((key,filtered[key]) for key in propmap['keywords'] if key in filtered)
            setattr(CustomPropertyGroup, definition['code'], propmap['property'](**kwargs))
                                                  
        bpy.utils.register_class(CustomPropertyGroup)
        return(CustomPropertyGroup)


    
        
    
        