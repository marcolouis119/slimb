import requests
import config
from typing import Dict, Optional, List
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ProductInfo:
    """Информация о продукте"""
    name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    salt: Optional[float] = None
    serving_size_g: float = 100
    source: str = "openfoodfacts"
    success: bool = True
    barcode: Optional[str] = None
    brands: Optional[str] = None
    categories: Optional[str] = None
    nova_group: Optional[int] = None  # 1-4 (1 - минимальная обработка, 4 - ультраобработанный)

class OpenFoodFactsAPI:
    """Клиент для работы с Open Food Facts API"""
    
    def __init__(self):
        self.base_url = "https://world.openfoodfacts.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SlimTrackerBot/1.0 (Telegram Bot)',
            'Accept': 'application/json'
        })
        
        # Локальная кэш-база для популярных продуктов
        self.local_db = self._init_local_database()
        
        # Кэш запросов
        self.cache = {}
        self.cache_expiry = timedelta(hours=1)
    
    def _init_local_database(self) -> Dict:
        """Инициализация локальной базы продуктов"""
        return {
            # Фрукты и ягоды
            'яблоко': {'calories': 52, 'protein': 0.3, 'fat': 0.2, 'carbs': 14, 'fiber': 2.4},
            'банан': {'calories': 89, 'protein': 1.1, 'fat': 0.3, 'carbs': 23, 'fiber': 2.6},
            'апельсин': {'calories': 47, 'protein': 0.9, 'fat': 0.1, 'carbs': 12, 'fiber': 2.4},
            'киви': {'calories': 61, 'protein': 1.1, 'fat': 0.5, 'carbs': 15, 'fiber': 3.0},
            'груша': {'calories': 57, 'protein': 0.4, 'fat': 0.1, 'carbs': 15, 'fiber': 3.1},
            'виноград': {'calories': 69, 'protein': 0.7, 'fat': 0.2, 'carbs': 18, 'fiber': 0.9},
            'клубника': {'calories': 32, 'protein': 0.7, 'fat': 0.3, 'carbs': 8, 'fiber': 2.0},
            'персик': {'calories': 39, 'protein': 0.9, 'fat': 0.3, 'carbs': 10, 'fiber': 1.5},
            'слива': {'calories': 46, 'protein': 0.7, 'fat': 0.3, 'carbs': 11, 'fiber': 1.4},
            'арбуз': {'calories': 30, 'protein': 0.6, 'fat': 0.2, 'carbs': 8, 'fiber': 0.4},
            
            # Овощи
            'морковь': {'calories': 41, 'protein': 0.9, 'fat': 0.2, 'carbs': 10, 'fiber': 2.8},
            'помидор': {'calories': 18, 'protein': 0.9, 'fat': 0.2, 'carbs': 4, 'fiber': 1.2},
            'огурец': {'calories': 15, 'protein': 0.7, 'fat': 0.1, 'carbs': 3, 'fiber': 0.5},
            'картофель': {'calories': 77, 'protein': 2.0, 'fat': 0.1, 'carbs': 17, 'fiber': 2.2},
            'брокколи': {'calories': 34, 'protein': 2.8, 'fat': 0.4, 'carbs': 7, 'fiber': 2.6},
            'капуста': {'calories': 25, 'protein': 1.3, 'fat': 0.1, 'carbs': 6, 'fiber': 2.5},
            'лук': {'calories': 40, 'protein': 1.1, 'fat': 0.1, 'carbs': 9, 'fiber': 1.7},
            'чеснок': {'calories': 149, 'protein': 6.4, 'fat': 0.5, 'carbs': 33, 'fiber': 2.1},
            'перец': {'calories': 20, 'protein': 0.9, 'fat': 0.2, 'carbs': 4, 'fiber': 1.7},
            'баклажан': {'calories': 25, 'protein': 1.0, 'fat': 0.2, 'carbs': 6, 'fiber': 3.0},
            
            # Белковые продукты
            'курица': {'calories': 165, 'protein': 31, 'fat': 3.6, 'carbs': 0, 'fiber': 0},
            'говядина': {'calories': 250, 'protein': 26, 'fat': 15, 'carbs': 0, 'fiber': 0},
            'свинина': {'calories': 242, 'protein': 25, 'fat': 14, 'carbs': 0, 'fiber': 0},
            'индейка': {'calories': 135, 'protein': 29, 'fat': 1.0, 'carbs': 0, 'fiber': 0},
            'рыба': {'calories': 206, 'protein': 22, 'fat': 13, 'carbs': 0, 'fiber': 0},
            'лосось': {'calories': 208, 'protein': 20, 'fat': 13, 'carbs': 0, 'fiber': 0},
            'тунец': {'calories': 132, 'protein': 29, 'fat': 1.0, 'carbs': 0, 'fiber': 0},
            'креветки': {'calories': 85, 'protein': 20, 'fat': 0.5, 'carbs': 0, 'fiber': 0},
            'яйцо': {'calories': 155, 'protein': 13, 'fat': 11, 'carbs': 1.1, 'fiber': 0},
            
            # Молочные продукты
            'молоко': {'calories': 42, 'protein': 3.4, 'fat': 1, 'carbs': 5, 'fiber': 0},
            'кефир': {'calories': 41, 'protein': 3.4, 'fat': 1.0, 'carbs': 4, 'fiber': 0},
            'йогурт': {'calories': 59, 'protein': 3.5, 'fat': 1.5, 'carbs': 6, 'fiber': 0},
            'творог': {'calories': 98, 'protein': 11, 'fat': 4.3, 'carbs': 3.4, 'fiber': 0},
            'сметана': {'calories': 193, 'protein': 2.5, 'fat': 20, 'carbs': 3.4, 'fiber': 0},
            'сыр': {'calories': 402, 'protein': 25, 'fat': 33, 'carbs': 1.3, 'fiber': 0},
            'масло': {'calories': 717, 'protein': 0.9, 'fat': 81, 'carbs': 0.1, 'fiber': 0},
            
            # Крупы и зерновые
            'рис': {'calories': 130, 'protein': 2.7, 'fat': 0.3, 'carbs': 28, 'fiber': 0.4},
            'гречка': {'calories': 92, 'protein': 3.4, 'fat': 0.6, 'carbs': 20, 'fiber': 1.7},
            'овсянка': {'calories': 68, 'protein': 2.4, 'fat': 1.4, 'carbs': 12, 'fiber': 1.7},
            'перловка': {'calories': 123, 'protein': 2.3, 'fat': 0.4, 'carbs': 28, 'fiber': 3.8},
            'пшено': {'calories': 119, 'protein': 3.5, 'fat': 1.0, 'carbs': 23, 'fiber': 1.3},
            'макароны': {'calories': 131, 'protein': 5, 'fat': 1.1, 'carbs': 25, 'fiber': 1.8},
            'хлеб': {'calories': 265, 'protein': 9, 'fat': 3.2, 'carbs': 49, 'fiber': 2.7},
            'булка': {'calories': 270, 'protein': 8, 'fat': 3.5, 'carbs': 50, 'fiber': 2.5},
            
            # Орехи и семена
            'орехи': {'calories': 607, 'protein': 20, 'fat': 54, 'carbs': 21, 'fiber': 7.0},
            'миндаль': {'calories': 579, 'protein': 21, 'fat': 50, 'carbs': 22, 'fiber': 12.5},
            'грецкий орех': {'calories': 654, 'protein': 15, 'fat': 65, 'carbs': 14, 'fiber': 6.7},
            'арахис': {'calories': 567, 'protein': 26, 'fat': 49, 'carbs': 16, 'fiber': 8.5},
            'семечки': {'calories': 584, 'protein': 21, 'fat': 51, 'carbs': 20, 'fiber': 9.0},
            
            # Напитки
            'вода': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0},
            'кофе': {'calories': 1, 'protein': 0.1, 'fat': 0, 'carbs': 0, 'fiber': 0},
            'чай': {'calories': 1, 'protein': 0.1, 'fat': 0, 'carbs': 0, 'fiber': 0},
            'сок': {'calories': 45, 'protein': 0.5, 'fat': 0.1, 'carbs': 11, 'fiber': 0.2},
            
            # Другое
            'шоколад': {'calories': 546, 'protein': 4.9, 'fat': 31, 'carbs': 61, 'fiber': 7.0},
            'мед': {'calories': 304, 'protein': 0.3, 'fat': 0, 'carbs': 82, 'fiber': 0.2},
            'сахар': {'calories': 387, 'protein': 0, 'fat': 0, 'carbs': 100, 'fiber': 0},
            'соль': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0},
        }
    
    def search_product(self, query: str, limit: int = 5) -> List[ProductInfo]:
        """
        Поиск продукта по названию в Open Food Facts
        
        Args:
            query: Название продукта для поиска
            limit: Максимальное количество результатов
        
        Returns:
            Список найденных продуктов
        """
        try:
            # Проверяем кэш
            cache_key = f"search_{query.lower()}"
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if datetime.now() - timestamp < self.cache_expiry:
                    return cached_data
            
            # Поиск через API Open Food Facts
            url = f"{self.base_url}/cgi/search.pl"
            params = {
                'search_terms': query,
                'search_simple': 1,
                'action': 'process',
                'json': 1,
                'page_size': limit,
                'lc': 'ru'  # Язык - русский
            }
            
            logger.info(f"Searching Open Food Facts for: {query}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            products = []
            
            if data.get('products'):
                for product_data in data['products']:
                    product_info = self._parse_product_data(product_data)
                    if product_info and product_info.success:
                        products.append(product_info)
            
            # Кэшируем результаты
            self.cache[cache_key] = (products, datetime.now())
            
            if products:
                logger.info(f"Found {len(products)} products for '{query}'")
            else:
                logger.warning(f"No products found for '{query}'")
            
            return products
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Open Food Facts: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []
    
    def get_product_by_barcode(self, barcode: str) -> Optional[ProductInfo]:
        """
        Получить информацию о продукте по штрих-коду
        
        Args:
            barcode: Штрих-код продукта
        
        Returns:
            Информация о продукте или None
        """
        try:
            cache_key = f"barcode_{barcode}"
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if datetime.now() - timestamp < self.cache_expiry:
                    return cached_data
            
            url = f"{self.base_url}/api/v2/product/{barcode}.json"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 404:
                logger.warning(f"Product with barcode {barcode} not found")
                return None
            
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 1:  # 1 means product found
                product_info = self._parse_product_data(data['product'])
                if product_info:
                    self.cache[cache_key] = (product_info, datetime.now())
                return product_info
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching product by barcode: {e}")
            return None
    
    def _parse_product_data(self, product_data: Dict) -> Optional[ProductInfo]:
        """
        Парсинг данных продукта из Open Food Facts
        
        Args:
            product_data: Сырые данные продукта
        
        Returns:
            Структурированная информация о продукте
        """
        try:
            # Извлекаем основную информацию
            product_name = (
                product_data.get('product_name_ru') or 
                product_data.get('product_name') or 
                product_data.get('generic_name_ru') or 
                product_data.get('generic_name') or 
                "Неизвестный продукт"
            )
            
            # Извлекаем питательные вещества
            nutriments = product_data.get('nutriments', {})
            
            # Калории (конвертируем из кДж если нужно)
            energy_kcal = nutriments.get('energy-kcal_100g')
            energy_kj = nutriments.get('energy-kj_100g')
            
            calories = energy_kcal
            if calories is None and energy_kj is not None:
                # Конвертируем из кДж в ккал: 1 ккал = 4.184 кДж
                calories = energy_kj / 4.184
            
            # Другие питательные вещества
            protein = nutriments.get('proteins_100g', 0)
            fat = nutriments.get('fat_100g', 0)
            carbs = nutriments.get('carbohydrates_100g', 0)
            fiber = nutriments.get('fiber_100g')
            sugar = nutriments.get('sugars_100g')
            salt = nutriments.get('salt_100g')
            
            # Нормализуем значения
            calories = float(calories) if calories is not None else 0
            protein = float(protein) if protein is not None else 0
            fat = float(fat) if fat is not None else 0
            carbs = float(carbs) if carbs is not None else 0
            
            # Если данных совсем нет, возвращаем None
            if calories == 0 and protein == 0 and fat == 0 and carbs == 0:
                return None
            
            # Получаем дополнительные данные
            serving_size = nutriments.get('serving_size')
            serving_size_g = 100  # по умолчанию 100г
            
            if serving_size:
                # Парсим размер порции (например, "100g" или "50 ml")
                match = re.search(r'(\d+(?:\.\d+)?)\s*g', serving_size.lower())
                if match:
                    serving_size_g = float(match.group(1))
            
            # NOVA группа (степень обработки)
            nova_group = None
            nova_tags = product_data.get('nova_groups_tags', [])
            if nova_tags:
                try:
                    nova_group = int(nova_tags[0].split('-')[-1])
                except (ValueError, IndexError):
                    pass
            
            return ProductInfo(
                name=product_name.strip(),
                calories=round(calories, 1),
                protein=round(protein, 1),
                fat=round(fat, 1),
                carbs=round(carbs, 1),
                fiber=round(fiber, 1) if fiber else None,
                sugar=round(sugar, 1) if sugar else None,
                salt=round(salt, 3) if salt else None,
                serving_size_g=serving_size_g,
                source='openfoodfacts',
                success=True,
                barcode=product_data.get('code'),
                brands=product_data.get('brands'),
                categories=product_data.get('categories'),
                nova_group=nova_group
            )
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing product data: {e}, data: {product_data}")
            return None
    
    def get_product_info(self, query: str) -> ProductInfo:
        """
        Основной метод для получения информации о продукте
        
        Пытается найти продукт в Open Food Facts, если не находит,
        ищет в локальной базе или оценивает по категории
        """
        # Сначала ищем в Open Food Facts
        search_results = self.search_product(query, limit=3)
        
        if search_results:
            # Возвращаем самый релевантный результат
            return search_results[0]
        
        # Если не нашли в Open Food Facts, ищем в локальной базе
        query_lower = query.lower()
        
        # Пробуем найти точное совпадение
        for product_name, nutrients in self.local_db.items():
            if product_name in query_lower:
                return ProductInfo(
                    name=product_name.capitalize(),
                    calories=nutrients['calories'],
                    protein=nutrients['protein'],
                    fat=nutrients['fat'],
                    carbs=nutrients['carbs'],
                    fiber=nutrients.get('fiber'),
                    serving_size_g=100,
                    source='local_db',
                    success=True
                )
        
        # Если не нашли точного совпадения, ищем по частичным совпадениям
        for product_name, nutrients in self.local_db.items():
            # Разбиваем запрос на слова
            query_words = set(query_lower.split())
            product_words = set(product_name.split())
            
            # Проверяем пересечение слов
            common_words = query_words.intersection(product_words)
            if len(common_words) >= 1:
                return ProductInfo(
                    name=product_name.capitalize(),
                    calories=nutrients['calories'],
                    protein=nutrients['protein'],
                    fat=nutrients['fat'],
                    carbs=nutrients['carbs'],
                    fiber=nutrients.get('fiber'),
                    serving_size_g=100,
                    source='local_db_approx',
                    success=True
                )
        
        # Если ничего не нашли, оцениваем по категории
        return self._estimate_product_info(query)
    
    def _estimate_product_info(self, query: str) -> ProductInfo:
        """
        Оценка питательной ценности по категории продукта
        """
        query_lower = query.lower()
        
        # Определяем категорию
        categories = {
            'фрукт': {'calories': 60, 'protein': 0.8, 'fat': 0.3, 'carbs': 15},
            'овощ': {'calories': 35, 'protein': 1.5, 'fat': 0.2, 'carbs': 7},
            'мясо': {'calories': 200, 'protein': 25, 'fat': 10, 'carbs': 0},
            'рыба': {'calories': 150, 'protein': 20, 'fat': 8, 'carbs': 0},
            'молочный': {'calories': 120, 'protein': 8, 'fat': 7, 'carbs': 5},
            'крупа': {'calories': 110, 'protein': 3, 'fat': 1, 'carbs': 25},
            'хлеб': {'calories': 250, 'protein': 8, 'fat': 3, 'carbs': 50},
            'сладость': {'calories': 400, 'protein': 5, 'fat': 20, 'carbs': 60},
            'напиток': {'calories': 30, 'protein': 0.5, 'fat': 0, 'carbs': 7},
        }
        
        # Ключевые слова для категорий
        category_keywords = {
            'фрукт': ['фрукт', 'ягод', 'абрикос', 'вишн', 'груш', 'персик', 'слив'],
            'овощ': ['овощ', 'огур', 'помидор', 'картош', 'морков', 'капуст', 'лук'],
            'мясо': ['мясо', 'говядин', 'свинин', 'баран', 'курин', 'индейк'],
            'рыба': ['рыба', 'лосос', 'форел', 'тунец', 'селед', 'скумбр'],
            'молочный': ['молок', 'кефир', 'йогурт', 'творог', 'сыр', 'сметан'],
            'крупа': ['рис', 'гречк', 'овсян', 'перлов', 'пшен', 'макарон'],
            'хлеб': ['хлеб', 'булк', 'батон', 'бухан', 'лаваш'],
            'сладость': ['шоколад', 'конфет', 'печень', 'торт', 'пирож', 'морожен'],
            'напиток': ['сок', 'компот', 'лимонад', 'кола', 'пепси', 'напиток'],
        }
        
        # Определяем категорию по ключевым словам
        estimated_category = 'овощ'  # категория по умолчанию
        
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    estimated_category = category
                    break
        
        # Берем средние значения для категории
        if estimated_category in categories:
            nutrients = categories[estimated_category]
        else:
            nutrients = categories['овощ']  # fallback
        
        return ProductInfo(
            name=query,
            calories=nutrients['calories'],
            protein=nutrients['protein'],
            fat=nutrients['fat'],
            carbs=nutrients['carbs'],
            serving_size_g=100,
            source='estimation',
            success=True
        )
    
    def analyze_meal(self, meal_description: str) -> Dict:
        """
        Анализ описания приема пищи с несколькими ингредиентами
        
        Пример: "200г овсянки с молоком и бананом"
        """
        try:
            # Простой парсинг (можно улучшить)
            ingredients = []
            
            # Ищем паттерны типа "200г овсянки"
            pattern = r'(\d+(?:\.\d+)?)\s*(?:г|грамм|кг|мл|литр|л)?\s+([а-яА-Я\s]+)'
            matches = re.findall(pattern, meal_description, re.IGNORECASE)
            
            for amount_str, ingredient in matches:
                try:
                    amount = float(amount_str)
                    
                    # Конвертируем кг в граммы
                    if 'кг' in meal_description.lower():
                        amount *= 1000
                    
                    # Ищем продукт
                    product_info = self.get_product_info(ingredient.strip())
                    
                    if product_info.success:
                        # Масштабируем питательные вещества
                        scale = amount / product_info.serving_size_g
                        
                        ingredients.append({
                            'name': product_info.name,
                            'amount_g': amount,
                            'calories': product_info.calories * scale,
                            'protein': product_info.protein * scale,
                            'fat': product_info.fat * scale,
                            'carbs': product_info.carbs * scale
                        })
                        
                except (ValueError, KeyError):
                    continue
            
            # Если не нашли паттерны, пробуем просто найти продукты
            if not ingredients:
                words = meal_description.split()
                for word in words:
                    if len(word) > 3:  # Игнорируем короткие слова
                        product_info = self.get_product_info(word)
                        if product_info.success:
                            # Используем стандартную порцию
                            ingredients.append({
                                'name': product_info.name,
                                'amount_g': 100,
                                'calories': product_info.calories,
                                'protein': product_info.protein,
                                'fat': product_info.fat,
                                'carbs': product_info.carbs
                            })
            
            # Суммируем все ингредиенты
            total = {
                'calories': sum(i['calories'] for i in ingredients),
                'protein': sum(i['protein'] for i in ingredients),
                'fat': sum(i['fat'] for i in ingredients),
                'carbs': sum(i['carbs'] for i in ingredients),
                'ingredients': ingredients
            }
            
            return {
                'success': len(ingredients) > 0,
                'total': total,
                'meal_description': meal_description
            }
            
        except Exception as e:
            logger.error(f"Error analyzing meal: {e}")
            return {
                'success': False,
                'error': str(e),
                'meal_description': meal_description
            }