import requests
import os
import json
import time
import logging


URL_PREFIX = "https://wechat.wecity.qq.com/trpcapi/THPneumoniaDataService"
session = requests.Session()
logger = logging.Logger(__name__)


def write_to_file(filename, data):
    dir = "data"
    if not os.path.exists(dir):
        os.makedirs(dir)
    with open(os.path.join(dir, filename), "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_data(url, post_body):
    sleep_time = 1
    while True:
        try:
            response = session.post(url, json=post_body)
            data = response.json()
            break
        except Exception as e:
            if sleep_time > 32:
                raise e
            else:
                logger.exception(f"Failed to fetch data. Retry after {sleep_time}s.")
                time.sleep(sleep_time)
                sleep_time *= 2
    if data["code"] == 0:
        return data["rsp"]
    else:
        raise Exception(f"Failed to parse data from {url}. Response: {data}")


def get_cities():
    data = get_data(
        f"{URL_PREFIX}/getPneProCityCode", {"request": {"req": {"none": ""}}}
    )
    data = data["cityList"]

    # Sort list by code to make sure the order is consistent
    def sort(items):
        items.sort(key=lambda x: x["cityCode"])
        for item in items:
            sort(item["children"])

    sort(data)
    write_to_file("cities.json", data)
    return data


def get_history(city_code, is_province_level):
    api_name = "getProvinceInfoHisByCode" if is_province_level else "getCityInfoHisByCode"
    code_name = "provinceCode" if is_province_level else "cityCode"
    data = get_data(
        f"{URL_PREFIX}/{api_name}",
        {
            "request": {"req": {code_name: city_code}},
        },
    )
    data = data["modifyHistory"]
    if len(data) == 0:
        raise Exception(f"History data for {city_code} is empty. Something is wrong.")

    # Sort list by date to make sure the order is consistent
    data.sort(key=lambda x: x["date"])
    write_to_file(f"{city_code}.json", data)
    return data


def get_counties(city_code):
    data = get_data(
        f"{URL_PREFIX}/getCityInfoByProvCode",
        {
            "request": {"req": {"provinceCode": city_code}},
        },
    )
    data = data["cityInfo"]
    data = [{
        "cityCode": county["cityCode"],
        "label": county["city"]
    } for county in data
    if county["cityCode"]]

    # Sort list by code to make sure the order is consistent
    data.sort(key=lambda x: x["cityCode"])
    if data:
        write_to_file(f"cities_{city_code}.json", data)
    return data


city_data = get_cities()
for province in city_data:
    print("Processing", province["label"], province["cityCode"])
    get_history(province["cityCode"], True)
    for city in province["children"]:
        if city["cityCode"] != province["cityCode"]:
            print("Processing", city["label"], city["cityCode"])
            get_history(city["cityCode"], False)
    if len(province["children"]) == 1: # 北京, 天津, 重庆, 上海, 香港, 澳门, 台湾
        counties = get_counties(province["cityCode"])
        for county in counties:
            print("Processing", county["label"], county["cityCode"])
            get_history(county["cityCode"], False)
