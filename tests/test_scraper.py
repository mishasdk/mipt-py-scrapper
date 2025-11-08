import os
import bs4

from scrapper import parse_book_data, parse_rating, parse_products_href_in_html

current_dir = os.path.dirname(os.path.abspath(__file__))

def test_parse_book_data():
    file_path = os.path.join(current_dir, "assets", "test_crown_of_midnight.html")
    with open(file_path) as file:
        html = file.read()

    book_data = parse_book_data(html)

    assert book_data.name == "Crown of Midnight (Throne of Glass #2)"
    assert len(book_data.description) == 1526 
    assert book_data.upc == "7267864328ae8b9d"
    assert book_data.product_type == "Books"
    assert book_data.price_excl_tax == "£43.29"
    assert book_data.price_excl_tax == "£43.29"
    assert book_data.tax == "£0.00"
    assert book_data.availablility == "In stock (16 available)"
    assert book_data.availability_number == 16
    assert book_data.reviews == 0


def test_parse_rating():
    assert parse_rating(_soup_with_rating("One")) == 1
    assert parse_rating(_soup_with_rating("Two")) == 2
    assert parse_rating(_soup_with_rating("Three")) == 3
    assert parse_rating(_soup_with_rating("Four")) == 4
    assert parse_rating(_soup_with_rating("Five")) == 5

    assert parse_rating(_empty_element()) is None
    assert parse_rating(_soup_with_rating("abacaba")) is None


def test_products_hrefs_parser():
    file_path = os.path.join(current_dir, "assets", "page_1.html")
    with open(file_path) as file:
        html = file.read()

    hrefs = parse_products_href_in_html(html)

    print(hrefs)
    assert len(hrefs) == 20
    assert "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html" in hrefs


def _soup_with_rating(rating_name):
    html = f'<p class="star-rating {rating_name}">'
    soup = bs4.BeautifulSoup(html, "html.parser")
    return soup.find("p", class_="star-rating")


def _empty_element():
    html = f'<div></div>'
    return bs4.BeautifulSoup(html, "html.parser")
