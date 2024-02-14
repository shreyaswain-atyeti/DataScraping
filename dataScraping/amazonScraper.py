import gzip
import math
import re
import requests
from bs4 import BeautifulSoup
import json
import time
from concurrent.futures import ThreadPoolExecutor
import logging



logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

BANGALORE_PINCODE = '560001'
DELHI_PINCODE = '110001'

class AmazonScraper:
    def __init__(self, base_url="https://www.amazon.in", headers=None):
        self.base_url = base_url
        self.headers = headers or {
            # use different user agent if its giving 503 error
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        

# this function try response and if fail then retry it till successfull fatch response or max_retries
    def get_page_content_with_retry(self, url, max_retries=10, retry_delay=5):
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers)
                logger.info(response)
                if response.status_code == 200:
                    return response.content
                elif response.status_code == 503:
                    logger.warning(f"Service temporarily unavailable (503). Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to fetch data from {url}. Status code: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error: {e}")
                logger.warning(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)

        logger.error(f"Maximum retries reached. Failed to fetch data from {url}. Skipping...")
        return None

# this function will extract per page data
    def extract_link(self, pincode, max_pages):
        laptops = []
        sample_url = f"{self.base_url}/s?k=laptops&page=1&location={pincode}"

        with ThreadPoolExecutor(max_pages) as executor:
            results = list(executor.map(self._extract_page, [sample_url] * max_pages, range(1, max_pages + 1)))

        for result in results:
            laptops.extend(result)

        return laptops

# this will extract page 
    def _extract_page(self, sample_url, page_number):
        url = f"{self.base_url}/s?k=laptops&page={page_number}&location={sample_url}"
        page_content = self.get_page_content_with_retry(url)
        soup = BeautifulSoup(page_content, 'html.parser')

        page_laptops = []
        for laptop in soup.find_all('div', {'class': 'sg-col-20-of-24 s-result-item s-asin sg-col-0-of-12 sg-col-16-of-20 AdHolder sg-col s-widget-spacing-small sg-col-12-of-16'}):
            laptop_info = self.extract_laptop_info(laptop)
            if laptop_info:
                page_laptops.append(laptop_info)

        return page_laptops

# this function is for giving individual page content soup
    def extractIndividualLaptopInfo(self, individualUrl):
        url = f"{self.base_url}{individualUrl}"
        page_content = self.get_page_content_with_retry(url)
        soup = BeautifulSoup(page_content, 'html.parser')
        return soup

# this function will find table value from element
    def find_text(self, soup, keyword):
        row = soup.find('th', string=re.compile(keyword, re.I))
        if row:
            parent_tr = row.find_parent('tr')
            if parent_tr:
                td = parent_tr.find('td', class_='a-size-base prodDetAttrValue')
                if td:
                    return td.get_text(strip=True)
        return "Not available"



