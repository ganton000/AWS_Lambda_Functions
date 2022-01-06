# import json
import os
import time
import boto3
import logging
from decimal import Decimal


#Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


#Initialize DynamoDB resource
dyn_resource = boto3.resource('dynamodb')
tbl_name = 'BankAccountsNew'


""" --- Generic functions used to simplify interaction with Amazon Lex --- """

def get_slots(intent_request):
    return intent_request['sessionState']['intent']['slots']


# def get_slot(intent_request, slotName):
#     slots = try_ex(lambda: get_slots(intent_request))
#     if slots is not None and slotName in slots and slots[slotName] is not None:
#         return slots[slotName]['value']['interpretedValue']
#     else:
#         return None 


def get_session_attributes(intent_request):
    sessionState = intent_request['sessionState']
    if 'sessionAttributes' in sessionState:
        return sessionState['sessionAttributes']
    
    return {}



def close(intent_name, session_attributes, fulfillment_state, message):
    '''Closes/Ends current Lex session with customer'''

    response = {
        'sessionState':{
            'sessionAttributes': session_attributes,
            'dialogAction':{
                'type':'Close'
            },
            'intent': {
                'name': intent_name,
                'state': fulfillment_state
            },
        'messages': [message]
        }
    }
    
    return response


def elicit_intent(session_attributes, message):
    '''Informs Amazon Lex that the user is expected to respond with an utterance that includes an intent. '''
    
    return {
        'sessionState':{
            'dialogAction':{
                'type':'ElicitIntent'
            },
            'sessionAttributes': session_attributes
        },
        'messages': [message] if message != None else None
    }


def confirm_intent(session_attributes, intent_name, slots, message):
    '''Informs Amazon Lex that the user is expected to give a yes or no answer to confirm or deny the current intent'''
    return {
        'messages': [
            message
        ],
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'ConfirmIntent'
            },
            'intent': {
                'name': intent_name,
                'slots': slots
            }
        }
    }


def elicit_slot(intent_name, slots, violated_slot, session_attributes, message):
    '''Re-prompts user to provide a slot value in the response'''
    return {
        'sessionState':{
            'sessionAttributes': session_attributes,
            'dialogAction':{
                'slotToElicit': violated_slot,
                'type':'ElicitSlot'
            },
            'intent':{
                'confirmationState': 'Denied',
                'name':intent_name,
                'slots':slots,
                'state':'InProgress'
            }
        },
        'messages': [message] if message != None else None
    }


def delegate(intent_name, slots, session_attributes):
    '''Directs Amazon Lex to choose the next course of action based on the bot configuration. '''
    return {
        'sessionState':{
            'sessionAttributes': session_attributes,
            'dialogAction':{
                'type':'Delegate'
            },
            'intent':{
                'name':intent_name,
                'slots': slots
            }
        }
    }


''' --- Validation Functions --- '''

def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            'isValid': is_valid,
            'violatedSlot': violated_slot
        }
    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message':{
            'contentType':'PlainText',
            'content': message_content
        }
    }

def isValid_Word(word):

    if word:
        try:
            if word.isalpha(): 
                return True
        except ValueError:
            return False

    return False

def isValid_Pin(pin):
    
    if pin:
        try:
            pin = str(pin)
            logger.info(f'isValid PinNumber={pin}')
            if (pin.isnumeric() == 1) & (len(pin) == 4): 
                return True
        except ValueError:
            return False
    
    return False

def isValid_AccountNumber(accountNumber):

    if accountNumber is not None:
        try:
            accountNumber = str(accountNumber)
            logger.info(f'isValid AccountNumber={accountNumber}')
            if (len(accountNumber) == 12) & (accountNumber.isnumeric() == 1):
                return True
        except ValueError:
            return False
            
    return False


def isValid_AccountType(accountType):

    account_types = ['checking', 'savings', 'checkings','saving']

    return accountType.lower() in account_types



def validate_balance_information(slots):

    table_name = tbl_name 

    #Get slots
    accountType = try_ex(lambda: slots['accountType'])
    accountNumber = try_ex(lambda: slots['accountNumber'])
    pin = try_ex(lambda: slots['pin'])

    logger.info(f'accountType={accountType}, accountNumber={accountNumber}, pin={pin}')


    if accountType and not isValid_AccountType(accountType['value']['interpretedValue']):
        return build_validation_result(
            False,
            'accountType',
            'Sorry I did not understand. Would you like to get the account balance for your Checking or Savngs account?'
        )
    
    if accountNumber:
        if not isValid_AccountNumber(accountNumber['value']['interpretedValue']):
            return build_validation_result(
                False,
                'accountNumber',
                f'Sorry I did not understand. Please enter your twelve digit {accountType} account number'
            )
        if not validate_account_dynamodb(table_name, accountNumber['value']['interpretedValue']):
            return build_validation_result(
                False,
                'accountNumber',
                'Sorry but the account number {} does not exist in our database. Please enter your twelve digit account number.'.format(accountNumber['value']['interpretedValue'])
            )
    
    if pin:
        user_pin = pin['value']['interpretedValue']
        if not isValid_Pin(user_pin):
            return build_validation_result(
                False,
                'pin',
                'Sorry I did not understand. Please enter your four digit pin number.'
            )
        if user_pin != get_item_dynamodb(table_name, accountNumber, 'Pin'):
            return build_validation_result(
                False,
                'pin',
                f'Sorry but the pin number {user_pin} is incorrect. Please enter your four digit pin number'
            )
    
    return {'isValid':True}


    
