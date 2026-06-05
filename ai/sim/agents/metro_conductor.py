from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class MetroConductor:
    """Represents a metro train conductor operating along metro line stations.

    Maintains fixed travel times (unaffected by road traffic), but experiences high passenger load during rain.
    """

    id: int
    line_name: str
    stations: list[dict] = field(default_factory=list)
    current_station_idx: int = 0
    direction: int = 1  # 1 for forward, -1 for reverse
    passenger_count: int = 0
    capacity: int = 300

    def get_comfort_score(self) -> float:
        """Comfort drops as the metro crowds up."""
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

    def advance_station(self) -> float:
        """Move to the next station in the direction of travel.

        Metro is on a separate track and has fixed commute times (e.g. 3 mins).
        """
        if not self.stations:
            return 0.0
        
        next_idx = self.current_station_idx + self.direction
        if next_idx >= len(self.stations) or next_idx < 0:
            self.direction *= -1
            next_idx = self.current_station_idx + self.direction
            
        self.current_station_idx = next_idx
        return 3.0  # Constant travel time
