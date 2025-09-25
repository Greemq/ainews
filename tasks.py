import logging
from dotenv import load_dotenv
from src.models.category import Category
from src.models.source import SourceType
from src.parsers.informburo_parser import InformburoParser
from src.parsers.kazinform_parser import KazinformParser
from src.parsers.nur_parser import NurParser
from src.parsers.zakon_parser import ZakonParser
from celery_app import app
from src.services.source_service import SourceService
from src.parsers.rss_parser import RSSParser
from src.services.news_service import NewsService
from src.services.gpt_service import GPTservice
from src.services.category_service import CategoryService
from src.database.db import get_db

logger = logging.getLogger(__name__)

@app.task(queue="parsers")
def run_all_parsers():
    db = next(get_db())
    newsService = NewsService(db)
    sourceService = SourceService(db)

    sources = sourceService.get_all()
    for source in sources:
        try:
            if source.source_type == SourceType.TENGRINEWS:
                parser = RSSParser(source, newsService)
            elif source.source_type == SourceType.KAZINFORM:
                parser = KazinformParser(source, newsService)
            elif source.source_type == SourceType.ZAKON:
                parser = ZakonParser(source, newsService)
            elif source.source_type == SourceType.NUR:
                parser = NurParser(source, newsService)
            elif source.source_type == SourceType.INFORMBURO:
                parser = InformburoParser(source, newsService)
            else:
                logger.warning(f"Unknown source type: {source.source_type}")
                continue

            parser.parse()
            logger.info(f"Parsed successfully: {source.name}")
        except Exception as e:
            logger.exception(f"Error while parsing source {source.name}: {e}")


@app.task(queue="summaries")
def run_summary_generation():
    load_dotenv()
    db = next(get_db())
    newsService = NewsService(db)
    gptService = GPTservice()
    categoryService = CategoryService(db)

    try:
        pending_news = newsService.get_pending_summaries()
        categories = categoryService.get_all()
        available_categories = [c.to_dict() for c in categories]

        if not pending_news:
            logger.info("No news items pending summary generation.")
            return

        for n in pending_news:
            try:
                result = gptService.summarize_and_categorize(
                    n.title,
                    n.content,
                    available_categories
                )

                # Заголовки
                n.title_en = result["titles"]["en"]
                n.title_ru = result["titles"]["ru"]
                n.title_kz = result["titles"]["kk"]

                # Сводки
                n.summary_en = result["summaries"]["en"]
                n.summary_ru = result["summaries"]["ru"]
                n.summary_kz = result["summaries"]["kk"]

                # Категории
                selected_ids = [c["id"] for c in result["selected_categories"]]
                selected_cats = db.query(Category).filter(Category.id.in_(selected_ids)).all()

                n.categories = selected_cats
                n.has_summary = True

                db.commit()
                logger.info(f"Updated summary for news {n.id}: {n.title_en}")
            except Exception as inner_e:
                db.rollback()
                logger.exception(f"Error processing news {n.id}: {inner_e}")

        logger.info(f"Generated summaries for {len(pending_news)} news items.")
    except Exception as e:
        logger.exception(f"Error during summary generation: {e}")
