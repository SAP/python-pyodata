""" Base class for defining ODATA versions. """

from abc import ABC, abstractmethod
from typing import List, Dict, Callable, TYPE_CHECKING

# pylint: disable=cyclic-import
if TYPE_CHECKING:
    from pyodata.model.elements import Typ, Annotation  # noqa


class ODATAVersion(ABC):
    """ This is base class for different OData releases. In it we define what are supported types, elements and so on.
        Furthermore, we specify how individual elements are parsed or represented by python objects.
    """

    def __init__(self):
        raise RuntimeError('ODATAVersion and its children are intentionally stateless, '
                           'therefore you can not create instance of them')

    # Separate dictionary of all registered types (primitive, complex and collection variants) for each child
    Types: Dict[str, 'Typ'] = dict()

    @staticmethod
    @abstractmethod
    def primitive_types() -> List['Typ']:
        """ Here we define which primitive types are supported and what is their python representation"""

    @staticmethod
    @abstractmethod
    def build_functions() -> Dict[type, Callable]:
        """ Here we define which elements are supported and what is their python representation"""

    @staticmethod
    @abstractmethod
    def annotations() -> Dict['Annotation', Callable]:
        """ Here we define which annotations are supported and what is their python representation"""
