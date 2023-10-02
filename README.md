# Brightwheel Bulk Download Photos and Videos Script

This is a short python script that downloads all your posted media on [Brightwheel](https://mybrightwheel.com/). According to [brightwheel's help](https://help.mybrightwheel.com/en/articles/942382-download-photos-videos#bulk-save-workaround) (as of October 2021 and October 2023),

> At this time photos must be downloaded individually, not in batches.

## Setup your credentials in .env

Create a `.env` file with this content:

```
GUARDIAN_ID='ZZZ'
X_CSRF_TOKEN='YYY'
COOKIE='XXX'
```

Now we need to fill in the values (but keep the single quote `'` marks).

Login to brightwheel's web app. On the first page, open up your [Chrome Network Panel](https://developer.chrome.com/docs/devtools/network/#open). Then, navigate to "My Children". You should see some entries populate the Network Panel table. In that able you will find some URLs that look like one of these (below) and which have your `GUARDIAN_ID`:

```
https://schools.mybrightwheel.com/api/v1/guardians/[GUARDIAN_ID]
https://schools.mybrightwheel.com/api/v1/guardians/[GUARDIAN_ID]/students?include[]=schools
```

Next copy the `cookie` and `x-csrf-token` headers under **Request Headers** ([here's how to find your request headers](https://stackoverflow.com/questions/4423061/how-can-i-view-http-headers-in-google-chrome)).

## How to run it

Install poetry and then install the required dependencies for this project

```bash
poetry install
```

Download the files to the `media-[Student Name]/` folders (takes some time)

```bash
poetry run python brightwheel.py
```
