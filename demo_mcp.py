"""
Demo MCP Module - Simulated SAS Viya MCP Server with McDonald's Consumer Analytics.

Exposes analytical tools and synthetic dataset for the Top 20 McDonald's frequent consumers,
including their profile, favorite products, visit frequency, and average spent.
Designed in English to demonstrate SAS Viya MCP integration and DLP PII protection.
"""

import json
from typing import List, Dict, Any


class DemoMCPTool:
    """Mock MCP Tool object matching the official MCP Tool schema structure."""
    def __init__(self, name: str, description: str, input_schema: dict):
        self.name = name
        self.description = description
        self.inputSchema = input_schema


# Synthetic dataset of the Top 20 McDonald's frequent consumers from SAS Viya analytics
MCDONALDS_TOP_20_USERS = [
    {
        "customer_id": "MCD-1001",
        "name": "Marcus Vance",
        "email": "marcus.vance@techlead.io",
        "phone": "(415) 555-8392",
        "ssn": "142-88-3921",
        "loyalty_tier": "Diamond",
        "monthly_visits": 28,
        "avg_spend_usd": 24.50,
        "monthly_total_spend_usd": 686.00,
        "favorite_products": [
            "Double Quarter Pounder with Cheese Meal",
            "10 pc Spicy Chicken McNuggets",
            "Oreo McFlurry",
            "Large Sprite"
        ],
        "preferred_channel": "Mobile App Drive-Thru",
        "favorite_daytime": "Late Night (11 PM - 2 AM)",
        "points_balance": 18450
    },
    {
        "customer_id": "MCD-1002",
        "name": "Sarah Jenkins",
        "email": "sarah.j@consultingcorp.com",
        "phone": "+1 212-555-0144",
        "ssn": "231-45-6712",
        "loyalty_tier": "Diamond",
        "monthly_visits": 26,
        "avg_spend_usd": 21.75,
        "monthly_total_spend_usd": 565.50,
        "favorite_products": [
            "Big Mac Meal with Large French Fries",
            "Apple Pie",
            "Coca-Cola Zero Sugar",
            "Chocolate Shake"
        ],
        "preferred_channel": "In-Store Kiosk",
        "favorite_daytime": "Lunch (12 PM - 2 PM)",
        "points_balance": 15200
    },
    {
        "customer_id": "MCD-1003",
        "name": "David Miller",
        "email": "david.miller@techlead.io",
        "phone": "(312) 555-4921",
        "ssn": "319-54-1092",
        "loyalty_tier": "Diamond",
        "monthly_visits": 25,
        "avg_spend_usd": 19.80,
        "monthly_total_spend_usd": 495.00,
        "favorite_products": [
            "Bacon, Egg & Cheese Biscuit Meal",
            "2x Hash Browns",
            "Iced Caramel Macchiato",
            "Hotcakes with Sausage"
        ],
        "preferred_channel": "Drive-Thru",
        "favorite_daytime": "Breakfast (7 AM - 9 AM)",
        "points_balance": 13900
    },
    {
        "customer_id": "MCD-1004",
        "name": "Emily Rodriguez",
        "email": "emily.rodriguez@logistics-hub.net",
        "phone": "+1 (713) 555-9012",
        "ssn": "402-12-8472",
        "loyalty_tier": "Platinum",
        "monthly_visits": 24,
        "avg_spend_usd": 18.25,
        "monthly_total_spend_usd": 438.00,
        "favorite_products": [
            "20 pc Chicken McNuggets Shareables",
            "Large French Fries",
            "Tangy Barbeque Sauce",
            "Hi-C Orange Lavaburst"
        ],
        "preferred_channel": "Curbside Pickup",
        "favorite_daytime": "Dinner (6 PM - 8 PM)",
        "points_balance": 12400
    },
    {
        "customer_id": "MCD-1005",
        "name": "James Wilson",
        "email": "jwilson@financepartners.com",
        "phone": "(617) 555-3211",
        "ssn": "518-72-9304",
        "loyalty_tier": "Platinum",
        "monthly_visits": 23,
        "avg_spend_usd": 17.60,
        "monthly_total_spend_usd": 404.80,
        "favorite_products": [
            "Quarter Pounder with Cheese Deluxe",
            "Medium French Fries",
            "M&M's McFlurry",
            "Dr Pepper"
        ],
        "preferred_channel": "McDelivery",
        "favorite_daytime": "Lunch (1 PM - 3 PM)",
        "points_balance": 11800
    },
    {
        "customer_id": "MCD-1006",
        "name": "Jessica Taylor",
        "email": "jtaylor@consultingcorp.com",
        "phone": "(206) 555-7744",
        "ssn": "610-33-4921",
        "loyalty_tier": "Platinum",
        "monthly_visits": 22,
        "avg_spend_usd": 16.90,
        "monthly_total_spend_usd": 371.80,
        "favorite_products": [
            "Spicy Crispy Chicken Sandwich",
            "Large French Fries",
            "Strawberry Banana Smoothie",
            "Chocolate Chip Cookies"
        ],
        "preferred_channel": "Mobile App Order",
        "favorite_daytime": "Dinner (7 PM - 9 PM)",
        "points_balance": 10550
    },
    {
        "customer_id": "MCD-1007",
        "name": "Robert Anderson",
        "email": "robert.anderson@aerospace-sys.org",
        "phone": "+1 404-555-8833",
        "ssn": "721-65-8812",
        "loyalty_tier": "Platinum",
        "monthly_visits": 22,
        "avg_spend_usd": 16.50,
        "monthly_total_spend_usd": 363.00,
        "favorite_products": [
            "Filet-O-Fish Meal",
            "Medium Fries",
            "Sweet Iced Tea",
            "Vanilla Cone"
        ],
        "preferred_channel": "Drive-Thru",
        "favorite_daytime": "Lunch (12 PM - 1 PM)",
        "points_balance": 9950
    },
    {
        "customer_id": "MCD-1008",
        "name": "Ashley Thomas",
        "email": "ashley.thomas@healthcare-group.com",
        "phone": "(305) 555-6129",
        "ssn": "834-90-2134",
        "loyalty_tier": "Platinum",
        "monthly_visits": 21,
        "avg_spend_usd": 15.95,
        "monthly_total_spend_usd": 334.95,
        "favorite_products": [
            "Sausage McMuffin with Egg Meal",
            "Hash Browns",
            "Premium Roast McCafe Coffee",
            "Blueberry Muffin"
        ],
        "preferred_channel": "Drive-Thru",
        "favorite_daytime": "Breakfast (6 AM - 8 AM)",
        "points_balance": 9400
    },
    {
        "customer_id": "MCD-1009",
        "name": "Brian Jackson",
        "email": "brian.j@logistics-hub.net",
        "phone": "(602) 555-4082",
        "ssn": "912-34-5678",
        "loyalty_tier": "Gold",
        "monthly_visits": 20,
        "avg_spend_usd": 15.40,
        "monthly_total_spend_usd": 308.00,
        "favorite_products": [
            "Big Mac Double Combo",
            "Large Fries",
            "Spicy Buffalo McNuggets (6 pc)",
            "Large Coke"
        ],
        "preferred_channel": "Mobile Order & Pay",
        "favorite_daytime": "Late Night (10 PM - 12 AM)",
        "points_balance": 8800
    },
    {
        "customer_id": "MCD-1010",
        "name": "Amanda White",
        "email": "awhite@financepartners.com",
        "phone": "+1 619-555-9271",
        "ssn": "189-42-8821",
        "loyalty_tier": "Gold",
        "monthly_visits": 20,
        "avg_spend_usd": 14.85,
        "monthly_total_spend_usd": 297.00,
        "favorite_products": [
            "Crispy Chicken Sandwich Meal",
            "Apple Slices",
            "Diet Coke",
            "Baked Apple Pie"
        ],
        "preferred_channel": "In-Store Kiosk",
        "favorite_daytime": "Lunch (1 PM - 2 PM)",
        "points_balance": 8200
    },
    {
        "customer_id": "MCD-1011",
        "name": "Christopher Harris",
        "email": "c.harris@techlead.io",
        "phone": "(214) 555-3810",
        "ssn": "283-59-1144",
        "loyalty_tier": "Gold",
        "monthly_visits": 19,
        "avg_spend_usd": 14.50,
        "monthly_total_spend_usd": 275.50,
        "favorite_products": [
            "McDouble 2-Cheeseburger Combo",
            "Large French Fries",
            "Fanta Orange",
            "Hot Fudge Sundae"
        ],
        "preferred_channel": "Drive-Thru",
        "favorite_daytime": "Afternoon Snack (3 PM - 5 PM)",
        "points_balance": 7900
    },
    {
        "customer_id": "MCD-1012",
        "name": "Stephanie Martin",
        "email": "smartin@consultingcorp.com",
        "phone": "(512) 555-7391",
        "ssn": "391-44-8022",
        "loyalty_tier": "Gold",
        "monthly_visits": 19,
        "avg_spend_usd": 14.20,
        "monthly_total_spend_usd": 269.80,
        "favorite_products": [
            "Egg McMuffin with Bacon",
            "Hash Browns",
            "Iced French Vanilla Coffee",
            "Fruit & Maple Oatmeal"
        ],
        "preferred_channel": "Curbside Pickup",
        "favorite_daytime": "Breakfast (8 AM - 10 AM)",
        "points_balance": 7450
    },
    {
        "customer_id": "MCD-1013",
        "name": "Matthew Thompson",
        "email": "matthew.t@healthcare-group.com",
        "phone": "+1 (702) 555-1940",
        "ssn": "481-99-3140",
        "loyalty_tier": "Gold",
        "monthly_visits": 18,
        "avg_spend_usd": 13.90,
        "monthly_total_usd": 250.20,
        "favorite_products": [
            "10 pc Chicken McNuggets Meal",
            "Honey Mustard Sauce",
            "Medium Fries",
            "Minute Maid Premium Orange Juice"
        ],
        "preferred_channel": "McDelivery",
        "favorite_daytime": "Dinner (6 PM - 8 PM)",
        "points_balance": 6900
    },
    {
        "customer_id": "MCD-1014",
        "name": "Nicole Garcia",
        "email": "nicole.garcia@aerospace-sys.org",
        "phone": "(303) 555-8271",
        "ssn": "572-13-9021",
        "loyalty_tier": "Gold",
        "monthly_visits": 18,
        "avg_spend_usd": 13.60,
        "monthly_total_spend_usd": 244.80,
        "favorite_products": [
            "Spicy McChicken Double Meal",
            "Large French Fries",
            "Dr Pepper",
            "Caramel Frappe"
        ],
        "preferred_channel": "Mobile App Order",
        "favorite_daytime": "Late Night (11 PM - 1 AM)",
        "points_balance": 6500
    },
    {
        "customer_id": "MCD-1015",
        "name": "Daniel Martinez",
        "email": "dmartinez@logistics-hub.net",
        "phone": "(972) 555-6632",
        "ssn": "661-88-7201",
        "loyalty_tier": "Gold",
        "monthly_visits": 17,
        "avg_spend_usd": 13.25,
        "monthly_total_spend_usd": 225.25,
        "favorite_products": [
            "Big Mac Single",
            "6 pc Chicken McNuggets",
            "Medium French Fries",
            "Strawberry Shake"
        ],
        "preferred_channel": "Drive-Thru",
        "favorite_daytime": "Lunch (12 PM - 2 PM)",
        "points_balance": 6100
    },
    {
        "customer_id": "MCD-1016",
        "name": "Elizabeth Robinson",
        "email": "e.robinson@financepartners.com",
        "phone": "+1 408-555-4491",
        "ssn": "753-29-1049",
        "loyalty_tier": "Gold",
        "monthly_visits": 17,
        "avg_spend_usd": 12.95,
        "monthly_total_spend_usd": 220.15,
        "favorite_products": [
            "Sausage Burrito (2 pack)",
            "Hash Browns",
            "Hot Picante Sauce",
            "Caramel Macchiato"
        ],
        "preferred_channel": "Drive-Thru",
        "favorite_daytime": "Breakfast (7 AM - 9 AM)",
        "points_balance": 5800
    },
    {
        "customer_id": "MCD-1017",
        "name": "Anthony Clark",
        "email": "aclark@aerospace-sys.org",
        "phone": "(615) 555-1102",
        "ssn": "842-70-4911",
        "loyalty_tier": "Gold",
        "monthly_visits": 16,
        "avg_spend_usd": 12.50,
        "monthly_total_spend_usd": 200.00,
        "favorite_products": [
            "Quarter Pounder with Cheese",
            "Large French Fries",
            "Diet Coke"
        ],
        "preferred_channel": "In-Store Kiosk",
        "favorite_daytime": "Lunch (12 PM - 1 PM)",
        "points_balance": 5400
    },
    {
        "customer_id": "MCD-1018",
        "name": "Megan Rodriguez",
        "email": "megan.r@consultingcorp.com",
        "phone": "(813) 555-9941",
        "ssn": "931-15-7729",
        "loyalty_tier": "Gold",
        "monthly_visits": 16,
        "avg_spend_usd": 12.20,
        "monthly_total_spend_usd": 195.20,
        "favorite_products": [
            "McCrispy Deluxe Sandwich Meal",
            "Medium Fries",
            "Sprite",
            "Oreo McFlurry"
        ],
        "preferred_channel": "Mobile Order & Pay",
        "favorite_daytime": "Dinner (6 PM - 8 PM)",
        "points_balance": 5100
    },
    {
        "customer_id": "MCD-1019",
        "name": "Joshua Lewis",
        "email": "jlewis@techlead.io",
        "phone": "+1 (901) 555-3319",
        "ssn": "119-82-4412",
        "loyalty_tier": "Gold",
        "monthly_visits": 15,
        "avg_spend_usd": 11.90,
        "monthly_total_spend_usd": 178.50,
        "favorite_products": [
            "Double Cheeseburger Meal",
            "Large French Fries",
            "Sweet 'N Sour Sauce",
            "Hi-C Orange"
        ],
        "preferred_channel": "Drive-Thru",
        "favorite_daytime": "Late Night (10 PM - 12 AM)",
        "points_balance": 4750
    },
    {
        "customer_id": "MCD-1020",
        "name": "Samantha Lee",
        "email": "slee@healthcare-group.com",
        "phone": "(704) 555-5520",
        "ssn": "208-93-6610",
        "loyalty_tier": "Gold",
        "monthly_visits": 15,
        "avg_spend_usd": 11.50,
        "monthly_total_spend_usd": 172.50,
        "favorite_products": [
            "Hotcakes and Sausage Meal",
            "Hash Browns",
            "Premium Roast Iced Coffee"
        ],
        "preferred_channel": "Curbside Pickup",
        "favorite_daytime": "Breakfast (8 AM - 10 AM)",
        "points_balance": 4400
    }
]


