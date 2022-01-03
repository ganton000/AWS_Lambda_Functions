
import boto3 #The AWS SDK library for Python
import json

#Insert elements into already existing table "BankAccounts" on DynamoDB.


ddb = boto3.resource('dynamodb')

table = ddb.Table('BankAccounts')

