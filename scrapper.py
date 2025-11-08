import json
import time
import requests

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from typing import List

from bs4 import PageElement, BeautifulSoup


THREAD_POOL_WORKERS = 32
DUMP_FILE_NAME = "books_data.txt"


@dataclass
class BookData:
    name: str
    description: str | None
    upc: str
    product_type: str
    price_excl_tax: str
    price_incl_tax: str
    tax: str
    rating: int
    availablility: str
    availability_number: int
    reviews: int


def scrape_books(is_save: bool) -> List[BookData]:
    """
    Парсим все книжки с books.toscrape.com.
    """
    pages_number = get_pages_number()
    book_urls = get_all_book_urls(pages_number)

    with ThreadPoolExecutor(max_workers=THREAD_POOL_WORKERS) as executor:
        books_data = list(executor.map(get_book_data, book_urls))

    if is_save:
        with open(DUMP_FILE_NAME, "+w") as file:
            json.dump(
                [asdict(b) for b in books_data], file, ensure_ascii=False, indent=4
            )

    return books_data


def get_pages_number():
    """
    Получение количества страниц в каталоге.
    """
    url = get_page_url(1)
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"Failed get request to {url}")

    soup = BeautifulSoup(response.text, "html.parser")
    parts = soup.find("li", class_="current").text.split()
    return int(parts[-1])


def get_all_book_urls(pages_number):
    """
    Собираем список всех ссылок на страницы с книжками.
    pages_number - общее количество страниц.
    """
    all_book_urls = []
    with ThreadPoolExecutor(max_workers=THREAD_POOL_WORKERS) as executor:
        page_numbers = [i for i in range(1, pages_number + 1)]
        book_urls = list(executor.map(get_book_urls_from_page, page_numbers))

    for urls in book_urls:
        all_book_urls.extend(urls)

    return all_book_urls


def get_book_urls_from_page(page_number) -> List[str]:
    """
    Получение списка урлов на все книжки со страници с номером page_number.
    """
    page_url = get_page_url(page_number)
    response = requests.get(page_url)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed get request to {page_url} with number {page_number}"
        )

    products_href = parse_products_href_in_html(html=response.text)
    return [get_book_url(href) for href in products_href]


def parse_products_href_in_html(html: str) -> List[str]:
    """
    Парсит ссылки на продукты из html отдельной страницы с продуктами из каталога.
    """
    soup = BeautifulSoup(html, "html.parser")
    li_tags = soup.find("ol", class_="row").find_all(
        "li", class_="col-xs-6 col-sm-4 col-md-3 col-lg-3"
    )
    hrefs = []
    for li in li_tags:
        a_tag = li.find("h3").find("a")
        href = a_tag.get("href")
        hrefs.append(href)
    return hrefs


def get_page_url(page_number: int) -> str:
    return f"http://books.toscrape.com/catalogue/page-{page_number}.html"


def get_book_url(book_href: str) -> str:
    return f"https://books.toscrape.com/catalogue/{book_href}"


def get_book_data(book_url: str) -> BookData:
    """
    Получение данных о книге с одной страницы.
    book_url - ссылка на web страницу с книгой.
    """
    response = requests.get(book_url)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed get request to {book_url} with status {response.status_code}"
        )

    try:
        book_data = parse_book_data(response.text)
    except Exception as ex:
        print(f"Failed to parse book with url {book_url}")
        raise ex

    return book_data


def parse_book_data(html: str) -> BookData:
    soup = BeautifulSoup(html, "html.parser")

    product_info_table = soup.find("table", class_="table table-striped")
    product_info = parse_product_info_table(product_info_table)

    upc = product_info["UPC"]
    tax = product_info["Tax"]
    availability = product_info["Availability"]
    availability_number = int(availability.split("(")[1].split()[0])
    reviews = int(product_info["Number of reviews"])
    product_type = product_info["Product Type"]
    price_excl_tax = product_info["Price (excl. tax)"]
    price_incl_tax = product_info["Price (incl. tax)"]

    product_page_article = soup.find("article", class_="product_page")
    description_p = product_page_article.find("p", recursive=False)
    description_text = description_p.text if description_p else None

    product_main_div = soup.find("div", class_="product_main")
    name = product_main_div.find("h1").text
    rating_p = product_main_div.find("p", class_="star-rating")
    rating = parse_rating(rating_p)

    return BookData(
        name=name,
        description=description_text,
        upc=upc,
        product_type=product_type,
        tax=tax,
        price_excl_tax=price_excl_tax,
        price_incl_tax=price_incl_tax,
        rating=rating,
        availablility=availability,
        availability_number=availability_number,
        reviews=reviews,
    )


def parse_rating(element: PageElement) -> int | None:
    """
    Парсим рейтинг из product_main div.
    """

    class_to_rating_map = {
        "Zero": 0,
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5,
    }

    classes = element.get("class", [])
    for class_name, value in class_to_rating_map.items():
        if class_name in classes:
            return value

    return None


def parse_product_info_table(table: PageElement) -> dict:
    return {item.find("th").text: item.find("td").text for item in table.find_all("tr")}


def parse_products_href_in_html(html: str) -> List[str]:
    """
    Парсит ссылки на продукты из html отдельной страницы с продуктами из каталога.
    """
    soup = BeautifulSoup(html, "html.parser")
    li_tags = soup.find("ol", class_="row").find_all(
        "li", class_="col-xs-6 col-sm-4 col-md-3 col-lg-3"
    )
    hrefs = []
    for li in li_tags:
        a_tag = li.find("h3").find("a")
        href = a_tag.get("href")
        hrefs.append(href)
    return hrefs


if __name__ == "__main__":
    print("Start books data collecting")
    start_time = time.time()
    books_data = scrape_books(is_save=True)
    end_time = time.time()

    print(
        f"Successfully collected {len(books_data)} books by {end_time - start_time:.2f} seconds"
    )
