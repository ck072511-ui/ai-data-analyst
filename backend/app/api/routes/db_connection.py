import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.connection_manager import ConnectionManager
from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.models.db_connection import DatabaseConnection
from app.utils.crypto import decrypt_password, encrypt_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/database", tags=["Database Connections"])


class ConnectionTestRequest(BaseModel):
    db_type: str = Field(..., description="Database type: postgresql, mysql, sqlite")
    host: Optional[str] = Field(None, description="Database host address")
    port: Optional[int] = Field(None, description="Database port number")
    database: str = Field(..., description="Database name or SQLite file path")
    username: Optional[str] = Field(None, description="Database login username")
    password: Optional[str] = Field(None, description="Database login password")


class ConnectionCreate(ConnectionTestRequest):
    name: str = Field(..., min_length=1, max_length=100, description="Display name for connection")


class ConnectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Display name for connection")
    db_type: Optional[str] = Field(None, description="Database type: postgresql, mysql, sqlite")
    host: Optional[str] = Field(None, description="Database host address")
    port: Optional[int] = Field(None, description="Database port number")
    database: Optional[str] = Field(None, description="Database name or SQLite file path")
    username: Optional[str] = Field(None, description="Database login username")
    password: Optional[str] = Field(None, description="Database login password")


@router.post("/test")
async def test_connection(request: ConnectionTestRequest, current_user: dict = Depends(get_current_user)):
    if request.db_type not in ["postgresql", "mysql", "sqlite"]:
        raise HTTPException(status_code=400, detail="Only postgresql, mysql, and sqlite are supported.")

    conn_mgr = ConnectionManager()
    success, msg = await conn_mgr.test_connection(
        request.db_type, request.host, request.port, request.database, request.username, request.password
    )
    if not success:
        raise HTTPException(status_code=400, detail=f"Database connection test failed: {msg}")
    return {"success": True, "message": "Database connection successful"}


@router.post("/connect")
async def connect_database(request: ConnectionCreate, current_user: dict = Depends(get_current_user)):
    conn_mgr = ConnectionManager()
    success, msg = await conn_mgr.test_connection(
        request.db_type, request.host, request.port, request.database, request.username, request.password
    )
    if not success:
        raise HTTPException(status_code=400, detail=f"Cannot save connection. Test failed: {msg}")

    encrypted_pw = encrypt_password(request.password) if request.password else None

    async with AsyncSessionLocal() as session:
        db_conn = DatabaseConnection(
            user_id=current_user["id"],
            name=request.name,
            db_type=request.db_type.lower(),
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            encrypted_password=encrypted_pw,
        )
        session.add(db_conn)
        await session.commit()
        await session.refresh(db_conn)

        # Prefetch schema asynchronously to cache it immediately upon successful connection
        try:
            await conn_mgr.get_schema(db_conn.id, db_conn, force_refresh=True)
        except Exception as e:
            logger.warning(f"Failed to prefetch schema for new connection {db_conn.id}: {e}")

        return {
            "id": db_conn.id,
            "name": db_conn.name,
            "db_type": db_conn.db_type,
            "host": db_conn.host,
            "port": db_conn.port,
            "database": db_conn.database,
            "username": db_conn.username,
            "created_at": db_conn.created_at.isoformat(),
        }


@router.get("/list")
async def list_connections(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        stmt = (
            select(DatabaseConnection)
            .where(DatabaseConnection.user_id == user_id)
            .order_by(DatabaseConnection.created_at.desc())
        )
        result = await session.execute(stmt)
        connections = result.scalars().all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "db_type": c.db_type,
                "host": c.host,
                "port": c.port,
                "database": c.database,
                "username": c.username,
                "created_at": c.created_at.isoformat(),
            }
            for c in connections
        ]


