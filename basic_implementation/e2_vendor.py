"""E2 - Vendor Selection & Decision Engine (basic)
Student B: Satish S Batakurki (01FE24BCS103)
Filters and sorts vendors (the algorithm is here); stock data comes from E3."""




import e3_integrity as e3


def search(product, qty):
    """Keep vendors with stock >= qty, then sort by price (cheapest first)."""
    vendors = [v for v in e3.stock_for_product(product) if v["stock_qty"] >= qty]
    vendors.sort(key=lambda v: v["unit_price"])
    return vendors


def select_vendor(product, qty, vendor_id):
    """Choose ONE vendor who can supply the whole quantity (no splitting)."""
    for v in search(product, qty):
        if v["vendor_id"] == vendor_id:
            return v["unit_price"]
    raise ValueError("Vendor cannot supply the full quantity")
