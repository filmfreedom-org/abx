# abx_schema.py
"""
Generalized fields-based parser based on provided schema.

Expands on the 'abx_episode' parser by allowing all the schema to
be defined by outside configuration data (generally provided in a
project YAML file, but this module does not depend on the data
source used).
"""

from . import registered_parser
    
@registered_parser
class Parser_ABX_Schema(object):
    """
    Parser based on using the list of schemas.    
    The schemas are normally defined in the project root directory YAML.
    
    The project YAML can additionally control parsing with this parser:
    
    ---
    definitions:
        parser: abx_schema                 # Force use of this parser
        
        parser_options:                    # Set parameters
            filetype_separator:    '.'
            comment_separator:     '--'
            role_separator:        '-'
            title_separator:       '-'
    
        filetypes:                         # Recognized filetypes.
            blend:    Blender File         # <filetype>: documentation
            ...
            
        roles:                             # Recognized role fields.
            anim:    Character Animation   # <role>: documentation
            ...
            
        roles_by_filetype:                 # Roles implied by filetype.
            kdenlive: edit                 # <filetype>:<role>
            ...
            
        (For the full default lists see abx/abx.yaml). 
    
    schemas (list):    The current schema-list defining how filenames should be parsed.
                       This "Schema" parser uses this to determine both parsing and
                       mapping of text fields in the filename.
                       
    definitions(dict): The project definitions currently visible to the parser.    
    """
    name = 'abx_schema'
    
    def __init__(self, schemas=None, definitions=None,
                    filetype_separator = '.',
                    comment_separator = '--',
                    role_separator = '-',
                    title_separator = '-', 
                    **kwargs):
        
        self.filetype_separator = filetype_separator
        self.comment_separator = comment_separator
        self.role_separator = role_separator
        self.title_separator = title_separator
        
        self.schemas = schemas
        
        if 'roles' in definitions:
            self.roles = definitions['roles']
        else:
            self.roles = []
            
        if 'filetypes' in definitions:
            self.filetypes = definitions['filetypes']
        else:
            self.filetypes = []
            
        if 'roles_by_filetype' in definitions:
            self.roles_by_filetype = definitions['roles_by_filetype']
        else:
            self.roles_by_filetype = []
            
    def _parse_ending(self, filename, separator):
        try:
            remainder, suffix = filename.rsplit(separator, 1)
            score = 1.0
        except ValueError:
            remainder = filename
            suffix = None
            score = 0.0
        return (suffix, remainder, score)
    
    def _parse_beginning(self, filename, separator):
        try:
            prefix, remainder = filename.split(separator, 1)
            score = 1.0
        except ValueError:
            prefix = filename
            remainder = ''
            score = 0.0
        return (prefix, remainder, score) 
    
    def __call__ (self, filename, namepath, debug=False):
        fields = {}
        score = 0.0
        possible = 0.0
               
        # First get specially-handled extensions
        remainder = filename
        field, newremainder, s = self._parse_ending(remainder, self.filetype_separator)
        if field and field in self.filetypes:
            remainder = newremainder
            fields['filetype'] = field
            score += s*1.0
        else:
            fields['filetype'] = None
        
        field, remainder, s = self._parse_ending(remainder, self.comment_separator)
        fields['comment'] = field
        score += s*0.5
        
        field, newremainder, s = self._parse_ending(remainder, self.role_separator)
        if field and field in self.roles:
            remainder = newremainder
            fields['role'] = field
            score += s*0.5
        else:
            fields['role'] = None
            
        field, remainder, s = self._parse_ending(remainder, self.title_separator)
        fields['title'] = field
        score += s*0.5
            
        possible += 3.0
        
        # Implicit roles
        if (    not fields['role'] and 
                fields['filetype'] and 
                fields['role'] in self.roles_by_filetype):
            self.role = self.roles_by_filetype[fields['filetype']]
            score += 0.2
            
        #possible += 0.2
                    
        # Figure the rest out from the schema
        # Find the matching rank start position for the filename
        start = 0
        for start, (schema, name) in enumerate(zip(self.schemas, namepath)):
            field, r, s = self._parse_beginning(remainder, schema.delimiter)
            try:
                if field.lower() == schema.format.format(name).lower():
                    score += 1.0
                    break
            except ValueError:
                print(' (365) field, format', field, schema.format)
            
        possible += 1.0
            
        # Starting from that position, try to match fields
        # up to the end of the namepath (checking against it)
        irank = 0
        for irank, (schema, name) in enumerate(
                zip(self.schemas[start:], namepath[start:])):
            if not remainder: break
            field, remainder, s = self._parse_beginning(remainder, schema.delimiter)
            score += s
            try:
                if ( type(field) == str and
                     field.lower() == schema.format.format(name).lower()):
                    fields[schema.rank]={'code':field}
                    fields['rank'] = schema.rank
                    score += 1.0
            except ValueError:
                print(' (384) field, format', field, schema.format)
            possible += 2.0
        
        # Remaining fields are authoritative (doesn't affect score)
        for schema in self.schemas[irank:]:
            if not remainder: break
            field, remainder, s = self._parse_beginning(remainder, schema.delimiter)
            fields[schema.rank]={'code':field}
            fields['rank'] = schema.rank
                           
        if 'rank' in fields:
            fields[fields['rank']]['title'] = fields['title']
            
        if not fields['role'] and fields['filetype'] in self.roles_by_filetype:
            fields['role'] = self.roles_by_filetype[fields['filetype']]
        
        return score/possible, fields
