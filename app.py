import os
import time
import hashlib
import requests
from flask import Flask
from flask import request

app = Flask(__name__)

@app.route('/')
def index():
    return 'AIcrowd Rendering Helper'


def download_ipynb(url):
    r = requests.get(url)
    return r.content

@app.route('/render/ipynb')
def ipynb_handler():
    # Input the parameters
    url = request.args.get('url')
    provided_hash = request.args.get('hash')
    if not url:
        return '<pre>Unable to render, URL not provided</pre>'

    # Some authenticatioon
    secret = os.getenv("ONEBOX_IPYNB_RENDERER_SECRET", "AIcrowd-magic")
    generated_hash = hashlib.md5((secret+url).encode()).hexdigest()

    if provided_hash != generated_hash:
        return '<pre>Authentication failed</pre>'

    # Downloading the ipynb and 5 minutes caching
    try:
        download_path = 'download/' + generated_hash
        if os.path.isfile(download_path) and time.time() - os.stat(download_path).st_mtime < 300:
            content = open(download_path, 'r').read()
        else:
            content = download_ipynb(url)
            if os.path.isfile(download_path):
                os.remove(download_path)
            open(download_path,"wb").write(content)
    except Exception as e:
        raise e
        return '<pre>Error fetching ipynb file</pre>'

    # nbconvert
    try:
        import nbconvert
        exportor = nbconvert.exporters.HTMLExporter(template_file='basic')
        generated_html = exportor.from_filename(download_path)[0]
    except Exception as e:
        raise e
        return '<pre>nbconvert parsing error</pre>'

    # Some home baked custom thing
    custom_start = open('start.html', 'r').read()
    custom_end = open('end.html', 'r').read()
    return custom_start + generated_html + custom_end
