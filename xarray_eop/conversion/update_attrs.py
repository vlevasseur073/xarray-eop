import importlib.resources
import json

ATTRS_PATH = importlib.resources.files("conf") / "attributes"
STAC_DISCOVERY = [
    "type",
    "stac_version",
    "stac_extensions",
    "id",
    "collection",
    "geometry",
    "bbox",
    "properties",
    "links",
    "assets"
]

def update_attributes(
        typ: str
) -> dict:
    filename = "_".join(["attrs",typ])
    with open(ATTRS_PATH / filename) as f:
        attrs=json.load(f)

    # print(attrs.keys())

    new_attrs: dict[str] = {
        "stac_discovery": {},
        "other_metadata": {},
    }
    for k in attrs.keys():
        if k in STAC_DISCOVERY:
            new_attrs["stac_discovery"][k] = attrs[k]
        elif k=="history":
            new_attrs["other_metadata"][k] = attrs[k]
        elif k=="other_metadata":
            for d1,d2 in attrs[k].items():
                new_attrs["other_metadata"][d1] = d2
        else:
            new_attrs["other_metadata"][k] = attrs[k]


    with open(ATTRS_PATH / (filename+"new"),"w") as f:
        json.dump(new_attrs,f,indent=4)

    return new_attrs

    
if __name__ == "__main__":
    
    update_attributes("S03OLCEFR")