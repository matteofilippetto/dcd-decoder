#!/usr/bin/python3

# Copyright 2021 Matteo Filippetto (https://github.com/matteofilippetto)
# based on code of Tobias Girstmair (https://gir.st/blog/greenpass.html)
# Consider this code GPLv3 licensed.
#


import argparse
import json
import zlib
import flynn
import base45
import os
from PIL import Image
from pyzbar import pyzbar
from datetime import datetime
from urllib.request import urlopen

dcdschema = urlopen(
    "https://raw.githubusercontent.com/ehn-dcc-development/ehn-dcc-schema/release/1.3.0/DCC.combined-schema.json"
)
glb_dcdschema = json.load(dcdschema)

vacholders = urlopen(
    "https://raw.githubusercontent.com/ehn-dcc-development/ehn-dcc-schema/release/1.3.0/valuesets/vaccine-mah-manf.json"
)
glb_vacholders = json.load(vacholders)["valueSetValues"]

mednames = urlopen(
    "https://raw.githubusercontent.com/ehn-dcc-development/ehn-dcc-schema/release/1.3.0/valuesets/vaccine-medicinal-product.json"
)
glb_mednames = json.load(mednames)["valueSetValues"]

vactypes = urlopen(
    "https://raw.githubusercontent.com/ehn-dcc-development/ehn-dcc-schema/release/1.3.0/valuesets/vaccine-prophylaxis.json"
)
glb_vactypes = json.load(vactypes)["valueSetValues"]


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", help="Input data: image file or qr code date")
    args = parser.parse_args()
    input = args.data

    if input is not None:
        payload = getPayload(input)
        if payload is not None:
            print("decoding payload: " + payload)
            # strip header ('HC1:')
            qr_data_zlib = base45.b45decode(payload)
            # decompress data
            qr_data = zlib.decompress(qr_data_zlib)
            # decode cose document
            (_, (headers1, headers2, cbor_data, signature)) = flynn.decoder.loads(
                qr_data
            )
            # decode cbor-encoded payload
            data = flynn.decoder.loads(cbor_data)
            # date format from UTC timestamp
            date = lambda ts: datetime.utcfromtimestamp(ts).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            #  start print QR Code informations
            print("QR Code Issuer :", data[1])
            print("QR Code Expiry :", date(data[4]))
            print("QR Code Generated :", date(data[6]))
            annotate(data[-260][1], glb_dcdschema["properties"])
    else:
        parser.print_help()


def getPayload(input):

    payload = None

    if os.path.exists(input):
        infile = input
    else:
        infile = None
        qr_data_zlib_b45 = input
        payload = str(qr_data_zlib_b45)[4:]

    if infile:
        try:
            qr_pil = Image.open(infile)
            # decode QR code into raw bytes:
            qr_data_zlib_b45 = pyzbar.decode(qr_pil)[0].data
            payload = str(qr_data_zlib_b45)[6:-1]
        except IOError:
            exit(1)

    return payload


def annotate(data, schema, level=0):
    for key, value in data.items():
        description = schema[key].get("title") or schema[key].get("description") or key
        description, _, _ = description.partition(" - ")
        if type(value) is dict:
            print("  " * level, description)
            _, _, sch_ref = schema[key]["$ref"].rpartition("/")
            annotate(value, glb_dcdschema["$defs"][sch_ref]["properties"], level + 1)
        elif type(value) is list:
            print("  " * level, description)
            _, _, sch_ref = schema[key]["items"]["$ref"].rpartition("/")
            for v in value:
                annotate(v, glb_dcdschema["$defs"][sch_ref]["properties"], level + 1)
        else:  # value is scalar
            if value in glb_vacholders:
                print(
                    "  " * level,
                    description,
                    ":",
                    value,
                    glb_vacholders[value]["display"],
                )
            elif value in glb_mednames:
                print(
                    "  " * level,
                    description,
                    ":",
                    value,
                    glb_mednames[value]["display"],
                )
            elif value in glb_vactypes:
                print(
                    "  " * level,
                    description,
                    ":",
                    value,
                    glb_vactypes[value]["display"],
                )
            else:
                print("  " * level, description, ":", value)


if __name__ == "__main__":
    main()
