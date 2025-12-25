import ydb
import ydb.iam
from datetime import datetime
from typing import Optional, List, Dict, Any
import config

class YDBClient:
    def __init__(self):
        self.driver = None
        self.pool = None
        
    async def connect(self):
        """Подключение к YDB с правильными credentials"""
        if self.driver is None:
            # Получаем credentials из конфига
            credentials = config.Config.get_ydb_credentials()
            
            self.driver = ydb.Driver(
                endpoint=config.Config.YDB_ENDPOINT,
                database=config.Config.YDB_DATABASE,
                credentials=credentials,
            )
            
            try:
                await self.driver.wait(timeout=5)
                self.pool = ydb.SessionPool(self.driver)
                print("✅ Подключение к YDB успешно установлено")
            except Exception as e:
                print(f"❌ Ошибка подключения к YDB: {e}")
                raise e
            
        return self.pool

    async def execute_query(self, query: str, parameters: dict = None) -> List[Dict]:
        """Выполнить SQL-запрос"""
        async with self.pool.acquire() as session:
            prepared_query = session.prepare(query)
            
            if parameters:
                result = await session.transaction().execute(
                    prepared_query,
                    parameters,
                    commit_tx=True
                )
            else:
                result = await session.transaction().execute(
                    prepared_query,
                    commit_tx=True
                )
            
            return [dict(row) for row in result[0].rows]
    
    async def create_tables(self):
        """Создание таблиц в YDB"""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id Uint64,
                telegram_id Uint64,
                username Utf8,
                full_name Utf8,
                age Uint8,
                gender Utf8,
                weight Float,
                height Float,
                activity_level Utf8,
                goal Utf8,
                daily_calorie_goal Float,
                daily_water_goal Float,
                created_at Timestamp,
                updated_at Timestamp,
                PRIMARY KEY (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS food_entries (
                id Uint64,
                user_id Uint64,
                food_name Utf8,
                meal_type Utf8,
                calories Float,
                protein Float,
                fat Float,
                carbs Float,
                quantity Float,
                date Timestamp,
                notes Utf8,
                PRIMARY KEY (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS water_intake (
                id Uint64,
                user_id Uint64,
                amount Float,
                date Timestamp,
                PRIMARY KEY (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS weight_history (
                id Uint64,
                user_id Uint64,
                weight Float,
                date Timestamp,
                PRIMARY KEY (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id Uint64,
                language Utf8 DEFAULT "ru",
                notifications_enabled Bool DEFAULT true,
                water_reminders Bool DEFAULT true,
                meal_reminders Bool DEFAULT true,
                PRIMARY KEY (user_id)
            )
            """
        ]
        
        for query in queries:
            await self.execute_query(query)
    
    async def close(self):
        """Закрыть соединение"""
        if self.driver:
            await self.driver.stop()

# Создаем глобальный экземпляр
ydb_client = YDBClient()