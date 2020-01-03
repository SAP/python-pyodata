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
package org.apache.olingo.server.sample.processor;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.Charset;
import java.util.List;
import java.util.Locale;

import org.apache.olingo.commons.api.data.ContextURL;
import org.apache.olingo.commons.api.data.ContextURL.Suffix;
import org.apache.olingo.commons.api.data.Entity;
import org.apache.olingo.commons.api.data.EntityCollection;
import org.apache.olingo.commons.api.data.Property;
import org.apache.olingo.commons.api.edm.EdmComplexType;
import org.apache.olingo.commons.api.edm.EdmEntitySet;
import org.apache.olingo.commons.api.edm.EdmPrimitiveType;
import org.apache.olingo.commons.api.edm.EdmProperty;
import org.apache.olingo.commons.api.format.ContentType;
import org.apache.olingo.commons.api.http.HttpHeader;
import org.apache.olingo.commons.api.http.HttpStatusCode;
import org.apache.olingo.server.api.OData;
import org.apache.olingo.server.api.ODataApplicationException;
import org.apache.olingo.server.api.ODataLibraryException;
import org.apache.olingo.server.api.ODataRequest;
import org.apache.olingo.server.api.ODataResponse;
import org.apache.olingo.server.api.ServiceMetadata;
import org.apache.olingo.server.api.deserializer.DeserializerException;
import org.apache.olingo.server.api.processor.ComplexProcessor;
import org.apache.olingo.server.api.processor.EntityCollectionProcessor;
import org.apache.olingo.server.api.processor.EntityProcessor;
import org.apache.olingo.server.api.processor.PrimitiveProcessor;
import org.apache.olingo.server.api.processor.PrimitiveValueProcessor;
import org.apache.olingo.server.api.serializer.ComplexSerializerOptions;
import org.apache.olingo.server.api.serializer.EntityCollectionSerializerOptions;
import org.apache.olingo.server.api.serializer.EntitySerializerOptions;
import org.apache.olingo.server.api.serializer.ODataSerializer;
import org.apache.olingo.server.api.serializer.PrimitiveSerializerOptions;
import org.apache.olingo.server.api.serializer.SerializerException;
import org.apache.olingo.server.api.uri.UriInfo;
import org.apache.olingo.server.api.uri.UriInfoResource;
import org.apache.olingo.server.api.uri.UriResource;
import org.apache.olingo.server.api.uri.UriResourceEntitySet;
import org.apache.olingo.server.api.uri.UriResourceProperty;
import org.apache.olingo.server.api.uri.queryoption.ExpandOption;
import org.apache.olingo.server.api.uri.queryoption.SelectOption;
import org.apache.olingo.server.sample.data.DataProvider;
import org.apache.olingo.server.sample.data.DataProvider.DataProviderException;

/**
 * This processor will deliver entity collections, single entities as well as properties of an entity.
 * This is a very simple example which should give you a rough guideline on how to implement such an processor.
 * See the JavaDoc of the server.api interfaces for more information.
 */
