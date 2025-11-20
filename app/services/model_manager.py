import hashlib
import json
import logging
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

import numpy as np

from app.config.settings import get_settings

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    HAS_TRANSFORMERS = True
except Exception:  # pragma: no cover
    torch = None
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    HAS_TRANSFORMERS = False

try:
    import xgboost as xgb

    HAS_XGBOOST = True
except Exception:  # pragma: no cover
    xgb = None
    HAS_XGBOOST = False

try:
    from openai import OpenAI

    HAS_OPENAI = True
except Exception:  # pragma: no cover
    OpenAI = None
    HAS_OPENAI = False

logger = logging.getLogger(__name__)


class ModelManager:
    """集中管理本地模型与云端推理接口。"""

    _instance: Optional["ModelManager"] = None
    _lock = Lock()

    def __init__(self):
        self.settings = get_settings()
        self.device = "cuda" if HAS_TRANSFORMERS and torch.cuda.is_available() else "cpu"
        self._tokenizer = None
        self._bert_model = None
        self._risk_model: Optional["xgb.Booster"] = None
        self._openai_client = None

    # --------- Singleton ----------
    @classmethod
    def get_instance(cls) -> "ModelManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # --------- BERT Chunker ----------
    def _load_transformers(self):
        if not HAS_TRANSFORMERS:
            return None, None
        if self._tokenizer is None or self._bert_model is None:
            logger.info("加载 BERT 模型：%s", self.settings.bert_model_name)
            self._tokenizer = AutoTokenizer.from_pretrained(self.settings.bert_model_name)
            self._bert_model = AutoModelForSequenceClassification.from_pretrained(
                self.settings.bert_model_name,
                num_labels=2,
            ).to(self.device)
        return self._tokenizer, self._bert_model

    def segment_policy_text(self, text: str) -> List[str]:
        """基于 tokenizer 将文本切分成子块。"""
        text = text.strip()
        if not text:
            return []
        tokenizer, _ = self._load_transformers()
        if tokenizer:
            tokens = tokenizer.encode(text)
            max_len = self.settings.bert_max_chunk_tokens
            segments = []
            for i in range(0, len(tokens), max_len):
                sub_tokens = tokens[i : i + max_len]
                segment = tokenizer.decode(sub_tokens, skip_special_tokens=True)
                segments.append(segment.strip())
            return segments
        # fallback：按段落拆分
        return [part.strip() for part in text.split("\n\n") if part.strip()]

    def classify_chunk(self, text: str) -> Dict[str, float]:
        """返回 chunk 的风险置信度。"""
        tokenizer, model = self._load_transformers()
        if tokenizer and model:
            inputs = tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=self.settings.bert_max_chunk_tokens,
            ).to(self.device)
            with torch.no_grad():
                outputs = model(**inputs)
                score = torch.softmax(outputs.logits, dim=-1)[0, 1].item()
            return {"score": float(score)}
        # fallback：长度越大风险越高
        score = min(0.95, max(0.05, len(text) / 2000))
        return {"score": score}

    # --------- DashScope Client ----------
    def _get_openai_client(self):
        if self._openai_client is None and self.settings.dashscope_api_key and HAS_OPENAI:
            self._openai_client = OpenAI(
                api_key=self.settings.dashscope_api_key,
                base_url=self.settings.dashscope_base_url,
            )
        return self._openai_client

    def embed_text(self, text: str) -> List[float]:
        client = self._get_openai_client()
        if client:
            response = client.embeddings.create(
                model=self.settings.dashscope_embedding_model,
                input=text,
            )
            return response.data[0].embedding  # type: ignore[attr-defined]
        # fallback：使用 hash 生成稳定伪向量
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vector = []
        for i in range(0, len(digest), 4):
            chunk = digest[i : i + 4]
            vector.append(int.from_bytes(chunk, "little") / 2**32)
        return vector

    def generate_text(self, prompt: str) -> str:
        client = self._get_openai_client()
        if client:
            response = client.chat.completions.create(
                model=self.settings.dashscope_moe_model,
                messages=[
                    {"role": "system", "content": "你是资深隐私合规专家。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content or ""
        return f"[MOCK RESPONSE]\n{prompt[:400]}"

    # --------- XGBoost ----------
    def _load_risk_model(self):
        if not HAS_XGBOOST:
            return None
        if self._risk_model is None:
            model_path = Path(self.settings.risk_model_path)
            if model_path.exists():
                logger.info("加载风险评估模型：%s", model_path)
                self._risk_model = xgb.Booster()
                self._risk_model.load_model(str(model_path))
            else:
                logger.warning("未找到风险模型文件：%s，使用启发式预测。", model_path)
        return self._risk_model

    def predict_risk_level(self, features: List[float]) -> str:
        model = self._load_risk_model()
        if model:
            dmatrix = xgb.DMatrix(np.array([features]))
            prob = model.predict(dmatrix)[0]
            if prob > 0.66:
                return "high"
            if prob > 0.33:
                return "medium"
            return "low"
        # fallback：基于特征简单打分
        score = sum(features) / (len(features) or 1)
        if score > 0.7:
            return "high"
        if score > 0.4:
            return "medium"
        return "low"

    # --------- Prompt 构造 ----------
    def build_generation_prompt(
        self,
        app_name: str,
        chunk: str,
        regulations: List[Dict[str, str]],
        cases: List[Dict[str, str]],
    ) -> str:
        reg_text = json.dumps(regulations, ensure_ascii=False)
        case_text = json.dumps(cases, ensure_ascii=False)
        return (
            f"应用：{app_name}\n"
            f"隐私政策片段：{chunk[:800]}\n"
            f"法规参考：{reg_text}\n"
            f"案例参考：{case_text}\n"
            "请概述该片段的潜在合规风险，并提供整改建议。"
        )

