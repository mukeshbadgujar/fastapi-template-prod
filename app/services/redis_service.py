"""
Redis configuration service for JSON-based config management
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import aioredis
from aioredis import Redis

from app.config.settings import settings
from app.utils.logger import logger


class RedisConfigService:
    """
    Service for Redis-based configuration management using JSON files
    """

    def __init__(self):
        self.redis: Optional[Redis] = None
        self.config_namespace = f"config:{settings.ENV}"
        self.config_dir = Path("config/redis")
        self.config_file = self.config_dir / f"{settings.ENV}_redis_config.json"
        self._config_cache: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize Redis connection and load configuration"""
        try:
            # Connect to Redis
            if settings.REDIS_URL:
                self.redis = await aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=10
                )
            else:
                logger.warning("REDIS_URL not configured, Redis service disabled")
                return False

            # Test connection
            await self.redis.ping()

            # Load configuration from JSON file
            await self.load_config_from_file()

            logger.info(
                "Redis configuration service initialized",
                extra={
                    "event_type": "redis_service_initialized",
                    "config_namespace": self.config_namespace,
                    "config_file": str(self.config_file),
                    "redis_url": settings.REDIS_URL
                }
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to initialize Redis service: {e}",
                extra={
                    "event_type": "redis_service_init_failed",
                    "error": str(e)
                }
            )
            return False

    async def load_config_from_file(self) -> bool:
        """Load configuration from JSON file into Redis"""
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Create default config file if it doesn't exist
            if not self.config_file.exists():
                await self._create_default_config_file()

            # Load configuration from file
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)

            # Store in Redis with namespace
            config_count = 0
            for key, value in config_data.items():
                redis_key = f"{self.config_namespace}:{key}"
                if isinstance(value, (dict, list)):
                    await self.redis.set(redis_key, json.dumps(value))
                else:
                    await self.redis.set(redis_key, str(value))

                # Cache locally for faster access
                self._config_cache[key] = value
                config_count += 1

            logger.info(
                "Configuration loaded from file to Redis",
                extra={
                    "event_type": "config_loaded_from_file",
                    "config_file": str(self.config_file),
                    "config_count": config_count,
                    "environment": settings.ENV
                }
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to load configuration from file: {e}",
                extra={
                    "event_type": "config_load_failed",
                    "config_file": str(self.config_file),
                    "error": str(e)
                }
            )
            return False

    async def _create_default_config_file(self):
        """Create a default configuration file for the environment"""
        default_config = {
            "app": {
                "name": "FastAPI Production Template",
                "version": "1.0.0",
                "debug": settings.ENV == "dev"
            },
            "features": {
                "user_registration": True,
                "api_key_creation": True,
                "email_verification": settings.ENV == "prod",
                "rate_limiting": True,
                "metrics_collection": True
            },
            "rate_limits": {
                "api_requests_per_minute": 1000,
                "login_attempts_per_hour": 5,
                "api_key_requests_per_minute": 100,
                "registration_per_day": 10
            },
            "security": {
                "password_min_length": 8,
                "session_timeout_minutes": 30,
                "max_login_attempts": 5,
                "account_lockout_minutes": 15
            },
            "external_apis": {
                "openweather": {
                    "enabled": True,
                    "timeout_seconds": 10,
                    "retry_attempts": 3
                }
            },
            "notifications": {
                "email_enabled": settings.ENV == "prod",
                "slack_enabled": False,
                "webhook_enabled": False
            },
            "monitoring": {
                "health_check_interval_seconds": 30,
                "performance_metrics": True,
                "error_tracking": True,
                "request_logging": True
            }
        }

        # Environment-specific overrides
        if settings.ENV == "dev":
            default_config["rate_limits"]["api_requests_per_minute"] = 10000
            default_config["security"]["max_login_attempts"] = 10
        elif settings.ENV == "prod":
            default_config["rate_limits"]["api_requests_per_minute"] = 500
            default_config["security"]["max_login_attempts"] = 3

        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)

        logger.info(
            "Default configuration file created",
            extra={
                "event_type": "default_config_created",
                "config_file": str(self.config_file),
                "environment": settings.ENV
            }
        )

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        if not self.redis:
            return self._config_cache.get(key, default)

        try:
            # Try cache first
            if key in self._config_cache:
                return self._config_cache[key]

            # Get from Redis
            redis_key = f"{self.config_namespace}:{key}"
            value = await self.redis.get(redis_key)

            if value is None:
                return default

            # Try to parse as JSON, fallback to string
            try:
                parsed_value = json.loads(value)
                self._config_cache[key] = parsed_value
                return parsed_value
            except json.JSONDecodeError:
                self._config_cache[key] = value
                return value

        except Exception as e:
            logger.error(
                f"Failed to get config value: {e}",
                extra={
                    "event_type": "config_get_failed",
                    "key": key,
                    "error": str(e)
                }
            )
            return default

    async def set(self, key: str, value: Any) -> bool:
        """Set a configuration value"""
        if not self.redis:
            self._config_cache[key] = value
            return True

        try:
            redis_key = f"{self.config_namespace}:{key}"

            if isinstance(value, (dict, list)):
                await self.redis.set(redis_key, json.dumps(value))
            else:
                await self.redis.set(redis_key, str(value))

            # Update cache
            self._config_cache[key] = value

            logger.debug(
                "Configuration value set",
                extra={
                    "event_type": "config_set",
                    "key": key,
                    "value_type": type(value).__name__
                }
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to set config value: {e}",
                extra={
                    "event_type": "config_set_failed",
                    "key": key,
                    "error": str(e)
                }
            )
            return False

    async def exists(self, key: str) -> bool:
        """Check if a configuration key exists"""
        if not self.redis:
            return key in self._config_cache

        try:
            redis_key = f"{self.config_namespace}:{key}"
            result = await self.redis.exists(redis_key)
            return bool(result)

        except Exception as e:
            logger.error(
                f"Failed to check config key existence: {e}",
                extra={
                    "event_type": "config_exists_failed",
                    "key": key,
                    "error": str(e)
                }
            )
            return False

    async def delete(self, key: str) -> bool:
        """Delete a configuration key"""
        if not self.redis:
            self._config_cache.pop(key, None)
            return True

        try:
            redis_key = f"{self.config_namespace}:{key}"
            result = await self.redis.delete(redis_key)

            # Remove from cache
            self._config_cache.pop(key, None)

            logger.info(
                "Configuration key deleted",
                extra={
                    "event_type": "config_deleted",
                    "key": key
                }
            )

            return bool(result)

        except Exception as e:
            logger.error(
                f"Failed to delete config key: {e}",
                extra={
                    "event_type": "config_delete_failed",
                    "key": key,
                    "error": str(e)
                }
            )
            return False

    async def get_all_keys(self, pattern: str = "*") -> List[str]:
        """Get all configuration keys matching a pattern"""
        if not self.redis:
            return [k for k in self._config_cache.keys() if pattern == "*" or pattern in k]

        try:
            redis_pattern = f"{self.config_namespace}:{pattern}"
            keys = await self.redis.keys(redis_pattern)

            # Remove namespace prefix
            return [key.replace(f"{self.config_namespace}:", "") for key in keys]

        except Exception as e:
            logger.error(
                f"Failed to get config keys: {e}",
                extra={
                    "event_type": "config_keys_failed",
                    "pattern": pattern,
                    "error": str(e)
                }
            )
            return []

    async def get_feature_flag(self, feature: str, default: bool = False) -> bool:
        """Get a feature flag value"""
        feature_flags = await self.get("features", {})
        return feature_flags.get(feature, default)

    async def get_rate_limit(self, limit_type: str, default: int = 100) -> int:
        """Get a rate limit value"""
        rate_limits = await self.get("rate_limits", {})
        return rate_limits.get(limit_type, default)

    async def reload_from_file(self) -> bool:
        """Reload configuration from file (useful for the /reload-config endpoint)"""
        logger.info(
            "Reloading configuration from file",
            extra={
                "event_type": "config_reload_requested",
                "config_file": str(self.config_file)
            }
        )

        # Clear cache
        self._config_cache.clear()

        # Reload from file
        return await self.load_config_from_file()

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")


# Global Redis configuration service instance
redis_config = RedisConfigService()
