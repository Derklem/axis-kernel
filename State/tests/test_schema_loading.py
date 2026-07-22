import pytest
from importlib.resources import files
import json
from pathlib import Path

def test_strategy_loads_state_schema():
    # Attempt to load state_vector.json from state.schemas package
    schema_text = files("state.schemas").joinpath("state_vector.json").read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    assert schema["$id"] == "urn:axis:state-vector:1.1.0"

def test_strategy_loads_observation_schema():
    schema_text = files("observation.schemas").joinpath("observation_feed.json").read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    assert "observations" in schema["properties"]

def test_state_loads_observation_schema():
    schema_text = files("observation.schemas").joinpath("observation_feed.json").read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    assert "observations" in schema["properties"]

def test_duplicate_schemas_do_not_exist():
    # Strategy should not have these
    strategy_schemas = Path(__file__).parent.parent.parent.parent / "Strategy" / "src" / "strategy" / "schemas"
    assert not (strategy_schemas / "state_vector.json").exists()
    assert not (strategy_schemas / "observation_feed.json").exists()
    
    # State should not have this
    state_schemas = Path(__file__).parent.parent / "src" / "state" / "schemas"
    assert not (state_schemas / "observation_feed.json").exists()
