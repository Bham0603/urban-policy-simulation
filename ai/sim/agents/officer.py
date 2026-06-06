from __future__ import annotations

from dataclasses import dataclass, field

from sim.agents.stall_owner import StallOwner

NodeID = int


@dataclass
class EnforcementOfficer:
    """Municipal authority officer enforcing street vendor regulations.

    Patrols nodes, evicts street vendors, issues fines, and forces relocation.
    """

    id: int
    current_location: NodeID
    patrol_nodes: list[NodeID] = field(default_factory=list)
    patrol_idx: int = 0

    def advance_patrol(self) -> NodeID:
        """Move to the next node in the patrol path."""
        if not self.patrol_nodes:
            return self.current_location
        self.patrol_idx = (self.patrol_idx + 1) % len(self.patrol_nodes)
        self.current_location = self.patrol_nodes[self.patrol_idx]
        return self.current_location

    def conduct_patrol(self, stalls: list[StallOwner]) -> list[int]:
        """Inspect the current location and evict any present street stalls.

        Evicted vendors are fined ₹100, frustration increases by 2.0,
        and they are marked for immediate relocation.

        Returns:
            list of evicted stall IDs.
        """
        evicted_ids: list[int] = []
        for stall in stalls:
            if stall.current_location == self.current_location and not stall.is_bankrupt:
                # Evict and fine the vendor
                stall.pay_fine(100.0)
                stall.retail_memory.frustration = min(5.0, stall.retail_memory.frustration + 2.0)
                # Force relocation flag on next check
                stall.retail_memory.frustration = max(2.5, stall.retail_memory.frustration)
                evicted_ids.append(stall.id)
        return evicted_ids
