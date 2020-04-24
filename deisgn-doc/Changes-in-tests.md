# Table of content

1. [Tests file structure](#Structure)
2. [Test and classes](#Clases)
3. [Using metadata templates](#Templates)


## Tests file structure <a name="Structure"></a>
The tests are split into multiple files: test_build_functions, test_build_functions_with_policies, 
test_elements, test_type_traits. The diference between test_build_functions and test_build_functions_with_policies is 
that the later is for testing on invalid metadata.


## Test and classes <a name="Classes"></a>
In previos versions all tests were writen as standalone function, however this is makes hard to orientate in the code 
and it makes hard to kwno witch tests are related. Tests in this release are bundled together in appropriate places. 
Such as when testing build_function(see the example below). Another advantage of bundeling is that tests for specific 
bundles can be run separately.  

```python
class TestSchema:
    def test_types(self, schema):
        assert isinstance(schema.complex_type('Location'), ComplexType)
        ...
        assert isinstance(schema.entity_set('People'), EntitySet)

    def test_property_type(self, schema):
        person = schema.entity_type('Person')
        ...
        assert repr(person.proprty('Weight').typ) == 'Typ(Weight)'
        assert repr(person.proprty('AddressInfo').typ) == 'Collection(ComplexType(Location))'
    ...
```

## Using metadata templates <a name="Templates"></a>
For testing the V4 there are two sets of metadata. `tests/v4/metadata.xml` is filed with test entities, types, sets etc.
while the `tests/v4/metadata.template.xml` is only metadata skeleton. The latter is useful when there is need for 
ceranty that any other metadata arent influensing the result, when custom elements are needed for specific test or when 
you are working with invalid metadata.  

To use the metadata template the Ninja2 is requited. Ninja2 is template engine which can load up the template xml and 
fill it with provided data. Fixture template_builder is available to all tests. Calling the fixture with array of EMD 
elements will return MetadataBuilder already filled with your custom data.

```python
    faulty_entity = """ 
        <EntityType Name="Restaurant">
            <NavigationProperty Name="Location" Type="Position"/>
        </EntityType> """
    builder, config = template_builder(ODataV4, schema_elements=[faulty_entity])
```   