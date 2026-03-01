"""
Ingredient to product mapping and QuickMarket catalog integration.
Handles matching AI-generated ingredients to available products.
"""
import logging
from typing import Optional, List, Dict, Tuple
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)



TAG_MAP = {
    # Grains
    "rice": ["rice", "long grain rice", "white rice"],
    "jollof rice":  ["rice", "jollof rice", "cooked rice"],
    "parboiled rice": ["jollof rice", "parboiled rice"],
    "cornmeal": ["cornmeal", "pap flour", "corn flour"],
    "garri": ["garri", "gari", "cassava flakes"],
    "millet": ["millet", "millet flour"],

    # Proteins
    "chicken": ["chicken", "poultry"],
    "beef": ["beef", "cow meat"],
    "fish": ["fish", "seafood", "frozen fish"],
    "crayfish": ["crayfish", "dried shrimp", "shrimp"],
    "stockfish": ["stockfish", "dried fish"],
    "eggs": ["eggs", "chicken eggs"],

    # Legumes
    "beans": ["beans", "black-eyed beans", "kidney beans"],
    "lentils": ["lentils", "red lentils"],
    "peas": ["peas", "split peas"],

    # Vegetables
    "tomato": ["tomato", "fresh tomato", "tomatoes"],
    "onion": ["onion", "white onion"],
    "pepper": ["pepper", "hot pepper", "scotch bonnet", "chilli", "chili"],
    "bell pepper": ["bell pepper", "green pepper", "sweet pepper"],
    "spinach": ["spinach", "leafy greens", "vegetable leaves"],
    "carrot": ["carrot", "carrots"],
    "cucumber": ["cucumber", "cucumbers"],

    # Oils & Seasonings
    "palm oil": ["palm oil", "red oil"],
    "vegetable oil": ["vegetable oil", "cooking oil", "groundnut oil", "groundnuts oil"],
    "groundnut oil": ["groundnut oil", "groundnuts oil", "peanut oil", "cooking oil", "vegetable oil"],
    "tomato paste": ["tomato paste", "tomato puree"],
    "tomato puree": ["tomato paste", "tomato puree"],
    "egusi": ["egusi", "melon seeds"],
    "salt": ["salt", "table salt"],
    "garlic": ["garlic", "garlic cloves"],
    "ginger": ["ginger", "ginger root"],
    "curry powder": ["curry powder", "curry"],
    "thyme": ["thyme", "dried thyme"],
}




class IngredientNormalizer:
    """Handles canonical names and normalization of ingredient strings."""
    
    def __init__(self, tag_map: Dict[str, List[str]]):
        self.tag_map = {k.lower(): [a.lower() for a in v] for k, v in tag_map.items()}

    def normalize(self, text: str) -> str:
        text = re.sub(r"[^\w\s]", "", text.lower().strip())
        return text

    def canonical(self, ingredient_name: str) -> str:
        norm = self.normalize(ingredient_name)
        for canonical, aliases in self.tag_map.items():
            if norm in aliases:
                return canonical
        return norm
    

