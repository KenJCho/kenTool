from unit_conversion import convert_unit


def approx_equal(a: float, b: float, tol: float = 1e-8) -> bool:
    return abs(a - b) <= tol


def test_conversions() -> None:
    assert approx_equal(convert_unit(1, "ft", "m"), 0.3048)
    assert approx_equal(convert_unit(12, "in", "mm"), 304.8)
    assert approx_equal(convert_unit(1, "in^2", "mm^2"), 645.16)
    assert approx_equal(convert_unit(1, "in^4", "mm^4"), 416231.99199999997)
    assert approx_equal(convert_unit(1, "psf", "kN/m^2"), 0.047880258988)
    assert approx_equal(convert_unit(1, "plf", "kN/m"), 0.014593903007)
    assert approx_equal(convert_unit(1, "lb", "N"), 4.4482216152605)
    assert approx_equal(convert_unit(1, "kip", "kN"), 4.4482216152605)
    assert approx_equal(convert_unit(1, "ksi", "MPa"), 6.894757293168361)
    assert approx_equal(convert_unit(1, "pcf", "kg/m^3"), 16.0184633739602)
    assert approx_equal(convert_unit(1, "in/s", "mm/s"), 25.4)
    assert approx_equal(convert_unit(1, "in/s^2", "m/s^2"), 0.0254)


def test_invalid_category() -> None:
    try:
        convert_unit(1, "ft", "lb")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for mismatched categories")


if __name__ == "__main__":
    test_conversions()
    test_invalid_category()
    print("All tests passed.")
