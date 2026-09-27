from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from app.models.domain import CategoryContext, MerchantContext, TriggerContext, CustomerContext
from app.models.schemas import ComposedMessage

class BaseComposer(ABC):
    @abstractmethod
    def can_handle(self, trigger_kind: str) -> bool:
        """Return True if this composer has specialized handling for this trigger kind."""
        pass

    @abstractmethod
    def compose(
        self,
        category: CategoryContext,
        merchant: MerchantContext,
        trigger: TriggerContext,
        customer: Optional[CustomerContext] = None
    ) -> ComposedMessage:
        """Compose message given 4-context input."""
        pass
