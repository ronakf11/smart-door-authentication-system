#!/usr/bin/bash
ARG1=${1:-myphoto}
ARG2=${2:-externalImageName}
ARG3=${3:-csgy9223a-a2-visitorphotos}
ARG4=${4:-smartDoor}
ARG5=${5:-us-east-1}

aws rekognition index-faces --image "{\"S3Object\": {\"Bucket\":\"$ARG3\",\"Name\":\"$ARG1.jpg\"}}" --collection-id $ARG4 --detection-attributes "ALL" --external-image-id $ARG2 --region $ARG5