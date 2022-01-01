import boto3
import random
import json


ddb = boto3.resource('dynamodb')

table = ddb.Table('BankAccounts')


Keys = ['BankAccountID', 'Zipcode', 'LastName', 'FirstName', 'AccountNumber', 'AccountType', 'AccountBalance', 'State', 'City', 'SSN']

AccountID = [ random.randint(1000,9999) for _ in range(10)]
Last_Names = ['Doe', 'Lopez', 'Diaz', 'Williams', 'Chowdhury', 'Lee', 'Napoli', 'Mann', 'Omarion','Lorentz']
First_Names = ['Maria', 'Larry', 'Joe', 'Thomas', 'Laura', 'Ayesha', 'Brian', 'Steven', 'Omar', 'Lorenzo']
Zipcodes = [10043, 11239, 12345, 11239, 11132, 10002, 11111, 12322, 11212, 30050]
AccountNumber = [ random.randint(1000000000,999999999999) for _ in range(10)]
AccountType = [ 'Checking' for _ in range(10)]
AccountBalance = [ random.randint(-10, 1000000) for _ in range(10)]
State = [ 'NY' for _ in range(9)] + ['MA']
City = ['New York' for _ in range(9)] + ['Boston']
SSN = [ random.randint(100000000,199999999) for _ in range(10)]

Vals = [AccountID, Zipcodes, Last_Names, First_Names, AccountNumber, AccountType, AccountBalance, State, City, SSN]

Items = [dict( (k, v[i]) for k,v in zip(Keys,Vals)) for i in range(10)]

#Convert Python list of dictionaries to JSOn string
#and write JSON string to file named bankinput.json

jsonString = json.dumps(Items)
jsonFile = open('bankdata.json','w')
jsonFile.write(jsonString)
jsonFile.close()


with table.batch_writer() as batch:
    for item in Items:
        batch.put_item(Item=item)
