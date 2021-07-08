# abx_context.py
"""
Simplified file-context information, used to determine the correct source
of ABX settings from 'abx.yaml' files in the project folders.

This is reduced from the earlier attempt to use the file_context system
which I've moved into KitCAT.
"""
import os, re, copy, string, collections
import yaml

DEFAULT_YAML = {}
with open(os.path.join(os.path.dirname(__file__), 'abx.yaml')) as def_yaml_file:
    DEFAULT_YAML.update(yaml.safe_load(def_yaml_file)) 


from . import accumulate
    
from .accumulate import RecursiveDict


class ABX_Context(object):
    """
    BlendFile context information.
    """
    filepath = None
    root = None
    folders = ()
    filename = None
    
    def __init__(self, path=None):
        self.clear()
        if path:
            self.update(path)
            
    def clear(self):
        """
        Clear contents of ABX_Context object.
        
        Nearly the same as reinitializing, but the notes
        attribute is left alone, to preserve the log history.
        """                
        # Identity
        self.root = os.path.abspath(os.environ['HOME'])
        self.render_root = os.path.join(self.root, 'Renders')
        self.role     = ''

        # Status / Settings
        self.filepath = None
        self.filename = None
        self.filetype = 'blend'
        self.file_exists = False
        self.folder_exists = False
        
        # Defaults
        self.provided_data = RecursiveDict(DEFAULT_YAML, source='default')
        self.abx_fields = DEFAULT_YAML['abx']
        self.render_profiles = {} #RenderProfileMap()
    
    def update(self, path):
        """
        Update the FileContext based on a new file path.
        """
        # Basic File Path Info
        self.filepath = os.path.abspath(path)
        self.filename = os.path.basename(path)
        
        # Does the file path exist?
        if os.path.exists(path):
            self.file_exists = True
            self.folder_exists = True
        else:
            self.file_exists = False
            if os.path.exists(os.path.dirname(path)):
                self.folder_exists = True
            else:
                self.folder_exists = False
            
        # Data from YAML Files                 
        #self._collect_yaml_data()
        self.provided_data = RecursiveDict(DEFAULT_YAML, source='default')
        
        kitcat_root, kitcat_data, abx_data = accumulate.get_project_data(self.filepath)
        self.root = kitcat_root
        self.provided_data.update(kitcat_data)
        path = os.path.abspath(os.path.normpath(self.filepath))
        root = os.path.abspath(self.root)
        self.folders = [os.path.basename(self.root)]
        self.folders.extend(os.path.normpath(os.path.relpath(path, root)).split(os.sep)[:-1])
        
        self.abx_fields = abx_data
        
        self.render_profiles = self.abx_fields['render_profiles']    
        
        try:
            self.render_root = os.path.join(self.root, 
                            self.provided_data['definitions']['render_root'])
        except KeyError:
            self.render_root = os.path.join(self.root, 'Renders') 
        


    