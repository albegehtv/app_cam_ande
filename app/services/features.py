"""Feature extraction helpers used for similarity matching."""
from __future__ import annotations

import colorsys
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import cv2
import numpy as np

BASIC_COLORS = {
    "negro": np.array([0, 0, 0]),
    "blanco": np.array([255, 255, 255]),
    "rojo": np.array([220, 20, 60]),
    "azul": np.array([65, 105, 225]),
    "verde": np.array([50, 205, 50]),
    "amarillo": np.array([255, 215, 0]),
    "naranja": np.array([255, 140, 0]),
    "gris": np.array([128, 128, 128]),
    "plateado": np.array([192, 192, 192]),
    "marron": np.array([139, 69, 19]),
}


@dataclass
class FeatureVector:
    color_hist: Iterable[float]
    average_color: Tuple[int, int, int]
    edge_density: float

    def to_dict(self) -> Dict:
        return {
            "color_hist": [float(value) for value in self.color_hist],
            "average_color": list(self.average_color),
            "edge_density": float(self.edge_density),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FeatureVector":
        return cls(
            color_hist=data["color_hist"],
            average_color=tuple(data["average_color"]),
            edge_density=float(data.get("edge_density", 0.0)),
        )


def compute_color_histogram(image: np.ndarray, bins: int = 16) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [bins, bins], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten()


def dominant_color_name(image: np.ndarray) -> str:
    mean_color = image.mean(axis=(0, 1))
    distances = {name: np.linalg.norm(mean_color - value) for name, value in BASIC_COLORS.items()}
    return min(distances, key=distances.get)


def calculate_edge_density(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, threshold1=80, threshold2=160)
    return float(np.count_nonzero(edges)) / float(edges.size)


def build_feature_vector(image: np.ndarray) -> FeatureVector:
    return FeatureVector(
        color_hist=compute_color_histogram(image),
        average_color=tuple(int(c) for c in image.mean(axis=(0, 1))),
        edge_density=calculate_edge_density(image),
    )


def compare_feature_vectors(a: FeatureVector, b: FeatureVector) -> float:
    hist_score = float(
        cv2.compareHist(
            np.array(a.color_hist, dtype=np.float32),
            np.array(b.color_hist, dtype=np.float32),
            cv2.HISTCMP_CORREL,
        )
    )
    hist_score = max(0.0, min(1.0, (hist_score + 1) / 2))
    color_distance = np.linalg.norm(np.array(a.average_color) - np.array(b.average_color))
    color_score = max(0.0, 1.0 - color_distance / 255.0)
    edge_score = max(0.0, 1.0 - abs(a.edge_density - b.edge_density))
    return float(0.6 * hist_score + 0.3 * color_score + 0.1 * edge_score)
