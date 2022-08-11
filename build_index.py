import gzip
import json
import lzma
import re
from json import JSONDecodeError

import requests
from bs4 import BeautifulSoup

from main import get_set_name


def build_relic_list(drop_table):
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

    build_set_data(set(prime_part_list))

    return relic_list


def add_to_dict_list(dict, key, value):
    if key in dict:
        dict[key].append(value)
    else:
        dict[key] = [value]


def build_set_data(prime_part_list):
    set_list = {}
    for part in prime_part_list:
        add_to_dict_list(set_list, get_set_name(part), part)

    print(set_list)


with open("drop_table.html", "r") as f:
    drop_table = f.read()

build_relic_list(drop_table)


def build_files():
    with open("drop_table.html", "r") as f:
        drop_table = f.read()

    relic_list = json.dumps(build_relic_list(drop_table))
    encoded_list = relic_list.encode('utf-8')

    with gzip.open('relic_list.json.gz', 'wb') as fp:
        fp.write(encoded_list)

    with open('price_history_2022-08-08.json', 'r') as f:
        price_history = json.load(f)

    price_data = {}
    for item in price_history:
        if ' Prime ' in item:
            price_data[item] = price_history[item][0]['avg_price']

    encoded_list = json.dumps(price_data).encode('utf-8')

    with gzip.open('price_data.json.gz', 'wb') as fp:
        fp.write(encoded_list)


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

    return recipes, resources


def parse_name(name, parser):
    if name in parser:
        if isinstance(parser[name], dict):
            mission_node = parser[name]['node']
            if 'planet' in parser[name]:
                mission_node += f" - {parser[name]['planet']}"
            return mission_node
        else:
            if parser[name] == '':
                print(name)

            if parser[name] in parser:
                return parser[parser[name]]
            else:
                return parser[name]
    else:
        return name


def get_ducat_required_data():
    with open('manifest/ExportRecipes.json') as f:
        recipes = json.load(f)

    with open('manifest/ExportResources.json') as f:
        resources = json.load(f)

    with open('json/parser.json') as f:
        parser = json.load(f)

    required_dict = {}
    ducat_dict = {}

    for item in recipes['ExportRecipes']:
        if "primeSellingPrice" in item:
            item_name = parse_name(item['uniqueName'], parser) + " Blueprint"

            ducat_dict[item_name] = item['primeSellingPrice']

            for sub_item in item['ingredients']:
                item_name = parse_name(sub_item['ItemType'], parser)
                if " Prime " in item_name and sub_item['ItemCount'] > 1:
                    required_dict[item_name] = sub_item['ItemCount']

    for item in resources['ExportResources']:
        if "primeSellingPrice" in item:
            item_name = parse_name(item['uniqueName'], parser)
            if item_name + " Blueprint" not in ducat_dict:
                ducat_dict[item_name] = item['primeSellingPrice']
