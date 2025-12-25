"""
SlimTracker Bot - Помощник для здорового питания
Версия для Sourcecraft с поддержкой контейнеризации
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler
from telegram.ext import filters
from config import Config
from handlers import BotHandlers, AGE, GENDER, WEIGHT, HEIGHT, ACTIVITY, GOAL, CLIMATE
from ydb_client import ydb_client
from api_client import OpenFoodFactsAPI

# Настройка логирования для Sourcecraft
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    handlers=[
        logging.StreamHandler(sys.stdout),  # Для Sourcecraft логов
        logging.FileHandler('/app/data/bot.log')  # Файловые логи
    ]
)
logger = logging.getLogger(__name__)

async def check_environment():
    """Проверка переменных окружения в Sourcecraft"""
    logger.info("🔍 Проверка окружения...")
    
    required_vars = ['TELEGRAM_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
        logger.error("Добавьте их в настройках Sourcecraft проекта")
        return False
    
    logger.info(f"✅ TELEGRAM_TOKEN: {'установлен' if Config.TELEGRAM_TOKEN else 'отсутствует'}")
    logger.info(f"✅ YDB_DATABASE: {'установлен' if Config.YDB_DATABASE else 'отсутствует (будет использована SQLite)'}")
    
    # Проверка файла с ключами YDB
    if Config.YDB_DATABASE:
        json_path = Path(Config.YDB_JSON_PATH)
        if json_path.exists():
            logger.info(f"✅ Файл с ключами YDB найден: {json_path}")
        else:
            logger.warning(f"⚠️ Файл с ключами YDB не найден: {json_path}")
            logger.warning("Бот будет использовать локальную SQLite базу")
    
    return True

async def initialize_database():
    """Инициализация базы данных"""
    try:
        if Config.YDB_DATABASE:
            logger.info("🔄 Подключение к YDB...")
            await ydb_client.connect()
            await ydb_client.create_tables()
            logger.info("✅ YDB подключена")
        else:
            # Используем SQLite
            from database import create_local_tables
            create_local_tables()
            logger.info("✅ Локальная SQLite база инициализирована")
            
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        # Fallback на SQLite
        from database import create_local_tables
        create_local_tables()
        logger.info("🔄 Используем локальную SQLite базу")

async def initialize_services():
    """Инициализация всех сервисов"""
    logger.info("🚀 Инициализация SlimTracker Bot...")
    
    # Проверяем окружение
    if not await check_environment():
        sys.exit(1)
    
    # Инициализируем базу данных
    await initialize_database()
    
    # Тестируем API
    try:
        api = OpenFoodFactsAPI()
        test = api.get_product_info("яблоко")
        logger.info(f"✅ Open Food Facts API работает, тестовый запрос: {test.name if test else 'ошибка'}")
    except Exception as e:
        logger.warning(f"⚠️ Open Food Facts API недоступен: {e}")

def setup_handlers(dispatcher):
    """Настройка обработчиков команд"""
    bot_handlers = BotHandlers()
    
    # ConversationHandler для профиля
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('profile', bot_handlers.profile_start)],
        states={
            AGE: [MessageHandler(Filters.text & ~Filters.command, bot_handlers.profile_age)],
            GENDER: [CallbackQueryHandler(bot_handlers.profile_gender)],
            WEIGHT: [MessageHandler(Filters.text & ~Filters.command, bot_handlers.profile_weight)],
            HEIGHT: [MessageHandler(Filters.text & ~Filters.command, bot_handlers.profile_height)],
            ACTIVITY: [CallbackQueryHandler(bot_handlers.profile_activity)],
            CLIMATE: [CallbackQueryHandler(bot_handlers.profile_climate)],
            GOAL: [CallbackQueryHandler(bot_handlers.profile_goal)],
        },
        fallbacks=[CommandHandler('cancel', bot_handlers.cancel)]
    )
    
    # Регистрация всех команд
    commands = [
        ('start', bot_handlers.start),
        ('help', bot_handlers.help_command),
        ('add_food', bot_handlers.add_food),
        ('search', bot_handlers.search_product),
        ('today', bot_handlers.today_stats),
        ('water', bot_handlers.water_intake),
        ('bmi', bot_handlers.bmi_calculator),
        ('product_info', bot_handlers.product_info),
        ('progress', bot_handlers.progress_tracking),
        ('recommend', bot_handlers.get_recommendations),
        ('history', bot_handlers.food_history),
        ('myplan', bot_handlers.my_plan),
    ]
    
    dispatcher.add_handler(conv_handler)
    for command, handler in commands:
        dispatcher.add_handler(CommandHandler(command, handler))
    
    # Обработчик обычных сообщений
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, bot_handlers.handle_message))
    
    # Обработчик ошибок
    dispatcher.add_error_handler(error_handler)
    
    logger.info(f"✅ Зарегистрировано {len(commands) + 1} команд")

def error_handler(update, context):
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)
    
    try:
        if update and update.effective_message:
            update.effective_message.reply_text(
                "❌ Произошла ошибка. Пожалуйста, попробуйте позже.\n"
                "Если ошибка повторяется, обратитесь к администратору."
            )
    except:
        pass

def health_check():
    """Проверка здоровья для Sourcecraft"""
    try:
        # Простая проверка - если файл бота существует
        if Path(__file__).exists():
            return True
        return False
    except:
        return False

def main():
    """Точка входа для Sourcecraft"""
    
    # Проверка обязательных переменных
    if not Config.TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN не установлен!")
        logger.error("Установите переменную TELEGRAM_TOKEN в настройках Sourcecraft")
        sys.exit(1)
    
    # Настройка event loop для асинхронности
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Инициализация сервисов
    loop.run_until_complete(initialize_services())
    
    try:
        # Создаем Updater
        updater = Updater(
            token=Config.TELEGRAM_TOKEN,
            use_context=True,
            request_kwargs={
                'read_timeout': 30,
                'connect_timeout': 30,
                'pool_timeout': 30
            }
        )
        
        # Настройка обработчиков
        setup_handlers(updater.dispatcher)
        
        # Запуск бота
        logger.info("🤖 Запуск SlimTracker Bot...")
        logger.info(f"📊 Режим: {'DEBUG' if Config.DEBUG else 'PRODUCTION'}")
        logger.info(f"📝 Логи: {Config.LOG_LEVEL}")
        
        # Используем polling для Sourcecraft
        updater.start_polling(
            drop_pending_updates=True,
            timeout=30,
            poll_interval=0.5,
            allowed_updates=['message', 'callback_query']
        )
        
        logger.info("✅ Бот запущен и готов к работе!")
        
        # Бесконечный цикл
        updater.idle()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Остановка по запросу пользователя")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
    finally:
        # Корректное завершение
        logger.info("🔄 Завершение работы...")
        loop.run_until_complete(ydb_client.close())

if __name__ == '__main__':
    # Проверка версии Python
    if sys.version_info < (3, 7):
        print("❌ Требуется Python 3.7+")
        sys.exit(1)
    
    # Запуск
    main()