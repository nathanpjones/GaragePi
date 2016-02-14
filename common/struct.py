import json

# http://stackoverflow.com/questions/1123000/does-python-have-anonymous-classes/1123054#1123054
class Struct:
    def __init__(self, **entries): self.__dict__.update(entries)

    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)

    def to_json_bytes(self) -> bytes:
        return str.encode(self.to_json())