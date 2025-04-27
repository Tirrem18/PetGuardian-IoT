# --- ai/models/illumination_model_trainer.py ---

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import joblib
import os

class IlluminationModelTrainer:
    def __init__(self):
        self.model = LogisticRegression()

    def generate_fake_data(self, num_samples=1000000):
        velocity_risk = np.random.uniform(0, 10, num_samples)
        lux_risk = np.random.uniform(0, 10, num_samples)
        gps_risk = np.random.uniform(0, 10, num_samples)

        labels = []
        for v, l, g in zip(velocity_risk, lux_risk, gps_risk):
            score = (v * 0.4) + (l * 0.5) + (g * 0.2)  # 40% velocity + 50% lux + 20% gps
            if score > 2.75:
                labels.append(1)  # Illuminate
            else:
                labels.append(0)  # No illumination

        data = pd.DataFrame({
            "velocity_risk": velocity_risk,
            "lux_risk": lux_risk,
            "gps_risk": gps_risk,
            "illumination_needed": labels
        })

        return data

    def train_and_save_model(self, save_path="ai/models/illumination_model.pkl"):
        data = self.generate_fake_data(num_samples=1000000)

        X = data[["velocity_risk", "lux_risk", "gps_risk"]]
        y = data["illumination_needed"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Illumination Model Accuracy: {accuracy * 100:.2f}%")

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(self.model, save_path)
        print(f"Illumination model saved to {save_path}")

if __name__ == "__main__":
    trainer = IlluminationModelTrainer()
    trainer.train_and_save_model()
