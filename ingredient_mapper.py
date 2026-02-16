"""
Ingredient to product mapping and QuickMarket catalog integration.
Handles matching AI-generated ingredients to available products.
"""
import logging
from typing import Optional, List, Dict, Tuple
from difflib import SequenceMatcher

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
        """
        Map an ingredient to a QuickMarket product.
        
        Args:
            ingredient_name: Name of the ingredient (from meal plan)
            quantity: Quantity needed
            unit: Unit of measurement (kg, ml, pieces, cups, etc.)
            
        Returns:
            Dict with:
            {
                "ingredient_name": "Egusi seeds",
                "quantity": 500,
                "unit": "g",
                "mapped_product_id": "prod_123",
                "product_name": "Ground Egusi (500g pack)",
                "product_price": 2500,
                "availability_status": "available|unavailable|substitute",
                "substitute_product_id": null or "prod_456",
                "confidence_score": 0.95
            }
        """
        # Normalize input
        ingredient_normalized = self._normalize_ingredient_name(ingredient_name)
        
        # Try exact match first
        exact_match = self._find_exact_match(ingredient_normalized)
        if exact_match:
            return self._build_mapping_result(
                ingredient_name, quantity, unit, exact_match, confidence=0.95
            )
        
        # Try fuzzy match
        fuzzy_matches = self._find_fuzzy_matches(ingredient_normalized)
        if fuzzy_matches:
            best_match = fuzzy_matches[0]
            return self._build_mapping_result(
                ingredient_name, quantity, unit, best_match, confidence=best_match["confidence"]
            )
        
        # Try category-based match
        category = self._infer_ingredient_category(ingredient_normalized)
        if category:
            category_matches = self._find_by_category(category)
            if category_matches:
                best_match = category_matches[0]
                return self._build_mapping_result(
                    ingredient_name, quantity, unit, best_match, confidence=0.6
                )
        
        # No match found - return unavailable
        return {
            "ingredient_name": ingredient_name,
            "quantity": quantity,
            "unit": unit,
            "mapped_product_id": None,
            "product_name": None,
            "product_price": None,
            "availability_status": "unavailable",
            "substitute_product_id": None,
            "confidence_score": 0.0,
            "notes": f"No product match found for '{ingredient_name}'. User can search manually."
        }
    
    def _normalize_ingredient_name(self, name: str) -> str:
        """Normalize ingredient name for matching."""
        # Check aliases first
        for alias_list, canonical in self.ingredient_aliases.items():
            if name.lower() in [a.lower() for a in alias_list]:
                return canonical
        
        # Otherwise just lowercase and strip
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
            "grains": ["rice", "cornmeal", "garri", "millet", "bread flour"],
            "proteins": ["chicken", "beef", "fish", "eggs", "crayfish", "stockfish"],
            "legumes": ["beans", "lentils", "peas"],
            "vegetables": ["tomato", "onion", "pepper", "spinach", "carrot", "cucumber"],
            "oils": ["palm oil", "vegetable oil"],
            "seasonings": ["salt", "garlic", "ginger", "curry powder", "thyme", "tomato paste"],
            "dairy": ["milk", "cheese", "butter", "yogurt"],
        }
    
    def _find_exact_match(self, ingredient_name: str) -> Optional[Dict]:
        """Find exact product match in catalog."""
        ingredient_lower = ingredient_name.lower()
        
        for product in self.product_catalog:
            product_name_lower = product.get("name", "").lower()
            
            # Exact match
            if ingredient_lower == product_name_lower:
                return product
            
            # Product name contains ingredient
            if ingredient_lower in product_name_lower:
                return product
        
        return None
    
    def _find_fuzzy_matches(
        self,
        ingredient_name: str,
        threshold: float = 0.7
    ) -> List[Dict]:
        """Find fuzzy matches using sequence matching."""
        matches = []
        
        for product in self.product_catalog:
            product_name = product.get("name", "").lower()
            
            # Calculate similarity
            similarity = SequenceMatcher(
                None, ingredient_name, product_name
            ).ratio()
            
            if similarity >= threshold:
                product_with_confidence = product.copy()
                product_with_confidence["confidence"] = similarity
                matches.append(product_with_confidence)
        
        # Sort by confidence descending
        return sorted(matches, key=lambda x: x["confidence"], reverse=True)
    
    def _infer_ingredient_category(self, ingredient_name: str) -> Optional[str]:
        """Infer ingredient category from name."""
        ingredient_lower = ingredient_name.lower()
        
        for category, keywords in self.category_mappings.items():
            for keyword in keywords:
                if ingredient_lower == keyword or ingredient_lower in keyword:
                    return category
        
        return None
    
    def _find_by_category(self, category: str) -> List[Dict]:
        """Find products in the same category."""
        matches = []
        
        for product in self.product_catalog:
            product_category = product.get("category", "").lower()
            
            if category.lower() in product_category or product_category == category.lower():
                matches.append(product)
        
        return matches[:3]  # Top 3 results
    
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
            "product_price": product.get("price"),
            "availability_status": availability,
            "substitute_product_id": substitute.get("id") if substitute else None,
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
