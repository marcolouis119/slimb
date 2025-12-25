from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler
import asyncio
import re
import logging
from datetime import datetime
from typing import Dict, List

from database import DatabaseManager
from api_client import OpenFoodFactsAPI
from utils import NutritionCalculator

# Настройка логирования
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
AGE, GENDER, WEIGHT, HEIGHT, ACTIVITY, GOAL, CLIMATE = range(7)

class BotHandlers:
    
    def __init__(self):
        self.db = DatabaseManager()
        self.api = OpenFoodFactsAPI()
        self.calculator = NutritionCalculator()
    
    async def start(self, update: Update, context: CallbackContext):
        """Обработчик команды /start"""
        user = update.effective_user
        
        try:
            await self.db.get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                full_name=user.full_name
            )
            
            welcome_text = f"""
👋 Привет, {user.first_name}!

Я - *SlimTracker*, ваш персональный помощник в здоровом питании!

🍎 *Что я умею:*
• 📊 Рассчитывать нормы калорий и воды
• 🥗 Отслеживать питание по базе Open Food Facts
• 💧 Контролировать водный баланс
• 📈 Анализировать ваш прогресс
• 🎯 Давать персональные рекомендации

*Основные команды:*
/help - Показать все команды
/profile - Создать персональный профиль
/add_food - Добавить прием пищи
/today - Статистика за сегодня
/water - Учет воды

💡 *Начните с создания профиля:* /profile
            """
            
            await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text(
                "Произошла ошибка при запуске бота. Попробуйте позже."
            )
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /help - показывает все команды"""
        help_text = """
📋 *Доступные команды:*

*/start* - Начало работы
*/help* - Показать это сообщение

👤 *Профиль и расчеты:*
*/profile* - Создать/редактировать профиль
*/myplan* - Мой персональный план
*/bmi* - Рассчитать ИМТ
*/calories* - Рассчитать норму калорий

🍽️ *Питание (Open Food Facts):*
*/add_food* [количество]г [продукт] - Добавить прием пищи
*/search* [продукт] - Найти продукт в базе
*/today* - Статистика за сегодня
*/history* [дней] - История питания
*/macros* - Баланс БЖУ

💧 *Вода:*
*/water* [мл] - Добавить выпитую воду
*/waterplan* - Мой питьевой режим

📊 *Аналитика:*
*/progress* - График прогресса
*/recommend* - Рекомендации
*/rate* - Скорость изменения веса

