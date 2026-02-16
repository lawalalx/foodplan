"""
MEAL PLANNING SYSTEM ARCHITECTURE
QuickMarket AI-Powered Meal Planner

This document describes the complete implementation of the meal planning feature
that helps users plan meals, generate ingredient lists, and purchase directly
from QuickMarket.
"""

# ============================================================================
# EXECUTIVE SUMMARY
# ============================================================================
"""
PRODUCT GOAL:
Help users plan meals easily and reduce decision fatigue by providing:
1. AI-generated meal plans (weekly/monthly)
2. Automatic ingredient list generation
3. Direct mapping to QuickMarket products
4. Seamless checkout
5. Personalization based on purchase history

NORTH STAR METRIC:
A user can go from "I don't know what to eat this week" → meal plan → ingredients → checkout
in one continuous flow.

TARGET USERS:
- Type A: New/Cold Users (no purchase history)
  → Use AI with preferences (dietary, budget, household size)
- Type B: Returning Users (have purchase history)
  → AI personalizes using past behavior + preferences
"""

# ============================================================================
# SYSTEM ARCHITECTURE
# ============================================================================
"""
┌─────────────────────────────────────────────────────────────────┐
│                        FASTAPI APPLICATION                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   API ENDPOINTS                          │  │
│  │  /meal-planning/preferences     → Save user preferences │  │
│  │  /meal-planning/generate        → Generate meal plan    │  │
│  │  /meal-planning/ingredients     → Get ingredients       │  │
│  │  /meal-planning/add-to-cart     → Add to cart           │  │
│  │  /meal-planning/feedback        → Record feedback       │  │
│  │  /meal-planning/recommendations → Get personalized recs │  │
│  └──────────────────────────────────────────────────────────┘  │
│           ↓                    ↓                   ↓             │
│  ┌────────────────────┐  ┌──────────────┐  ┌──────────┐        │
│  │ MealPlanGenerator  │  │ Ingredient   │  │ Learning │        │
│  │ (LLM-based)        │  │ ProductMapper│  │ System   │        │
│  │                    │  │              │  │          │        │
│  │ Uses:              │  │ Uses:        │  │ Tracks:  │        │
│  │ - ChatGroq         │  │ - Fuzzy      │  │ - Views  │        │
│  │ - Preferences      │  │   matching   │  │ - Selects│        │
│  │ - Purchase history │  │ - Keywords   │  │ - Purchases
│  │ - Budget/diet      │  │ - Categories │  │ - Ratings│        │
│  └────────────────────┘  └──────────────┘  └──────────┘        │
│           ↓                    ↓                   ↓             │
│  ┌────────────────────┐  ┌──────────────┐  ┌──────────┐        │
│  │  DATABASE (SQL)    │  │  VECTOR DB   │  │  CACHE   │        │
│  │  (SQLAlchemy)      │  │  (Optional)  │  │  (Redis) │        │
│  │                    │  │              │  │          │        │
│  │ Tables:            │  │ - Embeddings │  │ - User   │        │
│  │ - users            │  │ - Meals      │  │   profiles
│  │ - preferences      │  │ - Ingredients│  │ - Meal   │        │
│  │ - meal_plans       │  │              │  │   popularity
│  │ - plan_meals       │  │              │  │          │        │
│  │ - meal_ingredients │  │              │  │          │        │
│  │ - purchase_history │  │              │  │          │        │
│  │ - meal_feedback    │  │              │  │          │        │
│  └────────────────────┘  └──────────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
"""

# ============================================================================
# MODULES OVERVIEW
# ============================================================================

