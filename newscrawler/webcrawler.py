import asyncio
import os
import pytz

from datetime import datetime
from http_requests import create_client, get_valid_loop, add_async_callback, async_request, sync_request
# from threading import Thread
from urllib.parse import urlsplit

# Para la libreria tldextract, usada por newspaper3k
tldextract_cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public_suffix_list.dat")
os.environ["TLDEXTRACT_CACHE"] = tldextract_cache_file

import newspaper
from newspaper.source import Category

from .config import Article, categories_to_articles, construct_config, format_proxy, logger
from .url_utilities import filter_articles


async def _define_magazine(url, client, get_visited_links_function, loop, **request_kwargs):
    try:
        response = async_request(url, client=client, close_client_at_end=False, **request_kwargs)
        if response is None:
            return url, []
        html = response.text
        real_url = response.http_response.url.strip("/") + "/"

        proxy = request_kwargs.get('proxy')

        magazine = newspaper.build(url, dry=True, config=construct_config(proxy))
        magazine.html = html
        magazine.parse()

        magazine.set_categories()

        for cat in magazine.categories:
            if cat.uri[-1] != "/":
                cat.uri += "/"
        if real_url not in [c.uri for c in magazine.categories]:
            magazine.categories.append(Category(url=real_url))
        await loop.run_in_executor(None, magazine.download_categories)
        magazine.parse_categories()
        # magazine.generate_articles(limit=10000)
        articles_urls_set = set(categories_to_articles(magazine))

        logger.info(
            "Pre-filtered articles size for {0}: ".format(url) + str(len(articles_urls_set)) + "\n")

        curr_arts = filter_articles(source_url=url, art_urls=articles_urls_set,
                                    get_visited_links_function=get_visited_links_function)
        logger.info(
            "Post-filtered articles size for {0}: ".format(url) + str(len(curr_arts)) + "\n")
        return url, curr_arts
    except Exception as err:
        logger.error(
            "_define_magazines:: Lanza un error de tipo " + str(type(err)) + " y texto " + str(err) + " para {}".format(
                url))
        return url, []


async def _process_articles(magazine_info, client, add_article_function, loop, **request_kwargs):
    if not isinstance(magazine_info, (tuple, list)) or len(magazine_info) != 2:
        logger.error(
            f"Magazine info is not properly formated: \nType: {type(magazine_info)} \nLength: {str(len(magazine_info))}")
        return
    source_url, articles_list = magazine_info
    for article_url in articles_list:
        try:
            response = async_request(article_url, client=client, **request_kwargs)
            if response is None:
                continue

            proxy = request_kwargs.get('proxy')
            text = response.text

            article = Article(url=article_url, source_url=source_url, proxy=proxy)
            article.set_html(text)
            article.parse()
            title = article.title or ""
            url = article.url or ""
            description = article.meta_description or title
            text = article.text or ""
            if type(article.publish_date) == datetime:
                date = article.publish_date.strftime(format="%Y-%m-%d")
            elif article.publish_date not in ['', 'None', None]:
                date = article.publish_date.split()[0]
            else:
                now = datetime.now().replace(tzinfo=pytz.UTC)
                str_now = now.strftime(format="%Y-%m-%d")
                date = str_now

            # new_url_as_set = set([url])
            #
            # try:
            #     set_visited_links_function(source_url, new_url_as_set)
            #     logger.info(
            #         "Updated visited links for source {0} with link {1}\n".format(source_url, url))
            # # En caso de que al actualizar los links, los conjuntos sean iguales, se lanza un ValueError
            # except ValueError as err:
            #     logger.warning(
            #         "VALUE ERROR updating visited links with {0}: ".format(
            #             url) + str(err) + "\n")
            #     continue
            # # Cualquier otra excepcion detiene la operacion
            # except Exception as err:
            #     logger.error(
            #         "CRITICAL ERROR updating visited links with {0}: ".format(
            #             url) + str(err) + "\n")
            #     continue

            text = text.strip().rstrip().replace("\'", "\"")
            title = title.replace("\'", "\"")
            description = description.replace("\'", "\"")

            download_dict = {
                "source": source_url,
                "url": url,
                "title": title,
                "text": text,
                "date": date,
                "description": description,
            }

            add_article_function(download_dict)

            logger.info("Article '{}' successfully processed".format(url))

        except Exception as err:
            logger.error("_process_article:: " + str(err))
            continue


