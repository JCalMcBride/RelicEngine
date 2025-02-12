import json

import relic_engine

relic_data, set_data = relic_engine.build_json_files()

with open('relic_data.json', 'w') as f:
    json.dump(relic_data, f, indent=4)

with open('set_data.json', 'w') as f:
    json.dump(set_data, f, indent=4)