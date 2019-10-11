# pylint: disable=missing-docstring,invalid-name,unused-argument

from pyodata.model.elements import NavigationTypeProperty, Identifier
from pyodata.config import Config


def navigation_type_property_from_etree(node, config: Config):
    return NavigationTypeProperty(
        node.get('Name'), node.get('FromRole'), node.get('ToRole'), Identifier.parse(node.get('Relationship')))
