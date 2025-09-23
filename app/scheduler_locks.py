import threading
import time
from typing import Dict, Tuple

_locks: Dict[Tuple[str, str], Tuple[threading.Lock, float]] = {}
_TTL = 120  # segundos

def acquire_lock(key: Tuple[str, str]) -> bool:
    """Tenta adquirir um lock para uma chave (source, section). Retorna True se bem-sucedido."""
    now = time.time()
    lock, ts = _locks.get(key, (threading.Lock(), 0))
    _locks[key] = (lock, now)
    got = lock.acquire(blocking=False)
    # Limpa travas antigas para evitar memory leak
    for k, (lk, t) in list(_locks.items()):
        if now - t > _TTL and not lk.locked():
            _locks.pop(k, None)
    return got

def release_lock(key: Tuple[str, str]):
    """Libera o lock para uma chave."""
    pair = _locks.get(key)
    if pair:
        pair[0].release()