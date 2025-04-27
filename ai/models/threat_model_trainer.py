# --- ai/models/threat_model_trainer.py ---

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import joblib
import os

class ThreatModelTrainer:
    def __init__(self):
        self.model = LogisticRegression()

    def generate_fake_data(self, num_samples=1000000):
        # Create random acoustic scores between 0 and 10
        acoustic_scores = np.random.uniform(0, 10, num_samples)

        # Create random GPS risks between 0 and 10
        gps_risks = np.random.uniform(0, 10, num_samples)

        # Simple rule for labeling: high sound + far from home = likely threat
        labels = []
        for a, g in zip(acoustic_scores, gps_risks):
            if a > 5 and g > 2:
                labels.append(1)  # Threat
            else:
                labels.append(0)  # No threat

        data = pd.DataFrame({
            "acoustic_score": acoustic_scores,
            "gps_risk": gps_risks,
            "threat_detected": labels
        })

        return data

    def train_and_save_model(self, save_path="ai/models/threat_model.pkl"):
        data = self.generate_fake_data()

        X = data[["acoustic_score", "gps_risk"]]
        y = data["threat_detected"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Threat Model Accuracy: {accuracy * 100:.2f}%")

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(self.model, save_path)
        print(f"Threat model saved to {save_path}")

# --- Only run if executed directly ---
if __name__ == "__main__":
    trainer = ThreatModelTrainer()
    trainer.train_and_save_model()
