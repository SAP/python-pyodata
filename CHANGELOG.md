# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

## [1.10.1]

### Fixed
- Model: fix edge case for Edm.DateTimeOffset.from_json() without offset - @squeakyboots, Petr Hanak

## [1.10.0]

### Added
- Service: Add async networking libraries support - mnunzio, Albo90, Petr Hanak

### Fixed
- Service: fix navigation in EntityProxy - Masterchen09

## [1.9.2]

### Fixed
- Service: associations relationship fixes - Masterchen09

## [1.9.1]

### Added
- Client: Accept content type application/atom+xml - OmniTroid
- Model: Extract property 'FixedLength' - Reto Schneider

### Experimental, possible subject to backward incompatible changes
- Service: Support for server-side pagination (partial listings trough _next field) - Reto Schneider

## [1.9.0]

### Added
- Prevent substitution of missing, nullable values - Reto Schneider

### Fixed
- Fix Increased robustness when schema with empty properties is returned - Andre Gensler
- Use valid default value for Edm.DateTimeOffset - Reto Schneider

### Changed
- Adjusted Edm.DateTime default value to January 1, 1753 A.D - Reto Schneider

## [1.8.0]

### Fixed
- Fix Edm.Binary literal representation - Daniel Balko
- Datetime support for Edm.DateTimeOffset - Reto Schneider
- Disallow creation of non-UTC Edm.DateTime - Reto Schneider

### Changed
- Split properties schema.entity_types/complex_types and their generated Collections - Petr Hanak

### Removed
- Python 3.6 (after its EOL) is no longer supported by pyodata. Python 3.7 is now minimal supported version. - Petr Hanak

## [1.7.1]

### Fixed
- Workaround for screwed up date values - Timo S.
- Always escape special chars in URL query params - Simon Brulhart
- Helper for obtaining a token for services coming from SAP BTP, ABAP environment - Stoyko Stoev

## [1.7.0]

### Added
- Add inlinecount support - Stoyko Stoev
- Add a ProgramError exception - Stoyko Stoev
- Add is_valid schema property - Petr Hanak

### Fixed
- Passing custom URL query parameters for Entity Requests - Sylvain Fankhauser

## [1.6.0]

### Added
- Specify PATCH, PUT, or MERGE method for EntityUpdateRequest - Barton Ip
- Add a Service wide configuration (e.g. http.update\_method) - Jakub Filak
- <, <=, >, >= operators on GetEntitySetFilter - Barton Ip
- Django style filtering - Barton Ip
- Add etag property to EntityProxy - Martin Miksik

### Fixed
- URL encode $filter contents - Barton Ip
- JSON errors caused by invalid content length of Batch responses - Barton Ip
- Invalid test case - test_create_entity_nested_list - Martin Miksik

### Changed
- ODataHttpResponse.from_string produces header of type {header: value} instead of [(header, value)] - Martin Miksik

## [1.5.0]

### Added
- support for Edm.Float - Jakub Filak

### Changed
- handle GET EntitySet payload without the member results - Jakub Filak
- both Literal and JSON DateTimes has Timezone set to UTC - Jakub Filak

### Fixed
- removed superfluous debug print when parsing FunctionImports from metadata - Jakub Filak
- property 'Nullable' attributes are correctly parsed and respected - Vasilii Khomutov
- use correct type of deserialization of Literal (URL) structure values - Jakub Filak
- null values are correctly handled - Jakub Filak

## [1.4.0]

### Added
- Client can be created from local metadata - Jakub Filak
- support all standard EDM schema versions - Jakub Filak

### Fixed
- make sure configured error policies are applied for Annotations referencing
  unknown type/member - Martin Miksik

## [1.3.0]

### Added
- support Edm.EnumType - Martin Miksik
- support for permissive parsing of $metadata - Martin Miksik
- support deleting Entities - Martin Miksik

### Changed
- Edm.Int64 literals do no need to have the suffix L - Jakub Filak
- more user friendly Function call errors - Jakub Filak

### Fixed
- correctly handle calls to Function Imports without return type - Jakub Filak
- correctly serialize DateTime values to JSON in create/update methods - Martin Miksik
- remove timezone info from DateTime URL literals - Martin Miksik

## [1.2.3]

### Added
- add support for whitelisted and custom namespaces - Martin Miksik
- add Microsoft's edm namespace to whitelisted namespaces - Martin Miksik

## [1.2.2]

### Fixed
- fix parsing of Namespaces with several dots - Jakub Filak

## [1.2.1]

### Changed
- handle association set ends with same entity sets - Lubos Mjachky

## [1.2.0]

### Added
- add implementation of $count - FedorSelitsky

### Fixed
- fix searching for Associations Set without Namespace - Jakub Filak

### Changed
- reword error messages for Association Sets - Jakub Filak

## [1.1.2]

### Fixed
- client: correctly detect MIME of $metadata - Jakub Filak

### Changed
- dependencies: Update setup.py - minimal lxml instead of pinned. - Petr Hanak

## 1.1.1 - First PIP package release

[Unreleased]: https://github.com/SAP/python-pyodata/compare/1.10.0...HEAD
[1.10.0]: https://github.com/SAP/python-pyodata/compare/1.9.2...1.10.0
[1.9.2]: https://github.com/SAP/python-pyodata/compare/1.9.1...1.9.2
[1.9.1]: https://github.com/SAP/python-pyodata/compare/1.9.0...1.9.1
[1.9.0]: https://github.com/SAP/python-pyodata/compare/1.8.0...1.9.0
[1.8.0]: https://github.com/SAP/python-pyodata/compare/1.7.1...1.8.0
[1.7.1]: https://github.com/SAP/python-pyodata/compare/1.7.0...1.7.1
[1.7.0]: https://github.com/SAP/python-pyodata/compare/1.6.0...1.7.0
[1.6.0]: https://github.com/SAP/python-pyodata/compare/1.5.0...1.6.0
[1.5.0]: https://github.com/SAP/python-pyodata/compare/1.4.0...1.5.0
[1.4.0]: https://github.com/SAP/python-pyodata/compare/1.3.0...1.4.0
[1.3.0]: https://github.com/SAP/python-pyodata/compare/1.2.3...1.3.0
[1.2.3]: https://github.com/SAP/python-pyodata/compare/1.2.2...1.2.3
[1.2.2]: https://github.com/SAP/python-pyodata/compare/1.2.1...1.2.2
[1.2.1]: https://github.com/SAP/python-pyodata/compare/1.2.0...1.2.1
[1.2.0]: https://github.com/SAP/python-pyodata/compare/1.1.2...1.2.0
[1.1.2]: https://github.com/SAP/python-pyodata/compare/1.1.1...1.1.2
