import json
import sqlite3
from pathlib import Path

from app.common.db_logging.base import BaseDBLogger
from app.config.settings import settings
from app.models.models_request_response import ApiCallLog, AppRequestLog
from app.utils.logger import logger


class SQLiteLogger(BaseDBLogger):
    """SQLite logger implementation"""

    def __init__(self, db_path: str = None):
        self._conn = None
        self._db_path = db_path or settings.API_LOG_SQLITE_PATH or "api_logs.db"
        self._init_db()

    def is_available(self) -> bool:
        """SQLite is available if it's enabled in settings"""
        return settings.API_LOG_SQLITE_ENABLED or settings.API_LOG_FALLBACK_ENABLED

    def _init_db(self):
        """Initialize SQLite database and create table if not exists"""
        try:
            # Create directory if it doesn't exist
            db_dir = Path(self._db_path).parent
            if not db_dir.exists() and str(db_dir) != ".":
                db_dir.mkdir(parents=True, exist_ok=True)

            self._conn = sqlite3.connect(self._db_path)
            cursor = self._conn.cursor()

            # Create table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    endpoint TEXT,
                    method TEXT,
                    partner_journey_id TEXT,
                    account_id TEXT,
                    application_id TEXT,
                    request_body TEXT,
                    request_headers TEXT,
                    response_body TEXT,
                    response_headers TEXT,
                    status_code INTEGER,
                    status TEXT,
                    execution_time_ms REAL,
                    error_message TEXT,
                    timestamp TEXT,
                    vendor TEXT,
                    fallback_used INTEGER
                )
            ''')

            # Create app_requests table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    endpoint TEXT,
                    method TEXT,
                    client_ip TEXT,
                    user_agent TEXT,
                    user_id TEXT,
                    request_path TEXT,
                    request_query_params TEXT,
                    request_body TEXT,
                    request_headers TEXT,
                    response_body TEXT,
                    response_headers TEXT,
                    status_code INTEGER,
                    execution_time_ms REAL,
                    error_message TEXT,
                    timestamp TEXT
                )
            ''')

            # Create indexes for better query performance - each in a separate execute call
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_request_id ON api_calls(request_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON api_calls(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vendor ON api_calls(vendor)')

            # Create indexes for app_requests
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_app_request_id ON app_requests(request_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_app_timestamp ON app_requests(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_app_endpoint ON app_requests(endpoint)')

            self._conn.commit()
            logger.info(f"SQLite database initialized at {self._db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {str(e)}", exc_info=True)

    def _get_conn(self):
        """Get or create SQLite connection"""
        if self._conn is None:
            self._init_db()
        return self._conn

    async def log_api_call(self, log_data: ApiCallLog) -> None:
        """Log API call to SQLite"""
        try:
            if conn := self._get_conn():
                cursor = conn.cursor()

                # Create a complete dictionary with all required fields
                log_dict = {
                    "request_id": log_data.request_id,
                    "endpoint": log_data.endpoint,
                    "method": log_data.method,
                    "partner_journey_id": log_data.partner_journey_id or "",
                    "account_id": log_data.account_id or "",
                    "application_id": log_data.application_id or "",
                    "request_body": json.dumps(log_data.request_body or {}),
                    "request_headers": json.dumps(log_data.request_headers or {}),
                    "response_body": json.dumps(log_data.response_body or {}),
                    "response_headers": json.dumps(log_data.response_headers or {}),
                    "status_code": log_data.status_code or 0,
                    "status": log_data.status,
                    "execution_time_ms": log_data.execution_time_ms,
                    "error_message": log_data.error_message or "",
                    "timestamp": log_data.timestamp.isoformat(),
                    "vendor": log_data.vendor or "",
                    "fallback_used": 1 if log_data.fallback_used else 0
                }

                # Insert into SQLite
                cursor.execute('''
                    INSERT INTO api_calls (
                        request_id, endpoint, method, partner_journey_id,
                        account_id, application_id, request_body, request_headers,
                        response_body, response_headers, status_code, status,
                        execution_time_ms, error_message, timestamp, vendor,
                        fallback_used
                    ) VALUES (
                        :request_id, :endpoint, :method, :partner_journey_id,
                        :account_id, :application_id, :request_body, :request_headers,
                        :response_body, :response_headers, :status_code, :status,
                        :execution_time_ms, :error_message, :timestamp, :vendor,
                        :fallback_used
                    )
                ''', log_dict)
                conn.commit()
                logger.info(f"Logged API call to SQLite: {log_data.endpoint}")
        except Exception as e:
            logger.error(f"Failed to log API call to SQLite: {str(e)}", exc_info=True)

    async def log_app_request(self, log_data: AppRequestLog) -> None:
        """Log application request to SQLite"""
        try:
            if conn := self._get_conn():
                cursor = conn.cursor()

                # Create a complete dictionary with all required fields
                log_dict = {
                    "request_id": log_data.request_id,
                    "endpoint": log_data.endpoint,
                    "method": log_data.method,
                    "client_ip": log_data.client_ip or "",
                    "user_agent": log_data.user_agent or "",
                    "user_id": log_data.user_id or "",
                    "request_path": log_data.request_path,
                    "request_query_params": json.dumps(log_data.request_query_params or {}),
                    "request_body": json.dumps(log_data.request_body or {}),
                    "request_headers": json.dumps(log_data.request_headers or {}),
                    "response_body": json.dumps(log_data.response_body or {}),
                    "response_headers": json.dumps(log_data.response_headers or {}),
                    "status_code": log_data.status_code,
                    "execution_time_ms": log_data.execution_time_ms,
                    "error_message": log_data.error_message or "",
                    "timestamp": log_data.timestamp.isoformat()
                }

                # Insert into SQLite
                cursor.execute('''
                    INSERT INTO app_requests (
                        request_id, endpoint, method, client_ip,
                        user_agent, user_id, request_path, request_query_params,
                        request_body, request_headers, response_body, response_headers,
                        status_code, execution_time_ms, error_message, timestamp
                    ) VALUES (
                        :request_id, :endpoint, :method, :client_ip,
                        :user_agent, :user_id, :request_path, :request_query_params,
                        :request_body, :request_headers, :response_body, :response_headers,
                        :status_code, :execution_time_ms, :error_message, :timestamp
                    )
                ''', log_dict)
                conn.commit()
                logger.info(f"Logged application request to SQLite: {log_data.endpoint}")
        except Exception as e:
            logger.error(f"Failed to log application request to SQLite: {str(e)}", exc_info=True)

    async def close(self) -> None:
        """Close SQLite connection"""
        if self._conn:
            self._conn.close()
            self._conn = None
