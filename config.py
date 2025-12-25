import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot Token
    TELEGRAM_TOKEN = os.getenv('8382599129:AAFfIIenNkyCSkjHw3SAlXBDH7JPyWY7iVs')
    
    # Yandex Cloud YDB
    YDB_ENDPOINT = os.getenv('YDB_ENDPOINT', 'grpcs://ydb.serverless.yandexcloud.net:2135/?database=/ru-central1/b1gumsvre1hlrs9s5ijr/etnenas6dimrn967nisv')
    YDB_DATABASE = os.getenv('YDB_DATABASE', '/ru-central1/b1gumsvre1hlrs9s5ijr/etnenas6dimrn967nisv')
    
    # Путь к JSON файлу с ключами
    YDB_JSON_PATH = os.getenv('YDB_JSON_PATH', './authorized_key.json')
    
    # Open Food Facts
    OPENFOODFACTS_REQUEST_TIMEOUT = int(os.getenv('OPENFOODFACTS_REQUEST_TIMEOUT', '10'))
    OPENFOODFACTS_CACHE_HOURS = int(os.getenv('OPENFOODFACTS_CACHE_HOURS', '1'))
    

    
    # Параметры расчета
    WATER_MULTIPLIER = 35
    
    # Настройки приложения
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def get_ydb_credentials(cls):
        """Чтение credentials из JSON файла"""
        import ydb.iam
        
        json_path = Path(cls.YDB_JSON_PATH)
        if json_path.exists():
            with open(json_path, 'r') as f:
                key_data = json.load(f)
            return ydb.iam.ServiceAccountCredentials.from_json(key_data)
        
        return ydb.iam.MetadataUrlCredentials()