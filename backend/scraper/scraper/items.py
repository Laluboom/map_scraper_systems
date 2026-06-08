import scrapy


class TraderItem(scrapy.Item):
    company_name = scrapy.Field()
    email = scrapy.Field()
    phone = scrapy.Field()
    address = scrapy.Field()
    city = scrapy.Field()
    country = scrapy.Field()
    source = scrapy.Field()
    product_tags = scrapy.Field()
    priority_flag = scrapy.Field()
    raw_text = scrapy.Field()
