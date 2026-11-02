"""E4 - Concurrent Stock & Resource Engine (basic)
Student D: Swayambu V B (01FE24BCS102)
A lock (mutual exclusion) stops two orders using the same stock at the same time.
Stock data is read and changed through E3."""

import threading
import e3_integrity as e3

_lock = threading.Lock()


def check(vendor_id, product, qty):
    return e3.get_stock(vendor_id, product) >= qty


def reserve(vendor_id, product, qty):
    """Re-check stock and reduce it inside the lock (critical section)."""
    with _lock:
        if not e3.reduce_stock(vendor_id, product, qty):
            raise ValueError("Stock changed: not enough stock left for this order")


def release(vendor_id, product, qty):
    """Put stock back if something fails later."""
    with _lock:
        e3.add_stock(vendor_id, product, qty)
