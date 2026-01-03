"""
Finance Sentinel — Background Daemon
=====================================
Runs every 15 minutes to monitor the Five-Bank Ecosystem.

Monitors:
1. Payday Router (Chase) — Detect deposits, propose splits
2. Bill Vault Protection (BoA) — Alert if low, trigger Smart Transfer
3. Velocity Tracker (Cap1 Checking) — Calculate burn rate
4. Subscription Sentinel (Cap1 Credit) — Monitor for price hikes
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable, Awaitable

from .bank_ecosystem import BankEcosystem, get_bank_ecosystem
from .smart_transfer import SmartTransfer

logger = logging.getLogger("athena.finance.sentinel")


class FinanceSentinel:
    """
    Background daemon for autonomous financial monitoring.
    
    Usage:
        sentinel = FinanceSentinel()
        sentinel.set_alert_callback(send_telegram_message)
        await sentinel.run_check_loop()
    """
    
    CHECK_INTERVAL = 15 * 60  # 15 minutes in seconds
    PAYCHECK_THRESHOLD = 1000.0  # Deposits above this trigger payday logic
    BURN_RATE_WARNING = 15.0  # Daily budget below this triggers alert
    
    def __init__(
        self,
        bank_ecosystem: Optional[BankEcosystem] = None,
        days_until_payday: int = 14
    ):
        self.banks = bank_ecosystem or get_bank_ecosystem()
        self.days_until_payday = days_until_payday
        self._alert_callback: Optional[Callable[[str], Awaitable[None]]] = None
        self._running = False
    
    def set_alert_callback(self, callback: Callable[[str], Awaitable[None]]):
        """Set the async function to call when sending alerts (e.g., Telegram)."""
        self._alert_callback = callback
    
    async def send_alert(self, message: str):
        """Send an alert through the configured callback."""
        logger.info(f"Alert: {message}")
        if self._alert_callback:
            try:
                await self._alert_callback(message)
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
    
    async def run_check_loop(self):
        """
        Main heartbeat loop. Runs indefinitely.
        Call this as a background task.
        """
        self._running = True
        logger.info("Finance Sentinel started")
        
        while self._running:
            try:
                await self.run_all_checks()
            except Exception as e:
                logger.error(f"Sentinel check failed: {e}")
            
            await asyncio.sleep(self.CHECK_INTERVAL)
    
    def stop(self):
        """Stop the sentinel loop."""
        self._running = False
        logger.info("Finance Sentinel stopped")
    
    async def run_all_checks(self):
        """Run all monitoring checks once."""
        logger.info(f"Running financial checks at {datetime.now().isoformat()}")
        
        await self.check_payday_router()
        await self.check_bill_vault_protection()
        await self.check_velocity_tracker()
        await self.check_subscription_sentinel()
    
    # =========================================================================
    # CHECK FUNCTIONS
    # =========================================================================
    
    async def check_payday_router(self):
        """
        Chase Hub: Detect deposits > $1000, propose splits.
        """
        chase = self.banks.get_account("chase")
        if not chase:
            return
        
        deposits = self.banks.get_recent_deposits("chase", hours=24)
        
        for deposit in deposits:
            if deposit.amount >= self.PAYCHECK_THRESHOLD:
                split = self.banks.calculate_payday_split(deposit.amount)
                
                await self.send_alert(
                    f"💰 Paycheck Detected!\n"
                    f"Amount: ${deposit.amount:.2f}\n"
                    f"Source: {deposit.source}\n\n"
                    f"📊 Proposed Split:\n"
                    f"  • Bills (BoA): ${split['bills']:.2f}\n"
                    f"  • Fun (Cap1): ${split['fun']:.2f}\n"
                    f"  • Savings (Chime): ${split['savings']:.2f}"
                )
    
    async def check_bill_vault_protection(self):
        """
        BoA: If balance < upcoming bills, trigger Smart Transfer suggestion.
        """
        boa = self.banks.get_account("boa")
        if not boa:
            return
        
        upcoming_bills = self.banks.get_upcoming_bills(days=7)
        
        if boa.available < upcoming_bills:
            shortfall = upcoming_bills - boa.available
            
            # Get Smart Transfer recommendation
            transfer = SmartTransfer(self.banks)
            plan = transfer.find_source(shortfall, destination_id="boa", reason="upcoming bills")
            
            await self.send_alert(
                f"⚠️ Bill Vault Running Low!\n"
                f"Balance: ${boa.available:.2f}\n"
                f"Upcoming Bills (7 days): ${upcoming_bills:.2f}\n"
                f"Shortfall: ${shortfall:.2f}\n\n"
                f"{plan.label}"
            )
    
    async def check_velocity_tracker(self):
        """
        Capital One Checking: Calculate daily burn rate.
        Alert if burning too fast.
        """
        fun = self.banks.get_account("cap1_checking")
        if not fun:
            return
        
        daily_budget = self.banks.get_velocity("cap1_checking", self.days_until_payday)
        
        if daily_budget < self.BURN_RATE_WARNING:
            await self.send_alert(
                f"🔥 Burn Rate Alert!\n"
                f"Fun Account Balance: ${fun.available:.2f}\n"
                f"Days Until Payday: {self.days_until_payday}\n"
                f"Daily Budget: ${daily_budget:.2f}/day\n\n"
                f"⚠️ Consider reducing discretionary spending."
            )
    
    async def check_subscription_sentinel(self):
        """
        Capital One Credit: Monitor for subscription price hikes.
        Compares current month charges against historical.
        """
        subs = self.banks.get_account("cap1_credit")
        if not subs:
            return
        
        # TODO: Implement subscription tracking
        # This would compare charges against a stored baseline
        # and alert on significant increases
        pass
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def set_days_until_payday(self, days: int):
        """Update days until next payday (for velocity calculations)."""
        self.days_until_payday = days
    
    async def manual_check(self) -> str:
        """Run a manual check and return summary (for CLI use)."""
        summary_lines = ["📊 Finance Sentinel Report", ""]
        
        # Liquidity
        liquid = self.banks.get_total_liquid()
        summary_lines.append(f"💵 Total Liquid: ${liquid:.2f}")
        
        # Upcoming bills
        bills = self.banks.get_upcoming_bills(7)
        summary_lines.append(f"📋 Bills (7 days): ${bills:.2f}")
        
        # Fun account velocity
        daily = self.banks.get_velocity("cap1_checking", self.days_until_payday)
        summary_lines.append(f"🔥 Daily Budget: ${daily:.2f}/day")
        
        # Safe to spend
        sts = self.banks.safe_to_spend(100)
        summary_lines.append(f"✅ Available to Spend: ${sts.available:.2f}")
        summary_lines.append(f"⚠️ Risk Level: {sts.risk_level}")
        
        return "\n".join(summary_lines)


# =============================================================================
# FACTORY
# =============================================================================

_sentinel_instance: Optional[FinanceSentinel] = None


def get_finance_sentinel() -> FinanceSentinel:
    """Get or create the Finance Sentinel singleton."""
    global _sentinel_instance
    if _sentinel_instance is None:
        _sentinel_instance = FinanceSentinel()
    return _sentinel_instance
