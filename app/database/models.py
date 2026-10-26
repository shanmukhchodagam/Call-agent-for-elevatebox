from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class LeadRecord:
    call_id: Optional[int]
    phone_number: Optional[str]
    business_type: Optional[str]
    product_count_min: Optional[int]
    product_count_max: Optional[int]
    payment_gateway: Optional[bool]
    customer_accounts: Optional[bool]
    guest_checkout: Optional[bool]
    timeline_months: Optional[int]
    budget_min: Optional[int]
    budget_max: Optional[int]
    additional_requirements: Optional[str]
    inferred_business_type: Optional[str] = None
    classification: Optional[str] = None
    score: Optional[int] = None
    reasons: Optional[List[str]] = None
    transcript: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CallbackRecord:
    call_id: Optional[int]
    phone_number: Optional[str]
    raw_request: str
    scheduled_time: str
    timezone: str
    status: str = "scheduled"
    id: Optional[int] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FollowupRecord:
    call_id: Optional[int]
    phone_number: Optional[str]
    message: str
    channel: str = "whatsapp"
    status: str = "logged"
    id: Optional[int] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