@router.get("/{connection_id}/schema")
async def get_connection_schema(
    connection_id: str, refresh: bool = False, current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.id == connection_id, DatabaseConnection.user_id == user_id
        )
        db_conn = (await session.execute(stmt)).scalar_one_or_none()
        if not db_conn:
            raise HTTPException(status_code=404, detail="Connection not found")

        conn_mgr = ConnectionManager()
        try:
            schema_data = await conn_mgr.get_schema(connection_id, db_conn, force_refresh=refresh)
            return {"schema": schema_data}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to inspect database: {str(e)}")


@router.post("/{connection_id}/test")
async def test_existing_connection(connection_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.id == connection_id, DatabaseConnection.user_id == user_id
        )
        db_conn = (await session.execute(stmt)).scalar_one_or_none()
        if not db_conn:
            raise HTTPException(status_code=404, detail="Connection not found")

        decrypted_pw = decrypt_password(db_conn.encrypted_password) if db_conn.encrypted_password else None

        conn_mgr = ConnectionManager()
        success, msg = await conn_mgr.test_connection(
            db_conn.db_type, db_conn.host, db_conn.port, db_conn.database, db_conn.username, decrypted_pw
        )
        if not success:
            raise HTTPException(status_code=400, detail=f"Database connection test failed: {msg}")
        return {"success": True, "message": "Database connection successful"}


@router.put("/{connection_id}")
async def update_connection(
    connection_id: str, request: ConnectionUpdate, current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.id == connection_id, DatabaseConnection.user_id == user_id
        )
        db_conn = (await session.execute(stmt)).scalar_one_or_none()
        if not db_conn:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Merge update details with existing values for testing
        test_db_type = request.db_type if request.db_type is not None else db_conn.db_type
        test_host = request.host if request.host is not None else db_conn.host
        test_port = request.port if request.port is not None else db_conn.port
        test_database = request.database if request.database is not None else db_conn.database
        test_username = request.username if request.username is not None else db_conn.username

        if request.password is not None:
            test_password = request.password
        else:
            test_password = decrypt_password(db_conn.encrypted_password) if db_conn.encrypted_password else None

        conn_mgr = ConnectionManager()
        success, msg = await conn_mgr.test_connection(
            test_db_type, test_host, test_port, test_database, test_username, test_password
        )
        if not success:
            raise HTTPException(status_code=400, detail=f"Cannot update connection. Test failed: {msg}")

        # Update fields in the database
        if request.name is not None:
            db_conn.name = request.name
        if request.db_type is not None:
            db_conn.db_type = request.db_type.lower()
        if request.host is not None:
            db_conn.host = request.host
        if request.port is not None:
            db_conn.port = request.port
        if request.database is not None:
            db_conn.database = request.database
        if request.username is not None:
            db_conn.username = request.username
        if request.password is not None:
            db_conn.encrypted_password = encrypt_password(request.password)

        await session.commit()
        await session.refresh(db_conn)

        # Clear cached engine and schema
        conn_mgr.remove_engine(connection_id)
        await conn_mgr.clear_schema_cache(connection_id)

        # Prefetch new schema asynchronously
        try:
            await conn_mgr.get_schema(connection_id, db_conn, force_refresh=True)
        except Exception as e:
            logger.warning(f"Failed to prefetch schema for updated connection {connection_id}: {e}")

        return {
            "id": db_conn.id,
            "name": db_conn.name,
            "db_type": db_conn.db_type,
            "host": db_conn.host,
            "port": db_conn.port,
            "database": db_conn.database,
            "username": db_conn.username,
            "created_at": db_conn.created_at.isoformat(),
        }


@router.delete("/{connection_id}")
async def delete_connection(connection_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.id == connection_id, DatabaseConnection.user_id == user_id
        )
        connection = (await session.execute(stmt)).scalar_one_or_none()
        if not connection:
            raise HTTPException(status_code=404, detail="Database connection not found")

        await session.delete(connection)
        await session.commit()

        # Cleanup cached engine and schema cache
        conn_mgr = ConnectionManager()
        conn_mgr.remove_engine(connection_id)
        await conn_mgr.clear_schema_cache(connection_id)

        return {"success": True, "message": "Connection configuration deleted successfully"}
