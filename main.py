from time import sleep
from Anthropic import check_anthropic, pretty_print_anthropic_keys
from Logger import Logger
from OpenAI import get_oai_model, get_oai_key_attribs, get_oai_org, pretty_print_oai_keys
from APIKey import APIKey, Provider
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from datetime import datetime
import re

api_keys = set()

print("Enter API keys (OpenAI/Anthropic) one per line. Press Enter on a blank line to start validation")

inputted_keys = set()
while True:
    current_line = input()
    if not current_line:
        print("Starting validation...")
        break
    inputted_keys.add(current_line.strip().split(" ")[0])


def validate_openai(key: APIKey):
    if get_oai_model(key) is None:
        return
    if get_oai_key_attribs(key) is None:
        return
    if get_oai_org(key) is None:
        return
    api_keys.add(key)


def validate_anthropic(key: APIKey, retry_count):
    key_status = check_anthropic(key)
    if key_status is None:
        return
    elif key_status is False:
        i = 0
        while check_anthropic(key) is False and i < retry_count:
            i += 1
            sleep(1)
            print(f"Stuck determining pozzed status of rate limited Anthropic key '{key.api_key[-8:]}' - attempt {i} of {retry_count}")
            key.rate_limited = True
        else:
            if i < retry_count:
                key.rate_limited = False
    api_keys.add(key)


oai_regex = re.compile('(sk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20})')
anthropic_regex = re.compile(r'sk-ant-api03-[A-Za-z0-9\-_]{93}AA')

executor = ThreadPoolExecutor(max_workers=100)


def validate_keys():
    futures = []
    for key in inputted_keys:
        if "ant-api03" in key:
            match = anthropic_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.ANTHROPIC, key)
            futures.append(executor.submit(validate_anthropic, key_obj, 20))
        else:
            match = oai_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.OPENAI, key)
            futures.append(executor.submit(validate_openai, key_obj))

    for _ in as_completed(futures):
        pass

    futures.clear()


def get_invalid_keys(valid_oai_keys, valid_anthropic_keys):
    valid_oai_keys_set = set([key.api_key for key in valid_oai_keys])
    valid_anthropic_keys_set = set([key.api_key for key in valid_anthropic_keys])
    invalid_keys = inputted_keys - valid_oai_keys_set - valid_anthropic_keys_set
    if len(invalid_keys) < 1:
        return
    print('\nInvalid Keys:')
    for key in invalid_keys:
        print(key)


def output_keys():
    validate_keys()
    valid_oai_keys = []
    valid_anthropic_keys = []
    for key in api_keys:
        if key.provider == Provider.OPENAI:
            valid_oai_keys.append(key)
        elif key.provider == Provider.ANTHROPIC:
            valid_anthropic_keys.append(key)

    output_filename = "key_snapshots.txt"
    sys.stdout = Logger(output_filename)
    print("#" * 90)
    print(f"Key snapshot from {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 90)
    print(f'\n--- Checked {len(inputted_keys)} keys | {len(inputted_keys) - len(api_keys)} were invalid ---')
    get_invalid_keys(valid_oai_keys, valid_anthropic_keys)  # just for completeness’s sake
    print()
    if valid_oai_keys:
        pretty_print_oai_keys(valid_oai_keys)
    if valid_anthropic_keys:
        pretty_print_anthropic_keys(valid_anthropic_keys)

    sys.stdout.file.close()


output_keys()
