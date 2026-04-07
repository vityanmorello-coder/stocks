"""
risk.py — Risk management and position sizing.

Handles:
- Position sizing for small accounts (Kelly / fixed-fraction)
- Stop loss / take profit price calculation
- Daily loss limit enforcement
- Trade feasibility check (can we afford even 1 share?)
"""

import math
from dataclasses import dataclass, field
from typing import Optional
from config import Config


@dataclass
class Position:
    """Represents an open paper trade."""
    ticker: str
    direction: int          # +1 long, -1 short (not implemented for ETF)
    entry_price: float
    shares: float           # fractional shares allowed in paper mode
    stop_loss: float
    take_profit: float
    entry_capital_usd: float
    strategy: str
    entry_time: Optional[str] = None

    @property
    def current_pnl(self) -> float:
        """Unrealised P&L — requires current price update."""
        return 0.0  # updated externally

    def is_stopped(self, current_price: float) -> bool:
        if self.direction == 1:
            return current_price <= self.stop_loss
        return current_price >= self.stop_loss

    def is_target_hit(self, current_price: float) -> bool:
        if self.direction == 1:
            return current_price >= self.take_profit
        return current_price <= self.take_profit


class RiskManager:
    """
    Risk manager for a small EUR account trading US ETFs.

    Key constraints:
    - €50 starting capital (~$54 USD at 1.09)
    - SPY trades ~$550/share → can't buy whole shares, use fractional
    - Daily loss limit prevents blowing the account on a bad day
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.daily_loss_usd = 0.0
        self.trades_today = 0
        self._halted = False   # True if daily loss limit hit

    # ── Position Sizing ────────────────────────────────────────────────────

    def position_size(
        self,
        capital_usd: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> float:
        """
        Fixed-fractional position sizing.

        Risk per trade = capital × stop_loss_pct
        Shares = risk_amount / (entry - stop)

        Caps at max_position_pct of capital.
        Allows fractional shares (paper trading).
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return 0.0

        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share < 0.01:
            risk_per_share = entry_price * self.cfg.stop_loss_pct

        risk_amount = capital_usd * self.cfg.stop_loss_pct
        shares = risk_amount / risk_per_share

        # Cap: don't deploy more than max_position_pct of capital
        max_shares = (capital_usd * self.cfg.max_position_pct) / entry_price
        shares = min(shares, max_shares)

        return round(max(shares, 0.0), 4)

    # ── Stop / Target Prices ───────────────────────────────────────────────

    def stop_loss_price(self, entry: float, direction: int = 1) -> float:
        """Calculate stop loss price from entry."""
        if direction == 1:   # long
            return round(entry * (1 - self.cfg.stop_loss_pct), 2)
        return round(entry * (1 + self.cfg.stop_loss_pct), 2)

    def take_profit_price(self, entry: float, direction: int = 1) -> float:
        """Calculate take profit price from entry."""
        if direction == 1:
            return round(entry * (1 + self.cfg.take_profit_pct), 2)
        return round(entry * (1 - self.cfg.take_profit_pct), 2)

    def atr_stop(self, entry: float, atr_value: float, direction: int = 1) -> float:
        """ATR-based stop for momentum strategy."""
        offset = atr_value * self.cfg.momentum_atr_mult
        if direction == 1:
            return round(entry - offset, 2)
        return round(entry + offset, 2)

    # ── Daily Loss Limit ───────────────────────────────────────────────────

    def record_loss(self, loss_usd: float) -> bool:
        """
        Record a realised loss. Returns True if daily limit is now breached.
        loss_usd should be a positive number representing money lost.
        """
        if loss_usd > 0:
            self.daily_loss_usd += loss_usd
        if self.daily_loss_usd >= self.cfg.max_daily_loss_usd:
            self._halted = True
        return self._halted

    def record_pnl(self, pnl_usd: float):
        """Record any P&L (positive = profit, negative = loss)."""
        if pnl_usd < 0:
            self.record_loss(-pnl_usd)

    def is_halted(self) -> bool:
        return self._halted

    def reset_daily(self):
        """Call at start of each trading day."""
        self.daily_loss_usd = 0.0
        self.trades_today = 0
        self._halted = False

    # ── Trade Feasibility ──────────────────────────────────────────────────

    def can_trade(self, capital_usd: float, price: float) -> bool:
        """
        Check if we can open any position at all.
        With fractional shares, min trade = $1 notional.
        """
        if self._halted:
            return False
        min_position_usd = 1.0
        available = capital_usd * self.cfg.max_position_pct
        return available >= min_position_usd

    def apply_slippage(self, price: float, direction: int = 1) -> float:
        """Adjust fill price for slippage."""
        if direction == 1:  # buying — pay more
            return round(price * (1 + self.cfg.slippage_pct), 4)
        return round(price * (1 - self.cfg.slippage_pct), 4)

    # ── Summary ────────────────────────────────────────────────────────────

    def risk_summary(self, capital_usd: float) -> dict:
        remaining_risk = max(
            0, self.cfg.max_daily_loss_usd - self.daily_loss_usd
        )
        return {
            "daily_loss_usd": round(self.daily_loss_usd, 2),
            "daily_limit_usd": round(self.cfg.max_daily_loss_usd, 2),
            "remaining_risk_usd": round(remaining_risk, 2),
            "halted": self._halted,
            "trades_today": self.trades_today,
            "stop_loss_pct": f"{self.cfg.stop_loss_pct * 100:.1f}%",
            "take_profit_pct": f"{self.cfg.take_profit_pct * 100:.1f}%",
        }
