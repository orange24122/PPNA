import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app import models
from app.config.settings import get_settings

logger = logging.getLogger(__name__)

try:
    from pymilvus import Collection, connections, utility

    HAS_MILVUS = True
except Exception:  # pragma: no cover
    Collection = None
    connections = None
    utility = None
    HAS_MILVUS = False


class RagRetriever:
    """封装 Milvus 查询，若不可用则回退到 PostgreSQL。"""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.collection: Optional["Collection"] = None
        if HAS_MILVUS:
            try:
                connections.connect(
                    alias="default",
                    host=self.settings.milvus_host,
                    port=self.settings.milvus_port,
                )
                if utility.has_collection(self.settings.milvus_collection):
                    self.collection = Collection(self.settings.milvus_collection)
                    self.collection.load()
                    logger.info("Milvus collection 已加载：%s", self.settings.milvus_collection)
                else:
                    logger.warning("Milvus 不存在 collection：%s", self.settings.milvus_collection)
            except Exception as exc:  # pragma: no cover
                logger.warning("连接 Milvus 失败，使用数据库回退。%s", exc)
                self.collection = None

    def search(
        self,
        vector: List[float],
        kb_type: str,
        top_k: int = 3,
    ) -> List[Dict[str, str]]:
        if self.collection:
            try:
                results = self.collection.search(
                    data=[vector],
                    anns_field="embedding",
                    param={"metric_type": "IP", "params": {"nprobe": 10}},
                    limit=top_k,
                    expr=f"kb_type == \"{kb_type}\"",
                    output_fields=["kb_id", "content"],
                )
                hits = []
                for hit in results[0]:
                    hits.append(
                        {
                            "kb_id": hit.entity.get("kb_id"),
                            "title": hit.entity.get("kb_id"),
                            "content": hit.entity.get("content"),
                        }
                    )
                if hits:
                    return hits
            except Exception as exc:  # pragma: no cover
                logger.warning("Milvus 搜索失败，回退数据库：%s", exc)

        query = (
            self.db.query(models.KnowledgeBaseItem)
            .filter(models.KnowledgeBaseItem.kb_type == kb_type)
            .order_by(models.KnowledgeBaseItem.updated_at.desc())
            .limit(top_k)
            .all()
        )
        return [
            {"kb_id": item.kb_id, "title": item.kb_id, "content": item.content_text}
            for item in query
        ]

