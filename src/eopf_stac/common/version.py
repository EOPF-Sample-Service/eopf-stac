def get_eopf_stac_version(self) -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("eopf-stac")
    except PackageNotFoundError:
        __version__ = "unknown"

    return __version__