"""
1. MODELS (models.py)
   ├─ User                    → User accounts (new & returning)
   ├─ UserPreference          → User meal preferences
   ├─ MealPlan                → Generated meal plans
   ├─ PlanMeal                → Individual meals in a plan
   ├─ PlanMealIngredient      → Ingredients with product mapping
   ├─ PurchaseHistory         → User's past purchases
   ├─ MealFeedback            → User feedback signals
   ├─ Ingredient              → Global ingredient catalog
   └─ MealTemplate            → Predefined meal templates

2. MEAL PLANNER (meal_planner.py)
   ├─ MealPlanGenerator
   │  ├─ generate_meal_plan()      → Create AI meal plan
   │  ├─ _build_user_context()     → Prepare context from preferences/history
   │  ├─ _create_meal_plan_prompt() → LLM prompt engineering
   │  └─ _parse_meal_plan_response() → JSON parsing
   └─ IngredientGenerator
      ├─ generate_ingredients()    → Get ingredient list for meal
      ├─ _load_ingredient_templates() → Load predefined recipes
      └─ _parse_ingredients_response() → Parse LLM output

3. INGREDIENT MAPPER (ingredient_mapper.py)
   ├─ IngredientProductMapper
   │  ├─ map_ingredient_to_product() → Find matching QuickMarket product
   │  ├─ _find_exact_match()       → Exact product search
   │  ├─ _find_fuzzy_matches()     → Similarity-based matching
   │  ├─ _infer_ingredient_category() → Category detection
   │  └─ update_catalog()          → Real-time price/availability
   └─ CartBuilder
      └─ add_ingredients_to_cart() → Build shopping cart

4. LEARNING SYSTEM (learning_system.py)
   ├─ UserLearningProfile       → Per-user behavior tracking
   ├─ UserLearningSystem
   │  ├─ record_feedback()          → Log user interactions
   │  ├─ get_recommendations()      → Personalized suggestions
   │  ├─ get_user_insights()        → Analytics dashboard
   │  └─ record_ingredient_removal() → Track preferences
   └─ MealFeedback                  → Feedback data class

5. API ENDPOINTS (api_endpoints.py)
   ├─ /preferences              → Save/update user preferences
   ├─ /generate                 → Generate meal plan
   ├─ /ingredients              → Get meal ingredients
   ├─ /add-to-cart              → Add ingredients to cart
   ├─ /feedback                 → Record user feedback
   ├─ /history                  → Get meal history
   ├─ /recommendations          → Get personalized meals
   └─ /health                   → Service health check
"""

# ============================================================================
# USER WORKFLOWS
# ============================================================================

"""
WORKFLOW 1: NEW USER (PREFERENCE-BASED)
═════════════════════════════════════════

1. ENTRY POINT
   User clicks "Generate Meal Plan" on home or meal planner tab

2. PREFERENCE CAPTURE
   System asks for:
   ✓ Meal duration (weekly/monthly)
   ✓ Meals per day (breakfast/lunch/dinner)
   ✓ Dietary preferences (Nigerian/vegetarian/protein-heavy/budget)
   ✓ Household size (1, 3, 5+ people)

3. MEAL PLAN GENERATION
   POST /api/v1/meal-planning/generate
   {
     "user_id": "user_123",
     "duration": "weekly",
     "use_preference_history": false
   }
   
   Returns:
   {
     "meal_plan_id": "plan_456",
     "meal_plan": {
       "day_1": {
         "breakfast": "Pap & Akara",
         "lunch": "Egusi Soup & Swallow",
         "dinner": "Jollof Rice & Stew"
       },
       ...
     }
   }

4. MEAL SELECTION
   User taps meal → System opens meal detail view

5. INGREDIENT GENERATION
   POST /api/v1/meal-planning/ingredients
   {
     "meal_name": "Egusi Soup",
     "household_size": 3
   }
   
   Returns:
   {
     "meal_name": "Egusi Soup",
     "ingredients": [
       {
         "ingredient_name": "Egusi seeds",
         "quantity": 500,
         "unit": "g",
         "mapped_product_id": "prod_123",
         "product_name": "Ground Egusi (500g pack)",
         "product_price": 2500,
         "availability_status": "available"
       },
       ...
     ]
   }

6. ADD TO CART
   POST /api/v1/meal-planning/add-to-cart
   {
     "user_id": "user_123",
     "meal_plan_id": "plan_456",
     "meal_name": "Egusi Soup",
     "ingredients": [...]
   }

7. CHECKOUT
   → Standard QuickMarket checkout flow


WORKFLOW 2: RETURNING USER (HISTORY-BASED)
═════════════════════════════════════════

1. ENTRY POINT
   Same as new user OR personalized recommendation

2. PREFERENCE CAPTURE
   System automatically pulls:
   ✓ Past purchases
   ✓ Frequently bought ingredients
   ✓ Common meal patterns
   → Still allows manual override

3. MEAL PLAN GENERATION
   Same as new user, but AI receives purchase history context:
   Context: "User frequently buys rice, beans, chicken, tomato paste.
            Household size: 2 people. Budget: moderate."

4-7. MEAL SELECTION → CHECKOUT
   Same as new user


WORKFLOW 3: PERSONALIZATION & LEARNING
═══════════════════════════════════════

After each interaction, system records feedback:

✓ Meal viewed
  POST /api/v1/meal-planning/feedback
  {"user_id": "user_123", "feedback_type": "viewed", "meal_name": "..."}

✓ Meal selected
✓ Ingredients purchased
✓ Ingredients removed (signals allergies/preferences)
✓ Meal actually cooked
✓ User rating (1-5 stars)

Learning system uses signals to:
1. Track favorite meals
2. Identify dietary patterns
3. Build recommendation model
4. Cross-sell similar meals
5. Improve future personalization
"""

