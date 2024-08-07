Get Started
===========

Installation
------------

Install xarray-eop using pip:

.. code-block:: console

   $ pip install xarray-eop

.. currentmodule:: xarray_eop

A simple extended Path class
----------------------------

To handle both local filesystem path as well as distributed cloud storage or fsspec-like chain URL, a simple class :obj:`EOPath` is implemented deriving from :obj:`pathlib.Path`

.. ipython:: python

    from xarray_eop.path import EOPath

    p = EOPath("s3://bucket/prod/file")
    print(p)
    print(p.path)
    print(p.name)
    print(p.protocol)

    p = EOPath("zip::s3//bucket/prod/file.zip")
    print(p)
    print(p.zip)

Cloud-storage credentials
-------------------------
In `xarray_eop`, functions to open dataset/datatree can also access products in S3 object storage. The credentials
can be explicitely passed to the function using the addition kwargs *backend_kwargs*, whose value is a dictionary in
the form {"s3":{"key": *access-key*,"secret": *secret-key*,"endpoint_url": *endpoint_url*}}. In the case where
no credentials are explicitely set, the function tried to retrieve it from environment variable.

Additionaly `xarray_eop` provides few functions among which:

.. autosummary::

    xarray_eop.get_credentials
    xarray_eop.get_s3filesystem

.. ipython:: python

    from xarray_eop import EOPath, get_s3filesystem

    url = EOPath("s3://buc-acaw-dpr/Samples")
    s3fs = get_s3filesystem(url)
    s3fs.exists(url.path)
    s3fs.ls(url.path)

Open Sentinel-3 SAFE product
----------------------------

Open a specific dataset using :obj:`xarray.dataset`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `sentinel-3` backend mainly consists of organizing the structure following the new EOP zarr Product Structure specification.
Simple datasets can be created from a specific netcdf file or a group corresponding to a valid EOP zarr path.


.. py:function:: xr.open_dataset(product,file_or_group,engine="sentinel-3",decoded_times=True,backend_kwargs={})

   :param product: Path to the SEN3 product
   :type product: str or Path
   :param file_or_group: Netcdf files from the product to be opened or equivalent EOP zarr group
   :type file_or_group: str or Path
   :param backend_kwargs: kwargs specific to the backend. Specifically, it is used to passe the credentials to a S3 bucket, as backend_kwargs = {"storage_options": {"s3": {"key"=...,"secret"=...,"endpoint_url"=...}}}
   :type backend_kwargs: Dict
   :param decoded_times:
   :type decoded_times: boolean
   :return: xarray dataset
   :rtype: xarray.dataset


For instance, opening the *instrument_data.nc* file from OLCI L1 ERR product will be as follows.

.. ipython:: python
    :okwarning:

    import xarray as xr
    from xarray_eop.path import EOPath

    buc_name = EOPath("s3://buc-acaw-dpr")
    product = buc_name / "Samples/SAFE/S3B_OL_1_ERR____20230506T015316_20230506T015616_20230711T065804_0179_079_117______LR1_D_NR_003.SEN3"
    ds = xr.open_dataset(
        product,
        file_or_group="instrument_data.nc",
        engine="sentinel-3",
    )
    print(ds)

    %xmode minimal

.. note::
    The credentials to the cloud storage can be passed to the function using the *backend_kwargs* arguments as

    .. code-block:: json

        { "storage_options":
            { "s3":
                { "key"="","secret"="","endpoint_url"=""}
            }
        }

    If *storage_options* are not passed, the function looks for the environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL`
    or `S3_KEY`, `S3_SECRET`, `S3_URL`


Open the whole SAFE product
~~~~~~~~~~~~~~~~~~~~~~~~~~~
The whole product can be represented by the experimental DataTree hierarchical structure, using the high-level function:

.. autosummary::

    xarray_eop.api.open_datatree

Now let's open the whole OLCI L1 ERR product from s3 bucket:

.. ipython:: python
    :okwarning:

    import xarray as xr
    from xarray_eop import open_datatree
    from xarray_eop import EOPath

    buc_name = EOPath("s3://buc-acaw-dpr")
    product = buc_name / "Samples/SAFE/S3B_OL_1_ERR____20230506T015316_20230506T015616_20230711T065804_0179_079_117______LR1_D_NR_003.SEN3"
    dt = open_datatree(product)
    print(dt)


Verification Tool
-----------------
xarray_eop comes with a verification tool which compares to input products (SAFE or Zarr)
The CLI tool can be run and displays option by:

.. code-block:: bash

   $ compare --help
