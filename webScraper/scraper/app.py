import time

import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from flask_cors import CORS
from pyvirtualdisplay import Display
import colorama
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from dbpipeline import WebscrapeMysqlPipeline
import psutil
from urllib.parse import urlencode
from colorama import Fore
from flask import Flask, request, Response, jsonify
from prometheus_client import generate_latest, Counter, REGISTRY
from selenium.webdriver.common.action_chains import ActionChains

app = Flask(__name__)
CORS(app, resources={r"/scraper/*": {"origins": "*"}})

# Define your metrics
REQUESTS = Counter('hello_worlds_total', 'Hello Worlds requested.')


@app.route('/scraper/hello')
def hello():
    REQUESTS.inc()  # increment counter
    return "Hello World!"


@app.route('/scraper/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(REGISTRY), mimetype='text/plain')


@app.route("/scraper/scrape", methods=["POST"])
def scrape_api():
    print(request.get_json())
    data = request.get_json()
    city = data.get("city")
    date = data.get("date")
    nights = data.get("nights")
    guests = data.get("guests")
    rooms = data.get("rooms")
    accommodation = data.get("accommodation")

    scrape_hotels(city, date, nights, guests, rooms, accommodation)

    return jsonify({"message": "Scrape completed"})


options = {
    'verify_ssl': False
}

selectors = {
    'name': 'div[data-testid="title"]',
    'link': 'a[data-testid="title-link"]',
    'price': 'span[data-testid="price-and-discounted-price"]',
    'address': '[data-testid="address"]',
    'image': '[data-testid="image"]',
    'score': 'div[data-testid="review-score"] > div',
    'review': 'div[data-testid="review-score"] > div > div',
    'reviewCount': 'div[data-testid="review-score"] > div > div:last-child',

    'configuration': 'div[data-testid="property-card-unit-configuration"]:last-child',
    'location': 'a[data-testid="secondary-review-score-link"]',
    'distance': '[data-testid="distance"]',

    'rating_squares': 'div[data-testid="rating-squares"]',
    'rating_points': 'div[data-testid="rating-stars"]',
}

parameters = {
    'ss': 'Vienna',
    'lang': 'en-gb',
    'src_elem': 'sb',
    'checkin': '2023-06-23',
    'checkout': '2023-06-24',
    'group_adults': '2',
    'group_children': '0',
    'no_rooms': '1',
    'sb_travel_purpose': 'leisure',
    'nflt': 'ht_id%3D201',
}


def extract_property_data(property_element, is_known):
    property_data = {
        'name': '',
        'address': '',

        'link': '',
        'image': '',

        'price': '',

        'score': '',
        'review': '',
        'reviewCount': '',

        'checkin': parameters['checkin'],
        'checkout': parameters['checkout'],

        'group_adults': '2',
        'group_children': '0',

        'configuration': '',
        'square_meters': '',

        'location': '',
        'distance': '',

        'rating_squares': 0,
        'rating_points': 0,
    }

    try:
        property_data['name'] = property_element.find_element(By.CSS_SELECTOR, selectors['name']).text
    except NoSuchElementException:
        property_data['name'] = ''
    except StaleElementReferenceException:
        pass

    try:
        price_element = property_element.find_element(By.CSS_SELECTOR, selectors['price'])
        property_data['price'] = price_element.get_attribute("innerHTML").split(';', 1)[1]
    except NoSuchElementException:
        property_data['price'] = ''
    except StaleElementReferenceException:
        pass

    score_element = None
    try:
        score_element = property_element.find_element(By.CSS_SELECTOR, selectors['score'])
        property_data['score'] = score_element.text
    except NoSuchElementException:
        property_data['score'] = ''
    except StaleElementReferenceException:
        pass

    if score_element is not None:
        try:
            review_element = property_element.find_element(By.CSS_SELECTOR, selectors['review'])
            property_data['review'] = review_element.text
        except NoSuchElementException:
            property_data['review'] = ''
        except StaleElementReferenceException:
            pass

        try:
            review_count_element = property_element.find_element(By.CSS_SELECTOR, selectors['reviewCount'])
            property_data['reviewCount'] = review_count_element.text.split(' ', 1)[0]
        except NoSuchElementException:
            property_data['reviewCount'] = ''
        except StaleElementReferenceException:
            pass

    # if already existing in the database then only the necessary
    # data will be searched for, saves a LOT of time
    if is_known:
        return property_data

    found_element = False

    try:
        rating_squares_element = property_element.find_element(By.CSS_SELECTOR, selectors['rating_squares'])
        if rating_squares_element is not None:
            property_data['rating_squares'] = len(rating_squares_element.find_elements(By.TAG_NAME, 'span'))
            found_element = True
        else:
            property_data['rating_squares'] = 0
    except NoSuchElementException:
        property_data['rating_squares'] = 0
    except StaleElementReferenceException:
        pass

    if not found_element:
        try:
            rating_squares_element = property_element.find_element(By.CSS_SELECTOR, selectors['rating_points'])
            if rating_squares_element is not None:
                property_data['rating_points'] = len(rating_squares_element.find_elements(By.TAG_NAME, 'span'))
            else:
                property_data['rating_points'] = 0
        except NoSuchElementException:
            property_data['rating_points'] = 0
        except StaleElementReferenceException:
            pass

    try:
        property_data['distance'] = property_element.find_element(By.CSS_SELECTOR, selectors['distance']).text
    except NoSuchElementException:
        property_data['distance'] = ''
    except StaleElementReferenceException:
        pass

    try:
        secondary_review_element = property_element.find_element(
            By.CSS_SELECTOR, selectors['location'])
        property_data['location'] = secondary_review_element.get_attribute('aria-label')
    except NoSuchElementException:
        property_data['location'] = ''
    except StaleElementReferenceException:
        pass

    try:
        configuration_text = property_element.find_element(By.CSS_SELECTOR, selectors['configuration']).text
        property_data['configuration'] = configuration_text

        if 'm²' in configuration_text:  # check if 'm²' is in the configuration_text
            for part in configuration_text.split():  # split the text by spaces
                if 'm²' in part:  # find the part with 'm²'
                    property_data['square_meters'] = int(
                        part.replace('m²', ''))  # remove 'm²' and convert the number to an integer
                    break
        else:
            property_data['square_meters'] = None  # if 'm²' is not found in the configuration_text

    except NoSuchElementException:
        property_data['configuration'] = ''
        property_data['square_meters'] = None
    except StaleElementReferenceException:
        pass

    try:
        property_data['link'] = property_element.find_element(By.CSS_SELECTOR, selectors['link']).get_attribute('href')
    except NoSuchElementException:
        property_data['link'] = ''
    except StaleElementReferenceException:
        pass

    try:
        address_element = property_element.find_element(By.CSS_SELECTOR, selectors['address'])
        property_data['address'] = address_element.text
    except NoSuchElementException:
        property_data['address'] = ''
    except StaleElementReferenceException:
        pass

    try:
        property_data['image'] = property_element.find_element(By.CSS_SELECTOR, selectors['image']).get_attribute('src')
    except NoSuchElementException:
        property_data['image'] = ''
    except StaleElementReferenceException:
        pass

    return property_data


def extract_properties(driver, dbpl):
    property_cards = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="property-card"]')
    print(f"       Found {len(property_cards)} property cards on the current page")  # Debugging print
    print(f"        **values below do not represent the data                   \n")
    properties = []

    for property_element in property_cards:
        property_name = property_element.find_element(By.CSS_SELECTOR, selectors['name']).text
        is_known = dbpl.check_hotels_in_db(property_name)
        property_data = extract_property_data(property_element, is_known=is_known)
        properties.append(property_data)
        status = dbpl.process_item(property_data)

        colorama.init()

        if status == 'duplicate':
            status_color = Fore.YELLOW  # Set the color to orange
        elif status == 'new':
            status_color = Fore.GREEN  # Set the color to green
        else:
            status_color = Fore.RESET  # Reset color to default

        print(f"{status_color}{status}{Fore.RESET}: {property_data['name']} ...")

        colorama.deinit()

    return properties


