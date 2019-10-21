import os
import time
import io
import json
import requests
import subprocess
from PIL import Image
from PIL import ExifTags
import hashlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

DRIVER_PATH = '/home/raffa/Scraper/chromedriver'

#wd = webdriver.Chrome(executable_path=DRIVER_PATH)

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def fetch_image_urls(query:str, max_links_to_fetch:int, wd:webdriver, sleep_between_interactions:int=1):
    def scroll_to_end(wd):
        wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep_between_interactions)

    # build the google query
    search_url = "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&tbs=sur:fc"

    # load the page
    wd.get(search_url.format(q=query))

    image_urls = set()
    image_count = 0
    results_start = 0
    while image_count < max_links_to_fetch:
        scroll_to_end(wd)

        # get all image thumbnail results
        thumbnail_results = wd.find_elements_by_css_selector("img.rg_ic")
        number_results = len(thumbnail_results)

        print(f"Found: {number_results} search results. Extracting links from {results_start}:{number_results}")

        for img in thumbnail_results[results_start:number_results]:
            # try to click every thumbnail such that we can get the real image behind it
            try:
                img.click()
                time.sleep(sleep_between_interactions)
            except Exception:
                continue

            # extract image urls
            actual_images = wd.find_elements_by_css_selector('img.irc_mi')
            for actual_image in actual_images:
                if actual_image.get_attribute('src'):
                    image_urls.add(actual_image.get_attribute('src'))

            image_count = len(image_urls)

            if len(image_urls) >= max_links_to_fetch:
                print(f"Found: {len(image_urls)} image links, done!")
                break
        else:
            print("Found:", len(image_urls), "image links, looking for more ...")
            time.sleep(1)
            load_more_button = wd.find_element_by_css_selector(".ksb")
            if load_more_button:
                wd.execute_script("document.querySelector('.ksb').click();")

        # move the result startpoint further down
        results_start = len(thumbnail_results)

    return image_urls


def persist_image(folder_path:str,url:str,with_exif:int,wo_exif:int,abnormal_exif:int,skipped_imgs:int,ttl_dwnlds:int):
    try:
        image_content = requests.get(url).content

    except Exception as e:
        print(f"ERROR - Could not download {url} - {e}")

    # Checking the file exenstion
    split_url = url.split('.')
    img_extension = split_url[len(split_url)-1]
    print(img_extension)
    try:
        image_file = io.BytesIO(image_content)
        with Image.open(image_file).convert('RGB') as image:
            # Check if image size is more than 200*200 pixels
            width, height = image.size
            if width > 200 and height > 200:

                #Extracting EXIF data
                try:
                    with Image.open(image_file) as img:
                        exif_data = {
                            ExifTags.TAGS[k]: v
                            for k, v in img._getexif().items()
                            if k in ExifTags.TAGS
                        }
                    
                except Exception as e:
                    print(f"WARNING - problem extracting EXIF data {url} - {e}")
                    wo_exif += 1
                    exif_data = {}
  
                if 'Copyrights' in exif_data or 'Copyright' in exif_data or 'COPYRIGHTS' in exif_data or 'COPYRIGHT' in exif_data or  'copyrights' in exif_data or 'copyright' in exif_data:
                    print('Found copyrighted images, skipping.')
                    skipped_imgs += 1
                else:
                    print(width,height)
                    file_name = os.path.join(folder_path,hashlib.sha1(image_content).hexdigest()[:10])
                    file_path = file_name + '.jpg'
                    with open(file_path, 'wb') as f:
                        image.save(f, "JPEG", quality=85)
                        ttl_dwnlds += 1
                            
                    # Calculating MD5 hash
                    image_md5_hash = md5(file_path)
                try:
                    formatted_info = json.dumps({'URL':url,'MD5 Hash':image_md5_hash, 'Width':width, 'Height':height, 'EXIF Data':exif_data}, indent=4)
                    with_exif += 1
                except Exception as e:
                    print(f"WARNING - problem extracting EXIF data {file_path} - {e}")
                    formatted_info = json.dumps({'URL':url,'MD5 Hash':image_md5_hash, 'Width':width, 'Height':height}, indent=4)
                    abnormal_exif += 1
                    print(exif_data)

                # Create info file
                extra_info_file = file_name + '.json'
                subprocess.run(['touch', extra_info_file])                 
                with open(extra_info_file, 'a') as f: 
                    f.write(formatted_info)
                    print(f"SUCCES - saved {url} - as {file_path}")
    except Exception as e:
        print(f"ERROR - Could not save {url} - {e}")
    return with_exif, wo_exif, abnormal_exif, skipped_imgs, ttl_dwnlds

def search_and_download(search_term:str,driver_path:str,target_path='./PCBimages',number_images=5):
    target_folder = os.path.join(target_path,'_'.join(search_term.lower().split(' ')))

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    

    chrome_options = Options()
    #chrome_options.add_argument("--disable-extensions")
    #chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument('window-size=1920x1080')
    chrome_options.add_argument("--headless")

    with webdriver.Chrome(executable_path=driver_path,options=chrome_options) as wd:
        res = fetch_image_urls(search_term, number_images, wd=wd, sleep_between_interactions=0.5)


    ttl_imgs_found = len(res)
    ttl_dwnlds = 0
    skipped_imgs = 0
    with_exif = 0
    wo_exif = 0
    abnormal_exif = 0
    for elem in res:
        with_exif, wo_exif, abnormal_exif, skipped_imgs, ttl_dwnlds = persist_image(target_folder,elem,with_exif,wo_exif,abnormal_exif,skipped_imgs,ttl_dwnlds)


    with_exif -= wo_exif # Empty EXIF dictionaries are counted with 'With EXIF'; see persist_image()
    scraping_results = { 'Images statistics': { 'Found': ttl_imgs_found, 'Skipped': skipped_imgs, 'Downloads':ttl_dwnlds, 'With EXIF':with_exif, 'Abnormal EXIF':abnormal_exif, 'W/O EXIF':wo_exif } }
    scraping_results_file = target_path + '/scrapingResults.json'
    subprocess.run(['touch', scraping_results_file])
    with open(scraping_results_file, 'a') as f:
        formatted = json.dumps(scraping_results, indent=4)
        f.write(formatted)
        print(f"COMPLETE : Results file created at {scraping_results_file}")




search_term= 'PCB'
search_and_download(search_term=search_term, driver_path=DRIVER_PATH)
