# abx_fallback.py
"""
Fallback parser used in case others fail.

The fallback parser makes only a very minimal and robust set of assumptions.

Any legal filename will successfully return a simple parse, though much
interpretation may be lost. It still allows for common field-based practices,
but falls back on using the unaltered filename if necessary.
"""

import re, os

import yaml

from . import registered_parser


DEFAULT_YAML = {}
with open(os.path.join(os.path.dirname(__file__), '..', 'abx.yaml')) as def_yaml_file:
    DEFAULT_YAML.update(yaml.safe_load(def_yaml_file)) 


    
@registered_parser
class Parser_ABX_Fallback(object):
    """
    Highly-tolerant parser to fall back on if others fail.
    
    Makes very minimal assumptions about filename structure.
    
    YAML options available:
    
    ---
    definitions:
        parser: abx_fallback                # Force use of this parser.
        
    There are no other options. Field separators are defined very broadly,
    and include most non-word characters (~#$!=+&_-). This was mostly designed
    to work without a project schema available.    
    """
    name = 'abx_fallback'
    
    filetypes   = DEFAULT_YAML['definitions']['filetypes']
    roles       = DEFAULT_YAML['definitions']['roles']
    roles_by_filetype = (
                  DEFAULT_YAML['definitions']['roles_by_filetype'])
    
    main_sep_re     = re.compile(r'\W+') # Any single non-word char
    comment_sep_re  = re.compile(r'[\W_][\W_]+|[~#$!=+&]+')
    
    
    def __init__(self, **kwargs):
        pass
            
    def _parse_ending(self, filename, separator):
        try:
            remainder, suffix = filename.rsplit(separator, 1)
            score = 1.0
        except ValueError:
            remainder = filename
            suffix = None
            score = 0.0
        return (suffix, remainder, score)
    
    def __call__(self, filename, namepath):
        fields = {}
        score = 1.0
        possible = 4.5
        
        split = filename.rsplit('.', 1)
        if len(split)<2 or split[1] not in self.filetypes:
            fields['filetype'] = None
            remainder = filename
            score += 1.0
        else:
            fields['filetype'] = split[1]
            remainder = split[0]
            
        comment_match = self.comment_sep_re.search(remainder)
        if comment_match:
            fields['comment'] = remainder[comment_match.end():]
            remainder = remainder[:comment_match.start()]
        else:
            fields['comment'] = None
        
        role = self.main_sep_re.split(remainder)[-1]      
        if role in self.roles:
            fields['role'] = role
            remainder = remainder[:-1-len(role)]
            score += 1.0
        else:
            fields['role'] = None
        
        # Implied role
        if fields['filetype'] in self.roles_by_filetype:
            fields['role'] = self.roles_by_filetype[fields['filetype']]
            score += 1.0        
        
        words = self.main_sep_re.split(remainder)
        fields['code']  = ''.join([w.capitalize() for w in words])
        fields['title'] = remainder
        
        return score/possible, fields
        