async def add_callback(url, client, get_visited_links_function, add_article_function,
                       loop, **request_kwargs):
    # coro = asyncio.ensure_future(_define_magazines(url, DOWNLOAD_INSTANCE, loop, PROXY, USER_AGENT, TIMEOUT))
    # coro.add_done_callback(_process_article)
    # return coro

    future_fn = _define_magazine
    future_fn_args = (url, client, get_visited_links_function, loop)

    callback = _process_articles
    callback_args = (client, add_article_function, loop)

    return add_async_callback(future_fn, future_fn_args, request_kwargs, callback, callback_args, request_kwargs)


def find_redirection_url(url, proxy=None):
    splitted_url = urlsplit(url=url)
    scheme, netloc, path = splitted_url.scheme, splitted_url.netloc, splitted_url.path
    if scheme == '':
        url = "http://" + url
    req_proxy = format_proxy(proxy)
    response = sync_request(
        url=url,
        method='head',
        proxy_cfg=req_proxy,
        kwargs={
            "logger": logger,
            "allow_redirects": True
        }
    )
    # response = requests.head(url=url, proxies=req_proxy, allow_redirects=True, timeout=TIMEOUT, headers=headers)
    if response is None:
        return
    final_url = response.http_response.url.strip("/") + "/"
    logger.info(f"URL '{final_url}' successfully verified")
    return final_url


async def process_sources(
        url_list, loop, get_visited_links_function, add_article_function, **request_kwargs):
    async with create_client(loop=loop) as client:
        results = [
            add_callback(url, client, get_visited_links_function,
                         add_article_function, loop, **request_kwargs) for url in url_list
        ]
        return await asyncio.gather(*results, loop=loop)


def scrap(urls, get_visited_links_function, add_article_function, request_kwargs=None):
    """
    Scrap a collection of magazines URLs and extract new articles for each one of them
    Args:
        urls: List of URLs to be scraped
        get_visited_links_function: Callable or API URL that accepts only one URL and returns its already visited links
                                    Could be an which accepts a get request with
        add_article_function: Callable that accepts a dictionary with an article information (at least 'source' and 'url' keys)
        request_kwargs: Dictionary with the common options available for a http_requests.async_request function

    Returns: None

    """
    loop = get_valid_loop()

    request_kwargs = request_kwargs or dict()

    if not all([callable(func) for func in
                (get_visited_links_function, add_article_function)]):
        msg = "For scraping process, you need to specify two callable objects"
        logger.error(msg)
        raise AttributeError(msg)

    if 'proxy' in request_kwargs:
        request_kwargs['proxy'] = format_proxy(request_kwargs['proxy'])
    if 'logger' not in request_kwargs:
        request_kwargs['logger'] = logger

    loop.run_until_complete(
        process_sources(
            urls, loop, get_visited_links_function, add_article_function, **request_kwargs))


def source_current_state(url, proxy):
    response = sync_request(url=url, method='get', proxy_cfg=format_proxy(proxy), kwargs={"logger": logger})
    if response is None:
        return
    logger.info(f"URL '{url}' successfully verified")
    html = response.text
    real_url = response.http_response.url.strip("/") + "/"

    magazine = newspaper.build(real_url, dry=True, config=construct_config(proxy))
    magazine.html = html
    magazine.parse()

    magazine.set_categories()

    for cat in magazine.categories:
        if cat.url[-1] != "/":
            cat.url += "/"
    if real_url not in [c.url for c in magazine.categories]:
        magazine.categories.append(Category(url=real_url))
    magazine.download_categories()
    magazine.parse_categories()
    # magazine.generate_articles()
    articles_urls = list(set(categories_to_articles(magazine)))
    logger.info(f"{len(articles_urls)} new articles to be added for source {url}")
    return url, articles_urls


# source_url, articles_list = await _define_magazine(url, client, get_visited_links_function, loop, **request_kwargs)
# await _process_articles(source_url, articles_list, client, set_visited_links_function, add_article_function, loop,
#                         **request_kwargs)
