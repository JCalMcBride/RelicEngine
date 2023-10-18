import gzip
import json
import lzma
import re
from pprint import pprint
from typing import Optional

import requests
from bs4 import BeautifulSoup


def build_relic_list(drop_table: Optional[str]):
    if drop_table is None:
        drop_table = requests.get('https://www.warframe.com/droptables').text

    print(drop_table)

    soup = BeautifulSoup(drop_table, 'lxml')

    tables = soup.find_all('tr',
                           string=re.compile("Relic .Intact"))

    relic_list = {}
    prime_part_list = []

    for table in tables:
        items = table.find_all_next("tr", limit=6)

        raw_relic = table.find("th").contents[0].split("Relic")[0].rstrip().split()

        try:
            relic = f"{raw_relic[0]} {raw_relic[1].upper()}"
        except IndexError:
            continue

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

    tables = soup.find_all('tr', string=lambda t: t and any(x in t for x in ['(Exterminate)', '(Capture)', '(Defense)',
                                                                             '(Mobile Defense)', '(Sabotage)',
                                                                             '(Survival)', '(Rescue)', '(Caches)',
                                                                             'Kuva Siphon', 'Kuva Flood']))

    nv_relics = set()
    for table in tables:
        items = table.find_all_next("tr", limit=20)

        for item in items:
            item_contents = item.find_all("td")

            if not item.get_text():
                break
            if not item_contents:
                continue

            item_name = item_contents[0].contents[0]

            if 'Relic' in item_name:
                raw_relic = item_name.split()
                relic = f"{raw_relic[0]} {raw_relic[1].upper()}"
                nv_relics.add(relic)

    return relic_list, nv_relics


def add_to_dict_list(dct, key, value):
    if key in dct:
        dct[key].append(value)
    else:
        dct[key] = [value]


def encode_and_compress(json_file):
    encoded_list = json.dumps(json_file, indent=4).encode('utf-8')

    return encoded_list


def get_price_history(pd_file=None):
    if pd_file is None:
        soup = BeautifulSoup(requests.get('https://relics.run/history/').text, 'html.parser')
        return requests.get(sorted(['http://relics.run/history/' + node.get('href')
                                    for node in soup.find_all('a') if node.get('href').endswith('json')])[-1]).json()
    else:
        return requests.get(f"https://relics.run/history/{pd_file}").json()


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
    relic_list, nv_relics = build_relic_list(drop_table)
    price_data = build_price_data(price_history)
    ducat_data, required_data, type_data = get_mainfest_data(recipes, resources, warframes, weapons)

    index_file = {'relics': relic_list,
                  'non_vaulted': list(nv_relics),
                  'prices': price_data,
                  'ducats': ducat_data,
                  'required_count': required_data,
                  'types': type_data}

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
        elif "ExportSentinels" in item:
            sentinels = decode_manifest_file(item)

    return recipes, resources, warframes, weapons, sentinels


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


def get_mainfest_data(recipes=None, resources=None, warframes=None, weapons=None, sentinels=None):
    if any(x is None for x in [recipes, resources, warframes, weapons, sentinels]):
        recipes, resources, warframes, weapons, sentinels = get_manifest()

    parser = build_parser(resources, warframes, weapons)

    required_dict = {}
    ducat_dict = {}
    type_dict = {'Kavasa Prime': 'Skins'}

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
        if 'primeSellingPrice' in item and item['name'] + " Blueprint" not in ducat_dict:
            ducat_dict[item['name']] = item['primeSellingPrice']

    for item in warframes['ExportWarframes']:
        if ' Prime' in item['name']:
            item_name = item['name']
            if '<ARCHWING>' in item_name:
                item_name = item_name[11:]
            type_dict[item_name] = 'Warframes'


    translation_dict = {
        'LongGuns': 'Primary',
        'Pistols': 'Secondary',
        'SpaceMelee': 'Archmelee',
        'SpaceGuns': 'Archgun',
    }

    for item in weapons['ExportWeapons']:
        if 'Prime' in item['name'] and item['productCategory'] not in ['SpecialItems', 'SentinelWeapons']:
            item_type = item['productCategory']
            if item_type in translation_dict:
                item_type = translation_dict[item_type]

            type_dict[item['name']] = item_type

    for item in sentinels['ExportSentinels']:
        if 'Prime' in item['name'] and item['productCategory'] not in ['SpecialItems']:
            type_dict[item['name']] = item['productCategory']

    return ducat_dict, required_dict, type_dict


index_file = build_files()


with gzip.open('/var/www/html/index/index.json.gz', 'wb') as fp:
    fp.write(encode_and_compress(index_file))
