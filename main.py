import gzip
import json

import requests


def __decode_and_decompress(url):
    file = requests.get(url).content
    file = gzip.decompress(file)
    return json.loads(file.decode("utf-8"))


def __get_index_file():
    index = __decode_and_decompress("http://198.46.233.213/index/index.json.gz")

    return index


__index = __get_index_file()
__relic_dict = __index['relics']
__price_dict = __index['prices']
__ducat_dict = __index['ducats']
__required_dict = __index['required_count']
__nv_relics = __index['non_vaulted']

__rarity_dict = {
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
        return __rarity_dict[refinement[0]][rarity_id]
    except KeyError:
        drop_chances = []
        for digit in str(rarity_id):
            if int(digit) in __rarity_dict[refinement[0]]:
                drop_chances.append(get_drop_chance(refinement[0], int(digit)))
            else:
                return 'N/A'

        return drop_chances


def get_relic_drops(relic, refinement):
    relic_drops = {}

    for drop in __relic_dict[relic].items():
        relic_drops[drop[0]] = get_drop_chance(refinement, drop[1])

    return relic_drops


def fix_refinement_style(args):
    style_list = ['s', '1', '2', '3', '4', '8']
    refinement_list = ['i', 'e', 'f', 'r']

    style = '4'
    refinement = 'r'

    for arg in args:
        if arg is None:
            continue

        arg = arg.lower()
        if arg[-1] in refinement_list:
            refinement = arg[-1]

        arg = arg[:1]
        if arg in style_list:
            style = arg
        elif arg in refinement_list:
            refinement = arg

    return refinement, style


def get_price(item):
    if item in __price_dict:
        return __price_dict[item]
    else:
        return 0


def get_ducats(item):
    if item in __ducat_dict:
        return __ducat_dict[item]
    else:
        return 0


def get_required_amount(item):
    if item in __required_dict:
        return __required_dict[item]

    return 1


def get_relic_prices(drops):
    relic_prices = {}

    for drop in drops:
        relic_prices[drop] = get_price(drop)

    return relic_prices


def calculate_average(drops, style_data):
    modifier = style_data[0]
    num_drops = style_data[1]
    chance_left = 1
    chance_used = 1
    average_return = 0

    relic_prices = get_relic_prices(drops)

    relic_prices = {k: v for k, v in sorted(relic_prices.items(), key=lambda item: item[1], reverse=True)}

    for item_name in relic_prices:
        chance = drops[item_name]
        price = relic_prices[item_name]

        if not isinstance(chance, list):
            chance = [chance]

        for drop_chance in chance:
            adj_chance = 1 - (drop_chance / chance_left)

            actual_chance = adj_chance ** modifier

            item_chance = 1 - actual_chance

            item_chance = chance_used * item_chance

            chance_left = chance_left - drop_chance

            chance_used = chance_used * actual_chance

            adj_price = price * item_chance

            average_return += adj_price * num_drops

    return average_return


def get_average_return(relic, arg1=None, arg2=None):
    average_dict = {'s': 1,
                    '1': 4,
                    '2': [2, 2],
                    '3': [3, (4 / 3)],
                    '4': [4, 1],
                    '8': [8, 1]}

    refinement, style = fix_refinement_style([arg1, arg2])

    drops = get_relic_drops(relic, refinement)
    average_return = 0
    if not isinstance(average_dict[style], list):
        for relic_drop in drops:
            price = get_price(relic_drop)
            chance = drops[relic_drop]

            try:
                average_return += price * chance
            except TypeError:
                for drop_chance in chance:
                    average_return += price * drop_chance

        average_return *= average_dict[style]
    else:
        average_return = calculate_average(drops, average_dict[style])

    return round(average_return, 3)


def get_set_parts(set_name):
    return list(get_set_ducats(set_name))


def get_set_ducats(set_name):
    return dict(filter(lambda x: set_name in x[0], __ducat_dict.items()))


def get_set_list():
    return list(filter(lambda x: 'Set' in x, __price_dict.keys()))


def get_relic_list():
    return list(__relic_dict)


def get_relic_dict():
    return __relic_dict


def get_required_dict():
    return __required_dict


def get_ducat_dict():
    return __ducat_dict


def get_price_dict():
    return __price_dict


def get_non_vaulted_relics():
    return __nv_relics


def get_vaulted_relics():
    return list(set(__relic_dict) - set(__nv_relics))


def get_set_required(set_name):
    required_amount = {}
    for item in get_set_parts(set_name):
        required_amount[item] = get_required_amount(item)

    return required_amount
