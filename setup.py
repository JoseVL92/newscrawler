from setuptools import setup, find_packages

setup(
    name="newscrawler",
    version=0.1,
    author="Jose Alberto Varona Labrada",
    author_email="jovalab92@gmail.com",
    description="News site monitoring library",
    python_requires=">=3.6",
    url="https://github.com/JoseVL92/newscrawler",
    download_url="https://github.com/JoseVL92/newscrawler/archive/refs/tags/v0.1.tar.gz",
    packages=find_packages(),
    data_files=[
        ("", ["LICENSE.txt", "README.md"])
    ],
    install_requires=['newspaper3k', 'pytz', 'http_requests'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    license='MIT',
    keywords=['http', 'webscraping', 'request', 'asyncronous']
)
