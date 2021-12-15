#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Sungmin Oh <smoh2044@gmail.com>
#
# Distributed under terms of the MIT license.

"""

"""
from functools import lru_cache
from concurrent import futures
from importlib.resources import contents
from bs4 import BeautifulSoup
from bs4.element import Tag
import requests
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, splitquery
import webbrowser
import sys
import os
import json
import re
from selenium import webdriver
from dataclasses import dataclass


@dataclass
class Post:
    reviews: int
    rating: float
    yelp_link: str
    price: int
    title: str
    location: str
    link: str


class Apartment:
    headers = {
        'authority': 'www.apartments.com',
        'cache-control': 'max-age=0',
        'save-data': 'on',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.108 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9,ko;q=0.8',
        'cookie': '',
    }

    def __init__(self, url):
        self.url = url
        self._pages = None
        self.memo = {}

    @lru_cache(None)
    def soup(self, page=1):
        url = self.url
        if page != 1:
            url, query = splitquery(self.url)
            url = f'{os.path.join(url, str(page))}/?{query}'
            print(f'Getting page {page} from {url}')
        response = requests.get(url, headers=self.headers)
        return BeautifulSoup(response.text, 'html.parser')

    @property
    def pages(self):
        if not self._pages:
            # <span class="pageRange">Page 3 of 28</span>
            pattern = r'Page (\d+) of (\d)+'
            pages = self.soup(1).find_all('span', attrs={'class': 'pageRange'})
            if not pages:
                self._pages = [1, 1]
            else:
                match = re.search(pattern, pages[0].contents[0])
                if match:
                    self._pages = [int(x) for x in match.groups()]
                else:
                    self._pages = [1, 1]
        return self._pages

    def get_list(self, page=None):
        if page is not None:
            soup = self.soup(page)
            titles = []
            links = []
            for x in soup.find_all('div', 'property-information'):
                titles.append(x.find_all('span', 'js-placardTitle')[0].contents[0])
                links.append(x.find_all('a', 'property-link')[0].attrs['href'])
            prices = [x.contents[0].strip() for x in soup.find_all('p', 'property-pricing')]
            locations = [x.contents[0].strip() for x in soup.find_all('div', 'property-address')]
            return [Post(None, None, None, *args) for args in zip(prices, titles, locations, links)]
        pool = futures.ThreadPoolExecutor()
        results = [pool.submit(self.get_list, p) for p in range(self.pages[0], self.pages[1] + 1)]
        ret = []
        for r in results:
            ret.extend(r.result())
        return ret


class Yelp:
    my_location = [0, 0]
    base_url = 'https://www.yelp.com/search_suggest/v2/prefetch?lat={lat}&lng={lon}&is_new_loc=false&prefix={query}&is_initial_prefetch='
    headers = {
        'Host': 'www.yelp.com',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.59 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
        'Cookie': '',
    }

    def __init__(self, query):
        self.query = query
        self.url = self.base_url.format(lat=self.my_location[0], lon=self.my_location[1], query=quote(query))
        self.driver = webdriver.Chrome('/usr/local/bin/chromedriver')
        self._page_url = None
        self._review = [None, None]

    @property
    def page_url(self):
        if self._page_url is None:
            # print(f'Getting yelp url of {self.query!r} from {self.url}')
            self.driver.get(self.url)
            j = json.loads(self.driver.find_element_by_tag_name('pre').text)
            try:
                self._page_url = 'https://www.yelp.com' + j['response'][0]['suggestions'][0]['redirect_url']
            except:
                self._page_url = 'Not found'
            print(f'Yelp url of {self.query!r} >>> {self._page_url}')
        return self._page_url

    @property
    def review(self):
        if self._review[0] is None and self.page_url.startswith('http'):
            self.driver.get(self.page_url)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
            rating_pattern = r'"ratingValue":(?P<rating>\d*)'
            review_pattern = r'"reviewCount":(?P<review>\d*)'
            # pattern = r'"aggregateRating": {"reviewCount": (?P<count>\d*).*"AggregateRating", "ratingValue": (?P<rating>\d*)'
            rating = None
            n_reviews = None
            for script in scripts:
                for content in script.contents:
                    rating_match = re.search(rating_pattern, content)
                    if rating_match:
                        rating = rating_match.group(1)
                    review_match = re.search(review_pattern, content)
                    if review_match:
                        n_reviews = review_match.group(1)
            self._review = [n_reviews, rating]
        return self._review


def crawl(url):
    def _get_yelp_result(title):
        yelp = Yelp(title)
        return [*yelp.review, yelp.page_url]

    posts = Apartment(url).get_list()
    pool = futures.ThreadPoolExecutor()
    results = [pool.submit(_get_yelp_result, p.title) for p in posts]
    for ft, post in zip(results, posts):
        post.review, post.rating, post.yelp_link = ft.result()
    return posts


def to_html(posts):
    ret = ['<table style="width:100%">',
           '''
           <tr>
            <th>rating</th>
            <th>review</th>
            <th>price</th>
            <th>title</th>
            <th>location</th>
           </tr>
           ''']
    for post in posts:
        ret.append(f'''
                   <tr>
                   <td>{post.rating}</td>
                   <td><a href="{post.yelp_link}">{post.review}</a></td>
                   <td>{post.price}</td>
                   <td><a href="{post.link}">{post.title}</a></td>
                   <td>{post.location}</td>
                   <tr/>''')
    ret.append('</table>')
    return '\n'.join(ret)


if __name__ == '__main__':
    url = sys.argv[1]
    fname = sys.argv[2]
    with open(fname, 'w') as f:
        f.write(to_html(crawl(url)))
    webbrowser.open_new_tab('file://' + os.path.realpath(fname))
