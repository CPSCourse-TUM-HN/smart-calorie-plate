import pytest

from calorie_plate.nutrition import calc_kcal_per_weight
from calorie_plate.utils import calculate_nutrition_targets


def test_calc_kcal_per_weight():
    # 100 kcal/100g at 200 g -> 200 kcal
    assert calc_kcal_per_weight(100, 200) == 200


def test_calc_kcal_per_weight_scales_linearly():
    assert calc_kcal_per_weight(89, 50) == pytest.approx(44.5)


def test_targets_male_balance():
    """Mifflin-St Jeor for a male on a maintenance (balance) plan.

    BMR  = 10*80 + 6.25*180 - 5*30 + 5      = 1780
    TDEE = 1780 * 1.55                       = 2759
    protein = 1.8*80 = 144, fat = 0.9*80 = 72
    carbs   = (2759 - (144*4 + 72*9)) / 4    = 383.75
    """
    t = calculate_nutrition_targets(
        age=30, gender="male", height_cm=180, weight_kg=80,
        activity_level=1.55, diet_mode="balance",
    )
    assert t["target_calories"] == pytest.approx(2759.0)
    assert t["target_protein_g"] == pytest.approx(144.0)
    assert t["target_fat_g"] == pytest.approx(72.0)
    assert t["target_carbs_g"] == pytest.approx(383.8)


def test_targets_female_uses_lower_bmr_constant():
    """The female BMR constant (-161) is 166 lower than the male one (+5),
    so the female target must be strictly lower for identical body metrics."""
    common = dict(age=30, height_cm=180, weight_kg=80,
                  activity_level=1.55, diet_mode="balance")
    male = calculate_nutrition_targets(gender="male", **common)
    female = calculate_nutrition_targets(gender="female", **common)
    assert female["target_calories"] < male["target_calories"]


def test_diet_mode_shifts_calories_and_protein():
    """fat_loss subtracts 400 kcal and raises protein to 2.0 g/kg;
    muscle_gain adds 300 kcal relative to balance."""
    common = dict(age=30, gender="male", height_cm=180, weight_kg=80,
                  activity_level=1.55)
    balance = calculate_nutrition_targets(diet_mode="balance", **common)
    fat_loss = calculate_nutrition_targets(diet_mode="fat_loss", **common)
    muscle = calculate_nutrition_targets(diet_mode="muscle_gain", **common)

    assert fat_loss["target_calories"] == pytest.approx(balance["target_calories"] - 400)
    assert muscle["target_calories"] == pytest.approx(balance["target_calories"] + 300)
    assert fat_loss["target_protein_g"] == pytest.approx(2.0 * 80)
    assert balance["target_protein_g"] == pytest.approx(1.8 * 80)


def test_carbs_never_negative():
    """Even when protein + fat already exceed the calorie budget, carbs are
    floored at 0 rather than going negative."""
    t = calculate_nutrition_targets(
        age=80, gender="female", height_cm=140, weight_kg=120,
        activity_level=1.2, diet_mode="fat_loss",
    )
    assert t["target_carbs_g"] >= 0.0


def test_invalid_gender_raises():
    with pytest.raises(ValueError):
        calculate_nutrition_targets(
            age=30, gender="other", height_cm=180, weight_kg=80,
            activity_level=1.55, diet_mode="balance",
        )
