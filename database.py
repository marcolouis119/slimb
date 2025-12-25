from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio
from ydb_client import ydb_client

class DatabaseManager:
    
    @staticmethod
    async def get_or_create_user(telegram_id: int, username: str = None, full_name: str = None):
        """Получить или создать пользователя в YDB"""
        try:
            # Проверяем существование пользователя
            query = """
            SELECT * FROM users WHERE telegram_id = $telegram_id
            """
            
            result = await ydb_client.execute_query(query, {
                "telegram_id": telegram_id
            })
            
            if result:
                return result[0]
            
            # Создаем нового пользователя
            user_id_query = """
            SELECT MAX(id) as max_id FROM users
            """
            max_id_result = await ydb_client.execute_query(user_id_query)
            new_id = (max_id_result[0].get('max_id') or 0) + 1 if max_id_result else 1
            
            insert_query = """
            INSERT INTO users (id, telegram_id, username, full_name, created_at)
            VALUES ($id, $telegram_id, $username, $full_name, $created_at)
            """
            
            await ydb_client.execute_query(insert_query, {
                "id": new_id,
                "telegram_id": telegram_id,
                "username": username or "",
                "full_name": full_name or "",
                "created_at": datetime.utcnow()
            })
            
            return {
                "id": new_id,
                "telegram_id": telegram_id,
                "username": username,
                "full_name": full_name
            }
            
        except Exception as e:
            print(f"Error in get_or_create_user: {e}")
            raise
    
    @staticmethod
    async def update_user_profile(telegram_id: int, **kwargs):
        """Обновить профиль пользователя в YDB"""
        try:
            # Получаем текущие данные пользователя
            user = await DatabaseManager.get_or_create_user(telegram_id)
            
            update_fields = []
            params = {"telegram_id": telegram_id}
            
            for key, value in kwargs.items():
                if value is not None:
                    update_fields.append(f"{key} = ${key}")
                    params[key] = value
            
            if not update_fields:
                return True
            
            update_fields.append("updated_at = $updated_at")
            params["updated_at"] = datetime.utcnow()
            
            query = f"""
            UPDATE users
            SET {', '.join(update_fields)}
            WHERE telegram_id = $telegram_id
            """
            
            await ydb_client.execute_query(query, params)
            return True
            
        except Exception as e:
            print(f"Error in update_user_profile: {e}")
            return False
    
    @staticmethod
    async def add_food_entry(user_id: int, food_data: Dict):
        """Добавить запись о приеме пищи в YDB"""
        try:
            # Генерируем ID
            id_query = """
            SELECT MAX(id) as max_id FROM food_entries
            """
            max_id_result = await ydb_client.execute_query(id_query)
            new_id = (max_id_result[0].get('max_id') or 0) + 1 if max_id_result else 1
            
            query = """
            INSERT INTO food_entries (
                id, user_id, food_name, meal_type, calories, protein, 
                fat, carbs, quantity, date
            ) VALUES (
                $id, $user_id, $food_name, $meal_type, $calories, $protein,
                $fat, $carbs, $quantity, $date
            )
            """
            
            await ydb_client.execute_query(query, {
                "id": new_id,
                "user_id": user_id,
                "food_name": food_data.get('food_name', ''),
                "meal_type": food_data.get('meal_type'),
                "calories": food_data.get('calories', 0),
                "protein": food_data.get('protein', 0),
                "fat": food_data.get('fat', 0),
                "carbs": food_data.get('carbs', 0),
                "quantity": food_data.get('quantity', 0),
                "date": datetime.utcnow()
            })
            
            return new_id
            
        except Exception as e:
            print(f"Error in add_food_entry: {e}")
            raise
    
    @staticmethod
    async def get_today_stats(user_id: int):
        """Получить статистику за сегодня из YDB"""
        try:
            today = datetime.utcnow().date()
            tomorrow = today + timedelta(days=1)
            
            # Статистика по еде
            food_query = """
            SELECT 
                SUM(calories) as total_calories,
                SUM(protein) as total_protein,
                SUM(fat) as total_fat,
                SUM(carbs) as total_carbs
            FROM food_entries 
            WHERE user_id = $user_id 
            AND date >= $today 
            AND date < $tomorrow
            """
            
            food_result = await ydb_client.execute_query(food_query, {
                "user_id": user_id,
                "today": today,
                "tomorrow": tomorrow
            })
            
            # Статистика по воде
            water_query = """
            SELECT SUM(amount) as total_water
            FROM water_intake
            WHERE user_id = $user_id
            AND date >= $today 
            AND date < $tomorrow
            """
            
            water_result = await ydb_client.execute_query(water_query, {
                "user_id": user_id,
                "today": today,
                "tomorrow": tomorrow
            })
            
            return {
                'calories': food_result[0].get('total_calories') or 0,
                'protein': food_result[0].get('total_protein') or 0,
                'fat': food_result[0].get('total_fat') or 0,
                'carbs': food_result[0].get('total_carbs') or 0,
                'water': water_result[0].get('total_water') or 0
            }
            
        except Exception as e:
            print(f"Error in get_today_stats: {e}")
            return {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'water': 0}
    
    @staticmethod
    async def add_water_intake(user_id: int, amount: float):
        """Добавить запись о воде в YDB"""
        try:
            id_query = """
            SELECT MAX(id) as max_id FROM water_intake
            """
            max_id_result = await ydb_client.execute_query(id_query)
            new_id = (max_id_result[0].get('max_id') or 0) + 1 if max_id_result else 1
            
            query = """
            INSERT INTO water_intake (id, user_id, amount, date)
            VALUES ($id, $user_id, $amount, $date)
            """
            
            await ydb_client.execute_query(query, {
                "id": new_id,
                "user_id": user_id,
                "amount": amount,
                "date": datetime.utcnow()
            })
            
            return new_id
            
        except Exception as e:
            print(f"Error in add_water_intake: {e}")
            raise
    
    @staticmethod
    async def add_weight_record(user_id: int, weight: float):
        """Добавить запись о весе в YDB"""
        try:
            id_query = """
            SELECT MAX(id) as max_id FROM weight_history
            """
            max_id_result = await ydb_client.execute_query(id_query)
            new_id = (max_id_result[0].get('max_id') or 0) + 1 if max_id_result else 1
            
            query = """
            INSERT INTO weight_history (id, user_id, weight, date)
            VALUES ($id, $user_id, $weight, $date)
            """
            
            await ydb_client.execute_query(query, {
                "id": new_id,
                "user_id": user_id,
                "weight": weight,
                "date": datetime.utcnow()
            })
            
            return new_id
            
        except Exception as e:
            print(f"Error in add_weight_record: {e}")
            raise
    
    @staticmethod
    async def get_user_profile(telegram_id: int):
        """Получить профиль пользователя из YDB"""
        try:
            query = """
            SELECT * FROM users 
            WHERE telegram_id = $telegram_id
            LIMIT 1
            """
            
            result = await ydb_client.execute_query(query, {
                "telegram_id": telegram_id
            })
            
            return result[0] if result else None
            
        except Exception as e:
            print(f"Error in get_user_profile: {e}")
            return None
    
    @staticmethod
    async def get_weight_history(user_id: int, days: int = 30):
        """Получить историю веса из YDB"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = """
            SELECT * FROM weight_history
            WHERE user_id = $user_id
            AND date >= $start_date
            ORDER BY date ASC
            """
            
            return await ydb_client.execute_query(query, {
                "user_id": user_id,
                "start_date": start_date
            })
            
        except Exception as e:
            print(f"Error in get_weight_history: {e}")
            return []
    
    @staticmethod
    async def get_food_history(user_id: int, days: int = 7):
        """Получить историю питания из YDB"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = """
            SELECT * FROM food_entries
            WHERE user_id = $user_id
            AND date >= $start_date
            ORDER BY date DESC
            """
            
            return await ydb_client.execute_query(query, {
                "user_id": user_id,
                "start_date": start_date
            })
            
        except Exception as e:
            print(f"Error in get_food_history: {e}")
            return []