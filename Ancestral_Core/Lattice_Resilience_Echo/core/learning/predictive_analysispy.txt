from core.communication.alert_system import AlertSystem

class PredictiveAnalyzer:
    def __init__(self):
        print("[PredictiveAnalyzer] Initialized.")
        self.alert_system = AlertSystem()

    def analyze_and_predict(self, structured_data):
        predictions = []
        data_str = str(structured_data).lower()

        if 'ai' in data_str or 'artificial intelligence' in data_str:
            prediction = "AI trends accelerating: Increase AI-focused resources."
            self.alert_system.send_alert(prediction, alert_level="HIGH")
            predictions.append(prediction)

        if 'rain' in data_str or 'humidity' in data_str:
            prediction = "Weather indicates rain: Optimize nodes for stability."
            self.alert_system.send_alert(prediction, alert_level="MEDIUM")
            predictions.append(prediction)

        if 'market' in data_str or 'stock' in data_str:
            prediction = "Market activity detected: Secure financial data channels."
            self.alert_system.send_alert(prediction, alert_level="MEDIUM")
            predictions.append(prediction)

        if not predictions:
            prediction = "No significant trends detected: Maintain routine operations."
            self.alert_system.send_alert(prediction, alert_level="LOW")
            predictions.append(prediction)

        return predictions
