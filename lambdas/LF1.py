import boto3
import json
from datetime import datetime
import time
import random
import string
import cv2
from boto3.dynamodb.conditions import Key, Attr
import logging
import uuid
import base64
import os

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

session = boto3.Session()
credentials = session.get_credentials()
region = session.region_name
s3 = boto3.client('s3')
kvs = boto3.client('kinesisvideo',region_name=region)
sns = boto3.client('sns')
dynamo = boto3.resource('dynamodb', region_name=region)
dynamo_visitors = dynamo.Table('visitors')
dynamo_passcodes = dynamo.Table('passcodes')
s3photobucket = 'csgy9223a-a2-visitorphotos'
kvsStreamARN = 'arn:aws:kinesisvideo:us-east-1:456240511584:stream/kvs1/1604348007888'
ownerNumbers = [
    '+17181234567',
    '+16461234567'
]

def queryDB2(faceId):
    # search the visitors table for a row matching the faceId
    res = dynamo_visitors.query(
        KeyConditionExpression=Key('faceId').eq(faceId)
    )
    print(res)

    if res['Count'] > 0:
        return res['Items'][0]
    else:
        return None

def generate_otp(n):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))

def putDB1(faceId, otp):
    # put One Time Passcode for faceId with TTL into passcode DB
    res = dynamo_passcodes.put_item(
        Item = {
            'otp': str(otp),
            'faceId': faceId,
            'current_time': int(time.time()),
            'expiration_time': int(time.time() + 5 * 60)
        }
    )
    
    return None

def updateDB2(visitor, faceId, imgName):
    # update the row matching the faceId
    # the new picture(s) will be appended to the photos list
    visitor_photos = visitor['photos']

    photos = {
        'objectKey': imgName,
        'bucket': s3photobucket,
        'createdTimestamp': time.strftime("%Y-%m-%dT%H:%M:%S")
    }

    visitor_photos.append(photos)
    dynamo_visitors.delete_item(
        Key = {
            'faceId': faceId
        }
    )

    res = dynamo_visitors.put_item(
        Item = {
            'faceId': faceId,
            'name': visitor['name'],
            'phoneNumber': visitor['phoneNumber'],
            'photos': visitor_photos
        }
    )
    
    return None

def sendSNS(number, msg):
    # send message to either vistor or owner
    # if visitor, message will be the OTP
    # if owner, the message will be a link to the vistor photo
    res = sns.publish(
        PhoneNumber=number,
        Message=msg,
        MessageAttributes = {
            'AWS.SNS.SMS.SMSType': {
                'DataType': 'String',
                'StringValue': 'Transactional'
            }    
        }
    )
    print(res)

def lambda_handler(event, context):
    os.environ['TZ'] = 'US/Eastern'
    time.tzset()

    # kinesis triggers event
    record = event['Records'][0]
    payload = base64.b64decode(record["kinesis"]["data"])
    faceinfo = json.loads(payload.decode('utf-8'))

    # rekognition populates FaceSearchReponse with face data
    faces = faceinfo["FaceSearchResponse"]
    faceId = ''
    frameCaptured = False
    imgName = 'kvs1_'

    # there may be multiple faces in the FaceSearchResponse as there may be more than one person 'at the door'
    for face in faces:
        # unknown visitors will have 'newFace<timestamp>' appended to their photo in the s3 visitor bucket
        externalImageId = 'newFace'# + time.strftime("%Y%m%d-%H%M")

        # check to see if there are any matching faces
        # MatchedFaces is populated by rekognition based on the currently indexed faces within the collection
        for match in face["MatchedFaces"]:
            faceId = match["Face"]["FaceId"]
            externalImageId = match["Face"]["ExternalImageId"]

        #  take video stream and turn into a picture of the visitor
        if 'InputInformation' in faceinfo:
            # data within kinesis video stream
            fragment = faceinfo['InputInformation']['KinesisVideo']['FragmentNumber']

            # get endpoint for a specified stream for reading
            res = kvs.get_data_endpoint(
                StreamARN = kvsStreamARN,
                APIName = 'GET_MEDIA'
            )

            endpt = res['DataEndpoint']

            # retrieve media content from a kinesis video stream
            # the starting chunk is after the specified fragment
            kvsmedia = boto3.client('kinesis-video-media', endpoint_url = endpt, region_name = region)
            stream = kvsmedia.get_media(
                StreamARN = kvsStreamARN,
                StartSelector = {
                    'StartSelectorType': 'FRAGMENT_NUMBER',
                    'AfterFragmentNumber': fragment
                }
            )

            # use OpenCV to capture video and save as image within s3 bucket
            with open('/tmp/stream.mkv', 'wb') as tmpfile:
                streamBody = stream['Payload'].read(1024*16384)
                tmpfile.write(streamBody)
                cap = cv2.VideoCapture('/tmp/stream.mkv')

                # Capture frame-by-frame
                success, frame = cap.read()
                if frame is not None:
                    # Display the resulting frame
                    cap.set(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)/2)-1)
                    imgName = imgName + externalImageId + '_' + time.strftime("%Y%m%d-%H%M") + '.jpg'
                    cv2.imwrite('/tmp/' + imgName, frame)
                    s3.upload_file(
                        '/tmp/' + imgName,
                        s3photobucket,
                        imgName,
                        ExtraArgs = {
                            'ContentType': 'image/jpeg'
                        }
                    )
                    cap.release()
                    print('Image uploaded :', imgName)
                    frameCaptured = True
                    break
                else:
                    print("Frame is None")
                    break
        break

    # OpenCV captured a frame or there was a matched faceId
    if frameCaptured or faceId:
        # visitor was recognized
        # need to update visitors table with the new picture(s)
        # create One Time Password and put it into the passcodes table for the corresponding visitor's faceId
        # send SMS to visitor of OTP
        if faceId != '':
            visitor = queryDB2(faceId)
            print(visitor)
            if visitor:
                OTP = generate_otp(6)
                #OTP = str(uuid.uuid1())
                updateDB2(visitor, faceId, imgName)
                putDB1(faceId, OTP)
                phoneNumber = visitor['phoneNumber']
                message = 'Enter your one time passcode {} here - http://a2-smart-door.s3-website-us-east-1.amazonaws.com/auth.html'.format(str(OTP))
                sendSNS(phoneNumber, message)
                print('sms sent to visitor', str(phoneNumber))
        else:
            message = 'Unrecognized visitor appeared https://{}.s3.amazonaws.com/{}. Approve or deny access at https://a2-smart-door.s3.amazonaws.com/index.html?imgname={}'.format(s3photobucket, imgName, imgName)
            sendSNS(random.choice(ownerNumbers), message)
            print('sms sent to owner')
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
