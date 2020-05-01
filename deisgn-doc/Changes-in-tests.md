# Table of content

1. [Tests file structure](#Structure)
2. [Test and classes](#Clases)
3. [Using metadata templates](#Templates)


## Tests file structure <a name="Structure"></a>
The tests are split into multiple files: test_build_functions, test_build_functions_with_policies, 
test_elements, test_type_traits. The diference between test_build_functions and test_build_functions_with_policies is 
that the later is for testing on invalid metadata.


## Test and classes <a name="Classes"></a>
In previous versions all tests were written as a standalone function, however, due to that, it is hard to orientate in 
the code and it makes hard to know which test cases are related and which are not. To avoid that, tests in this release 
are bundled together in inappropriate places. Such as when testing build_function(see the example below). Also, bundling 
makes it easy to run all related tests at once, without having to run the whole test suit, thus making it faster to debug.  

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
while the `tests/v4/metadata.template.xml` is only metadata skeleton. The latter is useful when there is a need to be 
sure that any other metadata arent influencing the result, when custom elements are needed for a specific test or when 
you are working with invalid metadata.  

To use the metadata template the Ninja2 is requited. Ninja2 is a template engine which can load up the template XML and 
fill it with provided data. Fixture template_builder is available to all tests. Calling the fixture with an array of EMD 
elements will return MetadataBuilder preloaded with your custom data.

```python
    faulty_entity = """ 
        <EntityType Name="Restaurant">
            <NavigationProperty Name="Location" Type="Position"/>
        </EntityType> """
    builder, config = template_builder(ODataV4, schema_elements=[faulty_entity])
```   
