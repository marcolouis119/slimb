"""
Базовые тесты для Sourcecraft CI
"""

import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class TestConfig(unittest.TestCase):
    """Тесты конфигурации"""
    
    def test_config_import(self):
        """Тест импорта конфигурации"""
        from config import Config
        self.assertTrue(hasattr(Config, 'TELEGRAM_TOKEN'))
        self.assertTrue(hasattr(Config, 'YDB_ENDPOINT'))
        self.assertTrue(hasattr(Config, 'YDB_DATABASE'))
    
    def test_water_multiplier(self):
        """Тест параметров расчета"""
        from config import Config
        self.assertEqual(Config.WATER_MULTIPLIER, 35)

class TestUtils(unittest.TestCase):
    """Тесты утилит"""
    
    def test_bmi_calculation(self):
        """Тест расчета ИМТ"""
        from utils import NutritionCalculator
        calculator = NutritionCalculator()
        
        # Тест для веса 70кг и роста 175см
        bmi = calculator.calculate_bmi(70, 175)
        self.assertAlmostEqual(bmi, 22.86, places=1)
        
        # Тест интерпретации
        status = calculator.interpret_bmi(22.86)
        self.assertEqual(status, "Нормальная масса тела")
    
    def test_calorie_calculation(self):
        """Тест расчета калорий"""
        from utils import NutritionCalculator
        calculator = NutritionCalculator()
        
        calories, macros = calculator.calculate_daily_calories(
            weight=70,
            height=175,
            age=30,
            gender='male',
            activity_level='moderate',
            goal='maintain'
        )
        
        self.assertIsInstance(calories, int)
        self.assertGreater(calories, 0)
        self.assertIn('protein', macros)
        self.assertIn('fat', macros)
        self.assertIn('carbs', macros)

if __name__ == '__main__':
    unittest.main()