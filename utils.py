from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import pandas as pd
from typing import List, Dict, Tuple
import config

class NutritionCalculator:
    
    @staticmethod
    def calculate_bmi(weight: float, height: float) -> float:
        """Рассчитать индекс массы тела"""
        if height <= 0:
            return 0
        height_m = height / 100  # переводим см в метры
        bmi = weight / (height_m ** 2)
        return round(bmi, 1)
    
    @staticmethod
    def interpret_bmi(bmi: float) -> str:
        """Интерпретация значения ИМТ по ВОЗ"""
        if bmi < 16:
            return "Выраженный дефицит массы тела"
        elif 16 <= bmi < 18.5:
            return "Недостаточная масса тела"
        elif 18.5 <= bmi < 25:
            return "Нормальная масса тела"
        elif 25 <= bmi < 30:
            return "Избыточная масса тела (предожирение)"
        elif 30 <= bmi < 35:
            return "Ожирение 1 степени"
        elif 35 <= bmi < 40:
            return "Ожирение 2 степени"
        else:
            return "Ожирение 3 степени"
    
    @staticmethod
    def calculate_bmr(weight: float, height: float, age: int, gender: str) -> float:
        """Рассчитать базовый метаболизм (BMR) по формуле Миффлина-Сан Жеора"""
        if gender == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:  # female
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        
        return bmr
    
    @staticmethod
    def calculate_daily_calories(
        weight: float, 
        height: float, 
        age: int, 
        gender: str, 
        activity_level: str, 
        goal: str
    ) -> Tuple[float, Dict[str, float]]:
        """
        Рассчитать дневную норму калорий и БЖУ
        
        Возвращает:
        - total_calories: общее количество калорий
        - macros: распределение БЖУ в граммах
        """
        
        # Коэффициенты активности
        activity_multipliers = {
            'sedentary': 1.2,      # сидячий образ жизни
            'light': 1.375,        # легкие упражнения 1-3 раза в неделю
            'moderate': 1.55,      # умеренные упражнения 3-5 раз в неделю
            'active': 1.725,       # интенсивные упражнения 6-7 раз в неделю
            'very_active': 1.9     # очень интенсивные упражнения + физическая работа
        }
        
        # Коэффициенты цели
        goal_multipliers = {
            'lose': 0.8,      # дефицит 20% для похудения
            'maintain': 1.0,  # поддержание веса
            'gain': 1.2       # профицит 20% для набора массы
        }
        
        # Рассчитываем BMR
        bmr = NutritionCalculator.calculate_bmr(weight, height, age, gender)
        
        # Применяем коэффициент активности
        activity_multiplier = activity_multipliers.get(activity_level, 1.2)
        maintenance_calories = bmr * activity_multiplier
        
        # Применяем коэффициент цели
        goal_multiplier = goal_multipliers.get(goal, 1.0)
        total_calories = round(maintenance_calories * goal_multiplier)
        
        # Рассчитываем макронутриенты
        if goal == 'lose':
            # При похудении: больше белка, меньше углеводов
            protein_ratio = 0.35  # 35% калорий из белка
            fat_ratio = 0.30      # 30% калорий из жиров
            carbs_ratio = 0.35    # 35% калорий из углеводов
        elif goal == 'gain':
            # При наборе массы: больше углеводов
            protein_ratio = 0.30  # 30% калорий из белка
            fat_ratio = 0.25      # 25% калорий из жиров
            carbs_ratio = 0.45    # 45% калорий из углеводов
        else:
            # При поддержании: сбалансированное соотношение
            protein_ratio = 0.30  # 30% калорий из белка
            fat_ratio = 0.30      # 30% калорий из жиров
            carbs_ratio = 0.40    # 40% калорий из углеводов
        
        # Конвертируем проценты в граммы
        # Белок: 1 грамм = 4 калории
        # Углеводы: 1 грамм = 4 калории
        # Жиры: 1 грамм = 9 калорий
        
        protein_grams = round((total_calories * protein_ratio) / 4)
        fat_grams = round((total_calories * fat_ratio) / 9)
        carbs_grams = round((total_calories * carbs_ratio) / 4)
        
        macros = {
            'protein': protein_grams,
            'fat': fat_grams,
            'carbs': carbs_grams,
            'protein_percent': protein_ratio * 100,
            'fat_percent': fat_ratio * 100,
            'carbs_percent': carbs_ratio * 100
        }
        
        return total_calories, macros
    
    @staticmethod
    def calculate_water_needs(weight: float, activity_level: str, climate: str = 'moderate') -> float:
        """
        Рассчитать дневную норму воды
        
        Формула: 35 мл на 1 кг веса + коррекция на активность и климат
        """
        base_water = weight * config.Config.WATER_MULTIPLIER  # 35 мл на кг
        
        # Коррекция на активность
        activity_factors = {
            'sedentary': 1.0,
            'light': 1.1,
            'moderate': 1.2,
            'active': 1.3,
            'very_active': 1.4
        }
        
        # Коррекция на климат
        climate_factors = {
            'cold': 0.9,
            'moderate': 1.0,
            'hot': 1.2,
            'very_hot': 1.3
        }
        
        activity_factor = activity_factors.get(activity_level, 1.0)
        climate_factor = climate_factors.get(climate, 1.0)
        
        total_water = base_water * activity_factor * climate_factor
        
        # Округляем до ближайших 100 мл
        return round(total_water / 100) * 100
    
    @staticmethod
    def calculate_ideal_weight(height: float, gender: str) -> Dict[str, float]:
        """
        Рассчитать идеальный вес по разным формулам
        
        Возвращает диапазон идеального веса
        """
        # Формула Брока (рост в см - 100)
        broca = height - 100
        if gender == 'female':
            broca *= 0.85
        
        # Формула Лоренца
        if gender == 'male':
            lorenz = (height - 100) - ((height - 150) / 4)
        else:
            lorenz = (height - 100) - ((height - 150) / 2.5)
        
        # Формула Купера
        if gender == 'male':
            cooper = (height * 4 / 2.54 - 128) * 0.453
        else:
            cooper = (height * 3.5 / 2.54 - 108) * 0.453
        
        return {
            'broca': round(broca, 1),
            'lorenz': round(lorenz, 1),
            'cooper': round(cooper, 1),
            'min': min(broca, lorenz, cooper),
            'max': max(broca, lorenz, cooper)
        }
    
    @staticmethod
    def get_nutrition_plan(
        total_calories: float,
        meal_count: int = 4,
        diet_type: str = 'balanced'
    ) -> List[Dict]:
        """
        Сгенерировать план питания на день
        
        diet_type: balanced, high_protein, low_carb, mediterranean
        """
        
        # Распределение калорий по приемам пищи
        if meal_count == 3:
            distribution = {'breakfast': 0.35, 'lunch': 0.40, 'dinner': 0.25}
        elif meal_count == 4:
            distribution = {'breakfast': 0.30, 'lunch': 0.35, 'snack': 0.15, 'dinner': 0.20}
        elif meal_count == 5:
            distribution = {'breakfast': 0.25, 'snack1': 0.10, 'lunch': 0.30, 'snack2': 0.15, 'dinner': 0.20}
        else:
            distribution = {'breakfast': 0.30, 'lunch': 0.35, 'snack': 0.15, 'dinner': 0.20}
        
        meals = []
        for meal_name, ratio in distribution.items():
            meal_calories = round(total_calories * ratio)
            
            # Рекомендации по типам блюд
            if diet_type == 'high_protein':
                suggestion = f"Богатый белком прием пищи: мясо, рыба, яйца, творог"
            elif diet_type == 'low_carb':
                suggestion = f"Низкоуглеводный прием: овощи, зелень, белок"
            elif diet_type == 'mediterranean':
                suggestion = f"Средиземноморский стиль: рыба, оливковое масло, овощи"
            else:  # balanced
                suggestion = f"Сбалансированный прием: белки + сложные углеводы + овощи"
            
            meals.append({
                'name': meal_name,
                'calories': meal_calories,
                'ratio': ratio,
                'suggestion': suggestion
            })
        
        return meals
    
    @staticmethod
    def calculate_weight_change_rate(
        current_weight: float,
        target_weight: float,
        daily_calorie_balance: float
    ) -> Dict[str, any]:
        """
        Рассчитать скорость изменения веса
        
        daily_calorie_balance: разница между потребленными и расходуемыми калориями
        (положительная = избыток, отрицательная = дефицит)
        """
        # 7700 ккал ≈ 1 кг жира
        weekly_change_kg = (daily_calorie_balance * 7) / 7700
        
        if current_weight > target_weight:
            # Похудение
            weight_to_lose = current_weight - target_weight
            if daily_calorie_balance >= 0:
                weeks_needed = float('inf')  # никогда
            else:
                weeks_needed = weight_to_lose / abs(weekly_change_kg)
        else:
            # Набор массы
            weight_to_gain = target_weight - current_weight
            if daily_calorie_balance <= 0:
                weeks_needed = float('inf')  # никогда
            else:
                weeks_needed = weight_to_gain / weekly_change_kg
        
        return {
            'weekly_change_kg': round(weekly_change_kg, 2),
            'weeks_needed': round(weeks_needed, 1) if weeks_needed != float('inf') else None,
            'is_possible': weeks_needed != float('inf'),
            'daily_calorie_balance': daily_calorie_balance
        }