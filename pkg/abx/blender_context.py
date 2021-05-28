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
from accumulate import UnionList, RecursiveDict
import yaml

def EnumFromList(schema, listname):
    return [(e, e.capitalize(), e.capitalize()) for e in schema[listname]]

prop_types = {
    'string':{
        'property': bpy.props.StringProperty,
        'keywords': { 'name', 'description', 'default', 'maxlen', 'options', 'subtype'},
        'translate': {
            'desc': ('description', None)}},
    'enum': {
        'property': bpy.props.EnumProperty,
        'keywords': { 'items', 'name', 'description', 'default', 'options'},
        'translate': {
            'desc': ('description', None),
            'items_from': ('items', EnumFromList)}},
    'int': {
        'property': bpy.props.IntProperty,
        'keywords': { 'name', 'description', 'default', 'min', 'max', 'soft_min', 'soft_max',
                      'step', 'options', 'subtype'},
        'translate': {
            'desc': ('description', None)}},
    'float': {
        'property': bpy.props.FloatProperty,
        'keywords': { 'name', 'description', 'default', 'min', 'max', 'soft_min', 'soft_max',
                      'step', 'options', 'subtype', 'precision', 'unit'},
        'translate': {
            'desc': ('description', None)}},
    'bool': {
        'property': bpy.props.BoolProperty,
        'keywords': { 'name', 'description', 'default', 'options', 'subtype'},
        'translate': {
            'desc': ('description', None)}}
    }

class AbxMeta(bpy.types.PropertyGroup):
    """
    Metadata property group factory for attachment to Blender object types.
    Definitions come from a YAML source (or default defined below).
    """
    default_schema = yaml.safe_load(io.StringIO("""\
---
blender:
    - id: project
      type: string
      level: project
      name: Project Name
      desc: Name of the project
      maxlen: 32
      
    - id: project_title
      type: string
      level: project
      name: Project Title
      desc: Full title for the project
      maxlen: 64
      
    - id: project_description
      type: string
      level: project
      name: Project Description
      desc: Brief description of the project
      maxlen: 128
      
    - id: project_url
      type: list string
      level: project
      name: Project URL
      desc: URL for Project home page, or comma-separated list of Project URLs
      
    - id: level
      type: enum
      items_from: levels
      name: Level
      desc: Level of the file in the project hierarchy
      
levels:
    - project
    - series
    - episode
    - seq
    - subseq
    - camera
    - shot
    - element
    - frame
    
hierarchies:
    - library
    - episodes
    """))
    
    def __new__(cls, schema=default_schema):  
        class CustomPropertyGroup(bpy.types.PropertyGroup):
            pass                  
        for definition in schema['blender']:
            # Translate and filter parameters
            try:
                propmap = prop_types[definition['type']]
            except KeyError:
                # If no 'type' specified or 'type' not found, default to string:
                propmap = prop_types['string']
                
            filtered = {}
            for param in definition:   
                if 'translate' in propmap and param in propmap['translate']:
                    filter = propmap['translate'][param][1]
                    if callable(filter):
                        # Filtered translation
                        filtered[propmap['translate'][param][0]] = filter(schema, definition[param])
                    else:
                        # Simple translation
                        filtered[propmap['translate'][param][0]] = definition[param]
                        
            # Create the Blender Property object
            kwargs = dict((key,filtered[key]) for key in propmap['keywords'] if key in filtered)   
            setattr(CustomPropertyGroup, definition['id'], propmap['property'](**kwargs))
                                                  
        bpy.utils.register_class(CustomPropertyGroup)
        return(CustomPropertyGroup)



class BlenderContext(RecursiveDict):
    """
    Dictionary accumulating data from sources within the currently-open Blender file.
    """
    filepath = ''
    defaults = {}
    
    def __init__(self):
        self.clear()
        
    @classmethod
    def update(cls):
        try:
            cls.file_metadata = bpy.data.window_managers['WinMan'].metadata
        except AttributeError:
            bpy.data.window_managers['WinMan'].new(FileMeta())
        
            
    def clear(self):
        for key in self:
            del self[key]
        self.update(self.defaults)
        
    
        
    
        