""" --- Helper Functions --- """

def get_item_dynamodb(table_name, accountNumber, query_params):
    '''retrieves element from DynamoDB'''

    table = dyn_resource.Table(table_name)
    
    if (accountNumber is None) | (query_params is None): return False

    try:
        response = table.get_item(Key={
            'AccountNumber': Decimal(accountNumber)
        })['Item']
    except KeyError:
        return False

    return response[query_params]

def write_item_dynamodb(table_name, items):
    '''Inserts element into DynamoDB'''

    from botocore.exceptions import ClientError

    table = dyn_resource.Table(table_name)

    try:
        response = table.put_item(Item=items)
    except ClientError as err:
        if err.response['Error']['Code'] == 'InternalError':
            logger.info('Error Message: {}'.format(err.response['Error']['Message']))
        else:
            raise err

    return True
    

def validate_account_dynamodb(table_name, accountNumber):
    '''Checks if account number exists in DynamoDB'''
    
    if accountNumber is None: return False

    table = dyn_resource.Table(table_name)

    try:
        response = table.get_item(Key={
            'AccountNumber': Decimal(accountNumber)
        })['Item']
    except KeyError:
        return False

    return True



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


    table_name = tbl_name

    #Initialize required response parameters
    intent_name = intent_request['sessionState']['intent']['name']
    session_attributes = get_session_attributes(intent_request)
    source = intent_request['invocationSource']
    confirmation_status = intent_request['sessionState']['intent']['confirmationState']
    slots = get_slots(intent_request)

    logger.info(f'source={source}, slots={slots}, confirmation_status={confirmation_status}')


    #Get slot values
    accountType = slots['accountType']
    accountNumber = slots['accountNumber']
    pin = slots['pin']

    logger.info(f'accountType={accountType}, accountNumber={accountNumber}, pin={pin}')




    if source == 'DialogCodeHook':
        # Valdiate any slots which have been specified. If any are invalid, re-elicit for their value.
        validation_result = validate_balance_information(slots)
        logger.info(f'validation_result={validation_result}')
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] == None
            logger.debug(f'slots={slots}')
            logger.info('violatedSlot={}, message={}'.format(validation_result['violatedSlot'], validation_result['message']))
            return elicit_slot(
                intent_name,
                slots,
                validation_result['violatedSlot'],
                session_attributes,
                validation_result['message']
            )
        
        return delegate(intent_name,intent_request['sessionState']['intent']['slots'] ,session_attributes)

    
    balance = get_item_dynamodb(table_name, accountNumber['value']['interpretedValue'], 'Account Balance')
    logger.info(f'balance={balance}')

    output1 = 'The balance on your {} account is ${:,.2f} dollars. '.format(accountType['value']['interpretedValue'],balance)
    output2 = 'Thank you for banking with Example Bank. We appreciate your business. '
    output3= 'Please stay on the line if you would like to take out customer experience survey.'
    output = output1+output2+output3
    message = {
        'contentType':'PlainText',
        'content': output
    }
    fulfillment_state = 'Fulfilled'
    
    logger.info(f'fulfillment_state={fulfillment_state}')
    
    return close(intent_name, session_attributes, fulfillment_state, message)


def FollowupCheckBalance(intent_request):
    pass


def ReplaceCard(intent_request):
    pass



''' --- INTENTS --- '''


def dispatch(intent_request):

    intent_name = intent_request['sessionState']['intent']['name']
    
    logger.info(f'intent_name={intent_name}')
    

    #Dispatch to bot's intent handlers
    if intent_name == 'CheckBalance':
        return CheckBalance(intent_request)
    elif intent_name == 'FollowupCheckBalance':
        return FollowupCheckBalance(intent_request)
    elif intent_name == 'ReplaceCard':
        return ReplaceCard(intent_request)


''' --- MAIN handler --- '''



def lambda_handler(event, context):
    
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()

    bot_name = event['bot']['name']
    userMessage = event['inputTranscript'] #string
    inputType = event['inputMode'] #DTMF | Speech | Text
    

    logger.info(f'event.bot.name={bot_name}, userMessage={userMessage}, inputType={inputType}')


    return dispatch(event)
