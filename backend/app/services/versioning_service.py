import logging
import os
import shutil
from datetime import datetime

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.database import get_sync_engine
from app.models.dataset import UserDataset
from app.models.dataset_version import DatasetVersion

logger = logging.getLogger(__name__)


def copy_db_table_blocking(old_table: str, new_table: str):
    """Duplicates a database table blocking using the sync engine connection."""
    sync_engine = get_sync_engine()
    with sync_engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {new_table}"))
        conn.execute(text(f"CREATE TABLE {new_table} AS SELECT * FROM {old_table}"))
    logger.info(f"Copied database table {old_table} to {new_table}")


def create_initial_version(db_session: Session, dataset: UserDataset) -> DatasetVersion:
    """Creates the V1 snapshot of a newly uploaded dataset."""
    try:
        # 1. Generate versioned paths
        file_dir, file_name = os.path.split(dataset.file_path)
        name_parts = file_name.split(".")
        ext = name_parts[-1] if len(name_parts) > 1 else "csv"

        versioned_file_name = f"{dataset.id}_v1.{ext}"
        versioned_file_path = os.path.join(file_dir, versioned_file_name)

        # Copy file on disk if not already copied
        if dataset.file_path != versioned_file_path and os.path.exists(dataset.file_path):
            shutil.copy2(dataset.file_path, versioned_file_path)

        # 2. Duplicate database table to versioned name
        versioned_table_name = f"{dataset.table_name}_v1"
        copy_db_table_blocking(dataset.table_name, versioned_table_name)

        # 3. Insert Version record
        version_record = DatasetVersion(
            dataset_id=dataset.id,
            version_number=1,
            timestamp=datetime.utcnow(),
            user_id=dataset.user_id,
            file_path=versioned_file_path,
            table_name=versioned_table_name,
            row_count=dataset.row_count,
            col_count=dataset.col_count,
            columns=dataset.columns,
            schema_info=dataset.schema_info,
            profile_info=dataset.profile_info,
            operations_applied=["Initial Upload"],
            parent_version=None,
        )

        db_session.add(version_record)
        db_session.commit()
        db_session.refresh(version_record)

        # Update dataset pointer to point to Version 1
        dataset.file_path = versioned_file_path
        dataset.table_name = versioned_table_name
        db_session.add(dataset)
        db_session.commit()

        logger.info(f"Initialized Version 1 for dataset {dataset.filename} (ID: {dataset.id})")
        return version_record
    except Exception as e:
        db_session.rollback()
        logger.exception("Failed to initialize Version 1")
        raise e


def create_next_version(
    db_session: Session,
    dataset: UserDataset,
    operations: list,
    row_count: int,
    col_count: int,
    columns: list,
    schema_info: dict,
    profile_info: dict,
    save_df_callback,  # Callback to save cleaned dataframe to versioned file
) -> DatasetVersion:
    """Saves a cleaned dataset snapshot as a new version and updates the dataset active pointer."""
    try:
        # Get max version number
        stmt = select(func.max(DatasetVersion.version_number)).where(DatasetVersion.dataset_id == dataset.id)
        max_v = db_session.execute(stmt).scalar() or 1
        new_v = max_v + 1

        # Paths for new version
        file_dir = os.path.dirname(dataset.file_path)
        name_parts = dataset.filename.split(".")
        ext = name_parts[-1] if len(name_parts) > 1 else "csv"

        new_file_path = os.path.join(file_dir, f"{dataset.id}_v{new_v}.{ext}")
        new_table_name = f"dataset_{dataset.id.replace('-', '_')}_v{new_v}"

        # Save dataframe
        save_df_callback(new_file_path, ext)

        # Copy temp clean database (which was written to dataset.table_name during clean steps)
        # We copy it to the permanent new versioned table name
        copy_db_table_blocking(dataset.table_name, new_table_name)

        # Create new version record
        version_record = DatasetVersion(
            dataset_id=dataset.id,
            version_number=new_v,
            timestamp=datetime.utcnow(),
            user_id=dataset.user_id,
            file_path=new_file_path,
            table_name=new_table_name,
            row_count=row_count,
            col_count=col_count,
            columns=columns,
            schema_info=schema_info,
            profile_info=profile_info,
            operations_applied=operations,
            parent_version=max_v,
        )

        db_session.add(version_record)
        db_session.commit()
        db_session.refresh(version_record)

        # Update user active dataset to point to this new version
        dataset.file_path = new_file_path
        dataset.table_name = new_table_name
        dataset.row_count = row_count
        dataset.col_count = col_count
        dataset.columns = columns
        dataset.schema_info = schema_info
        dataset.profile_info = profile_info

        db_session.add(dataset)
        db_session.commit()

        logger.info(f"Created version {new_v} for dataset {dataset.filename}")
        return version_record
    except Exception as e:
        db_session.rollback()
        logger.exception("Failed to create next dataset version")
        raise e


