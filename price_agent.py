from typing import List, Dict, Optional
from model import llm
from langchain.tools import tool
import requests

BASE_URL = "https://api.kittchens.com/api/products"



@tool
def fetch_purchase_options(product_id: str) -> dict:
    """
    Fetch purchase options for a product by ID.
    Returns raw pricing and measurement units from catalog.
    """
    if not product_id:
        return {"success": False, "data": []}

    url = f"{BASE_URL}/{product_id}/purchase-options"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}
    



import re
from difflib import SequenceMatcher
from langchain.tools import tool

# ----- UNIT PARSING -----
def _extract_size(unit_text: str):
    """
    Extract numeric size + base unit from strings like:
    '1kg', '5l', '500ml', '1 bag (5kg)', '1 piece', '1 pack'
    """
    unit_text = unit_text.lower().strip()
    
    # Standard units
    match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)", unit_text)
    if match:
        return float(match.group(1)), match.group(2)
    
    # Non-standard units like piece, pack → treat as 1 each
    if any(x in unit_text for x in ["piece", "pack", "unit"]):
        return 1.0, "unit"
    
    # Extract size from things like "1 bag (5kg)"
    match = re.search(r"\((\d+(?:\.\d+)?)\s*(kg|g|l|ml)\)", unit_text)
    if match:
        return float(match.group(1)), match.group(2)

    return None, None


def _convert_to_base(size: float, unit: str):
    """
    Convert to base units: g, ml, unit
    """
    if unit == "kg":
        return size * 1000, "g"
    if unit == "l":
        return size * 1000, "ml"
    return size, unit


