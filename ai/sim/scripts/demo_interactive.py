"""Interactive terminal-based simulation dashboard for economic & retail agents.
Allows the user to trigger events, run dynamic loops, and view colored live status metrics.

Usage: python -m sim.scripts.demo_interactive
"""

from __future__ import annotations

import os
import sys
import time
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


from sim.agents.agent import Agent
from sim.agents.modes import Occupation
from sim.agents.retail_interaction import process_purchase
from sim.agents.retail_memory import SalesOutcome
from sim.agents.shop_choice import ShopAlternative, ShopChoiceModel, ShoppingNeed, ShopType
from sim.agents.stall_owner import FoodStallOwner, ClothesStallOwner, AccessoriesStallOwner
from sim.agents.store_agents import StoreManager, StoreStaff
from sim.agents.utility_weights import UtilityWeights
from sim.agents.supplier import WholesaleSupplier
from sim.agents.officer import EnforcementOfficer
from sim.agents.delivery import DeliveryAgent
from sim.agents.schedule import ActivitySchedule, Activity, ActivityType
from sim.agents.bus_driver import BusDriver
from sim.agents.metro_conductor import MetroConductor
from sim.agents.traffic_police import TrafficPolice
from sim.agents.drainage_worker import DrainageWorker


# ANSI terminal colors for premium styling
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_BLUE = "\033[34m"
C_MAGENTA = "\033[35m"
C_BG_DARK = "\033[40m"

