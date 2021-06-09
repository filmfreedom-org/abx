# enum.py
"""
A custom enumeration type that supports ordering and Blender enum UI requirements.
"""


class Enum(dict):
    """
    List of options defined in a two-way dictionary.
    """
    def __init__(self, *options):
        """
        Args:
            *options (list): a list of strings to be used as enumerated values.
        """       
        for i, option in enumerate(options):
            if isinstance(option, list) or isinstance(option, tuple):
                name = option[0]
                self[i] = tuple(option)
            else:
                name = str(option)
                self[i] = (option, option, option)
            self[name] = i
            if name not in ('name', 'number', 'options'):
                setattr(self, name, i)
                
    @property
    def options(self):
        """
        Gives the options in a Blender-friendly format.
        
        Returns:
            A list of triples containing the three required fields for 
            Blender's bpy.props.EnumProperty.
        
        If the Enum was initialized with strings, the options will
        contain the same string three times. If initialized with
        tuples of strings, they will be used unaltered.
        """
        options = []
        number_keys = sorted([k for k in self.keys() if type(k) is int])
        return [self[i] for i in number_keys]
    
    def name(self, n):
        """
        Return the name (str) value of enum, regardless of which is provided.
        
        Args:
            n (str, int): An enum value (either number or string).
            
        Returns:
            Returns a string if n is recognized. Returns None if not.
        """
        if type(n) is int:
            return self[n][0]
        elif type(n) is str:
            return n
        else:
            return None
    
    def number(self, n):
        """
        Return the number (int) value of enum, regardless of which is provided.
        
        Args:
            n (str, int): An enum value (either number or string).
            
        Returns:
            Returns a number if n is recognized. Returns None if not.
        """
        if type(n) is str:
            return self[n]
        elif type(n) is int:
            return n
        else:
            return None
        
