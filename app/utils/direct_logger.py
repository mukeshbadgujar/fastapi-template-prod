"""
Direct logging utility for ensuring requests are logged to SQLite
without relying on the existing (potentially problematic) logging mechanisms.
"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config.settings import settings
from app.utils.logger import logger

# Get SQLite database path from settings or use default
SQLITE_DB_PATH = settings.API_LOG_SQLITE_PATH or "api_logs.db"


def ensure_sqlite_table_exists():
    """Create the SQLite database and app_requests table if they don't exist"""
    try:
        # Create directory if it doesn't exist
        db_dir = Path(SQLITE_DB_PATH).parent
        if not db_dir.exists() and str(db_dir) != ".":
            db_dir.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            cursor = conn.cursor()

            # Use the existing app_requests table
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

            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_app_request_id ON app_requests(request_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_app_timestamp ON app_requests(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_app_endpoint ON app_requests(endpoint)')

            conn.commit()
            logger.info(f"SQLite database initialized at {SQLITE_DB_PATH}")

        return True
    except Exception as e:
        logger.error(f"Failed to create SQLite table: {str(e)}")
        return False


# Initialize on module load
SQLITE_INITIALIZED = ensure_sqlite_table_exists()


def log_request_direct(request_id, endpoint, method, path, response, response_body, status_code, client_ip=None, user_agent=None,
                      request_query_params=None, request_body=None, request_headers=None, execution_time_ms=0, error_message=None):
    """
    Log a request directly to SQLite with minimal processing
    to avoid any potential issues in the main logging system.
    """
    if not SQLITE_INITIALIZED:
        return False

    try:
        # Get response body as text
        response_headers = "{}"

        # Get response headers if available
        if response and hasattr(response, "headers"):
            try:
                response_headers = json.dumps(dict(response.headers))
            except Exception as e:
                logger.error(f"Error getting response headers: {str(e)}")

        # Handle request data
        if request_query_params is None:
            request_query_params = {}
        if request_body is None:
            request_body = {}
        if request_headers is None:
            request_headers = {}

        # Serialize JSON fields
        try:
            query_params_json = json.dumps(request_query_params)
            request_body_json = json.dumps(request_body)
            request_headers_json = json.dumps(request_headers)
            response_body = json.dumps(response_body)
        except Exception as e:
            logger.error(f"Error serializing request data: {str(e)}")
            query_params_json = "{}"
            request_body_json = "{}"
            request_headers_json = "{}"
            response_body = "{}"


        # Connect to DB and insert record
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            cursor = conn.cursor()

            # Use the existing app_requests table with its required fields
            cursor.execute(
                '''
                INSERT INTO app_requests
                (request_id, endpoint, method, request_path, response_body, status_code,
                 client_ip, user_agent, request_query_params, request_body,
                 request_headers, response_headers, execution_time_ms, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    request_id,
                    endpoint,
                    method,
                    path,
                    response_body,
                    status_code,
                    client_ip or "",
                    user_agent or "",
                    query_params_json,
                    request_body_json,
                    request_headers_json,
                    response_headers,
                    execution_time_ms,
                    error_message or "",
                    datetime.now().isoformat()
                )
            )
            conn.commit()
            logger.info(f"Successfully logged request to app_requests: {endpoint}")

        return True
    except Exception as e:
        logger.error(f"Failed to log request directly: {str(e)}")
        return False


def get_logged_requests(limit=10):
    """Get the most recent directly logged requests for diagnostic purposes"""
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT request_id, endpoint, method, response_body, timestamp FROM app_requests ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return rows
    except Exception as e:
        logger.error(f"Failed to get logged requests: {str(e)}")
        return []


def get_app_request_logs(limit=10, with_body=False, refresh=True):
    """
    Get app request logs in a more detailed format with optional body content

    Args:
        limit: Maximum number of records to return
        with_body: Whether to include request and response bodies
        refresh: Whether to refresh the connection to ensure we get the latest logs

    Returns:
        List of dictionaries containing log data
    """
    try:
        conn = None
        try:
            # Close and reopen connection if refresh is True to ensure fresh data
            if refresh:
                conn = sqlite3.connect(SQLITE_DB_PATH, uri=True)
            else:
                conn = sqlite3.connect(SQLITE_DB_PATH)

            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()

            if with_body:
                # Get all fields
                cursor.execute(
                    """
                    SELECT
                        request_id, endpoint, method, client_ip, user_agent,
                        request_path, request_query_params, request_body,
                        response_body, status_code, execution_time_ms,
                        error_message, timestamp
                    FROM app_requests
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit,)
                )
            else:
                # Get fields except bodies
                cursor.execute(
                    """
                    SELECT
                        request_id, endpoint, method, client_ip, user_agent,
                        request_path, request_query_params, status_code,
                        execution_time_ms, error_message, timestamp
                    FROM app_requests
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit,)
                )

            # Convert to list of dicts
            rows = cursor.fetchall()
            result = []

            for row in rows:
                row_dict = dict(row)

                # Parse JSON strings
                if 'request_query_params' in row_dict and row_dict['request_query_params']:
                    try:
                        row_dict['request_query_params'] = json.loads(row_dict['request_query_params'])
                    except:
                        pass

                if with_body:
                    if 'request_body' in row_dict and row_dict['request_body']:
                        try:
                            row_dict['request_body'] = json.loads(row_dict['request_body'])
                        except:
                            pass

                    if 'response_body' in row_dict and row_dict['response_body']:
                        try:
                            row_dict['response_body'] = json.loads(row_dict['response_body'])
                        except:
                            pass

                result.append(row_dict)
        finally:
            if conn:
                conn.close()

        return result
    except Exception as e:
        logger.error(f"Failed to get app request logs: {str(e)}")
        return []
