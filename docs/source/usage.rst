Get Started
===========

Installation
------------

Install xarray-eop using pip:

.. code-block:: console

   $ pip install xarray-eop


Open Sentinel-3 SAFE product
----------------------------

The `sentinel3` backend mainly consists of organizing the structure following the new EOP zarr Product Structure specification.
Simple datasets can be created from a specific netcdf file or a group corresponding to a valid EOP zarr path.
The whole product can be represented by the experimental DataTree hierarchical structure.

.. py:function:: xr.open_dataset(product,file_or_group="instrument_data.nc",engine="sentinel-3")

   Return an xarray dataset.

   :param product: Path to the SEN3 product
   :type product: str or Path
   :return: xarray dataset
   :rtype: xarray.dataset


Open Sentinel zarr product
--------------------------
 Opening gridded measurement data with xarray

.. currentmodule:: xarray_eop

.. ipython:: python
    .. :suppress:

    import xarray as xr
    from pathlib import Path

    SAMPLE_PATH = Path("/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Products/Zarr_Beta")
    product = SAMPLE_PATH / "S3OLCEFR_20230506T015316_0180_B117_T931.zarr"

    %xmode minimal

.. ipython:: python

    group = "measurements/image"
    # Open with custom engine="eop"
    ds=xr.open_dataset(SAMPLE_PATH / product, group=group, engine="eop")
    rad = ds.oa01_radiance
    rad


.. ipython:: python

    import matplotlib.pyplot as plt
    plt.figure(figsize=(14, 6))
    ax = plt.axes()
    ds.oa01_radiance.plot.pcolormesh(
        ax=ax,
        x="longitude", y="latitude", add_colorbar=False
    )


Opening the whole product with datatree

.. ipython:: python

    import datatree
    #datatree.open_datatree(product,engine="zarr")
    print("toto")