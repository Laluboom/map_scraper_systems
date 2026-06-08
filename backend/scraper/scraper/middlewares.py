import os
from scrapy import signals


class ProxyRotationMiddleware:
    """Routes all requests through the configured proxy. PH-007: set PROXY_URL in .env."""

    def __init__(self, proxy_url: str):
        self.proxy_url = proxy_url

    @classmethod
    def from_crawler(cls, crawler):
        proxy_url = crawler.settings.get("PROXY_URL", "")
        return cls(proxy_url)

    def process_request(self, request, spider):
        if self.proxy_url:
            request.meta["proxy"] = self.proxy_url
