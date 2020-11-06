import aiohttp
import asyncio
import argparse
import random
import glob
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

API_SEARCH_500PX = 'https://api.500px.com/v1/photos/search?type=photos&formats=jpeg%2Clytro&exclude_nude=true&page=1&rpp=2000&image_size%5B%5D=2048'

TAGS = ['graffiti', 'streetart', 'panda']

CANVAS_OUTPUT = (1920, 1080)

async def beautiful_slideshow():
    clean_output_directory()
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        for tag in TAGS:
            tasks.append(process_tag(session, tag))

        await asyncio.gather(*tasks)

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
        for photo in photos[0:20]:
            tasks.append(process_image(session, tag, i, photo))
            i += 1
            
        await asyncio.gather(*tasks)

async def process_image(session, tag: str, index: int, json):
    print(json['images'][0]['url'])
            
    async with session.get(json['images'][0]['url']) as content_img:
        dest_image = Image.new('RGB', CANVAS_OUTPUT)

        
        binary_content = await content_img.read()
        
        url_page = 'http://www.500px.com/' + json['url']
        name = json['name']
        latitude = json['latitude']
        longitude = json['longitude']
        location = json['location']
        
        
        # TODO: change the method to write the file, for use asyncio
        f = open(f"output/{tag}_{index}.jpg", "wb")
        f.write(binary_content)
        f.close()
        
        # load image and resize that
        source_image = Image.open(f"output/{tag}_{index}.jpg")
        source_image.thumbnail(CANVAS_OUTPUT, Image.ANTIALIAS)
        
        # apply the resized image in the dest image 
        dest_image.paste(source_image, (0,0))
        
        # create description
        fnt_title = ImageFont.truetype('fonts/Roboto/Roboto-Light.ttf', 72)
        fnt_location = ImageFont.truetype('fonts/Roboto/Roboto-Light.ttf', 28)
        
        d = ImageDraw.Draw(dest_image)
        d.text((155,900), name, font=fnt_title, fill=(255,255,255,128))
        
        if location:
            d.text((20,10), location, font=fnt_location, fill=(255,255,255,128))

        # generate qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=3,
            border=1,
        )
        qr.add_data(url_page)
        qr.make(fit=True)        
        
        img_qrcode = qr.make_image(fill_color="black", back_color="white")
        
        dest_image.paste(img_qrcode, (20, 885))
        
        # save img
        dest_image.save(f"output/{tag}_{index}.jpg", "JPEG")
    
    
    
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(beautiful_slideshow())
