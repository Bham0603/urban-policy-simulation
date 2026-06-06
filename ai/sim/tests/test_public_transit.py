from __future__ import annotations

import pytest

from sim.agents.bus_driver import BusDriver
from sim.agents.metro_conductor import MetroConductor
from sim.agents.traffic_police import TrafficPolice
from sim.agents.drainage_worker import DrainageWorker

def test_bus_driver_rain_delay() -> None:
    stops = [
        {"name": "Stop A", "lat": 28.6, "lon": 77.2},
        {"name": "Stop B", "lat": 28.7, "lon": 77.3}
    ]
    bus = BusDriver(id=1, route_id="R1", route_name="Mudrika", stops=stops)

    # 1. Capacity & boarding checks
    assert bus.capacity == 50
    assert bus.passenger_count == 0
    assert bus.get_comfort_score() == 1.0

    boarded = bus.board_passengers(30)
    assert boarded == 30
    assert bus.passenger_count == 30
    assert bus.get_comfort_score() < 1.0

    # Boarding past capacity
    boarded_extra = bus.board_passengers(30)
    assert boarded_extra == 20  # only 20 could fit
    assert bus.passenger_count == 50
    assert bus.get_comfort_score() == 0.1  # min comfort reached

    deboarded = bus.deboard_passengers(10)
    assert deboarded == 10
    assert bus.passenger_count == 40

    # 2. Advance stop delays
    dry_time = bus.advance_stop(rain_intensity=0.0, road_congestion=1.0)
    assert dry_time == 5.0
    assert bus.current_stop_idx == 1

    wet_time = bus.advance_stop(rain_intensity=1.0, road_congestion=2.0)
    # base 5.0 * (1 + 1.5 * 1.0 + 0.5 * 1.0) = 5.0 * 3.0 = 15.0
    assert wet_time == 15.0
    assert bus.current_stop_idx == 0

def test_metro_conductor_crowding_comfort() -> None:
    stations = [
        {"id": "rajiv_chowk", "name": "Rajiv Chowk"},
        {"id": "new_delhi", "name": "New Delhi"},
        {"id": "patel_chowk", "name": "Patel Chowk"}
    ]
    metro = MetroConductor(id=2, line_name="Yellow", stations=stations)

    # 1. Capacity & boarding checks
    assert metro.capacity == 300
    metro.board_passengers(150)
    # comfort is 1.0 - 0.9 * (150/300) = 0.55
    assert metro.get_comfort_score() == pytest.approx(0.55)

    # 2. Station advancing
    assert metro.current_station_idx == 0
    assert metro.direction == 1
    
    t1 = metro.advance_station()
    assert t1 == 3.0  # constant time
    assert metro.current_station_idx == 1

    t2 = metro.advance_station()
    assert metro.current_station_idx == 2
    assert metro.direction == 1

    t3 = metro.advance_station()
    # At the end of the line, direction reverses to -1
    assert metro.current_station_idx == 1
    assert metro.direction == -1

def test_mitigation_agents_behavior() -> None:
    # 1. Traffic Police clears road congestion
    police = TrafficPolice(id=3, current_location=101, efficiency=0.3)
    assert police.current_location == 101
    
    mitigated_delay = police.clear_congestion(40.0)
    assert mitigated_delay == 28.0  # 40 * (1 - 0.3)
    
    police.patrol_to(102)
    assert police.current_location == 102

    # 2. Drainage Worker clears flood levels
    worker = DrainageWorker(id=4, current_location=105, clearing_power=0.25)
    assert worker.is_busy is False

    worker.dispatch_to(106)
    assert worker.current_location == 106
    assert worker.is_busy is True

    # Work simulation
    flood_level = 0.60
    flood_level = worker.work_tick(flood_level)
    assert flood_level == 0.35
    assert worker.is_busy is True

    flood_level = worker.work_tick(flood_level)
    assert flood_level == pytest.approx(0.10)
    assert worker.is_busy is True

    flood_level = worker.work_tick(flood_level)
    assert flood_level == 0.0
    assert worker.is_busy is False  # cleared!
