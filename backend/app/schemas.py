"""Pydantic request/response models for the planning API."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    event_type: str = Field(..., examples=["wedding reception"])
    guest_count: int = Field(..., gt=0, examples=[120])
    budget: float = Field(0, ge=0, description="Total ingredient budget; 0 = no limit")
    dietary_restrictions: List[str] = Field(default_factory=list,
                                            examples=[["vegetarian", "no nuts"]])
    cuisine_pref: Optional[str] = Field(None, examples=["Indian"])
    location: Optional[str] = None
    event_date: Optional[str] = None
    # optional caller-supplied planning session id; generated if omitted
    session_id: Optional[str] = None

    def to_requirements(self) -> dict:
        return {
            "event_type": self.event_type,
            "guest_count": self.guest_count,
            "budget": self.budget,
            "dietary_restrictions": self.dietary_restrictions,
            "cuisine_pref": self.cuisine_pref or "",
            "location": self.location or "",
            "event_date": self.event_date or "",
        }


class ApproveRequest(BaseModel):
    """Freeze the chosen option (tier) for an event into an approved order."""

    event_id: str
    option_id: str


class VendorDecisionRequest(BaseModel):
    """Human decision at the vendor approval gate."""

    decision: str = Field(..., pattern="^(approve|reject)$",
                          description="'approve' places the order; 'reject' cancels it")
