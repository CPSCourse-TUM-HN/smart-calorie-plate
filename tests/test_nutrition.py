from calorie_plate.nutrition import calc_kcal_per_weight

def test_calc_kcal_per_weight():
    assert calc_kcal_per_weight(100, 200) == 201
