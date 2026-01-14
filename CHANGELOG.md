# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog] and this project adheres to [Semantic Versioning].

<!--
GitHub MD Syntax:
https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax

Highlighting:
https://docs.github.com/assets/cb-41128/mw-1440/images/help/writing/alerts-rendered.webp

> [!NOTE]
> Highlights information that users should take into account, even when skimming.

> [!IMPORTANT]
> Crucial information necessary for users to succeed.

> [!WARNING]
> Critical content demanding immediate user attention due to potential risks.
-->

## [In Development] - Unreleased

<!--
Section Order:

### Added
### Fixed
### Changed
### Deprecated
### Removed
### Security
-->

<!-- Your changes go here -->

### Added

- Tests

### Fixed

- Some methods are static and should be decorated as such

### Changed

- Made it a proper Python package
- Normalize international prefix and remove non-numeric characters except `*`

### Removed

- Obsolete functions

## [1.1.1] - 2025-12-06

### Fixed

- "Home" number type was not mapped correctly. As GEQUDIO only allows 3 types
  (Mobile, Telephone, Other), "Home" is now mapped to "Other", since "Telephone" is
  displayed as "Office" on the phone.

### Changed

- Reduce the number of calls to Nextcloud by fetching all contacts in one request

## [1.1.0] - 2025-12-06

### Added

- Makefile configuration
- Changelog file
- Isort configuration
- Pylint configuration

### Changed

- Moved functions from the global namespace into the class

## [1.0.0] - 2025-12-05

### Added

- Initial release of Nextcloud Contacts to GEQUDIO XML tool

<!-- Links -->

[1.0.0]: https://github.com/ppfeufer/nextcloud-contacts-to-gequdio/commits/v1.0.0 "v1.0.0"
[1.1.0]: https://github.com/ppfeufer/nextcloud-contacts-to-gequdio/compare/v1.0.0...v1.1.0 "v1.1.0"
[1.1.1]: https://github.com/ppfeufer/nextcloud-contacts-to-gequdio/compare/v1.1.0...v1.1.1 "v1.1.1"
[in development]: https://github.com/ppfeufer/nextcloud-contacts-to-gequdio/compare/v1.1.1...HEAD "In Development"
[keep a changelog]: https://keepachangelog.com/en/1.0.0/ "Keep a Changelog"
[semantic versioning]: https://semver.org/spec/v2.0.0.html "Semantic Versioning"
