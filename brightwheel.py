import logging
import requests
from dotenv import load_dotenv
import piexif, piexif.helper
from PIL import Image, ExifTags
from PIL.ExifTags import GPS, TAGS
import mutagen
from mutagen.mp4 import MP4
from pathlib import Path
from datetime import datetime, timezone
from dateutil.tz import gettz
import os
import shutil

# useful variables for debugging
PAGE_SIZE = 100  # number of results per page
MAX_PAGE = None  # set to 1 to limit to only 1 page, etc ...

# use these for a dispatch approach
PHOTO = "Photo"
VIDEO = "Video"

# push .env variables into OS environment variables for guardian id and headers
load_dotenv()

# need this for clean requests
# moved outside of fetch of media urls procedure since we also need to
# grab the list of students 
HEADERS = {
    'authority': 'schools.mybrightwheel.com',
    'sec-ch-ua': '"Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"',
    'x-csrf-token': os.environ['X_CSRF_TOKEN'],
    'cookie': os.environ['COOKIE'],
}

DAYCARE_LOCATION = {
    "GPSLatitude": ((41, 1), (52, 1), (98, 10)),
    "GPSLatitudeRef": "N",
    "GPSLongitude": ((87, 1), (37, 1), (3432, 100)),
    "GPSLongitudeRef": "W",
    "GPSAltitude": (181, 1),
    "GPSAltitudeRef": 0
}

ACTION_STRINGS = {
    'ac_photo': "Photo",
    'ac_video': "Video",
    'ac_note': "Note",
    'ac_observation': "Learning Observation",
    'ac_nap': "Nap",
    'ac_health_check': "Health Check",
    'ac_incident': "Incident",
    'ac_kudo': "Kudos"
}

def gps_tuple_to_decimal(latlong, latlong_ref):
    decimal_num = (latlong[0][0]/latlong[0][1] +
                    latlong[1][0]/latlong[1][1]/60 +
                    latlong[2][0]/latlong[2][1]/3600)
    if latlong_ref == "W" or latlong_ref == "S":
        decimal_num *= -1
    return decimal_num

# use the preceding helper to auto-set some DAYCARE_LOCATION entries
DAYCARE_LOCATION['GPSLatDec'] = gps_tuple_to_decimal(DAYCARE_LOCATION['GPSLatitude'],
                                                         DAYCARE_LOCATION['GPSLatitudeRef'])
DAYCARE_LOCATION['GPSLongDec'] = gps_tuple_to_decimal(DAYCARE_LOCATION['GPSLongitude'],
                                                         DAYCARE_LOCATION['GPSLongitudeRef'])
DAYCARE_LOCATION['GPSAltDec'] = (DAYCARE_LOCATION['GPSAltitude'][0] /
                                     DAYCARE_LOCATION['GPSAltitude'][1])

