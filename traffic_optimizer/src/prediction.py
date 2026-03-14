"""
Simple AI traffic prediction module using scikit-learn LinearRegression.
Predicts approximate vehicle count ~10 minutes into the future.
"""
from sklearn.linear_model import LinearRegression
import numpy as np


def train_model():
    """
    Train on synthetic traffic progression data.
    X = current vehicle counts, y = projected counts ~10 min later.
    """
    X = np.array([[10], [20], [40], [60], [80], [100], [120], [150]])
    y = np.array([  15,   28,   52,   75,  100,  128,  155,  190])

    model = LinearRegression()
    model.fit(X, y)
    return model


def predict_traffic(model, current):
    """Return predicted vehicle count (clipped to >= 0)."""
    prediction = model.predict([[current]])[0]
    return max(0, int(round(prediction)))
