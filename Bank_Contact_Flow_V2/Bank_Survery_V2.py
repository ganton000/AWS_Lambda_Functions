import json
import os
import time
import boto3
import logging
import random
from decimal import Decimal


#Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


#Initialize DynamoDB resource
ddb = boto3.resource('dynamodb')
table_name = ''



""" --- Generic functions used to simplify interaction with Amazon Lex --- """

def get_slots(intent_request):
    return intent_request['sessionState']['intent']['slots']

def get_slot(intent_request, slotName):
    slots = get_slots(intent_request)
    if slots is not None and slotName in slots and slots[slotName] is not None:
        return slots[slotName]['value']['interpretedValue']
    else:
        return None 

def get_session_attributes(intent_request):
    sessionState = intent_request['sessionState']
    if 'sessionAttributes' in sessionState:
        return sessionState['sessionAttributes']
    
    return {}

def elicit_intent(intent_request, session_attributes, message):
    '''Re-prompts user for intent information'''
    return {
        'sessionState':{
            'dialogAction':{
                'type':'ElicitIntent'
            },
            'sessionAttributes': session_attributes
        },
        'messages': [message] if message != None else None,
        'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
    }

def close(intent_request, session_attributes, fulfillment_state, message):
    '''Closes/Ends current Lex session with customer'''

    intent_request['sessionState']['intent']['state'] = fulfillment_state
    return {
        'sessionState':{
            'sessionAttributes': session_attributes,
            'dialogAction':{
                'type':'Close'
            },
            'intent': intent_request['sessionState']['intent']
        },
        'messages': [message],
        'sessionId': intent_request['sessionId'],
        'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
    }

''' --- Validation Functions --- '''

def build_validation_result():
    pass 




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





""" --- Functions that control the bot's behavior --- """

def CheckBalance(intent_request):
    pass





''' --- INTENTS --- '''


def dispatch(intent_request):

    intent_name = intent_request['sessionState']['intent']['name']

    #Dispatch to bot's intent handlers
    if intent_name == 'CheckBalance':
        return CheckBalance(intent_request)


''' --- MAIN handler --- '''



def lambda_handler(event, context):
    
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()

    return dispatch(event)