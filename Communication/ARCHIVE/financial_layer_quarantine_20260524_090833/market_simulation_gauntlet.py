import os
import sys
import json
import math
import random
import time

sys.path.append(r"D:\Infinite\Infinity\Strategy")
from trading_engine import TradingEngine

engine = TradingEngine()
model_path = r"D:\Infinite\Infinity\Strategy\State\paper_market_model.json"

def get_simulated_price(step):
    """Phase 207: Regime Shifts for 100 cycles."""
    base = 60000.0
    
    # 0-30: Ranging/Chop
    # 30-60: Bull Trend
    # 60-80: Flash Crash
    # 80-100: Recovery
    
    if step < 30:
        price = base + math.sin(step * 0.8) * 1500.0 + random.uniform(-500, 500)
    elif step < 60:
        base += (step - 30) * 400.0 # trending up
        price = base + math.sin(step * 0.5) * 2000.0 + random.uniform(-1000, 1000)
    elif step < 80:
        base = 72000.0 - ((step - 60) * 1200.0) # crashing down fast
        price = base + random.uniform(-2000, 2000)
    else:
        base = 48000.0 + ((step - 80) * 800.0) # recovering
        price = base + random.uniform(-500, 500)
        
    return max(1000.0, price) # ensure positive

def inject_observation(price):
    if not os.path.exists(model_path):
        with open(model_path, "w", encoding="utf-8") as f:
            json.dump({"claims": {}}, f)
            
    with open(model_path, 'r', encoding='utf-8') as f:
        model = json.load(f)
        
    if "claims" not in model:
        model["claims"] = {}
        
    cid = f"claim_{int(time.time()*1000)}"
    model["claims"][cid] = {
        "entity": "market_data",
        "claim": f"Current BTC market conditions require observation. Price: ${price:,.2f}",
        "source_id": "simulated_gauntlet",
        "artifact_type": "market_observation"
    }
    
    with open(model_path, 'w', encoding='utf-8') as f:
        json.dump(model, f, indent=2)

def print_portfolio():
    pf = engine.portfolio
    mem = engine.memory
            
    total_val = pf.get("portfolio_value_usd", 100.0)
    unrealized = pf.get("unrealized_pnl", 0.0)
    realized = pf.get("realized_profit_usd", 0.0)
    print(f"| Value: ${total_val:,.2f} | Unrealized: ${unrealized:,.2f} | Realized: ${realized:,.2f} | USD: ${pf['usd_balance']:,.2f} | BTC: {pf['btc_holdings']:.4f} | Margin: {mem.get('buy_margin', 0):.3f} |")

print("===============================================")
print("  PHASE 207: ISOLATED TRADING GAUNTLET (100)   ")
print("===============================================")

TOTAL_CYCLES = 100

for cycle in range(1, TOTAL_CYCLES + 1):
    price = get_simulated_price(cycle)
    
    if cycle == 1:
        regime = "Ranging"
    elif cycle == 30:
        regime = "Bull Trend"
        print(f"\n>>> REGIME SHIFT: {regime} <<<\n")
    elif cycle == 60:
        regime = "Flash Crash"
        print(f"\n>>> REGIME SHIFT: {regime} <<<\n")
    elif cycle == 80:
        regime = "Recovery"
        print(f"\n>>> REGIME SHIFT: {regime} <<<\n")
        
    print(f"\n[Cycle {cycle}/{TOTAL_CYCLES}] Injecting Simulated Price: ${price:,.2f}")
    
    try:
        inject_observation(price)
        engine.run_cycle()
        print_portfolio()
    except Exception as ex:
        print(f"Engine Exception: {ex}")
        
print("\n===============================================")
print("  GAUNTLET COMPLETE                            ")
print("===============================================")