# ============================================================================
# EPIC 1: MEAL PLAN GENERATION (AI)
# ============================================================================

"""
USER STORY 1: Entry into Meal Planning
───────────────────────────────────────
As a user, I want to generate a meal plan, so that I know what to cook without stress.

Entry point:
- Home page "Generate Meal Plan" button
- Dedicated "Meal Planner" tab
- WhatsApp command: "Generate my meal plan"

Flow: User clicks button → System serves preference form → Submit → Generate


USER STORY 2: Preference Capture
─────────────────────────────────
For NEW USERS:
  System asks:
  - Meal duration (weekly/monthly)
  - Meals per day (breakfast/lunch/dinner) 
  - Dietary preferences (Nigerian/vegetarian/protein-heavy/budget-friendly)
  - Household size (optional)

For RETURNING USERS:
  System automatically pulls:
  - Past purchases
  - Frequently bought ingredients
  - Common meal patterns
  - Still allows manual override

Implementation: /api/v1/meal-planning/preferences [POST]


USER STORY 3: AI Meal Plan Generation
──────────────────────────────────────
As a user, I want the system to generate a meal plan,
so that I can see what meals I'll eat over time.

System Logic:
- Receive user preferences OR purchase history
- Call LLM (ChatGroq) with context
- LLM generates meal plan (calendar-based)
- Parse response and validate JSON

Output example:
{
  "day_1": {
    "breakfast": "Pap & Akara",
    "lunch": "Egusi Soup & Swallow",
    "dinner": "Rice & Stew"
  },
  "day_2": { ... }
}

Implementation: /api/v1/meal-planning/generate [POST]


USER STORY 4: Viewing & Selecting Meals
────────────────────────────────────────
As a user, I want to tap on a meal, so that I can see the details and cook it.

Flow:
1. Display meal plan calendar
2. User taps meal (e.g., "Egusi Soup")
3. System records "viewed" signal
4. Open meal detail view with:
   - Meal name and description
   - Estimated cook time
   - Difficulty level
   - "Get ingredients" button
"""

# ============================================================================
# EPIC 2: INGREDIENT GENERATION & PURCHASE
# ============================================================================

"""
USER STORY 5: Ingredient Generation
────────────────────────────────────
As a user, I want to see the ingredients for a meal,
so that I can cook it correctly.

System Logic:
- Receive meal name
- Call LLM to generate ingredient list
- Adjust quantities for household size
- Return with units (kg, cups, pieces, etc.)

Example:
Egusi Soup (for 3 people):
- Egusi seeds – 500g
- Palm oil – 250ml
- Beef – 1kg
- Stockfish – 2 pieces
- Crayfish – 100g
- Pepper – 5 pieces

Implementation: /api/v1/meal-planning/ingredients [POST]


USER STORY 6: Ingredient Availability Mapping
──────────────────────────────────────────────
As a user, I want to buy ingredients directly,
so that I don't have to search manually.

System processes each ingredient:
1. Normalize ingredient name
2. Try exact match in QuickMarket catalog
3. Try fuzzy/similarity match
4. Try category-based match
5. Mark as available/unavailable/substitute

Ingredient states:
- Available: ✓ Show product and price
- Unavailable: Show "Out of stock", offer substitute
- Substitute: Recommend similar product

Mapping confidence scores:
- Exact match: 0.95+
- Fuzzy match: 0.70-0.95
- Category match: 0.50-0.70
- No match: 0.0

Implementation: IngredientProductMapper.map_ingredient_to_product()


USER STORY 7: Add Ingredients to Cart
──────────────────────────────────────
As a user, I want to add all ingredients to my cart,
so that I can check out quickly.

Features:
- "Add All Ingredients to Cart" button
- User can remove items
- User can adjust quantities
- System adds as standard products
- Cart shows total cost estimate

POST /api/v1/meal-planning/add-to-cart
{
  "user_id": "user_123",
  "meal_plan_id": "plan_456",
  "meal_name": "Egusi Soup",
  "ingredients": [...]
}
"""

