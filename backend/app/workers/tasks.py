import asyncio
import os
import tempfile

import boto3
import structlog
from celery import Celery

from app.core.config import settings
from app.rag.pipeline import rag_pipeline

logger = structlog.get_logger()


celery_app = Celery(
    "forgent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_task(
    self,
    document_id: str,
    s3_key: str,
    file_type: str,
    collection_name: str,
    filename: str,
):
    temp_path = None
    try:
        logger.info("Document processing task started", document_id=document_id)

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

        extension = f".{file_type}" if file_type else ""
        temp_path = tempfile.mktemp(suffix=extension)
        s3.download_file(settings.AWS_BUCKET_NAME, s3_key, temp_path)

        result = asyncio.run(
            rag_pipeline.ingest_document(
                temp_path,
                file_type,
                collection_name,
                document_id,
                filename,
            )
        )

        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
            temp_path = None

        logger.info("Document processing task completed", document_id=document_id)
        return result

    except Exception as exc:
        logger.exception(
            "Document processing task failed",
            document_id=document_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
