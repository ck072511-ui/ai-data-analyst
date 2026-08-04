import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.core.cache import CacheManager
from app.utils.crypto import decrypt_password

logger = logging.getLogger(__name__)


class ConnectionManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(ConnectionManager, cls).__new__(cls, *args, **kwargs)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.engines: Dict[str, Engine] = {}
        self.cache = CacheManager()
        self.lock = threading.Lock()
        self._initialized = True

    def sanitize_sqlite_path(self, database_path: str) -> str:
        """Sanitize SQLite database path to prevent directory traversal outside the workspace."""
        cwd = Path.cwd().resolve()

        # Remove drive letters (e.g., C:/) and leading slashes
        cleaned = re.sub(r"^[a-zA-Z]:[\\/]", "", database_path)
        cleaned = cleaned.lstrip("\\/")
        # Prevent parent directory traversal
        cleaned = re.sub(r"\.\.+", ".", cleaned).strip()

        # Resolve path relative to current working directory
        target_path = (cwd / cleaned).resolve()

        # If it resolved inside the workspace, it's safe
        if target_path.as_posix().startswith(cwd.as_posix()):
            return str(target_path)

        # Fallback to backend/data directory inside the workspace
        fallback_dir = (cwd / "backend" / "data").resolve()
        os.makedirs(fallback_dir, exist_ok=True)
        return str((fallback_dir / Path(cleaned).name).resolve())

    def build_connection_string(
        self,
        db_type: str,
        host: Optional[str],
        port: Optional[int],
        database: str,
        username: Optional[str],
        password: Optional[str],
    ) -> str:
        """Build SQLAlchemy connection string safely."""
        db_type = db_type.lower()
        if db_type == "sqlite":
            clean_path = self.sanitize_sqlite_path(database)
            return f"sqlite:///{clean_path}"

        escaped_password = quote_plus(password) if password else ""
        port_part = f":{port}" if port else ""

        if db_type == "postgresql":
            return f"postgresql://{username}:{escaped_password}@{host}{port_part}/{database}"
        elif db_type == "mysql":
            return f"mysql+pymysql://{username}:{escaped_password}@{host}{port_part}/{database}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    def get_engine(self, connection_id: str, db_conn) -> Engine:
        """Get or create cached SQLAlchemy engine for a database connection."""
        with self.lock:
            if connection_id in self.engines:
                return self.engines[connection_id]

            decrypted_pw = decrypt_password(db_conn.encrypted_password) if db_conn.encrypted_password else ""
            url = self.build_connection_string(
                db_conn.db_type, db_conn.host, db_conn.port, db_conn.database, db_conn.username, decrypted_pw
            )

            db_type = db_conn.db_type.lower()
            if db_type == "sqlite":
                # SQLite pooling and timeout configuration
                engine = create_engine(url, connect_args={"timeout": 5}, pool_recycle=1800)
            else:
                # Enterprise database connection pooling and timeout configuration
                engine = create_engine(
                    url,
                    connect_args={"connect_timeout": 5},
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=10,
                    pool_recycle=1800,
                )

            self.engines[connection_id] = engine
            logger.info(f"Created connection pool for database connection {connection_id} ({db_conn.name})")
            return engine

    def remove_engine(self, connection_id: str):
        """Dispose and remove engine from cache registry."""
        with self.lock:
            if connection_id in self.engines:
                try:
                    self.engines[connection_id].dispose()
                    logger.info(f"Disposed engine for connection {connection_id}")
                except Exception as e:
                    logger.error(f"Error disposing engine {connection_id}: {e}")
                del self.engines[connection_id]

    async def clear_schema_cache(self, connection_id: str):
        """Clear cached database schema metadata."""
        cache_key = f"db_schema:{connection_id}"
        await self.cache.delete(cache_key)
        logger.info(f"Cleared schema cache for connection {connection_id}")

    async def test_connection(
        self,
        db_type: str,
        host: Optional[str],
        port: Optional[int],
        database: str,
        username: Optional[str],
        password: Optional[str],
    ) -> Tuple[bool, str]:
        """Test database connectivity synchronously (run inside thread pool)."""
        try:
            url = self.build_connection_string(db_type, host, port, database, username, password)
            db_type = db_type.lower()
            connect_args = {"timeout": 5} if db_type == "sqlite" else {"connect_timeout": 5}

            # Temporary engine for testing
            engine = create_engine(url, connect_args=connect_args)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return True, "Connection successful"
        except Exception as e:
            logger.warning(f"Connection test failed for {db_type}://{host}: {str(e)}")
            # Make the error message cleaner and more user-friendly
            err_msg = str(e)
            if "Authentication failed" in err_msg or "password authentication failed" in err_msg:
                err_msg = "Invalid credentials. Password authentication failed."
            elif "Connection refused" in err_msg or "Can't connect to" in err_msg:
                err_msg = "Could not connect to database server. Host or port might be incorrect."
            elif "database does not exist" in err_msg or "unknown database" in err_msg:
                err_msg = f"Database '{database}' does not exist on the server."
            return False, err_msg

    async def get_schema(
        self, connection_id: str, db_conn, force_refresh: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve schema, utilizing CacheManager for caching."""
        cache_key = f"db_schema:{connection_id}"

        if not force_refresh:
            cached_schema = await self.cache.get(cache_key)
            if cached_schema:
                logger.info(f"Returned cached schema for connection {connection_id}")
                return cached_schema

        engine = self.get_engine(connection_id, db_conn)

        def run_inspect():
            inspector = inspect(engine)
            schema = {}
            for table_name in inspector.get_table_names():
                cols = []
                for col in inspector.get_columns(table_name):
                    cols.append({"name": col["name"], "type": str(col["type"]), "nullable": col.get("nullable", True)})
                schema[table_name] = cols
            return schema

        try:

            from fastapi.concurrency import run_in_threadpool

            schema_data = await run_in_threadpool(run_inspect)

            # Store schema metadata in cache for 1 hour
            await self.cache.set(cache_key, schema_data, expire=3600)
            return schema_data
        except Exception as e:
            logger.error(f"Failed to inspect database connection {connection_id}: {e}")
            raise e
