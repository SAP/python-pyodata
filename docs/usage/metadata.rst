Metadata evaluation
===================


By default, the client makes sure that references to properties, entities and
entity sets are pointing to existing elements.

The most often problem that we had to deal with was an invalid *ValueList*
annotation pointing to a non-existing property.

To enable verification of service definition, the client instance of the class
*Service* publishes the property *schema* which returns an instance of the
class *Schema* from the module *pyodata.v2.model* and it contains parsed
*$metadata*.

List of the defined EntitySets
------------------------------

If you need to iterate over all EntitySets:

.. code-block:: python

    for es in service.schema.entity_sets:
         print(es.name)

or if you just need the list of EntitySet names:

.. code-block:: python

    entity_set_names = [es.name for es in service.schema.entity_sets]


Property has this label
-----------------------

.. code-block:: python

    assert northwind.schema.entity_type('Customer').proprty('CustomerID').label == 'Identifier'


Property has a value helper
---------------------------

.. code-block:: python

    assert northwind.schema.entity_type('Customer').proprty('City').value_helper is not None
