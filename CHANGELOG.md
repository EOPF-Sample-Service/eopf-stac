# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.13.0] - 2026-08-13

### Fixed
- Add `zarr` dependency to pyproject.toml [#68](https://github.com/EOPF-Sample-Service/eopf-stac/issues/68)
- Correctly set href for zipped EOPF product asset based on EOPF products [#75](https://github.com/EOPF-Sample-Service/eopf-stac/pull/75)


## [0.12.0] - 2026-02-03

### Added

- Add support for products converted with CPM 2.6.4 [#66](https://github.com/EOPF-Sample-Service/eopf-stac/issues/66)
- Add option to output to file [#65](https://github.com/EOPF-Sample-Service/eopf-stac/pull/65)
- Make the CLI executable [#64](https://github.com/EOPF-Sample-Service/eopf-stac/pull/64)


### Fixed

- Inconsistent `proj:bbox` with `proj:code` [#60](https://github.com/EOPF-Sample-Service/eopf-stac/issues/60)
- Missing `proj:bbox` in STAC asset metadata for older Sentinel-2 data [#61](https://github.com/EOPF-Sample-Service/eopf-stac/issues/61)

## [0.11.0] - 2025-10-28

### Added

- Add support for products converted with CPM 2.6.2 [#49](https://github.com/EOPF-Sample-Service/eopf-stac/issues/49)
- Add additional asset to enable download of individual Zarr stores as zip file [#56](https://github.com/EOPF-Sample-Service/eopf-stac/issues/56)

### Changed

- Use the [common band names](https://github.com/stac-extensions/eo/tree/main?tab=readme-ov-file#common-band-names) in Sentinel-2 and Sentinel-3 assets [#47](https://github.com/EOPF-Sample-Service/eopf-stac/issues/47)
- Use version 2.0.0 of [eo extension](https://github.com/stac-extensions/eo) in items and assets [#36](https://github.com/EOPF-Sample-Service/eopf-stac/issues/36)

## [0.10.0] - 2025-09-23

### Added

- Add support for products converted with CPM 2.5.9, 2.6.0 and 2.6.1
- Add alternate link pointing to corresponding STAC item at CDSE [#37](https://github.com/EOPF-Sample-Service/eopf-stac/issues/37)
- Add support for Sentinel-3 SLSTR L2 FRP product [#12](https://github.com/EOPF-Sample-Service/eopf-stac/issues/12)
- Add field `processing:version` to STAC item [#28](https://github.com/EOPF-Sample-Service/eopf-stac/issues/28)
- Add CPM version to `processing:software` field in STAC item [#31](https://github.com/EOPF-Sample-Service/eopf-stac/issues/31)
- Add `deprecated` field from [version extension](https://github.com/stac-extensions/version) to STAC item [#43](https://github.com/EOPF-Sample-Service/eopf-stac/issues/43)
- Add CLI option to provide source URI of converted product [#41](https://github.com/EOPF-Sample-Service/eopf-stac/issues/41)

### Changed

- The STAC item id will be identical to the name of the Zarr store, without the `.zarr` extension [#42](https://github.com/EOPF-Sample-Service/eopf-stac/issues/42)

### Fixed

- Add support for Sentinel-1 GRD and SLC products converted with CPM 2.6.0 [#33](https://github.com/EOPF-Sample-Service/eopf-stac/issues/33)
- Correct antimeridian and polar crossing geometries [#39](https://github.com/EOPF-Sample-Service/eopf-stac/issues/39)

## [0.9.1] - 2025-05-20

### Fixed

- Add version for package dependencies [#19](https://github.com/EOPF-Sample-Service/eopf-stac/issues/19)

## [0.9.0] - 2025-04-29

### Added

- Add support for the following Sentinel 3 OLCI products: `S03OLCEFR`, `S03OLCERR`, `S03OLCLFR`, `S03OLCLRR` [#9](https://github.com/EOPF-Sample-Service/eopf-stac/issues/9)
- Add support for the following Sentinel 3 SLSTR products: `S03SLSRBT`, `S03SLSLST` [#11](https://github.com/EOPF-Sample-Service/eopf-stac/issues/11)
- Add tests [#10](https://github.com/EOPF-Sample-Service/eopf-stac/issues/10)

## [0.8.0] - 2025-04-15

### Added

- Add support for HTTPS product URLs ([#5](https://github.com/EOPF-Sample-Service/eopf-stac/issues/5))
- Add support for Sentinel 1 instrument modes `EW`, `SM`, `WV` and corresponding EOPF product types `S01SSMGRH`, `S01SEWGRH`, `S01SWVSLC`, `S01SSMSLC`, `S01SEWSLC`, `S01SEWOCN`, `S01SSMOCN`, `S01SWVOCN` ([#7](https://github.com/EOPF-Sample-Service/eopf-stac/issues/7))

## [0.7.1] - 2025-04-14

### Fixed

- Added `xarray` dependency ([#8](https://github.com/EOPF-Sample-Service/eopf-stac/issues/8))

## [0.7.0] - 2025-04-14

### Changed

- Change name of [EOPF Xarray backend](https://github.com/EOPF-Sample-Service/xarray-eopf) parameter `mode` to `op_mode` ([#3](https://github.com/EOPF-Sample-Service/eopf-stac/issues/3))


## [0.6.0] - 2025-03-24

### Added

- Add support for Sentinel EOPF product types `S01SIWGRH`, `S01SIWSLC`, `S01SIWOCN`, `S02MSIL1C`, `S02MSIL2A`
