# --- ai/models/threat_model_trainer.py ---

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os

# --- Threat Model Trainer Class ---
class ThreatModelTrainer:
    def __init__(self):
        self.model = LogisticRegression()

    def generate_fake_data(self, num_samples=1000000):
        # Generate synthetic threat data
        acoustic_scores = np.random.uniform(0, 10, num_samples)
        gps_risks = np.random.uniform(0, 10, num_samples)

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

# --- Visualizer Function ---
def visualize_threat_model():
    trainer = ThreatModelTrainer()
    data = trainer.generate_fake_data(num_samples=5000)  # 5,000 samples for faster graphing

    X = data[["acoustic_score", "gps_risk"]]
    y = data["threat_detected"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    trainer.model.fit(X_train, y_train)
    y_pred = trainer.model.predict(X_test)

    # --- CONFUSION MATRIX ---
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(6,6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["No Threat", "Threat"])
    disp.plot(ax=ax, cmap="Blues", colorbar=False)
    plt.title("Threat Detection - Confusion Matrix", fontsize=14)
    plt.grid(False)
    plt.tight_layout()
    plt.show()

    # --- FEATURE SPACE SCATTER PLOT ---
    plt.figure(figsize=(8,6))
    sns.scatterplot(
        x=X_test["acoustic_score"],
        y=X_test["gps_risk"],
        hue=y_test,
        palette=["green", "red"],
        style=y_pred,
        markers=["o", "X"],
        s=80,
        edgecolor="black",
        alpha=0.7
    )
    plt.title("Threat Model Feature Space: Acoustic Score vs GPS Risk", fontsize=14)
    plt.xlabel("Acoustic Score", fontsize=12)
    plt.ylabel("GPS Risk", fontsize=12)
    plt.legend(title="True Label (Color) / Predicted (Shape)", loc="upper right")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# --- Only run if executed directly ---
if __name__ == "__main__":
    trainer = ThreatModelTrainer()
    trainer.train_and_save_model()
    visualize_threat_model()
