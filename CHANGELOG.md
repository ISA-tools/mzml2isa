# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
[Unreleased]: https://github.com/ISA-Tools/mzml2isa/compare/v1.1.0...HEAD


## [v1.1.0] - 2022-10-14
[v1.1.0]: https://github.com/ISA-Tools/mzml2isa/compare/v1.0.4...v1.1.0

### Added
- Support for Python 3.10.
### Changed
- Updated redistributed PSI-MS file to latest version.
- Bumped required `pronto` dependency to `v2.0` and up.
- Use `functools.cached_property` instead of `cached_property.cached_property` in recent Python version where it is available.
- Use `importlib.resources` instead of `pkg-resources` for managing the package resources.
### Removed
- Support for Python 2.7.
- `six` dependency.


## [v1.0.4] - 2021-12-14
[v1.0.4]: https://github.com/ISA-Tools/mzml2isa/compare/v1.0.3...v1.0.4
### Fixed
- Allow higher versions of `openpyxl` to be installed ([#46](https://github.com/ISA-tools/mzml2isa/pull/46)).
### Changed
- Added support for Python 3.9.


## [v1.0.3] - 2020-04-01
[v1.0.3]: https://github.com/ISA-Tools/mzml2isa/compare/v1.0.2...v1.0.3
### Fixed
- Issue with cli not being accessible as expected - see PR ([#40](https://github.com/ISA-tools/mzml2isa/pull/43)).
### Changed
- Added support for Python 3.8.
- Changed Pyinstaller requirement for >= v3.6 (this is only for making the windows standalone executable and is not part of the standard installation)


## [v1.0.2] - 2019-10-01
[v1.0.2]: https://github.com/ISA-Tools/mzml2isa/compare/v1.0.1...v1.0.2
### Fixed
- Issue in ISA Investigation template failing the ISA-API test suite.
  ([#39](https://github.com/ISA-tools/mzml2isa/issues/39)).
### Changed
- Dropped support for Python 3.4.
- Added support for Python 3.7.
- Bumped `pronto` requirement to `0.12.0`.
- Bumped `fs` requirement to `2.4.0`.


## [v1.0.1] - 2019-01-06
[v1.0.1]: https://github.com/ISA-Tools/mzml2isa/compare/v1.0.0...v1.0.1
### Changed
- Added `fs` version `2.2.0` to supported `fs` versions.
- Bumped `pronto` requirement to `0.11.0`


## [v1.0.0] - 2018-10-16
[v1.0.0]: https://github.com/ISA-Tools/mzml2isa/compare/v0.5.1...v1.0.0
### Added
- Added GPLv3 license file to source and `wheel` distribution.
- Added unit testing framework using Metabolights data from the EBI FTP server.
### Changed
- Changed inner API to use Pyfilesystem2 to access to `mzML` and `imzML` files.
- Made `mzml2isa` directly output files in the directory passed to the `-o` flag.
- Switched to `tqdm` to display the progress bar.
### Fixed
- Updated `imzML` investigation template to support multiple assays.
- Fixed crash case when parsing a ZIP file.
- Updated local `psi-ms.obo` with newer version without dead links.
- Pinned dependencies in `setup.cfg`.
- Fixed crash on missing `Spectrum representation`.
