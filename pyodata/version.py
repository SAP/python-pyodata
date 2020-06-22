""" Base class for defining ODATA versions. """

from abc import ABC, abstractmethod
from typing import List, Dict, Callable, TYPE_CHECKING, Type

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from pyodata.model.elements import Typ, Annotation  # noqa

PrimitiveTypeDict = Dict[str, 'Typ']
PrimitiveTypeList = List['Typ']
BuildFunctionDict = Dict[type, Callable]
BuildAnnotationDict = Dict[Type['Annotation'], Callable]


class ODATAVersion(ABC):
    """ This is base class for different OData releases. In it we define what are supported types, elements and so on.
        Furthermore, we specify how individual elements are parsed or represented by python objects.
    """

    def __init__(self):
        raise RuntimeError('ODATAVersion and its children are intentionally stateless, '
                           'therefore you can not create instance of them')

    # Separate dictionary of all registered types (primitive, complex and collection variants) for each child
    Types: PrimitiveTypeDict = dict()

    @staticmethod
    @abstractmethod
    def primitive_types() -> PrimitiveTypeList:
        """ Here we define which primitive types are supported and what is their python representation"""

    @staticmethod
    @abstractmethod
    def build_functions() -> BuildFunctionDict:
        """ Here we define which elements are supported and what is their python representation"""

    @staticmethod
    @abstractmethod
    def annotations() -> BuildAnnotationDict:
        """ Here we define which annotations are supported and what is their python representation"""
    #
    # @staticmethod
    # def init_service(url: str, schema: 'Schema', connection: requests.Session) -> Service
