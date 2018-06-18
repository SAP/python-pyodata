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
           <EntityType Name="City" sap:content-version="1" sap:value-list="true" sap:label="City">
            <Key>
              <PropertyRef Name="Name"/>
              <PropertyRef Name="CountryISO"/>
            </Key>
            <Property Name="Name" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="true" sap:filterable="true"/>
            <Property Name="CountryISO" Type="Edm.String" Nullable="false"  sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="true" sap:filterable="true"/>
            <Property Name="Country" Type="Edm.String" Nullable="false"  sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="true" sap:filterable="true"/>
           </EntityType>
           <EntityType Name="Car" sap:content-version="1" sap:value-list="true" sap:label="Car">
            <Key>
              <PropertyRef Name="Name"/>
            </Key>
            <Property Name="Name" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="true" sap:filterable="true"/>
            <Property Name="CodeName" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="true" sap:filterable="true"  sap:filter-restriction="single-value"/>
            <Property Name="Price" Type="Edm.Decimal" Nullable="false" Precision="7" Scale="3" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="true" sap:filterable="true"/>
            <NavigationProperty Name="IDPic" Relationship="EXAMPLE_SRV.toCarIDPic" FromRole="FromRole_toCarIDPic" ToRole="ToRole_toCarIDPic"/>
           </EntityType>
           <EntityType Name="CarIDPic" m:HasStream="true" sap:content-versiom="1" sap:label="Car ID">
            <Key>
             <PropertyRef Name="CarName"/>
            </Key>
            <Property Name="CarName" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Data" sap:creatable="false" sap:updatable="false" sap:sortable="true" sap:filterable="true"/>
            <Property Name="Content" Type="Edm.Binary" Nullable="false" sap:label="Picture" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:filterable="false"/>
           </EntityType>
           <ComplexType Name="ComplexNumber">
            <Property Name="Real" Type="Edm.Double" Nullable="false"/>
            <Property Name="Imaginary" Type="Edm.Double" Nullable="false"/>
           </ComplexType>
           <ComplexType Name="Rectangle">
            <Property Name="Width" Type="Edm.Double" Nullable="false"/>
            <Property Name="Height" Type="Edm.Double" Nullable="false"/>
           </ComplexType>
           <ComplexType Name="Building">
             <Property Name="Street" Type="Edm.String" Nullable="true"/>
             <Property Name="Number" Type="Edm.String" Nullable="false"/>
             <Property Name="City" Type="Edm.String" Nullable="false"/>
             <Property Name="Region" Type="Edm.String" Nullable="false"/>
             <Property Name="Country" Type="Edm.String" Nullable="false"/>
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
           <Association Name="toCarIDPic" sap:content-version="1">
            <End Type="EXAMPLE_SRV.Car" Multiplicity="1" Role="FromRole_toCarIDPic" />
            <End Type="EXAMPLE_SRV.CarIDPic" Multiplicity="1" Role="ToRole_toCarIDPic" />
            <ReferentialConstraint>
             <Principal Role="FromRole_toCarIDPic">
              <PropertyRef Name="Name" />
             </Principal>
             <Dependent Role="ToRole_toCarIDPic">
              <PropertyRef Name="CarName" />
             </Dependent>
            </ReferentialConstraint>
           </Association>
           <EntityContainer Name="EXAMPLE_SRV" m:IsDefaultEntityContainer="true" sap:supported-formats="atom json xlsx">
            <EntitySet Name="MasterEntities" EntityType="EXAMPLE_SRV.MasterEntity" sap:creatable="false" sap:updatable="false" sap:deletable="false" sap:searchable="true" sap:content-version="1"/>
            <EntitySet Name="DataValueHelp" EntityType="EXAMPLE_SRV.DataEntity" sap:creatable="false" sap:updatable="false" sap:deletable="false" sap:searchable="true" sap:content-version="1"/>
            <EntitySet Name="Cities" EntityType="EXAMPLE_SRV.City" sap:creatable="false" sap:updatable="false" sap:deletable="false" sap:searchable="true" sap:content-version="1"/>
            <EntitySet Name="CitiesWithFilter" EntityType="EXAMPLE_SRV.City" sap:requires-filter="true"/>
            <EntitySet Name="CitiesNotAddressable" EntityType="EXAMPLE_SRV.City" sap:addressable="false"/>
            <EntitySet Name="Cars" EntityType="EXAMPLE_SRV.Car" sap:countable="false" sap:pageable="false" sap:topable="true"/>
            <EntitySet Name="CarIDPics" EntityType="EXAMPLE_SRV.CarIDPic" sap:countable="false" sap:pageable="false" sap:topable="false"/>
            <FunctionImport Name="retrieve" ReturnType="Edm.Boolean" EntitySet="MasterEntities" m:HttpMethod="GET" sap:action-for="EXAMPLE_SRV.MasterEntity">
             <Parameter Name="Param" Type="Edm.String" Mode="In" MaxLenght="5" />
            </FunctionImport>
            <AssociationSet Name="toDataEntitySet" Association="EXAMPLE_SRV.toDataEntity" sap:creatable="false" sap:updatable="false" sap:deletable="false" sap:content-version="1">
                <End EntitySet="MasterEntities" Role="FromRole_toDataEntity" />
                <End EntitySet="DataValueHelp" Role="ToRole_toDataEntity" />
            </AssociationSet>
            <AssociationSet Name="toCarIDPicSet" Association="EXAMPLE_SRV.toCarIDPic" sap:creatable="false" sap:updatable="false" sap:deletable="false" sap:content-version="1">
              <End EntitySet="Cars" Role="FromRole_toCarIDPic" />
              <End EntitySet="CarIDPics" Role="ToRole_toCarIDPic" />
            </AssociationSet>
           </EntityContainer>
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
           <Annotations xmlns="http://docs.oasis-open.org/odata/ns/edm" Target="EXAMPLE_SRV.Building/City">
            <Annotation Term="com.sap.vocabularies.Common.v1.ValueList">
             <Record>
              <PropertyValue Property="Label" String="Name"/>
              <PropertyValue Property="CollectionPath" String="Cities"/>
              <PropertyValue Property="SearchSupported" Bool="true"/>
              <PropertyValue Property="Parameters">
               <Collection>
                <Record Type="com.sap.vocabularies.Common.v1.ValueListParameterInOut">
                 <PropertyValue Property="LocalDataProperty" PropertyPath="City"/>
                 <PropertyValue Property="ValueListProperty" String="Name"/>
                </Record>
                <Record Type="com.sap.vocabularies.Common.v1.ValueListParameterDisplayOnly">
                 <PropertyValue Property="ValueListProperty" String="Country"/>
                </Record>
               </Collection>
              </PropertyValue>
             </Record>
            </Annotation>
           </Annotations>
           <Annotations xmlns="http://docs.oasis-open.org/odata/ns/edm" Target="EXAMPLE_SRV.Building/City" Qualifier="2ND_BUILDING_CITY_IGNORED">
            <Annotation Term="com.sap.vocabularies.Common.v1.ValueList">
             <Record>
              <PropertyValue Property="Label" String="Name"/>
              <PropertyValue Property="CollectionPath" String="Cities"/>
              <PropertyValue Property="SearchSupported" Bool="true"/>
              <PropertyValue Property="Parameters">
               <Collection>
                <Record Type="com.sap.vocabularies.Common.v1.ValueListParameterInOut">
                 <PropertyValue Property="LocalDataProperty" PropertyPath="City"/>
                 <PropertyValue Property="ValueListProperty" String="Name"/>
                </Record>
               </Collection>
              </PropertyValue>
             </Record>
            </Annotation>
           </Annotations>
          </Schema>

          <Schema xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" xmlns="http://schemas.microsoft.com/ado/2008/09/edm" Namespace="EXAMPLE_SRV_SETS" xml:lang="en" sap:schema-version="1">

            <EntityType Name="Employee">
                <Key>
                    <PropertyRef Name="ID"/>
                </Key>
                <Property Name="ID" Type="Edm.Int32" Nullable="false"/>
                <Property Name="NameFirst" Type="Edm.String" Nullable="true"/>
                <Property Name="NameLast" Type="Edm.String" Nullable="true"/>
                <NavigationProperty Name="Addresses" Relationship="EXAMPLE_SRV_SETS.AssociationEmployeeAddress" FromRole="EmployeeRole" ToRole="AddressRole"/>
            </EntityType>

            <EntityType Name="Address">
                <Key>
                    <PropertyRef Name="ID"/>
                </Key>
                <Property Name="ID" Type="Edm.Int32" Nullable="false"/>
                <Property Name="Street" Type="Edm.String" Nullable="true"/>
                <Property Name="City" Type="Edm.String" Nullable="true"/>
            </EntityType>

            <Association Name="AssociationEmployeeAddress">
                <End Type="EXAMPLE_SRV_SETS.Employee" Multiplicity="1" Role="EmployeeRole"/>
                <End Type="EXAMPLE_SRV_SETS.Address" Multiplicity="*" Role="AddressRole"/>
            </Association>

            <ComplexType Name="Rectangle">
                <Property Name="Width" Type="Edm.Double" Nullable="false"/>
                <Property Name="Height" Type="Edm.Double" Nullable="false"/>
            </ComplexType>

            <EntityContainer Name="EXAMPLE_SRV" m:IsDefaultEntityContainer="true" sap:supported-formats="atom json xlsx">

                <EntitySet Name="TemperatureMeasurements" EntityType="EXAMPLE_SRV.TemperatureMeasurement" sap:creatable="true" sap:updatable="true" sap:deletable="true" sap:searchable="true" sap:content-version="1"/>

                <EntitySet Name="Employees" EntityType="Employee"/>

                <EntitySet Name="Addresses" EntityType="Address"/>

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

                <AssociationSet Name="AssociationEmployeeAddress_AssocSet" Association="EXAMPLE_SRV_SETS.AssociationEmployeeAddress" sap:creatable="false" sap:updatable="false" sap:deletable="false" sap:content-version="1">
                    <End Role="EmployeeRole" EntitySet="Employees"/>
                    <End Role="AddressRole" EntitySet="Addresses"/>
                </AssociationSet>

            </EntityContainer>

          </Schema>
         </edmx:DataServices>
         </edmx:Edmx>"""


@pytest.fixture
def metadata_builder_factory():
    """Skeleton OData metadata"""

    # pylint: disable=line-too-long

    class MetadaBuilder(object):
        """Helper class for building XML metadata document"""

        PROLOGUE = """
        <edmx:Edmx xmlns:edmx="http://schemas.microsoft.com/ado/2007/06/edmx" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" xmlns:sap="http://www.sap.com/Protocols/SAPData" Version="1.0">
          <edmx:Reference xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx" Uri="https://example.sap.corp/sap/opu/odata/IWFND/CATALOGSERVICE;v=2/Vocabularies(TechnicalName='%2FIWBEP%2FVOC_COMMON',Version='0001',SAP__Origin='LOCAL')/$value">
           <edmx:Include Namespace="com.sap.vocabularies.Common.v1" Alias="Common"/>
          </edmx:Reference>
         <edmx:DataServices m:DataServiceVersion="2.0">
         """

        EPILOGUE = """
         </edmx:DataServices>
        </edmx:Edmx>
        """

        def __init__(self):
            self._schemas = ''

        def add_schema(self, namespace, xml_definition):
            """Add schema element"""

            self._schemas += '<Schema xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" xmlns="http://schemas.microsoft.com/ado/2008/09/edm" Namespace="{0}" xml:lang="en" sap:schema-version="1">'.format(namespace)
            self._schemas += xml_definition
            self._schemas += '</Schema>'

        def serialize(self):
            """Returns full metadata XML document"""

            return MetadaBuilder.PROLOGUE + self._schemas + MetadaBuilder.EPILOGUE

    return MetadaBuilder


@pytest.fixture
def schema(metadata):
    """Parsed metadata"""

    # pylint: disable=redefined-outer-name

    return Edmx.parse(metadata)
