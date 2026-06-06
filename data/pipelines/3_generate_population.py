"""
Pipeline 3: Generate Synthetic Population
==========================================

Generates a synthetic population of 5,000 agents for the Urban Intelligence
Platform's study area (4 km radius around Rajiv Chowk, New Delhi).

Demographics (age, income_bracket, household_size) are sampled from the
census-derived distributions produced by Pipeline 2:
    - delhi_age_distribution.csv   (Census 2011, Table C-13)
    - delhi_household_size.csv     (Census 2011, Table HH-1)
    - delhi_income_proxy.csv       (Census 2011, Table B-4 × PLFS wages)

Spatial attributes (home_node, work_node) are drawn from the OSM network
graph produced by Pipeline 1.

Idempotency:
    Uses a fixed random seed (42).  Repeated runs produce the identical
    Parquet file byte-for-byte.

Output:
    → ../processed_data/synthetic_population.parquet  (5,000 rows)
"""

import sys
import random
import pandas as pd
import numpy as np
import osmnx as ox
from pathlib import Path

# ── Encoding safety (Windows) ───────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ── Paths ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "processed_data"
GRAPHML_PATH = DATA_DIR / "network.graphml"
OUTPUT_PATH = DATA_DIR / "synthetic_population.parquet"

# Census distribution CSVs (produced by Pipeline 2)
AGE_CSV = DATA_DIR / "delhi_age_distribution.csv"
HH_CSV = DATA_DIR / "delhi_household_size.csv"
INCOME_CSV = DATA_DIR / "delhi_income_proxy.csv"

NUM_AGENTS = 5000
RANDOM_SEED = 42


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def load_census_distributions() -> tuple:
    """
    Load the three census distribution CSVs.

    Returns
    -------
    age_df : pd.DataFrame   – columns: age_group, proportion
    hh_df  : pd.DataFrame   – columns: household_size, probability
    inc_df : pd.DataFrame   – columns: income_bracket_inr, proportion
    """
    missing = []
    for p in [AGE_CSV, HH_CSV, INCOME_CSV]:
        if not p.exists():
            missing.append(p.name)
    if missing:
        raise FileNotFoundError(
            f"Census distribution file(s) not found: {', '.join(missing)}.  "
            "Please run 2_fetch_census_demographics.py first."
        )

    age_df = pd.read_csv(AGE_CSV, encoding="utf-8")
    hh_df = pd.read_csv(HH_CSV, encoding="utf-8")
    inc_df = pd.read_csv(INCOME_CSV, encoding="utf-8")

    # Validate expected columns
    assert "age_group" in age_df.columns and "proportion" in age_df.columns, \
        f"age CSV missing expected columns: {age_df.columns.tolist()}"
    assert "household_size" in hh_df.columns and "probability" in hh_df.columns, \
        f"household CSV missing expected columns: {hh_df.columns.tolist()}"
    assert "income_bracket_inr" in inc_df.columns and "proportion" in inc_df.columns, \
        f"income CSV missing expected columns: {inc_df.columns.tolist()}"

    return age_df, hh_df, inc_df


def _sample_age_from_group(age_group: str, rng: np.random.Generator) -> int:
    """
    Given an age-group label like '25-29' or '80+', return a uniformly
    sampled integer age within that range.
    """
    if age_group.endswith("+"):
        lo = int(age_group.replace("+", ""))
        return int(rng.integers(lo, lo + 15))  # 80–94
    parts = age_group.split("-")
    lo, hi = int(parts[0]), int(parts[1])
    return int(rng.integers(lo, hi + 1))


def _income_bracket_to_numeric(bracket: str) -> int:
    """
    Map an income bracket label to a numeric tier (1–5) for downstream
    vehicle-ownership models.

    Mapping:
        0-10000     → 1
        10000-20000 → 2
        20000-50000 → 3
        50000-100000→ 4
        100000+     → 5
    """
    mapping = {
        "0-10000": 1,
        "10000-20000": 2,
        "20000-50000": 3,
        "50000-100000": 4,
        "100000+": 5,
    }
    return mapping.get(bracket, 3)  # default to mid-tier if unrecognised


