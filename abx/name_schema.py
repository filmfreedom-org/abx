# name_schema.py
"""
Object for managing schema directives from project YAML and applying them to parsing and mapping name fields.
"""

import string, collections

from .ranks import RankNotFound, Rank, Branch, Trunk
    
class FieldSchema(object):
    """
    Represents a schema used for parsing and constructing a field in names.
    
    We need naming information in various formats, based on knowledge about
    the role of the Blender file and scene in the project. This object tracks
    this information and returns correct names based on it via properties.
    
    Note that FieldSchema is NOT an individual project unit name, but a defined
    pattern for how names are treat at that level in the project. It is a class
    of names, not a name itself. Thus "shot" has a schema, but is distinct from
    "shot A" which is a particular "project unit". The job of the schema is
    to tell us things like "shots in this project will be represented by
    single capital letters".
    
    See NameContext for the characteristics of a particular unit.
    
    Attributes:
        codetype (type):    Type of code name used for this rank.
                            Usually it will be int, str, or Enum.
                            Pre-defined enumerations are available
                            for uppercase letters (_letters) and
                            lowercase letters (_lowercase) (Roman --
                            in principle, other alphabets could be added).
        
        rank (Rank):        Rank of hierarchy under project (which is 0). The
                            rank value increases as you go "down" the tree.
                            Sorry about that confusion.
        
        
        ranks (Branch): List of named ranks known to schema (may include
                            both higher and lower ranks).
                            
        parent (|None):
                            Earlier rank to which this schema is attached.
        
        format (str):       Code for formatting with Python str.format() method.
                            Optional: format can also be specified with the
                            following settings, or left to default formatting.
        
        pad (str):          Padding character.
        minlength (int):    Minimum character length (0 means it may be empty).
        maxlength (int):    Maximum character length (0 means no limit).
        
        words (bool):       Treat name/title fields like a collection of words,
                            which can then be represented using "TitleCaps" or
                            "underscore_spacing", etc for identifier use.
                            
        delimiter (str):    Field delimiter marking the end of this ranks'
                            code in designations. Note this is the delimiter
                            after this rank - the higher (lower value) rank
                            controls the delimiter used before it.
                            
        default:            The default value for this rank. May be None, 
                            in which case, the rank will be treated as unset
                            until a setting is made. The UI must provide a
                            means to restore the unset value. Having no values
                            set below a certain rank is how a NameContext's
                            rank is determined.
                            
        Note that the rank may go back to a lower value than the schema's
        parent object in order to overwrite earlier schemas (for overriding a
        particular branch in the project) or (compare this to the use of '..'
        in operating system paths). Or it may skip a rank, indicating an
        implied intermediate value, which will be treated as having a fixed
        value.  (I'm not certain I want that, but it would allow us to keep
        rank numbers synchronized better in parallel hierarchies in a project).
        
        Note that schemas can be overridden at any level in a project by 
        'project_schema' directives in unit YAML files, so it is possible to
        change the schema behavior locally. By design, only lower levels in
        the hierarchy (higher values of rank) can be affected by overrides.
        
        This kind of use isn't fully developed yet, but the plan is to include
        things like managing 'Library' assets with a very different structure
        from shot files. This way, the project can split into 'Library' and
        'Episode' forks with completely different schemas for each.
    """
    # Defaults
    _default_schema = {
        'delimiter':'-',
        
        'type': 'string',
        'format':'{:s}',        
        'minlength':1,          # Must be at least one character
        'maxlength':0,          # 0 means unlimited
        'words': False,         # If true, treat value as words and spaces
        'pad': '0',             # Left-padding character for fixed length
        'default': None,
        
        'rank': 'project',
        'irank': 0,
        'ranks': ('series', 'episode', 'sequence',
                  'block', 'camera', 'shot', 'element')
        }
    
    # Really this is more like a set than a dictionary right now, but I
    # thought I might refactor to move the definitions into the dictionary:
    _codetypes = {
        'number':{}, 
        'string':{},
        'letter':{},
        'lowercase':{},
        }
    
    _letter = tuple((A,A,A) for A in string.ascii_uppercase)
    _lowercase = tuple((a,a,a) for a in string.ascii_lowercase)
        
    rank = 'project'
    irank = 0
    default = None
    
    #ranks = ('project',)
    branch = Trunk
    
    def __init__(self, parent=None, rank=None, schema=None, debug=False):
        """
        Create a FieldSchema from schema data source.
        
        FieldSchema is typically initialized based on data from YAML files
        within the project. This allows us to avoid encoding project structure
        into ABX, leaving how units are named up to the production designer.
        
        If you want our suggestions, you can look at the "Lunatics!" project's
        'lunatics.yaml' file, or the 'myproject.yaml' file in the ABX source
        distribution.
        
        Arguments:
            parent (FieldSchema):    
                           The level in the schema hierarchy above this one.
                           Should be None if this is the top.
                            
            rank (int):    The rank of this schema to be created.
            
            schema (dict): Data defining the schema, typically loaded from a
                           YAML file in the project.
                           
            debug (bool):  Used only for testing. Turns on some verbose output
                           about internal implementation.
        
        Note that the 'rank' is specified because it may NOT be sequential from
        the parent schema. 
        """
        # Three types of schema data:
        
        # Make sure schema is a copy -- no side effects!
        if not schema:
            schema = {}
        else:
            s = {}
            s.update(schema)
            schema = s
            
        if not rank and 'rank' in schema:
            rank = schema['rank']
        
        # Stepped down in rank from parent:
        self.parent = parent
        
        if parent and rank:
            # Check rank is defined in parent ranks and use that
            # We can skip optional ranks
            if rank in parent.ranks:
                j = parent.ranks.index(rank)
                self.ranks = parent.ranks[j+1:]
                self.rank = rank
            else:
                # It's an error to ask for a rank that isn't defined
                raise RankNotFound(
                    '"%s" not in defined ranks for "%s"' % (rank, parent))
                
        elif parent and not rank:
            # By default, get the first rank below parent
            self.rank = parent.ranks[0]
            self.ranks = parent.ranks[1:]
            
        elif rank and not parent:
            # With no parent, we're starting a new tree and renaming the root
            self.rank = rank
            self.ranks = self._default_schema['ranks']
            
        else: # not rank and not parent:
            # New tree with default rank
            self.rank = self._default_schema['rank']
            self.ranks = self._default_schema['ranks']
        
        # Directly inherited/acquired from parent
        # So far, only need a delimiter specified, but might be other stuff
        self.delimiter = self._default_schema['delimiter']
        if parent and parent.delimiter: self.delimiter = parent.delimiter
        
        # Explicit override by the new schema:
        if 'ranks'      in schema: self.ranks = schema['ranks']
        if 'delimiter'  in schema: self.delimiter = schema['delimiter'] 
        if 'default'    in schema:
            if schema['default'] == 'None':
                self.default = None
            else: 
                self.default = schema['default']
            
        # Default unless specified (i.e. not inherited from parent)
        newschema = {}
        newschema.update(self._default_schema)
        newschema.update(schema)
   
        self.format = str(newschema['format'])
        
        self.minlength = int(newschema['minlength'])
        self.maxlength = int(newschema['maxlength'])
        self.pad       = str(newschema['pad'])
        self.words     = bool(newschema['words'])
     
        if newschema['type'] == 'letter':
            self.codetype = self._letter
        
        elif newschema['type'] == 'lowercase':
            self.codetype = self._lowercase
                
        elif newschema['type'] == 'number':
            # Recognized Python types
            self.codetype = int
            if 'minlength' or 'maxlength' in schema:
                self.format = '{:0>%dd}' % self.minlength
                
        elif newschema['type'] == 'string':
            self.codetype = str
                
            if ('minlength' in schema) or ('maxlength' in schema):
                if self.maxlength == 0:
                    # Special case for unlimited length
                    self.format = '{:%1.1s>%ds}' % (self.pad, self.minlength)
                self.format = '{:%1.1s>%d.%ds}' % (
                                    self. pad, self.minlength, self.maxlength)
            
        elif newschema['type'] == 'bool':
                self.codetype = bool
                
        elif isinstance(newschema['type'], collections.Sequence):
            # Enumerated types
            # This is somewhat specific to Blender -- setting the 
            # enumeration values requires a sequence in a particular format
            self.codetype = []
            for option in newschema['type']:
                if type(option) is not str and isinstance(option, collections.Sequence):
                    option = tuple([str(e) for e in option][:3])
                else:
                    option = (str(option), str(option), str(option))
                self.codetype.append(option)
                
        elif isinstance(newschema['type'], collections.Mapping):
            self.codetype = []
            for key, val in newschema['type'].items():
                if type(val) is not str and isinstance(val, collections.Sequence):
                    if len(val) == 0:
                        option = (str(key), str(key), str(key))
                    elif len(val) == 1:
                        option = (str(key), str(val[0]), str(val[0]))
                    else:
                        option = (str(key), str(val[0]), str(val[1]))
                else:
                    option = (str(key), str(val), str(val))
                self.codetype.append(option)
        else:
            # If all else fails
            self.codetype = None
        
    def __repr__(self):
        return('<(%s).FieldSchema: %s (%s, %s, %s, (%s))>' % (
            repr(self.parent),
            #self.irank, 
            self.rank,
            self.delimiter,
            self.default,
            self.format,
            self.codetype
            ))
        
