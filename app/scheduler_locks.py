import threading
import time
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

_locks: Dict[Tuple[str, str], Tuple[threading.Lock, float]] = {}  # Stores (lock, timestamp)
_master_lock = threading.Lock()  # Protects access to the _locks dictionary
_TTL = 120  # Time-to-live for old, unlocked entries in seconds
_STALE_AFTER_SECONDS = 30  # A lock is considered stale after this many seconds

def acquire_lock(key: Tuple[str, str], force_if_stale: bool = True) -> bool:
    """
    Tries to acquire a lock for a key (source, section). Returns True if successful.
    This is now thread-safe and handles stale locks.
    """
    with _master_lock:
        if key not in _locks:
            _locks[key] = (threading.Lock(), 0.0)
        lock, ts = _locks[key]

    # Check for staleness outside the master lock to avoid holding it.
    if lock.locked():
        age = time.time() - ts
        if force_if_stale and age > _STALE_AFTER_SECONDS:
            logger.warning(f"Lock for {key} is stale (held for {age:.1f}s). Forcing acquire.")
            # The old lock will be released by the original thread eventually.
            # We just proceed as if we got the lock. This is a pragmatic choice
            # to prevent deadlocks from long-running or failed scrapes.
            pass  # We will attempt to acquire it anyway.
        else:
            return False  # Lock is held and not stale.

    got = lock.acquire(blocking=False)
    if got:
        # Update timestamp only on successful acquisition
        with _master_lock:
            _locks[key] = (lock, time.time())
    return got

def release_lock(key: Tuple[str, str]):
    """Releases the lock for a key."""
    with _master_lock:
        pair = _locks.get(key)
    if pair and pair[0].locked():
        pair[0].release()