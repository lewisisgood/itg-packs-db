"""
parser.py - This parses .scc and .sm files to extract metadata

TODO: add .sm parsing functionality
"""
import os
import json
from pprint import pprint

from multidict import MultiDict


with open('parser_config.json', 'r') as config:
    CONFIG = json.load(config)


# mapping strings to python types
STR_TO_TYPE = {
    "str": str,
    "int": lambda x: int(float(x)),
}

# TODO: document what these do
EXCLUDED_KEYS = (
    'bpms',
    'steps',
    'stops',
    'radarvalues',
    'notes',
    'notedata',
    'chartname',
    )

"""
This function grabs the simfile from a directory. May or may not currently work
"""
def grab_simfiles(rootdir, path_array=[], simfile_array=[]):
    for subdir, dirs, files in os.walk(rootdir):
        path = subdir.split('/')
        print("\n****** - Next Song Dir -", '*' * 50)
        if len(path) > 2:
            path_array.append(path)
            for path in path_array:
                #print(f"pack_name: {path[1]} -- song_name: {path[2]}")
                pass

        for file in files:
            #print("os.path.join(subdir, file):", os.path.join(subdir, file))
            if file.lower().endswith(('.ssc', '.sm')):
                print(f"KICKASS BRO: '{file}' is a simfile")
                simfile_array.append(os.path.join(subdir, file))
                #print("simfile_array:", simfile_array)
            else:
                print(f"IGNORED: '{file}' is not a simfile")
        print('*' * 75, '\n')
    print("simfile_array at end of grab_simfiles():", simfile_array)
    return simfile_array


"""
This function parses a .ssc file, given a filename, and deserializes it into a MultiDict
"""
def parse_ssc_file(filename):
    with open(filename, "r") as fp:
        raw = fp.read()
    parsed = MultiDict()
    """
    Each "key" in the .ssc file is separated by a semicolon.
    We use semicolons to delimit
    """
    for value in raw.split(';'):
        value = value.strip('\r\n')
        if not value:
            continue
        """
        Takes only the first k/v pair in a given semicolon grouping
        In case there are instances of values without keys, i.e. there are 2 colons in a row
        """
        k, v = value.split(":")[:2]
        if not v:
            continue
        

        k = k.strip('#').lower()
        # print("k:", k)
        # print("value:", value)
        if k in EXCLUDED_KEYS:
            continue
        else:
            parsed.add(k, v)
    return parsed


"""
Extract values out of a parsed MultiDict using the given mapping config.
Returns a sequence of key, value tuples of the form field_name, field_value
"""
def map_parsed_multidict(parsed, mapping_config):
    # returns the value at a certain key within parsed, and casts it to the appropriate type
    def _map_and_cast(field, type):
        return STR_TO_TYPE[type](parsed[field]) if field in parsed else None

    # Call _map_and_cast with each mapping config, and filter out the None values
    return filter(lambda x: x[1],
                  map(lambda x: (x[0], _map_and_cast(**x[1])), mapping_config.items()))


"""
Given a parsed multidict and a difficulty_config with a "key" and "value" property
corresponding to properties within the dict, build out a mapping
of the form {'%difficulty%' : '%level%'}
"""
def create_difficulty_map(parsed, difficulty_config):
    if difficulty_config['key'] not in parsed or difficulty_config['value'] not in parsed:
        raise Exception(f"keys {difficulty_config['key']} or {difficulty_config['value']} were not present in the SSC file")

    keys = parsed.getall(difficulty_config['key'])
    values = parsed.getall(difficulty_config['value'])

    if len(keys) != len(values):
        raise Exception("Length mismatch in difficulties")

    return dict(zip(keys, values))


def process_ssc_file(filename):
    # load the ssc file into a multidict and initialize the empty mapped object
    parsed = parse_ssc_file(filename)
    mapped = {}

    # update the mapped object with the direct mappings specified in mapping_config
    mapped.update(map_parsed_multidict(parsed, CONFIG["mappings"]))

    # create a difficulty mapping of names to levels
    mapped["difficulty"] = create_difficulty_map(parsed, CONFIG["difficulties"])

    # todo: add a pack link

    """
    final_data is JSON/dictionary that will be loaded 
    into MongoDB
    """
    # NOTE: this is no longer the case; the JSON/dictionary to be loaded into mongodb will be
    # the raw dictionary (post processing will be done within mongodb)
    """
    final_data = {
        "song_name": None,
        "song_artist": None,
        "bpm": None,
        # read_meta.py will be updated and eventually fill this in at the db_insert level
        "pack_name": None,
        "pack_link": None,
        "difficulty": {
            "Challenge": None,
            "Hard": None,
            "Medium": None,
            "Easy": None,
            "Beginner": None,
            "Edit": None
        }
    }
    """

    """
    Expected structure:
    {
        "song_name": "Dream a Dream",
        "song_artist": "Captain Jack",
        "bpm": "120",
        "pack_name": "DDR MAX 2",
        "pack_link": "drive.google.com/onemoretimeimbackwithanewrhyme",
        "difficulty": {
            "light": "3",
            "standard": "5",
            "heavy": "7"
        }
    }
    """
    return mapped


"""
Test suite: Run the parser for multiple files
TODO: move files into their own folder
TODO: populate this into 'songinfo.json' instead of print to Terminal
"""
processed = process_ssc_file('night.ssc')

# Print valid JSON object to terminal
print('[')
print(json.dumps(processed))
print(',')

processed = process_ssc_file('tranoid.ssc')
print('')
print(json.dumps(processed))
print(',')
processed = process_ssc_file('westworld.ssc')

print('')
print(json.dumps(processed))
print(',')

# Test: see if parser automatically works for .sm files
parsed_sm = process_ssc_file('30MinutesHarder.sm')
print(json.dumps(parsed_sm))
print(']')
