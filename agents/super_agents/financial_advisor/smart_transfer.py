"""
Smart Transfer — Transfer Decision Engine
==========================================
Decides where to pull money when bills are at risk.

Priority Order:
1. Chime (Savings) — Preferred, no impact on lifestyle
2. Capital One Checking (Fun) — "Austerity Mode", requires confirmation
3. Emergency — Alert only, no auto-transfer
"""

from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .bank_ecosystem import BankEcosystem


@dataclass
class TransferPlan:
    """A recommended transfer to cover a shortfall."""
    source_account_id: Optional[str]  # None if no source available
    source_name: str
    destination_account_id: str
    destination_name: str
    amount: float
    label: str  # Human-readable description
    approved: bool  # Can be auto-approved?
    needs_confirmation: bool  # Requires user confirmation?
    urgency: str  # "low", "medium", "high", "critical"


class SmartTransfer:
    """
    Decides where to pull money when bills are at risk.
    
    Decision Tree:
    1. Check Chime (HYSA/Savings)
       - If sufficient: APPROVE transfer from savings
       - If partial: Note partial, continue to step 2
    
    2. Check Capital One Checking (Fun)
       - If sufficient: APPROVE "Austerity Mode"
       - User must confirm pulling from fun money
    
    3. Neither sufficient:
       - ALERT: Emergency - consider credit or Robinhood liquidation
       - DO NOT auto-approve
    """
    
    # Priority order for sourcing funds
    PRIORITY_ORDER = [
        ("chime", "Chime Savings", False),       # (account_id, label, needs_confirmation)
        ("cap1_checking", "Fun Account", True),  # Austerity mode - needs confirmation
    ]
    
    def __init__(self, bank_ecosystem: "BankEcosystem"):
        self.banks = bank_ecosystem
    
    def find_source(
        self,
        amount_needed: float,
        destination_id: str = "boa",
        reason: str = "bills"
    ) -> TransferPlan:
        """
        Find the best source to cover a shortfall.
        
        Args:
            amount_needed: How much is needed
            destination_id: Which account needs the money (default: Bill Vault)
            reason: Why the transfer is needed
        
        Returns:
            TransferPlan with recommendation
        """
        destination = self.banks.get_account(destination_id)
        dest_name = destination.name if destination else "Bill Payment"
        
        # Try each source in priority order
        for account_id, label, needs_confirm in self.PRIORITY_ORDER:
            account = self.banks.get_account(account_id)
            if not account:
                continue
            
            if account.available >= amount_needed:
                # Full coverage from this source
                urgency = "medium" if needs_confirm else "low"
                
                if needs_confirm:
                    action_label = f"⚠️ Austerity Mode: Pull ${amount_needed:.2f} from {label}"
                else:
                    action_label = f"✅ Transfer ${amount_needed:.2f} from {label}"
                
                return TransferPlan(
                    source_account_id=account_id,
                    source_name=label,
                    destination_account_id=destination_id,
                    destination_name=dest_name,
                    amount=amount_needed,
                    label=action_label,
                    approved=True,
                    needs_confirmation=needs_confirm,
                    urgency=urgency
                )
        
        # No single source sufficient — check if combined sources work
        combined = self._try_combined_sources(amount_needed, destination_id, dest_name)
        if combined:
            return combined
        
        # Emergency fallback — insufficient funds everywhere
        return TransferPlan(
            source_account_id=None,
            source_name="NONE AVAILABLE",
            destination_account_id=destination_id,
            destination_name=dest_name,
            amount=amount_needed,
            label=f"🚨 EMERGENCY: Insufficient funds. Need ${amount_needed:.2f} for {reason}. Consider credit or asset liquidation.",
            approved=False,
            needs_confirmation=True,
            urgency="critical"
        )
    
    def _try_combined_sources(
        self,
        amount_needed: float,
        destination_id: str,
        dest_name: str
    ) -> Optional[TransferPlan]:
        """
        Try combining multiple sources to cover the shortfall.
        Returns a plan if possible, None otherwise.
        """
        total_available = 0.0
        sources_used = []
        
        for account_id, label, _ in self.PRIORITY_ORDER:
            account = self.banks.get_account(account_id)
            if account and account.available > 0:
                total_available += account.available
                sources_used.append(f"{label}: ${account.available:.2f}")
        
        if total_available >= amount_needed:
            return TransferPlan(
                source_account_id="MULTIPLE",
                source_name=", ".join(sources_used),
                destination_account_id=destination_id,
                destination_name=dest_name,
                amount=amount_needed,
                label=f"⚠️ Multi-source transfer needed: {'; '.join(sources_used)}",
                approved=True,
                needs_confirmation=True,
                urgency="high"
            )
        
        return None
    
    def get_transfer_summary(self, plan: TransferPlan) -> str:
        """Generate a human-readable summary of the transfer plan."""
        lines = [
            f"💸 Transfer Plan",
            f"   Amount: ${plan.amount:.2f}",
            f"   From: {plan.source_name}",
            f"   To: {plan.destination_name}",
            f"   Status: {'✅ Ready' if plan.approved else '❌ Blocked'}",
        ]
        
        if plan.needs_confirmation:
            lines.append("   ⚠️ Requires your confirmation")
        
        if plan.urgency == "critical":
            lines.append("   🚨 URGENT: Immediate action required")
        
        return "\n".join(lines)


def get_smart_transfer(bank_ecosystem: "BankEcosystem") -> SmartTransfer:
    """Factory function for SmartTransfer."""
    return SmartTransfer(bank_ecosystem)
