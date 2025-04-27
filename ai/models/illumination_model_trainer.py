# --- ai/models/illumination_model_trainer.py ---

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os

from mpl_toolkits.mplot3d import Axes3D  # <--- Required for 3D plotting

# --- Illumination Model Trainer ---
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

# --- Visualizer Function (2D Confusion + Scatter) ---
def visualize_illumination_model():
    trainer = IlluminationModelTrainer()
    data = trainer.generate_fake_data(num_samples=5000)

    X = data[["velocity_risk", "lux_risk", "gps_risk"]]
    y = data["illumination_needed"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    trainer.model.fit(X_train, y_train)
    y_pred = trainer.model.predict(X_test)

    # --- CONFUSION MATRIX ---
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(6,6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["No Light", "Illuminate"])
    disp.plot(ax=ax, cmap="Oranges", colorbar=False)
    plt.title("Illumination Detection - Confusion Matrix", fontsize=14)
    plt.grid(False)
    plt.tight_layout()
    plt.show()

    # --- FEATURE SPACE SCATTER PLOT (Velocity vs Lux) ---
    plt.figure(figsize=(8,6))
    sns.scatterplot(
        x=X_test["velocity_risk"],
        y=X_test["lux_risk"],
        hue=y_test,
        palette=["blue", "orange"],
        style=y_pred,
        markers=["o", "X"],
        s=80,
        edgecolor="black",
        alpha=0.7
    )
    plt.title("Illumination Model: Velocity Risk vs Lux Risk", fontsize=14)
    plt.xlabel("Velocity Risk", fontsize=12)
    plt.ylabel("Lux Risk", fontsize=12)
    plt.legend(title="True Label (Color) / Prediction (Shape)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# --- 3D Feature Space Plot (Velocity, Lux, GPS Risk) ---
def plot_illumination_feature_space_3d():
    trainer = IlluminationModelTrainer()
    data = trainer.generate_fake_data(num_samples=3000)

    X = data[["velocity_risk", "lux_risk", "gps_risk"]]
    y = data["illumination_needed"]

    fig = plt.figure(figsize=(10,8))
    ax = fig.add_subplot(111, projection='3d')

    colors = ["blue" if label == 0 else "orange" for label in y]

    ax.scatter(
        X["velocity_risk"],
        X["lux_risk"],
        X["gps_risk"],
        c=colors,
        s=50,
        alpha=0.7,
        edgecolor="black"
    )

    ax.set_title("Illumination Model Feature Space (3D)", fontsize=14)
    ax.set_xlabel("Velocity Risk", fontsize=12)
    ax.set_ylabel("Lux Risk", fontsize=12)
    ax.set_zlabel("GPS Risk", fontsize=12)

    plt.tight_layout()
    plt.show()

# --- Only run if executed directly ---
if __name__ == "__main__":
    trainer = IlluminationModelTrainer()
    trainer.train_and_save_model()
    visualize_illumination_model()
    plot_illumination_feature_space_3d()
