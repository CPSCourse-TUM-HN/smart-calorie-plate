from typing import Dict


def calculate_nutrition_targets(
    age: int,
    gender: str,
    height_cm: float,
    weight_kg: float,
    activity_level: float,
    diet_mode: str,
) -> Dict[str, float]:
    """Compute the calorie and macro targets
    (BMR -> TDEE -> target calories -> macro split).

    Returns a dict with: target_calories, target_protein_g, target_fat_g,
    target_carbs_g.
    """
    gender_lower = gender.lower()
    if gender_lower not in ("male", "female"):
        raise ValueError("gender must be 'male' or 'female'")

    # BMR: Mifflin-St Jeor
    if gender_lower == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    tdee = bmr * activity_level

    mode = diet_mode.lower()
    if mode == "fat_loss":
        target_calories = tdee - 400
    elif mode == "muscle_gain":
        target_calories = tdee + 300
    else:
        target_calories = tdee

    # Macro split
    if mode in ("fat_loss", "muscle_gain"):
        target_protein_g = 2.0 * weight_kg
    else:
        target_protein_g = 1.8 * weight_kg

    target_fat_g = 0.9 * weight_kg

    # Keep the calorie budget closed: carbs = (calories - protein*4 - fat*9) / 4
    remaining_kcal = target_calories - (target_protein_g * 4 + target_fat_g * 9)
    target_carbs_g = max(0.0, remaining_kcal / 4.0)

    return {
        "target_calories": round(target_calories, 1),
        "target_protein_g": round(target_protein_g, 1),
        "target_fat_g": round(target_fat_g, 1),
        "target_carbs_g": round(target_carbs_g, 1),
    }
