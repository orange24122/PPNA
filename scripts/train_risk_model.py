"""
根据模拟数据训练一个简易 XGBoost 风险评估模型。
运行方式：
    conda activate PPNA
    python scripts/train_risk_model.py
"""

from pathlib import Path
from typing import List

import numpy as np
import xgboost as xgb

MODEL_PATH = Path("models/risk_classifier.json")


def generate_mock_dataset(sample_size: int = 2000):
    rng = np.random.default_rng(seed=42)
    # 特征：chunk 置信度、长度特征、法规匹配数量
    confidences = rng.uniform(0, 1, sample_size)
    lengths = rng.uniform(0, 2, sample_size)
    regs = rng.uniform(0, 1, sample_size)
    features = np.stack([confidences, lengths, regs], axis=1)

    labels = (
        (confidences * 0.6 + lengths * 0.3 + regs * 0.1 + rng.normal(0, 0.05, sample_size))
        > 0.55
    ).astype(int)
    return features, labels


def train():
    X, y = generate_mock_dataset()
    dtrain = xgb.DMatrix(X, label=y)
    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 4,
        "eta": 0.2,
    }
    booster = xgb.train(params, dtrain, num_boost_round=80)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(MODEL_PATH))
    print(f"模型已保存到 {MODEL_PATH}")


if __name__ == "__main__":
    train()