*Примеры использования:*
• `/add_food 200г овсянка завтрак`
• `/search йогурт`
• `/water 500`
• `/history 7`
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def profile_start(self, update: Update, context: CallbackContext):
        """Начало создания профиля"""
        await update.message.reply_text(
            "📝 *Создание персонального профиля*\n\n"
            "Я рассчитаю индивидуальные нормы калорий и воды!\n\n"
            "*Шаг 1 из 7*\nСколько вам лет? (например: 25)",
            parse_mode=ParseMode.MARKDOWN
        )
        return AGE
    
    async def profile_age(self, update: Update, context: CallbackContext):
        """Получение возраста"""
        try:
            age = int(update.message.text)
            if not 10 <= age <= 120:
                await update.message.reply_text("Пожалуйста, введите реальный возраст (10-120):")
                return AGE
            
            context.user_data['age'] = age
            
            keyboard = [
                [InlineKeyboardButton("Мужской ♂️", callback_data='male'),
                 InlineKeyboardButton("Женский ♀️", callback_data='female')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "*Шаг 2 из 7*\nВыберите ваш пол:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return GENDER
            
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число:")
            return AGE
    
    async def profile_gender(self, update: Update, context: CallbackContext):
        """Обработка выбора пола"""
        query = update.callback_query
        await query.answer()
        
        gender = query.data
        context.user_data['gender'] = gender
        
        gender_text = "Мужской ♂️" if gender == 'male' else "Женский ♀️"
        
        await query.edit_message_text(
            text=f"✅ Пол: {gender_text}\n\n"
                 "*Шаг 3 из 7*\nВведите ваш текущий вес (в кг):\n"
                 "Например: 68.5",
            parse_mode=ParseMode.MARKDOWN
        )
        return WEIGHT
    
    async def profile_weight(self, update: Update, context: CallbackContext):
        """Получение веса"""
        try:
            weight = float(update.message.text.replace(',', '.'))
            if not 30 <= weight <= 300:
                await update.message.reply_text(
                    "Пожалуйста, введите реальный вес (30-300 кг):"
                )
                return WEIGHT
            
            context.user_data['weight'] = weight
            await update.message.reply_text(
                "*Шаг 4 из 7*\nВведите ваш рост (в см):\n"
                "Например: 175",
                parse_mode=ParseMode.MARKDOWN
            )
            return HEIGHT
            
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число:")
            return WEIGHT
    
    async def profile_height(self, update: Update, context: CallbackContext):
        """Получение роста"""
        try:
            height = float(update.message.text.replace(',', '.'))
            if not 100 <= height <= 250:
                await update.message.reply_text(
                    "Пожалуйста, введите реальный рост (100-250 см):"
                )
                return HEIGHT
            
            context.user_data['height'] = height
            
            keyboard = [
                [InlineKeyboardButton("Сидячий (офисная работа)", callback_data='sedentary')],
                [InlineKeyboardButton("Легкая (1-3 тренировки)", callback_data='light')],
                [InlineKeyboardButton("Умеренная (3-5 тренировок)", callback_data='moderate')],
                [InlineKeyboardButton("Высокая (6-7 тренировок)", callback_data='active')],
                [InlineKeyboardButton("Очень высокая (спорт + труд)", callback_data='very_active')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "*Шаг 5 из 7*\nВыберите уровень активности:\n\n"
                "• *Сидячий* - офисная работа\n"
                "• *Легкая* - 1-3 тренировки в неделю\n"
                "• *Умеренная* - 3-5 тренировок\n"
                "• *Высокая* - 6-7 тренировок\n"
                "• *Очень высокая* - спортсмены",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return ACTIVITY
            
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число:")
            return HEIGHT
    
    async def profile_activity(self, update: Update, context: CallbackContext):
        """Обработка выбора активности"""
        query = update.callback_query
        await query.answer()
        
        activity = query.data
        activity_texts = {
            'sedentary': 'Сидячий',
            'light': 'Легкая',
            'moderate': 'Умеренная',
            'active': 'Высокая',
            'very_active': 'Очень высокая'
        }
        context.user_data['activity_level'] = activity
        
        await query.edit_message_text(
            text=f"✅ Активность: {activity_texts[activity]}\n\n"
                 "*Шаг 6 из 7*\nВыберите ваш климат:",
            parse_mode=ParseMode.MARKDOWN
        )
        
        keyboard = [
            [InlineKeyboardButton("Холодный ❄️", callback_data='cold')],
            [InlineKeyboardButton("Умеренный 🌤️", callback_data='moderate')],
            [InlineKeyboardButton("Жаркий ☀️", callback_data='hot')],
            [InlineKeyboardButton("Очень жаркий 🔥", callback_data='very_hot')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "*Климат влияет на норму воды:*\n\n"
            "• *Холодный* - меньше воды\n"
            "• *Умеренный* - стандартно\n"
            "• *Жаркий* - больше воды\n"
            "• *Очень жаркий* - значительно больше",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return CLIMATE
    
    async def profile_climate(self, update: Update, context: CallbackContext):
        """Обработка выбора климата"""
        query = update.callback_query
        await query.answer()
        
        climate = query.data
        climate_texts = {
            'cold': 'Холодный ❄️',
            'moderate': 'Умеренный 🌤️',
            'hot': 'Жаркий ☀️',
            'very_hot': 'Очень жаркий 🔥'
        }
        context.user_data['climate'] = climate
        
        await query.edit_message_text(
            text=f"✅ Климат: {climate_texts[climate]}\n\n"
                 "Теперь выберите вашу цель:",
            parse_mode=ParseMode.MARKDOWN
        )
        
        keyboard = [
            [InlineKeyboardButton("Похудение 📉", callback_data='lose')],
            [InlineKeyboardButton("Поддержание ⚖️", callback_data='maintain')],
            [InlineKeyboardButton("Набор массы 📈", callback_data='gain')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "🎯 *Шаг 7 из 7*\nВыберите вашу цель:\n\n"
            "• *Похудение* - дефицит калорий\n"
            "• *Поддержание* - баланс\n"
            "• *Набор массы* - профицит",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return GOAL
    
    async def profile_goal(self, update: Update, context: CallbackContext):
        """Завершение создания профиля"""
        query = update.callback_query
        await query.answer()
        
        goal = query.data
        goal_texts = {
            'lose': 'Похудение 📉',
            'maintain': 'Поддержание веса ⚖️',
            'gain': 'Набор массы 📈'
        }
        context.user_data['goal'] = goal
        
        # Сохраняем профиль
        user_data = context.user_data
        
        try:
            # Рассчитываем нормы
            daily_calories, macros = self.calculator.calculate_daily_calories(
                weight=user_data['weight'],
                height=user_data['height'],
                age=user_data['age'],
                gender=user_data['gender'],
                activity_level=user_data['activity_level'],
                goal=goal
            )
            
            daily_water = self.calculator.calculate_water_needs(
                weight=user_data['weight'],
                activity_level=user_data['activity_level'],
                climate=user_data.get('climate', 'moderate')
            )
            
            bmi = self.calculator.calculate_bmi(
                user_data['weight'],
                user_data['height']
            )
            bmi_status = self.calculator.interpret_bmi(bmi)
            
            # Сохраняем в базу
            await self.db.update_user_profile(
                telegram_id=update.effective_user.id,
                age=user_data['age'],
                gender=user_data['gender'],
                weight=user_data['weight'],
                height=user_data['height'],
                activity_level=user_data['activity_level'],
                goal=goal,
                daily_calorie_goal=daily_calories,
                daily_water_goal=daily_water
            )
            
            # Сохраняем начальный вес
            await self.db.add_weight_record(
                user_id=update.effective_user.id,
                weight=user_data['weight']
            )
            
            # Формируем ответ
            completion_text = f"""
✅ *Профиль успешно создан!*

*Ваши данные:*
• Возраст: {user_data['age']}
• Пол: {'Мужской ♂️' if user_data['gender'] == 'male' else 'Женский ♀️'}
• Вес: {user_data['weight']} кг
• Рост: {user_data['height']} см
• Цель: {goal_texts[goal]}

*Результаты:*
• ИМТ: *{bmi}* ({bmi_status})
• Калории: *{daily_calories} ккал/день*
• Вода: *{daily_water} мл/день*

*Рекомендуемые БЖУ:*
• Белки: *{macros['protein']}г*
• Жиры: *{macros['fat']}г*
• Углеводы: *{macros['carbs']}г*

🎯 *Что дальше?*
1. Используйте /add_food чтобы добавить прием пищи
2. Следите за прогрессом /today
3. Получите рекомендации /recommend
            """
            
            await query.edit_message_text(
                text=completion_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error creating profile: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при создании профиля. Попробуйте позже."
            )
        
        context.user_data.clear()
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: CallbackContext):
        """Отмена создания профиля"""
        await update.message.reply_text("Создание профиля отменено.")
        context.user_data.clear()
        return ConversationHandler.END
    
    async def add_food(self, update: Update, context: CallbackContext):
        """Добавление приема пищи с использованием Open Food Facts"""
        if not context.args:
            await update.message.reply_text(
                "🍽️ *Добавление приема пищи*\n\n"
                "Формат: `/add_food [количество]г [продукт] [тип приема пищи]`\n\n"
                "*Примеры:*\n"
                "• `/add_food 200г овсянка завтрак`\n"
                "• `/add_food 150г куриная грудка обед`\n"
                "• `/add_food 1 яблоко перекус`\n\n"
                "*Типы приема пищи:*\n"
                "`завтрак`, `обед`, `ужин`, `перекус`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user_input = ' '.join(context.args)
        user_id = update.effective_user.id
        
        # Сообщение о поиске
        search_msg = await update.message.reply_text(
            "🔍 *Ищу продукт в базе Open Food Facts...*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Парсим количество
            quantity_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:г|грамм?|кг|л|мл)?', user_input.lower())
            
            if quantity_match:
                quantity = float(quantity_match.group(1))
                if 'кг' in user_input.lower():
                    quantity *= 1000
                elif 'л' in user_input.lower():
                    quantity *= 1000
                
                product_text = re.sub(r'\d+(?:\.\d+)?\s*(?:г|грамм?|кг|л|мл)?', '', user_input, count=1).strip()
            else:
                quantity = 100
                product_text = user_input
            
            # Определяем тип приема пищи
            meal_types = ['завтрак', 'обед', 'ужин', 'перекус']
            meal_type = None
            
            for mt in meal_types:
                if mt in product_text.lower():
                    meal_type = mt
                    product_text = product_text.lower().replace(mt, '').strip()
                    break
            
            if not product_text:
                await search_msg.edit_text("❌ Не указан продукт.")
                return
            
            # Ищем продукт в Open Food Facts
            product_info = await asyncio.to_thread(
                self.api.get_product_info, product_text
            )
            
            if not product_info or not product_info.success:
                await search_msg.edit_text(
                    f"❌ Не удалось найти информацию о продукте: {product_text}\n\n"
                    "💡 *Попробуйте:*\n"
                    "• Указать другое название\n"
                    "• Использовать /search для поиска"
                )
                return
            
            # Рассчитываем питательные вещества
            multiplier = quantity / product_info.serving_size_g
            
            calories = product_info.calories * multiplier
            protein = product_info.protein * multiplier
            fat = product_info.fat * multiplier
            carbs = product_info.carbs * multiplier
            
            # Сохраняем в базу
            await self.db.add_food_entry(
                user_id=user_id,
                food_data={
                    'food_name': product_info.name,
                    'calories': calories,
                    'protein': protein,
                    'fat': fat,
                    'carbs': carbs,
                    'quantity': quantity,
                    'meal_type': meal_type,
                    'source': product_info.source
                }
            )
            
            # Формируем ответ
            response = f"""
✅ *Прием пищи добавлен!*

*Продукт:* {product_info.name}
*Количество:* {quantity:.0f}{'г' if quantity <= 1000 else 'мл'}
*Тип:* {meal_type if meal_type else 'Не указан'}

📊 *Питательные вещества:*
• Калории: {calories:.0f} ккал
• Белки: {protein:.1f}г
• Жиры: {fat:.1f}г
• Углеводы: {carbs:.1f}г
"""
            
            if product_info.fiber:
                fiber_amount = product_info.fiber * multiplier
                response += f"• Клетчатка: {fiber_amount:.1f}г\n"
            
            if product_info.nova_group:
                nova_desc = {
                    1: "Минимальная обработка 🟢",
                    2: "Обработанные ингредиенты 🟡",
                    3: "Обработанные продукты 🟠",
                    4: "Ультраобработанные продукты 🔴"
                }.get(product_info.nova_group, "Неизвестно")
                response += f"• Степень обработки: {nova_desc}\n"
            
            source_desc = {
                'openfoodfacts': 'Open Food Facts 🌍',
                'local_db': 'Локальная база 📚',
                'estimation': 'Оценка 🤔'
            }.get(product_info.source, product_info.source)
            
            response += f"\n*Источник данных:* {source_desc}"
            
            await search_msg.edit_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error adding food: {e}")
            await search_msg.edit_text(
                "❌ Произошла ошибка при добавлении пищи. Попробуйте позже."
            )
    
    async def search_product(self, update: Update, context: CallbackContext):
        """Поиск продуктов в Open Food Facts"""
        if not context.args:
            await update.message.reply_text(
                "🔍 *Поиск продуктов*\n\n"
                "Формат: `/search [название продукта]`\n\n"
                "*Примеры:*\n"
                "• `/search йогурт`\n"
                "• `/search хлеб бородинский`\n"
                "• `/search Coca-Cola`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        query = ' '.join(context.args)
        
        search_msg = await update.message.reply_text(
            f"🔍 *Ищу:* {query}\n*Источник:* Open Food Facts...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Ищем продукты
            products = await asyncio.to_thread(
                self.api.search_product, query, 5
            )
            
            if not products:
                await search_msg.edit_text(
                    f"❌ *Не найдено продуктов:* {query}\n\n"
                    "💡 *Попробуйте:*\n"
                    "• Другое название\n"
                    "• Более простой запрос\n"
                    "• Английское название",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            response = f"🔍 *Результаты поиска:* {query}\n\n"
            
            for i, product in enumerate(products, 1):
                response += f"*{i}. {product.name}*\n"
                
                if product.brands:
                    response += f"   Бренд: {product.brands}\n"
                
                response += f"   📊 На 100г: {product.calories} ккал"
                response += f", Б: {product.protein}г"
                response += f", Ж: {product.fat}г"
                response += f", У: {product.carbs}г\n"
                
                if product.nova_group:
                    nova_emoji = ['🟢', '🟡', '🟠', '🔴'][product.nova_group - 1]
                    response += f"   Обработка: {nova_emoji} (NOVA {product.nova_group})\n"
                
                response += "\n"
            
            response += (
                "💡 *Как добавить продукт:*\n"
                "Используйте: `/add_food 150г [название продукта]`"
            )
            
            await search_msg.edit_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error searching product: {e}")
            await search_msg.edit_text(
                "❌ Ошибка при поиске. Попробуйте позже."
            )
    
    async def today_stats(self, update: Update, context: CallbackContext):
        """Показать статистику за сегодня"""
        user_id = update.effective_user.id
        
        try:
            # Получаем статистику
            stats = await self.db.get_today_stats(user_id)
            
            # Получаем профиль
            user_profile = await self.db.get_user_profile(user_id)
            
            if not user_profile:
                await update.message.reply_text(
                    "Сначала создайте профиль: /profile"
                )
                return
            
            daily_goal = user_profile.get('daily_calorie_goal', 2000)
            water_goal = user_profile.get('daily_water_goal', 2000)
            
            # Рассчитываем проценты
            calorie_percent = (stats['calories'] / daily_goal * 100) if daily_goal > 0 else 0
            water_percent = (stats['water'] / water_goal * 100) if water_goal > 0 else 0
            
            # Создаем прогресс-бары
            def create_progress_bar(percent, length=10):
                filled = int(percent * length / 100)
                empty = length - filled
                return '█' * filled + '░' * empty
            
            calorie_bar = create_progress_bar(min(calorie_percent, 100))
            water_bar = create_progress_bar(min(water_percent, 100))
            
            response = f"""
📊 *Статистика за сегодня*

*Калории:*
{calorie_bar}
{stats['calories']:.0f} / {daily_goal:.0f} ккал ({calorie_percent:.0f}%)

*БЖУ:*
• Белки: {stats['protein']:.1f}г
• Жиры: {stats['fat']:.1f}г
• Углеводы: {stats['carbs']:.1f}г

*Вода:*
{water_bar}
{stats['water']:.0f} / {water_goal:.0f} мл ({water_percent:.0f}%)
"""
            
            # Добавляем рекомендации
            if calorie_percent < 80:
                response += "\n💡 *Можно добавить еще пищи*"
            elif calorie_percent > 120:
                response += "\n⚠️ *Превышена дневная норма калорий*"
            else:
                response += "\n✅ *Калории в пределах нормы*"
            
            if water_percent < 70:
                response += f"\n💧 *Выпито {stats['water']:.0f} мл, цель {water_goal:.0f} мл*"
            else:
                response += "\n💧 *Отличный водный баланс!*"
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error getting today stats: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении статистики. Попробуйте позже."
            )
    
    async def water_intake(self, update: Update, context: CallbackContext):
        """Добавление выпитой воды"""
        user_id = update.effective_user.id
        
        if not context.args:
            # Показываем текущую статистику
            try:
                stats = await self.db.get_today_stats(user_id)
                user_profile = await self.db.get_user_profile(user_id)
                
                water_goal = user_profile.get('daily_water_goal', 2000) if user_profile else 2000
                water_drunk = stats.get('water', 0)
                percent = (water_drunk / water_goal * 100) if water_goal > 0 else 0
                
                response = f"""
💧 *Водный баланс*

Выпито сегодня: {water_drunk:.0f} мл
Цель: {water_goal:.0f} мл
Прогресс: {percent:.0f}%

💡 *Добавить воду:*
`/water 500` - добавить 500 мл
`/water 250` - добавить стакан воды
                """
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
                
            except Exception as e:
                logger.error(f"Error getting water stats: {e}")
                await update.message.reply_text(
                    "💧 Используйте: `/water [количество]`\nПример: `/water 500`"
                )
            return
        
        try:
            amount = float(context.args[0])
            if amount <= 0 or amount > 5000:
                await update.message.reply_text(
                    "Пожалуйста, введите разумное количество (1-5000 мл)."
                )
                return
            
            # Добавляем воду
            await self.db.add_water_intake(user_id, amount)
            
            # Показываем обновленную статистику
            stats = await self.db.get_today_stats(user_id)
            user_profile = await self.db.get_user_profile(user_id)
            
            water_goal = user_profile.get('daily_water_goal', 2000) if user_profile else 2000
            water_drunk = stats.get('water', 0)
            percent = (water_drunk / water_goal * 100) if water_goal > 0 else 0
            
            response = f"""
✅ Добавлено {amount:.0f} мл воды!

Всего сегодня: {water_drunk:.0f} мл
Цель: {water_goal:.0f} мл
Прогресс: {percent:.0f}%
"""
            
            if percent >= 100:
                response += "\n🎉 *Достигнута дневная норма воды!*"
            elif percent >= 80:
                response += "\n✅ *Почти у цели!*"
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число (количество воды в мл).")
        except Exception as e:
            logger.error(f"Error adding water: {e}")
            await update.message.reply_text(
                "❌ Ошибка при добавлении воды. Попробуйте позже."
            )
    
    async def bmi_calculator(self, update: Update, context: CallbackContext):
        """Расчет индекса массы тела"""
        user_id = update.effective_user.id
        
        # Получаем данные пользователя
        user_profile = await self.db.get_user_profile(user_id)
        
        if context.args and len(context.args) >= 2:
            try:
                weight = float(context.args[0])
                height = float(context.args[1])
            except ValueError:
                await update.message.reply_text(
                    "Пожалуйста, введите числа для веса и роста.\n"
                    "Пример: `/bmi 70 175`"
                )
                return
        elif user_profile and user_profile.get('weight') and user_profile.get('height'):
            weight = user_profile['weight']
            height = user_profile['height']
        else:
            await update.message.reply_text(
                "Сначала создайте профиль: /profile\n"
                "Или введите: `/bmi [вес] [рост]`\n"
                "Пример: `/bmi 70 175`"
            )
            return
        
        # Рассчитываем ИМТ
        bmi = self.calculator.calculate_bmi(weight, height)
        bmi_status = self.calculator.interpret_bmi(bmi)
        
        # Рассчитываем здоровый диапазон веса
        height_m = height / 100
        min_weight = 18.5 * (height_m ** 2)
        max_weight = 24.9 * (height_m ** 2)
        
        response = f"""
📏 *Индекс массы тела*

*Ваши данные:*
• Вес: {weight:.1f} кг
• Рост: {height:.1f} см

*Результат:*
• ИМТ: *{bmi}*
• Категория: *{bmi_status}*

*Здоровый диапазон веса для вашего роста:*
• Минимальный: {min_weight:.1f} кг
• Максимальный: {max_weight:.1f} кг
"""
        
        # Добавляем рекомендации
        if bmi < 18.5:
            response += "\n💡 *Рекомендации:*\n• Увеличьте потребление калорий\n• Добавьте силовые тренировки"
        elif bmi < 25:
            response += "\n✅ *Ваш вес в норме!*\n• Продолжайте питаться сбалансированно"
        elif bmi < 30:
            response += "\n⚠️ *Рекомендации:*\n• Умеренный дефицит калорий\n• Увеличьте активность"
        else:
            response += "\n🩺 *Рекомендации:*\n• Значительный дефицит калорий\n• Консультация врача\n• Регулярные тренировки"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def product_info(self, update: Update, context: CallbackContext):
        """Получение информации о продукте"""
        if not context.args:
            await update.message.reply_text(
                "🍎 *Информация о продукте*\n\n"
                "Формат: `/product_info [продукт]`\n\n"
                "*Примеры:*\n"
                "• `/product_info яблоко`\n"
                "• `/product_info Coca-Cola`\n"
                "• `/product_info хлеб`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        product_name = ' '.join(context.args)
        
        search_msg = await update.message.reply_text(
            f"🔍 *Ищу информацию о продукте:* {product_name}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            product_info = await asyncio.to_thread(
                self.api.get_product_info, product_name
            )
            
            if not product_info or not product_info.success:
                await search_msg.edit_text(
                    f"❌ Не удалось найти информацию о продукте: {product_name}"
                )
                return
            
            response = f"""
🍎 *Информация о продукте*

*Название:* {product_info.name}
*На 100 грамм:*

• Калории: {product_info.calories} ккал
• Белки: {product_info.protein}г
• Жиры: {product_info.fat}г
• Углеводы: {product_info.carbs}г
"""
            
            if product_info.fiber:
                response += f"• Клетчатка: {product_info.fiber}г\n"
            
            if product_info.sugar:
                response += f"• Сахар: {product_info.sugar}г\n"
            
            response += f"""
*Примеры порций:*
• 50г: {product_info.calories * 0.5:.0f} ккал
• 100г: {product_info.calories:.0f} ккал
• 200г: {product_info.calories * 2:.0f} ккал

*Источник данных:* Open Food Facts 🌍
"""
            
            await search_msg.edit_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error getting product info: {e}")
            await search_msg.edit_text(
                "❌ Ошибка при получении информации о продукте."
            )
    
    async def progress_tracking(self, update: Update, context: CallbackContext):
        """Отслеживание прогресса"""
        user_id = update.effective_user.id
        
        try:
            # Получаем историю веса
            weight_history = await self.db.get_weight_history(user_id, days=30)
            
            if len(weight_history) < 2:
                await update.message.reply_text(
                    "Недостаточно данных для отслеживания прогресса.\n"
                    "Добавьте несколько записей веса через профиль."
                )
                return
            
            # Создаем график
            chart = await asyncio.to_thread(
                self.calculator.create_progress_chart, weight_history
            )
            
            if chart:
                # Отправляем график
                first_weight = weight_history[0]['weight']
                last_weight = weight_history[-1]['weight']
                weight_change = last_weight - first_weight
                
                await update.message.reply_photo(
                    photo=chart,
                    caption=f"📈 *График изменения веса*\n\n"
                           f"Начальный вес: {first_weight:.1f} кг\n"
                           f"Текущий вес: {last_weight:.1f} кг\n"
                           f"Изменение: {weight_change:+.1f} кг",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text("Не удалось создать график прогресса.")
                
        except Exception as e:
            logger.error(f"Error tracking progress: {e}")
            await update.message.reply_text(
                "❌ Ошибка при отслеживании прогресса. Попробуйте позже."
            )
    
    async def get_recommendations(self, update: Update, context: CallbackContext):
        """Персонализированные рекомендации"""
        user_id = update.effective_user.id
        
        try:
            # Получаем статистику и профиль
            stats = await self.db.get_today_stats(user_id)
            user_profile = await self.db.get_user_profile(user_id)
            
            if not user_profile:
                await update.message.reply_text(
                    "Сначала создайте профиль: /profile"
                )
                return
            
            daily_goal = user_profile.get('daily_calorie_goal', 2000)
            water_goal = user_profile.get('daily_water_goal', 2000)
            
            # Рассчитываем дефицит/профицит
            calorie_diff = daily_goal - stats['calories']
            water_diff = water_goal - stats['water']
            
            response = "🎯 *Персонализированные рекомендации*\n\n"
            
            # Рекомендации по калориям
            if calorie_diff > 500:
                response += "✅ *Калории:* В пределах нормы\n"
            elif calorie_diff > 0:
                response += f"⚠️ *Калории:* Можно добавить {calorie_diff:.0f} ккал\n"
            else:
                response += f"❌ *Калории:* Превышение на {abs(calorie_diff):.0f} ккал\n"
            
            # Рекомендации по воде
            if water_diff > 500:
                response += f"💧 *Вода:* Осталось выпить {water_diff:.0f} мл\n"
            elif water_diff > 0:
                response += f"💧 *Вода:* Почти у цели, осталось {water_diff:.0f} мл\n"
            else:
                response += "✅ *Вода:* Норма достигнута\n"
            
            # Рекомендации по БЖУ
            protein_ratio = stats['protein'] / (daily_goal / 4 * 0.3) if daily_goal > 0 else 0
            if protein_ratio < 0.8:
                response += "💪 *Белок:* Добавьте белковые продукты\n"
            
            # Общие рекомендации
            response += "\n💡 *Общие советы:*\n"
            response += "• Ешьте 3-4 раза в день\n"
            response += "• Пейте воду перед едой\n"
            response += "• Включайте овощи в каждый прием\n"
            response += "• Избегайте сладких напитков\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении рекомендаций. Попробуйте позже."
            )
    
    async def food_history(self, update: Update, context: CallbackContext):
        """История питания"""
        user_id = update.effective_user.id
        
        # Определяем количество дней
        days = 7
        if context.args:
            try:
                days = int(context.args[0])
                if days < 1 or days > 30:
                    days = 7
            except ValueError:
                pass
        
        try:
            # Получаем историю
            entries = await self.db.get_food_history(user_id, days)
            
            if not entries:
                await update.message.reply_text(
                    f"За последние {days} дней не найдено записей о питании.\n"
                    "Используйте /add_food чтобы добавить прием пищи."
                )
                return
            
            # Анализируем данные
            total_calories = sum(e['calories'] for e in entries)
            avg_daily = total_calories / days
            
            # Группируем по дням
            from collections import defaultdict
            daily_stats = defaultdict(lambda: {'calories': 0, 'meals': []})
            
            for entry in entries:
                date_str = entry['date'].strftime('%d.%m')
                daily_stats[date_str]['calories'] += entry['calories']
                if entry['food_name']:
                    daily_stats[date_str]['meals'].append(entry['food_name'][:20])
            
            # Формируем ответ
            response = f"""
📅 *История питания за {days} дней*

*Общая статистика:*
• Всего приемов пищи: {len(entries)}
• Общие калории: {total_calories:.0f}
• Среднесуточные: {avg_daily:.0f}

*По дням:*
"""
            
            for date, stats in sorted(daily_stats.items()):
                response += f"\n• {date}: {stats['calories']:.0f} ккал"
                if stats['meals']:
                    unique_meals = set(stats['meals'])
                    meals_str = ', '.join(list(unique_meals)[:2])
                    if len(unique_meals) > 2:
                        meals_str += f"... (+{len(unique_meals)-2})"
                    response += f" ({meals_str})"
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error getting food history: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении истории питания. Попробуйте позже."
            )
    
    async def my_plan(self, update: Update, context: CallbackContext):
        """Показать персональный план питания"""
        user_id = update.effective_user.id
        
        try:
            user_profile = await self.db.get_user_profile(user_id)
            
            if not user_profile or not user_profile.get('daily_calorie_goal'):
                await update.message.reply_text(
                    "Сначала создайте профиль: /profile"
                )
                return
            
            daily_calories = user_profile['daily_calorie_goal']
            daily_water = user_profile.get('daily_water_goal', 2000)
            
            # Рассчитываем план питания
            nutrition_plan = await asyncio.to_thread(
                self.calculator.get_nutrition_plan, daily_calories, 4, 'balanced'
            )
            
            response = f"""
📋 *Ваш персональный план*

🎯 *Цель:* {user_profile.get('goal', 'maintain')}
⚖️ *Вес:* {user_profile.get('weight', 0)} кг
📏 *Рост:* {user_profile.get('height', 0)} см

🍽️ *Дневная норма:*
• Калории: *{daily_calories} ккал*
• Вода: *{daily_water} мл*

📅 *Рекомендуемый план питания:*
"""
            
            for meal in nutrition_plan:
                meal_name_ru = {
                    'breakfast': 'Завтрак 🍳',
                    'lunch': 'Обед 🍲',
                    'dinner': 'Ужин 🥗',
                    'snack': 'Перекус 🍎'
                }.get(meal['name'], meal['name'])
                
                response += f"\n*{meal_name_ru}*\n"
                response += f"• Калории: {meal['calories']} ккал\n"
            
            response += f"""

💡 *Советы:*
• Распределите калории равномерно
• Пейте воду за 30 минут до еды
• Не пропускайте приемы пищи
• Следите за балансом БЖУ
"""
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error getting my plan: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении плана. Попробуйте позже."
            )
    
    async def handle_message(self, update: Update, context: CallbackContext):
        """Обработка текстовых сообщений"""
        text = update.message.text.lower()
        
        # Простые ответы
        greetings = ['привет', 'здравствуй', 'добрый день', 'доброе утро', 'добрый вечер']
        farewells = ['пока', 'до свидания', 'спасибо', 'благодарю']
        
        if any(greet in text for greet in greetings):
            await update.message.reply_text(f"Привет, {update.effective_user.first_name}! Чем могу помочь?")
        elif any(farewell in text for farewell in farewells):
            await update.message.reply_text("Всегда рад помочь! Обращайтесь!")
        else:
            await update.message.reply_text(
                "Я вас не совсем понял. Используйте:\n"
                "/help - чтобы увидеть все команды\n"
                "/start - чтобы начать работу"
            )
    
    async def cancel_any(self, update: Update, context: CallbackContext):
        """Отмена любых действий"""
        await update.message.reply_text("Действие отменено.")
        return ConversationHandler.END