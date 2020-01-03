/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements. See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership. The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.olingo.server.sample.data;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.apache.olingo.commons.api.ex.ODataException;
import org.apache.olingo.commons.api.ex.ODataRuntimeException;
import org.apache.olingo.commons.api.data.Entity;
import org.apache.olingo.commons.api.data.EntityCollection;
import org.apache.olingo.commons.api.data.Property;
import org.apache.olingo.commons.api.data.ValueType;
import org.apache.olingo.commons.api.data.ComplexValue;
import org.apache.olingo.commons.api.edm.EdmEntitySet;
import org.apache.olingo.commons.api.edm.EdmEntityType;
import org.apache.olingo.commons.api.edm.EdmPrimitiveType;
import org.apache.olingo.commons.api.edm.EdmPrimitiveTypeException;
import org.apache.olingo.commons.api.edm.EdmProperty;
import org.apache.olingo.server.api.uri.UriParameter;
import org.apache.olingo.server.sample.edmprovider.CarsEdmProvider;

public class DataProvider {

  private final Map<String, EntityCollection> data;

  public DataProvider() {
    data = new HashMap<String, EntityCollection>();
    data.put("Cars", createCars());
    data.put("Manufacturers", createManufacturers());
  }

  public EntityCollection readAll(EdmEntitySet edmEntitySet) {
    return data.get(edmEntitySet.getName());
  }

  public Entity read(final EdmEntitySet edmEntitySet, final List<UriParameter> keys) throws DataProviderException {
    final EdmEntityType entityType = edmEntitySet.getEntityType();
    final EntityCollection entitySet = data.get(edmEntitySet.getName());
    if (entitySet == null) {
      return null;
    } else {
      try {
        for (final Entity entity : entitySet.getEntities()) {
          boolean found = true;
          for (final UriParameter key : keys) {
            final EdmProperty property = (EdmProperty) entityType.getProperty(key.getName());
            final EdmPrimitiveType type = (EdmPrimitiveType) property.getType();
            if (!type.valueToString(entity.getProperty(key.getName()).getValue(),
                property.isNullable(), property.getMaxLength(), property.getPrecision(), property.getScale(),
                property.isUnicode())
                .equals(key.getText())) {
              found = false;
              break;
            }
          }
          if (found) {
            return entity;
          }
        }
        return null;
      } catch (final EdmPrimitiveTypeException e) {
        throw new DataProviderException("Wrong key!", e);
      }
    }
  }

  public static class DataProviderException extends ODataException {
    private static final long serialVersionUID = 5098059649321796156L;

    public DataProviderException(String message, Throwable throwable) {
      super(message, throwable);
    }

    public DataProviderException(String message) {
      super(message);
    }
  }

  private EntityCollection createCars() {
    EntityCollection entitySet = new EntityCollection();
    Entity el = new Entity()
        .addProperty(createPrimitive("Id", 1))
        .addProperty(createPrimitive("Model", "F1 W03"))
        .addProperty(createPrimitive("ModelYear", "2012"))
        .addProperty(createPrimitive("Price", 189189.43))
        .addProperty(createPrimitive("Currency", "EUR"));
    el.setId(createId(CarsEdmProvider.ES_CARS_NAME, 1));
    entitySet.getEntities().add(el);

    el = new Entity()
        .addProperty(createPrimitive("Id", 2))
        .addProperty(createPrimitive("Model", "F1 W04"))
        .addProperty(createPrimitive("ModelYear", "2013"))
        .addProperty(createPrimitive("Price", 199999.99))
        .addProperty(createPrimitive("Currency", "EUR"));
    el.setId(createId(CarsEdmProvider.ES_CARS_NAME, 2));
    entitySet.getEntities().add(el);

    el = new Entity()
        .addProperty(createPrimitive("Id", 3))
        .addProperty(createPrimitive("Model", "F2012"))
        .addProperty(createPrimitive("ModelYear", "2012"))
        .addProperty(createPrimitive("Price", 137285.33))
        .addProperty(createPrimitive("Currency", "EUR"));
    el.setId(createId(CarsEdmProvider.ES_CARS_NAME, 3));
    entitySet.getEntities().add(el);

    el = new Entity()
        .addProperty(createPrimitive("Id", 4))
        .addProperty(createPrimitive("Model", "F2013"))
        .addProperty(createPrimitive("ModelYear", "2013"))
        .addProperty(createPrimitive("Price", 145285.00))
        .addProperty(createPrimitive("Currency", "EUR"));
    el.setId(createId(CarsEdmProvider.ES_CARS_NAME, 4));
    entitySet.getEntities().add(el);

    el = new Entity()
        .addProperty(createPrimitive("Id", 5))
        .addProperty(createPrimitive("Model", "F1 W02"))
        .addProperty(createPrimitive("ModelYear", "2011"))
        .addProperty(createPrimitive("Price", 167189.00))
        .addProperty(createPrimitive("Currency", "EUR"));
    el.setId(createId(CarsEdmProvider.ES_CARS_NAME, 5));
    entitySet.getEntities().add(el);

    for (Entity entity:entitySet.getEntities()) {
      entity.setType(CarsEdmProvider.ET_CAR.getFullQualifiedNameAsString());
    }
    return entitySet;
  }

  private EntityCollection createManufacturers() {
    EntityCollection entitySet = new EntityCollection();

    Entity el = new Entity()
        .addProperty(createPrimitive("Id", 1))
        .addProperty(createPrimitive("Name", "Star Powered Racing"))
        .addProperty(createAddress("Star Street 137", "Stuttgart", "70173", "Germany"));
    el.setId(createId(CarsEdmProvider.ES_MANUFACTURER_NAME, 1));
    entitySet.getEntities().add(el);

    el = new Entity()
        .addProperty(createPrimitive("Id", 2))
        .addProperty(createPrimitive("Name", "Horse Powered Racing"))
        .addProperty(createAddress("Horse Street 1", "Maranello", "41053", "Italy"));
    el.setId(createId(CarsEdmProvider.ES_MANUFACTURER_NAME, 2));
    entitySet.getEntities().add(el);

    for (Entity entity:entitySet.getEntities()) {
      entity.setType(CarsEdmProvider.ET_MANUFACTURER.getFullQualifiedNameAsString());
    }
    return entitySet;
  }

  private Property createAddress(final String street, final String city, final String zipCode, final String country) {
    ComplexValue complexValue=new ComplexValue();
    List<Property> addressProperties = complexValue.getValue();
    addressProperties.add(createPrimitive("Street", street));
    addressProperties.add(createPrimitive("City", city));
    addressProperties.add(createPrimitive("ZipCode", zipCode));
    addressProperties.add(createPrimitive("Country", country));
    return new Property(null, "Address", ValueType.COMPLEX, complexValue);
  }

  private Property createPrimitive(final String name, final Object value) {
    return new Property(null, name, ValueType.PRIMITIVE, value);
  }

  private URI createId(String entitySetName, Object id) {
    try {
      return new URI(entitySetName + "(" + String.valueOf(id) + ")");
    } catch (URISyntaxException e) {
      throw new ODataRuntimeException("Unable to create id for entity: " + entitySetName, e);
    }
  }
}
