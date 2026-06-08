import os

BOT_NAME = "scraper"
SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

ROBOTSTXT_OBEY = True

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

DOWNLOADER_MIDDLEWARES = {
    "scraper.middlewares.ProxyRotationMiddleware": 350,
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
}

ITEM_PIPELINES = {
    "scraper.pipelines.DeduplicationPipeline": 200,
    "scraper.pipelines.DatabasePipeline": 300,
}

PROXY_URL = os.environ.get("PROXY_URL", "")  # PH-007

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
