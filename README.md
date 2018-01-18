Python3 - LineBot & Heroku 101
====

###### tags: `python` `linebot` `Heroku` `KM` 


## 系統環境
*    python 3.6
*    django 1.11.8

ps. 可以用 anaconda 2.7 or 3.6 來建立 pyenv ，內建的 libs 很豐富
```shell=
    conda create -n py36 python=3.6 django=1.11.8
    activate py36         # windows
    source activate py36  # macOS and Linux

    # 透過 conda 建立一個 python3.6 與 django1.11 的 pyenv 
```
[reference](https://conda.io/docs/user-guide/tasks/manage-environments.html#activating-an-environment)

## 從建立 Django 專案開始！

### step 1. 新開一個專案

```shell=
    django-admin.py startproject mychatbot
```

### step 2. 開一個新APP
```shell=
    cd mychatbot/mychatbot
    django-admin.py startapp echobot

    vi settings.py
```

把 app 加到 settings.py
```python=
    ...

    # Application definition
    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        
        # my app
        'mychatbot',
        'mychatbot.echobot',
    ]

    ...
```

### step 3. 來寫 line 的 echobot 吧

前面 import django 的東西不多說了～
final code 可以參考我的 github

#### step 3.1 import linebot
首先要 import linebot 的 api lib 跟一些 event 相關模組

#### views.py
```python=
from linebot import (LineBotApi,
                     WebhookParser,
                     WebhookHandler)
from linebot.models import (MessageEvent,
                            TextMessage,
                            TextSendMessage)
from linebot.exceptions import InvalidSignatureError, LineBotApiError
```
#### step 3.2 設定 api 的 token
LINE_CHANNEL_ACCESS_TOKEN ＆ LINE_CHANNEL_SECRET 我們把它設定在 django settings 中，token 可從 [line develop](https://developers.line.me/en/) 申請
並決定要用 line 的 parser OR handler


#### views.py
```python= 
...

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)

VERSION = 'parser'  # WebhookParser
```

#### step 3.3 寫 webhook 解析 request 的部分

parser 與 handler 作法不太一樣，parser 可以自己寫 parse event 的方法，handler 則是用 linebot default 提供的，當然也可以用 decorator，自己寫 handle event function

#### views.py
```python=
...

def callback(request):
    if request.method == 'POST':
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')

        try:
            if VERSION == "parser":
                events = parser.parse(body, signature)
                parse_events(events)

            elif VERSION == "handler":
                handler.handle(body, signature)

        except InvalidSignatureError as e:
            return HttpResponseForbidden()
        except LineBotApiError as e:
            return HttpResponseBadRequest()

        return HttpResponse()
    else:
        return HttpResponseBadRequest()
```

#### step 3.4 寫 custom handle function
自己的 handler 自己寫，這邊提供兩種做法，"parse_events" 是給 webhook_parser 用，"handle_text_message" 是給 webhook_handler 用，兩個 function 都只是很單純的將 input_text 放到 reply 的 TextSendMessage 中，echo 就是這樣！

#### views.py
```python=
...

def parse_events(events):
    for event in events:
        is_msg_event = isinstance(event, MessageEvent) and isinstance(event.message, TextMessage)
        
        if is_msg_event:
            handle_text_message(event)


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    line_bot_api.reply_message(event.reply_token,
                               TextSendMessage(text=event.message.text))
 

@handler.default()
def default(event):
    line_bot_api.reply_message(event.reply_token,
                               TextSendMessage(text='Currently Not Support None Text Message'))
```

### step 4. 處理 deploy 的問題
因為這個 project 最後要 deploy 至 Heroku 平台上，需要透過 github 讓整個過程更簡化，所以我們的 project env 必須先處理過才行

我的做法是在 project root 建立一個 .env 的檔案
這個 .env 檔紀錄 project SECRET_KEY, LINE_CHANNEL_ACCESS_TOKEN 以及 LINE_CHANNEL_SECRET

#### .env
``` shell=
SECRET_KEY='@!@#!@QWE!@#!@#!@#!@#!@#'
LINE_CHANNEL_ACCESS_TOKEN='!@#!@#!@#!@#!@#'
LINE_CHANNEL_SECRET='!@#!@#!@#!@#'
```

接著寫一支簡單的 script，用來取得環境變數

#### get_env.py
```python=
import os
from django.core.exceptions import ImproperlyConfigured


def get_env_variable(var_name):
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = 'Set the {} environment variable'.format(var_name)
        raise ImproperlyConfigured(error_msg)

```

並且修改一下 settings.py，把 project secret_key 拿掉用 get_env 方式取代

#### settings.py
```python=
...
import os
from .get_env import get_env_variable

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_variable('SECRET_KEY')
LINE_CHANNEL_ACCESS_TOKEN = get_env_variable('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = get_env_variable('LINE_CHANNEL_SECRET')
...
```

這樣基本上 django app 就告一段落了，下一步處理 heroku 的問題

## Deploy linebot 至 Heroku 上！

### step 1. 先去 HEROKU 上開一個新 APP
![](https://i.imgur.com/SeGcUl6.png)

### step 2. Deploy app
這裡是以 github webhook 為例

#### step 2.1 取得 github repo
先去把剛剛的程式碼 push 上 github，取得 git repo (例如我的 repo 為 https://github.com/gn00672312/mychatbot)
    ![](https://i.imgur.com/jkP32am.png)

#### step 2.2 掛上 github webhook
接著到 heroku deploy 介面，找到 deployment method，選擇 github，並輸入要 deploy 的 repo
![](https://i.imgur.com/FCH3uyr.png)
![](https://i.imgur.com/Bh3wqhj.png)

#### step 2.3 設定 automatic depolys
點擊 "Enable Automatic Deploys"，之後只要 github 的 master branch 有任何更動，Heroku 就會自動 deploy
![](https://i.imgur.com/jrBe9wv.png)

### step 3. 設定 heroku 的 deploy file
我們需要在 project root 中增加一些檔案，以下逐一介紹

#### step 3.1 增加 "Pipfile.lock" 跟 "requirements.txt"
Heroku 在 deploy 時會去偵測這檔案的設定，他會依照裡面設定來建立環境

#### Pipfile.lock
```yaml=
[[source]]

url = "https://pypi.python.org/simple"
verify_ssl = true


[packages]

gunicorn = "*"

[requires]

python_version = "3.6"
```
gunicorn - Python WSGI HTTP 伺服器套件

#### requirements.txt
```
django==1.11.8
line-bot-sdk==1.5.0
django-heroku==0.2.0
```

#### step 3.2 增加 "Procfile"
Heroku 在 deploy 完成後會去偵測這檔案的設定，他會執行下面的指令啟動 HTTP SERVER
```yaml=
web: gunicorn footbot.wsgi --log-file -
```

### step 4. create heroku app
