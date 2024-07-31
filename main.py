import argparse
import json
import re
import os
import configparser
import sys
import logging
from datetime import datetime
import requests

# Global variables for configuration
DATAVERSE_URL_BASE = None
API_TOKEN = None
LOG_DIR = None

LOGGER = None


def validate_identifier_version(file_path):
    if not os.path.isfile(file_path):
        print(f"Error: The file path '{file_path}' is not valid or does not exist.")
        return None

    doi_pattern = re.compile(r'^(doi:\d+\.\d+/[a-zA-Z0-9]+/[a-zA-Z0-9]+?,?|hdl:\d+/\d+),(\d+),(\d+)$', re.IGNORECASE)

    valid_dois = []
    seen_dois = set()  # To track seen DOIs for duplicate checking
    invalid_dois = []

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            match = doi_pattern.match(line)
            if match:
                identifier = match.group(1)
                major_version = match.group(2)
                minor_version = match.group(3)
                doi_combined = f"{identifier} {major_version}.{minor_version}"
                if doi_combined not in seen_dois:
                    valid_dois.append(doi_combined)
                    seen_dois.add(doi_combined)
            else:
                invalid_dois.append(line)

    if invalid_dois:
        print("Invalid DOIs:")
        for doi in invalid_dois:
            print(doi)
        print("\nPlease fix the invalid DOIs and re-run the program.")
        return None

    return valid_dois


def read_config(config_path):
    try:
        global DATAVERSE_URL_BASE, API_TOKEN, LOG_DIR
        config = configparser.ConfigParser()
        if not config.read(config_path):
            raise FileNotFoundError(f"Config file '{config_path}' not found or empty.")
        DATAVERSE_URL_BASE = config.get("DATAVERSE", "url_base")
        API_TOKEN = config.get("DATAVERSE", "api_token")
        LOG_DIR = config.get("DATAVERSE", "log_dir")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def setup_logger(build_number):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Create a file handler
    log_file = os.path.join(LOG_DIR, f"{build_number}_baggit.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def submit_baggit_archive(ids):
    counters = {
        'baggit request success': 0,
        'Unauthorized': 0,
        'Dataset Not Found': 0,
        'Requested version not found': 0,
        'Version already submitted': 0,
        'connection_errors': 0,
        'other_errors': 0
    }

    for id in ids:
        parts = id.split()
        if len(parts) != 2:
            LOGGER.error(f"Invalid ID format: {id}")
            continue

        persistent_identifier, version = parts
        url = f"{DATAVERSE_URL_BASE}/api/admin/submitDatasetVersionToArchive/:persistentId/{version}?persistentId={persistent_identifier}"

        headers = {
            "X-Dataverse-key": API_TOKEN
        }

        try:
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                LOGGER.info(f"Submitted version {version} of {persistent_identifier} to archive.")
                counters['baggit request success'] += 1
            elif response.status_code == 401:
                LOGGER.error(f"Error: version {version} of {persistent_identifier} - Unauthorized: Bad API key")
                counters['Unauthorized'] += 1
            elif response.status_code == 404:
                LOGGER.error(f"Error: version {version} of {persistent_identifier} - Not Found: Dataset with Persistent ID {persistent_identifier} not found.")
                counters['Dataset Not Found'] += 1
            elif response.status_code == 400:
                error_message = response.json().get('message', 'Bad Request')
                if "Requested version not found" in error_message:
                    LOGGER.error(f"Error: version {version} of {persistent_identifier} - Bad Request: Requested version not found.")
                    counters['Requested version not found'] += 1
                elif "Version was already submitted for archiving" in error_message:
                    LOGGER.error(f"Error: version {version} of {persistent_identifier} - Bad Request: Version was already submitted for archiving.")
                    counters['Version already submitted'] += 1
                else:
                    LOGGER.error(f"Error: version {version} of {persistent_identifier} - Bad Request: {error_message}")
                    counters['other_errors'] += 1
            else:
                LOGGER.error(f"Error: version {version} of {persistent_identifier} - Status code: {response.status_code}")
                counters['other_errors'] += 1
        except requests.ConnectionError:
            LOGGER.error(f"Error: version {version} of {persistent_identifier} - Connection refused: Failed to connect to server")
            counters['connection_errors'] += 1
        except requests.RequestException as e:
            LOGGER.error(f"Error: version {version} of {persistent_identifier} - {e}")
            counters['other_errors'] += 1

    return counters



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate DOIs in a file.")
    parser.add_argument("file_path", type=str, help="The path to the file to be validated")
    parser.add_argument("--config_path", type=str, default="config/config.ini",
                        help="The path to the config file (default: config/config.ini)")
    parser.add_argument("-b", "--build_number", type=str, default=datetime.now().strftime("%Y-%m-%d-%H%M"),
                        help="Build number (default: current timestamp)")
    args = parser.parse_args()

    read_config(args.config_path)

    if not API_TOKEN:
        print("Error: The 'api_token' value in the config file is empty. Please provide a valid API token.")
        sys.exit(1)

    LOGGER = setup_logger(args.build_number)
    LOGGER.info("Script started.")

    ids = validate_identifier_version(args.file_path)

    if ids:
        print("Valid DOIs:")
        for doi in ids:
            print(doi)

    counters = submit_baggit_archive(ids)
    LOGGER.info(counters)

    with open('archive_counters.txt', 'w') as file:
        non_zero_counters = [f"{key}: {value}" for key, value in counters.items() if value > 0]
        file.write(', '.join(non_zero_counters))

    if any(key not in ['baggit request success', 'Version already submitted'] and value > 0 for key, value in
           counters.items()):
        sys.exit(311)

    LOGGER.info("Script completed.")