def build_url_template(base_url, params):
    try:
        url = base_url + urlencode(params)
    except Exception as e:
        print(f"Error constructing URL: {e}")
        url = base_url
    return url


# Function to monitor CPU and memory usage
def monitor_performance():
    cpu_percent = psutil.Process().cpu_percent(interval=1)
    memory_usage = psutil.Process().memory_percent()
    print(f"    cpu usage: {cpu_percent}%")
    print(f"    memory usage: {memory_usage}%\n")


def wait_and_find(driver, css_selector, timeout=None):
    if timeout is not None:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector))
            )
        except TimeoutException as e:
            print(f"Error: {e}")
            return None
    else:
        try:
            return driver.find_element(By.CSS_SELECTOR, css_selector)
        except NoSuchElementException as e:
            print(f"Error: {e}")
            return None


def intercept_request(requestS):
    if requestS.path.endswith('.jpg') or requestS.path.endswith('.png') or requestS.path.endswith('.gif'):
        requestS.abort()  # Abort the request for images


def configure_webdriver():
    optionsW = webdriver.ChromeOptions()
    optionsW.add_argument('--no-sandbox')
    optionsW.add_argument('--disable-gpu')
    optionsW.add_argument('--disable-dev-shm-usage')
    optionsW.add_argument('--blink-settings=imagesEnabled=false')
    optionsW.add_argument('--start-maximized')

    return optionsW