public class CarsProcessor implements EntityCollectionProcessor, EntityProcessor,
    PrimitiveProcessor, PrimitiveValueProcessor, ComplexProcessor {

  private OData odata;
  private final DataProvider dataProvider;
  private ServiceMetadata edm;

  // This constructor is application specific and not mandatory for the Olingo library. We use it here to simulate the
  // database access
  public CarsProcessor(final DataProvider dataProvider) {
    this.dataProvider = dataProvider;
  }

  @Override
  public void init(OData odata, ServiceMetadata edm) {
    this.odata = odata;
    this.edm = edm;
  }

  @Override
  public void readEntityCollection(final ODataRequest request, ODataResponse response, final UriInfo uriInfo,
      final ContentType requestedContentType) throws ODataApplicationException, SerializerException {
    // First we have to figure out which entity set to use
    final EdmEntitySet edmEntitySet = getEdmEntitySet(uriInfo.asUriInfoResource());

    // Second we fetch the data for this specific entity set from the mock database and transform it into an EntitySet
    // object which is understood by our serialization
    EntityCollection entitySet = dataProvider.readAll(edmEntitySet);

    // Next we create a serializer based on the requested format. This could also be a custom format but we do not
    // support them in this example
    ODataSerializer serializer = odata.createSerializer(requestedContentType);

    // Now the content is serialized using the serializer.
    final ExpandOption expand = uriInfo.getExpandOption();
    final SelectOption select = uriInfo.getSelectOption();
    final String id = request.getRawBaseUri() + "/" + edmEntitySet.getName();
    InputStream serializedContent = serializer.entityCollection(edm, edmEntitySet.getEntityType(), entitySet,
        EntityCollectionSerializerOptions.with()
            .id(id)
            .contextURL(isODataMetadataNone(requestedContentType) ? null :
                getContextUrl(edmEntitySet, false, expand, select, null))
            .count(uriInfo.getCountOption())
            .expand(expand).select(select)
            .build()).getContent();

    // Finally we set the response data, headers and status code
    response.setContent(serializedContent);
    response.setStatusCode(HttpStatusCode.OK.getStatusCode());
    response.setHeader(HttpHeader.CONTENT_TYPE, requestedContentType.toContentTypeString());
  }

  @Override
  public void readEntity(final ODataRequest request, ODataResponse response, final UriInfo uriInfo,
      final ContentType requestedContentType) throws ODataApplicationException, SerializerException {
    // First we have to figure out which entity set the requested entity is in
    final EdmEntitySet edmEntitySet = getEdmEntitySet(uriInfo.asUriInfoResource());

    // Next we fetch the requested entity from the database
    Entity entity;
    try {
      entity = readEntityInternal(uriInfo.asUriInfoResource(), edmEntitySet);
    } catch (DataProviderException e) {
      throw new ODataApplicationException(e.getMessage(), 500, Locale.ENGLISH);
    }

    if (entity == null) {
      // If no entity was found for the given key we throw an exception.
      throw new ODataApplicationException("No entity found for this key", HttpStatusCode.NOT_FOUND
          .getStatusCode(), Locale.ENGLISH);
    } else {
      // If an entity was found we proceed by serializing it and sending it to the client.
      ODataSerializer serializer = odata.createSerializer(requestedContentType);
      final ExpandOption expand = uriInfo.getExpandOption();
      final SelectOption select = uriInfo.getSelectOption();
      InputStream serializedContent = serializer.entity(edm, edmEntitySet.getEntityType(), entity,
          EntitySerializerOptions.with()
              .contextURL(isODataMetadataNone(requestedContentType) ? null :
                  getContextUrl(edmEntitySet, true, expand, select, null))
              .expand(expand).select(select)
              .build()).getContent();
      response.setContent(serializedContent);
      response.setStatusCode(HttpStatusCode.OK.getStatusCode());
      response.setHeader(HttpHeader.CONTENT_TYPE, requestedContentType.toContentTypeString());
    }
  }

  @Override
  public void createEntity(ODataRequest request, ODataResponse response, UriInfo uriInfo,
                           ContentType requestFormat, ContentType responseFormat)
          throws ODataApplicationException, DeserializerException, SerializerException {
    throw new ODataApplicationException("Entity create is not supported yet.",
            HttpStatusCode.NOT_IMPLEMENTED.getStatusCode(), Locale.ENGLISH);
  }

  @Override
  public void deleteEntity(ODataRequest request, ODataResponse response, UriInfo uriInfo)
          throws ODataApplicationException {
    throw new ODataApplicationException("Entity delete is not supported yet.",
            HttpStatusCode.NOT_IMPLEMENTED.getStatusCode(), Locale.ENGLISH);
  }

  @Override
  public void readPrimitive(ODataRequest request, ODataResponse response, UriInfo uriInfo, ContentType format)
          throws ODataApplicationException, SerializerException {
    readProperty(response, uriInfo, format, false);
  }

  @Override
  public void readComplex(ODataRequest request, ODataResponse response, UriInfo uriInfo, ContentType format)
          throws ODataApplicationException, SerializerException {
    readProperty(response, uriInfo, format, true);
  }

  @Override
  public void readPrimitiveValue(ODataRequest request, ODataResponse response, UriInfo uriInfo, ContentType format)
          throws ODataApplicationException, SerializerException {
    // First we have to figure out which entity set the requested entity is in
    final EdmEntitySet edmEntitySet = getEdmEntitySet(uriInfo.asUriInfoResource());
    // Next we fetch the requested entity from the database
    final Entity entity;
    try {
      entity = readEntityInternal(uriInfo.asUriInfoResource(), edmEntitySet);
    } catch (DataProviderException e) {
      throw new ODataApplicationException(e.getMessage(), 500, Locale.ENGLISH);
    }
    if (entity == null) {
      // If no entity was found for the given key we throw an exception.
      throw new ODataApplicationException("No entity found for this key", HttpStatusCode.NOT_FOUND
              .getStatusCode(), Locale.ENGLISH);
    } else {
      // Next we get the property value from the entity and pass the value to serialization
      UriResourceProperty uriProperty = (UriResourceProperty) uriInfo
              .getUriResourceParts().get(uriInfo.getUriResourceParts().size() - 1);
      EdmProperty edmProperty = uriProperty.getProperty();
      Property property = entity.getProperty(edmProperty.getName());
      if (property == null) {
        throw new ODataApplicationException("No property found", HttpStatusCode.NOT_FOUND
                .getStatusCode(), Locale.ENGLISH);
      } else {
        if (property.getValue() == null) {
          response.setStatusCode(HttpStatusCode.NO_CONTENT.getStatusCode());
        } else {
          String value = String.valueOf(property.getValue());
          ByteArrayInputStream serializerContent = new ByteArrayInputStream(
                  value.getBytes(Charset.forName("UTF-8")));
          response.setContent(serializerContent);
          response.setStatusCode(HttpStatusCode.OK.getStatusCode());
          response.setHeader(HttpHeader.CONTENT_TYPE, ContentType.TEXT_PLAIN.toContentTypeString());
        }
      }
    }
  }

  private void readProperty(ODataResponse response, UriInfo uriInfo, ContentType contentType,
      boolean complex) throws ODataApplicationException, SerializerException {
    // To read a property we have to first get the entity out of the entity set
    final EdmEntitySet edmEntitySet = getEdmEntitySet(uriInfo.asUriInfoResource());
    Entity entity;
    try {
      entity = readEntityInternal(uriInfo.asUriInfoResource(), edmEntitySet);
    } catch (DataProviderException e) {
      throw new ODataApplicationException(e.getMessage(),
              HttpStatusCode.INTERNAL_SERVER_ERROR.getStatusCode(), Locale.ENGLISH);
    }

    if (entity == null) {
      // If no entity was found for the given key we throw an exception.
      throw new ODataApplicationException("No entity found for this key",
              HttpStatusCode.NOT_FOUND.getStatusCode(), Locale.ENGLISH);
    } else {
      // Next we get the property value from the entity and pass the value to serialization
      UriResourceProperty uriProperty = (UriResourceProperty) uriInfo
          .getUriResourceParts().get(uriInfo.getUriResourceParts().size() - 1);
      EdmProperty edmProperty = uriProperty.getProperty();
      Property property = entity.getProperty(edmProperty.getName());
      if (property == null) {
        throw new ODataApplicationException("No property found",
                HttpStatusCode.NOT_FOUND.getStatusCode(), Locale.ENGLISH);
      } else {
        if (property.getValue() == null) {
          response.setStatusCode(HttpStatusCode.NO_CONTENT.getStatusCode());
        } else {
          ODataSerializer serializer = odata.createSerializer(contentType);
          final ContextURL contextURL = isODataMetadataNone(contentType) ? null :
              getContextUrl(edmEntitySet, true, null, null, edmProperty.getName());
          InputStream serializerContent = complex ?
              serializer.complex(edm, (EdmComplexType) edmProperty.getType(), property,
                  ComplexSerializerOptions.with().contextURL(contextURL).build()).getContent() :
              serializer.primitive(edm, (EdmPrimitiveType) edmProperty.getType(), property,
                                    PrimitiveSerializerOptions.with()
                                    .contextURL(contextURL)
                                    .scale(edmProperty.getScale())
                                    .nullable(edmProperty.isNullable())
                                    .precision(edmProperty.getPrecision())
                                    .maxLength(edmProperty.getMaxLength())
                                    .unicode(edmProperty.isUnicode()).build()).getContent();
          response.setContent(serializerContent);
          response.setStatusCode(HttpStatusCode.OK.getStatusCode());
          response.setHeader(HttpHeader.CONTENT_TYPE, contentType.toContentTypeString());
        }
      }
    }
  }

  private Entity readEntityInternal(final UriInfoResource uriInfo, final EdmEntitySet entitySet)
      throws DataProvider.DataProviderException {
    // This method will extract the key values and pass them to the data provider
    final UriResourceEntitySet resourceEntitySet = (UriResourceEntitySet) uriInfo.getUriResourceParts().get(0);
    return dataProvider.read(entitySet, resourceEntitySet.getKeyPredicates());
  }

  private EdmEntitySet getEdmEntitySet(final UriInfoResource uriInfo) throws ODataApplicationException {
    final List<UriResource> resourcePaths = uriInfo.getUriResourceParts();
    /*
     * To get the entity set we have to interpret all URI segments
     */
    if (!(resourcePaths.get(0) instanceof UriResourceEntitySet)) {
      throw new ODataApplicationException("Invalid resource type for first segment.",
          HttpStatusCode.NOT_IMPLEMENTED.getStatusCode(), Locale.ENGLISH);
    }

    /*
     * Here we should interpret the whole URI but in this example we do not support navigation so we throw an exception
     */

    final UriResourceEntitySet uriResource = (UriResourceEntitySet) resourcePaths.get(0);
    return uriResource.getEntitySet();
  }

  private ContextURL getContextUrl(final EdmEntitySet entitySet, final boolean isSingleEntity,
      final ExpandOption expand, final SelectOption select, final String navOrPropertyPath)
      throws SerializerException {

    return ContextURL.with().entitySet(entitySet)
        .selectList(odata.createUriHelper().buildContextURLSelectList(entitySet.getEntityType(), expand, select))
        .suffix(isSingleEntity ? Suffix.ENTITY : null)
        .navOrPropertyPath(navOrPropertyPath)
        .build();
  }

  @Override
  public void updatePrimitive(final ODataRequest request, final ODataResponse response,
                              final UriInfo uriInfo, final ContentType requestFormat,
                              final ContentType responseFormat)
          throws ODataApplicationException, DeserializerException, SerializerException {
    throw new ODataApplicationException("Primitive property update is not supported yet.",
            HttpStatusCode.NOT_IMPLEMENTED.getStatusCode(), Locale.ENGLISH);
  }

  @Override
  public void updatePrimitiveValue(final ODataRequest request, ODataResponse response,
      final UriInfo uriInfo, final ContentType requestFormat, final ContentType responseFormat)
      throws ODataApplicationException, ODataLibraryException {
    throw new ODataApplicationException("Primitive property update is not supported yet.",
        HttpStatusCode.NOT_IMPLEMENTED.getStatusCode(), Locale.ENGLISH);
  }

  @Override
  public void deletePrimitive(ODataRequest request, ODataResponse response, UriInfo uriInfo) throws
          ODataApplicationException {
    throw new ODataApplicationException("Primitive property delete is not supported yet.",
            HttpStatusCode.NOT_IMPLEMENTED.getStatusCode(), Locale.ENGLISH);
  }

  @Override
  public void deletePrimitiveValue(final ODataRequest request, ODataResponse response, final UriInfo uriInfo)
      throws ODataApplicationException, ODataLibraryException {
    throw new ODataApplicationException("Primitive property update is not supported yet.",
        HttpStatusCode.NOT_IMPLEMENTED.getStatusCode(), Locale.ENGLISH);
  }

  @Override
  public void updateComplex(final ODataRequest request, final ODataResponse response,
                            final UriInfo uriInfo, final ContentType requestFormat,
                            final ContentType responseFormat)
          throws ODataApplicationException, DeserializerException, SerializerException {
    throw new ODataApplicationException("Complex property update is not supported yet.",
            HttpStatusCode.NOT_IMPLEMENTED.getStatusCode(), Locale.ENGLISH);
  }

  @Override
  public void deleteComplex(final ODataRequest request, final ODataResponse response, final UriInfo uriInfo)
          throws ODataApplicationException {
    throw new ODataApplicationException("Complex property delete is not supported yet.",
            HttpStatusCode.NOT_IMPLEMENTED.getStatusCode(), Locale.ENGLISH);
  }

  @Override
  public void updateEntity(final ODataRequest request, final ODataResponse response,
                           final UriInfo uriInfo, final ContentType requestFormat,
                           final ContentType responseFormat)
          throws ODataApplicationException, DeserializerException, SerializerException {
    throw new ODataApplicationException("Entity update is not supported yet.",
            HttpStatusCode.NOT_IMPLEMENTED.getStatusCode(), Locale.ENGLISH);
  }
  
  public static boolean isODataMetadataNone(final ContentType contentType) {
    return contentType.isCompatible(ContentType.APPLICATION_JSON) 
       && ContentType.VALUE_ODATA_METADATA_NONE.equalsIgnoreCase(
           contentType.getParameter(ContentType.PARAMETER_ODATA_METADATA));
  }
}