def _normalize_unit(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


# ----- PRICING TOOL -----
@tool
def choose_best_unit_price(ingredient_unit: str, quantity: float, purchase_options: dict) -> dict:
    """
    Select the best purchase option from catalog and compute total price.
    - Always pick the smallest option that fully covers the requested quantity.
    - Fall back to next larger unit if exact match not available.
    """
    if not purchase_options.get("success"):
        return {"total_price": None, "reason": "no_purchase_options"}

    # Parse ingredient size
    ing_size, ing_unit = _extract_size(ingredient_unit)
    if ing_size is None:
        ing_size, ing_unit = 1.0, "unit"
    ing_size, ing_unit = _convert_to_base(ing_size, ing_unit)
    ing_total_size = ing_size * quantity

    # Collect candidate options
    candidates = []
    for option in purchase_options.get("data", []):
        display_name = option["measurement_units"]["display_name"]
        cat_size, cat_unit = _extract_size(display_name)
        if cat_size is None:
            cat_size, cat_unit = 1.0, "unit"
        cat_size, cat_unit = _convert_to_base(cat_size, cat_unit)

        # Skip incompatible units
        if cat_unit != ing_unit:
            if cat_unit != "unit" and ing_unit != "unit":
                continue

        # Similarity for reference
        score = _similarity(_normalize_unit(ingredient_unit), _normalize_unit(display_name))

        candidates.append({
            "option": option,
            "cat_size": cat_size,
            "cat_unit": cat_unit,
            "similarity": score
        })

    if not candidates:
        return {"total_price": None, "reason": "no_close_unit_match", "confidence": 0}

    # Filter options that cover requested quantity
    # If none, fallback to the next largest
    covering_options = [c for c in candidates if c["cat_size"] >= ing_total_size]
    if not covering_options:
        covering_options = sorted(candidates, key=lambda x: x["cat_size"])

    # Choose smallest that covers the size, with highest similarity
    best = sorted(
        covering_options,
        key=lambda x: (x["cat_size"], -x["similarity"])
    )[0]

    option = best["option"]
    cat_size = best["cat_size"]

    # Price per base unit (g, ml, unit)
    price_per_base_unit = option["price"] / cat_size
    total_price = price_per_base_unit * ing_total_size

    return {
        "matched_unit": option["measurement_units"]["display_name"],
        "unit_price": round(price_per_base_unit, 4),
        "quantity": quantity,
        "total_price": round(total_price, 2),
        "confidence": round(best["similarity"], 2)
    }
    
    
@tool
def calculate_total_cost(priced_items: list) -> dict:
    """
    Sum total cost of all priced ingredients.
    """
    total = 0
    unavailable = 0

    for item in priced_items:
        if item.get("total_price") is None:
            unavailable += 1
        else:
            total += item["total_price"]

    return {
        "total_estimated_cost": round(total, 2),
        "unavailable_count": unavailable
    }
    
    

tools = [
    fetch_purchase_options,
    choose_best_unit_price,
    calculate_total_cost,
]

llm_with_tools = llm.bind_tools(tools)




from langchain_core.messages import SystemMessage

SYSTEM_PROMPT = """
You are a tool-using pricing agent.

RULES:
- NEVER guess prices
- NEVER compute totals yourself
- ALWAYS call tools
- If product_id is null → mark unavailable
- If unit mismatch → rely on choose_best_unit_price
- Return ONLY structured JSON
"""

async def price_ingredients(ingredients: list):
    priced_items = []

    for ing in ingredients:
        if not ing.get("mapped_product_id"):
            priced_items.append({
                **ing,
                "product_price": None,
                "availability_status": "unavailable",
                "matched_unit": None,
                "unit_price": None,
                "total_price": None
            })
            continue

        # Fetch real purchase options
        options = await fetch_purchase_options.ainvoke({
            "product_id": ing["mapped_product_id"]
        })

        # Determine best unit and price
        price_info = choose_best_unit_price.invoke({
            "ingredient_unit": ing["unit"],
            "quantity": ing["quantity"],
            "purchase_options": options
        })

        # Overwrite old product_price with price from purchase option
        real_price = None
        if options.get("success") and price_info.get("matched_unit"):
            for opt in options["data"]:
                if opt["measurement_units"]["display_name"] == price_info["matched_unit"]:
                    real_price = opt["price"]
                    break

        priced_items.append({
            **ing,
            **price_info,
            "product_price": real_price,  # this is now the actual catalog price
            "availability_status": "available" if price_info.get("total_price") else "unavailable"
        })

    totals = calculate_total_cost.invoke({
        "priced_items": priced_items
    })

    return {
        "ingredients": priced_items,
        **totals
    }


import requests
import asyncio

async def main():
    response = [
    {
      "ingredient_name": "Rice",
      "quantity": 0.5,
      "unit": "1kg",
      "mapped_product_id": "a8d401f0-ec60-4eaf-beac-7160db30d06e",
      "product_name": "Tropical Sun Golden Sella Pure Basmati Rice",
      "product_price": 17249,
      "availability_status": "available",
      "confidence_score": 0.99,
      "category_id": "1d6dd861-ec97-4f1d-bdfd-7bcdfb73c80e",
      "category_name": "Grain & Rice",
      "notes": "Mapped within category 'Grain & Rice'"
    },
    {
      "ingredient_name": "Tomato",
      "quantity": 2,
      "unit": "1 piece",
      "mapped_product_id": "df2f612c-f8c1-4e14-9adf-370554493d8a",
      "product_name": "Tomatoes",
      "product_price": 0,
      "availability_status": "available",
      "confidence_score": 0.99,
      "category_id": "f759c63d-c227-4c54-bf6f-a9bfda5ca920",
      "category_name": "Vegetables",
      "notes": "Mapped within category 'Vegetables'"
    },
    {
      "ingredient_name": "Onion",
      "quantity": 1,
      "unit": "1 piece",
      "mapped_product_id": "5639e13b-9255-4b08-a190-af1d62ae6fd1",
      "product_name": "Onions",
      "product_price": 83986,
      "availability_status": "available",
      "confidence_score": 0.91,
      "category_id": "f759c63d-c227-4c54-bf6f-a9bfda5ca920",
      "category_name": "Vegetables",
      "notes": "Mapped within category 'Vegetables'"
    },
    {
      "ingredient_name": "Pepper",
      "quantity": 1,
      "unit": "1 piece",
      "mapped_product_id": "2e530167-7544-4ba8-a8ed-cb4eaf308b6d",
      "product_name": "Pepper",
      "product_price": 37650,
      "availability_status": "available",
      "confidence_score": 0.99,
      "category_id": "f759c63d-c227-4c54-bf6f-a9bfda5ca920",
      "category_name": "Vegetables",
      "notes": "Mapped within category 'Vegetables'"
    },
    {
      "ingredient_name": "Vegetable Oil",
      "quantity": 1,
      "unit": "500ml",
      "mapped_product_id": "72a654b2-2ab1-45d7-a9b7-cc39ffc11f47",
      "product_name": "Groundnuts Oil",
      "product_price": 46999,
      "availability_status": "available",
      "confidence_score": 0.99,
      "category_id": "2aacaaab-93e6-479c-bf15-c963bf02199b",
      "category_name": "Cooking Essentials",
      "notes": "Mapped within category 'Cooking Essentials'"
    },
    {
      "ingredient_name": "Salt",
      "quantity": 1,
      "unit": "1 pack",
      "mapped_product_id": "db932c09-0076-4fb6-a657-f6d392438782",
      "product_name": "Mr chef Salt",
      "product_price": 8999,
      "availability_status": "available",
      "confidence_score": 0.99,
      "category_id": "2aacaaab-93e6-479c-bf15-c963bf02199b",
      "category_name": "Cooking Essentials",
      "notes": "Mapped within category 'Cooking Essentials'"
    },
    {
      "ingredient_name": "Curry",
      "quantity": 1,
      "unit": "1 pack",
      "mapped_product_id": None,
      "product_name": None,
      "product_price": None,
      "availability_status": "unavailable",
      "confidence_score": 0,
      "category_id": None,
      "category_name": None,
      "notes": "No product match found in category"
    },
    {
      "ingredient_name": "Chicken",
      "quantity": 0.25,
      "unit": "1kg",
      "mapped_product_id": "5baeca8a-7810-4866-8856-6a08e43b5de8",
      "product_name": "meat (chicken)",
      "product_price": 4099,
      "availability_status": "available",
      "confidence_score": 0.99,
      "category_id": "d3589489-dd27-4f73-b37e-3830ed3704b7",
      "category_name": "Proteins",
      "notes": "Mapped within category 'Proteins'"
    }
  ]

    priced_result = await price_ingredients(response)
    print(priced_result)


# if __name__ == "__main__":
#     asyncio.run(main())
