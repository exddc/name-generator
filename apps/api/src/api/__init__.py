from importlib.metadata import PackageNotFoundError, version

__title__ = "Domain Generator API"
__description__ = "API for the Domain Generator service"
try:
    __version__ = version("api")
except PackageNotFoundError:
    __version__ = "0.1.0"