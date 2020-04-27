import os
import time
import hashlib
import requests
from flask import Flask
from flask import request
import json

app = Flask(__name__)
BASE_URL = 'https://api.github.com'
COLAB_URL = 'https://colab.research.google.com/gist/'
API_TOKEN = os.environ.get('AICROWDBOT_GITHUB_TOKEN',None)
headers={'Authorization':'token %s'%API_TOKEN}
params={'scope':'gist'}
USER_NAME = "aicrowd-bot"

@app.route('/')
def index():
    return 'AIcrowd Rendering Helper'


def download_ipynb(url):
    r = requests.get(url)
    return r.content

def get_gist_id(gist_name):

    get_url = BASE_URL + "/users/" + USER_NAME + "/gists" 
    res = requests.get(get_url,headers=headers)
    if res.status_code == 200:
        res_text = json.loads(res.text)
        limit = len(res.json())

        for g,no in zip(res_text, range(0,limit)):  
            for ka,va in res.json()[no]['files'].items():
                if str(va['filename']) == str(gist_name):
                    print(res.json()[no]['id'])
                    return res.json()[no]['id']
        return 0




def create_gist(content,challenge_name):
    gist_name = challenge_name+"_baseline.ipynb"
    gist_id = get_gist_id(gist_name)
    headers={'Authorization':'token %s'%API_TOKEN}
    params={'scope':'gist'}
    if gist_id == '':
        payload={"description":"Gist created to open in colab","public":True,"files":{gist_name:{"content":content}}}
        res=requests.post(url,headers=headers,params=params,data=json.dumps(payload))
        j=json.loads(res.text)
        gist_id = j['id']
    else:
        payload={"description":"Gist created to open in colab","public":True,"files":{gist_name:{"content":content}}}
        res = requests.patch(url,headers=headers,params=params,data=json.dumps(payload))

    colab_url = COLAB_URL + USER_NAME +"/" + gist_id
    return colab_url



@app.route('/render/ipynb')
def ipynb_handler():
    # Input the parameters
    url = request.args.get('url')
    # print(url)
    provided_hash = request.args.get('hash')
    challenge_name = request.args.get('challenge_name')
    print(url)
    if not url:
        return '<pre>Unable to render, URL not provided</pre>'

    # # Some authenticatioon
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
    raw_url = url.replace("blob","raw")
    download_url = raw_url + "?inline=false"
    colab_url = create_gist(content,challenge_name)
    contribute_button = '<a href="' + url + '"class=btn btn-primary"><i class="fas fa-edit"> Contribute</i></a>'
    download_button = '<a href="' + download_url + '"class=btn btn-primary"><i class="fa fa-download"> Download</i></a>'
    colab_button = '<a href="' + colab_url + '"class=btn btn-primary"><i class="fas fa-infinity"> Execute In Colab</i></a>'
    custom_start += '<div style="text-align: center;">'+ contribute_button + download_button + colab_button+'</div>'

    custom_end = open('end.html', 'r').read()

    return custom_start + generated_html + custom_end


