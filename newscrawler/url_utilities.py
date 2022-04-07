# -*- coding: utf-8 -*-
"""
Newspaper treats urls for news articles as critical components.
Hence, we have an entire module dedicated to them.
"""
__title__ = 'newspaper'
__author__ = 'Lucas Ou-Yang'
__license__ = 'MIT'
__copyright__ = 'Copyright 2014, Lucas Ou-Yang'

# import os
import re

from urllib.parse import urlparse, urldefrag

# tldextract_cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public_suffix_list.dat")
# os.environ["TLDEXTRACT_CACHE"] = tldextract_cache_file

from tldextract import tldextract

_STRICT_DATE_REGEX_PREFIX = r'(?<=\W)'
DATE_REGEX = r'([\./\-_]{0,1}(19|20)\d{2})[\./\-_]{0,1}(([0-3]{0,1}[0-9][\./\-_])|(\w{3,5}[\./\-_]))([0-3]{0,1}[0-9][\./\-]{0,1})?'
STRICT_DATE_REGEX = _STRICT_DATE_REGEX_PREFIX + DATE_REGEX

ALLOWED_TYPES = ['html', 'htm', 'md', 'rst', 'aspx', 'jsp', 'rhtml', 'cgi',
                 'xhtml', 'jhtml', 'asp', 'shtml']

GOOD_PATHS = ['story', 'article', 'feature', 'featured', 'slides', 'news', 'v', 'press']

BAD_CHUNKS = ['careers', 'contact', 'contacto', 'about', 'faq', 'terms', 'privacy',
              'advert', 'preferences', 'preferencias', 'feedback', 'info', 'browse', 'howto',
              'account', 'subscribe', 'donate', 'shop', 'admin', 'user', 'usuario', 'login', 'logout',
              'media', 'audio', 'video', 'videos', 'gallery', 'galeria', 'powerpoint']

BAD_DOMAINS = ['amazon', 'doubleclick', 'twitter', 'facebook', 'youtube']


def valid_url(url, is_article=True, parent_url=None, verbose=False, same_domain=False, mag_categories=None):
    """
    Is this URL a valid news-article url?

    """
    if url == "":
        return False

    r1 = ('mailto:' in url)  # TODO not sure if these rules are redundant
    r2 = ('http://' not in url) and ('https://' not in url)

    if r1:
        if verbose: print('\t%s rejected because len of url structure' % url)
        return False
    if r2:
        if parent_url and '//' not in url:
            if url[0] == "/":
                original_source_schema = urlparse(parent_url).scheme
                original_source_netloc = urlparse(parent_url).netloc
                url = original_source_schema + "://" + original_source_netloc + url
            else:
                prefix = parent_url if parent_url[-1] == "/" else parent_url + "/"
                url = prefix + url
        else:
            if verbose: print('\t%s rejected because len of url structure' % url)
            return False

    # 11 chars is shortest valid url length, eg: http://x.co
    if url is None or len(url) < 11:
        if verbose: print('\t%s rejected because len of url is less than 11' % url)
        return False

    if "javascript:void" in url:
        return False

    # Encode strange characters:
    # url_strange_characters = {
    #     " ": "%20",
    #     "!": "%21",
    #     "#": "%23",
    #     "$": "%24",
    #     "&": "%26",
    #     "'": "%27",
    #     "(": "%28",
    #     ")": "%29",
    #     "*": "%2A",
    #     "+": "%2B",
    #     ",": "%2C",
    #     "/": "%2F",
    #     ":": "%3A",
    #     ";": "%3B",
    #     "=": "%3D",
    #     "?": "%3F",
    #     "@": "%40",
    #     "[": "%5B",
    #     "]": "%5D"
    # }
    # for character, encoded in url_strange_characters.items():
    #     url = url.replace(character, encoded)

    url.replace("'", "")
    # while "'" in url:
    #     index = url.find("'")
    #     url = url[:index] + url[index + 1:]

    # eliminate fragments from url
    url = urldefrag(url)[0]

    path = urlparse(url).path

    # input url is not in valid form (scheme, netloc, tld)
    if not path.startswith('/'):
        return False

    # the '/' which may exist at the end of the url provides us no information
    if path.endswith('/'):
        path = path[:-1]

    # '/story/cnn/blahblah/index.html' --> ['story', 'cnn', 'blahblah', 'index.html']
    path_chunks = [x for x in path.split('/') if len(x) > 0]

    # siphon out the file type. eg: .html, .htm, .md
    if len(path_chunks) > 0:
        file_type = url_to_filetype(url)

        # if the file type is a media type, reject instantly
        if file_type and file_type not in ALLOWED_TYPES:
            if verbose: print('\t%s rejected due to bad filetype' % url)
            return False

        last_chunk = path_chunks[-1].split('.')
        # the file type is not of use to use anymore, remove from url
        if len(last_chunk) > 1:
            path_chunks[-1] = last_chunk[-2]

    if same_domain:
        src_tld = tldextract.extract(parent_url)
        art_tld = tldextract.extract(url)
        if not art_tld.domain == src_tld.domain or not art_tld.suffix == src_tld.suffix:
            if verbose: print('\t%s rejected due to different domain' % url)
            return False

    if is_article:

        # Index gives us no information
        if 'index' in path_chunks:
            path_chunks.remove('index')

        # extract the tld (top level domain)
        tld_dat = tldextract.extract(url)
        subd = tld_dat.subdomain
        tld = tld_dat.domain.lower()

        url_slug = path_chunks[-1] if path_chunks else ''

        if tld in BAD_DOMAINS:
            if verbose: print('%s caught for a bad tld' % url)
            return False

        if len(path_chunks) == 0:
            dash_count, underscore_count = 0, 0
        else:
            dash_count = url_slug.count('-')
            underscore_count = url_slug.count('_')

        # If the url has a news slug title
        if url_slug and (dash_count > 4 or underscore_count > 4):

            if dash_count >= underscore_count:
                if tld not in [x.lower() for x in url_slug.split('-')]:
                    if verbose: print('%s verified for being a slug' % url)
                    return url

            if underscore_count > dash_count:
                if tld not in [x.lower() for x in url_slug.split('_')]:
                    if verbose: print('%s verified for being a slug' % url)
                    return url

        # There must be at least 2 subpaths
        if len(path_chunks) <= 1:
            if verbose: print('%s caught for path chunks too small' % url)
            return False

        # Check for subdomain & path red flags
        # Eg: http://cnn.com/careers.html or careers.cnn.com --> BAD
        for b in BAD_CHUNKS:
            if b in path_chunks or b == subd:
                if verbose: print('%s caught for bad chunks' % url)
                return False

        match_date = re.search(DATE_REGEX, url)

        # if we caught the verified date above, it's an article
        if match_date is not None:
            if verbose: print('%s verified for date' % url)
            return url

        for GOOD in GOOD_PATHS:
            if GOOD.lower() in [p.lower() for p in path_chunks]:
                if verbose: print('%s verified for good path' % url)
                return url

        if mag_categories:
            url_with_final_slash = url.strip("/") + "/"
            if url_with_final_slash in [cat.url for cat in mag_categories]:
                if verbose: print('%s caught for be a category' % url)
                return False

        # if verbose: print('%s caught for default false' % url)
        # return False

    if verbose: print('%s verified for default true' % url)
    return url


