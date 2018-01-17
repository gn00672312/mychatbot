# -*- coding:utf-8 -*-

import logging
import datetime
import requests
import json

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
                            TextSendMessage,
                            StickerMessage,
                            StickerSendMessage)
from linebot.exceptions import InvalidSignatureError, LineBotApiError

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)

CWB_API_KEY = settings.CWB_API_KEY
VERSION = 'parser'

TAIPEI_2D_FCST = "F-D0047-061"

logger = logging.getLogger('testlogger')


def index(request):
    return render(request, "echobot/index.html", {})


@csrf_exempt
def callback(request):
    logger.info(request)
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
            logger.error(e, e.message)
            return HttpResponseForbidden()
        except LineBotApiError as e:
            logger.error(e, e.message)
            return HttpResponseBadRequest()

        return HttpResponse()
    else:
        return HttpResponseBadRequest()


def parse_events(events):
    for event in events:
        logger.info(event)

        is_msg_event = isinstance(event, MessageEvent) and isinstance(event.message, TextMessage)
        is_sticker_event = isinstance(event, MessageEvent) and isinstance(event.message, StickerMessage)

        if is_msg_event:
            handle_text_message(event)
        elif is_sticker_event:
            handle_sticker_message(event)


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    if event.message.text == u"開團":
        open_new_game(event)

    elif u"天氣" in event.message.text:
        now_weather(event)


def get_game_day(weekday=3):
    today = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    return get_next_weekday(today, weekday)


def get_game_day_weather_info():
    game_day = get_game_day(4)
    game_day = game_day.replace(hour=18, minute=0, second=0)

    return get_weather_info(game_day, location="大安區",
                            default_info="目前查無{gd}晚上的大安區天氣預報".format(gd=game_day.strftime("%a")))


def open_new_game(event):
    game_day = get_game_day(4)

    game_msg_zhtw = ("【練球團】{game_day} \n"
                     "台科大平地足球場 \n\n"
                     "今晚10:30前有4人以上成團，明晚如下雨則取消，請盡量帶球，能到的請回+1，謝謝 \n"
                     ).format(game_day=game_day.strftime("%m/%d (%a) 7:30-10:00 PM"))

    game_msg_enus = ("【It's Football Time】{game_day} \n"
                     "on NTUST hard ground football field \n\n"
                     "It might rain tmr, but we'll still do a headcount first. "
                     "If u can come, please reply '+1', thx! "
                     "If less than 4 people reply '+1' before 10:30pm tonight, the game'll be canceled. \n"
                     ).format(game_day=game_day.strftime("%m/%d (%a) 7:30-10:00 PM"))

    game_msg = game_msg_zhtw + "\n" + game_msg_enus + "\n"

    weather_info = get_game_day_weather_info()

    line_bot_api.reply_message(event.reply_token,
                               TextSendMessage(text=game_msg + weather_info))


def now_weather(event):

    now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    location = event.message.text.replace("天氣", "").strip()

    location = "大安區" if location == "" else location

    info = get_weather_info(now, location,
                            default_info="目前查無" + location + "天氣")

    line_bot_api.reply_message(event.reply_token,
                               TextSendMessage(text=info))


def fetch_forecast(location="大安區"):
    logger.info("get cwb weather forecast")
    url = "https://opendata.cwb.gov.tw/api/v1/rest/datastore/{data_id}"

    try:
        params = dict(Authorization=CWB_API_KEY, locationName=location,
                      format="json", elementName="WeatherDescription")

        req = requests.get(url.format(data_id=TAIPEI_2D_FCST), params=params, verify=False)
        context = json.loads(req.text)
        fcst = context["records"]["locations"][0]["location"][0]

        return fcst["weatherElement"]

    except Exception:
        return None


def get_weather_info(target_dt, location="大安區", default_info="目前查無大安區天氣"):
    weather_elems = fetch_forecast(location)

    weather_info = default_info
    first_fcst_time = None

    if weather_elems is None:
        return default_info

    logger.info("parsing api request")
    for we in weather_elems:
        if not we["elementName"] == "WeatherDescription":
            continue

        for fcst in we["time"]:
            start_time = datetime.datetime.strptime(fcst["startTime"], "%Y-%m-%d %H:%M:%S")
            end_time = datetime.datetime.strptime(fcst["endTime"], "%Y-%m-%d %H:%M:%S")
            weather_desc = fcst["elementValue"]

            # 抓目標時間的3小時內預報
            delta = target_dt - start_time
            if first_fcst_time is None and abs(delta.days * 24 + delta.seconds / 3600) <= 3:

                first_fcst_time = start_time
                weather_info = (u"3小時天氣預報 - 預報時間：\n" +
                                start_time.strftime("%m/%d(%a) %H:%M") + " ~ " +
                                end_time.strftime("%H:%M") + "\n" +
                                location + u"天氣概況：\n" +
                                weather_desc)

    logger.info("parsed api request success")
    return weather_info


def get_next_weekday(dt, wd):
    weekday = dt.isoweekday()
    delta_wd = wd - weekday

    if delta_wd < 0:
        delta_wd += 7

    return dt + datetime.timedelta(days=delta_wd)


@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    # Bot can echo official sticker.
    if event.message.package_id in [str(i) for i in range(1, 5)]:
        line_bot_api.reply_message(event.reply_token,
                                   StickerSendMessage(package_id=event.message.package_id,
                                                      sticker_id=event.message.sticker_id))


@handler.default()
def default(event):
    logger.info(event)

    line_bot_api.reply_message(event.reply_token,
                               TextSendMessage(text='Currently Not Support None Text Message'))
