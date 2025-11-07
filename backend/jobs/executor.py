"""Job executor for AIrsenal CLI commands."""
import os
import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from config import config
from utils.logging import get_logger
from utils.encryption import decrypt_secret
from .parser import output_parser

logger = get_logger(__name__)


class JobExecutionError(Exception):
    """Exception raised when job execution fails."""
    pass


class JobExecutor:
    """Execute AIrsenal CLI commands."""

    ALLOWED_SECRET_KEYS = {
        "APP_ADMIN_EMAIL", "APP_ADMIN_PASSWORD_HASH",
        "FPL_TEAM_ID", "FPL_LOGIN", "FPL_PASSWORD", "AIRSENAL_HOME"
    }

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.active_process: Optional[asyncio.subprocess.Process] = None

    async def _hydrate_local_db(self, job_id: str) -> None:
        """
        Hydrate local database from persistent storage.

        Args:
            job_id: Job identifier for logging

        Raises:
            JobExecutionError: If hydration fails
        """
        try:
            if Path(config.PERSISTENT_DB_PATH).exists():
                shutil.copyfile(config.PERSISTENT_DB_PATH, config.LOCAL_DB_PATH)
                logger.info(
                    f"Hydrated local DB from persistent storage",
                    extra={'job_id': job_id, 'source': config.PERSISTENT_DB_PATH}
                )
            else:
                logger.info(
                    f"No persisted DB found; starting fresh local DB",
                    extra={'job_id': job_id}
                )
        except Exception as exc:
            logger.error(
                f"DB hydration failed: {exc}",
                extra={'job_id': job_id},
                exc_info=True
            )
            raise JobExecutionError(f"Failed to hydrate database: {exc}")

    async def _persist_sqlite(self, job_id: str) -> None:
        """
        Persist local database to persistent storage.

        Args:
            job_id: Job identifier for logging

        Raises:
            JobExecutionError: If persistence fails
        """
        try:
            if not Path(config.LOCAL_DB_PATH).exists():
                logger.warning(
                    f"No local DB to persist (skipping)",
                    extra={'job_id': job_id}
                )
                return

            Path(config.PERSISTENT_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
            tmp_target = f"{config.PERSISTENT_DB_PATH}.tmp"
            shutil.copyfile(config.LOCAL_DB_PATH, tmp_target)

            with open(tmp_target, 'rb') as handle:
                os.fsync(handle.fileno())

            os.replace(tmp_target, config.PERSISTENT_DB_PATH)
            logger.info(
                f"Persisted DB to storage",
                extra={'job_id': job_id, 'target': config.PERSISTENT_DB_PATH}
            )
        except Exception as exc:
            logger.error(
                f"DB persistence failed: {exc}",
                extra={'job_id': job_id},
                exc_info=True
            )
            raise JobExecutionError(f"Failed to persist database: {exc}")

    async def _get_secrets(self) -> Dict[str, str]:
        """
        Fetch and decrypt secrets from database.

        Returns:
            Dictionary of secret key-value pairs

        Raises:
            JobExecutionError: If secret retrieval fails
        """
        try:
            secrets = await self.db.secrets.find(
                {"key": {"$in": list(self.ALLOWED_SECRET_KEYS)}}
            ).to_list(None)

            env_vars = {}
            for secret in secrets:
                if secret["key"] in ["FPL_TEAM_ID", "FPL_LOGIN", "FPL_PASSWORD", "AIRSENAL_HOME"]:
                    try:
                        # Decrypt secret value
                        decrypted_value = decrypt_secret(secret["value"])
                        env_vars[secret["key"]] = decrypted_value
                    except Exception as e:
                        logger.error(
                            f"Failed to decrypt secret {secret['key']}: {e}",
                            exc_info=True
                        )
                        # Try using the value as-is (for backwards compatibility)
                        env_vars[secret["key"]] = secret["value"]

            logger.debug(f"Retrieved {len(env_vars)} secrets")
            return env_vars
        except Exception as exc:
            logger.error(f"Failed to get secrets: {exc}", exc_info=True)
            raise JobExecutionError(f"Failed to retrieve secrets: {exc}")

    def _build_command(self, command: str, parameters: Dict[str, Any]) -> List[str]:
        """
        Build command line arguments.

        Args:
            command: Command type
            parameters: Command parameters

        Returns:
            Command line arguments

        Raises:
            JobExecutionError: If command is invalid
        """
        cmd_parts: List[str] = []

        if command == "setup_db":
            cmd_parts = ["airsenal_setup_initial_db"]
        elif command == "update_db":
            cmd_parts = ["airsenal_update_db"]
        elif command == "predict":
            weeks = parameters.get("weeks_ahead", 3)
            cmd_parts = ["airsenal_run_prediction", "--weeks_ahead", str(weeks)]
        elif command == "optimize":
            weeks = parameters.get("weeks_ahead", 3)
            cmd_parts = ["airsenal_run_optimization", "--weeks_ahead", str(weeks)]
            if parameters.get("wildcard_week"):
                cmd_parts += ["--wildcard_week", str(parameters["wildcard_week"])]
            if parameters.get("free_hit_week"):
                cmd_parts += ["--free_hit_week", str(parameters["free_hit_week"])]
            if parameters.get("triple_captain_week"):
                cmd_parts += ["--triple_captain_week", str(parameters["triple_captain_week"])]
            if parameters.get("bench_boost_week"):
                cmd_parts += ["--bench_boost_week", str(parameters["bench_boost_week"])]
        elif command == "pipeline":
            cmd_parts = ["airsenal_run_pipeline"]
        else:
            raise JobExecutionError(f"Unknown command: {command}")

        logger.debug(f"Built command: {' '.join(cmd_parts)}")
        return cmd_parts

    async def execute(
        self,
        job_id: str,
        command: str,
        parameters: Dict[str, Any],
        log_callback: Optional[callable] = None
    ) -> tuple[List[str], int]:
        """
        Execute a job command.

        Args:
            job_id: Job identifier
            command: Command type
            parameters: Command parameters
            log_callback: Optional callback for log messages

        Returns:
            Tuple of (logs, return_code)

        Raises:
            JobExecutionError: If execution fails
        """
        logger.info(
            f"Starting job execution",
            extra={'job_id': job_id, 'command': command, 'parameters': parameters}
        )

        try:
            # Get secrets
            secret_env_vars = await self._get_secrets()
            env_vars = os.environ.copy()
            env_vars.update(secret_env_vars)
            env_vars.setdefault("AIRSENAL_HOME", "/data/airsenal")
            env_vars["AIRSENAL_DB_FILE"] = config.LOCAL_DB_PATH

            # Build command
            cmd_parts = self._build_command(command, parameters)

            # Log command
            if log_callback:
                await log_callback(f"Executing: {' '.join(cmd_parts)}")

            # Hydrate database
            await self._hydrate_local_db(job_id)
            if log_callback:
                await log_callback(f"Database hydrated")

            # Execute command
            captured_logs: List[str] = []
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env_vars,
            )
            self.active_process = process

            try:
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace").rstrip()
                    captured_logs.append(decoded)

                    # Limit log size
                    if len(captured_logs) > config.MAX_LOG_LINES:
                        captured_logs.pop(0)

                    if log_callback:
                        await log_callback(decoded)
            finally:
                await process.wait()
                self.active_process = None

            returncode = process.returncode
            logger.info(
                f"Job execution completed",
                extra={'job_id': job_id, 'return_code': returncode}
            )

            return captured_logs, returncode

        except asyncio.CancelledError:
            logger.warning(f"Job execution cancelled", extra={'job_id': job_id})
            if self.active_process:
                try:
                    self.active_process.terminate()
                    await asyncio.wait_for(self.active_process.wait(), timeout=5)
                except Exception as e:
                    logger.error(f"Failed to terminate process: {e}", extra={'job_id': job_id})
            raise
        except JobExecutionError:
            raise
        except Exception as exc:
            logger.error(
                f"Job execution failed: {exc}",
                extra={'job_id': job_id},
                exc_info=True
            )
            raise JobExecutionError(f"Execution failed: {exc}")

    async def parse_output(
        self,
        command: str,
        parameters: Dict[str, Any],
        logs: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse command output.

        Args:
            command: Command type
            parameters: Command parameters
            logs: Command output logs

        Returns:
            Parsed output or None
        """
        return output_parser.parse(command, parameters, logs)

    def terminate(self):
        """Terminate the active process."""
        if self.active_process:
            try:
                self.active_process.terminate()
                logger.info("Process terminated")
            except ProcessLookupError:
                logger.warning("Process already terminated")
            except Exception as e:
                logger.error(f"Failed to terminate process: {e}", exc_info=True)
