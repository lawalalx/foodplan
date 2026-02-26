"""
Ingredient to product mapping and QuickMarket catalog integration.
Handles matching AI-generated ingredients to available products.
"""
import logging
from typing import Optional, List, Dict, Tuple
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)


class IngredientProductMapper:
    """Maps generic ingredients to QuickMarket products with flexible matching."""
    
    def __init__(self, product_catalog: Optional[List[Dict]] = None):
        """
        Initialize mapper with optional pre-loaded catalog.
        
        Args:
            product_catalog: List of product dicts with {id, name, category, price, availability}
        """
        self.product_catalog = product_catalog or []
        self.ingredient_aliases = self._load_ingredient_aliases()
        self.category_mappings = self._load_category_mappings()

    
    def map_ingredient_to_product(
        self,
        ingredient_name: str,
        quantity: float,
        unit: str
    ) -> Dict:
        # 1. Normalize (Alias check + lowercase/strip)
        normalized = self._normalize_ingredient_name(ingredient_name)
        
        # 2. Multi-Field Search (Name + Descriptions)
        match = self._find_exact_match(normalized)
        
        # 3. Fuzzy Match Fallback (If exact/desc match failed)
        if not match:
            fuzzy_results = self._find_fuzzy_matches(normalized)
            if fuzzy_results:
                match = fuzzy_results[0]
                confidence = match["confidence"]
        else:
            confidence = 0.95

        # 5. Build Result
        if match:
            return self._build_mapping_result(
                ingredient_name, quantity, unit, match, confidence
            )

        return {
            "ingredient_name": ingredient_name,
            "quantity": quantity,
            "unit": unit,
            "mapped_product_id": None,
            "product_name": None,
            "product_price": 0,
            "availability_status": "unavailable",
            "confidence_score": 0.0,
            "notes": f"No product match found for '{ingredient_name}'"
        }


    def _normalize_ingredient_name(self, name: str) -> str:
        for alias_list, canonical in self.ingredient_aliases.items():
            if name.lower() in [a.lower() for a in alias_list]:
                return canonical.lower()

        return name.lower().strip()
    
    
    def _load_ingredient_aliases(self) -> Dict[Tuple[str, ...], str]:
        """Load map of ingredient aliases to canonical names."""
        return {
            # Grains
            ("long grain rice", "rice", "white rice"): "Rice",
            ("jollof rice", "parboiled rice"): "Parboiled Rice",
            ("cornmeal", "pap flour", "corn flour"): "Cornmeal",
            ("garri", "gari"): "Garri",
            ("millet", "millet flour"): "Millet",
            
            # Proteins
            ("chicken", "poultry"): "Chicken",
            ("beef", "cow meat"): "Beef",
            ("fish", "seafood", "frozen fish"): "Fish",
            ("crayfish", "dried shrimp", "shrimp"): "Crayfish",
            ("stockfish", "dried fish"): "Stockfish",
            ("eggs", "chicken eggs"): "Eggs",
            
            # Legumes
            ("beans", "black-eyed beans", "kidney beans"): "Beans",
            ("lentils", "red lentils"): "Lentils",
            ("peas", "split peas"): "Peas",
            
            # Vegetables
            ("tomato", "fresh tomato"): "Tomato",
            ("onion", "white onion"): "Onion",
            ("pepper", "hot pepper", "scotch bonnet", "chilli"): "Pepper",
            ("bell pepper", "green pepper", "sweet pepper"): "Bell Pepper",
            ("spinach", "leafy greens"): "Spinach",
            ("carrot", "carrots"): "Carrot",
            ("cucumber", "cucumbers"): "Cucumber",
            
            # Oils & Seasonings
            ("palm oil", "red oil"): "Palm Oil",
            ("vegetable oil", "cooking oil"): "Vegetable Oil",
            ("tomato paste", "tomato puree"): "Tomato Paste",
            ("egusi", "melon seeds"): "Egusi",
            ("salt", "table salt"): "Salt",
            ("garlic", "garlic cloves"): "Garlic",
            ("ginger", "ginger root"): "Ginger",
            ("curry powder", "curry"): "Curry Powder",
            ("thyme", "dried thyme"): "Thyme",
        }

    
    def _load_category_mappings(self) -> Dict[str, List[str]]:
        """Map ingredient categories to QuickMarket categories."""
        return {
            "grains": [
                "rice", "cornmeal", "garri", "millet", "bread flour"
            ],
            "proteins": [
                "chicken", "beef", "fish", "eggs", "crayfish", "stockfish"
            ],
            "legumes": [
                "beans", "lentils", "peas"
            ],
            "vegetables": [
                "tomato", "onion", "pepper", "spinach", "carrot", "cucumber"
            ],
            "oils": [
                "palm oil", "vegetable oil"
            ],
            "seasonings": [
                "salt", "garlic", "ginger", "curry powder", "thyme", "tomato paste"
            ],
            "dairy": [
                "milk", "cheese", "butter", "yogurt"
            ],
        }
    

    def _find_exact_match(self, ingredient_name: str) -> Optional[Dict]:
        """
            Enhanced search: Handles singular/plural forms, punctuation,
            and searches across name + short/long descriptions.
        """
        # Normalize input
        query = re.sub(r'[^\w\s]', '', ingredient_name.lower().strip())
        
        # Generate plural form (simple 's' addition)
        if not query.endswith('s'):
            query_plural = query + 's'
        else:
            query_plural = query[:-1]  # singular fallback

        for product in self.product_catalog:
            # Normalize product fields
            name = re.sub(r'[^\w\s]', '', product.get("name", "").lower())
            short_desc = re.sub(r'[^\w\s]', '', product.get("short_description", "").lower())
            long_desc = re.sub(r'[^\w\s]', '', product.get("long_description", "").lower())

            combined_text = f"{name} {short_desc} {long_desc}"

            # Check direct match
            tokens = combined_text.split()
            if query in tokens:
                return product

            # Check plural/singular forms
            if re.search(r'\b' + re.escape(query_plural) + r'\b', combined_text):
                return product
            
        return None


    def _find_fuzzy_matches(self, ingredient_name: str, threshold: float = 0.7) -> list:
        """
        Fuzzy match fallback: handles minor typos or variations.
        """
        matches = []
        query = ingredient_name.lower().strip()
        
        for product in self.product_catalog:
            text = " ".join([
                product.get("name", ""),
                product.get("short_description", ""),
                product.get("long_description", "")
            ]).lower()

            similarity = SequenceMatcher(None, query, text).ratio()
            
            if similarity >= threshold:
                product_with_confidence = product.copy()
                product_with_confidence["confidence"] = similarity
                matches.append(product_with_confidence)

        # Sort by confidence descending
        return sorted(matches, key=lambda x: x["confidence"], reverse=True)


    def _build_mapping_result(
        self,
        ingredient_name: str,
        quantity: float,
        unit: str,
        product: Dict,
        confidence: float
    ) -> Dict:
        """Build the result mapping."""
        availability = product.get("availability_status", "available")
        substitute = None
        
        # If not available, try to find substitute in same category
        if availability != "available":
            category = product.get("category", "")
            substitutes = self._find_by_category(category)
            if len(substitutes) > 1:  # More than current product
                substitute = substitutes[1]
        
        return {
            "ingredient_name": ingredient_name,
            "quantity": quantity,
            "unit": unit,
            "mapped_product_id": product.get("id"),
            "product_name": product.get("name"),
            "product_price": product.get("base_price"),
            "availability_status": availability,
            "confidence_score": confidence,
            "notes": f"Mapped with {confidence:.0%} confidence"
        }
    
    
    def update_catalog(self, new_products: List[Dict]):
        """Update product catalog (for real-time price/availability updates)."""
        self.product_catalog = new_products
        logger.info(f"Product catalog updated with {len(new_products)} products")




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

    
    