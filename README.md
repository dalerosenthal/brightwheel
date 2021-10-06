# brightwheel

This is a short python script that downloads all your posted on [Brightwheel](https://mybrightwheel.com/). According to [brightwheel's help](https://help.mybrightwheel.com/en/articles/942382-download-photos-videos#bulk-save-workaround) (as of October 2021),

> At this time photos must be downloaded individually, not in batches.

## Setup your credentials in .env

Create a `.env` file with this content:

```
COOKIE='XXX'
X_CSRF_TOKEN='YYY'
STUDENT_ID='ZZZ'
```

Now we need to fill in the values (but keep the single quote `'` marks).

Login to brightwheel's web app, navigate to your child's feed, and look at the url, which has the `STUDENT_ID`:

```
https://schools.mybrightwheel.com/students/[STUDENT_ID]/feed
```

While on this page, open up your [Chrome Network Panel](https://developer.chrome.com/docs/devtools/network/#open) and click the "APPLY" button on the webpage:
![Apply Button](apply.jpg)

Now copy the `cookie` and `x-csrf-token` headers under **Request Headers** ([here's how to find your request headers](https://stackoverflow.com/questions/4423061/how-can-i-view-http-headers-in-google-chrome)).

## How to run it

Install poetry and then install the required dependencies for this project

```bash
poetry install
```

Downlaod the files to the `media/` folder (takes some time)

```bash
poetry run python brightwheel.py
```
