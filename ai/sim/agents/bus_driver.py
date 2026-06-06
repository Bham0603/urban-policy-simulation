from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class BusDriver:
    """Represents a public transit bus driver operating along specified routes.

    Experiences travel delays under rain and congestion.
    """

    id: int
    route_id: str
    route_name: str
    stops: list[dict] = field(default_factory=list)
    current_stop_idx: int = 0
    passenger_count: int = 0
    capacity: int = 50

    def get_comfort_score(self) -> float:
        """Comfort drops as the bus crowds up."""
        if self.passenger_count == 0:
            return 1.0
        ratio = self.passenger_count / self.capacity
        return max(0.1, 1.0 - 0.9 * ratio)

    def board_passengers(self, count: int) -> int:
        """Board passengers up to capacity. Returns count boarded."""
        boarded = min(count, self.capacity - self.passenger_count)
        self.passenger_count += boarded
        return boarded

    def deboard_passengers(self, count: int) -> int:
        """Deboard passengers. Returns count deboarded."""
        deboarded = min(count, self.passenger_count)
        self.passenger_count -= deboarded
        return deboarded

    def advance_stop(self, rain_intensity: float = 0.0, road_congestion: float = 1.0) -> float:
        """Move to the next stop and return travel time in minutes."""
        if not self.stops:
            return 0.0
        self.current_stop_idx = (self.current_stop_idx + 1) % len(self.stops)
        
        # Base travel time is 5.0 minutes
        base_time = 5.0
        # Rain and road traffic multiply travel times
        delay_factor = 1.0 + 1.5 * rain_intensity + 0.5 * max(0.0, road_congestion - 1.0)
        return base_time * delay_factor
