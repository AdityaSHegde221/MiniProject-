"""E1 - Procurement Workflow Engine (basic)
Student A: Rakshita Kadam (01FE24BCS135)
Status flow and role-based permissions. Stores data through E3."""
import e3_integrity as e3

# Allowed next steps: a request cannot skip a step
ALLOWED_STEPS = {
    "Pending": ["Approved", "Rejected"],
    "Approved": ["Vendor Selected"],
    "Vendor Selected": ["Ordered"],
    "Ordered": ["Received"],
    "Received": ["Completed"],
    "Completed": [],
    "Rejected": [],
}

# What each role may do
ROLE_ACTIONS = {
    "Customer":   ["create_request", "track_status"],
    "Shopkeeper": ["create_request", "approve_request", "select_vendor", "place_order", "track_status"],
    "Vendor":     ["submit_invoice"],
    "Warehouse":  ["record_receipt"],
    "Finance":    ["verify_match", "record_payment", "track_status"],
}


def check_role(user_id, action):
    role = e3.get_role(user_id)
    if role is None:
        raise ValueError("Unknown user")
    if action not in ROLE_ACTIONS[role]:
        raise PermissionError(f"{role} is not allowed to {action}")


def create_request(user_id, product, qty):
    check_role(user_id, "create_request")
    if qty <= 0:
        raise ValueError("Quantity must be greater than 0")
    return e3.add_request(user_id, product, qty)


def change_status(request_id, new_status):
    current = e3.get_request(request_id)["status"]
    if new_status not in ALLOWED_STEPS[current]:
        raise ValueError(f"Cannot go from {current} to {new_status}")
    e3.set_request_status(request_id, new_status)


def track_status(request_id):
    return e3.get_request(request_id)["status"]
