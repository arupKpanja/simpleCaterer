"""T7: MCP tool layer returns validated DTOs (the agents' only data path)."""
from app.mcp import tools
from app.mcp.schemas import DishDTO, StockLevelDTO


def test_get_dishes_returns_dtos_with_derived_allergens():
    dishes = tools.get_dishes()
    assert dishes and all(isinstance(d, DishDTO) for d in dishes)
    biryani = next(d for d in dishes if d.name == "Chicken Biryani")
    assert biryani.ingredients
    # allergens are the derived union of ingredient allergens
    expected = sorted({a for line in biryani.ingredients for a in line.allergens})
    assert biryani.allergens == expected


def test_get_dishes_filtered_by_course():
    mains = tools.get_dishes(course="main")
    assert mains and all(d.course == "main" for d in mains)


def test_get_venues_respects_min_capacity():
    venues = tools.get_venues(min_capacity=300)
    assert venues and all(v.capacity >= 300 for v in venues)
    # ordered by price ascending
    assert [v.price for v in venues] == sorted(v.price for v in venues)


def test_get_decor_packages_priced_ascending():
    decor = tools.get_decor_packages()
    assert [d.price for d in decor] == sorted(d.price for d in decor)


def test_get_stock_returns_levels():
    stock = tools.get_stock(["Paneer", "Basmati rice"])
    assert {s.item for s in stock} == {"Paneer", "Basmati rice"}
    assert all(isinstance(s, StockLevelDTO) and s.stock_qty >= 0 for s in stock)


def test_mcp_server_import_is_safe_without_mcp_package():
    """Importing the server module never fails; build_server degrades gracefully."""
    import importlib.util as u
    from app.mcp import server

    if u.find_spec("mcp") is None:  # Python < 3.10 here — mcp can't be installed
        import pytest
        with pytest.raises(RuntimeError, match="mcp"):
            server.build_server()
    else:
        assert server.build_server() is not None
