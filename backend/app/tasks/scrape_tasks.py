from app.celery_app import celery_app

SPIDER_MAP = {
    "isri": "scraper.spiders.isri_spider.ISRISpider",
    "bir": "scraper.spiders.bir_spider.BIRSpider",
    "cari": "scraper.spiders.cari_spider.CARISpider",
    "yellowpages": "scraper.spiders.yellowpages_spider.YellowPagesSpider",
    "kompass": "scraper.spiders.kompass_spider.KompassSpider",
    "europages": "scraper.spiders.europages_spider.EuropagesSpider",
    "thomasnet": "scraper.spiders.thomasnet_spider.ThomasNetSpider",
    "scrapmonster": "scraper.spiders.scrapmonster_spider.ScrapMonsterSpider",
    "recycling_intl": "scraper.spiders.recycling_intl_spider.RecyclingIntlSpider",
    "epa": "scraper.spiders.epa_spider.EPASpider",
}


@celery_app.task
def run_spider(source: str, regions: list[str]):
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    import importlib

    spider_path = SPIDER_MAP.get(source)
    if not spider_path:
        return {"error": f"Unknown source: {source}"}

    module_path, class_name = spider_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    spider_cls = getattr(module, class_name)

    process = CrawlerProcess(get_project_settings())
    process.crawl(spider_cls, regions=regions)
    process.start()
    return {"status": "completed", "source": source}
