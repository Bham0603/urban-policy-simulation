from __future__ import annotations

import numpy as np
import pytest

from sim.agents import (
    Agent,
    FoodStallOwner,
    StoreManager,
    WholesaleSupplier,
    EnforcementOfficer,
    DeliveryAgent,
    ShopAlternative,
    ShopChoiceModel,
    ShopType,
    ShoppingNeed,
    Occupation,
)
from sim.agents.schedule import Activity, ActivitySchedule, ActivityType


# ------------------------------------------------------------------ #
# 1. Rain level increases restocking travel time but keeps prices stable
# ------------------------------------------------------------------ #
def test_supplier_restock_rain_delays() -> None:
    supplier = WholesaleSupplier(id=1, location_node=100, base_wholesale_price=25.0)
    stall = FoodStallOwner(id=2, home_node=0, current_location=10, cash_balance=500.0, inventory=0.5)

    # Price should be base wholesale price
    assert supplier.get_wholesale_price() == 25.0

    # Restock in dry conditions (rain = 0.0)
    dry_time = stall.restock_from_supplier(supplier, rain_intensity=0.0)
    assert dry_time == 30.0  # base restock time is 30 mins
    assert stall.inventory > 0.5
    assert stall.cash_balance < 500.0

    # Reset vendor inventory and cash for wet test
    stall.inventory = 0.5
    stall.cash_balance = 500.0
    supplier.inventory = 1.0  # reset supplier inventory

    # Restock in heavy storm (rain = 1.0)
    wet_time = stall.restock_from_supplier(supplier, rain_intensity=1.0)
    assert wet_time == 60.0  # 100% time increase under rain
    # Pricing remains stable: charged cost should be identical
    assert supplier.get_wholesale_price() == 25.0


# ------------------------------------------------------------------ #
# 2. Busy shopper chooses delivery app over physical store
# ------------------------------------------------------------------ #
def test_busy_shopper_prefers_delivery() -> None:
    model = ShopChoiceModel(rng=np.random.default_rng(42))

    # Busy shopper has multiple destinations in their schedule (Home -> Work -> Leisure -> Home)
    busy_shopper = Agent(
        id=10,
        home_node=0,
        work_node=5,
        income_bracket=4,
        age=30,
        household_id=1,
        schedule=ActivitySchedule(
            activities=[
                Activity(ActivityType.HOME, 0, 0, 0),
                Activity(ActivityType.WORK, 5, 540, 480),
                Activity(ActivityType.RECREATION, 8, 1020, 120),
            ]
        ),
        shopping_needs=[ShoppingNeed("food", 0.8)],
    )
    assert busy_shopper.is_busy() is True

    # Relaxed shopper has a simple schedule (Home -> Home)
    relaxed_shopper = Agent(
        id=11,
        home_node=0,
        work_node=None,
        income_bracket=4,
        age=30,
        household_id=2,
        schedule=ActivitySchedule(
            activities=[
                Activity(ActivityType.HOME, 0, 0, 0),
            ]
        ),
        shopping_needs=[ShoppingNeed("food", 0.8)],
    )
    assert relaxed_shopper.is_busy() is False

    alts = [
        # Physical store: needs travel (distance and travel time penalty)
        ShopAlternative(
            shop_id=100,
            shop_type=ShopType.FORMAL_STORE,
            distance_km=1.0,
            travel_time_min=5.0,
            price_level=0.5,
            product_match=0.9,
        ),
        # Delivery app: zero travel for the shopper but significantly more expensive
        ShopAlternative(
            shop_id=101,
            shop_type=ShopType.DELIVERY,
            distance_km=0.0,
            travel_time_min=0.0,
            price_level=2.5,  # delivery fee markup
            product_match=0.9,
        ),
    ]

    # Busy shopper should choose DELIVERY to save time
    busy_choice = model.choose(busy_shopper, alts, stochastic=False)
    assert busy_choice.shop_type == ShopType.DELIVERY

    # Relaxed shopper has plenty of time, so they commute physically to save cash
    relaxed_choice = model.choose(relaxed_shopper, alts, stochastic=False)
    assert relaxed_choice.shop_type == ShopType.FORMAL_STORE


# ------------------------------------------------------------------ #
# 3. Rain triggers a surge delivery pricing hike
# ------------------------------------------------------------------ #
def test_delivery_rain_surge_hike() -> None:
    # Under dry conditions (rain = 0.0)
    dry_fee = DeliveryAgent.get_delivery_fee(base_fee=40.0, rain_intensity=0.0)
    assert dry_fee == 40.0

    # Under heavy rain (rain = 1.0)
    wet_fee = DeliveryAgent.get_delivery_fee(base_fee=40.0, rain_intensity=1.0)
    assert wet_fee == 40.0 * 2.5  # 150% surcharge -> 100.0


# ------------------------------------------------------------------ #
# 4. Enforcement officer evicts street vendors and issues fines
# ------------------------------------------------------------------ #
def test_officer_evictions() -> None:
    officer = EnforcementOfficer(id=50, current_location=15, patrol_nodes=[10, 15, 20])
    
    stall_a = FoodStallOwner(id=1, home_node=0, current_location=10, cash_balance=150.0)
    stall_b = FoodStallOwner(id=2, home_node=0, current_location=15, cash_balance=150.0)

    # 1. Inspect current node (Node 15)
    evicted_ids = officer.conduct_patrol([stall_a, stall_b])
    assert evicted_ids == [2], "Only Stall B at Node 15 should be evicted"
    assert stall_b.cash_balance == 50.0, "Eviction fine should deduct ₹100"
    assert stall_b.retail_memory.frustration >= 2.5, "Relocation frustration should be primed"

    # 2. Bankrupt fine eviction
    evicted_ids_2 = officer.conduct_patrol([stall_b])
    assert evicted_ids_2 == [2]
    assert stall_b.is_bankrupt is True, "Fine dropping cash to <= 0 should trigger bankruptcy"
    assert stall_b.occupation == Occupation.UNEMPLOYED

    # 3. Bankrupt vendor is ignored during patrols
    evicted_ids_3 = officer.conduct_patrol([stall_b])
    assert evicted_ids_3 == [], "Bankrupt vendors are not evicted further"