#this will give individual data for laptop
    def extract_laptop_info(self, laptop):
        
        if laptop:
            anchor_tag = laptop.find('a', {'class': 'a-link-normal s-no-outline'})
            url = anchor_tag['href'] if anchor_tag and 'href' in anchor_tag.attrs else None
            sku_element=soup.find('div',{'id':'imageBlock_feature_div','class':'celwidget'})
            sku=(sku_element.get('data-csa-c-asin')) if sku_element else None
            soup = self.extractIndividualLaptopInfo(url)
            brand_element = soup.find('span', {'class': 'a-size-base po-break-word'})
            productName_element = soup.find('tr', {'class': 'a-spacing-small po-model_name'}).find('span', {'class': 'a-size-base po-break-word'})
            productTitle_element = soup.find('span', {'id': 'productTitle'})
            sellingPrice_element = soup.find('span', {'class': 'a-price-whole'})
            mRP_element = soup.find('span', {'class': 'a-price a-text-price'})
            discount_element = soup.find('span', {'class': 'a-size-large a-color-price savingPriceOverride aok-align-center reinventPriceSavingsPercentageMargin savingsPercentage'})
            category_element = soup.find('img', {'class': 'nav-categ-image'})
            productImg_element = soup.find('img', {'id': 'landingImage'})
            description_element = soup.find('ul', {'class': 'a-unordered-list a-vertical a-spacing-mini'})

            # asin = self.find_text(soup, 'ASIN')
            processor = self.find_text(soup, 'Processor')
            weight = self.find_text(soup, 'Item\s*Weight')
            storage = self.find_text(soup, 'Hard\s*Drive\s*Size')
            display = self.find_text(soup, 'Resolution')
            graphics_ram = self.find_text(soup, 'Graphics\s*Card\s*Ram\s*Size')
            graphics = self.find_text(soup, 'Graphics\s*Coprocessor')
            ram = self.find_text(soup, 'RAM\s*Size')

            brand = brand_element.text.strip() if brand_element else "Not available"
            productName = productName_element.text.strip() if productName_element else "Not available"
            productTitle = productTitle_element.text.strip() if productTitle_element else "Not available"
            sellingPrice = sellingPrice_element.text.strip() if sellingPrice_element else "Not available"
            mRP = mRP_element.find('span', {'class':'a-offscreen'}).text.strip() if mRP_element else "Not available"
            discount = discount_element.text.strip() if discount_element else ""
            category = category_element['alt'] if category_element and 'alt' in category_element.attrs else "Not available"
            productImg = productImg_element['src'] if productImg_element and 'src' in productImg_element.attrs else "Not available"
            description = description_element.text.strip() if description_element else "Not available"

            delivery_fee_element = soup.find('span', {'data-csa-c-type': 'element', 'data-csa-c-delivery-price': True})
            delivery_time_element = soup.find('span', {'data-csa-c-type': 'element', 'data-csa-c-delivery-time': True})

            deliveryFee = delivery_fee_element['data-csa-c-delivery-price'] if delivery_fee_element and 'data-csa-c-delivery-price' in delivery_fee_element.attrs else "Not available"
            deliveryTime = delivery_time_element['data-csa-c-delivery-time'] if delivery_time_element and 'data-csa-c-delivery-time' in delivery_time_element.attrs else "Not available"

            product_data = {
                
                "SKU": sku,
                "Product name": productName,
                "Product title": productTitle,
                "Description": description,
                "Category": category,
                "MRP": mRP,
                "Selling price": sellingPrice,
                "Discount": discount,
                "Weight": weight,
                "Brand name": brand,
                "Image url": productImg,
                "Laptop specification": {
                    "Processor": processor,
                    "RAM": ram,
                    "Storage": storage,
                    "Display": display,
                    "Graphics": graphics + " " + graphics_ram
                },
                "Delivery Fee": deliveryFee,
                "Delivery Time": deliveryTime
            }
            
            return product_data

# this function will save data into json file
    def save_to_json(self, data, filename):
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
        logger.info(f'Data saved to {filename}')


    def save_to_gzip_ndjson(self, data, filename):
        with gzip.open(filename, 'wt', encoding='utf-8') as gzipped_ndjson_file:
            for item in data:
                json.dump(item, gzipped_ndjson_file)
                gzipped_ndjson_file.write('\n')
        logger.info(f'Data saved to {filename}')

    def read_from_gzip_ndjson(self, filename):
        data = []
        try:
            with gzip.open(filename, 'rt', encoding='utf-8') as gzipped_ndjson_file:
                for line in gzipped_ndjson_file:
                    data.append(json.loads(line))
            logger.info(f'Data read from {filename}')
        except FileNotFoundError:
            logger.warning(f'{filename} not found. Returning empty list.')
        return data



def main():
    amazon_scraper = AmazonScraper()
    # Take Page Number as per your wish
    max_pages = 10
    # Scrape laptops for Bangalore
    bangalore_laptops = amazon_scraper.extract_link(BANGALORE_PINCODE, max_pages)
    amazon_scraper.save_to_json(bangalore_laptops, 'bangalore_laptops.json')
    amazon_scraper.save_to_gzip_ndjson(bangalore_laptops, 'bangalore_laptops.ndjson.gz')

    delhi_laptops = amazon_scraper.extract_link(DELHI_PINCODE, max_pages)
    amazon_scraper.save_to_json(delhi_laptops, 'delhi_laptops.json')
    amazon_scraper.save_to_gzip_ndjson(delhi_laptops, 'delhi_laptops.ndjson.gz')

    # Read data from Gzip-compressed NDJSON files
    read_bangalore_laptops = amazon_scraper.read_from_gzip_ndjson('bangalore_laptops.ndjson.gz')
    read_delhi_laptops = amazon_scraper.read_from_gzip_ndjson('delhi_laptops.ndjson.gz')


if __name__ == "__main__":
    main()
