"""Optional MCP server exposing the tool layer over the Model Context Protocol.

The tools in :mod:`app.mcp.tools` are the real boundary and are used in-process
today. This module wraps the *same* functions as MCP tools so an external MCP
client can call them too. It requires the ``mcp`` package (Python >= 3.10); on
older interpreters ``build_server`` raises with guidance instead of failing at
import time, so the rest of the app keeps running on 3.9.

Run (needs Python 3.10+ and ``pip install mcp``):

    python -m app.mcp.server
"""
from __future__ import annotations

from typing import List, Optional

from app.mcp import tools


def build_server():
    """Build a FastMCP server exposing the catalog tools. Requires `mcp`."""
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # noqa: BLE001 - mcp not installed / Python < 3.10
        raise RuntimeError(
            "The 'mcp' package (Python >= 3.10) is required to run the MCP server. "
            "Install it with `pip install mcp`. The in-process tool layer in "
            "app.mcp.tools works without it."
        ) from exc

    mcp = FastMCP("caterer-catalog")

    @mcp.tool()
    def get_dishes(course: Optional[str] = None) -> list:
        """Catalog dishes with priced recipes, optionally filtered by course."""
        return [d.model_dump() for d in tools.get_dishes(course)]

    @mcp.tool()
    def get_decor_packages() -> list:
        """Decor packages, priced ascending."""
        return [d.model_dump() for d in tools.get_decor_packages()]

    @mcp.tool()
    def get_venues(min_capacity: int = 0) -> list:
        """Venues seating at least `min_capacity` guests, cheapest first."""
        return [v.model_dump() for v in tools.get_venues(min_capacity)]

    @mcp.tool()
    def get_stock(item_names: Optional[List[str]] = None) -> list:
        """Current on-hand stock levels."""
        return [s.model_dump() for s in tools.get_stock(item_names)]

    return mcp


if __name__ == "__main__":
    build_server().run()
