#!/bin/bash
set -e

# Parameters Passed
BUILD=$1
UPLOAD_FILEPATH=$2
CONF_FILE=$3

if [ -z "$BUILD" ] || [ -z "$UPLOAD_FILEPATH" ]
then
  echo "Error: Both BUILD and UPLOAD_FILEPATH parameters are required"
  exit 1
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
#echo "Updating following file from uploaed CSV file | fileId,Location|"
#cat $UPLOAD_FILEPATH
echo -e "\n\n"

cd $APP_FOLDER || exit 1
echo "Creating/Updating  python virtual environment"
/bin/python3 -m venv $VENV_PATH || exit 1
./$VENV_PATH/bin/pip3 install -r requirements.txt || exit 1
if [ $? = 1 ]
then
  exit 1
fi

./$VENV_PATH/bin/python3 -u $APP_FOLDER/main.py $CONFIG_OPTION  -b $BUILD $UPLOAD_FILEPATH || exit 1
if [ $? -ne 0 ]
then
  exit 1
fi
echo "<<<< RUN SUCCESSFULLY COMPLETED! >>>>"
exit 0
