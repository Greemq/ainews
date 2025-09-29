# run_once.py
from celery_app import app
from tasks import run_all_parsers, run_summary_generation

if __name__ == "__main__":
    # запуск парсеров один раз
    run_all_parsers.apply_async(queue="parsers")
    
    # запуск генерации summary один раз
    run_summary_generation.apply_async(queue="summaries")
    
    print("Задачи отправлены в очереди.")
