import requests
from dotenv import load_dotenv
import os

# useful variables for debugging
PAGE_SIZE = 100  # number of results per page
MAX_PAGE = None  # set to 1 to limit to only 1 page, etc ...

load_dotenv()

media_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'media')

def fetch_image_urls(page_size=100, max_page=None):
  page = 0
  headers = {
    'authority': 'schools.mybrightwheel.com',
    'sec-ch-ua': '"Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"',
    'x-csrf-token': os.environ['X_CSRF_TOKEN'],
    'cookie': os.environ['COOKIE'],
  }

  while page < max_page if max_page else True:
    url = f'https://schools.mybrightwheel.com/api/v1/students/{os.environ["STUDENT_ID"]}/activities?page={page}&page_size={page_size}&include_parent_actions=true'
    results = requests.get(url, headers=headers).json()

    for activity in results['activities']:
      media = activity.get('media')
      if not media:
        continue
      image_url = media.get('image_url')
      if image_url:
        created_at = activity.get('created_at')
        yield created_at, image_url

    if len(results['activities']) < page_size:
      break

    page += 1

def save_image(created_at, image_url):
  media_id = image_url.split('/')[-1].split('.')[0]
  stem = created_at + '-' + media_id
  filename = os.path.join(media_dir, stem + '.jpg')

  if os.path.exists(filename):
    return

  img_blob = requests.get(image_url, timeout=10).content
  with open(filename, 'wb') as img_file:
    img_file.write(img_blob)

if __name__ == '__main__':
  data = fetch_image_urls(page_size=PAGE_SIZE, max_page=MAX_PAGE)

  # single thread saving of files to be nice
  for created_at, image_url in data:
    print(created_at, image_url)
    save_image(created_at, image_url)
