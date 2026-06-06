from __future__ import annotations

from dataclasses import dataclass

@dataclass
class TrafficPolice:
    """Traffic police agent representing traffic management authorities.

    Stations at congested intersections to mitigate road travel delays.
    """

    id: int
    current_location: int
    efficiency: float = 0.3  # Reduces delay at node by 30%

    def clear_congestion(self, base_delay: float) -> float:
        """Clear traffic congestion delay at their station location."""
        return base_delay * (1.0 - self.efficiency)

    def patrol_to(self, node_id: int) -> int:
        """Move to patrol a new node/intersection."""
        self.current_location = node_id
        return self.current_location