def url_to_filetype(abs_url):
    """
    Input a URL and output the filetype of the file
    specified by the url. Returns None for no filetype.
    'http://blahblah/images/car.jpg' -> 'jpg'
    'http://yahoo.com'               -> None
    """
    path = urlparse(abs_url).path
    # Eliminate the trailing '/', we are extracting the file
    if path.endswith('/'):
        path = path[:-1]
    path_chunks = [x for x in path.split('/') if len(x) > 0]
    last_chunk = path_chunks[-1].split('.')  # last chunk == file usually
    if len(last_chunk) < 2:
        return None
    file_type = last_chunk[-1]
    # Assume that file extension is maximum 5 characters long
    if len(file_type) <= 5 or file_type.lower() in ALLOWED_TYPES:
        return file_type.lower()
    return None


def filter_articles(source_url, art_urls, get_visited_links_function, include_not_articles=True, new_links_only=True, same_domain=True):
    try:
        lastate = get_visited_links_function(source_url)
        if lastate is None:
            lastate = set()
    except Exception as err:
        raise Exception("\nXSA..........Error getting visited links for {0}: ".format(source_url) + str(err) + "\n")
    # curr_art = set(art_urls).difference(lastate)

    if not include_not_articles:
        lastate = [l for l in lastate if valid_url(l, is_article=True, parent_url=source_url)]

    if new_links_only:
        art_urls = [art for art in art_urls if art not in lastate]

    if same_domain:
        filtered = []
        src_tld = tldextract.extract(source_url)
        for art in art_urls:
            art_tld = tldextract.extract(art)
            if art_tld.domain == src_tld.domain and art_tld.suffix == src_tld.suffix:
                filtered.append(art)
        art_urls = filtered

    return list(set(art_urls))


if __name__ == '__main__':
    print(valid_url(
        "http://stm.sciencemag.org/content/11/483/eaau1428",
        verbose=False,
        is_article=True
    ))
    print(valid_url(
        '/content/11/483/eaau6753.full.pdf',
        parent_url="http://stm.sciencemag.org/",
        verbose=False,
        is_article=True
    ))
    print(valid_url(
        '/content/11/483/eaau6753',
        parent_url="http://stm.sciencemag.org/",
        verbose=False,
        is_article=True
    ))
    print(valid_url(
        'http://www.sciencemag.org/authors/science-translational-medicine',
        parent_url="http://stm.sciencemag.org/",
        verbose=False,
        is_article=True
    ))
