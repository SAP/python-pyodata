"""PyTest Fixtures"""

import pytest
from pyodata.v2.model import Edmx


@pytest.fixture
def metadata():
    """Example OData metadata"""

    # pylint: disable=line-too-long

    return """<edmx:Edmx xmlns:edmx="http://schemas.microsoft.com/ado/2007/06/edmx" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" xmlns:sap="http://www.sap.com/Protocols/SAPData" Version="1.0">
          <edmx:Reference xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx" Uri="https://example.sap.corp/sap/opu/odata/IWFND/CATALOGSERVICE;v=2/Vocabularies(TechnicalName='%2FIWBEP%2FVOC_COMMON',Version='0001',SAP__Origin='LOCAL')/$value">
           <edmx:Include Namespace="com.sap.vocabularies.Common.v1" Alias="Common"/>
          </edmx:Reference>
         <edmx:DataServices m:DataServiceVersion="2.0">
          <Schema xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" xmlns="http://schemas.microsoft.com/ado/2008/09/edm" Namespace="EXAMPLE_SRV" xml:lang="en" sap:schema-version="1">
           <EntityType Name="MasterEntity" sap:content-version="1">
            <Key><PropertyRef Name="Key"/></Key>
            <Property Name="Key" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Key" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:value-list="standard"/>
            <Property Name="DataType" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Key" sap:creatable="false" sap:updatable="false" sap:sortable="false"/>
            <Property Name="Data" Type="Edm.String" MaxLength="Max" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:filterable="false" sap:text="DataName"/>
            <Property Name="DataName" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:filterable="false"/>
           </EntityType>
           <EntityType Name="DataEntity" sap:content-version="1" sap:value-list="true" sap:label="Data entities">
            <Key><PropertyRef Name="Name"/></Key>
            <Property Name="Name" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:filterable="false"/>
            <Property Name="Type" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:filterable="false"/>
            <Property Name="Value" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:filterable="false"/>
            <Property Name="Description" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:filterable="false"/>
            <Property Name="Invisible" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:filterable="false" sap:visible="false"/>
           </EntityType>
           <EntityType Name="AnnotationTest" sap:content-version="1" sap:label="Annotations Tests">
            <Key><PropertyRef Name="NoFormat"/></Key>
            <Property Name="NoFormat" Type="Edm.String"/>
            <Property Name="UpperCase" Type="Edm.String" sap:display-format="UpperCase"/>
            <Property Name="Date" Type="Edm.DateTime" sap:display-format="Date"/>
            <Property Name="NonNegative" Type="Edm.Decimal" sap:display-format="NonNegative"/>
           </EntityType>
           <EntityType Name="TemperatureMeasurement" sap:content-version="1" sap:value-list="true" sap:label="Data entities">
            <Key>
              <PropertyRef Name="Sensor"/>
              <PropertyRef Name="Date"/>
            </Key>
            <Property Name="Sensor" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="true" sap:filterable="true"/>
            <Property Name="Date" Type="Edm.DateTime" Nullable="false"  sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="true" sap:filterable="true"/>
            <Property Name="Value" Type="Edm.Double" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="true" sap:filterable="true"/>
           </EntityType>
           <ComplexType Name="ComplexNumber">
            <Property Name="Real" Type="Edm.Double" Nullable="false"/>
            <Property Name="Imaginary" Type="Edm.Double" Nullable="false"/>
           </ComplexType>
           <ComplexType Name="Rectangle">
            <Property Name="Width" Type="Edm.Double" Nullable="false"/>
            <Property Name="Height" Type="Edm.Double" Nullable="false"/>
           </ComplexType>
           <Association Name="toDataEntity" sap:content-version="1">
            <End Type="EXAMPLE_SRV.MasterEntity" Multiplicity="1" Role="FromRole_toDataEntity" />
            <End Type="EXAMPLE_SRV.DataEntity" Multiplicity="*" Role="ToRole_toDataEntity" />
            <ReferentialConstraint>
             <Principal Role="FromRole_toDataEntity">
              <PropertyRef Name="Key" />
             </Principal>
             <Dependent Role="ToRole_toDataEntity">
              <PropertyRef Name="Name" />
             </Dependent>
            </ReferentialConstraint>
           </Association>
           <EntityContainer Name="EXAMPLE_SRV" m:IsDefaultEntityContainer="true" sap:supported-formats="atom json xlsx">
            <EntitySet Name="MasterEntities" EntityType="EXAMPLE_SRV.MasterEntity" sap:creatable="false" sap:updatable="false" sap:deletable="false" sap:searchable="true" sap:content-version="1"/>
            <EntitySet Name="DataValueHelp" EntityType="EXAMPLE_SRV.DataEntity" sap:creatable="false" sap:updatable="false" sap:deletable="false" sap:searchable="true" sap:content-version="1"/>
            <FunctionImport Name="retrieve" ReturnType="Edm.Boolean" EntitySet="MasterEntities" m:HttpMethod="GET" sap:action-for="EXAMPLE_SRV.MasterEntity">
             <Parameter Name="Param" Type="Edm.String" Mode="In" MaxLenght="5" />
            </FunctionImport>
           </EntityContainer>
           <AssociationSet Name="toDataEntitySet" Association="EXAMPLE_SRV.toDataEntity" sap:creatable="false" sap:updatable="false" sap:deletable="false" sap:content-version="1">
            <End EntitySet="MasterEntities" Role="FromRole_toDataEntity" />
            <End EntitySet="DataValueHelp" Role="ToRole_toDataEntity" />
           </AssociationSet>
           <Annotations xmlns="http://docs.oasis-open.org/odata/ns/edm" Target="EXAMPLE_SRV.MasterEntity/Data">
            <Annotation Term="com.sap.vocabularies.Common.v1.ValueList">
             <Record>
              <PropertyValue Property="Label" String="Data"/>
              <PropertyValue Property="CollectionPath" String="DataValueHelp"/>
              <PropertyValue Property="SearchSupported" Bool="true"/>
              <PropertyValue Property="Parameters">
               <Collection>
                <Record Type="com.sap.vocabularies.Common.v1.ValueListParameterIn">
                 <PropertyValue Property="LocalDataProperty" PropertyPath="DataType"/>
                 <PropertyValue Property="ValueListProperty" String="Type"/>
                </Record>
                <Record Type="com.sap.vocabularies.Common.v1.ValueListParameterOut">
                 <PropertyValue Property="LocalDataProperty" PropertyPath="Data"/>
                 <PropertyValue Property="ValueListProperty" String="Value"/>
                </Record>
                <Record Type="com.sap.vocabularies.Common.v1.ValueListParameterInOut">
                 <PropertyValue Property="LocalDataProperty" PropertyPath="DataName"/>
                 <PropertyValue Property="ValueListProperty" String="Name"/>
                </Record>
                <Record Type="com.sap.vocabularies.Common.v1.ValueListParameterDisplayOnly">
                 <PropertyValue Property="ValueListProperty" String="Description"/>
                </Record>
               </Collection>
              </PropertyValue>
             </Record>
            </Annotation>
           </Annotations>
          </Schema>
          <Schema xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" xmlns="http://schemas.microsoft.com/ado/2008/09/edm" Namespace="EXAMPLE_SRV_SETS" xml:lang="en" sap:schema-version="1">
           <ComplexType Name="Rectangle">
            <Property Name="Width" Type="Edm.Double" Nullable="false"/>
            <Property Name="Height" Type="Edm.Double" Nullable="false"/>
           </ComplexType>
           <EntityContainer Name="EXAMPLE_SRV" m:IsDefaultEntityContainer="true" sap:supported-formats="atom json xlsx">
            <EntitySet Name="TemperatureMeasurements" EntityType="EXAMPLE_SRV.TemperatureMeasurement" sap:creatable="true" sap:updatable="true" sap:deletable="true" sap:searchable="true" sap:content-version="1"/>
            <FunctionImport Name="get_max" ReturnType="TemperatureMeasurement" EntitySet="TemperatureMeasurements" m:HttpMethod="GET" />
            <FunctionImport Name="get_best_measurements" ReturnType="Collection(EXAMPLE_SRV.TemperatureMeasurement)" EntitySet="EXAMPLE_SRV.TemperatureMeasurements" m:HttpMethod="GET" />
            <FunctionImport Name="sum" ReturnType="Edm.Int32" m:HttpMethod="GET">
             <Parameter Name="A" Type="Edm.Int32" Mode="In" />
             <Parameter Name="B" Type="Edm.Int32" Mode="In" />
            </FunctionImport>
            <FunctionImport Name="sum_complex" ReturnType="EXAMPLE_SRV.ComplexNumber" m:HttpMethod="GET">
             <Parameter Name="Param" Type="EXAMPLE_SRV.ComplexNumber" Mode="In" />
             <Parameter Name="Param" Type="EXAMPLE_SRV.ComplexNumber" Mode="In" />
            </FunctionImport>
           </EntityContainer>
          </Schema>
         </edmx:DataServices>
         </edmx:Edmx>"""


@pytest.fixture
def schema(metadata):
    """Parsed metadata"""
    return Edmx.parse(metadata)
