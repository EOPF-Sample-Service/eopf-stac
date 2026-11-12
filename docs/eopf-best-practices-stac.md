
# EOPF STAC Best Practices

## Table of Contents

- [EOPF STAC Best Practices](#eopf-stac-best-practices)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Glossary](#glossary)
  - [General Rules](#general-rules)
  - [Product Type Specific Rules](#product-type-specific-rules)
  - [Required Extensions](#required-extensions)
  - [Credits](#credits)

## Introduction

This document defines best practices for representing ESA's EOPF products in STAC. It adopts the [STAC Zarr and N-Dimensional Array Best Practices](https://github.com/radiantearth/stac-best-practices/blob/71b1b2a94abe42625a3f9f5f224030b914598412/best-practices-zarr-ndarray.md) document to the characteristics of EOPF Zarr stores and complements the [EOPF metadata conventions](https://cpm.pages.eopf.copernicus.eu/eopf-cpm/main/PSFD/7-metadata.html) with respect to STAC assets.

These guidelines address:

- Mapping of EOPF data model concepts to STAC concepts
- Metadata requirements for different EOPF product types
  - Asset organisation and metadata 
  - Integration patterns with existing extensions
  - Metadata inheritance when converting from SAFE to EOPF
- etc.

Specifications referenced or applied in this document:
- [STAC Specification v1.1](https://github.com/radiantearth/stac-spec/tree/v1.1.0)
- [STAC Zarr and N-Dimensional Array Best Practices](https://github.com/radiantearth/stac-best-practices/blob/71b1b2a94abe42625a3f9f5f224030b914598412/best-practices-zarr-ndarray.md)
- [EOPF Metadata Representation](https://cpm.pages.eopf.copernicus.eu/eopf-cpm/main/PSFD/7-metadata.html)
- [EOPF Product Structure and Format Definition](https://cpm.pages.eopf.copernicus.eu/eopf-cpm/main/PSFD/index.html)
- [EOPF STAC extension](https://github.com/CS-SI/eopf-stac-extension)
- etc.

## Glossary

For complete terminology please also refer to
- the [EOPF Core Python Modules Documentation](https://cpm.pages.eopf.copernicus.eu/eopf-cpm/main/index.html)
- the [STAC Zarr and N-Dimensional Array Best Practices](#)
- the [Zarr specification](https://zarr-specs.readthedocs.io/en/latest/v3/core/#concepts-and-terminology) 

## General Rules

## Product Type Specific Rules

## Required Extensions

## Credits