#Lambda example found on StackExchange performing Data dip from DynamoDB.

import boto3
import json
from boto3.dynamodb.conditions import Key, Attr

def lambda_handler(event, context):
    print("Lambda Trigger event: " + json.dumps(event))

    try:

        phoneNumber = event['Details']['ContactData']['CustomerEndpoint']['Address']
        print("Customer Phone Number : " + phoneNumber)

        dynamodb = boto3.resource('dynamodb',region_name='ap-southeast-2')

        table = dynamodb.Table('data_dip_table')

        response = table.get_item(Key={
                                'phone-number': phoneNumber
                                })
        print("dynamodb response: " + json.dumps(response))

        if 'Item' in response:
            # TODO: Match Found
            print("Phone number match found!")

            firstName = response['Item']['first-name']
            print("Customer First Name: " + firstName)

            welcomeMessage = 'Welcome' + firstName + ' to Our data dip'
            print("welcome message :" + welcomeMessage)

            return {'welcomeMessage' : welcomeMessage }

        else:
            print("Phone Number was not Found")

            return { 'welcomeMessage' : 'Welcome!' }

    except Exception as e:
        print("An Error Has Occurred")
        print(e)
        return {'welcomeMessage' : 'Welcome !'}

