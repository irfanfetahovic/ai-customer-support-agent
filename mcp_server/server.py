"""
Customer Support CRM — MCP Server

Exposes two tools that the AI worker agent can call via the
Model Context Protocol (stdio transport):

  • lookup_customer_profile  – fetch account details for a customer ID
  • lookup_order_status      – fetch current status of an order ID

Simulated data is used so the server runs without any external dependencies.
In a real deployment, replace the dicts with database / API calls.
"""

import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Customer Support CRM")

# Simulated data stores

CUSTOMERS: dict[str, dict] = {
    "C001": {
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "subscription_tier": "Premium",
        "account_age_days": 730,
        "open_tickets": 1,
        "preferred_contact": "email",
    },
    "C002": {
        "name": "Bob Smith",
        "email": "bob@example.com",
        "subscription_tier": "Basic",
        "account_age_days": 120,
        "open_tickets": 0,
        "preferred_contact": "chat",
    },
    "C003": {
        "name": "Carol White",
        "email": "carol@example.com",
        "subscription_tier": "Enterprise",
        "account_age_days": 1460,
        "open_tickets": 2,
        "preferred_contact": "phone",
    },
}

ORDERS: dict[str, dict] = {
    "ORD-1001": {
        "status": "Delivered",
        "item": "Wireless Earbuds Pro",
        "quantity": 1,
        "tracking_number": "TRK123456",
        "delivered_date": "2026-04-25",
        "carrier": "FedEx",
    },
    "ORD-1002": {
        "status": "In Transit",
        "item": "Smartwatch X",
        "quantity": 1,
        "tracking_number": "TRK789012",
        "estimated_delivery": "2026-05-02",
        "carrier": "UPS",
    },
    "ORD-1003": {
        "status": "Processing",
        "item": "Laptop Stand",
        "quantity": 2,
        "tracking_number": None,
        "estimated_delivery": "2026-05-05",
        "carrier": "USPS",
    },
    "ORD-1004": {
        "status": "Cancelled",
        "item": "USB-C Hub",
        "quantity": 1,
        "tracking_number": None,
        "estimated_delivery": None,
        "carrier": None,
        "cancellation_reason": "Customer request",
    },
}

# Tool definitions

@mcp.tool()
def lookup_customer_profile(customer_id: str) -> str:
    """Look up a customer's profile and account details by customer ID.

    Args:
        customer_id: The customer identifier (e.g. C001, C002, C003).

    Returns:
        JSON string with account details, or an error message.
    """
    profile = CUSTOMERS.get(customer_id.strip().upper())
    if not profile:
        return json.dumps(
            {
                "error": (
                    f"No customer found with ID '{customer_id}'. "
                    "Available IDs for demo: C001, C002, C003."
                )
            }
        )
    return json.dumps({"customer_id": customer_id.upper(), **profile})


@mcp.tool()
def lookup_order_status(order_id: str) -> str:
    """Look up the current status and details of a customer order by order ID.

    Args:
        order_id: The order identifier (e.g. ORD-1001, ORD-1002).

    Returns:
        JSON string with order details, or an error message.
    """
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        return json.dumps(
            {
                "error": (
                    f"No order found with ID '{order_id}'. "
                    "Available IDs for demo: ORD-1001, ORD-1002, ORD-1003, ORD-1004."
                )
            }
        )
    return json.dumps({"order_id": order_id.upper(), **order})


# Entry point

if __name__ == "__main__":
    mcp.run(transport="stdio")