def clear_screen() -> None:
    """Clear terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")

def print_header(title: str) -> None:
    """Prints a styled section header."""
    print(f"\n{C_BOLD}{C_CYAN}{'=' * 72}{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}  {title:^68}  {C_RESET}")
    print(f"{C_BOLD}{C_CYAN}{'=' * 72}{C_RESET}\n")

def make_progress_bar(val: float, max_val: float = 1.0, length: int = 15, color: str = C_GREEN) -> str:
    """Creates a beautiful ANSI colored progress bar."""
    ratio = max(0.0, min(1.0, val / max_val))
    filled_len = int(length * ratio)
    empty_len = length - filled_len
    bar = color + "█" * filled_len + C_DIM + "░" * empty_len + C_RESET
    return f"[{bar}] {color}{val:.2f}{C_RESET}"

# ====================================================================== #
# SCENARIO 1: Live Interactive Transaction Loop
# ====================================================================== #
def scenario_transaction() -> None:
    clear_screen()
    print_header("SCENARIO 1: INTERACTIVE TRANSACTION SIMULATOR")
    print(f"{C_DIM}In this scenario, you control the base transaction parameters and watch how{C_RESET}")
    print(f"{C_DIM}Asha (Low-Income) and Vikram (High-Income) choose their shopping venue.{C_RESET}\n")

    shop_model = ShopChoiceModel(rng=np.random.default_rng(42))
    
    # 1. Setup alternatives
    stalls = [
        ShopAlternative(101, ShopType.FORMAL_STORE, distance_km=1.5, travel_time_min=12, price_level=0.85, product_match=0.95),
        ShopAlternative(201, ShopType.FOOD_STALL, distance_km=1.0, travel_time_min=8, price_level=0.15, product_match=0.70),
        ShopAlternative(202, ShopType.CLOTHES_STALL, distance_km=1.2, travel_time_min=9, price_level=0.25, product_match=0.60)
    ]
    
    food_stall = FoodStallOwner(id=201, home_node=0, current_location=10, inventory=0.8)
    clothes_stall = ClothesStallOwner(id=202, home_node=0, current_location=20, inventory=0.9)

    # Pre-populate memories with standard baseline days so 0 sales triggers location frustration
    food_stall.retail_memory.record_sales(SalesOutcome(revenue=80.0, customers_served=2, foot_traffic=20, location_node=10))
    food_stall.retail_memory.record_sales(SalesOutcome(revenue=80.0, customers_served=2, foot_traffic=20, location_node=10))
    clothes_stall.retail_memory.record_sales(SalesOutcome(revenue=100.0, customers_served=2, foot_traffic=25, location_node=20))
    clothes_stall.retail_memory.record_sales(SalesOutcome(revenue=100.0, customers_served=2, foot_traffic=25, location_node=20))

    # 2. Get user input for pricing adjustments
    try:
        raw_price = input(f"{C_BOLD}Enter transaction base price in ₹ (default 50.0): {C_RESET}")
        base_price = float(raw_price) if raw_price.strip() else 50.0
    except ValueError:
        base_price = 50.0

    # Calculate dynamic price multiplier based on user input:
    # Dirt cheap threshold <= 10.0 -> M = 0.0 (no cost penalty)
    # Expensive threshold >= 150.0 -> M = 25.0 (huge cost penalty)
    if base_price <= 10.0:
        price_multiplier = 0.0
    elif base_price >= 150.0:
        price_multiplier = 25.0
    else:
        # Smooth interpolation:
        if base_price < 50.0:
            price_multiplier = (base_price - 10.0) / 40.0
        else:
            price_multiplier = 1.0 + 24.0 * (base_price - 50.0) / 100.0

    # Scale the price_level of the alternatives dynamically!
    scaled_stalls = []
    for alt in stalls:
        scaled_stalls.append(
            ShopAlternative(
                shop_id=alt.shop_id,
                shop_type=alt.shop_type,
                distance_km=alt.distance_km,
                travel_time_min=alt.travel_time_min,
                price_level=alt.price_level * price_multiplier,
                product_match=alt.product_match
            )
        )

    # 2b. Dynamic Product Category Alignment based on Agent Need
    # Asha needs food. Clothes stall product match becomes 0.0 (irrelevant to food shopping).
    asha_stalls = []
    for alt in scaled_stalls:
        match = alt.product_match
        if alt.shop_type == ShopType.CLOTHES_STALL:
            match = 0.0
        asha_stalls.append(
            ShopAlternative(
                shop_id=alt.shop_id,
                shop_type=alt.shop_type,
                distance_km=alt.distance_km,
                travel_time_min=alt.travel_time_min,
                price_level=alt.price_level,
                product_match=match
            )
        )

    # Vikram needs clothes. Food stall product match becomes 0.0 (irrelevant to clothing shopping).
    # Clothes stall is Meena, let's boost her product match to a strong 0.80 for clothes!
    vikram_stalls = []
    for alt in scaled_stalls:
        match = alt.product_match
        if alt.shop_type == ShopType.FOOD_STALL:
            match = 0.0
        elif alt.shop_type == ShopType.CLOTHES_STALL:
            match = 0.80
        vikram_stalls.append(
            ShopAlternative(
                shop_id=alt.shop_id,
                shop_type=alt.shop_type,
                distance_km=alt.distance_km,
                travel_time_min=alt.travel_time_min,
                price_level=alt.price_level,
                product_match=match
            )
        )

    print(f"\n{C_BOLD}{C_BLUE}Running transaction choice utility checks (Base Price ₹{base_price:.2f}):{C_RESET}")
    if base_price <= 10.0:
        print(f"  {C_CYAN}✦ Price Effect: Dirt Cheap (≤₹10.00). Price barriers are completely gone!{C_RESET}")
    elif base_price >= 150.0:
        print(f"  {C_RED}✦ Price Effect: Extremely Expensive (≥₹150.00). Price barriers are highly amplified!{C_RESET}")
    else:
        print(f"  {C_GREEN}✦ Price Effect: Normal pricing. Market behaves according to standard parameters.{C_RESET}")
    
    # Asha
    asha = Agent(
        id=1,
        home_node=5,
        work_node=15,
        income_bracket=1,
        age=34,
        household_id=10,
        occupation=Occupation.BLUE_COLLAR_WORKER,
        shopping_needs=[ShoppingNeed("food", 0.9)]
    )
    print(f"\n{C_BOLD}--- Asha (Low-Income Worker, Bracket 1/5) ---{C_RESET}")
    for alt in asha_stalls:
        u = shop_model.utility(asha, alt)
        print(f"  {alt.shop_type.value:15s} | Price: {alt.price_level:.2f} | Utility: {C_GREEN if u > -2 else C_RED}{u:8.4f}{C_RESET}")
    chosen_asha = shop_model.choose(asha, asha_stalls, stochastic=False)
    print(f"  ➜ {C_BOLD}{C_GREEN}Asha decides to shop at: {chosen_asha.shop_type.value}{C_RESET}")

    # Vikram
    vikram = Agent(
        id=2,
        home_node=5,
        work_node=30,
        income_bracket=5,
        age=45,
        household_id=20,
        occupation=Occupation.OFFICE_EXECUTIVE,
        shopping_needs=[ShoppingNeed("clothes", 0.6)],
        weights=UtilityWeights.for_occupation(Occupation.OFFICE_EXECUTIVE)
    )
    print(f"\n{C_BOLD}--- Vikram (High-Income Executive, Bracket 5/5) ---{C_RESET}")
    for alt in vikram_stalls:
        u = shop_model.utility(vikram, alt)
        print(f"  {alt.shop_type.value:15s} | Price: {alt.price_level:.2f} | Utility: {C_GREEN if u > -2 else C_RED}{u:8.4f}{C_RESET}")
    chosen_vikram = shop_model.choose(vikram, vikram_stalls, stochastic=False)
    print(f"  ➜ {C_BOLD}{C_GREEN}Vikram decides to shop at: {chosen_vikram.shop_type.value}{C_RESET}")

    # 3. Dynamic Purchase Processing for Asha and Vikram
    print(f"\n{C_BOLD}{C_BLUE}========================================================================{C_RESET}")
    print(f"{C_BOLD}{C_BLUE}                     PROCESSING SHOPPING TRANSACTIONS                    {C_RESET}")
    print(f"{C_BOLD}{C_BLUE}========================================================================{C_RESET}")

    purchased_food = False
    purchased_clothes = False

    for agent, name, chosen in [(asha, "Asha", chosen_asha), (vikram, "Vikram", chosen_vikram)]:
        print(f"\n{C_BOLD}Processing transaction for {name} ↔ {chosen.shop_type.value}:{C_RESET}")
        
        if chosen.shop_id == 201:
            # Food Stall (Raju)
            print(f"  Stall Inventory: {make_progress_bar(food_stall.inventory, 1.0, color=C_CYAN)}")
            res = process_purchase(agent, food_stall, base_price=base_price, foot_traffic=30)
            if res.success:
                print(f"  {C_GREEN}✔ Purchase Succeeded at Food Stall #{food_stall.id} (Raju)!{C_RESET}")
                print(f"  Revenue earned by Raju:   {C_BOLD}₹{res.stall_revenue:.2f}{C_RESET}")
                print(f"  Shopper utility gain:     {C_BOLD}{res.shopper_utility_gain:+.4f}{C_RESET}")
                print(f"  New Stall Inventory:     {make_progress_bar(food_stall.inventory, 1.0, color=C_CYAN)}")
                print(f"  Raju's rolling frustration: {make_progress_bar(food_stall.retail_memory.frustration, 5.0, color=C_YELLOW)}")
                purchased_food = True
            else:
                print(f"  {C_RED}❌ Purchase Failed: {res.reason}{C_RESET}")
        
        elif chosen.shop_id == 202:
            # Clothes Stall (Meena)
            print(f"  Stall Inventory: {make_progress_bar(clothes_stall.inventory, 1.0, color=C_CYAN)}")
            res = process_purchase(agent, clothes_stall, base_price=base_price, foot_traffic=30)
            if res.success:
                print(f"  {C_GREEN}✔ Purchase Succeeded at Clothes Stall #{clothes_stall.id} (Meena)!{C_RESET}")
                print(f"  Revenue earned by Meena:  {C_BOLD}₹{res.stall_revenue:.2f}{C_RESET}")
                print(f"  Shopper utility gain:     {C_BOLD}{res.shopper_utility_gain:+.4f}{C_RESET}")
                print(f"  New Stall Inventory:     {make_progress_bar(clothes_stall.inventory, 1.0, color=C_CYAN)}")
                print(f"  Meena's rolling frustration: {make_progress_bar(clothes_stall.retail_memory.frustration, 5.0, color=C_YELLOW)}")
                purchased_clothes = True
            else:
                print(f"  {C_RED}❌ Purchase Failed: {res.reason}{C_RESET}")

        elif chosen.shop_id == 101:
            # Formal Store
            # Let's calculate standard corporate checkout
            price = base_price * 1.5  # 1.5x premium markup
            cost_scale = (6 - agent.income_bracket) / 3.0
            utility_gain = 1.0 - (price / base_price) * cost_scale * 0.5
            
            print(f"  {C_GREEN}✔ Purchase Succeeded at Formal Store #101 (Premium Supermarket)!{C_RESET}")
            print(f"  Revenue earned by Corporate Retailer: {C_BOLD}₹{price:.2f}{C_RESET}")
            print(f"  Shopper utility gain:                 {C_BOLD}{utility_gain:+.4f}{C_RESET}")
            print(f"  Checkout comfort status:              {C_CYAN}Premium high-comfort scan & go.{C_RESET}")

    # 4. Show impact on vendors (Zero sales frustration)
    print(f"\n{C_BOLD}{C_RED}========================================================================{C_RESET}")
    print(f"{C_BOLD}{C_RED}                    DAILY IMPACT ON STREET VENDORS                       {C_RESET}")
    print(f"{C_BOLD}{C_RED}========================================================================{C_RESET}")

    # Process Food Stall (Raju) daily sales outcome
    if not purchased_food:
        # No one bought from Raju! Record zero sales and spike frustration
        food_stall.retail_memory.record_sales(
            SalesOutcome(revenue=0.0, customers_served=0, foot_traffic=10, location_node=food_stall.current_location)
        )
        print(f"  {C_RED}⚠ [Raju (Food Stall)]{C_RESET} Made {C_BOLD}0 sales{C_RESET} today! Shoppers went elsewhere.")
        print(f"    Raju's location frustration spikes: {make_progress_bar(food_stall.retail_memory.frustration, 5.0, color=C_RED)}")
    else:
        print(f"  {C_GREEN}✔ [Raju (Food Stall)]{C_RESET} Made successful sales today! Frustration is controlled.")
        print(f"    Raju's location frustration:        {make_progress_bar(food_stall.retail_memory.frustration, 5.0, color=C_YELLOW)}")

    # Process Clothes Stall (Meena) daily sales outcome
    if not purchased_clothes:
        # No one bought from Meena! Record zero sales and spike frustration
        clothes_stall.retail_memory.record_sales(
            SalesOutcome(revenue=0.0, customers_served=0, foot_traffic=10, location_node=clothes_stall.current_location)
        )
        print(f"  {C_RED}⚠ [Meena (Clothes Stall)]{C_RESET} Made {C_BOLD}0 sales{C_RESET} today! Shoppers went elsewhere.")
        print(f"    Meena's location frustration spikes: {make_progress_bar(clothes_stall.retail_memory.frustration, 5.0, color=C_RED)}")
    else:
        print(f"  {C_GREEN}✔ [Meena (Clothes Stall)]{C_RESET} Made successful sales today! Frustration is controlled.")
        print(f"    Meena's location frustration:        {make_progress_bar(clothes_stall.retail_memory.frustration, 5.0, color=C_YELLOW)}")

    input(f"\n{C_BOLD}{C_DIM}Press Enter to return to main menu...{C_RESET}")

# ====================================================================== #
# SCENARIO 2: Animated Stall Relocation and Inventory Decay
# ====================================================================== #
def scenario_animated_stall() -> None:
    clear_screen()
    print_header("SCENARIO 2: LIVE ANIMATED STALL LIFECYCLE")
    print(f"{C_DIM}This scenario runs a live simulation of three different stall types.{C_RESET}")
    print(f"{C_DIM}Watch their inventory decay, frustration level, and dynamic relocation in real-time!{C_RESET}\n")

    food = FoodStallOwner(id=301, home_node=0, current_location=101)
    clothes = ClothesStallOwner(id=302, home_node=0, current_location=102)
    acc = AccessoriesStallOwner(id=303, home_node=0, current_location=103)

    # Pre-populate Sunita (accessories) with good sales average so a drop triggers location frustration
    acc.retail_memory.record_sales(SalesOutcome(revenue=150.0, customers_served=3, foot_traffic=80, location_node=103))
    acc.retail_memory.record_sales(SalesOutcome(revenue=150.0, customers_served=3, foot_traffic=80, location_node=103))

    candidates = [(201, 30), (202, 140), (203, 75), (204, 50)]
    rng = np.random.default_rng(101)

    # Ask user for frames
    try:
        raw_ticks = input(f"{C_BOLD}Enter number of simulation ticks/frames to run (default 10): {C_RESET}")
        num_ticks = int(raw_ticks) if raw_ticks.strip() else 10
        if num_ticks <= 0:
            num_ticks = 10
    except ValueError:
        num_ticks = 10

    print(f"\n{C_BOLD}{C_GREEN}Starting the live animation loop ({num_ticks} frames)...{C_RESET}")
    time.sleep(0.8)

    for tick in range(1, num_ticks + 1):
        clear_screen()
        print_header(f"STALL LIFECYCLE SIMULATION - TICK {tick}/{num_ticks}")
        
        # 1. Check out-of-stock states
        food_is_out = food.inventory <= 0.05
        clothes_is_out = clothes.inventory <= 0.05
        acc_is_out = acc.inventory <= 0.05

        # Dynamic restocking action: resets to 1.0, but uses up a tick (decays do not apply)
        restocking_stalls = {}
        for stall, is_out, key in [(food, food_is_out, "food"), (clothes, clothes_is_out, "clothes"), (acc, acc_is_out, "accessories")]:
            if is_out:
                stall.restock(1.0)
                restocking_stalls[key] = True
            else:
                stall.decay_inventory()
                restocking_stalls[key] = False

        # 2. Record daily sales outcome
        food_rev = 0.0 if restocking_stalls["food"] else (10.0 if tick < (num_ticks // 2 + 1) else 150.0)
        clothes_rev = 0.0 if restocking_stalls["clothes"] else (90.0 if tick < (num_ticks // 2 + 1) else 120.0)
        acc_rev = 0.0 if restocking_stalls["accessories"] else (15.0 if tick < (num_ticks // 2 + 1) else 60.0)

        food.retail_memory.record_sales(
            SalesOutcome(revenue=food_rev, customers_served=0 if food_rev < 50 else 3, foot_traffic=10 if tick < (num_ticks // 2 + 1) else 100, location_node=food.current_location),
            ignore_frustration=restocking_stalls["food"]
        )
        clothes.retail_memory.record_sales(
            SalesOutcome(revenue=clothes_rev, customers_served=2 if clothes_rev < 100 else 3, foot_traffic=40 if tick < (num_ticks // 2 + 1) else 50, location_node=clothes.current_location),
            ignore_frustration=restocking_stalls["clothes"]
        )
        acc.retail_memory.record_sales(
            SalesOutcome(revenue=acc_rev, customers_served=0 if acc_rev < 30 else 1, foot_traffic=5 if tick < (num_ticks // 2 + 1) else 30, location_node=acc.current_location),
            ignore_frustration=restocking_stalls["accessories"]
        )

        # 3. Peer Comparison Logic (Relative Frustration Management)
        active_vendors = []
        for key, stall, rev, name in [("food", food, food_rev, "Raju (Food)"), ("clothes", clothes, clothes_rev, "Meena (Clothes)"), ("accessories", acc, acc_rev, "Sunita (Accessory)")]:
            if not restocking_stalls[key]:
                active_vendors.append((stall, rev, name))

        comparison_logs = []
        if len(active_vendors) >= 2:
            peer_avg = sum(v[1] for v in active_vendors) / len(active_vendors)
            for stall, rev, name in active_vendors:
                if rev < peer_avg * 0.6:
                    # Relative peer envy: frustration increases when neighbors do much better!
                    stall.retail_memory.frustration = min(5.0, stall.retail_memory.frustration + 0.6)
                    richest_peer = max(active_vendors, key=lambda x: x[1])
                    comparison_logs.append(f"  {C_RED}⚠ Peer Envy:{C_RESET} {name} sees neighbors thriving and feels more frustrated! (₹{rev:.0f} vs ₹{richest_peer[1]:.0f})")
                elif rev > peer_avg * 1.3:
                    # Peer confidence: pride cools down location frustration!
                    stall.retail_memory.frustration = max(0.0, stall.retail_memory.frustration - 0.4)
                    comparison_logs.append(f"  {C_GREEN}✔ Market Leader:{C_RESET} {name} is secure leading today's street sales with ₹{rev:.0f}!")

        # 4. Peer-Influenced Relocation & Clustering Action
        # Dynamic candidate scoring: vendors prefer to cluster near successful peer locations
        star_vendor = None
        if active_vendors:
            star_vendor = max(active_vendors, key=lambda x: x[1])[0]

        dynamic_candidates = list(candidates)
        clustering_node = None
        if star_vendor and star_vendor.current_location:
            star_loc = star_vendor.current_location
            new_candidates = []
            for node, ft in candidates:
                # If a candidate node is right next to the successful vendor, boost its traffic appeal!
                if abs(node - star_loc) <= 2:
                    new_candidates.append((node, ft * 2))
                    clustering_node = node
                else:
                    new_candidates.append((node, ft))
            dynamic_candidates = new_candidates

        # Check relocation (only if they weren't busy restocking this tick!)
        food_moved = food.maybe_relocate(dynamic_candidates, rng=rng) if not restocking_stalls["food"] else None
        clothes_moved = clothes.maybe_relocate(dynamic_candidates, rng=rng) if not restocking_stalls["clothes"] else None
        acc_moved = acc.maybe_relocate(dynamic_candidates, rng=rng) if not restocking_stalls["accessories"] else None

        # Print current statuses in a gorgeous table dashboard
        print(f"{C_BOLD}{'STALL VENDOR':20s} | {'LOCATION':10s} | {'INVENTORY STATUS':26s} | {'FRUSTRATION':26s} | {'STATUS':12s}{C_RESET}")
        print(f"{C_DIM}{'-' * 105}{C_RESET}")
        
        for stall, name, moved in [(food, "Raju (Food)", food_moved), (clothes, "Meena (Clothes)", clothes_moved), (acc, "Sunita (Accessory)", acc_moved)]:
            loc_str = f"Node {stall.current_location}"
            inv_bar = make_progress_bar(stall.inventory, 1.0, color=C_CYAN)
            frust_bar = make_progress_bar(stall.retail_memory.frustration, 5.0, color=C_YELLOW)
            
            if restocking_stalls[stall.stall_type.value]:
                status_str = f"{C_BOLD}{C_CYAN}⚡ RESTOCKED{C_RESET}"
            elif moved:
                status_str = f"{C_BOLD}{C_MAGENTA}✈ MOVED{C_RESET}"
            elif stall.retail_memory.frustration > 2.0:
                status_str = f"{C_RED}⚠ FRUSTRATED{C_RESET}"
            else:
                status_str = f"{C_GREEN}✔ STABLE{C_RESET}"

            print(f"{name:20s} | {loc_str:10s} | {inv_bar:26s} | {frust_bar:26s} | {status_str:12s}")

        # Render peer comparison live commentary
        if comparison_logs:
            print(f"\n{C_BOLD}Marketplace Live Commentary:{C_RESET}")
            for log in comparison_logs:
                print(log)

        if clustering_node and (food_moved or acc_moved):
            print(f"  {C_CYAN}✦ Agglomeration Economy:{C_RESET} Relocating vendors targeted Node {clustering_node} to cluster near successful peers!")

        print(f"\n{C_DIM}Candidate nodes (with clustering boosts): {[(f'Node {n}', f'traffic={t}') for n, t in dynamic_candidates]}{C_RESET}")
        time.sleep(1.2)

    print(f"\n{C_BOLD}{C_GREEN}Animation finished successfully!{C_RESET}")
    input(f"\n{C_BOLD}{C_DIM}Press Enter to return to main menu...{C_RESET}")

# ====================================================================== #
# SCENARIO 3: Weather Disruptions & Store Staff Tardiness Dashboard
# ====================================================================== #
def scenario_weather_disruption() -> None:
    clear_screen()
    print_header("SCENARIO 3: WEATHER DISRUPTIONS & STORE OPERATIONS")
    print(f"{C_DIM}This dashboard simulates store managers, staff shifts, and staff lateness frustration{C_RESET}")
    print(f"{C_DIM}as weather and road traffic conditions change.{C_RESET}\n")

    manager = StoreManager(id=400, store_node=25, staff_ids=[401, 402])
    ankit = StoreStaff(id=401, home_node=5, store_node=25)
    deepa = StoreStaff(id=402, home_node=12, store_node=25)

    manager.assign_shifts([ankit, deepa])
    shift_start = ankit.assigned_shift.start_time_min # 9:00 AM (540 mins)

    print(f"{C_BOLD}Formal Store Node: {manager.store_node}{C_RESET}")
    print(f"Shift Assigned: 09:00 AM – 05:00 PM (Start tick: 540)")
    
    # Run a weather loop
    weather_states = [
        ("Clear Sky", 0.0, 535), # 8:55 AM (early)
        ("Clear Sky", 0.0, 538), # 8:58 AM (on-time)
        ("Light Rain", 0.3, 545), # 9:05 AM (slightly late)
        ("Heavy Storm", 0.8, 560), # 9:20 AM (very late)
        ("Heavy Storm", 1.0, 580)  # 9:40 AM (extremely late)
    ]

    for i, (weather_name, intensity, arrival) in enumerate(weather_states, 1):
        ankit.record_arrival(arrival)
        arr_str = f"{arrival // 60:02d}:{arrival % 60:02d} AM"
        
        print(f"\n{C_BOLD}Day {i} Weather: {weather_name} (Intensity: {intensity}){C_RESET}")
        
        # Color codes based on lateness
        if arrival <= shift_start:
            status = f"{C_GREEN}ON TIME{C_RESET}"
        else:
            status = f"{C_RED}LATE{C_RESET}"

        print(f"  Staff Ankit arrival: {arr_str} -> status: {status}")
        print(f"  Ankit's Tardiness Frustration: {make_progress_bar(ankit.lateness_frustration, 5.0, color=C_RED)}")

    print(f"\n{C_BOLD}{C_BLUE}Impact on Formal Store operations:{C_RESET}")
    if ankit.lateness_frustration > 2.5:
        print(f"  {C_RED}⚠ WARNING: Store operation speed is reduced due to high staff frustration levels.{C_RESET}")
    else:
        print(f"  {C_GREEN}✔ Store operating at peak performance capacity.{C_RESET}")

    input(f"\n{C_BOLD}{C_DIM}Press Enter to return to main menu...{C_RESET}")

# ====================================================================== #
# SCENARIO 4: Wholesale Restocking Delays (Dry vs. Rain Conditions)
# ====================================================================== #
def scenario_restock_delays() -> None:
    clear_screen()
    print_header("SCENARIO 4: WHOLESALE RESTOCKING DELAYS (DRY VS. RAIN)")
    print(f"{C_DIM}This scenario demonstrates Raju (Food Stall Owner) restocking from a wholesale{C_RESET}")
    print(f"{C_DIM}supplier under different weather conditions.{C_RESET}")
    print(f"{C_DIM}Rain does NOT change the wholesale price, but doubles travel time due to waterlogging.{C_RESET}\n")

    # Initialize supplier and stall owner
    supplier = WholesaleSupplier(id=501, location_node=100, base_wholesale_price=20.0)
    raju = FoodStallOwner(id=301, home_node=0, current_location=10, cash_balance=500.0, inventory=0.3)

    print(f"{C_BOLD}Initial State:{C_RESET}")
    print(f"  Raju's Cash Balance: ₹{raju.cash_balance:.2f}")
    print(f"  Raju's Inventory:    {make_progress_bar(raju.inventory, 1.0, color=C_CYAN)}")
    print(f"  Supplier Wholesale Unit Price: ₹{supplier.get_wholesale_price():.2f}")
    print(f"  Supplier Stock:      {make_progress_bar(supplier.inventory, 1.0, color=C_GREEN)}")

    # 1. Restock in Dry Conditions
    print(f"\n{C_BOLD}{C_BLUE}--- Part 1: Restocking in Dry Conditions (Rain = 0.0) ---{C_RESET}")
    time.sleep(0.5)
    print("Raju is traveling to the wholesale supplier...")
    
    # Progress animation for dry travel
    bar_length = 20
    for i in range(1, bar_length + 1):
        ratio = i / bar_length
        filled = "█" * i
        empty = "░" * (bar_length - i)
        print(f"\r  Travel: [{C_GREEN}{filled}{C_DIM}{empty}{C_RESET}] {int(ratio*100)}% (Est. 30m)", end="", flush=True)
        time.sleep(0.04)
    print()

    # Perform restock
    dry_time = raju.restock_from_supplier(supplier, rain_intensity=0.0)
    
    print(f"  {C_GREEN}✔ Restock Completed!{C_RESET}")
    print(f"  Travel Time:         {C_BOLD}{dry_time:.1f} minutes{C_RESET}")
    print(f"  Raju's New Cash:     ₹{raju.cash_balance:.2f}")
    print(f"  Raju's New Inventory:{make_progress_bar(raju.inventory, 1.0, color=C_CYAN)}")
    print(f"  Supplier Stock left: {make_progress_bar(supplier.inventory, 1.0, color=C_GREEN)}")

    # Reset Raju and Supplier for Wet Conditions
    raju.inventory = 0.3
    raju.cash_balance = 500.0
    supplier.inventory = 1.0

    # 2. Restock in Wet Conditions
    print(f"\n{C_BOLD}{C_YELLOW}--- Part 2: Restocking in Monsoon/Rainy Conditions (Rain = 1.0) ---{C_RESET}")
    time.sleep(0.5)
    print("Raju is traveling to the wholesale supplier in heavy rain...")
    
    # Progress animation for wet travel (slower)
    for i in range(1, bar_length + 1):
        ratio = i / bar_length
        filled = "█" * i
        empty = "░" * (bar_length - i)
        print(f"\r  Travel (Rain Delay): [{C_RED}{filled}{C_DIM}{empty}{C_RESET}] {int(ratio*100)}% (Est. 60m)", end="", flush=True)
        time.sleep(0.07)
    print()

    # Perform restock
    wet_time = raju.restock_from_supplier(supplier, rain_intensity=1.0)

    print(f"  {C_GREEN}✔ Restock Completed!{C_RESET}")
    print(f"  Travel Time:         {C_BOLD}{wet_time:.1f} minutes{C_RESET} ({C_RED}100% delay applied{C_RESET})")
    print(f"  Wholesale price paid:₹{supplier.get_wholesale_price():.2f} per unit ({C_GREEN}Unchanged!{C_RESET})")
    print(f"  Raju's New Cash:     ₹{raju.cash_balance:.2f} ({C_GREEN}Same cost charged!{C_RESET})")
    print(f"  Raju's New Inventory:{make_progress_bar(raju.inventory, 1.0, color=C_CYAN)}")
    print(f"  Supplier Stock left: {make_progress_bar(supplier.inventory, 1.0, color=C_GREEN)}")

    input(f"\n{C_BOLD}{C_DIM}Press Enter to return to main menu...{C_RESET}")

# ====================================================================== #
# SCENARIO 5: Delivery App Choice & Monsoon Surge Hikes
# ====================================================================== #
def scenario_deliveries_surge() -> None:
    clear_screen()
    print_header("SCENARIO 5: DELIVERY APP CHOICE & MONSOON SURGE HIKES")
    print(f"{C_DIM}In this scenario, a busy executive (Vikram) and a relaxed worker (Asha){C_RESET}")
    print(f"{C_DIM}choose whether to order delivery or travel physically to a formal store.{C_RESET}")
    print(f"{C_DIM}Rain triggers a surge delivery pricing hike (up to 2.5x base fee).{C_RESET}\n")

    # 1. Setup Agents
    # Vikram: 3 activities (Busy)
    vikram = Agent(
        id=601,
        home_node=5,
        work_node=30,
        income_bracket=5,
        age=45,
        household_id=20,
        occupation=Occupation.OFFICE_EXECUTIVE,
        schedule=ActivitySchedule(
            activities=[
                Activity(ActivityType.HOME, 5, 0, 480),
                Activity(ActivityType.WORK, 30, 480, 480),
                Activity(ActivityType.RECREATION, 15, 960, 120),
            ]
        ),
        shopping_needs=[ShoppingNeed("food", 0.8)],
        weights=UtilityWeights.for_occupation(Occupation.OFFICE_EXECUTIVE),
        cash_balance=2000.0
    )

    # Asha: 1 activity (Relaxed)
    asha = Agent(
        id=602,
        home_node=5,
        work_node=None,
        income_bracket=2,
        age=34,
        household_id=10,
        occupation=Occupation.BLUE_COLLAR_WORKER,
        schedule=ActivitySchedule(
            activities=[
                Activity(ActivityType.HOME, 5, 0, 1440),
            ]
        ),
        shopping_needs=[ShoppingNeed("food", 0.8)],
        cash_balance=800.0
    )

    # Delivery agent
    rahul = DeliveryAgent(id=701, home_node=12, current_location=12, cash_balance=150.0, earnings=0.0)

    # 2. Get user input for rain intensity
    try:
        raw_rain = input(f"{C_BOLD}Enter rain intensity [0.0 = Dry, 1.0 = Storm] (default 0.8): {C_RESET}")
        rain_intensity = float(raw_rain) if raw_rain.strip() else 0.8
        rain_intensity = max(0.0, min(1.0, rain_intensity))
    except ValueError:
        rain_intensity = 0.8

    # Calculate dynamic delivery fee
    base_fee = 40.0
    fee = DeliveryAgent.get_delivery_fee(base_fee=base_fee, rain_intensity=rain_intensity)
    multiplier = fee / base_fee

    print(f"\n{C_BOLD}Dynamic Delivery Pricing Status:{C_RESET}")
    print(f"  Rain Intensity:      {C_CYAN}{rain_intensity:.2f}{C_RESET}")
    print(f"  Surge Multiplier:    {C_YELLOW}{multiplier:.2f}x{C_RESET}")
    print(f"  Total Delivery Fee:  {C_GREEN}₹{fee:.2f}{C_RESET} (Base: ₹{base_fee:.2f})")

    # Define choice alternatives
    # For delivery, price_level increases with the fee
    price_level_delivery = 0.8 + (fee / 50.0) # base level 0.8 + fee contribution
    
    alts = [
        # Store Alternative: requires travel time and distance
        ShopAlternative(
            shop_id=101,
            shop_type=ShopType.FORMAL_STORE,
            distance_km=1.8,
            travel_time_min=15.0,
            price_level=0.8,
            product_match=0.9
        ),
        # Delivery Alternative: zero travel time/distance for shopper, but higher price
        ShopAlternative(
            shop_id=102,
            shop_type=ShopType.DELIVERY,
            distance_km=0.0,
            travel_time_min=0.0,
            price_level=price_level_delivery,
            product_match=0.9
        )
    ]

    choice_model = ShopChoiceModel(rng=np.random.default_rng(42))

    # Evaluate for Asha (Relaxed)
    print(f"\n{C_BOLD}--- Asha (Relaxed, Non-busy Worker) ---{C_RESET}")
    print(f"  Busy status: {C_GREEN}False (1 schedule activity){C_RESET}")
    for alt in alts:
        u = choice_model.utility(asha, alt)
        print(f"  {alt.shop_type.value:15s} | Price Level: {alt.price_level:.2f} | Utility: {C_GREEN if u > -2 else C_RED}{u:8.4f}{C_RESET}")
    chosen_asha = choice_model.choose(asha, alts, stochastic=False)
    print(f"  ➜ {C_BOLD}{C_GREEN}Asha decides to shop at: {chosen_asha.shop_type.value}{C_RESET}")

    # Evaluate for Vikram (Busy)
    print(f"\n{C_BOLD}--- Vikram (Busy Office Executive) ---{C_RESET}")
    print(f"  Busy status: {C_RED}True (3 schedule activities → Busy Bonus!){C_RESET}")
    for alt in alts:
        u = choice_model.utility(vikram, alt)
        print(f"  {alt.shop_type.value:15s} | Price Level: {alt.price_level:.2f} | Utility: {C_GREEN if u > -2 else C_RED}{u:8.4f}{C_RESET}")
    chosen_vikram = choice_model.choose(vikram, alts, stochastic=False)
    print(f"  ➜ {C_BOLD}{C_GREEN}Vikram decides to shop at: {chosen_vikram.shop_type.value}{C_RESET}")

    # Process Vikram's Transaction
    print(f"\n{C_BOLD}{C_BLUE}========================================================================{C_RESET}")
    print(f"{C_BOLD}{C_BLUE}                  EXECUTING SELECTED SHOPPING PLANS                     {C_RESET}")
    print(f"{C_BOLD}{C_BLUE}========================================================================{C_RESET}")

    for agent, name, chosen in [(asha, "Asha", chosen_asha), (vikram, "Vikram", chosen_vikram)]:
        print(f"\n{C_BOLD}{name}'s Action:{C_RESET}")
        if chosen.shop_type == ShopType.DELIVERY:
            print(f"  Shopper orders via Delivery App. Dispatching Rahul (Delivery Agent)...")
            
            # Simple delivery dispatch animation
            bar_length = 20
            for i in range(1, bar_length + 1):
                ratio = i / bar_length
                spaces_before = " " * i
                spaces_after = " " * (bar_length - i)
                print(f"\r  Rahul riding bike: [{C_YELLOW}{spaces_before}🚲{spaces_after}{C_RESET}] {int(ratio*100)}%", end="", flush=True)
                time.sleep(0.04)
            print()
            
            # Rahul delivers order
            # Rahul earns fee, ends up at agent's home node
            rahul.deliver_order(fee, destination_node=agent.home_node)
            
            # Deduct cost from shopper
            # Assume base product price is ₹150.0
            product_cost = 150.0
            total_charged = product_cost + fee
            agent.cash_balance = max(0.0, agent.cash_balance - total_charged)
            
            print(f"  {C_GREEN}✔ Delivery Successful!{C_RESET}")
            print(f"  Total charged to {name}:  ₹{total_charged:.2f} (Product: ₹{product_cost:.2f} + Fee: ₹{fee:.2f})")
            print(f"  {name}'s Remaining Cash: ₹{agent.cash_balance:.2f}")
            print(f"  Rahul's Earnings today: +₹{fee:.2f}")
            print(f"  Rahul's New Cash:       ₹{rahul.cash_balance:.2f}")
            print(f"  Rahul's total completed: {rahul.completed_deliveries_count} delivery/ies")
        else:
            # Physical shop commute
            print(f"  Shopper decides to travel physically to save cash (No delivery fee paid).")
            product_cost = 150.0
            agent.cash_balance = max(0.0, agent.cash_balance - product_cost)
            print(f"  Total charged to {name}:  ₹{product_cost:.2f}")
            print(f"  {name}'s Remaining Cash: ₹{agent.cash_balance:.2f}")

    input(f"\n{C_BOLD}{C_DIM}Press Enter to return to main menu...{C_RESET}")

# ====================================================================== #
# SCENARIO 6: Delhi Public Transit & Municipal Mitigation Dashboard
# ====================================================================== #
def scenario_municipal_mitigation() -> None:
    import json
    clear_screen()
    print_header("SCENARIO 6: DELHI PUBLIC TRANSIT & MUNICIPAL MITIGATION")
    print(f"{C_DIM}This scenario demonstrates public transit operators (Metro and Bus) under{C_RESET}")
    print(f"{C_DIM}monsoon stress, and the role of municipal mitigation agents.{C_RESET}\n")

    # 1. Load Route Data
    bus_stops = []
    metro_stations = []
    
    # Load bus routes from JSON
    try:
        base_path = os.path.dirname(__file__)
        bus_json_path = os.path.abspath(os.path.join(base_path, "..", "..", "..", "data", "processed_data", "bus_routes.json"))
        with open(bus_json_path, "r", encoding="utf-8") as f:
            routes = json.load(f)
            # Find Route 522 stops
            route_522 = next((r for r in routes if r["route_id"] == "route_4"), routes[0])
            bus_stops = route_522["stops"]
            route_name = route_522["route_name"]
    except Exception:
        # Fallback to hardcoded Delhi Bus 522 stops
        route_name = "Route 522"
        bus_stops = [
            {"name": "Ambedkar Nagar Terminal", "lat": 28.5200, "lon": 77.2300},
            {"name": "AIIMS", "lat": 28.5670, "lon": 77.2090},
            {"name": "Krishi Bhawan", "lat": 28.6140, "lon": 77.2100},
            {"name": "Connaught Place", "lat": 28.6328, "lon": 77.2197}
        ]

    # Load metro network from JSON
    try:
        base_path = os.path.dirname(__file__)
        metro_json_path = os.path.abspath(os.path.join(base_path, "..", "..", "..", "data", "processed_data", "metro_network.json"))
        with open(metro_json_path, "r", encoding="utf-8") as f:
            net = json.load(f)
            metro_stations = net["stations"]
    except Exception:
        # Fallback to hardcoded Delhi Metro Yellow Line stations
        metro_stations = [
            {"id": "new_delhi", "name": "New Delhi"},
            {"id": "rajiv_chowk", "name": "Rajiv Chowk"},
            {"id": "patel_chowk", "name": "Patel Chowk"}
        ]

    # 2. Instantiate Transit Operators
    bus = BusDriver(id=801, route_id="route_4", route_name=route_name, stops=bus_stops, capacity=50)
    metro = MetroConductor(id=802, line_name="Yellow Line", stations=metro_stations, capacity=300)

    print(f"{C_BOLD}Public Transit Fleet Status (Baseline):{C_RESET}")
    print(f"  [Bus]   {bus.route_name} at Stop: {bus.stops[bus.current_stop_idx]['name']}")
    print(f"          Comfort level:      {make_progress_bar(bus.get_comfort_score(), 1.0, color=C_GREEN)}")
    print(f"  [Metro] {metro.line_name} at Station: {metro.stations[metro.current_station_idx]['name']}")
    print(f"          Comfort level:      {make_progress_bar(metro.get_comfort_score(), 1.0, color=C_GREEN)}")

    # 3. Simulate weather shock
    raw_monsoon = input(f"\n{C_BOLD}Simulate heavy monsoon storm? (y/n) [default: y]: {C_RESET}").strip().lower()
    is_monsoon = raw_monsoon != "n"

    rain_intensity = 0.9 if is_monsoon else 0.0
    road_congestion = 2.5 if is_monsoon else 1.0
    
    if is_monsoon:
        print(f"\n{C_BOLD}{C_RED}⛈ HEAVY MONSOON STORM DETECTED (Rain: {rain_intensity}) ⛈{C_RESET}")
        print(f"  - Road nodes are waterlogged (flooding index = 0.8)")
        print(f"  - Commuters rush to shelters, spiking metro passenger load!")
        
        # Simulating passenger loads
        bus.board_passengers(15) # some riders stay on bus
        metro.board_passengers(265) # metro gets highly crowded
    else:
        print(f"\n{C_BOLD}{C_GREEN}☀️ CLEAR WEATHER CONDITIONS ☀️{C_RESET}")
        bus.board_passengers(10)
        metro.board_passengers(60)

    # Initial travel times under simulated weather
    base_bus_delay = bus.advance_stop(rain_intensity=rain_intensity, road_congestion=road_congestion)
    # Undo step increment for demonstration purposes
    bus.current_stop_idx = (bus.current_stop_idx - 1) % len(bus.stops)

    print(f"\n{C_BOLD}Current Travel Impacts:{C_RESET}")
    print(f"  Bus Stop-to-Stop travel time: {C_BOLD}{C_RED if base_bus_delay > 10 else C_GREEN}{base_bus_delay:.2f} mins{C_RESET} (Base: 5.0 mins)")
    print(f"  Bus Passenger Count:          {bus.passenger_count}/{bus.capacity} (Comfort: {make_progress_bar(bus.get_comfort_score(), 1.0, color=C_YELLOW if bus.get_comfort_score() > 0.4 else C_RED)})")
    print(f"  Metro Station-to-Station time:{C_BOLD}{C_GREEN}{metro.advance_station():.2f} mins{C_RESET} ({C_CYAN}Fixed - runs underground!{C_RESET})")
    # Undo step increment
    metro.current_station_idx = metro.current_station_idx - metro.direction
    print(f"  Metro Passenger Count:        {metro.passenger_count}/{metro.capacity} (Comfort: {make_progress_bar(metro.get_comfort_score(), 1.0, color=C_YELLOW if metro.get_comfort_score() > 0.4 else C_RED)})")

    if not is_monsoon:
        input(f"\n{C_BOLD}{C_DIM}Press Enter to return to main menu...{C_RESET}")
        return

    # 4. Mitigation Actions
    print(f"\n{C_BOLD}{C_CYAN}========================================================================{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}                      MUNICIPAL MITIGATION CONSOLE                      {C_RESET}")
    print(f"{C_BOLD}{C_CYAN}========================================================================{C_RESET}")
    print(f"  [1] Dispatch Drainage Worker (drains water logged roads)")
    print(f"  [2] Station Traffic Police (coordinates traffic, reduces congestion)")
    print(f"  [3] Apply BOTH Mitigations (Joint municipal effort)")
    print(f"  [4] None (Let gridlock resolve naturally)")
    
    choice = input(f"\n{C_BOLD}Select mitigation action [1-4]: {C_RESET}").strip()
    
    eff_rain = rain_intensity
    eff_congestion = road_congestion
    
    if choice == "1" or choice == "3":
        print(f"\n{C_BOLD}{C_BLUE}Dispatching Drainage Worker...{C_RESET}")
        worker = DrainageWorker(id=901, current_location=0, clearing_power=0.3)
        worker.dispatch_to(10)
        
        # Animate drainage work
        bar_length = 20
        for i in range(1, bar_length + 1):
            ratio = i / bar_length
            water = "~" * (bar_length - i)
            drained = "█" * i
            print(f"\r  Clearing waterlogging: [{C_BLUE}{drained}{C_DIM}{water}{C_RESET}] {int(ratio*100)}%", end="", flush=True)
            time.sleep(0.04)
        print()
        
        # Drainage clears waterlogged delay
        eff_rain = 0.0 # water cleared from road
        print(f"  {C_GREEN}✔ Road flooding cleared by drainage worker!{C_RESET}")

    if choice == "2" or choice == "3":
        print(f"\n{C_BOLD}{C_YELLOW}Stationing Traffic Police...{C_RESET}")
        police = TrafficPolice(id=902, current_location=0, efficiency=0.4)
        
        # Animate police direction
        bar_length = 20
        for i in range(1, bar_length + 1):
            ratio = i / bar_length
            spaces = " " * (i % 5)
            print(f"\r  Police directing traffic: [🚦 {C_YELLOW}👮‍♂️{C_RESET}{spaces}🚗 🚙] {int(ratio*100)}%", end="", flush=True)
            time.sleep(0.04)
        print()
        
        # Traffic police reduces congestion index
        eff_congestion = police.clear_congestion(road_congestion)
        print(f"  {C_GREEN}✔ Congestion index reduced from {road_congestion:.2f} to {eff_congestion:.2f} by Traffic Police!{C_RESET}")

    # 5. Show mitigated results
    final_bus_delay = bus.advance_stop(rain_intensity=eff_rain, road_congestion=eff_congestion)
    
    print(f"\n{C_BOLD}{C_GREEN}Mitigation Results Summary:{C_RESET}")
    print(f"  Original Bus Travel Time: {C_BOLD}{C_RED}{base_bus_delay:.2f} minutes{C_RESET}")
    print(f"  New Bus Travel Time:      {C_BOLD}{C_GREEN}{final_bus_delay:.2f} minutes{C_RESET}")
    if final_bus_delay < base_bus_delay:
        improvement = ((base_bus_delay - final_bus_delay) / base_bus_delay) * 100.0
        print(f"  Transit speedup:          {C_BOLD}{C_GREEN}+{improvement:.1f}% travel time saved!{C_RESET}")
    else:
        print(f"  Transit speedup:          {C_YELLOW}No change (No mitigations applied).{C_RESET}")

    # Show Metro ridership shift back to normal if roads clear
    if choice == "1" or choice == "3":
        # roads are clear, so some commuters deboard metro and return to bus/auto
        deboarded = metro.deboard_passengers(120)
        print(f"\n  [Metro Update] Commuters notice clear roads. Deboarding {deboarded} passengers back to surface modes.")
        print(f"  New Metro Passenger Count: {metro.passenger_count}/{metro.capacity} (Comfort: {make_progress_bar(metro.get_comfort_score(), 1.0, color=C_GREEN)})")

    input(f"\n{C_BOLD}{C_DIM}Press Enter to return to main menu...{C_RESET}")

# ====================================================================== #
# Main Shell Menu
# ====================================================================== #
def main() -> None:
    while True:
        clear_screen()
        print_header("SUB-02 RETAIL & ECONOMIC AGENT SIMULATION SHIELD")
        print(f"{C_BOLD}{C_CYAN}Select an interactive terminal scenario to execute:{C_RESET}\n")
        print(f"  {C_BOLD}{C_GREEN}[1]{C_RESET} Scenario 1: Interactive Transaction Utility & Choice Simulator")
        print(f"  {C_BOLD}{C_GREEN}[2]{C_RESET} Scenario 2: Live Animated Stall Lifecycle (Inventory & Relocation)")
        print(f"  {C_BOLD}{C_GREEN}[3]{C_RESET} Scenario 3: Weather Disruptions & Store Staff Tardiness Dashboard")
        print(f"  {C_BOLD}{C_GREEN}[4]{C_RESET} Scenario 4: Wholesale Restocking Delays (Dry vs. Rain Conditions)")
        print(f"  {C_BOLD}{C_GREEN}[5]{C_RESET} Scenario 5: Delivery App Choice & Monsoon Surge Hikes")
        print(f"  {C_BOLD}{C_GREEN}[6]{C_RESET} Scenario 6: Delhi Public Transit & Municipal Mitigation Dashboard")
        print(f"  {C_BOLD}{C_RED}[7]{C_RESET} Exit Dashboard")
        print()

        choice = input(f"{C_BOLD}Enter scenario number [1-7]: {C_RESET}").strip()
        if choice == "1":
            scenario_transaction()
        elif choice == "2":
            scenario_animated_stall()
        elif choice == "3":
            scenario_weather_disruption()
        elif choice == "4":
            scenario_restock_delays()
        elif choice == "5":
            scenario_deliveries_surge()
        elif choice == "6":
            scenario_municipal_mitigation()
        elif choice == "7":
            clear_screen()
            print(f"\n{C_BOLD}{C_GREEN}Thank you for playing the simulator! Goodbye!{C_RESET}\n")
            break
        else:
            print(f"\n{C_RED}Invalid choice! Press Enter to try again.{C_RESET}")
            time.sleep(1.0)

if __name__ == "__main__":
    main()
