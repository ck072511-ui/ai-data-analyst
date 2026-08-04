import logging
from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cleaning_audit import CleaningAudit
from app.models.dataset import UserDataset

logger = logging.getLogger(__name__)


def log_audit_entry(
    db_session: Session,
    dataset: UserDataset,
    user_id: str,
    user_email: str,
    operations_applied: List[str],
    rows_changed: int,
    columns_changed: int,
    quality_score_before: int,
    quality_score_after: int,
    version_created: int,
    status: str = "success",
) -> CleaningAudit:
    """Inserts a new auditing record describing the operations applied and changes to the data quality score."""
    try:
        audit_entry = CleaningAudit(
            dataset_id=dataset.id,
            dataset_name=dataset.filename,
            user_id=user_id,
            user_email=user_email,
            operations_applied=operations_applied,
            rows_changed=rows_changed,
            columns_changed=columns_changed,
            quality_score_before=quality_score_before,
            quality_score_after=quality_score_after,
            version_created=version_created,
            timestamp=datetime.utcnow(),
            status=status,
        )

        db_session.add(audit_entry)
        db_session.commit()
        db_session.refresh(audit_entry)
        logger.info(f"Log audit entry added for dataset {dataset.filename} - Version: {version_created}")
        return audit_entry
    except Exception as e:
        db_session.rollback()
        logger.exception("Failed to write cleaning audit log")
        raise e


def get_audit_history(db_session: Session, dataset_id: str) -> List[CleaningAudit]:
    """Retrieves all cleaning history logs sorted chronologically (newest first) for a specific dataset."""
    stmt = select(CleaningAudit).where(CleaningAudit.dataset_id == dataset_id).order_by(CleaningAudit.timestamp.desc())
    return list(db_session.execute(stmt).scalars().all())


async def log_audit_entry_async(
    session,
    dataset: UserDataset,
    user_id: str,
    user_email: str,
    operations_applied: List[str],
    rows_changed: int,
    columns_changed: int,
    quality_score_before: int,
    quality_score_after: int,
    version_created: int,
    status: str = "success",
) -> CleaningAudit:
    """Inserts a new auditing record asynchronously inside the active transaction session."""
    try:
        audit_entry = CleaningAudit(
            dataset_id=dataset.id,
            dataset_name=dataset.filename,
            user_id=user_id,
            user_email=user_email,
            operations_applied=operations_applied,
            rows_changed=rows_changed,
            columns_changed=columns_changed,
            quality_score_before=quality_score_before,
            quality_score_after=quality_score_after,
            version_created=version_created,
            timestamp=datetime.utcnow(),
            status=status,
        )
        session.add(audit_entry)
        await session.commit()
        logger.info(f"Log audit entry added asynchronously for dataset {dataset.filename} - Version: {version_created}")
        return audit_entry
    except Exception as e:
        await session.rollback()
        logger.exception("Failed to write cleaning audit log asynchronously")
        raise e
