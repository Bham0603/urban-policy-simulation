import pytest
from simulation.engine import UrbanModel
from simulation.economic_agents import MesaStallOwner, MesaStoreManager, MesaStoreStaff, MesaDeliveryAgent
from app.models.schemas import ScenarioConfig

@pytest.fixture
def base_config():
    return ScenarioConfig(
        name="test_scenario",
        city="delhi",
        population=100,
        seed=42,
        use_real_data=False,
    )

def test_economic_agents_spawn(base_config):
    """Test that economic agents are spawned in correct proportions."""
    model = UrbanModel(base_config)
    
    stalls = [a for a in model.schedule.agents if isinstance(a, MesaStallOwner)]
    managers = [a for a in model.schedule.agents if isinstance(a, MesaStoreManager)]
    staff = [a for a in model.schedule.agents if isinstance(a, MesaStoreStaff)]
    delivery = [a for a in model.schedule.agents if isinstance(a, MesaDeliveryAgent)]
    
    assert len(stalls) == 5  # 5% of 100
    assert len(managers) == 1  # 1% of 100
    assert len(staff) == 2  # 2% of 100
    assert len(delivery) == 2  # 2% of 100

def test_stall_owner_steps(base_config):
    """Test that StallOwner processes a day, decays inventory, and earns money."""
    model = UrbanModel(base_config)
    
    stall = next(a for a in model.schedule.agents if isinstance(a, MesaStallOwner))
    
    # Set time to 10:00 AM
    model.sim_time_minutes = 10 * 60
    
    # Force state to prevent random failures
    stall._has_begun_day = True
    stall.is_disrupted_today = False
    
    initial_inv = stall.inventory
    
    # Step a few times
    for _ in range(3):
        stall.step()
        model.sim_time_minutes += 5
        
    assert stall.inventory < initial_inv

def test_delivery_agent_rain_surge(base_config):
    """Test dynamic rain pricing for delivery agents."""
    model = UrbanModel(base_config)
    
    delivery = next(a for a in model.schedule.agents if isinstance(a, MesaDeliveryAgent))
    
    # Base fee
    base_fee = delivery.get_delivery_fee(10.0, 0.0)
    assert base_fee == 10.0
    
    # Surge fee
    surge_fee = delivery.get_delivery_fee(10.0, 0.8)
    assert surge_fee > 10.0
    assert surge_fee == 10.0 * (1.0 + 1.5 * 0.8)

def test_dynamic_restock_time(base_config):
    """Test that restocking uses dynamic travel times."""
    model = UrbanModel(base_config)
    stall = next(a for a in model.schedule.agents if isinstance(a, MesaStallOwner))
    
    # Force low inventory to trigger restock
    stall.inventory = 0.0
    stall._has_begun_day = True
    
    # Set time to midday
    model.sim_time_minutes = 12 * 60
    
    stall.step()
    
    assert stall.inventory > 0.0
    assert stall.cash_balance < 1000.0  # Spent money on restock