# ============================================================================
# EPIC 3: CHECKOUT & LEARNING LOOP
# ============================================================================

"""
USER STORY 8: Checkout
──────────────────────
Normal checkout flow (QuickMarket standard)
Delivery fees & rules apply as usual
Meal plan origin is transparent

After checkout:
- System records "purchased" signal
- Links meal to actual order
- Prepares for "cooked" signal


USER STORY 9: Feedback & Learning
──────────────────────────────────
As the system, I want to learn from user behavior,
so that future meal plans are better.

Signals Captured:
- Meals viewed
- Meals selected
- Ingredients purchased
- Ingredients removed (allergies/preferences)
- Repeat cooking behavior
- User ratings (1-5 stars)

Used for:
1. Better personalization
   → Future recommendations weight user preferences
2. Smarter meal suggestions
   → Recommend similar meals to favorites
3. Cross-selling
   → Suggest ingredients they frequently buy
4. Analytics dashboard
   → Show user their cooking patterns

Implementation:
POST /api/v1/meal-planning/feedback
{
  "user_id": "user_123",
  "meal_name": "Egusi Soup",
  "feedback_type": "viewed|selected|purchased|cooked",
  "rating": 4
}

UserLearningSystem tracks:
- Favorite meals (by selection count)
- Favorite ingredients (by purchase count)
- Removed ingredients (allergen/preference detection)
- Cooking frequency (meal_name -> [dates])
- User ratings
"""

# ============================================================================
# KEY DESIGN PATTERNS & CONSTRAINTS
# ============================================================================

"""
PRODUCT CONSTRAINTS (Non-Negotiable)
────────────────────────────────────
1. Meal planning works WITHOUT purchase history
   → Must support preference-based generation for new users

2. Ingredient generation must be:
   ✓ Deterministic (same meal = same ingredients)
   ✓ Editable (user can adjust quantities)
   ✓ Flexible (works with various household sizes)

3. AI logic should be stateless
   ✓ No session dependencies
   ✓ Context packaged in request
   ✓ Easy to scale horizontally

4. Ingredient → Product mapping must be flexible
   ✓ Not 1:1 hardcoded
   ✓ Support fuzzy matching
   ✓ Handle substitutions
   ✓ Work with new products added to catalog


FLOW PRINCIPLES
───────────────
1. Continuous flow: prefs → plan → ingredients → cart → checkout
   → No friction points or required clicks

2. Smart defaults
   → New user: use popular meals
   → Returning user: personalize with history

3. Progressive personalization
   → Starts generic (preferences)
   → Improves over time (purchase history)
   → Becomes highly personalized (learning)

4. Async-friendly
   → Can queue meal plan generation
   → Can batch catalog updates
   → Can refresh recommendations in background
"""

# ============================================================================
# DEPLOYMENT & INTEGRATION
# ============================================================================

