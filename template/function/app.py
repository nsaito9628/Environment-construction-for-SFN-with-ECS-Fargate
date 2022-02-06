#!/usr/bin/python
# -*- coding: utf-8 -*-
import time
import urllib.request, urllib.parse
import json
import datetime
import os
from bs4 import BeautifulSoup as bs4
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 場所から緯度経度を取得
def getLatitude(place):

    params = {
        'q': place
    }

    # 入力された地点よりクエリパラメータを生成
    params = urllib.parse.urlencode(params)

    # 緯度経度取得APIに地点をセット
    url = 'http://www.geocoding.jp/api/?' + params

    # 緯度経度取得API取得サイトにアクセス
    url = urllib.request.urlopen(url).read()

    # APIの実行結果を取得
    soup = bs4(url, 'html.parser')

    # 実行結果にエラーが含まれていた場合は空文字を返す
    if soup.find('error'):
        return '', ''

    # 緯度経度を文字列型に変換して返す
    lat = soup.find('lat').string
    lon = soup.find('lng').string

    return lat, lon

# 経度緯度から降水強度を取得
def getWeatherReport(lat, lon):
    # YahooWebAPIアプリケーションID
    appId = os.environ['APP_ID']

    # Yahoo気象情報APIのリクエストURLの大元
    baseUrl =  'https://map.yahooapis.jp/weather/V1/place?coordinates='

    # 大元のURLに緯度経度とアプリケーションIDを設定して気象情報取得用のURLを生成
    url = baseUrl + lon + ',' + lat + '&output=json&appid=' + appId

    # 気象情報取得用のURLにアクセス
    weather_report = urllib.request.urlopen(url).read()

    # json形式で取得できるので辞書型に変換
    json_tree = json.loads(weather_report)

    # 取得結果の中から必要な情報のみ抽出(現在時刻から10分感覚で取得できるので[6]:1時間後を取得)
    weather_list = json_tree['Feature'][0]['Property']['WeatherList']['Weather'][6]

    # 時刻表示用にフォーマットを整形
    dt = datetime.datetime.strptime(weather_list['Date'], '%Y%m%d%H%M')
    dt = dt.strftime("%Y/%m/%d %H:%M")

    # 降水強度に応じて傘の必要不要を判定
    if weather_list['Rainfall'] == 0.0:
        message = dt + ' : 傘は必要ありません'
    elif 0.0 < weather_list['Rainfall'] < 1.0:
        message = dt + ' : 長時間出かける場合は傘を持っていきましょう'
    elif weather_list['Rainfall'] >= 1.0:
        message = dt + ' : 絶対に傘を持って出かけてください'

    return message

def lambda_handler(event, context):
    # 送られたメッセージから地点と返信用トークンを取得
    for message_event in json.loads(event['body'])['events']:
        place = message_event['message']['text']
        reply_token = message_event['replyToken']

    # 入力された地点の緯度、経度を取得
    lat, lon = getLatitude(place)

    # 緯度、経度を用いて傘の必要不要を取得
    message = getWeatherReport(lat, lon)

    # チャンネルアクセストークンと返信用トークンを用いてユーザにメッセージを返す
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + os.environ['ChannelAccessToken']
    }
    body = {
        'replyToken': reply_token,
        'messages': [
            {
                "type": "text",
                "text": message,
            }
        ]
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), method='POST', headers=headers)
    with urllib.request.urlopen(req) as res:
        logger.info(res.read().decode("utf-8"))


    return {
        'statusCode': 200,
        'body': json.dumps('Success!')
    }