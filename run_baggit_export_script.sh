#!/bin/bash
set -e

# Initialize variables
BUILD=""
UPLOAD_FILEPATH=""
CONF_FILE=""
HELP=""

# Function to display help
display_help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -b, --build_number BUILD_NUMBER     Specify the build number"
    echo "  -f, --upload-file UPLOAD_FILEPATH   Specify the upload file path"
    echo "  -c, --config-file CONF_FILE       Specify the config file path (optional)"
    echo "  -h, --help                   Display this help message"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -b|--build_number)
            BUILD="$2"
            shift 2
            ;;
        -f|--upload-file)
            UPLOAD_FILEPATH="$2"
            shift 2
            ;;
        -c|--config-file)
            CONF_FILE="$2"
            shift 2
            ;;
        -h|--help)
            HELP="true"
            shift
            ;;
        *)
            echo "Error: Invalid option: $1"
            display_help
            ;;
    esac
done

# Display help if requested
if [ -n "$HELP" ]; then
    display_help
fi

# Check if required parameters are provided
if [ -z "$BUILD" ] || [ -z "$UPLOAD_FILEPATH" ]; then
    echo "Error: Both BUILD and UPLOAD_FILEPATH parameters are required"
    display_help
fi

if [ -n "$CONF_FILE" ]; then
    CONFIG_OPTION="--config_path $CONF_FILE"
else
    CONFIG_OPTION=""
fi

# Get the absolute path of the script
SCRIPT=$(readlink -f "$0")
# Get the directory where the script is located
APP_FOLDER=$(dirname "$SCRIPT")

VENV_PATH="venv"

echo " ** Starting baggit export script with following parameters **"
echo "Build Number : $BUILD"
echo "App Path : $APP_FOLDER"
echo "Upload file path : $UPLOAD_FILEPATH"
echo -e "\n\n"

cd "$APP_FOLDER" || exit 1
echo "Creating/Updating python virtual environment"
/bin/python3 -m venv "$VENV_PATH" || exit 1
./"$VENV_PATH"/bin/pip3 install -r requirements.txt || exit 1
if [ $? = 1 ]; then
    exit 1
fi

./"$VENV_PATH"/bin/python3 -u "$APP_FOLDER"/main.py $CONFIG_OPTION -b "$BUILD" "$UPLOAD_FILEPATH" || exit 1
if [ $? -ne 0 ]; then
    exit 1
fi

echo "<<<< RUN COMPLETED! >>>>"
exit 0