"""
DATABASE SETUP
──────────────
Prerequisites:
- PostgreSQL 12+ (or any SQLAlchemy-compatible DB)
- SQLAlchemy 2.0+

Setup:
1. Create migration using Alembic:
   alembic revision --autogenerate -m "Add meal planning tables"

2. Run migration:
   alembic upgrade head

3. Seed data:
   python scripts/seed_meal_templates.py


LLM CONFIGURATION
─────────────────
Model: ChatGroq (Mixtral 8x7B)
- Fast inference
- Good instruction following
- Token-efficient

Requirements:
- GROQ_API_KEY environment variable
- Temperature: 0.7 (some creativity, but controlled)
- Max tokens: 2000 (enough for meal plan)

Alternative models:
- GPT-4 (more reliable but expensive)
- Claude 3 (better quality but slower)
- Local Ollama (privacy-first option)


PRODUCT CATALOG INTEGRATION
───────────────────────────
Sync with QuickMarket catalog:
1. Set up webhook for product updates
2. Periodic scrape/cache of products
3. Real-time price/availability checks
4. Build search index for ingredients

Categories needed:
- Grains (rice, cornmeal, garri)
- Proteins (chicken, beef, fish)
- Vegetables (tomato, onion, pepper)
- Legumes (beans, lentils)
- Oils & Fats (palm oil, vegetable oil)
- Seasonings (salt, spices, pastes)
- Dairy (milk, cheese, butter)
- Others (eggs, bread, etc.)


API DEPLOYMENT
──────────────
Framework: FastAPI
Server: Uvicorn + Gunicorn
Scale: 2+ workers

Endpoints:
POST   /api/v1/meal-planning/preferences
POST   /api/v1/meal-planning/generate
GET    /api/v1/meal-planning/history/{user_id}
POST   /api/v1/meal-planning/ingredients
POST   /api/v1/meal-planning/add-to-cart
POST   /api/v1/meal-planning/feedback
GET    /api/v1/meal-planning/recommendations/{user_id}
GET    /api/v1/meal-planning/health

Rate limits:
- Anonymous: 10 req/min
- Authenticated: 100 req/min
- Bot detection: 5 req/sec
"""

# ============================================================================
# FUTURE ENHANCEMENTS
# ============================================================================

"""
PHASE 2: ADVANCED RECOMMENDATIONS
──────────────────────────────────
- Collaborative filtering (users → similar users → meals)
- Content-based filtering (meal features → similar meals)
- Hybrid approach combining both
- A/B test different algorithms
- Feedback loops for recommendation quality

PHASE 3: NUTRITIONAL INTELLIGENCE
──────────────────────────────────
- Store nutritional data per meal/ingredient
- Generate nutrition reports
- Track macros/micros over time
- Health goal tracking (weight loss, muscle gain)
- Dietary requirement recommendations

PHASE 4: COMMUNITY & SOCIAL
───────────────────────────
- Share meal plans with friends
- Community ratings on meals
- User-contributed recipes
- Meal plan challenges
- Leaderboards (most cooked meals)

PHASE 5: ADVANCED PERSONALIZATION
────────────────────────────────
- Video cooking guides
- Smart notifications (low ingredients)
- Seasonal meal adjustments
- Cultural preferences
- Time-of-day meal suggestions
- Integration with fitness trackers

PHASE 6: SUPPLY CHAIN OPTIMIZATION
───────────────────────────────────
- Demand forecasting
- Inventory optimization
- Seasonal pricing
- Bulk discounts for popular meals
- Smart warehouse management
"""

# ============================================================================
# TESTING STRATEGY
# ============================================================================

"""
UNIT TESTS
──────────
- MealPlanGenerator.generate_meal_plan() ✓
- IngredientGenerator.generate_ingredients() ✓
- IngredientProductMapper.map_ingredient_to_product() ✓
- UserLearningSystem methods ✓

INTEGRATION TESTS
─────────────────
- Full workflow: preferences → meal plan → ingredients → cart
- Preference saving and retrieval
- Meal plan persistence
- Feedback recording and retrieval

END-TO-END TESTS
────────────────
- New user workflow
- Returning user workflow
- Ingredient removal learning
- Recommendation accuracy
- Cart total calculations

PERFORMANCE TESTS
─────────────────
- Meal plan generation time (<5s)
- Ingredient mapping time (<2s)
- Product search performance
- Recommendation generation time (<3s)

LOAD TESTS
──────────
- 100 concurrent meal plan requests
- 1000 feedback events/minute
- API endpoints under load
- Database query optimization
"""

print("""
═══════════════════════════════════════════════════════════════════════════════
                 MEAL PLANNING SYSTEM ARCHITECTURE
                         Complete Implementation
═══════════════════════════════════════════════════════════════════════════════

✓ All modules created and documented
✓ Database models defined
✓ AI meal plan generation (LLM-based)
✓ Ingredient generation with portion adjustments
✓ Product mapping with fuzzy matching
✓ Shopping cart builder
✓ User learning system for personalization
✓ Complete API endpoints
✓ End-to-end test suite

STATUS: Ready for integration with main application

NEXT STEPS:
1. Set up database migrations
2. Integrate with QuickMarket product catalog
3. Add authentication middleware
4. Deploy to staging
5. Run load tests
6. Implement monitoring/logging
7. Set up CI/CD pipeline
═══════════════════════════════════════════════════════════════════════════════
""")
