"""
Seavoyage API
"""
from seavoyage import utils
from seavoyage.classes.m_network import MNetwork
from seavoyage import constants
from seavoyage.base import seavoyage, custom_seavoyage
from seavoyage.utils import *
from seavoyage.settings import *
from seavoyage.modules import *
from seavoyage.modules.restriction import (
    register_custom_restriction, 
    get_custom_restriction, 
    list_custom_restrictions,
    reset_custom_restrictions
)
from seavoyage.exceptions import (
    RouteError,
    UnreachableDestinationError,
    StartInRestrictionError,
    DestinationInRestrictionError,
    IsolatedOriginError
)

__all__ = (
    [MNetwork]+
    [seavoyage, custom_seavoyage]+
    [*utils.__all__]+
    [PACKAGE_ROOT, MARNET_DIR, DATA_DIR]+
    [constants]+
    [register_custom_restriction, get_custom_restriction, list_custom_restrictions, reset_custom_restrictions]+
    [RouteError, UnreachableDestinationError, StartInRestrictionError, DestinationInRestrictionError, IsolatedOriginError]
)
