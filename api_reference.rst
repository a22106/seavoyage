API Reference
=============

This page contains the complete API reference for the seavoyage package.

Main API Functions
------------------

Simple API (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: seavoyage.get_quick_route

.. autofunction:: seavoyage.calculate_sea_route_simple

.. autofunction:: seavoyage.calculate_sea_route

Legacy API
~~~~~~~~~~

.. autofunction:: seavoyage.seavoyage

Data Models
-----------

Route Configuration
~~~~~~~~~~~~~~~~~~~

.. autoclass:: seavoyage.RouteCoordinates
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: seavoyage.RouteConfig
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: seavoyage.NetworkConfig
   :members:
   :undoc-members:
   :show-inheritance:

Route Results
~~~~~~~~~~~~~

.. autoclass:: seavoyage.RouteResult
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: seavoyage.RouteProperties
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: seavoyage.RouteGeometry
   :members:
   :undoc-members:
   :show-inheritance:

Network Classes
---------------

.. autoclass:: seavoyage.MNetwork
   :members:
   :undoc-members:
   :show-inheritance:

Restriction Management
----------------------

.. autofunction:: seavoyage.register_custom_restriction

.. autofunction:: seavoyage.list_custom_restrictions

.. autofunction:: seavoyage.get_custom_restriction

.. autofunction:: seavoyage.clear_custom_restrictions

Network Resolution Functions
----------------------------

.. autofunction:: seavoyage.get_m_network_5km

.. autofunction:: seavoyage.get_m_network_10km

.. autofunction:: seavoyage.get_m_network_20km

.. autofunction:: seavoyage.get_m_network_50km

.. autofunction:: seavoyage.get_m_network_100km

Utilities
---------

Mapping Utilities
~~~~~~~~~~~~~~~~~

.. autofunction:: seavoyage.utils.map_folium

.. autofunction:: seavoyage.utils.plot_route

Coordinate Utilities
~~~~~~~~~~~~~~~~~~~~

.. autofunction:: seavoyage.utils.is_in_ocean

.. autofunction:: seavoyage.utils.get_nearest_ocean_point

GeoJSON Utilities
~~~~~~~~~~~~~~~~~

.. autofunction:: seavoyage.utils.geojson_to_linestring

.. autofunction:: seavoyage.utils.linestring_to_geojson

Exceptions
----------

.. autoexception:: seavoyage.exceptions.SeavoyageError
   :show-inheritance:

.. autoexception:: seavoyage.exceptions.InvalidCoordinatesError
   :show-inheritance:

.. autoexception:: seavoyage.exceptions.RouteNotFoundError
   :show-inheritance:

.. autoexception:: seavoyage.exceptions.NetworkError
   :show-inheritance:

.. autoexception:: seavoyage.exceptions.RestrictionError
   :show-inheritance: