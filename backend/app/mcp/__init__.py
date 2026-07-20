"""MCP tool layer (T7).

A single typed, validated boundary between the agents and the local database.
Agents call the tools in :mod:`app.mcp.tools` (which return the Pydantic DTOs in
:mod:`app.mcp.schemas`) instead of touching SQLAlchemy directly, giving one place
for data access and validation. The same tools can be exposed over the Model
Context Protocol via :mod:`app.mcp.server` (optional).
"""
