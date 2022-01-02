
# resource: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html
# resource: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GettingStarted.Python.html


import boto3 #The AWS SDK library for Python
import json

#Create table named BankAccounts

def create_bank_accounts_table(table_name):

    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    table = dynamodb.create_table(
    TableName=table_name,
    KeySchema=[ #Key schema specifies attributes that make up primary key of table
        { 
            'AttributeName': 'AccountNumber',
            'KeyType':'HASH' #Partition Key
        }
    ], 
    AttributeDefinitions=[ #Attributes for table keys
        { 
            'AttributeName': 'AccountNumber',
            'AttributeType': 'N'
        }
    ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 5, #The maximum number of strongly consistent reads consumed per second 
        #before DynamoDB returns a ThrottlingException
        'WriteCapacityUnits':5 #The maximum number of writes consumed per second 
        #before DynamoDB returns a ThrottlingException
    })
    
    return table


ddb = boto3.resource('dynamodb')

table_name = 'BankAccounts3'
try:
    bank_table = create_bank_accounts_table(table_name)
    print('Created Table', table_name)
except:
    bank_table = ddb.Table(table_name)
    print('Table already exists. Table status:', bank_table.table_status)
