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




""" --- Generic functions used to simplify interaction with Amazon Lex --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    ''' 
    Informs Amazon Lex that the user is expected to provide a slot value in the response.
    '''

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
    '''
    'dialogAction':{'type':'Close'} informs Amazon Lex not to expect a response from the user. 
    For example, "Your pizza order has been placed" does not require a response.
    '''

    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type':'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

def delegate(session_attributes, slots):
    '''
    Directs Amazon Lex to choose the next course of action based on the bot configuration. 
    If the response does not include any session attributes Amazon Lex retains the existing attributes. 
    If you want a slot value to be null, you don't need to include the slot field in the request
    You will get a DependencyFailedException exception if your fulfillment function 
    returns the Delegate dialog action without removing any slots.
    '''

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


# def get_random_int(minimum, maximum):
#     """
#     Returns a random integer between min (included) and max (excluded)
#     """
#     min_int = math.ceil(minimum)
#     max_int = math.floor(maximum)

#     return random.randint(min_int, max_int - 1)

def isValid_Name(name):
    try:
        if name.isalpha(): 
            return True
    except ValueError:
        return False

def isValid_Pin(pin):
    try:
        pin = str(pin)
        if (pin.isnumeric()) & (len(pin) == 4): 
            return True
    except ValueError:
        return False


def validate_replace_card_information(firstName, lastName, pin):

    if not isValid_Name(firstName):
        return build_validation_result(False, 'First Name', 'I did not recognize that, please enter your first name.')

    elif not isValid_Name(lastName):
        return build_validation_result(False, 'Last Name', 'I did not recognize that, please enter your last name.')

    elif not isValid_Pin(pin):
        return build_validation_result(False, 'Pin', 'I did not recognize that, pleae enter your pin.')
    
    return build_validation_result(True, None, None)

def query(AccountNumber, query_params):

    from botocore.exceptions import ClientError

    #Initialize DynamoDB Client
    ddb = boto3.resource('dynamodb')

    #DynamoDB table
    table = ddb.Table('BankAccounts3')

    try:
        response = table.get_item(Key={
            'AccountNumber': AccountNumber 
            })
    except ClientError as e:
        return build_validation_result(False, query_params, e.response['Error']['Message'])
        #return build_validation_result(False, query_params, 'There does not exist such a {} in our database.'.format(query_params))
    
    return response[query_params]

def update_accountNumber(accountNumber, new_accountNumber):

    from botocore.exceptions import ClientError

    ddb = boto3.resource('dynamodb')

    table = ddb.Table('BankAccounts3')

    try:
        response = table.update_item(Key={
            'AccountNumber': accountNumber 
            },
            UpdateExpression="set info.AccountNumber",
            ExpressionAttributeValues={new_accountNumber}
            )

    except ClientError as e:
        return build_validation_result(False, None, e.response['Error']['Message'])
        #return build_validation_result(False, query_params, 'There does not exist such a {} in our database.'.format(query_params))
    
    return response['AccountNumber']


""" --- Functions that control the bot's behavior --- """

def replace_card(intent_request):

    """
    Performs dialog management and fulfillment for replacing a card.
    """

    accountNumber = int(intent_request['inputTranscript'])

    #Initialize slot information
    firstName = intent_request['currentIntent']['slots']['FirstName']
    lastName = intent_request['currentIntent']['slots']['LastName']
    pin = intent_request['currentIntent']['slots']['Pin']


    source = intent_request['invocationSource']
    output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}


    logger.debug('output_session_attributes={}, source={}'.format(output_session_attributes, source))


    if source == 'DialogCodeHook':

        #Perform basic validation on the supplied input slots
        slots = intent_request['currentIntent']['slots']
        validation_result = validate_replace_card_information(firstName, lastName, pin)

        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                output_session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        #Perform identity validation on supplied input slots with database

        if firstName != query(accountNumber, 'FirstName'):
            validation_result = build_validation_result(False, 'FirstName', 'The first name {} does not exist in our database.'.format(firstName))
            return elicit_slot(
                output_session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )
        
        if lastName != query(accountNumber, 'LastName'):
            validation_result = build_validation_result(False, 'LastName', 'The last name {} does not exist in our database.'.format(lastName))
            return elicit_slot(
                output_session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        if pin != query(accountNumber, 'Pin'):
            validation_result = build_validation_result(False, 'Pin', 'The pin number {} does not exist in our database.'.format(pin))
            return elicit_slot(
                output_session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )
        
        #Create new Debit Account Number and Update it in Database

    new_accountNumber = random.randint(100000000000, 1000000000000 - 1)
        
    response = update_accountNumber(accountNumber, new_accountNumber)

    if new_accountNumber != response:
        return build_validation_result(False, None, 'Error updating Database')
        
    logger.info('Updated Account Number to: {}'.format(new_accountNumber))

    return close(
        output_session_attributes,
        'Fulfilled',
        {
            'contentType':'PlainText',
            'content': 'Okay, we have mailed out your new debit card to your current address. Please expect it in five to seven business days.'
        }
    )




    response = table.put_item( Key={
            'pass':passed
        })

    print('dynamodb response: ' + json.dumps(response))




def retrieve_inquiry(intent_request):
    '''
    Performs dialog management and fulfillment for account lookup.
    '''
    pass


""" --- Intents --- """

def dispatch(intent_request):
    '''
    Called when the user specifies an intent for this bot.
    '''

    logger.debug('dispatch userId= {}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    #Dispatch to your bot's intent handlers

    if intent_name == 'AccountLookUp':
        return retrieve_inquiry(intent_request)
    
    elif intent_name == 'ReplaceCard':
        return replace_card(intent_request)
    
    else:
        raise Exception('Intent with name ' + intent_name + ' not supported'




""" --- Main handler --- """

def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    """

    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()

    logger.debug('event.bot.name={}, userMessage={}'.format(event['bot']['name'], event['inputTranscript']))

    return dispatch(event)
