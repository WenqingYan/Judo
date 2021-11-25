import numpy as np
import pandas as pd
import re
import sys
import os
import binascii
import base64
import numpy as np
from difflib import SequenceMatcher
import itertools
import os.path

# First byte: sfd '20'; 2nd byte: type_id; 3rd byte: packet_no; from 4th byte is payload
# 32 - 3 = 29 bytes
PACKET_LEN=29

RE_PACKET_LINE = r'(?P<timestamp>\d+:\d+:\d+\.\d+)\s+\|\s+(?P<payload>([\da-fA-F]{2} )+)\s+\|\s+(?P<rssi>[\+-]?\d+)'

def parse_payload(payload_string):
    tmp = map(lambda x: int(x, base=16), payload_string.split())
    return tmp[1], tmp[2], tmp[3:]


def compute_sequence(seed, length):
    A1 = 1664525
    C1 = 1013904223
    RAND_MAX1 = ((1 << 31) - 1)
    MAX_BYTE = ((1<<8) - 1)
    num = seed | (1<<4)
    seq = list()
    for _ in range(length):
        num = (num * A1 + C1) & RAND_MAX1
        seq.append(num & MAX_BYTE)
    return seq

SEQUENCE_LIST = [compute_sequence(i, PACKET_LEN) for i in range(256)]
for x in SEQUENCE_LIST:
    print (x)

def popcount(n):
    return bin(n).count('1')

def compute_bit_errors(payload, sequence):
    return sum(map(popcount, (np.array(payload[:PACKET_LEN])^ np.array(sequence[:len(payload[:PACKET_LEN])]))))

def discover_closest_sequence(payload, packet_no):
    error_cnt = compute_bit_errors(payload, SEQUENCE_LIST[packet_no])
    min_err_cnt = error_cnt
    min_err_idx = packet_no
    orig_err_cnt = error_cnt
    if error_cnt > 0:
        for i in range(len(SEQUENCE_LIST)):
            tmp = compute_bit_errors(payload, SEQUENCE_LIST[i])
            if ( tmp < min_err_cnt):
                min_err_cnt = tmp
                min_err_idx = i
            if min_err_cnt == 0:
                break
    return min_err_idx, orig_err_cnt, min_err_cnt

def parse_file(file_name, extradict=None, max_lines=-1):
    ret = list()
    regex_packet = re.compile(RE_PACKET_LINE)
    with open(file_name, 'r') as data_file:
        for line in data_file.readlines()[:max_lines]:

            res = regex_packet.match(line)
            if res is None:
                continue
            d = res.groupdict()
            d['type_id'], d['packet_no'], d['payload'] = parse_payload(d['payload'])
            d['rssi'] = int(d['rssi'])
            d['bit_count'] = 8 * len(d['payload'])
            d['closest_packet_no'], d['orig_bit_errors'], d['bit_errors'] = discover_closest_sequence(d['payload'],
                                                                               d['packet_no'])
            print (d['orig_bit_errors'], d['bit_errors'], d['bit_count'], d['rssi'])
            if extradict is not None:
                d.update(extradict)
            ret.append(d)
    return ret



def ret_ber(distancearr):
    data = list()
    for dist in distancearr:
        file_name = "{data_dir}/{distance}m.txt".format(
            data_dir=DATA_DIR,
            file_label=FILE_LABEL,
            distance=dist,
            freq=FREQ)
        print(file_name)
        data.extend(parse_file(file_name, {'distance' : dist,
                                      'label'    : FILE_LABEL,
                                      'frequency': float(FREQ)},
                              max_lines=MAX_PACKETS))

    raw_data = pd.DataFrame(data)
    packets = raw_data.groupby('distance')
    BER = pd.DataFrame(packets['bit_errors'].sum()/packets['bit_count'].sum())
    BER = BER.rename(index=str, columns={0: 'BER'})

    # print(list(packets['rssi'].mean()))
    BER['RSSI'] = list(packets['rssi'].mean())
    return BER



DATA_DIR = 'tmp'
FILE_LABEL = ''
DISTANCES = [1,2,3]
FREQ = '1'
MAX_PACKETS = 2000

ber = []
rssi = []

DF = ret_ber(DISTANCES)
for x in DF['BER']:
    if x == 0:
        ber.append(ber.append(1.00/144000.00))
    else:
        ber.append(x)

for x in DF['RSSI']:
    rssi.append(x)

print("BER")
print (ber)

print("RSSI")
print (rssi)
