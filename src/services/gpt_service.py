# src/services/gpt_service.py
import os
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from openai import OpenAI
from jsonschema import validate, ValidationError

class GPTservice:
    def __init__(self, db: Optional[Session] = None, model: str = "gpt-4o-mini"):
        self.db = db
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def _categories_items_schema(self, available: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string", "enum": [c["name"] for c in available]},
            },
        } if available else {"type": "object"}
        

    def summarize_and_categorize(
        self,
        title_ru: str,
        article_text_ru: str,
        available_categories: List[Dict[str, Any]],  # теперь список словарей {id, name}
        *,
        max_tokens: int = 1200,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "titles": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["en", "ru", "kk"],
                    "properties": {
                        "en": {"type": "string", "minLength": 5, "maxLength": 140},
                        "ru": {"type": "string", "minLength": 5, "maxLength": 140},
                        "kk": {"type": "string", "minLength": 5, "maxLength": 140},
                    },
                },
                "summaries": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["en", "ru", "kk"],
                    "properties": {
                        "en": {"type": "string", "minLength": 40, "maxLength": 800},
                        "ru": {"type": "string", "minLength": 40, "maxLength": 800},
                        "kk": {"type": "string", "minLength": 40, "maxLength": 800},
                    },
                },
                "selected_categories": {
                    "type": "array",
                    "uniqueItems": True,
                    "minItems": 1,
                    "maxItems": 6,
                    "items": self._categories_items_schema(available_categories),
                },
            },
            "required": ["titles", "summaries", "selected_categories"],
        }

        system_msg = (
            "You are a professional news editor and translator (RU→EN, RU→KK). "
            "Write concise, factual outputs strictly from the provided article. "
            "No extra facts. Neutral media tone."
        )

        # формируем строку вида: "1 — Политика, 2 — Экономика, 3 — Спорт..."
        cats_str = ", ".join([f"{c['id']} — {c['name']}" for c in available_categories])

        user_msg = f"""
    ЗАДАЧА:
    1) Перефразируй заголовок (EN, RU, KK) — сохраняй смысл, не копируй дословно, без кликбейта.
    2) Краткое содержание (EN, RU, KK) по 2–4 предложения, только факты из текста.
    • EN/RU: профессиональный новостной стиль.
    • KK: әдеби нормаларға сай, калькадан аулақ, табиғи тіркестер.
    3) Выбери от 1 до 6 категорий строго из списка (верни id и name).

    ДАНО:
    • Заголовок (RU): {title_ru}
    • Текст (RU): {article_text_ru}

    СПИСОК ДОСТУПНЫХ КАТЕГОРИЙ (id — название):
    {cats_str}

    ТРЕБОВАНИЯ:
    • Используй только информацию из текста.
    • Верни строго JSON с полями: 
    - titles{{en,ru,kk}}, 
    - summaries{{en,ru,kk}}, 
    - selected_categories[] (каждый элемент {{id, name}}).
    """

        tools = [{
            "type": "function",
            "function": {
                "name": "news_multilang_summary",
                "description": "Return structured translations, summaries and categories for a news article.",
                "parameters": schema,
            }
        }]

        comp = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "news_multilang_summary"}},
        )

        tool_calls = comp.choices[0].message.tool_calls
        if not tool_calls:
            raise RuntimeError("Модель не вернула function-call с данными.")
        args = tool_calls[0].function.arguments
        result = json.loads(args)

        try:
            validate(instance=result, schema=schema)
        except ValidationError as e:
            raise RuntimeError(f"Invalid GPT response: {e.message}")
        
        return result
    
    
    
    def get_embedding(
        self, 
        text: str, 
        model: str = "text-embedding-3-small"
    ) -> List[float]:
        """
        Получает эмбеддинг для текста с помощью OpenAI API
        
        Args:
            text: Текст для получения эмбеддинга
            model: Модель для эмбеддинга (по умолчанию text-embedding-3-small)
            
        Returns:
            List[float]: Вектор эмбеддинга
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=model
            )
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"Ошибка получения эмбеддинга: {str(e)}")
