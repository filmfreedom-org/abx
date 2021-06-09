# parsers (sub-package)
"""
Filename Parsers & Registry for FileContext.
"""          

NameParsers = {} # Parser registry

def registered_parser(parser):
    """
    Decorator function to register a parser class.
    """
    NameParsers[parser.name] = parser
    return parser

from . import abx_episode, abx_fallback, abx_schema