def scrape_hotels(city, date, nights, guests, rooms, accommodations, driver=None):
    parameters['ss'] = city
    parameters['checkin'] = date
    parameters['checkout'] = (datetime.strptime(date, "%Y-%m-%d") + timedelta(nights)).strftime("%Y-%m-%d")
    parameters['group_adults'] = guests
    parameters['group_children'] = 0
    parameters['no_rooms'] = rooms

    print(parameters)

    dbpl = WebscrapeMysqlPipeline()
    optionsW = configure_webdriver()
    display = None

    try:
        base_url = "https://www.booking.com/searchresults.en-gb.html?"
        url_template = build_url_template(base_url, parameters)

        if not driver:
            display = Display(visible=False, size=(1920, 1080))
            display.start()

            driver = webdriver.Chrome(service=Service('/usr/local/bin/chromedriver'), options=optionsW)

        # Add the request interceptor to the webdriver
        driver.request_interceptor = intercept_request

        driver.get(url_template)
        driver.implicitly_wait(5)

        total_pages = int(wait_and_find(driver, 'div[data-testid="pagination"] li:last-child').text)

        for current_page in range(total_pages):
            driver.implicitly_wait(5)
            driver.get(url_template)

            print(f"\n                   Page: {current_page + 1}/{total_pages}")
            print("#******************************************************#\n")
            monitor_performance()

            try:
                wait_and_find(driver, 'div[data-testid="property-card"]', 20)
                extract_properties(driver, dbpl)
                del driver.requests

                try:
                    banner_element = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'button[id="onetrust-accept-btn-handler"]'))
                    )
                    if banner_element.is_displayed():
                        # Scroll to the button
                        ActionChains(driver).move_to_element(banner_element).perform()

                        banner_element.click()
                except (NoSuchElementException, TimeoutException):
                    print("**one-trust banner not found or not clickable")

                if current_page < total_pages - 2:  # No need to click "Next" on the last page
                    # Wait for the "Next" button to become clickable

                    try:
                        next_button = WebDriverWait(driver, 25).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Next page"]'))
                        )

                        # Scroll to the button
                        ActionChains(driver).move_to_element(next_button).perform()

                        next_button.click()  # Click the "Next" button
                        url_template = driver.current_url
                    except (NoSuchElementException, TimeoutException, Exception) as e:
                        print(f'Error on page {current_page + 1} with the "Next button": {e}')
                        print(driver.page_source)

                        # Retry clicking the next button
                        time.sleep(2)  # wait for 2 seconds before retrying
                        scrape_hotels(city, date, nights, guests, rooms, accommodations, driver)  # recursive call

            except (NoSuchElementException, TimeoutException) as e:
                print(f"Error on page {current_page + 1}: {e}")  # Debugging print
                pass

    finally:
        if not driver:
            if driver:
                driver.quit()
                display.stop()


def wait_for_db():
    while True:
        try:
            connection = mysql.connector.connect(
                host='db',
                user='root',
                password='root'
            )

            if connection.is_connected():
                print('Connected to MySQL server')
                connection.close()
                break

        except Error as e:
            print("Error while connecting to MySQL", e)
            print("Retrying in 5 seconds...")
            time.sleep(5)


if __name__ == '__main__':
    wait_for_db()
    app.run(host='0.0.0.0', port=8080)
