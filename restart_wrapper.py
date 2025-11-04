#!/usr/bin/env python3
"""
Автоматический перезапуск бота при ошибках
"""
import asyncio
import sys
import time
import traceback
from typing import Optional
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_restart.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotRestartWrapper:
    def __init__(self, restart_delay: int = 5):
        self.restart_delay = restart_delay
        self.restart_count = 0
        self.last_restart_time = 0
        
    async def run_with_restart(self, main_func):
        """Запускает основную функцию с автоматическим перезапуском"""
        while True:  # Бесконечный цикл - бот будет перезапускаться всегда
            try:
                logger.info(f"Запуск бота (попытка {self.restart_count + 1})")
                await main_func()
                
            except KeyboardInterrupt:
                logger.info("Бот остановлен пользователем")
                break
                
            except Exception as e:
                self.restart_count += 1
                error_msg = f"Ошибка в боте: {type(e).__name__}: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Проверяем, не слишком ли часто перезапускаемся
                current_time = time.time()
                if current_time - self.last_restart_time < 30:  # Если перезапуск чаще чем раз в 30 секунд
                    logger.warning("Слишком частые перезапуски. Увеличиваем задержку.")
                    self.restart_delay = min(self.restart_delay * 2, 300)  # Максимум 5 минут
                
                logger.info(f"Перезапуск через {self.restart_delay} секунд...")
                
                try:
                    await asyncio.sleep(self.restart_delay)
                except KeyboardInterrupt:
                    logger.info("Перезапуск отменен пользователем")
                    break
                
                # Сбрасываем задержку если прошло достаточно времени с последнего перезапуска
                if current_time - self.last_restart_time > 300:  # 5 минут
                    self.restart_delay = 5
                
                self.last_restart_time = current_time

async def main():
    """Основная функция для запуска с перезапуском"""
    from main import main as bot_main
    
    wrapper = BotRestartWrapper(restart_delay=5)
    await wrapper.run_with_restart(bot_main)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа остановлена пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1) 