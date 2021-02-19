import json
import boto3
import random
import string
import time
import datetime
import uuid
import logging
import os
from botocore.exceptions import ClientError
from urllib.parse import urlparse, parse_qs
import urllib.parse
import time

session = boto3.Session()
credentials = session.get_credentials()
region = session.region_name
dynamo = boto3.resource('dynamodb', region_name=region)
dynamo_visitors = dynamo.Table('visitors')
dynamo_passcodes = dynamo.Table('passcodes')
rek = boto3.client('rekognition')

s3photobucket = 'csgy9223a-a2-visitorphotos'

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.ERROR)
#DB Client
client = boto3.client('dynamodb')
# SNS client
sns_client = boto3.client('sns')

def generate_otp(n):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))

def SMS_to_visitor(name, phoneNumber, faceId):
    # Generate OTP
    OTP = generate_otp(6)
    # put item in passcode table using TTL
    # put One Time Passcode for faceId with TTL into passcode DB
    res = dynamo_passcodes.put_item(
        Item = {
            'otp': str(OTP),
            'faceId': faceId,
            'current_time': int(time.time()),
            'expiration_time': int(time.time() + 5 * 60)
        }
    )
    print('############## putDB1 res: {}'.format(res))
    
    # Send SMS to visitor
    webpage_link = 'http://a2-smart-door.s3-website-us-east-1.amazonaws.com/auth.html'
    text = 'Welcome '+ name +'! Your One-Time Passcode (OTP) is ' + OTP + ' . Please submit your passcode by visiting this link: ' + webpage_link
    LOGGER.info(text)
    response = sns_client.publish(
        PhoneNumber = phoneNumber,
        Message=text,
        MessageAttributes = {
            'AWS.SNS.SMS.SMSType': {
                'DataType': 'String',
                'StringValue': 'Transactional'
            }    
        }
    )

    print(response)
    
    return None

def index_face(imgName, name):
    # detect face from image and add to the specified collection
    res = rek.index_faces(
        CollectionId = "smartDoor",
        DetectionAttributes = [],
        ExternalImageId = name,
        Image = {
            "S3Object": {
                "Bucket": s3photobucket,
                "Name": imgName
            }
        }   
    )
    faceId = res['FaceRecords'][0]['Face']['FaceId']
    return faceId
    print(faceId)
    
    
def store_visitor(name, phoneNumber, faceId, imgName) :
    visitor_photos = []
    photos = {
        'objectKey': imgName,
        'bucket': s3photobucket,
        'createdTimestamp': time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    visitor_photos.append(photos)
    
    res = dynamo_visitors.put_item(
        Item = {
            'faceId': faceId,
            'name': name,
            'phoneNumber': phoneNumber,
            'photos': visitor_photos
        }
    )
    print('############## putDB2 res: {}'.format(res))
    return None
    # Insert a test item into the table
    # try:
    #     response = client.put_item(
    #         Item={
    #             'faceId': {
    #                 'S': faceId   # 'S' stands for String
    #             },
    #             'name': {
    #                 'S': name
    #             },
    #             'phoneNumber': {
    #                 'S': phoneNumber
    #             },
    #             'photos': {
    #                 'L': [          # 'L' stands for list, our sample list contains 
    #                                 # pictures for this person
    #                     {
    #                     'M':        #  'M' stands for map
    #                         {
    #                             'objectKey': imgName,
    #                             'bucket': s3photobucket,
    #                             'createdTimestamp': time.strftime("%Y-%m-%dT%H:%M:%S")
                            
    #                         }
    #                     }
    #                 ]
    #             }
    #         },
    #         TableName='visitors',
    #     )
    #     message = 'Function completed successfully !'
          
    # except ClientError as err:
    #     message = err
    #     LOGGER.error(err)
    # return {
    #     'message' : message
    #     }


def main(event, context): 
    params = parse_qs(event['body'].strip())
    name = params['firstname'][0]
    phoneNumber = params['phone'][0]
    imgName = params['imgname'][0]
    
    faceId = index_face(imgName, name)
    

    # Store visitor information
    response = store_visitor(name, phoneNumber, faceId, imgName)
    
    # Send an SNS message to visitor
    SMS_to_visitor(name, phoneNumber, faceId) 
    
    return {
            'statusCode': 200,
            'body': "visitor has been sent an OTP for access"
        }
        

'''
From Ronak Fofaliya to Everyone:  01:00 PM
if len(response_search['FaceMatches']) == 0:
            response = rekognition_client.index_faces(
                CollectionId='assignment2-collection',
                Image={
                    'S3Object': {
                        'Bucket': 'hw2-photos',
                        'Name': key,
                    },
                },
            )
            logger.info(response)
            if len(response['FaceRecords']) != 0:
                faceId = response['FaceRecords'][0]['Face']['FaceId']
            else:
                logger.info("Cannot index faces of "+key)
                return
        else:
            faceId = response_search['FaceMatches'][0]['Face']['FaceId']


def add_face(s3bucket, collectionID, imgName):
    # detect face from image and add to the specified collection
    res = rek.index_faces(
        CollectionId = collectionID,
        DetectionAttributes = [],
        ExternalImageId = 'myphotoid',
        Image = {
            "S3Object": {
                "Bucket": s3bucket,
                "Name": imgName
            }
        }   
    )

    print(res)
'''
