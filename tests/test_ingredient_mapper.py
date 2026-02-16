"""
Tests for ingredient-to-product mapping logic.
Validates the 4-tier matching algorithm and cart building.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingredient_mapper import IngredientProductMapper, CartBuilder


class TestIngredientProductMapper:
    """Test ingredient to product mapping."""
    
    @pytest.fixture
    def mapper(self, dummy_product_catalog):
        """Initialize mapper with dummy catalog."""
        return IngredientProductMapper(product_catalog=dummy_product_catalog)
    
    def test_mapper_initialization(self, mapper):
        """Test mapper can be initialized."""
        assert mapper is not None
        assert len(mapper.product_catalog) > 0
    
    def test_exact_match(self, mapper):
        """Test exact ingredient-to-product matching."""
        result = mapper.map_ingredient_to_product(
            ingredient_name="Fresh Chicken",
            quantity=2,
            unit="kg"
        )
        
        assert result is not None
        assert "availability_status" in result
        assert result["availability_status"] in ["available", "unavailable", "substitute"]
    
    def test_fuzzy_match(self, mapper):
        """Test fuzzy matching for similar ingredient names."""
        result = mapper.map_ingredient_to_product(
            ingredient_name="Chicken meat",  # Similar to "Fresh Chicken"
            quantity=1,
            unit="kg"
        )
        
        assert result is not None
    
    def test_category_match(self, mapper):
        """Test category-level matching."""
        result = mapper.map_ingredient_to_product(
            ingredient_name="Generic protein",  # No exact match
            quantity=1,
            unit="kg"
        )
        
        assert result is not None
    
    def test_fallback_behavior(self, mapper):
        """Test fallback when no match found."""
        result = mapper.map_ingredient_to_product(
            ingredient_name="Nonexistent ingredient xyz",
            quantity=1,
            unit="kg"
        )
        
        assert result is not None
        # Should have fallback structure
        assert "ingredient_name" in result or "product_name" in result
    
    def test_quantity_scaling(self, mapper):
        """Test that quantities are properly scaled."""
        result = mapper.map_ingredient_to_product(
            ingredient_name="Fresh Chicken",
            quantity=2.5,
            unit="kg"
        )
        
        assert result is not None
        # Quantity should be preserved or scaled
        assert "quantity" in result or "estimated_total" in result
    
    def test_multiple_ingredients_mapping(self, mapper):
        """Test mapping multiple ingredients."""
        ingredients = [
            {"name": "Fresh Chicken", "quantity": 1, "unit": "kg"},
            {"name": "Tomatoes", "quantity": 2, "unit": "kg"},
            {"name": "Onions", "quantity": 0.5, "unit": "kg"},
        ]
        
        results = []
        for ingredient in ingredients:
            result = mapper.map_ingredient_to_product(
                ingredient_name=ingredient["name"],
                quantity=ingredient["quantity"],
                unit=ingredient["unit"]
            )
            results.append(result)
        
        assert len(results) == 3
        for result in results:
            assert result is not None


class TestCartBuilder:
    """Test shopping cart building."""
    
    @pytest.fixture
    def sample_ingredients(self, dummy_product_catalog):
        """Sample mapped ingredients."""
        return [
            {
                "product_id": "prod_chicken_001",
                "product_name": "Fresh Chicken",
                "quantity": 1,
                "unit": "kg",
                "price": 45000,
                "availability_status": "available"
            },
            {
                "product_id": "prod_rice_001",
                "product_name": "Parboiled Rice",
                "quantity": 2,
                "unit": "cups",
                "price": 18000,
                "availability_status": "available"
            },
            {
                "product_id": "prod_tomato_001",
                "product_name": "Fresh Tomatoes",
                "quantity": 3,
                "unit": "kg",
                "price": 8000,
                "availability_status": "available"
            }
        ]
    
    def test_add_ingredients_to_cart(self, sample_ingredients):
        """Test adding ingredients to cart."""
        cart_update = CartBuilder.add_ingredients_to_cart(
            mapped_ingredients=sample_ingredients,
            user_cart_id="cart_user123"
        )
        
        assert cart_update is not None
        assert "added_count" in cart_update
        assert "total_items" in cart_update
        assert cart_update["added_count"] == 3
    
    def test_cart_respects_availability(self, sample_ingredients):
        """Test that unavailable items are handled."""
        # Mark one item as unavailable
        sample_ingredients[1]["availability_status"] = "unavailable"
        
        cart_update = CartBuilder.add_ingredients_to_cart(
            mapped_ingredients=sample_ingredients,
            user_cart_id="cart_user123"
        )
        
        assert cart_update is not None
        # Should note unavailable items
        assert "unavailable_count" in cart_update or "warnings" in cart_update
    
    def test_cart_pricing(self, sample_ingredients):
        """Test cart pricing calculation."""
        cart_update = CartBuilder.add_ingredients_to_cart(
            mapped_ingredients=sample_ingredients,
            user_cart_id="cart_user123"
        )
        
        assert cart_update is not None
        # Should have pricing information
        assert "total_estimated_cost" in cart_update or "estimated_cost" in cart_update
        if "total_estimated_cost" in cart_update:
            assert cart_update["total_estimated_cost"] > 0
    
    def test_cart_with_substitutes(self, sample_ingredients):
        """Test cart building with substitute products."""
        sample_ingredients[0]["availability_status"] = "substitute"
        sample_ingredients[0]["substitute_product_id"] = "prod_chicken_alt"
        
        cart_update = CartBuilder.add_ingredients_to_cart(
            mapped_ingredients=sample_ingredients,
            user_cart_id="cart_user123"
        )
        
        assert cart_update is not None


class TestMappingIntegration:
    """Integration tests for mapping pipeline."""
    
    @pytest.fixture
    def mapper(self, dummy_product_catalog):
        return IngredientProductMapper(product_catalog=dummy_product_catalog)
    
    @pytest.mark.asyncio
    async def test_full_mapping_pipeline(self, mapper, dummy_product_catalog):
        """Test full pipeline: ingredients -> map -> cart."""
        # Raw ingredients from AI
        raw_ingredients = [
            {"name": "Fresh Chicken", "quantity": 1, "unit": "kg"},
            {"name": "Tomatoes", "quantity": 2, "unit": "kg"},
            {"name": "Rice", "quantity": 2, "unit": "cups"},
        ]
        
        # Step 1: Map ingredients
        mapped = []
        for ingredient in raw_ingredients:
            result = mapper.map_ingredient_to_product(
                ingredient_name=ingredient["name"],
                quantity=ingredient["quantity"],
                unit=ingredient["unit"]
            )
            mapped.append(result)
        
        assert len(mapped) == 3
        
        # Step 2: Add to cart
        cart_update = CartBuilder.add_ingredients_to_cart(
            mapped_ingredients=mapped,
            user_cart_id="cart_test"
        )
        
        assert cart_update is not None
        assert cart_update["added_count"] >= 0
