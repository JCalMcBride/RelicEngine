import gzip
import json

import requests


def decode_and_decompress(url):
    file = requests.get(url).content
    file = gzip.decompress(file)
    return json.loads(file.decode("utf-8"))


def get_index_files():
    rl = decode_and_decompress("http://23.95.43.245/index/relic_list.json.gz")
    pd = decode_and_decompress("http://23.95.43.245/index/price_data.json.gz")
    dd = decode_and_decompress("http://23.95.43.245/index/ducat_data.json.gz")
    rd = decode_and_decompress("http://23.95.43.245/index/required_data.json.gz")

    return rl, pd, dd, rd


relic_list, price_data, ducat_data, required_data = get_index_files()

rarity_dict = {
    'i': {
        1: ((25 + (1 / 3)) / 100),
        2: .11,
        3: .02
    },
    'e': {
        1: ((23 + (1 / 3)) / 100),
        2: .13,
        3: .04
    },
    'f': {
        1: .2,
        2: .17,
        3: .06
    },
    'r': {
        1: (1 / 6),
        2: .2,
        3: .1
    },
}


def get_set_name(prime_part):
    set_name = prime_part.split(" Prime")[0] + " Prime"
    if "Kavasa" in set_name:
        set_name += " Kubrow Collar"

    return set_name


def get_drop_chance(refinement: str, rarity_id: int):
    try:
        return rarity_dict[refinement[0]][rarity_id]
    except KeyError:
        drop_chances = []
        for digit in str(rarity_id):
            if int(digit) in rarity_dict[refinement[0]]:
                drop_chances.append(get_drop_chance(refinement[0], int(digit)))
            else:
                return 'N/A'

        return drop_chances


def get_relic_drops(relic, refinement):
    relic_drops = {}

    for drop in relic_list[relic].items():
        relic_drops[drop[0]] = get_drop_chance(refinement, drop[1])

    return relic_drops


def calculate_average(relic, param, param1, param2):
    pass


def get_average_return(relic, refinement, style):
    get_relic_drops(relic, refinement)

    solo = 0
    for drop in relic['drops']:
        solo += relic['drops'][drop]['price'] * relic['drops'][drop]['chance']

    solo = solo
    one_by_one = solo * 4

    relic['average_return']['solo'] = round(solo, 0)
    relic['average_return']['1b1'] = round(one_by_one, 0)

    relic = calculate_average(relic, "2b2", 2, 2)
    relic = calculate_average(relic, "3b3", 3, (4 / 3))
    relic = calculate_average(relic, "4b4", 4, 1)

    return relic