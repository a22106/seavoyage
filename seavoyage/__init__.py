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
    reset_custom_restrictions,
    clear_custom_restrictions
)
from seavoyage.exceptions import (
    RouteError,
    UnreachableDestinationError,
    StartInRestrictionError,
    DestinationInRestrictionError,
    IsolatedOriginError
)
from seavoyage.api import (
    calculate_sea_route,
    calculate_sea_route_simple,
    get_quick_route
)
from seavoyage.models import (
    RouteConfig,
    NetworkConfig,
    RouteCoordinates,
    RouteResult,
    RouteProperties,
    RouteGeometry
)
from seavoyage.enhanced_api import (
    seavoyage_with_progress,
    calculate_sea_route_with_recovery
)
from seavoyage.callbacks import (
    ProgressCallback,
    SimpleProgressCallback,
    FunctionProgressCallback,
    ProgressInfo,
    ProgressStage
)
from seavoyage.retry import (
    RetryConfig,
    RetryStrategy
)

__all__ = (
    [MNetwork]+
    [seavoyage, custom_seavoyage]+
    [calculate_sea_route, calculate_sea_route_simple, get_quick_route]+
    [seavoyage_with_progress, calculate_sea_route_with_recovery]+
    [RouteConfig, NetworkConfig, RouteCoordinates, RouteResult, RouteProperties, RouteGeometry]+
    [ProgressCallback, SimpleProgressCallback, FunctionProgressCallback, ProgressInfo, ProgressStage]+
    [RetryConfig, RetryStrategy]+
    [*utils.__all__]+
    [PACKAGE_ROOT, MARNET_DIR, DATA_DIR]+
    [constants]+
    [register_custom_restriction, get_custom_restriction, list_custom_restrictions, reset_custom_restrictions, clear_custom_restrictions]+
    [RouteError, UnreachableDestinationError, StartInRestrictionError, DestinationInRestrictionError, IsolatedOriginError]
)
