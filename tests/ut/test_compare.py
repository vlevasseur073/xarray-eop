import pytest

from xarray_eop.verification.compare import parse_cmp_vars


@pytest.mark.unit
def test_compare_utils() -> None:
    reference = "/path/to/product1"
    new = "path/to/product2/"
    cmp_vars = "group/var1:group/var2,var3:/grp/var4"

    list_prods = parse_cmp_vars(reference, new, cmp_vars)
    assert list_prods[0] == (
        "path/to/product1/group/var1",
        "path/to/product2/group/var2",
    )
    assert list_prods[1] == ("/path/to/product1/var3", "path/to/product2/grp/var4")
