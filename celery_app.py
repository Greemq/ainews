from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

app = Celery(
    "kaznews",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

# Регистрация двух очередей
app.conf.task_queues = {
    "parsers": {},   # очередь для парсеров
    "summaries": {}  # очередь для генерации summary
}
import tasks  

# Планировщик
app.conf.beat_schedule = {
    "run-parsers-every-10-minutes": {
        "task": "tasks.run_all_parsers",
	"schedule": timedelta(seconds=10),
        "options": {"queue": "parsers"},    # кладём задачу в очередь parsers
    },
    "run-summary-generation-every-10-minutes": {
        "task": "tasks.run_summary_generation",
	"schedule": timedelta(seconds=10),
        "options": {"queue": "summaries"},  # кладём задачу в очередь summaries
    },
}
app.conf.timezone = "UTC"
