import os
import time
import hashlib
import requests
from flask import Flask
from flask import request
import json
import re

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
    CHUNK_SIZE = 32768
    content = b''
    response = requests.get(url, allow_redirects=True, stream=True)
    for chunk in response.iter_content(CHUNK_SIZE):
        if chunk:
            content += chunk
    content.decode("utf-8")
    return content

def get_gist_id(gist_name):

    get_url = BASE_URL + "/users/" + USER_NAME + "/gists" 
    res = requests.get(get_url,headers=headers)

    if res.status_code == 200:
        res_text = json.loads(res.text)
        limit = len(res.json())

        for g,no in zip(res_text, range(0,limit)):  
            for ka,va in res.json()[no]['files'].items():
                if str(va['filename']) == str(gist_name):
                    return res.json()[no]['id']
    return 0



def create_gist(content,challenge_name):
    gist_name = challenge_name+"_baseline.ipynb"
    gist_id = get_gist_id(gist_name)
    headers={'Authorization':'token %s'%API_TOKEN}
    params={'scope':'gist'}
    try:
        content = content.decode('utf-8')
    except:
        pass
    if gist_id == 0 :
        url = BASE_URL + '/gists'
        payload={"description":"Gist created to open in colab","private":True,"files":{gist_name:{"content":content}}}
        data = json.dumps(payload)
        res=requests.post(url,headers=headers,params=params,data=data)
        j=json.loads(res.text)
        gist_id = j['id']
    else:
        url = BASE_URL + '/gists/' + gist_id
        payload={"description":"Gist created to open in colab","private":True,"files":{gist_name:{"content":content}}}

        data = json.dumps(payload)
        res = requests.patch(url,headers=headers,params=params,data=data)

    colab_url = COLAB_URL + USER_NAME +"/" + gist_id
    return colab_url

def authentication(url,provided_hash):
    # Some authenticatioon
    secret = os.getenv("ONEBOX_IPYNB_RENDERER_SECRET", "AIcrowd-magic")
    generated_hash = hashlib.md5((secret+url).encode()).hexdigest()
    if provided_hash != generated_hash:
        return 'failed'
    return generated_hash


def convert_tohtml(download_path):
    try:
        from nbconvert import HTMLExporter
        import nbformat
        f = open(download_path)
        con = f.read()
        con = nbformat.reads(con,as_version=4)
        con['nbformat_minor'] = 4
        html_exporter = HTMLExporter()
        html_exporter.template_name = 'basic'

        generated_html = html_exporter.from_notebook_node(con)[0]
    except Exception as e:
        raise e
        return '<pre>nbconvert parsing error</pre>'
    return generated_html


@app.route('/render/ipynb')
def ipynb_handler():
    # Input the parameters
    url = request.args.get('url')
    provided_hash = request.args.get('hash')
    if not url:
        return '<pre>Unable to render, URL not provided</pre>'
    generated_hash = authentication(url,provided_hash)

    if generated_hash == 'failed':
        return '<pre>Authentication Failed</pre>'

    # Downloading the ipynb and 2 minutes caching
    try:
        download_path = 'download/' + generated_hash
        if os.path.isfile(download_path) and time.time() - os.stat(download_path).st_mtime < 120:
            content = open(download_path, 'r').read()
        else:
            content = download_ipynb(url)
            if os.path.isfile(download_path):
                os.remove(download_path)
            open(download_path,"wb").write(content)

    except Exception as e:
        raise e
        return '<pre>Error fetching ipynb file</pre>'

    generated_html = convert_tohtml(download_path)

    custom_start = open('start.html', 'r').read()
    raw_url = url.replace("blob","raw")
    url = url.replace("raw", "blob")
    download_url = raw_url + "?inline=false"

    colab_url = create_gist(content,generated_hash)
    contribute_button = '<a href="' + url + '" target="_blank"  class="btn btn-primary action-btn"><i class="fas fa-edit"> Contribute</i></a>'
    download_button = '<a href="' + download_url + '" class="btn btn-primary action-btn"><i class="fa fa-download"> Download</i></a>'
    colab_button = '<a href="' + colab_url + '" target="_blank" class="btn btn-primary action-btn"><i class="fas fa-infinity"> Execute In Colab</i></a>'
    custom_start += '<div style="text-align: center;">'+ contribute_button + download_button + colab_button+'</div>'

    custom_end = open('end.html', 'r').read()

    return custom_start + generated_html + custom_end


@app.route('/render/colab')
def colab_handler():
    # Input the parameters
    url = request.args.get('url')
    provided_hash = request.args.get('hash')
    if not url:
        return '<pre>Unable to render, URL not provided</pre>'

    generated_hash = authentication(url,provided_hash)
    # if generated_hash == 'failed':
    #     return '<pre>Authentication Failed</pre>'

    if "?usp=sharing" in url:
        url = url.replace("?usp=sharing", '') 
    # print(url)
    if "colab.research.google.com/drive/" in url:
        colab_id = re.findall("[-\w]{25,}", url)[0]
        download_url = "https://docs.google.com/uc?export=download&id=%s" % (colab_id)
    elif "colab.research.google.com/github/" in url:
        github_url = re.findall("github(.*)", url)[0]
        download_url = "https://github.com" + github_url.split("#")[0]
        download_url = download_url.replace("blob", "raw")
    elif "colab.research.google.com/gist/" in url:
        gist_url = re.findall("gist(.*)", url)[0]
        download_url = "https://gist.github.com" + gist_url.split("#")[0] + "/raw"
    else:
        raise Exception("Wrong type of url sent -> %s" % url)
    
    # Downloading the ipynb and 2 minutes caching
    try:
        download_path = 'download/' + generated_hash
        if os.path.isfile(download_path) and time.time() - os.stat(download_path).st_mtime < 120:
            content = open(download_path, 'r').read()
        else:
            content = download_ipynb(download_url)
            if os.path.isfile(download_path):
                os.remove(download_path)
            open(download_path,"wb").write(content)

    except Exception as e:
        raise e
        return '<pre>Error fetching ipynb file</pre>'

    generated_html = convert_tohtml(download_path)
    custom_start = open('start.html', 'r').read()

    colab_url = url

    download_button = '<a href="' + download_url + '" class="btn btn-primary action-btn"><i class="fa fa-download"> Download</i></a>'
    colab_button = '<a href="' + url + '" target="_blank" class="btn btn-primary action-btn"><i class="fas fa-infinity"> Execute In Colab</i></a>'
    custom_start += '<div style="text-align: center;">' + download_button + colab_button + '</div>'

    custom_end = open('end.html', 'r').read()

    return custom_start + generated_html + custom_end