def utc_to_localtz(utc_dttm_str, local_timezone):
    exif_date_format = "%Y:%m:%d %H:%M:%S"
    utc_dttm = datetime.strptime(utc_dttm_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    local_tzinfo = gettz(local_timezone)
    local_dttm = utc_dttm.replace(tzinfo=timezone.utc).astimezone(tz=local_tzinfo)
    local_dttm_str = local_dttm.strftime(exif_date_format)
    local_offset_str = local_dttm.strftime("%z")
    local_offset_str = local_offset_str[:3]+":"+local_offset_str[3:]
    milliseconds_str = local_dttm.strftime("%f")[:-3]
    # return local timestamp, offset, milliseconds from UTC time in +/-HH:MM
    return (local_dttm_str, local_offset_str, milliseconds_str)

def action_type_to_str(action_type):
    return ACTION_STRINGS[action_type] if action_type in ACTION_STRINGS else "???"

def fetch_students(headers={}):
    url = f'https://schools.mybrightwheel.com/api/v1/guardians/{os.environ["GUARDIAN_ID"]}/students?include[]=schools'
    results = requests.get(url, headers=headers).json()
    for student_record in results['students']:
        student = student_record.get('student')
        student_id = student.get('object_id')
        student_name = "{} {}".format(student.get('first_name'), student.get('last_name'))
        time_zone = student.get('time_zone')
        yield {'id': student_id, 'name': student_name, 'tz': time_zone}

def fetch_media_urls(student, page_size=100, max_page=None, headers={}):
    page = 0

    while page < max_page if max_page else True:
        url = (f"https://schools.mybrightwheel.com/api/v1/students/{student['id']}"+
                   f"/activities?page={page}&page_size={page_size}&include_parent_actions=true")
        results = requests.get(url, headers=headers).json()

        for activity in results['activities']:
            # photos, incidents, kudos, notes, observations: all may have an associated image
            media = activity.get('media')
            video_info = activity.get('video_info')

            if media or video_info:
                creator = activity.get('actor')
                creator_str = (creator.get('first_name')+" "+creator.get('last_name')+
                               ", "+creator.get('email'))
                action_type_str = action_type_to_str(activity.get('action_type'))
                room = activity.get('room').get('name')
                note = activity.get('note')
                comment = note if note else ""
                if action_type_str and action_type_str not in ("Photo", "Video"):
                    comment = action_type_str+"\n"+comment
                if room:
                    comment = comment+"\nRoom: "+room
                created_dttm_utc = activity.get('created_at')
                # Brightwheel timestamps are UTC; convert to local time and get offset, ms
                created_dttm, tz_offset, msecs = utc_to_localtz(created_dttm_utc, student['tz'])

            if media:
                image_url = media.get('image_url')
                if image_url:
                    yield PHOTO, image_url, created_dttm, tz_offset, msecs, creator_str, comment

            if video_info:
                video_url = video_info.get('downloadable_url')
                if video_url:
                    yield VIDEO, video_url, created_dttm, tz_offset, msecs, creator_str, comment

        # if we got a short page, we are at the end; break out of the loop
        if len(results['activities']) < page_size:
            break
        page += 1

def save_media(media_dir, media_url, created_dttm):
    media_id, file_suffix = media_url.split('/')[-1].split('?')[0].split('.')
    filestem = created_dttm.replace(":","-") + '--' + media_id
    filename = os.path.join(media_dir, filestem + '.' + file_suffix)
    if os.path.exists(filename):
        return
    media_blob = requests.get(media_url, timeout=10).content
    with open(filename, 'wb') as img_file:
        img_file.write(media_blob)
    return filename

def tag_image(filename, created_dttm, tz_offset_str, msecs_str, creator, comment):
    try:
        img = Image.open(filename)
        exif_dict = piexif.load(img.info['exif'])
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = created_dttm
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = created_dttm
        exif_dict["Exif"][piexif.ExifIFD.OffsetTimeOriginal] = tz_offset_str
        exif_dict["Exif"][piexif.ExifIFD.OffsetTimeDigitized] = tz_offset_str
        exif_dict["Exif"][piexif.ExifIFD.SubSecTimeOriginal] = msecs_str
        exif_dict["Exif"][piexif.ExifIFD.SubSecTimeDigitized] = msecs_str
        exif_dict["0th"][piexif.ImageIFD.Artist] = creator.encode()
        exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = DAYCARE_LOCATION["GPSLatitude"]
        exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = DAYCARE_LOCATION["GPSLatitudeRef"]
        exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = DAYCARE_LOCATION["GPSLongitude"]
        exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = DAYCARE_LOCATION["GPSLongitudeRef"]
        exif_dict['GPS'][piexif.GPSIFD.GPSAltitude] = DAYCARE_LOCATION["GPSAltitude"]
        exif_dict['GPS'][piexif.GPSIFD.GPSAltitudeRef] = DAYCARE_LOCATION["GPSAltitudeRef"]
        if comment:
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(
                comment, encoding="unicode")
        exif_bytes = piexif.dump(exif_dict)
        img.save(filename, exif=exif_bytes, quality=100) # was exif_bytes
    except:
        logging.error('[!] - Could not write EXIF data for file {}'.format(filename))

def tag_video(filename, created_dttm, tz_offset_str, msecs, creator, comment):
    # tag MP4 file; should work for mp4, m4a, m4p, mov
    try:
        vidfile = MP4(filename)
        vidfile["\xa9nam"] = created_dttm+"."+msecs+" "+tz_offset_str+" UTC"
        vidfile["\xa9cpy"] = "© "+created_dttm+"."+msecs+" "+tz_offset_str+" UTC"
        vidfile["\xa9ART"] = creator
        gps_coords = ("%+0.4f, %0.4f, %0.0f" %
                          (DAYCARE_LOCATION["GPSLatDec"],
                           DAYCARE_LOCATION["GPSLongDec"],
                           DAYCARE_LOCATION["GPSAltDec"]))
        vidfile["\xa9xyz"] = gps_coords
        if comment:
            vidfile["desc"] = comment
            vidfile["\xa9cmt"] = comment
        logging.info("[-] Tagged video {}".format(vidfile.pprint()))
        vidfile.save()
    except:
        logging.error("[!] Failed to open and write tags to file {}".format(filename))


if __name__ == '__main__':
    logging.basicConfig(filename='brightwheel.log', filemode='w', level=logging.INFO)
    students = fetch_students(headers=HEADERS)
    for student in students:
        media_data = fetch_media_urls(student, page_size=PAGE_SIZE,
                                      max_page=MAX_PAGE, headers=HEADERS)
        media_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'media-'+student['name'])
        Path(media_dir).mkdir(parents=True, exist_ok=True)
        # single thread saving of files to be nice
        # note that this also looks more like how a user would browse, so
        # this may minimize the chance of being detected as a bot
        for media_type, media_url, created_dttm, *tagdata in media_data:
            logging.info(media_type+":"+created_dttm+" <- "+media_url)
            media_file = save_media(media_dir, media_url, created_dttm)
            if media_type == PHOTO:
                tag_image(media_file, created_dttm, *tagdata)
            elif type == VIDEO:
                tag_video(media_file, created_dttm, *tagdata)
