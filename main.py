# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1 import news
from src.api.v1 import clusters

app = FastAPI()

# ✅ Разрешаем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # адрес Nuxt
    allow_credentials=True,
    allow_methods=["*"],   # или ["GET", "POST"]
    allow_headers=["*"],   # или ["Authorization", "Content-Type"]
)

# ✅ Подключаем роуты
app.include_router(news.router)
app.include_router(clusters.router)
