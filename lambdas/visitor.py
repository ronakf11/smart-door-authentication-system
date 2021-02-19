import json
import boto3
import time
from boto3.dynamodb.conditions import Key, Attr

def lambda_handler(event, context):
    
    # faceId = event["faceId"]
    
    user_otp = event['body'].strip().split('=')[1]
    
    # Connect to dynamoDB
    dynamodb = boto3.resource('dynamodb', "us-east-1") 
    passcodeTableName = 'passcodes'
    table = dynamodb.Table(passcodeTableName)

    response = table.query(
        TableName=passcodeTableName,
        KeyConditionExpression=Key('otp').eq(user_otp)
    )
    
    real_otp = ""
    # is_ttl = False

    if len(response["Items"]) > 0:
        real_otp = response["Items"][0]["otp"]
        # ttl = int(response["Items"][0]['ttl'])
        # if ttl < int(time.time()):
            # is_ttl = True
    
    response_info = {}
    
    if real_otp == user_otp:
        response_info = table.query(
            TableName='visitors',
            KeyConditionExpression=Key('faceId').eq(response["Items"][0]["faceId"])
        )
        
        response_delete = table.delete_item(
            TableName=passcodeTableName,
            Key={
                'otp': real_otp
            }
        )
        username = (response_info['Items'][0]['name'])
        return {
            'statusCode': 200,
            'body': "Welcome, " + username
        }
    
    return {
        'statusCode': 403,
        'body': str("Permission Denied")
    }
