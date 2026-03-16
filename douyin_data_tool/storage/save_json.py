import json


def save_json(data, file):

    with open(file, "w", encoding="utf8") as f:

        json.dump(data, f, ensure_ascii=False, indent=2)