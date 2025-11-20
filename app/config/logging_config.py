import logging


def setup_logging() -> None:
    """基础日志配置，供 FastAPI 与 Celery 共用。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

