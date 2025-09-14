import json

def load_multiple_json_objects(filepath):
    """
    Lee un archivo con múltiples objetos JSON concatenados y retorna una lista de objetos.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    objects = []
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(content):
        content = content.lstrip()
        try:
            obj, end = decoder.raw_decode(content)
            objects.append(obj)
            content = content[end:]
            idx = 0
        except json.JSONDecodeError:
            break
    return objects
