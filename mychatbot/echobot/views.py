# -*- coding:utf-8 -*-
from django.conf import settings
from django.http import (HttpResponse,
                         HttpResponseBadRequest,
                         HttpResponseForbidden)

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

from linebot import (LineBotApi,
                     WebhookParser,
                     WebhookHandler)
from linebot.models import (MessageEvent,
                            TextMessage,
                            TextSendMessage)
from linebot.exceptions import InvalidSignatureError, LineBotApiError

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)

VERSION = 'parser'


def index(request):
    return render(request, "echobot/index.html", {})


@csrf_exempt
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
