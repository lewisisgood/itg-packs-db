"""
parser.py - This parses .scc and .sm files to extract metadata

Expected structure of JSON output:
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

TODO: Run linter
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
    # STR_TO_TYPE fails when displaybpm like '35..140'
    "int": lambda x: int(float(x)),
}

# Exclude data fields we don't care to track
EXCLUDED_KEYS = (
    'steps',
    'stops',
    'radarvalues',
    'notedata',
    'chartname',
    )

"""
This function grabs simfiles from a directory.
"""
def grab_simfiles(rootdir, path_array=[], simfile_array=[]):
    for subdir, dirs, files in os.walk(rootdir):
        path = subdir.split('/')
        if len(path) > 2:
            path_array.append(path)
            for path in path_array:
                pass
        for file in files:
            if file.lower().endswith(('.ssc', '.sm', '.dwi')):
                simfile_array.append(os.path.join(subdir, file))
    return simfile_array


"""
This function parses a .ssc file, given a filename, and deserializes it into a MultiDict
"""
# TODO: change to parse_file
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
        k, v = value.split(":", 1)
        if not v:
            continue

        k = k.strip('#').lower()
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
TODO: delete diff configs
"""
def create_difficulty_map_ssc(parsed):
    # lambda functions lowercase everything in the list
    difficulties = map(lambda x: x.lower(), parsed.getall('difficulty'))
    meters = parsed.getall('meter')

    if len(difficulties) != len(meters):
        raise Exception("Length mismatch in difficulties")

    return dict(zip(difficulties, meters))

"""
Given a parsed multidict with a "key" and "value" property
corresponding to properties within the dict, build out a mapping
of the form {'%difficulty%' : '%level%'}
'ANOTHER:5:00000...'
"""
def create_difficulty_map_dwi(parsed):
    single_difficulties = parsed.getall('single')
    parsed_difficulties = {}

    for item in single_difficulties:
        difficulty, level, _ = item.split(':')
        parsed_difficulties[difficulty.lower()] = int(level)

    return parsed_difficulties


"""
Given a filename, run the helper functions and perform formatting on fields

TODO: Refactor such that the value formatting happens before mapping occurs
"""
def process_ssc_file(filename):
    # load the ssc file into a multidict and initialize the empty mapped object
    parsed = parse_ssc_file(filename)
    mapped = {}

    # update the mapped object with the direct mappings specified in mapping_config
    mapped.update(map_parsed_multidict(parsed, CONFIG["mappings"]))

    # create a difficulty mapping of names to levels for ssc files
    if filename.endswith('.ssc'):
        mapped["difficulty"] = create_difficulty_map_ssc(parsed)
    elif filename.endswith('.dwi'): 
        mapped["difficulty"] = create_difficulty_map_dwi(parsed)

    # add in pack_name
    mapped["pack_name"] = filename.split('/')[1]

    """
    TODO: correct for strange '#title' key in 'parsed'
    MultiDict does not seem to take kindly to asking for #title even though it has it
    For now, just pulls the name of the audio file as the title
    """
    if "title" not in parsed:
        mapped["song_name"] = parsed["music"].split('.')[0]

    # pull difficulties/bpm in title into the difficulty mapping and reformat title
    # e.g. song_name = '[14] [175] Crossroad'
    if "song_name" in mapped:
        if mapped["song_name"].startswith("["):
            song_name = mapped["song_name"]
            mapped["difficulty"]["Challenge"] = song_name.split('] ')[0][1:]
            mapped["bpm"] = song_name.split('] ')[1][1:]
            mapped["song_name"] = song_name.split('] ')[2]

    # pull in bpm from bpms if displaybpm not given in file
    if "bpm" not in parsed and "bpms" in parsed:
        mapped["bpm"] = int(float(parsed["bpms"].split(",")[0].split("=")[1]))

    """
    # fill in missing difficulty map for .sm and .dwi files
    if mapped["difficulty"] == {}:
        possible_diff_array = ['beginner', 'basic', 'another', 'maniac', 'light',
                               'standard', 'heavy', 'challenge', 'oni']
        pprint(parsed)
        if filename.endswith('.dwi'):
            with open(filename, "r") as fp:
                raw = fp.read()
            for item in raw.split(';'):
                # TODO: Make this work
                if item.startswith('#SINGLE'):
                    if item.split('\n').split(':')[1].lower() in possible_diff_array:
                        new_key = item.split(':')[1]
                        mapped["difficulty"][new_key] = item.split(':')[2]
        if filename.endswith('.sm'):
            # TODO: Make this work
            if "notes" in parsed:
                if parsed["notes"].split(':')[1] == 'dance-single':
                    new_key = parsed["notes"].split(':')[3]
                    mapped["difficulty"][new_key] = parsed["notes"].split(':')[4]
    """
    
    return mapped


"""
Test suite: Output processed results to a .json file
TODO: Make an actual test suite
"""
# Get the simfile_array
simfile_array = grab_simfiles(rootdir='packs')

final_file = []

# Run test for single file
"""
parsed_ssc = process_ssc_file('packs/dimo/nail gun/nail gun.ssc')
final_file.append(parsed_ssc)
"""

# Run test for folders of packs
for simfile in simfile_array:
    # If the current simfile is a .sm and an equivalent .ssc file exists, do nothing
    if simfile.endswith('.sm') and f"{simfile.strip('.sm')}.ssc" in simfile_array:
        pass
    else:
        parsed_ssc = process_ssc_file(simfile)
        final_file.append(parsed_ssc)


# Creates a .json file for the output. Assumes an existing file is there.
os.remove("songinfo.json")

with open('songinfo.json', 'w') as filehandle:
    json.dump(final_file, filehandle)