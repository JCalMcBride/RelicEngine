import gzip
import json
import lzma
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup


def build_relic_list(drop_table: Optional[str]):
    if drop_table is None:
        drop_table = requests.get('https://n8k6e2y6.ssl.hwcdn.net/repos/hnfvc0o3jnfvc873njb03enrf56.html').text

    soup = BeautifulSoup(drop_table, 'lxml')

    tables = soup.find_all('tr',
                           string=re.compile("Relic .Intact"))

    relic_list = {}
    prime_part_list = []

    for table in tables:
        items = table.find_all_next("tr", limit=6)

        relic = table.find("th").contents[0].split("Relic")[0].rstrip()

        chance_dict = {'Uncommon (25.33%)': 1, 'Uncommon (11.00%)': 2, 'Rare (2.00%)': 3}

        relic_drops = {}
        for item in items:
            item_contents = item.find_all("td")

            item_name = item_contents[0].contents[0]
            tier_id = chance_dict[item_contents[1].contents[0]]

            if " Prime " in item_name:
                prime_part_list.append(item_name)

            if item_name not in relic_drops:
                relic_drops[item_name] = tier_id
            else:
                tier_ids = sorted([str(relic_drops[item_name]), str(tier_id)], reverse=True)
                relic_drops[item_name] = int(''.join(tier_ids))

        relic_list[relic] = dict(sorted(relic_drops.items(), reverse=True, key=lambda x: str(x[1])))

    return relic_list


def add_to_dict_list(dict, key, value):
    if key in dict:
        dict[key].append(value)
    else:
        dict[key] = [value]


def encode_and_compress(json_file):
    encoded_list = json.dumps(json_file).encode('utf-8')

    return encoded_list


def get_price_history(pd_file=None):
    if pd_file is None:
        soup = BeautifulSoup(requests.get('http://23.95.43.245/history/').text, 'html.parser')
        return requests.get(sorted(['http://23.95.43.245/history/' + node.get('href')
                                    for node in soup.find_all('a') if node.get('href').endswith('json')])[-1]).json()
    else:
        return requests.get(f"http://23.95.43.245/history/{pd_file}").json()


def build_price_data(price_history):
    if price_history is None:
        price_history = get_price_history()

    price_data = {}
    for item in price_history:
        if ' Prime ' in item:
            price_data[item] = price_history[item][0]['avg_price']

    return price_data


def build_files(drop_table=None, price_history=None,
                recipes=None, resources=None, warframes=None, weapons=None):
    relic_list = build_relic_list(drop_table)
    price_data = build_price_data(price_history)
    ducat_data, required_data = get_ducat_required_data(recipes, resources, warframes, weapons)

    index_file = {'relics': relic_list,
                  'prices': price_data,
                  'ducats': ducat_data,
                  'required_count': required_data}

    return index_file


def decompress_lzma(data):
    results = []
    while True:
        decomp = lzma.LZMADecompressor(lzma.FORMAT_AUTO, None, None)
        try:
            res = decomp.decompress(data)
        except lzma.LZMAError:
            if results:
                break  # Leftover data is not a valid LZMA/XZ stream; ignore it.
            else:
                raise  # Error on the first iteration; bail out.
        results.append(res)
        data = decomp.unused_data
        if not data:
            break
        if not decomp.eof:
            raise lzma.LZMAError("Compressed data ended before the end-of-stream marker was reached")
    return b"".join(results)


def fix():
    response = requests.get('https://content.warframe.com/PublicExport/index_en.txt.lzma')
    data = response.content
    byt = bytes(data)
    length = len(data)
    stay = True
    while stay:
        stay = False
        try:
            decompress_lzma(byt[0:length])
        except lzma.LZMAError:
            length -= 1
            stay = True

    return decompress_lzma(byt[0:length]).decode("utf-8")


def decode_manifest_file(manifest_url):
    json_file = requests.get(f"http://content.warframe.com/PublicExport/Manifest/{manifest_url}").text
    return json.loads(json_file, strict=False)


def get_manifest():
    wf_mainfest = fix().split('\r\n')

    for item in wf_mainfest:
        if "ExportRecipes" in item:
            recipes = decode_manifest_file(item)
        elif "ExportResources" in item:
            resources = decode_manifest_file(item)
        elif "ExportWarframes" in item:
            warframes = decode_manifest_file(item)
        elif "ExportWeapons" in item:
            weapons = decode_manifest_file(item)

    return recipes, resources, warframes, weapons


def build_parser(resources, warframes, weapons):
    parser = {}

    for item in resources['ExportResources']:
        if "Prime" in item['name']:
            parser[item['uniqueName']] = item['name']

    for item in warframes['ExportWarframes']:
        if "Prime" in item['name']:
            item_name = item['name']
            if '<ARCHWING>' in item['name']:
                item_name = item_name.split(maxsplit=1)[1]
            parser[item['uniqueName']] = item_name

    for item in weapons['ExportWeapons']:
        if "Prime" in item['name'] and item['productCategory'] not in ['SpecialItems', 'SentinelWeapons']:
            parser[item['uniqueName']] = item['name']

    return parser


def get_ducat_required_data(recipes=None, resources=None, warframes=None, weapons=None):
    if recipes is None or resources is None or warframes is None or weapons is None:
        recipes, resources, warframes, weapons = get_manifest()

    parser = build_parser(resources, warframes, weapons)

    required_dict = {}
    ducat_dict = {}

    for item in recipes['ExportRecipes']:
        if item['resultType'] in parser:
            item_name = parser[item['resultType']] + " Blueprint"

            ducat_dict[item_name] = item['primeSellingPrice']

            for sub_item in item['ingredients']:
                if sub_item['ItemType'] in parser:
                    item_name = parser[sub_item['ItemType']]
                    if sub_item['ItemCount'] > 1:
                        required_dict[item_name] = sub_item['ItemCount']

    for item in resources['ExportResources']:
        if 'primeSellingPrice' in item:
            ducat_dict[item['name']] = item['primeSellingPrice']

    return ducat_dict, required_dict


index_file = build_files()

with gzip.open('/var/www/html/index/index.json.gz', 'wb') as fp:
    fp.write(encode_and_compress(index_file))