def get_demo_mcp_tools() -> List[DemoMCPTool]:
    """Return tool schemas exposed by the simulated SAS Viya McDonald's analytics MCP server."""
    return [
        DemoMCPTool(
            name="get_mcdonalds_top_customers",
            description=(
                "SAS Viya MAS Analytical Service: Query the top 20 McDonald's loyalty consumers, "
                "returning consumer profiles, visit frequency, average spend per ticket, "
                "monthly totals, and their most frequently ordered products."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of top consumers to retrieve (1 to 20, default 20)",
                        "default": 20
                    },
                    "min_avg_spend": {
                        "type": "number",
                        "description": "Filter consumers whose average ticket spend in USD is greater than or equal to this threshold",
                        "default": 0.0
                    },
                    "loyalty_tier": {
                        "type": "string",
                        "description": "Filter by McDonald's Rewards tier: 'all', 'Diamond', 'Platinum', 'Gold'",
                        "default": "all"
                    }
                }
            }
        ),
        DemoMCPTool(
            name="get_customer_consumption_profile",
            description=(
                "SAS Viya Customer Intelligence: Retrieve detailed consumption history, item basket analytics, "
                "and preferred order channel for a specific McDonald's customer by ID or email."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Customer identifier (e.g., 'MCD-1001' to 'MCD-1020') or customer email"
                    }
                },
                "required": ["customer_id"]
            }
        ),
        DemoMCPTool(
            name="get_mcdonalds_popular_products_kpis",
            description=(
                "SAS Model Manager Analytical Summary: Calculate product popularity ranking, order frequency, "
                "and revenue contributions across all McDonald's top consumer segments."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product category: 'all', 'Burgers', 'Breakfast', 'Chicken', 'Beverages', 'Desserts'",
                        "default": "all"
                    }
                }
            }
        )
    ]


