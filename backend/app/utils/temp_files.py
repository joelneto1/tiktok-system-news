import shutil
import tempfile
import uuid
from pathlib import Path
from types import TracebackType

from app.utils.logger import logger

_JOBS_ROOT = Path(tempfile.gettempdir()) / "jobs"


class TempDir:
    """Context manager (sync & async) that provisions a temporary directory
    under ``/tmp/jobs/{job_id}/`` and removes it on exit.

    Usage (async)::

        async with TempDir() as td:
            path: Path = td.path
            # write files into path ...

    Usage (sync)::

        with TempDir(job_id="my-run") as td:
            ...
    """

    def __init__(self, job_id: str | None = None) -> None:
        self.job_id = job_id or uuid.uuid4().hex
        self.path: Path = _JOBS_ROOT / self.job_id

    # ── sync context manager ──────────────────────────────────────────

    def __enter__(self) -> "TempDir":
        self.path.mkdir(parents=True, exist_ok=True)
        logger.debug("Created temp dir: {p}", p=self.path)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._cleanup()

    # ── async context manager ─────────────────────────────────────────

    async def __aenter__(self) -> "TempDir":
        self.path.mkdir(parents=True, exist_ok=True)
        logger.debug("Created temp dir: {p}", p=self.path)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._cleanup()

    # ── internal ──────────────────────────────────────────────────────

    def _cleanup(self) -> None:
        if self.path.exists():
            shutil.rmtree(self.path, ignore_errors=True)
            logger.debug("Removed temp dir: {p}", p=self.path)


__all__ = ["TempDir"]