class IngredientProductMapper:

    def __init__(self, product_catalog: Optional[List[Dict]] = None):
        self.product_catalog = []
        self._indexed_products = []
        
        self.normalizer = IngredientNormalizer(TAG_MAP)


        if product_catalog:
            self.update_catalog(product_catalog)

    # --------------------------------------------------
    # PUBLIC
    # --------------------------------------------------
    def map_ingredient_to_product(
        self,
        ingredient_name: str,
        quantity: float,
        category_name: Optional[str],
        unit: str
    ) -> Dict:

        normalized_query = self._normalize(ingredient_name)

        # 1️⃣ Try STRICT category filter first
        candidates = self._filter_by_category(category_name)

        if candidates:
            match = self._search_within_candidates(
                normalized_query,
                candidates
            )

            if match:
                product, confidence = match
                return self._build_result(
                    ingredient_name,
                    quantity,
                    unit,
                    product,
                    confidence
                )

        # 2️⃣ 🔥 FALLBACK: Global search (only if strict failed)
        logger.info(
            f"Falling back to global search for '{ingredient_name}'"
        )

        match = self._search_within_candidates(
            normalized_query,
            self._indexed_products
        )

        if match:
            product, confidence = match
            return self._build_result(
                ingredient_name,
                quantity,
                unit,
                product,
                confidence
            )

        # 3️⃣ Nothing found anywhere
        return self._not_found(
            ingredient_name,
            quantity,
            unit
        )
    # --------------------------------------------------
    # CATEGORY FILTER
    # --------------------------------------------------

    def _filter_by_category(self, category_name: Optional[str]):


        if not category_name:
            return []

        normalized_cat = category_name.lower().strip()
        
        
        logger.info(f"Incoming category: {normalized_cat}")
        logger.info(f"Available categories: {[p['category_name'] for p in self._indexed_products]}")
        
        return [
            p for p in self._indexed_products
            if (p.get("category_name") or "").lower().strip() == normalized_cat
        ]
        
    # --------------------------------------------------
    # SEARCH (STRICT)
    # --------------------------------------------------


    def _search_within_candidates(self, query: str, candidates: list) -> Optional[Tuple[Dict, float]]:
        canonical_query = self.normalizer.canonical(query)
        query_norm = self.normalizer.normalize(canonical_query)

        best_match = None
        best_score = 0.0

        for product in candidates:
            name = product.get("normalized_name")
            tags = product.get("tags", set())
            tokens = product.get("tokens", set())

            if query_norm == name:
                return product, 0.99  # exact match
            if query_norm in tags:
                return product, 0.97  # alias/tag match
            if query_norm in tokens:
                return product, 0.95  # token match

            # fuzzy match
            score = SequenceMatcher(None, query_norm, name).ratio()
            if score > best_score:
                best_score = score
                best_match = product

        if best_score >= 0.82:
            return best_match, round(best_score, 2)

        return None
        
       
    # --------------------------------------------------
    # BUILD RESULT
    # --------------------------------------------------

    def _build_result(
        self,
        ingredient_name: str,
        quantity: float,
        unit: str,
        product: Dict,
        confidence: float
    ):

        return {
            "ingredient_name": ingredient_name,
            "quantity": quantity,
            "unit": unit,

            "mapped_product_id": product["id"],
            "product_name": product["name"],
            "product_price": product.get("base_price"),

            "availability_status": product.get("availability_status", "available"),
            "confidence_score": confidence,

            # ✅ RETURN CATEGORY INFO
            "category_id": product.get("category_id"),
            "category_name": product.get("category_name"),

            "notes": f"Mapped within category '{product.get('category_name')}'"
        }

    def _not_found(self, ingredient_name, quantity, unit):
        return {
            "ingredient_name": ingredient_name,
            "quantity": quantity,
            "unit": unit,

            "mapped_product_id": None,
            "product_name": None,
            "product_price": None,

            "availability_status": "unavailable",
            "confidence_score": 0.0,

            "category_id": None,
            "category_name": None,

            "notes": "No product match found in category"
        }

    # --------------------------------------------------
    # CATALOG INDEXING
    # --------------------------------------------------
    
    def update_catalog(self, products: List[Dict]):
        self._indexed_products = []

        for p in products:
            name = p.get("name", "")
            canonical_name = self.normalizer.canonical(name)
            normalized_name = self.normalizer.normalize(canonical_name)

            # Build tags: aliases + canonical
            tags_set = set(self.normalizer.normalize(a) for a in TAG_MAP.get(canonical_name, []))
            tags_set.add(normalized_name)

            self._indexed_products.append({
                "id": p.get("id"),
                "name": name,
                "normalized_name": normalized_name,
                "tokens": set(normalized_name.split()),
                "tags": tags_set,
                "category_id": p.get("categories", {}).get("id"),
                "category_name": p.get("categories", {}).get("name", "").strip(),
                "base_price": p.get("base_price"),
                "availability_status": p.get("availability_status", "available")
            })

        logger.info(f"Indexed {len(self._indexed_products)} products")
    # --------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------

    def _normalize(self, text: str):
        text = text.lower().strip()
        return re.sub(r"[^\w\s]", "", text)
    
    
    
    

import httpx

async def fetch_all_products(base_url: str, limit: int = 100, max_pages: int = 20):
    """
    Fetch all products across paginated API.
    Stops when empty page is returned or max_pages reached.
    """
    all_products = []
    
    async with httpx.AsyncClient(timeout=8.0) as client:
        for page in range(1, max_pages + 1):
            try:
                url = f"{base_url}?page={page}&limit={limit}"
                resp = await client.get(url)

                if resp.status_code != 200:
                    break

                data = resp.json()

                # Handle both formats:
                # Case 1: {"success": true, "data": [...]}
                # Case 2: [...]
                products = data.get("data") if isinstance(data, dict) else data

                if not products:
                    break  # No more pages

                all_products.extend(products)

                # If returned less than limit → last page
                if len(products) < limit:
                    break

            except Exception as e:
                logger.debug(f"Pagination fetch failed at page {page}: {e}")
                break

    return all_products




class CartBuilder:
    """Build shopping cart from selected ingredients."""
    
    @staticmethod
    def add_ingredients_to_cart(
        mapped_ingredients: List[Dict],
        user_cart_id: str
    ) -> Dict:
        """
        Add mapped ingredients to user's cart.
        
        Args:
            mapped_ingredients: List of mapped ingredient dicts
            user_cart_id: User's cart identifier
            
        Returns:
            Dict with cart update result:
            {
                "added_count": 5,
                "skipped_count": 2,
                "total_amount": 15000,
                "items": [...]
            }
        """
        added_items = []
        skipped_items = []
        total_amount = 0
        
        for ingredient in mapped_ingredients:
            # Skip if not available and no substitute
            if ingredient["availability_status"] == "unavailable" and not ingredient.get("substitute_product_id"):
                skipped_items.append({
                    "ingredient": ingredient["ingredient_name"],
                    "reason": "Not available at QuickMarket"
                })
                continue
            
            # Use substitute if main product unavailable
            product_id = ingredient["mapped_product_id"]
            if ingredient["availability_status"] != "available":
                product_id = ingredient.get("substitute_product_id")
            
            # Build cart item
            cart_item = {
                "product_id": product_id,
                "product_name": ingredient["product_name"],
                "quantity": ingredient["quantity"],
                "unit": ingredient["unit"],
                "price": ingredient["product_price"],
                "subtotal": ingredient["product_price"] * ingredient["quantity"],
                "from_meal_plan": True,
                "meal_ingredient": ingredient["ingredient_name"]
            }
            
            added_items.append(cart_item)
            total_amount += cart_item["subtotal"]
        
        return {
            "user_cart_id": user_cart_id,
            "added_count": len(added_items),
            "skipped_count": len(skipped_items),
            "total_amount": total_amount,
            "items": added_items,
            "skipped_items": skipped_items
        }

    
    