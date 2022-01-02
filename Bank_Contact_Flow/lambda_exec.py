"""
 This code sample demonstrates an implementation of the Lex Code Hook Interface
 in order to serve a bot which manages bank account inquiries.

 For instructions on how to set up and test this bot, as well as additional samples,
 visit the Lex Getting Started documentation http://docs.aws.amazon.com/lex/latest/dg/getting-started.html.
"""



import json
import boto3 
import logging
import random
import math

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)





#Initialize DynamoDB Client
ddb = boto3.resource('dynamodb')

#DynamoDB table
table = ddb.Table('BankAccount3')


""" --- Generic functions used to simplify interaction with Amazon Lex --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

def close(session_attributes, fulfillment_state, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type':'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }



def build_validation_result(is_valid, violated_slot, message_content):

    if message_content is None:
        return {
            "isValid": is_valid, 
            "violatedSlot": violated_slot
        }
    return {
            "isValid": is_valid, 
            "violatedSlot": violated_slot,
            "message": {'contentType':'PlainText','content': message_content}
        }


""" --- Helper Functions --- """

def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None


def get_random_int(minimum, maximum):
    """
    Returns a random integer between min (included) and max (excluded)
    """
    min_int = math.ceil(minimum)
    max_int = math.floor(maximum)

    return random.randint(min_int, max_int - 1)


""" --- Functions that control the bot's behavior --- """

def perform_action(intent_request):

    #Get user message
    user_message = intent_request['inputTranscript']

    response = table.put_item( Key={
            'pass':passed
        })

    print('dynamodb response: ' + json.dumps(response))

def retrieve_inquiry(intent_request):

    #Get Bot Response
    AccountNumber = get_slots(intent_request)['AccountNumber']
    Pin = get_slots(intent_request)['Pin']

    response = table.get_item( Key={

    })

    




def lambda_handler(event, context):


    intent_name = event['currentIntent']['name']

    #get User input/message
    user_message = event['inputTranscript']

    if intent_name == 'AccountLookUp':
        return retrieve_inquiry(event)
    
    elif intent_name == 'ReplaceCard':
        return perform_action(event)
    
    else:
        raise Exception('Intent with name ' + intent_name + ' not supported')
