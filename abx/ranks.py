# ranks.py
"""
Branches and ranks objects.

Objects for representing the ranks of a hierarchy, with the 
possibility of branching at nodes with redefined ranks via
the 'project_schema' directives in project YAML files.
"""
    
class RankNotFound(LookupError):
    """
    Error returned if an unexpected 'rank' is encountered.
    """
    pass

class Branch(object):
    """
    Branch represents a ranking system in the tree of schemas.
    
    It takes the name of the project_unit where the ranking system
    is overridden, and controls how all ranks defined within it
    are interpreted.
    """
    def __init__(self, parent, code, start, ranks):
        self.parent = parent
        self.code = str(code)
        self.start = int(start)
        
        self._ranks = RankList(self,[])
        if parent:
            for rank in parent.ranks:
                if int(rank) < start:
                    self._ranks.append(rank)
            
        for num, name in enumerate(ranks):
            rank = Rank(self, num + start, name)
            self._ranks.append(rank)
            
    def __repr__(self):
        ranklist = ', '.join([str(r) for r in self.ranks[1:]])
        if self.code:
            code = self.code
        else:
            code = 'Trunk'
        return "<branch '%s': %s>" % (code, ranklist)
    
    def __contains__(self, other):
        if isinstance(other, Rank) and other in self._ranks:
            return True
        else:
            return False
            
    def rank(self, n):
        """
        Coerce int or string to rank, if it matches a rank in this Branch.
        """
        if isinstance(n, int) and 0 < n < len(self._ranks):
            return self._ranks[n]
        elif isinstance(n, str):
            if n.lower()=='trunk':
                return self._ranks[0]
            for rank in self._ranks:
                if str(rank) == n:
                    return rank
        elif n==0:
            self._ranks[0]
        else:
            raise TypeError
            
    @property
    def ranks(self):
        # Read-only property.
        return self._ranks
    

            
class Rank(object):
    """
    Ranks are named numbers indicating the position in a hierarchy.
    
    They can be incremented and decremented. The value 0 represents the top
    rank, with increasing numbers indicating finer grades in taxonomic rank.
    
    They can have integers added to or subtracted from them, meaning to go
    down or up in rank. They cannot be added to each other, though. Note that
    higher and lower rank in the real world since of more or less scope is
    inverted as a number -- the lower rank has a higher number.
    
    There are upper and lower bounds to rank, defined by the schema 'Branch'.
    
    Coercing a rank to an integer (int()) returns the numeric rank.
    
    Coercing a rank to a string (str()) returns the rank name.
    
    The representation includes the branch name and rank name.
    
    Ranks can be subtracted, returning an integer representing the difference
    in rank.
    """
    def __init__(self, branch, num, name):
        self.num = num
        self.name = name
        self.branch = branch
        
    def __index__(self):
        return self.num
        
    def __int__(self):
        return self.num
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return '<%s:%d-%s>' % (self.branch.code, self.num, self.name)
    
    def __hash__(self):
        return hash((self.branch, self.num, self.name))
    
    def __eq__(self, other):
        if isinstance(other, Rank):
            if hash(self) == hash(other):
                return True
            else:
                return False
        elif isinstance(other, str):
            if other == self.name:
                return True
            else:
                return False
        elif isinstance(other, int):
            if other == self.num:
                return True
            else:
                return False
        else:
            return False
        
    def __gt__(self, other):
        if isinstance(other, Rank):
            if self.num > other.num:
                return True
            else:
                return False
        elif isinstance(other, int):
            if self.num > other:
                return True
            else:
                return False
        else:
            raise TypeError("Rank can't compare to %s" % type(other))
        
    def __lt__(self, other):
        if isinstance(other, Rank):
            if self.num < other.num:
                return True
            else:
                return False
        elif isinstance(other, int):
            if self.num < other:
                return True
            else:
                return False
        else:
            raise TypeError("Rank can't compare to %s" % type(other))
        
    def __ge__(self, other):
        return (self > other or self == other)
    
    def __le__(self, other):
        return (self < other or self == other)

        
    def __add__(self, other):
        if isinstance(other, int):
            if (self.num + other) < len(self.branch.ranks):
                return self.branch.ranks[self.num+other]
            elif (self.num + other) < 1:
                return Trunk
            else:
                return None
        else:
            raise TypeError("Changes in rank must be integers.")
        
    def __radd__(self, other):
        return self.__add__(other)
    
    def __sub__(self, other):
        if isinstance(other, Rank):
            return (self.num - other.num)
        elif isinstance(other, int):
            if 0 < (self.num - other) < len(self.branch.ranks):
                return self.branch.ranks[self.num-other]
            elif (self.num - other) < 1:
                return Trunk
            elif (self.num - other) > len(self.branch.ranks):
                return None
        else:
            raise TypeError("Rank subtraction not defined for %s" % type(other))
        
    def __rsub__(self, other):
        if isinstance(other, Rank):
            return (other.num - self.num)
        else:
            raise TypeError("Rank subtraction not defined for %s" % type(other))


class RankList(list):
    """
    Convenience wrapper for a list of ranks, with simplified look-up.
    
    This allows indexes and slices on the ranks to use Rank objects and/or
    string names in addition to integers for accessing the elements of the
    list.
    
    The RankList also has to know what branch it is indexing, so it includes
    a 'branch' attribute.
    """
    def __init__(self, branch, ranks):
        self.branch = branch
        for rank in ranks:
            self.append(rank)
            
    def __getitem__(self, rank):
        if isinstance(rank, Rank):
            i = int(rank)
        elif isinstance(rank, str):
            i = [r.name for r in self].index(rank)
        elif isinstance(rank, int):
            i = rank
        elif isinstance(rank, slice):
            if rank.start is None:
                j = 0
            else:
                j = self.__getitem__(rank.start)
                
            if rank.stop is None:
                k = len(self)
            else:
                k = self.__getitem__(rank.stop)
                
            s = []
            for i in range(j,k):
                s.append(super().__getitem__(i))
                
            return s
        else:
            raise IndexError("Type %s not a valid index for RankList" % type(rank))
        return super().__getitem__(i)
                    
    
# Define the Trunk branch object
# This schema will make sense for any unaffiliated Blender document,
# even if it hasn't been saved as a file yet:
Trunk = Branch(None, '', 0, ('', 'file', 'scene'))
