import json
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


def get_slot(intent_request, slotName):
    slots = try_ex(lambda: get_slots(intent_request))
    if slots is not None and slotName in slots and slots[slotName] is not None:
        return slots[slotName]['value']['interpretedValue']
    else:
        return None 


def get_session_attributes(intent_request):
    sessionState = intent_request['sessionState']
    if 'sessionAttributes' in sessionState:
        return sessionState['sessionAttributes']
    
    return {}



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

def elicit_intent(intent_request, session_attributes, message):
    '''Informs Amazon Lex that the user is expected to respond with an utterance that includes an intent. '''
    
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

def confirm_intent(intent_request, session_attributes, message):
    '''Informs Amazon Lex that the user is expected to give a yes or no answer to confirm or deny the current intent'''
    return {
        'sessionState':{
            'dialogAction':{
                'type':'ConfirmIntent'
            },
            'sessionAttributes': session_attributes
        },
        'messages': [message] if message != None else None,
        'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
    }


def elicit_slot(intent_request, intent_name, slots, violated_slot, session_attributes, message):
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
        'messages': [message] if message != None else None,
        'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
    }


def delegate(intent_request, session_attributes):
    '''Directs Amazon Lex to choose the next course of action based on the bot configuration. '''
    return {
        'sessionState':{
            'sessionAttributes': session_attributes,
            'dialogAction':{
                'type':'Delegate'
            }
        },
        'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
    }



##Possible delegate function:

# def delegate(intent_request, intent_name, slots, session_attributes):
#     '''Directs Amazon Lex to choose the next course of action based on the bot configuration. '''
#     return {
#         'sessionState':{
#             'sessionAttributes': session_attributes,
#             'dialogAction':{
#                 'type':'Delegate'
#             },
#             'intent':{
#                 'confirmationState': 'Confirmed',
#                 'name':intent_name,
#                 'slots':slots,
#                 'state':'ReadyForFulfillment'
#             }
#         },
#         'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
#     }


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
    
    if pin is not None:
        try:
            pin = str(pin)
            if (pin.isnumeric() == 1) & (len(pin) == 4): 
                return True
        except ValueError:
            return False
    
    return False

def isValid_AccountNumber(accountNumber):

    if accountNumber is not None:
        try:
            accountNumber = str(accountNumber)
            if (len(accountNumber) == 12) & (accountNumber.isnumeric() == 1):
                return True
        except ValueError:
            return False
            
    return False


def isValid_AccountType(accountType):

    if accountType is not None & (accountType.lower() in ['checking', 'savings', 'checkings','saving']):
        return True
    
    return False


def validate_balance_information(accountType, accountNumber, pin):


    if not isValid_AccountType(accountType):
        return build_validation_result(False, 'accountType', 'Sorry I did not recognize that, please enter or say your twelve digit account number.')

    if not isValid_AccountNumber(accountNumber):
        return build_validation_result(False, 'accountNumber', 'Sorry I did not recognize that, please enter or say your twelve digit account number.')
    
    if not isValid_Pin(pin):
        return build_validation_result(False, 'pin', 'Sorry I did not recognize that, please enter or say your pin number.')

""" --- Helper Functions --- """

# def mapping_string_to_numeric(word):

#     #Create mapping 
#     dict_keys = [['a','b','c'], ['d','e','f'], ['g','h','i'], ['j','k','l'], ['m','n','o'],
#     ['p','q','r','s'], ['t','u','v'], ['w','x','y','z']]
    
#     mapping = {}

#     for keys,vals in zip(dict_keys, range(2,10)):
#         mapping.update(dict.fromkeys(keys, str(vals)))

#     res = ''
#     for i in word:
#         res += mapping[i.lower()]

#     return res


def get_item_dynamodb(table_name, accountNumber, query_params):
    '''retrieves element from DynamoDB'''

    table = dyn_resource.Table(table_name)

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


    #dynamodb table name
    table_name = 'BankAccountsNew'

    #Initialize required response parameters
    intent_name = intent_request['sessionState']['intent']['name']
    session_attributes = get_session_attributes(intent_request)
    slots = get_slots(intent_request)

    logger.info(f'slots={slots}')
    
    #text = 'Thank you for choosing National Bank. Please tell us for which account would you like your balance?'
    #elicit_slot(intent_request, intent_name, slots, 'None', session_attributes, text)
    #delegate(intent_request, session_attributes)
    


    #Get slot values
    accountType = get_slot(intent_request, 'accountType')
    accountNumber = get_slot(intent_request, 'accountNumber')
    pin = get_slot(intent_request, 'pin')

    logger.info(f'accountType={accountType}, accountNumber={accountNumber}, pin={pin}')
    

    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        validation_result = validate_balance_information(accountType, accountNumber, pin)
        logger.info(f'validation_result={validation_result}')
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] == None
            logger.info('violatedSlot={}, message={}'.format(validation_result['violatedSlot'], validation_result['message']))
            return elicit_slot(
                intent_request,
                intent_name,
                slots,
                validation_result['violatedSlot'],
                session_attributes,
                validation_result['message']
            )
    
        return delegate(intent_request, session_attributes)
        #return delegate(intent_request, intent_name, slots, session_attributes)


    #Validation of user data with database values
    num_to_validate = get_item_dynamodb(table_name, accountNumber, 'AccountNumber')
    if not (accountNumber == num_to_validate):
        logger.info(f'accountNumber input={accountNumber}, acct_num_to_validate={num_to_validate}')
        validation_result = build_validation_result(False, 'accountNumber', f'The account number {accountNumber} does not exist in our database. Goodbye')
        fulfillment_state = 'Failed'
        return close(
            intent_request,
            session_attributes,
            fulfillment_state,
            validation_result['message']
            )
    num_to_validate = get_item_dynamodb(table_name, accountNumber, 'Pin')
    if not (pin == num_to_validate):
        logger.info(f'pin number input={pin}, pin_to_validate={num_to_validate}')
        validation_result = build_validation_result(False, 'pin', f'The pin number {pin} does not exist in our database. Goodbye.')
        fulfillment_state = 'Failed'
        return close(
            intent_request,
            session_attributes,
            fulfillment_state,
            validation_result['message']
            )

        


    
    balance = get_item_dynamodb(table_name, accountNumber, 'Account Balance')
    logger.info(f'balance={balance}')

    output_response = f'Thank you. The balance on your {accountType} account is {balance} dollars.'
    message = {
        'contentType':'PlainText',
        'content': output_response
    }
    fulfillment_state = 'Fulfilled'
    
    logger.info(f'fulfillment_state={fulfillment_state}')

    return close(intent_request, session_attributes, fulfillment_state, message)


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