# ═══════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 65)
    print("Pipeline 3: Generate Synthetic Population")
    print("=" * 65)

    # ── Set deterministic seeds ──────────────────────────────────────
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    rng = np.random.default_rng(RANDOM_SEED)

    # ── Load network ─────────────────────────────────────────────────
    print(f"\n[INFO] Loading network from {GRAPHML_PATH} ...")
    try:
        G = ox.load_graphml(GRAPHML_PATH)
    except FileNotFoundError:
        print(f"[ERROR] {GRAPHML_PATH} not found. Run 1_download_osm_network.py first.")
        return

    valid_nodes = list(G.nodes)
    print(f"  Loaded {len(valid_nodes):,} valid nodes.")

    if len(valid_nodes) < 2:
        print("[ERROR] Network has fewer than 2 nodes — cannot assign home/work.")
        return

    # ── Load census distributions ────────────────────────────────────
    print("\n[INFO] Loading census distributions ...")
    age_df, hh_df, inc_df = load_census_distributions()
    print(f"  Age groups:       {len(age_df)} cohorts")
    print(f"  Household sizes:  {len(hh_df)} categories")
    print(f"  Income brackets:  {len(inc_df)} brackets")

    # Normalise weights (defensive — should already sum to 1)
    age_weights = (age_df["proportion"] / age_df["proportion"].sum()).values
    hh_weights = (hh_df["probability"] / hh_df["probability"].sum()).values
    inc_weights = (inc_df["proportion"] / inc_df["proportion"].sum()).values

    age_labels = age_df["age_group"].values
    hh_labels = hh_df["household_size"].values
    inc_labels = inc_df["income_bracket_inr"].values

    # ── Weighted sampling via pandas ─────────────────────────────────
    print(f"\n[INFO] Generating {NUM_AGENTS:,} synthetic agents ...")

    # Sample age groups, household sizes, and income brackets
    sampled_age_groups = rng.choice(age_labels, size=NUM_AGENTS, p=age_weights)
    sampled_hh_sizes = rng.choice(hh_labels, size=NUM_AGENTS, p=hh_weights)
    sampled_inc_brackets = rng.choice(inc_labels, size=NUM_AGENTS, p=inc_weights)

    # Convert age groups to integer ages
    sampled_ages = np.array([
        _sample_age_from_group(str(ag), rng) for ag in sampled_age_groups
    ])

    # Convert income brackets to numeric tiers (1-5)
    sampled_income_tiers = np.array([
        _income_bracket_to_numeric(str(b)) for b in sampled_inc_brackets
    ])

    # Sample home and work nodes (ensuring they differ)
    node_array = np.array(valid_nodes)
    home_indices = rng.integers(0, len(node_array), size=NUM_AGENTS)
    work_indices = rng.integers(0, len(node_array), size=NUM_AGENTS)
    # Where home == work, resample work
    collision_mask = home_indices == work_indices
    while collision_mask.any():
        work_indices[collision_mask] = rng.integers(
            0, len(node_array), size=collision_mask.sum()
        )
        collision_mask = home_indices == work_indices

    home_nodes = node_array[home_indices]
    work_nodes = node_array[work_indices]

    # ── Vehicle ownership (correlated with income tier) ──────────────
    car_probs = {1: 0.05, 2: 0.15, 3: 0.35, 4: 0.60, 5: 0.85}
    bike_probs = {1: 0.50, 2: 0.60, 3: 0.40, 4: 0.20, 5: 0.10}

    has_car = np.array([
        rng.random() < car_probs[tier] for tier in sampled_income_tiers
    ])
    has_bike = np.array([
        rng.random() < bike_probs[tier] for tier in sampled_income_tiers
    ])

    # ── Occupation (correlated with age and income) ──────────────────
    occupations = ["Corporate", "Service", "Student", "Labor", "Unemployed"]
    occupation_weights_base = np.array([0.30, 0.25, 0.20, 0.15, 0.10])
    occupation_weights_base = occupation_weights_base / occupation_weights_base.sum()

    sampled_occupations = []
    for age, tier in zip(sampled_ages, sampled_income_tiers):
        weights = occupation_weights_base.copy()
        if age < 22:
            weights[2] *= 3.0  # boost "Student"
            weights[0] *= 0.3  # reduce "Corporate"
        elif age > 55:
            weights[4] *= 2.0  # boost "Unemployed" (retired proxy)
            weights[2] *= 0.1  # reduce "Student"
        if tier >= 4:
            weights[0] *= 1.5  # boost "Corporate" for higher income
            weights[3] *= 0.3  # reduce "Labor"
        weights = weights / weights.sum()
        occ = rng.choice(occupations, p=weights)
        sampled_occupations.append(occ)

    sampled_occupations = np.array(sampled_occupations)

    # ── Metro pass (correlated with occupation + income) ─────────────
    metro_probs = np.full(NUM_AGENTS, 0.1)
    corporate_or_student = np.isin(sampled_occupations, ["Corporate", "Student"])
    metro_probs[corporate_or_student] += 0.5
    high_income = sampled_income_tiers >= 4
    metro_probs[high_income] += 0.3
    metro_probs = np.minimum(metro_probs, 1.0)
    has_metro_pass = rng.random(NUM_AGENTS) < metro_probs

    # ── Build DataFrame ──────────────────────────────────────────────
    df = pd.DataFrame({
        "id": [f"agent_{i:05d}" for i in range(1, NUM_AGENTS + 1)],
        "home_node": home_nodes,
        "work_node": work_nodes,
        "age": sampled_ages,
        "age_group": sampled_age_groups,
        "household_size": sampled_hh_sizes.astype(int),
        "income_bracket": sampled_inc_brackets,
        "income_bracket_numeric": sampled_income_tiers,
        "occupation": sampled_occupations,
        "has_car": has_car,
        "has_bike": has_bike,
        "has_metro_pass": has_metro_pass,
    })

    # ── Validation ───────────────────────────────────────────────────
    assert len(df) == NUM_AGENTS, f"Expected {NUM_AGENTS} rows, got {len(df)}"

    null_counts = df.isnull().sum()
    cols_with_nulls = null_counts[null_counts > 0]
    if len(cols_with_nulls) > 0:
        print(f"[WARN] Null values detected:\n{cols_with_nulls}")
    else:
        print("  ✓ No null values in any column.")

    assert (df["home_node"] != df["work_node"]).all(), \
        "Some agents have home_node == work_node"

    # ── Summary statistics ───────────────────────────────────────────
    print(f"\n  Population summary:")
    print(f"    Agents:          {len(df):,}")
    print(f"    Mean age:        {df['age'].mean():.1f}")
    print(f"    Mean HH size:    {df['household_size'].mean():.1f}")
    print(f"    Car ownership:   {df['has_car'].mean()*100:.1f}%")
    print(f"    Bike ownership:  {df['has_bike'].mean()*100:.1f}%")
    print(f"    Metro pass:      {df['has_metro_pass'].mean()*100:.1f}%")
    print(f"\n  Income distribution:")
    print(df["income_bracket"].value_counts().sort_index().to_string(header=False))
    print(f"\n  Occupation distribution:")
    print(df["occupation"].value_counts().to_string(header=False))

    # ── Save ─────────────────────────────────────────────────────────
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n[INFO] Saving to {OUTPUT_PATH} ...")
    df.to_parquet(OUTPUT_PATH, engine="pyarrow", index=False)

    print(f"\n✅ Pipeline 3 complete — {NUM_AGENTS:,} agents written to Parquet.")


if __name__ == "__main__":
    main()