def execute_demo_tool(name: str, args: dict) -> str:
    """Execute simulated SAS Viya MCP tool and return formatted analytical output in English."""
    args = args or {}
    
    if name == "get_mcdonalds_top_customers":
        limit = int(args.get("limit") or 20)
        min_spend = float(args.get("min_avg_spend") or 0.0)
        tier = str(args.get("loyalty_tier") or "all").strip().lower()

        filtered = []
        for u in MCDONALDS_TOP_20_USERS:
            if min_spend > 0 and u["avg_spend_usd"] < min_spend:
                continue
            if tier != "all" and u["loyalty_tier"].lower() != tier:
                continue
            filtered.append(u)

        filtered = filtered[:limit]

        # Calculate high-level summary KPIs
        total_customers = len(filtered)
        avg_ticket = sum(u["avg_spend_usd"] for u in filtered) / total_customers if total_customers else 0
        avg_visits = sum(u["monthly_visits"] for u in filtered) / total_customers if total_customers else 0

        response_payload = {
            "source": "SAS Viya Micro Analytic Service (MAS) - McDonald's Consumer Intelligence",
            "status": "SUCCESS_200",
            "analytics_summary": {
                "total_top_consumers": total_customers,
                "average_monthly_visits": round(avg_visits, 1),
                "overall_average_spend_usd": round(avg_ticket, 2),
                "top_ordered_categories": [
                    "Quarter Pounder & Big Mac Combos",
                    "Chicken McNuggets (10 pc / 20 pc)",
                    "McFlurry Desserts (Oreo / M&M's)",
                    "Breakfast Biscuits & McCafe Beverages"
                ]
            },
            "top_consumers": filtered
        }
        return json.dumps(response_payload, indent=2, ensure_ascii=False)

    elif name == "get_customer_consumption_profile":
        cid = str(args.get("customer_id") or "").strip().lower()
        match = None
        for u in MCDONALDS_TOP_20_USERS:
            if u["customer_id"].lower() == cid or u["email"].lower() == cid or u["name"].lower() == cid:
                match = u
                break

        if not match:
            # Fallback to first user as example if not found
            match = MCDONALDS_TOP_20_USERS[0]

        return json.dumps({
            "source": "SAS Viya Customer Journey Analytics",
            "customer_profile": match,
            "consumption_recommendations": [
                "Eligible for VIP Double Points Promo on favorite items",
                "App push notification recommended during preferred daytime: " + match["favorite_daytime"]
            ]
        }, indent=2, ensure_ascii=False)

    elif name == "get_mcdonalds_popular_products_kpis":
        category = str(args.get("category") or "all").capitalize()
        return json.dumps({
            "source": "SAS Viya Model Manager - Menu Item Affinity Matrix",
            "filter_category": category,
            "ranking": [
                {"rank": 1, "item": "Large French Fries", "monthly_orders": 448, "avg_item_price": "$3.89", "affinity": "92%"},
                {"rank": 2, "item": "Double Quarter Pounder with Cheese", "monthly_orders": 312, "avg_item_price": "$7.49", "affinity": "78%"},
                {"rank": 3, "item": "10 pc Chicken McNuggets", "monthly_orders": 286, "avg_item_price": "$5.99", "affinity": "74%"},
                {"rank": 4, "item": "Big Mac", "monthly_orders": 264, "avg_item_price": "$5.89", "affinity": "71%"},
                {"rank": 5, "item": "Oreo McFlurry", "monthly_orders": 220, "avg_item_price": "$4.29", "affinity": "65%"},
                {"rank": 6, "item": "Bacon, Egg & Cheese Biscuit", "monthly_orders": 194, "avg_item_price": "$4.59", "affinity": "61%"},
                {"rank": 7, "item": "Iced Caramel Macchiato", "monthly_orders": 182, "avg_item_price": "$3.79", "affinity": "58%"}
            ]
        }, indent=2, ensure_ascii=False)

    else:
        return json.dumps({"error": f"Unknown tool '{name}'"}, indent=2)
