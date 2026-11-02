"""Demo: one request through all 4 engines. Only E3 uses the PostgreSQL database."""
import e1_workflow as e1
import e2_vendor as e2
import e3_integrity as e3
import e4_stock as e4

e3.connect()
e3.reset_db()                         # fresh tables + sample data (users 1-4, Vendor A/B)
CUSTOMER, SHOP, WAREHOUSE, FINANCE = 1, 2, 3, 4

# E1: create and approve a request
rid = e1.create_request(CUSTOMER, "Laptop", 5)
e1.check_role(SHOP, "approve_request")
e1.change_status(rid, "Approved")

# E2: search (Vendor B has only 3, so only Vendor A is listed) and select
print("Vendors:", [(v["name"], v["unit_price"]) for v in e2.search("Laptop", 5)])
price = e2.select_vendor("Laptop", 5, vendor_id=1)
e1.change_status(rid, "Vendor Selected")

# E4 + E3 together: reserve stock and create the order in one transaction
with e3.atomic():
    e4.reserve(1, "Laptop", 5)
    oid = e3.create_order(rid, 1, 5, price)
    e1.change_status(rid, "Ordered")

# E3: receipt, invoice, 3-way match, payment
e3.record_receipt(oid, 5)
e1.change_status(rid, "Received")
e3.submit_invoice("INV-001", oid, 5, 2500)
print("3-way match:", e3.three_way_match(oid))
e3.record_payment(oid)
e1.change_status(rid, "Completed")

print("Final status:", e1.track_status(rid))
print("Stock left (Vendor A):", e3.get_stock(1, "Laptop"))
print("\nAudit log:")
for row in e3.audit_entries():
    print(" ", row["actor"], "|", row["action"])

# Rule checks
def attempt(label, fn):
    try:
        fn()
    except (ValueError, PermissionError) as err:
        print(f"Blocked ({label}):", err)

print()
attempt("skipped step", lambda: e1.change_status(rid, "Approved"))
attempt("wrong role", lambda: e1.check_role(CUSTOMER, "record_payment"))
attempt("too much", lambda: e4.reserve(1, "Laptop", 99))
attempt("duplicate invoice", lambda: e3.submit_invoice("INV-001", oid, 5, 2500))

# Rollback demo: stock is reduced, then an error happens -> everything is undone
def failing_order():
    with e3.atomic():
        e4.reserve(1, "Laptop", 2)
        raise ValueError("something failed after reserving")
before = e3.get_stock(1, "Laptop")
attempt("rollback", failing_order)
print(f"Stock before={before}, after={e3.get_stock(1, 'Laptop')} (unchanged, rollback worked)")
e3.close()
