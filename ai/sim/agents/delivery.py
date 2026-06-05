from __future__ import annotations

from dataclasses import dataclass

NodeID = int


@dataclass
class DeliveryAgent:
    """Represents a delivery gig worker (Delivery Agent / Delivery Man).

    Owns a two-wheeler, travels from retail outlets to shopper locations,
    and earns delivery fees (which surge during rainy conditions).
    """

    id: int
    home_node: NodeID
    current_location: NodeID
    cash_balance: float = 200.0
    has_bike: bool = True
    completed_deliveries_count: int = 0
    earnings: float = 0.0

    @staticmethod
    def get_delivery_fee(base_fee: float, rain_intensity: float) -> float:
        """Dynamic delivery fee containing rain surge pricing hike."""
        if rain_intensity >= 0.5:
            # Surcharge: up to 2.5x base fee in heavy rain
            return base_fee * (1.0 + 1.5 * rain_intensity)
        return base_fee

    def deliver_order(self, fee: float, destination_node: NodeID) -> None:
        """Process delivery: earn delivery fee and update location."""
        self.earnings += fee
        self.cash_balance += fee
        self.completed_deliveries_count += 1
        self.current_location = destination_node
