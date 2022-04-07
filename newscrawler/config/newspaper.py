import re

import newspaper
from newspaper.extractors import ContentExtractor as NewspaperExtractor

from newscrawler.url_utilities import valid_url


def format_proxy(proxy):
    """
    Format proxy configuration to be used with newspaper configuration, which uses requests.request function
    Args:
        proxy: String or dictionary containing proxy configuration
                Example 1. "http://user:pass@proxy_host:proxy_port"
                Example 2. {
                               "http": "http://user:pass@proxy_host:proxy_port",
                               "https": "http://user:pass@proxy_host:proxy_port"
                           }
                Example 3.  {
                                "http": (proxy_host, proxy_port, user, pass),
                                "https": (proxy_host, proxy_port, user, pass)
                            }

    Returns: A dictionary formatted as a valid requests.request 'proxies' param

    """

    if isinstance(proxy, str):
        return {
            "http": proxy,
            "https": proxy
        }

    if isinstance(proxy, dict):
        if len(proxy) == 0:
            return proxy

        final_proxy = {}
        for schema, values in proxy.items():
            if isinstance(values, str):
                proxy_as_string = values
            elif values[2]:
                if re.match("http(s)?://", values[0]):
                    proxy_as_string = re.match("http(s)?://", values[0]).group(0)
                    proxy_as_string += values[2] + ":" + values[3] + "@"
                    proxy_as_string += re.sub("http(s)?://", "", values[0]) + ":" + values[1]
                else:
                    proxy_as_string = schema + "://" + values[2] + ":" + values[3] + "@" + values[0] + ":" + values[1]
            else:
                if re.match("http(s)?://", values[0]):
                    proxy_as_string = values[0] + ":" + values[1]
                else:
                    proxy_as_string = schema + "://" + values[0] + ":" + values[1]

            prox = {
                schema: proxy_as_string
            }

            final_proxy.update(prox)

        return final_proxy


def construct_config(proxy=None, **kwargs):
    config = newspaper.Config()
    config.fetch_images = False
    config.memoize_articles = False
    if 'user_agent' in kwargs:
        config.browser_user_agent = kwargs['user_agent']
    if 'timeout' in kwargs:
        config.request_timeout = int(kwargs['timeout'])
    if proxy:
        config.proxies = format_proxy(proxy)
    return config


class Article(newspaper.Article):
    def __init__(self, url, title='', source_url='', config=None, proxy=None, **kwargs):
        proxy = format_proxy(proxy)
        if not isinstance(config, newspaper.Config):
            config = construct_config(proxy)
        super(Article, self).__init__(url, title, source_url, config, **kwargs)


# class Source(newspaper.Source):
#     def __init__(self, url, config=None, **kwargs):
#         proxy = PROXY
#         if 'proxy' in kwargs:
#             proxy = kwargs.pop('proxy')
#         if not isinstance(config, newspaper.Config):
#             config = construct_config(proxy)
#         super(Source, self).__init__(url, config, **kwargs)


class ContentExtractor(NewspaperExtractor):
    def __init__(self, config=None):
        if not isinstance(config, newspaper.Config):
            config = construct_config()
        super(ContentExtractor, self).__init__(config)


def categories_to_articles(magazine):
    """Takes the categories, splays them into a big list of urls and churns
    the articles out of each url with the url_to_article method
    """
    articles = []
    for category in magazine.categories:
        urls_ = magazine.extractor.get_urls(category.doc)
        before_purge = len(urls_)

        cur_articles = [
            valid_url(art_url, parent_url=magazine.url, same_domain=True, mag_categories=magazine.categories) for
            art_url in urls_]
        cur_articles = [art for art in cur_articles if art]
        after_purge = len(cur_articles)

        articles.extend(cur_articles)

        print('%d->%d for %s' % (before_purge, after_purge, category.url))
    return articles
