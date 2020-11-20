import aiohttp
import asyncio
import argparse
import random
import glob
import os
import io
import qrcode
from PIL import Image, ImageDraw, ImageFont

from dotenv import load_dotenv
load_dotenv()

API_SEARCH_500PX = 'https://api.500px.com/v1/photos/search?type=photos&formats=jpeg%2Clytro&exclude_nude=true&page=1&rpp=2000&image_size%5B%5D=2048'

TAGS = ['graffiti', 'streetart', 'nature', 'city', 'travel', 'art']
CANVAS_OUTPUT = (1920, 1080)
HERE_API_KEY = os.getenv('HERE_API_KEY')
HOME_LONGITUDE = os.getenv('HOME_LONGITUDE')
HOME_LATITUDE = os.getenv('HOME_LATITUDE')
MAX_IMAGES_BY_TAG = 30

async def beautiful_slideshow():
    ensure_output_directory_exists()
    clean_output_directory()
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        for tag in TAGS:
            tasks.append(process_tag(session, tag))

        await asyncio.gather(*tasks)

def ensure_output_directory_exists():
    if os.path.exists("output") is False:
        os.mkdir(output)


def clean_output_directory():
    files = glob.glob('output/*.jpg')
    for file in files:
        os.remove(file)

async def process_tag(session, tag: str):
    async with session.get(API_SEARCH_500PX + "&term=" + tag) as response:
        json_search = await response.json()

        photos = json_search['photos']
        random.shuffle(photos)
        
        tasks = []
        i=1
        for photo in photos[0:MAX_IMAGES_BY_TAG]:
            # skip the photo if it is too small
            if(photo['width'] < CANVAS_OUTPUT[0] and photo['height'] < CANVAS_OUTPUT[1]):
                continue
            
            # skip the photo if its ratio is too different than the output ratio
            ratio_photo = photo['width'] / photo['height']
            ratio_screen = CANVAS_OUTPUT[0] / CANVAS_OUTPUT[1]
                        
            if ratio_photo < ratio_screen * 0.75 or ratio_photo > ratio_screen * 1.25:
                continue
            
            tasks.append(process_image(session, tag, i, photo))
            i += 1
            
        await asyncio.gather(*tasks)

async def process_image(session, tag: str, index: int, json):
    print(json['images'][0]['url'])

    dest_image = Image.new('RGB', CANVAS_OUTPUT)

    async with session.get(json['images'][0]['url']) as content_img:
        binary_content = await content_img.read()
        source_image = Image.open(io.BytesIO(binary_content))
        
        source_image.thumbnail(CANVAS_OUTPUT, Image.ANTIALIAS)
        
        # apply the resized image in the dest image and center the thumb
        dest_image.paste(source_image, (int((CANVAS_OUTPUT[0] - source_image.width)/2), int((CANVAS_OUTPUT[1] - source_image.height)/2)))
        
        # create description
        fnt_title = ImageFont.truetype('fonts/Roboto/Roboto-Light.ttf', 72)
        fnt_location = ImageFont.truetype('fonts/Roboto/Roboto-Light.ttf', 28)
        
        d = ImageDraw.Draw(dest_image)
        d.text((155,900), json['name'], font=fnt_title, fill=(255,255,255,128))
        
        if json['location']:
            d.text((250,10), json['location'], font=fnt_location, fill=(255,255,255,128))

        # generate minimap
        if json['longitude'] and json['latitude'] and HERE_API_KEY:
            img_minimap = await generate_minimap(json['longitude'], json['latitude'], session)        
            dest_image.paste(img_minimap, (20, 20))
            
     # generate qrcode
        img_qrcode = generate_qrcode('http://www.500px.com/' + json['url'])
        
        dest_image.paste(img_qrcode, (20, 885))
        
        # save img
        dest_image.save(f"output/{tag}_{index}.jpg", "JPEG")
        
async def generate_minimap(longitude, latitude, session) -> Image:
    poi = [str(latitude), str(longitude)]    

    if HOME_LATITUDE and HOME_LONGITUDE:
        poi += [str(HOME_LATITUDE), str(HOME_LONGITUDE)]
    
    url_map = f"https://image.maps.ls.hereapi.com/mia/1.6/mapview?apiKey={HERE_API_KEY}&ml=fre&nocp=1&poithm=0&poifc=FF6655&ppi=320&t=4&w=200&h=200&poi={','.join(poi)}"

    print(f">>> {url_map}")

    async with session.get(url_map) as content_img:
        binary_content = await content_img.read()
        
    return Image.open(io.BytesIO(binary_content))
   
        
def generate_qrcode(url:str) -> Image:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=3,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)        
    
    return qr.make_image(fill_color="black", back_color="white")
    
    
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(beautiful_slideshow())
