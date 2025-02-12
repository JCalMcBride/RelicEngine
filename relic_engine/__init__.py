import gzip
import warnings
from typing import Dict, Tuple, List
import json

import requests


def __decode_and_decompress(url):
    file = requests.get(url).content
    file = gzip.decompress(file)
    return json.loads(file.decode("utf-8"))


def __get_index_file():
    index = __decode_and_decompress("https://github.com/JCalMcBride/RelicEngine/raw/master/index.json.gz")

    return index


__index = __get_index_file()
__relic_dict = __index['relics']
__price_dict = __index['prices']
__ducat_dict = __index['ducats']
__required_dict = __index['required_count']
__nv_relics = __index['non_vaulted']
__type_dict = __index['types']

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
    ref = refinement.lower()[0]
    try:
        return __rarity_dict[ref][rarity_id]
    except KeyError:
        drop_chances = []
        for digit in str(rarity_id):
            if int(digit) in __rarity_dict[ref]:
                drop_chances.append(get_drop_chance(ref, int(digit)))
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


def calculate_average(drops, style_data, custom_prices=None):
    modifier = style_data[0]
    num_drops = style_data[1]
    chance_left = 1
    chance_used = 1
    average_return = 0

    if custom_prices:
        relic_prices = {k: custom_prices[k] for k in drops if k in custom_prices}
    else:
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


def get_average_return(relic, arg1=None, arg2=None, custom_prices=None):
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
            if custom_prices and relic_drop in custom_prices:
                price = custom_prices[relic_drop]
            else:
                price = get_price(relic_drop)
            chance = drops[relic_drop]

            try:
                average_return += price * chance
            except TypeError:
                for drop_chance in chance:
                    average_return += price * drop_chance

        average_return *= average_dict[style]
    else:
        average_return = calculate_average(drops, average_dict[style], custom_prices)

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


def get_type_dict():
    return __type_dict


def get_set_type(item):
    item_type = None
    if item in __type_dict:
        item_type = __type_dict[item]

    return item_type


def get_vaulted_relics():
    return list(set(__relic_dict) - set(__nv_relics))


def get_set_required(set_name):
    required_amount = {}
    for item in get_set_parts(set_name):
        required_amount[item] = get_required_amount(item)

    return required_amount


PAlist = {
    "prime access": {
        "Ash": "Carrier,Vectis",
        "Atlas": "Dethcube,Tekko",
        "Banshee": "Euphona,Helios",
        "Chroma": "Gram,Rubico",
        "Ember": "Sicarus,Glaive",
        "Equinox": "Stradavar,Tipedo",
        "Frost": "Latron,Reaper",
        "Gara": "Astilla,Volnus",
        "Hydroid": "Ballistica,Nami Skyla",
        "Inaros": "Karyst,Panthera",
        "Ivara": "Baza,Aksomati",
        "Limbo": "Destreza,Pyrana",
        "Loki": "Bo,Wyrm",
        "Mag": "Boar,Dakra",
        "Mesa": "Akjagara,Redeemer",
        "Mirage": "Akbolto,Kogake",
        "Nekros": "Galatine,Tigris",
        "Nezha": "Guandao,Zakti",
        "Nidus": "Magnus,Strun",
        "Nova": "Soma,Vasto",
        "Nyx": "Hikou,Scindo",
        "Oberon": "Sybaris,Silva & Aegis",
        "Octavia": "Pandero,Tenora",
        "Rhino": "Ankyros,Boltor",
        "Saryn": "Nikana,Spira",
        "Titania": "Corinth,Pangolin",
        "Trinity": "Kavasa,Dual Kamas",
        "Valkyr": "Cernos,Venka",
        "Vauban": "Akstiletto,Fragor",
        "Volt": "Odonata",
        "Wukong": "Ninkondi,Zhuge",
        "Zephyr": "Kronen,Tiberon",
        "Harrow": "Knell,Scourge",
        "Garuda": "Corvas,Nagantaka",
        "Khora": "Hystrix,Dual Keres",
        "Revenant": "Phantasma,Tatsu",
        "Baruuk": "Afuris,Cobra & Crane",
        "Hildryn": "Larkspur,Shade",
        "Wisp": "Fulmin,Gunsen",
        "Grendel": "Zylok,Masseter",
        "Gauss": "Akarius,Acceltra",
        "Protea": "Velox,Okina"
    }
}


