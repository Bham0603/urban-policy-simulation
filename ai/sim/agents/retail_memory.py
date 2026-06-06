"""Retail-specific memory for stall owners and store managers.

Tracks sales outcomes over a rolling window and drives location-change
decisions via a frustration metric, mirroring the commute-frustration
pattern in ``memory.py``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

NodeID = int


@dataclass
class SalesOutcome:
    """One day's sales result at a given location."""

    revenue: float
    customers_served: int
    foot_traffic: int
    location_node: NodeID


@dataclass
class RetailMemory:
    """Per-agent rolling memory of recent sales outcomes.

    Frustration mechanics:
    - Increases by 1.0 when daily revenue drops ≥30 % below the rolling average.
    - Cools down by 0.3 on a normal/good day.
    - Capped at [0.0, 5.0].
    """

    window: int = 7
    sales_history: deque[SalesOutcome] = field(
        default_factory=lambda: deque(maxlen=7),
    )
    frustration: float = 0.0

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #

    def record_sales(self, outcome: SalesOutcome, ignore_frustration: bool = False) -> None:
        """Append a daily sales outcome and update frustration.

        If ignore_frustration is True, rolling sales are logged but location-based
        frustration is not penalized (e.g. when out of stock / idle).
        """
        old_avg = self.avg_revenue()

        self.sales_history.append(outcome)

        if ignore_frustration:
            # Out of stock or idle time: do not penalise location frustration!
            return

        # If vendor makes profit (revenue > 0) -> decrease frustration by 0.25!
        if outcome.revenue > 0.0:
            self.frustration = max(0.0, self.frustration - 0.25)
        else:
            # Zero revenue day (not ignored) -> frustration spikes by 1.0
            self.frustration = min(5.0, self.frustration + 1.0)

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def avg_revenue(self) -> float | None:
        """Rolling average revenue, or None if no history yet."""
        if not self.sales_history:
            return None
        return sum(o.revenue for o in self.sales_history) / len(self.sales_history)

    def avg_foot_traffic(self) -> float | None:
        """Rolling average foot traffic, or None if no history yet."""
        if not self.sales_history:
            return None
        return sum(o.foot_traffic for o in self.sales_history) / len(self.sales_history)

    def should_relocate(self, threshold: float = 2.0) -> bool:
        """Return True when frustration exceeds the relocation threshold."""
        return self.frustration >= threshold

    # ------------------------------------------------------------------ #
    # Disruption helper
    # ------------------------------------------------------------------ #

    def record_disruption(self, location_node: NodeID) -> None:
        """Record a disrupted day (zero revenue) and spike frustration.

        Called when weather, police clearance, or other events shut down the stall.
        """
        self.sales_history.append(
            SalesOutcome(
                revenue=0.0,
                customers_served=0,
                foot_traffic=0,
                location_node=location_node,
            )
        )
        self.frustration = min(5.0, self.frustration + 1.5)
