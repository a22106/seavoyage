.. seavoyage documentation master file

Seavoyage Documentation
=======================

Welcome to seavoyage's documentation! Seavoyage is an improved version of the searoute package 
for calculating the shortest sea route between two points on Earth.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   api_reference
   examples
   contributing

Features
--------

* Maritime network-based optimal route calculation
* Custom restriction zones (GeoJSON) registration and application
* Multiple maritime network resolutions (5km~100km)
* Folium-based route/network map visualization
* Network and route GeoJSON conversion

Quick Example
-------------

.. code-block:: python

   import seavoyage as sv

   # Get quick route information
   start = (129.17, 35.075)  # Busan
   end = (4.158, 51.921)     # Rotterdam
   
   info = sv.get_quick_route(start, end)
   print(f"Distance: {info['distance_nm']:.1f} nautical miles")
   print(f"Duration: {info['duration_hours']:.1f} hours")

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`