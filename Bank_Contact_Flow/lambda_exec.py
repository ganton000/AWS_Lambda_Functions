import json
import boto3 



def get_slots(intent_request):
    return intent_request['currentIntent']['slots']
    
def perform_action(intent_request):

    #retrieve DynamoDB object
    import boto3
    ddb = boto3.resource('dynamodb')
    table = ddb.Table('BankAccount')

    #Get user message
    user_message = intent_request['inputTranscript']

    response = table.put_item( Key={
            '':
        })

    print('dynamodb response: ' + json.dumps(response))

def retrieve_inquiry(intent_request):

    #Get Bot Response
    AccountNumber = get_slots(intent_request)['AccountNumber']
    Pin = get_slots(intent_request)['Pin']

    response = table.get_item( Key={

    })

    




def lambda_handler(event, context):
    #intent_name = event['interpretations']['intent']['name']
    intent_name = event['currentIntent']['name']

    if intent_name == 'AccountLookUp':
        return retrieve_inquiry(event)
    
    elif intent_name == 'ReplaceCard':
        return perform_action(event)
    
    else:
        raise Exception('Intent with name ' + intent_name + ' not supported')





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