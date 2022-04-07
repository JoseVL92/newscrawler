import os
import sys

from .webcrawler import scrap, find_redirection_url

# from .config import setup_crawlers


if __name__ == "__main__":
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if ROOT not in sys.path:
        sys.path.append(ROOT)
