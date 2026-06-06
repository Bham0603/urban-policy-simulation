from __future__ import annotations

from dataclasses import dataclass

NodeID = int


@dataclass
class WholesaleSupplier:
    """Represents a wholesale market supplier.

    Roadside vendors and formal stores must purchase bulk inventory from here.
    """

    id: int
    location_node: NodeID
    inventory: float = 1.0
    base_wholesale_price: float = 20.0

    def get_wholesale_price(self) -> float:
        """Wholesale price remains stable under weather shifts (rain does not hike price)."""
        return self.base_wholesale_price

    def sell_stock(self, buyer_cash: float, quantity: float = 1.0) -> tuple[float, float]:
        """Sell bulk stock to a vendor or store manager.

        Returns:
            tuple of (cost_charged, quantity_sold)
        """
        price_per_unit = self.get_wholesale_price()
        max_qty = min(quantity, self.inventory)
        total_cost = max_qty * price_per_unit

        if total_cost > buyer_cash:
            # Buyer can only purchase what their cash allows
            max_qty = buyer_cash / price_per_unit
            total_cost = max_qty * price_per_unit

        self.inventory = max(0.0, self.inventory - max_qty)
        return total_cost, max_qty
