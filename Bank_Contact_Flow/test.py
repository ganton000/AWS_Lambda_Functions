import boto3


dyn_client = boto3.resource('dynamodb')


table = dyn_client.Table('BankAccounts3')

accountNumber = 462604245119

response = table.get_item(Key={'AccountNumber': accountNumber})

print(accountNumber == response['Item']['AccountNumber'])
