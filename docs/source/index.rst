.. xarray-eop documentation master file, created by
   sphinx-quickstart on Thu Feb 22 11:24:33 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to xarray-eop's documentation!
======================================

xarray_eop is an xarray backend to open and manipulate EO data products from the Copernicus Sentinel mission,
in the legacy SAFE format as well as the new zarr format used by the Re-engineered python processors.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

.. note::

   This project is under active development.

Features
========

- specific xarray backends : ["sentinel-3","eop"] to be used with  `xarray.open_dataset` function
  - **sentinel-3**: handles Sentinel-3 SAFE product (.SEN3)
  - **eop**: Generic zarr product (.zarr) following the EOPF Product Structure Format
- Use of experimental xarray-datatree to represent the overall hierarchical data
- Conversion of products from SAFE to EOP Zarr
- Create empty products based on zmetadata template


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Contents
========

.. toctree::

   usage
   tutorial
   api
