import json
import os
import time

class TradingEngine:
    """Phase 207: Dedicated, Isolated Trading Subsystem."""
    
    def __init__(self):
        self.model_path = r"D:\Infinite\Infinity\Strategy\State\paper_market_model.json"
        self.portfolio_path = r"D:\Infinite\Infinity\Strategy\State\paper_portfolio.json"
        self.memory_path = r"D:\Infinite\Infinity\Strategy\State\financial_memory.json"
        self.ledger_path = r"D:\Infinite\Infinity\Strategy\State\paper_trade_ledger.jsonl"
        
        self.memory = self._load_memory()
        self.portfolio = self._load_portfolio()

    def _load_portfolio(self):
        if os.path.exists(self.portfolio_path):
            with open(self.portfolio_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"usd_balance": 100.0, "btc_holdings": 0.0, "cost_basis_usd": 0.0, "trading_locked": False, "total_trades_executed": 0}

    def _load_memory(self):
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "price_history": [],
            "buy_margin": 0.05,
            "sell_margin": 0.05,
            "learning_rate": 0.02,
            "regime": "ranging",
            "last_eval_trade_count": -1
        }

    def _save_memory(self):
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2)
            
    def _save_portfolio(self):
        with open(self.portfolio_path, "w", encoding="utf-8") as f:
            json.dump(self.portfolio, f, indent=2)
            
    def _log_receipt(self, action, asset, price, amount_usd, btc_amount):
        import uuid
        receipt = {
            "receipt_id": str(uuid.uuid4()),
            "timestamp_utc": time.time(),
            "action": action,
            "asset": asset,
            "price": price,
            "amount_usd_impact": amount_usd,
            "btc_impact": btc_amount,
            "portfolio_value": self.portfolio.get("portfolio_value_usd"),
            "unrealized_pnl": self.portfolio.get("unrealized_pnl")
        }
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt) + "\n")

    def _evaluate_portfolio_performance(self):
        """Phase 207: Autonomous calibration and Regime Detection."""
        total_trades = self.portfolio.get("total_trades_executed", 0)
        wins = self.portfolio.get("profitable_trades", 0)
        
        # Calculate Regime
        hist = self.memory.get("price_history", [])
        if len(hist) >= 10:
            st_ma = sum(hist[-3:]) / 3
            lt_ma = sum(hist) / len(hist)
            if st_ma > lt_ma * 1.02:
                self.memory["regime"] = "bull"
            elif st_ma < lt_ma * 0.98:
                self.memory["regime"] = "bear_crash"
            else:
                self.memory["regime"] = "ranging"
        else:
            self.memory["regime"] = "ranging"
        
        if total_trades > 0 and total_trades % 5 == 0 and total_trades != self.memory.get("last_eval_trade_count", -1):
            self.memory["last_eval_trade_count"] = total_trades
            win_rate = wins / total_trades
            if win_rate < 0.5:
                self.memory["buy_margin"] += self.memory["learning_rate"]
                self.memory["sell_margin"] += self.memory["learning_rate"]
                print(f"DEBUG: TradingEngine tightening financial posture. New margins: {self.memory['buy_margin']:.3f}")
            elif win_rate > 0.7:
                self.memory["buy_margin"] = max(0.005, self.memory["buy_margin"] - self.memory["learning_rate"])
                self.memory["sell_margin"] = max(0.005, self.memory["sell_margin"] - self.memory["learning_rate"])
                print(f"DEBUG: TradingEngine loosening financial posture. New margins: {self.memory['buy_margin']:.3f}")

    def run_cycle(self):
        if not os.path.exists(self.model_path):
            return

        if self.portfolio.get("trading_locked", False):
            print("WARNING: Paper Trading is locked due to hard drawdown limits.")
            return

        with open(self.model_path, "r", encoding="utf-8") as f:
            model = json.load(f)

        claims = model.get("claims", {})
        
        latest_btc_price = None
        for cid, claim_data in claims.items():
            if claim_data.get("entity") == "market_data" and claim_data.get("artifact_type") == "market_observation":
                text = claim_data.get("claim", "")
                try:
                    price_str = text.split("$")[1].split(" ")[0].replace(",", "")
                    latest_btc_price = float(price_str)
                except Exception:
                    pass

        if not latest_btc_price:
            return

        # Update Memory
        self.memory["price_history"].append(latest_btc_price)
        if len(self.memory["price_history"]) > 10:
            self.memory["price_history"].pop(0)
            
        self._evaluate_portfolio_performance()
        self._save_memory()

        if len(self.memory["price_history"]) < 3:
            return

        # Calculate Thresholds
        ma = sum(self.memory["price_history"]) / len(self.memory["price_history"])
        buy_threshold = ma * (1.0 - self.memory["buy_margin"])
        sell_threshold = ma * (1.0 + self.memory["sell_margin"])

        regime = self.memory.get("regime", "ranging")
        if regime == "bull":
            max_usd_deploy = self.portfolio["usd_balance"] * 0.50
        elif regime == "bear_crash":
            max_usd_deploy = self.portfolio["usd_balance"] * 0.10
        else:
            max_usd_deploy = self.portfolio["usd_balance"] * 0.20

        # Execute Logic
        action_taken = None
        amount_usd_impact = 0.0
        btc_impact = 0.0

        fee_rate = 0.005
        pre_usd = self.portfolio["usd_balance"]
        pre_btc = self.portfolio["btc_holdings"]

        if latest_btc_price <= buy_threshold and max_usd_deploy > 5.0:
            amount_usd = max_usd_deploy
            fee = amount_usd * fee_rate
            net_usd_to_buy = amount_usd - fee
            btc_bought = net_usd_to_buy / latest_btc_price
            
            # Execute Buy
            total_invested = self.portfolio.get("cost_basis_usd", 0) * self.portfolio["btc_holdings"] + amount_usd
            self.portfolio["btc_holdings"] += btc_bought
            self.portfolio["cost_basis_usd"] = total_invested / self.portfolio["btc_holdings"]
            self.portfolio["usd_balance"] -= amount_usd
            
            action_taken = "BUY"
            amount_usd_impact = -amount_usd
            btc_impact = btc_bought

        elif latest_btc_price >= sell_threshold and self.portfolio["btc_holdings"] > 0:
            amount_btc = self.portfolio["btc_holdings"]
            gross_usd = amount_btc * latest_btc_price
            fee = gross_usd * fee_rate
            net_usd_gained = gross_usd - fee
            
            # Execute Sell
            cost_of_sold = amount_btc * self.portfolio.get("cost_basis_usd", 0)
            profit = net_usd_gained - cost_of_sold
            
            self.portfolio["realized_profit_usd"] = self.portfolio.get("realized_profit_usd", 0) + profit
            self.portfolio["usd_balance"] += net_usd_gained
            self.portfolio["btc_holdings"] = 0.0 # Sold all
            self.portfolio["cost_basis_usd"] = 0.0
            
            if profit > 0:
                self.portfolio["profitable_trades"] = self.portfolio.get("profitable_trades", 0) + 1
            else:
                self.portfolio["loss_trades"] = self.portfolio.get("loss_trades", 0) + 1
                
            action_taken = "SELL"
            amount_usd_impact = net_usd_gained
            btc_impact = -amount_btc

        # Global Invariants & PNL Updating
        total_portfolio_value = self.portfolio["usd_balance"] + (self.portfolio["btc_holdings"] * latest_btc_price)
        self.portfolio["portfolio_value_usd"] = total_portfolio_value
        
        # Phase 207 Fix: Unrealized P&L is 0 if we hold no BTC.
        if self.portfolio["btc_holdings"] == 0.0:
            self.portfolio["unrealized_pnl"] = 0.0
        else:
            # Unrealized PNL is current value of holdings minus what we paid for them
            current_btc_value = self.portfolio["btc_holdings"] * latest_btc_price
            cost_of_holdings = self.portfolio["btc_holdings"] * self.portfolio["cost_basis_usd"]
            self.portfolio["unrealized_pnl"] = current_btc_value - cost_of_holdings

        if total_portfolio_value < 95.0:
            self.portfolio["trading_locked"] = True
            print("CRITICAL: Kill switch activated! Drawdown > 5%")

        if action_taken:
            self.portfolio["total_trades_executed"] = self.portfolio.get("total_trades_executed", 0) + 1
            self._log_receipt(action_taken, "BTC", latest_btc_price, amount_usd_impact, btc_impact)
            print(f"[*] Paper Trade: {action_taken} BTC at ${latest_btc_price:,.2f}. Portfolio Value: ${total_portfolio_value:,.2f}")
            
        self._save_portfolio()