def _build_relic_data(relic_dict: Dict, price_dict: Dict, ducat_dict: Dict, nv_relics: List[str]) -> Dict:
    """Helper function to build relic data."""
    relic_data = {}
    tier_map = {3: 'Rare', 2: 'Uncommon', 1: 'Common'}

    for relic, drops in relic_dict.items():
        relic_data[relic] = {}
        for refinement in ['Intact', 'Exceptional', 'Flawless', 'Radiant']:
            relic_data[relic][refinement] = {
                'drops': {},
                'vaulted': relic not in nv_relics,
                'average_return': {}
            }

            for part, rarity in drops.items():
                tier_id = int(str(rarity)[0]) - 1  # Take first digit and shift by 1
                chance = get_drop_chance(refinement[0], rarity)

                relic_data[relic][refinement]['drops'][part] = {
                    'chance': chance,
                    'tier': tier_map[tier_id + 1],
                    'tier_id': tier_id,
                    'price': price_dict.get(part, 0),
                    'ducats': ducat_dict.get(part, 0),
                    'calculated_chance': {style: None for style in ['solo', '1b1', '2b2', '3b3', '4b4']},
                    'calculated_price': {style: None for style in ['solo', '1b1', '2b2', '3b3', '4b4']}
                }

            avg_return = get_average_return(relic, refinement[0], '4')
            relic_data[relic][refinement]['average_return'] = {
                'solo': get_average_return(relic, refinement[0], 's'),
                '1b1': get_average_return(relic, refinement[0], '1'),
                '2b2': get_average_return(relic, refinement[0], '2'),
                '3b3': get_average_return(relic, refinement[0], '3'),
                '4b4': avg_return
            }

    return relic_data


def _build_set_data(relic_data: Dict, relic_dict: Dict, price_dict: Dict, ducat_dict: Dict, required_dict: Dict,
                    type_dict: Dict) -> Dict:
    """Helper function to build set data."""
    set_data = {}
    for set_name in get_set_list():
        set_name_without_set = set_name.replace(' Set', '')
        set_data[set_name_without_set] = {
            'parts': {},
            'vaulted': all(relic_data[relic]['Intact']['vaulted'] for relic in relic_dict if
                           any(part in relic_dict[relic] for part in get_set_parts(set_name_without_set))),
            'type': type_dict.get(set_name_without_set, type_dict.get(set_name, 'N/A')),
            'plat': price_dict.get(set_name, 0),
            'prime-access': next((frame for frame, items in PAlist['prime access'].items() if
                                  set_name_without_set.split()[0] in [frame] + items.split(',')), 'N/A')
        }

        for part in get_set_parts(set_name_without_set):
            set_data[set_name_without_set]['parts'][part] = {
                'plat': price_dict.get(part, 0),
                'ducats': ducat_dict.get(part, 0),
                'required': required_dict.get(part, 1)
            }
    return set_data


def build_json_files(pd_file: str = None) -> Tuple[Dict, Dict]:
    """
    Build JSON files containing relic and set data for backwards compatibility.

    Note: This function is maintained for backwards compatibility only.
    It is recommended to use other specific functions when possible.

    Args:
        pd_file (str, optional): Price data file. This parameter is deprecated and not used in the current implementation.

    Returns:
        Tuple[Dict, Dict]: A tuple containing relic_data and set_data dictionaries.
    """
    if pd_file is not None:
        warnings.warn("The 'pd_file' parameter is deprecated and not used in the current implementation.",
                      DeprecationWarning, stacklevel=2)

    # Fetch required data
    relic_dict = get_relic_dict()
    price_dict = get_price_dict()
    ducat_dict = get_ducat_dict()
    required_dict = get_required_dict()
    nv_relics = get_non_vaulted_relics()
    type_dict = get_type_dict()

    # Build relic and set data
    relic_data = _build_relic_data(relic_dict, price_dict, ducat_dict, nv_relics)
    set_data = _build_set_data(relic_data, relic_dict, price_dict, ducat_dict, required_dict, type_dict)

    # Convert to JSON-compatible format
    return json.loads(json.dumps(relic_data)), json.loads(json.dumps(set_data))
