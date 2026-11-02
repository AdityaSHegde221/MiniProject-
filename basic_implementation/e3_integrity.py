"""E3 - Data, Transaction & Integrity Engine (basic)
Student C: Aditya S Hegde (01FE24BCS091)

This is the ONLY engine that talks to PostgreSQL. Other engines call these functions.
It owns: connection, tables, transactions (commit/rollback), orders, receipts,
invoices, payments, the 3-way match and the audit log."""
import os
from contextlib import contextmanager
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

# Change this or set the DATABASE_URL environment variable
DEFAULT_URL = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/procureflow"
_conn = None


# ---------- connection and transactions ----------
def connect(url=None):
    # autocommit=True: single statements save at once; atomic() groups several together
    global _conn
    _conn = psycopg.connect(url or os.getenv("DATABASE_URL", DEFAULT_URL),
                            autocommit=True, row_factory=dict_row)


def close():
    _conn.close()


def reset_db():
    """Delete all tables and recreate them from basic_schema.sql (for demo/testing)."""
    _conn.execute("DROP SCHEMA public CASCADE")
    _conn.execute("CREATE SCHEMA public")
    _conn.execute(Path(__file__).with_name("basic_schema.sql").read_text())


@contextmanager
def atomic():
    """Everything inside the 'with' block is saved together (commit) or undone together (rollback)."""
    with _conn.transaction():
        yield


# ---------- data used by E1 (workflow) ----------
def get_role(user_id):
    row = _conn.execute("SELECT role FROM app_user WHERE user_id = %s", (user_id,)).fetchone()
    return row["role"] if row else None


def add_request(user_id, product, qty):
    row = _conn.execute(
        "INSERT INTO purchase_request(requester_id, product, quantity) "
        "VALUES (%s, %s, %s) RETURNING request_id", (user_id, product, qty)).fetchone()
    return row["request_id"]


def get_request(request_id):
    return _conn.execute("SELECT * FROM purchase_request WHERE request_id = %s",
                         (request_id,)).fetchone()


def set_request_status(request_id, status):
    _conn.execute("UPDATE purchase_request SET status = %s WHERE request_id = %s",
                  (status, request_id))


# ---------- data used by E2 (vendor) and E4 (stock) ----------
def stock_for_product(product):
    """All vendors that stock this product (E2 does the filtering and sorting)."""
    return _conn.execute(
        "SELECT v.vendor_id, v.name, s.stock_qty, s.unit_price "
        "FROM vendor_stock s JOIN vendor v ON v.vendor_id = s.vendor_id "
        "WHERE s.product = %s", (product,)).fetchall()


def get_stock(vendor_id, product):
    row = _conn.execute("SELECT stock_qty FROM vendor_stock WHERE vendor_id = %s AND product = %s",
                        (vendor_id, product)).fetchone()
    return row["stock_qty"] if row else 0


def reduce_stock(vendor_id, product, qty):
    """Reduce stock only if enough is left (one statement). Returns True if it worked."""
    result = _conn.execute(
        "UPDATE vendor_stock SET stock_qty = stock_qty - %s "
        "WHERE vendor_id = %s AND product = %s AND stock_qty >= %s",
        (qty, vendor_id, product, qty))
    return result.rowcount == 1


def add_stock(vendor_id, product, qty):
    _conn.execute("UPDATE vendor_stock SET stock_qty = stock_qty + %s "
                  "WHERE vendor_id = %s AND product = %s", (qty, vendor_id, product))


# ---------- orders, receipt, invoice, payment ----------
def log(actor, action):
    _conn.execute("INSERT INTO audit_log(actor, action) VALUES (%s, %s)", (actor, action))


def audit_entries():
    return _conn.execute("SELECT actor, action FROM audit_log ORDER BY log_id").fetchall()


def create_order(request_id, vendor_id, qty, price):
    row = _conn.execute(
        "INSERT INTO purchase_order(request_id, vendor_id, quantity, unit_price) "
        "VALUES (%s, %s, %s, %s) RETURNING order_id", (request_id, vendor_id, qty, price)).fetchone()
    log("Shopkeeper", f"Order {row['order_id']} created")
    return row["order_id"]


def record_receipt(order_id, qty_received):
    _conn.execute("INSERT INTO goods_receipt(order_id, received_qty) VALUES (%s, %s)",
                  (order_id, qty_received))
    log("Warehouse", f"Order {order_id}: received {qty_received}")


def submit_invoice(invoice_no, order_id, qty, amount):
    try:
        with _conn.transaction():
            _conn.execute("INSERT INTO invoice(invoice_no, order_id, qty, amount) VALUES (%s, %s, %s, %s)",
                          (invoice_no, order_id, qty, amount))
    except psycopg.errors.UniqueViolation:
        raise ValueError("Duplicate invoice rejected")
    log("Vendor", f"Order {order_id}: invoice {invoice_no}")


def three_way_match(order_id):
    """Order quantity = received quantity = invoice quantity, and amount = qty x price."""
    row = _conn.execute(
        "SELECT o.quantity, o.unit_price, r.received_qty, i.qty AS inv_qty, i.amount "
        "FROM purchase_order o "
        "JOIN goods_receipt r ON r.order_id = o.order_id "
        "JOIN invoice i ON i.order_id = o.order_id "
        "WHERE o.order_id = %s", (order_id,)).fetchone()
    if row is None:
        return False
    return (row["received_qty"] == row["quantity"]
            and row["inv_qty"] == row["quantity"]
            and row["amount"] == row["quantity"] * row["unit_price"])


def record_payment(order_id):
    if not three_way_match(order_id):
        raise ValueError("Payment refused: order, receipt and invoice do not match")
    inv = _conn.execute("SELECT invoice_id, amount FROM invoice WHERE order_id = %s",
                        (order_id,)).fetchone()
    _conn.execute("INSERT INTO payment(invoice_id, amount) VALUES (%s, %s)",
                  (inv["invoice_id"], inv["amount"]))
    log("Finance", f"Order {order_id}: paid {inv['amount']}")
