#!/usr/bin/env python
"""
Quick validation script for the meal planning system.
Checks all dependencies, database connection, and system readiness.
"""
import os
import sys
import asyncio
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


async def check_environment():
    """Check environment variables."""
    print("\n📋 Checking Environment Setup...")
    print("-" * 50)
    
    required_vars = {
        "DATABASE_URL": "PostgreSQL connection string",
        "GROQ_API_KEY": "LLM API key for meal generation"
    }
    
    missing = []
    for var, description in required_vars.items():
        if os.environ.get(var):
            print(f"✓ {var}: Set ({description})")
        else:
            print(f"✗ {var}: Missing ({description})")
            missing.append(var)
    
    if missing:
        print(f"\n⚠️  Missing variables: {', '.join(missing)}")
        print("   Configure in .env or as environment variables")
        return False
    return True


async def check_dependencies():
    """Check Python dependencies."""
    print("\n📦 Checking Dependencies...")
    print("-" * 50)
    
    required_packages = {
        "fastapi": "FastAPI web framework",
        "uvicorn": "ASGI server",
        "sqlmodel": "SQLModel ORM",
        "sqlalchemy": "SQLAlchemy async support",
        "asyncpg": "Async PostgreSQL driver",
        "pydantic": "Data validation",
        "langchain_groq": "ChatGroq integration"
    }
    
    missing = []
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {package}: Installed ({description})")
        except ImportError:
            print(f"✗ {package}: Missing ({description})")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Install missing packages:")
        print(f"   pip install {' '.join(missing)}")
        return False
    return True


async def check_database_connection():
    """Check database connectivity."""
    print("\n🗄️  Checking Database Connection...")
    print("-" * 50)
    
    try:
        from config import check_db_connection
        
        db_ok = await check_db_connection()
        if db_ok:
            print("✓ Database connection successful")
            return True
        else:
            print("✗ Database connection failed")
            print("   Check DATABASE_URL_NEON in .env")
            return False
    except Exception as e:
        print(f"✗ Database check error: {e}")
        return False


async def check_models():
    """Check that all models are valid."""
    print("\n📊 Checking Database Models...")
    print("-" * 50)
    
    try:
        from models import (
            User, UserPreference, MealPlan, PlanMeal, PlanMealIngredient,
            PurchaseHistory, MealFeedback, Ingredient, MealTemplate
        )
        
        models = [
            User, UserPreference, MealPlan, PlanMeal, PlanMealIngredient,
            PurchaseHistory, MealFeedback, Ingredient, MealTemplate
        ]
        
        for model in models:
            print(f"✓ {model.__name__}: Valid SQLModel")
        
        print(f"\n✓ All {len(models)} database models are valid")
        return True
    except Exception as e:
        print(f"✗ Model validation error: {e}")
        return False


async def check_services():
    """Check that core services can be initialized."""
    print("\n⚙️  Checking Services...")
    print("-" * 50)
    
    try:
        from meal_planner import MealPlanGenerator, IngredientGenerator
        from ingredient_mapper import IngredientProductMapper
        from learning_system import UserLearningSystem
        
        services = {
            "MealPlanGenerator": MealPlanGenerator,
            "IngredientGenerator": IngredientGenerator,
            "IngredientProductMapper": IngredientProductMapper,
            "UserLearningSystem": UserLearningSystem
        }
        
        for name, service_class in services.items():
            try:
                if name == "IngredientProductMapper":
                    service = service_class(product_catalog=[])
                else:
                    service = service_class()
                print(f"✓ {name}: Initialized")
            except Exception as e:
                print(f"✗ {name}: Failed - {e}")
                return False
        
        print(f"\n✓ All {len(services)} services initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Service initialization error: {e}")
        return False


async def run_health_checks():
    """Run all health checks."""
    print("\n" + "=" * 60)
    print("🔍 MEAL PLANNING SYSTEM - HEALTH CHECK")
    print("=" * 60)
    
    checks = [
        ("Environment", check_environment),
        ("Dependencies", check_dependencies),
        ("Models", check_models),
        ("Services", check_services),
        ("Database", check_database_connection),
    ]
    
    results = {}
    for check_name, check_func in checks:
        try:
            results[check_name] = await check_func()
        except Exception as e:
            print(f"\n✗ {check_name} check failed: {e}")
            results[check_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {check_name}")
    
    print(f"\nTotal: {passed}/{total} checks passed\n")
    
    if passed == total:
        print("🎉 System is ready! You can start the server:")
        print("   uvicorn main:app --reload")
        return True
    else:
        print("⚠️  Some checks failed. Please fix issues before starting server.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(run_health_checks())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏸️  Checks interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)
