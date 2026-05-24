import os
import json
import logging
from typing import List, Optional
from google import genai
from google.genai import types
from PIL import Image
import io

logger = logging.getLogger(__name__)

def get_gemini_client() -> Optional[genai.Client]:
    """Dynamically get the Gemini client if the API key is configured."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    api_key_stripped = api_key.strip()
    if not api_key_stripped or api_key_stripped == "YOUR_GEMINI_API_KEY_HERE":
        return None
    try:
        return genai.Client(api_key=api_key_stripped)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini Client: {e}")
        raise ValueError(f"Failed to initialize Gemini Client: {e}")


def generate_mock_data(
    dietary_restrictions: List[str],
    inventory_items: List[str] = None,
    strict_match: bool = False,
    oldest_items: List[str] = None
) -> dict:
    """Generate realistic mock data based on input parameters when API key is missing."""
    # Base set of ingredients
    is_vegetarian = any(r.lower() in ["vegetarian", "vegan"] for r in dietary_restrictions)
    is_halal = any(r.lower() in ["halal"] for r in dietary_restrictions)
    has_peanut_allergy = any("peanut" in r.lower() or "nut" in r.lower() for r in dietary_restrictions)

    # Determine ingredients to return
    if strict_match and inventory_items:
        # Use only items from the inventory list
        detected_names = inventory_items[:5]
    else:
        # Standard fridge ingredients
        detected_names = ["Eggs", "Milk", "Tomatoes", "Cheddar Cheese"]
        if not is_vegetarian:
            detected_names.append("Chicken Breast")
        else:
            detected_names.append("Tofu")
        
        if not has_peanut_allergy:
            detected_names.append("Peanut Butter")
        else:
            detected_names.append("Avocado")

    # Build ingredient objects
    ingredients = []
    category_map = {
        "Eggs": "Dairy/Eggs", "Milk": "Dairy/Eggs", "Cheddar Cheese": "Dairy/Eggs",
        "Tomatoes": "Vegetables", "Tofu": "Proteins", "Chicken Breast": "Proteins",
        "Peanut Butter": "Pantry", "Avocado": "Fruits"
    }
    unit_map = {
        "Eggs": "pcs", "Milk": "ml", "Cheddar Cheese": "grams",
        "Tomatoes": "pcs", "Tofu": "grams", "Chicken Breast": "grams",
        "Peanut Butter": "grams", "Avocado": "pcs"
    }
    quantity_map = {
        "Eggs": 6, "Milk": 500, "Cheddar Cheese": 200,
        "Tomatoes": 3, "Tofu": 300, "Chicken Breast": 400,
        "Peanut Butter": 250, "Avocado": 2
    }

    for name in detected_names:
        cat = category_map.get(name, "Others")
        unit = unit_map.get(name, "pcs")
        qty = quantity_map.get(name, 1.0)
        # Expiration simulation
        days = 3 if name in ["Milk", "Chicken Breast"] else (7 if name in ["Eggs", "Tofu", "Tomatoes"] else 15)
        
        ingredients.append({
            "name": name,
            "quantity": qty,
            "unit": unit,
            "category": cat,
            "days_to_expiration": days
        })

    # Prepare mock recipes
    recipes = []
    
    # Recipe 1: Quick Scramble / Tofu Scramble
    scramble_name = "Quick Egg Scramble" if "Eggs" in detected_names else "Savory Tofu Scramble"
    scramble_ing = ["Eggs" if "Eggs" in detected_names else "Tofu", "Tomatoes"]
    if "Cheddar Cheese" in detected_names:
        scramble_ing.append("Cheddar Cheese")
    
    recipes.append({
        "name": scramble_name,
        "ingredients_used": scramble_ing,
        "instructions": [
            f"Chop the tomatoes into small cubes.",
            f"Heat a non-stick pan over medium heat with a splash of oil.",
            f"Sauté the tomatoes for 2 minutes until slightly soft.",
            f"Whisk the eggs in a bowl (or crumble the tofu) and pour into the pan.",
            f"Gently stir until cooked through. Fold in shredded cheese at the end if desired."
        ],
        "prep_time": "10 mins"
    })

    # Recipe 2: Protein Bowl
    bowl_name = "Kulkas Starter Protein Bowl"
    bowl_ing = ["Chicken Breast" if "Chicken Breast" in detected_names else "Tofu"]
    if "Tomatoes" in detected_names:
        bowl_ing.append("Tomatoes")
    if "Avocado" in detected_names:
        bowl_ing.append("Avocado")
    
    recipes.append({
        "name": bowl_name,
        "ingredients_used": bowl_ing,
        "instructions": [
            f"Season your protein (chicken breast or tofu) with salt, pepper, and herbs.",
            f"Sear in a hot skillet for 5-6 minutes per side until cooked through, then slice.",
            f"Chop the tomatoes and avocado.",
            f"Assemble the sliced protein alongside the fresh veggies in a bowl.",
            f"Drizzle with olive oil or a squeeze of lemon juice."
        ],
        "prep_time": "20 mins"
    })

    # Recipe 3: Simple Pantry Melt
    melt_name = "Cheesy Tomato Melt"
    melt_ing = ["Cheddar Cheese"]
    if "Tomatoes" in detected_names:
        melt_ing.append("Tomatoes")
    
    recipes.append({
        "name": melt_name,
        "ingredients_used": melt_ing,
        "instructions": [
            f"Slice the tomatoes and get your favorite bread slices.",
            f"Layer cheese and tomato slices on the bread.",
            f"Toast in a skillet with butter over medium-low heat until the bread is golden and the cheese is fully melted.",
            f"Cut in half and serve warm."
        ],
        "prep_time": "12 mins"
    })

    # Apply oldest items priority if "Save the Food" is toggled
    if oldest_items:
        # Move recipes using oldest items to the top of list
        def count_oldest_used(recipe):
            return sum(1 for item in recipe["ingredients_used"] if item.lower() in [o.lower() for o in oldest_items])
        recipes.sort(key=count_oldest_used, reverse=True)

    return {
        "ingredients": ingredients,
        "recipes": recipes[:3]
    }

async def analyze_fridge_image(
    image_bytes: bytes,
    dietary_restrictions: List[str],
    inventory_items: List[dict] = None,
    strict_match: bool = False,
    save_the_food: bool = False
) -> dict:
    """
    Sends the fridge image and config parameters to the Gemini API.
    Falls back to mock generator if GEMINI_API_KEY is not set.
    """
    client = get_gemini_client()
    
    # Process inventory parameters
    inv_names = [item["name"] for item in inventory_items] if inventory_items else []
    
    # If "Save the Food" is active, get the oldest items
    oldest_items = []
    if save_the_food and inventory_items:
        # Sort items by added_at (oldest first)
        sorted_items = sorted(inventory_items, key=lambda x: x.get("added_at") or "")
        oldest_items = [item["name"] for item in sorted_items[:3]]

    if not client:
        logger.warning("GEMINI_API_KEY environment variable is not set. Running in Demo Mode.")
        return generate_mock_data(dietary_restrictions, inv_names, strict_match, oldest_items)

    try:
        # Load image from bytes
        img = Image.open(io.BytesIO(image_bytes))
        
        # Prepare inventory context for the prompt
        inventory_context = ""
        if inv_names:
            inventory_context = f"\nUser's Current Inventory: {', '.join(inv_names)}"
            if oldest_items:
                inventory_context += f"\nOldest Ingredients (Prioritize using these): {', '.join(oldest_items)}"

        dietary_context = ""
        if dietary_restrictions:
            dietary_context = f"\nDietary Restrictions (MUST strictly follow): {', '.join(dietary_restrictions)}"

        # Construct the system instruction and prompt
        prompt = f"""