def rollback_to_version(db_session: Session, dataset: UserDataset, version_number: int) -> DatasetVersion:
    """Restores the dataset pointer and active data table to a historical version snapshot."""
    try:
        stmt = select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset.id, DatasetVersion.version_number == version_number
        )
        version_record = db_session.execute(stmt).scalar_one_or_none()
        if not version_record:
            raise ValueError(f"Version {version_number} not found for this dataset")

        # Verify physical file and table exist
        if not os.path.exists(version_record.file_path):
            raise ValueError("Historical snapshot file not found on disk")

        # Update parent dataset values to point back to target version
        dataset.file_path = version_record.file_path
        dataset.table_name = version_record.table_name
        dataset.row_count = version_record.row_count
        dataset.col_count = version_record.col_count
        dataset.columns = version_record.columns
        dataset.schema_info = version_record.schema_info
        dataset.profile_info = version_record.profile_info

        db_session.add(dataset)
        db_session.commit()

        logger.info(f"Successfully rolled back dataset {dataset.filename} to version {version_number}")
        return version_record
    except Exception as e:
        db_session.rollback()
        logger.exception("Failed to rollback dataset version")
        raise e


async def create_initial_version_async(session, dataset: UserDataset) -> DatasetVersion:
    """Async wrapper to initialize version 1 using an async database session context."""
    try:
        file_dir, file_name = os.path.split(dataset.file_path)
        name_parts = file_name.split(".")
        ext = name_parts[-1] if len(name_parts) > 1 else "csv"

        versioned_file_name = f"{dataset.id}_v1.{ext}"
        versioned_file_path = os.path.join(file_dir, versioned_file_name)

        if dataset.file_path != versioned_file_path and os.path.exists(dataset.file_path):
            await run_in_threadpool(shutil.copy2, dataset.file_path, versioned_file_path)

        versioned_table_name = f"{dataset.table_name}_v1"
        await run_in_threadpool(copy_db_table_blocking, dataset.table_name, versioned_table_name)

        version_record = DatasetVersion(
            dataset_id=dataset.id,
            version_number=1,
            timestamp=datetime.utcnow(),
            user_id=dataset.user_id,
            file_path=versioned_file_path,
            table_name=versioned_table_name,
            row_count=dataset.row_count,
            col_count=dataset.col_count,
            columns=dataset.columns,
            schema_info=dataset.schema_info,
            profile_info=dataset.profile_info,
            operations_applied=["Initial Upload"],
            parent_version=None,
        )
        session.add(version_record)

        dataset.file_path = versioned_file_path
        dataset.table_name = versioned_table_name
        session.add(dataset)

        await session.commit()
        logger.info(f"Successfully created initial async Version 1 for {dataset.filename}")
        return version_record
    except Exception as e:
        await session.rollback()
        logger.exception("Failed to create initial version asynchronously")
        raise e


async def create_next_version_async(
    session,
    dataset: UserDataset,
    operations: list,
    row_count: int,
    col_count: int,
    columns: list,
    schema_info: dict,
    profile_info: dict,
    save_df_callback,
) -> DatasetVersion:
    """Async wrapper to save cleaned dataset snapshot as a new version and update pointers."""
    try:
        # Get max version
        stmt = select(func.max(DatasetVersion.version_number)).where(DatasetVersion.dataset_id == dataset.id)
        max_v = (await session.execute(stmt)).scalar() or 1
        new_v = max_v + 1

        file_dir = os.path.dirname(dataset.file_path)
        name_parts = dataset.filename.split(".")
        ext = name_parts[-1] if len(name_parts) > 1 else "csv"

        new_file_path = os.path.join(file_dir, f"{dataset.id}_v{new_v}.{ext}")
        new_table_name = f"dataset_{dataset.id.replace('-', '_')}_v{new_v}"

        # Save file to disk
        await run_in_threadpool(save_df_callback, new_file_path, ext)

        # Copy temporary database data to versioned table name
        await run_in_threadpool(copy_db_table_blocking, dataset.table_name, new_table_name)

        version_record = DatasetVersion(
            dataset_id=dataset.id,
            version_number=new_v,
            timestamp=datetime.utcnow(),
            user_id=dataset.user_id,
            file_path=new_file_path,
            table_name=new_table_name,
            row_count=row_count,
            col_count=col_count,
            columns=columns,
            schema_info=schema_info,
            profile_info=profile_info,
            operations_applied=operations,
            parent_version=max_v,
        )
        session.add(version_record)

        dataset.file_path = new_file_path
        dataset.table_name = new_table_name
        dataset.row_count = row_count
        dataset.col_count = col_count
        dataset.columns = columns
        dataset.schema_info = schema_info
        dataset.profile_info = profile_info
        session.add(dataset)

        await session.commit()
        logger.info(f"Successfully created next Version {new_v} asynchronously")
        return version_record
    except Exception as e:
        await session.rollback()
        logger.exception("Failed to create next version asynchronously")
        raise e


async def rollback_to_version_async(session, dataset: UserDataset, version_number: int) -> DatasetVersion:
    """Async wrapper to restore database pointer to chosen version."""
    try:
        stmt = select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset.id, DatasetVersion.version_number == version_number
        )
        version_record = (await session.execute(stmt)).scalar_one_or_none()
        if not version_record:
            raise ValueError(f"Version {version_number} not found for this dataset")

        if not os.path.exists(version_record.file_path):
            raise ValueError("Historical snapshot file not found on disk")

        dataset.file_path = version_record.file_path
        dataset.table_name = version_record.table_name
        dataset.row_count = version_record.row_count
        dataset.col_count = version_record.col_count
        dataset.columns = version_record.columns
        dataset.schema_info = version_record.schema_info
        dataset.profile_info = version_record.profile_info
        session.add(dataset)

        await session.commit()
        logger.info(f"Successfully rolled back asynchronously to version {version_number}")
        return version_record
    except Exception as e:
        await session.rollback()
        logger.exception("Failed to rollback dataset version asynchronously")
        raise e
