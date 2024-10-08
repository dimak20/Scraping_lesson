import csv
import logging
import sys
from dataclasses import dataclass, fields, astuple
from typing import List
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

BASE_URL = "https://webscraper.io/"
HOME_URL = urljoin(BASE_URL, "test-sites/e-commerce/allinone")


PRODUCTS_OUTPUT_CSV_PATH = "products.csv"


@dataclass
class Product:
    title: str
    description: str
    price: float
    rating: int
    num_of_reviews: int
    additional_info: dict

PRODUCT_FIELDS = [field.name for field in fields(Product)]

_driver: WebDriver | None = None

def get_driver() -> WebDriver:
    return _driver

def set_driver(new_driver: WebDriver):
    global _driver
    _driver = new_driver

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)8s]: %(message)s",
    handlers=[
        logging.FileHandler("parser.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


def parse_hdd_block_prices(product_soup: BeautifulSoup) -> dict[str, float]:
    # get detailed_url
    # Driver get this page
    # Driver find swatches
    # Driver for each button -> button click (if clickable) -> get price
    detailed_url = urljoin(BASE_URL, product_soup.select_one(".title")["href"])
    driver = get_driver() #bad practice
    driver.get(detailed_url)
    dropdowns = driver.find_element(By.CSS_SELECTOR, "select[aria-label='color']")
    items = dropdowns.find_elements(By.CSS_SELECTOR, "option.dropdown-item")

    prices = {}


    for item in items:
        if not item.get_property("disabled"):
            item.click()
            prices[item.get_property("value")] = float(driver.find_element(
                By.CLASS_NAME, "price"
            ).text.replace("$", ""))

    return prices


# [attr for attr in dir(obj)]

def parse_single_product(product_soup: BeautifulSoup) -> Product:
    hdd_prices = parse_hdd_block_prices(product_soup)
    return (Product(
        title=product_soup.select_one("a.title")["title"],
        description=product_soup.select_one(".description").text,
        price=float(product_soup.select_one(".price").text.replace("$", "")),
        rating=int(product_soup.select_one("p[data-rating]")["data-rating"]),
        num_of_reviews=int(product_soup.select_one(
            "div.ratings > .review-count"
        ).text.split()[0]),
        additional_info={"hdd_prices": hdd_prices}
    ))


def get_num_pages(page_soup: BeautifulSoup) -> int:
    pagination = page_soup.select_one(".pagination")

    if pagination is None:
        return 1

    return int(pagination.select("li")[-2].text)


def get_single_page_products(page_soup: BeautifulSoup) -> list[Product]:
    products = page_soup.select(".thumbnail")

    return [parse_single_product(product_soup) for product_soup in products]


def get_home_products() -> List[Product]:
    logging.info(f"Start parsing laptops")
    page = requests.get(HOME_URL).content
    first_page_soup = BeautifulSoup(page, "html.parser")

    # get nums of pages
    num_pages = get_num_pages(first_page_soup)

    all_products = get_single_page_products(first_page_soup)

    # iterate on pages & get all products from single page
    for page_num in range(2, num_pages + 1):
        logging.info(f"Start parsing page #{page_num}")
        page = requests.get(HOME_URL, {"page": page_num}).content
        soup = BeautifulSoup(page, "html.parser")
        all_products.extend(get_single_page_products(soup))

    return all_products


def write_products_to_csv(products: list[Product]) -> None:
    with open(PRODUCTS_OUTPUT_CSV_PATH, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(PRODUCT_FIELDS)
        writer.writerows([astuple(product) for product in products])


def main():
    with webdriver.Chrome() as new_driver:
        set_driver(new_driver)
        products = get_home_products()
        # write_products_to_csv(products)


if __name__ == '__main__':
    main()
