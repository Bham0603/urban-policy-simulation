from __future__ import annotations

from dataclasses import dataclass

@dataclass
class DrainageWorker:
    """Drainage worker agent representing municipal maintenance crews.

    Dispatched to flooded or waterlogged road nodes to clear water and restore traffic flow.
    """

    id: int
    current_location: int
    is_busy: bool = False
    clearing_power: float = 0.2  # Reduces flood level by 0.2 per tick

    def dispatch_to(self, node_id: int) -> int:
        """Dispatch crew to a specific node."""
        self.current_location = node_id
        self.is_busy = True
        return self.current_location

    def work_tick(self, flood_level: float) -> float:
        """Perform a tick of work draining water. Returns new flood level."""
        new_flood = max(0.0, flood_level - self.clearing_power)
        if new_flood <= 0.0:
            self.is_busy = False
        return new_flood