Analyze this image of a refrigerator or pantry. Perform two tasks:
1. Extract all visible ingredients (items, quantity estimate, category, and an estimated shelf life / days to expiration based on general food storage guidelines).
2. Generate exactly 3 recipes using the ingredients.

Parameters to follow strictly:
- "Strict Match Toggle" is set to: {strict_match}. 
  If True, you MUST only generate recipes using ingredients present in the User's Current Inventory list. Do not use items visible in the image if they are not in the list.
  If False, you can use ingredients visible in the image, but still try to use the inventory items.
- "Save the Food Toggle" is set to: {save_the_food}.
  If True, prioritize the "Oldest Ingredients" mentioned below at the top of recipe ingredients and recipe ordering.
{dietary_context}
{inventory_context}

Return the results ONLY as a valid JSON object matching this schema:
{{
  "ingredients": [
    {{
      "name": "ingredient name",
      "quantity": 1.0,
      "unit": "pcs/ml/grams/etc",
      "category": "Dairy/Vegetables/Meat/etc",
      "days_to_expiration": 5
    }}
  ],
  "recipes": [
    {{
      "name": "Recipe Name",
      "ingredients_used": ["ingredient1", "ingredient2"],
      "instructions": ["Step 1...", "Step 2..."],
      "prep_time": "15 mins"
    }}
  ]
}}
Do not write markdown block quotes (like ```json), just return raw JSON text.
"""
        # Call the Gemini model
        # For safety and structured responses, we specify the output format
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[img, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        # Parse the JSON response
        result_text = response.text.strip()
        # Strip potential markdown formatting if returned
        if result_text.startswith("```"):
            lines = result_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            result_text = "\n".join(lines).strip()
            
        data = json.loads(result_text)
        return data

    except Exception as e:
        logger.error(f"Gemini API execution failed: {e}. Raising error as client was initialized.")
        raise ValueError(f"Gemini API Error: {e}")

