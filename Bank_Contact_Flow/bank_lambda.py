import json
import time
import boto3
import logging
import os
from decimal import Decimal



#Configure Logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


#Initialize DynamoDB Client
dynamodb = boto3.resource('dynamodb')



""" --- Generic functions used to simplify interaction with Amazon Lex --- """


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    ''' 
    Informs Amazon Lex that the user is expected to provide a slot value in the response.
    The intentName, slotToElicit, and slots fields are required. 
    The message and responseCard fields are optional.

    Note: "slots": {
      "slot-name": "value",
      "slot-name": "value",
      "slot-name": "value"  
   },
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


def confirm_intent(session_attributes, intent_name, slots, message):
    '''
    Informs Amazon Lex that the user is expected to give a yes or no answer to confirm or deny the current intent.

    You must include the intentName and slots fields. 
    The slots field must contain an entry for each of the filled slots for the specified intent.
     You don't need to include a entry in the slots field for slots that aren't filled. 
     You must include the message field if the intent's confirmationPrompt field is null.
    '''
    return {
        'sessionAttributes':session_attributes,
        'dialogAction': {
            'type':'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
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

def elicit_intent(session_attributes, content):
    '''
    Informs Amazon Lex that the user is expected to respond with an utterance that includes an intent. 
    For example, "I want a large pizza," which indicates the OrderPizzaIntent. 
    '''

    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitIntent',
            'message':{
                'contentType':'PlainText',
                'content': content
            }
        }
    }

def close(session_attributes, fulfillment_state, message):
    '''
    Informs Amazon Lex not to expect a response from the user. 
    For example, "Your pizza order has been placed" does not require a response.

    The fulfillmentState field is required
    '''

    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type':'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }



''' --- Validation Functions --- '''


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

def isValid_Name(name):

    if name:
        try:
            if name.isalpha(): 
                return True
        except ValueError:
            return False

    return False


def isValid_Pin(pin):
    
    if pin:
        try:
            pin = str(pin)
            if (pin.isnumeric() == 1) & (len(pin) == 4): 
                return True
        except ValueError:
            return False
    
    return False


def isValid_AccountNumber(accountNumber):

    if accountNumber:
        try:
            accountNumber = str(accountNumber)
            if (len(accountNumber) == 12) & (accountNumber.isnumeric() == 1):
                return True
        except ValueError:
            return False
            
    return False

def validate_balance_information(accountNumber, pin):

    if not isValid_AccountNumber(accountNumber):
        return build_validation_result(False, 'AccountNumber', 'I did not recognize that, please enter your twelve digit account number.')

    if not isValid_Pin(pin):
        return build_validation_result(False, 'Pin', 'I did not recognize that, pleae enter your pin.')
    
    return build_validation_result(True, None, None)


def validate_replace_card_information(accountNumber, pin, firstName, lastName):

    if not isValid_AccountNumber(accountNumber):
        return build_validation_result(False, 'AccountNumber', 'I did not recognize that, please enter your twelve digit account number.')

    if not isValid_Name(firstName):
        return build_validation_result(False, 'FirstName', 'I did not recognize that, please enter your first name.')

    if not isValid_Name(lastName):
        return build_validation_result(False, 'LastName', 'I did not recognize that, please enter your last name.')

    if not isValid_Pin(pin):
        return build_validation_result(False, 'Pin', 'I did not recognize that, pleae enter your pin.')
    
    return build_validation_result(True, None, None)



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



def query(accountNumber, query_params):

    from botocore.exceptions import ClientError

    #DynamoDB table
    table = dynamodb.Table('BankAccounts')

    try:
        response = table.get_item(Key={'AccountNumber': Decimal(accountNumber)})
    except ClientError as err:
        if err.response['Error']['Code'] == 'InternalError':
            logger.info('Error Message: {}'.format(err.response['Error']['Message']))
        else:
            raise err
        

    return response['Item'][query_params]




def update_accountNumber(accountNumber):

    from botocore.exceptions import ClientError
    import random
    
    new_checkaccountNumber = Decimal(random.randint(1000000000000000, 9999999999999999))

    #DDB Table
    table = dynamodb.Table('BankAccounts')

    try:
        response = table.update_item(Key={'AccountNumber': Decimal(accountNumber)},
            UpdateExpression="set CheckingAccountNumber = :g",
            #ExpressionAttributeNames={'AccountNumber': accountNumber},
            ExpressionAttributeValues={':g':new_checkaccountNumber},
            ReturnValues="UPDATED_NEW"
            )

    except ClientError as err:
        if err.response['Error']['Code'] == 'InternalError':
            logger.info('Error Message: {}'.format(err.response['Error']['Message']))
        else:
            raise err
        
    res = response['Attributes']['CheckingAccountNumber']

    if new_checkaccountNumber != res:
        return False
    else:
        return res




""" --- Functions that control the bot's behavior --- """

def retrieve_balance(intent_request):
    

    slots = intent_request['currentIntent']['slots']

    #initialize slot variables
    accountNumber = try_ex(lambda: slots['AccountNumber'])
    pin = try_ex(lambda: slots['Pin'])


    output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    source = intent_request['invocationSource']

    logger.debug('output_session_attributes={}, source={}'.format(output_session_attributes, source))


    #Validating User Data
    if source == 'DialogCodeHook':
        validation_result = validate_balance_information(accountNumber, pin)
        logger.debug(validation_result)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] == None
            return elicit_slot(
                output_session_attributes, 
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )
    
        return delegate(output_session_attributes, intent_request['currentIntent']['slots'])

    
    #Now source = 'FullfillmentCodeHook
    
    source=intent_request['invocationSource']
    logger.info('source={}'.format(source))
    logger.info('slots={}'.format(slots))

    #Validation of Input Data with Database Values
    for slot_name, slot_val in slots.items():
        if (slot_val != query(accountNumber, slot_name)):
            res = query(accountNumber, slot_name)
            logger.info('slot_val={}, query_res={}'.format(slot_val, res))
            validation_result = build_validation_result(False, slot_name, f'The {slot_name} {slot_val} does not exist in our database.')
            logger.debug(validation_result)
            return close( 
                output_session_attributes,
                'Failed',
                {
                    'contentType':'PlainText',
                    'content': f'Sorry! The {slot_name} {slot_val} does not exist in our database.'
                }
            )

    balance = query(accountNumber, 'AccountBalance')
    logger.info('balance={}'.format(balance))

    return close(
        output_session_attributes,
        'Fulfilled',
        {
            'contentType':'PlainText',
            'content': f'Your debit card balance is ${balance:,.2f} dollars.'
        }
    )


def replace_card(intent_request):


    slots = intent_request['currentIntent']['slots']

    #initialize slot variables
    accountNumber = try_ex(lambda: slots['AccountNumber'])
    pin = try_ex(lambda: slots['Pin'])
    firstName = try_ex(lambda: slots['FirstName'])
    lastName = try_ex(lambda: slots['LastName'])


    output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    source = intent_request['invocationSource']

    logger.debug('output_session_attributes={}, source={}'.format(output_session_attributes, source))

    #Validating User Data
    if source == 'DialogCodeHook':
        validation_result = validate_replace_card_information(accountNumber, pin, firstName, lastName)
        logger.info(validation_result)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] == None
            return elicit_slot( #reprompts user to enter data
                output_session_attributes, 
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            ) 

        return delegate(output_session_attributes, intent_request['currentIntent']['slots']) #returns control back to Lex Bot to go to next step

    #Now source == 'FulfillmentCodeHook'
    
    source=intent_request['invocationSource']
    logger.info('source={}'.format(source))
    #Validation of Input Data with Database Values
    logger.info('slots={}'.format(slots))
    for slot_name, slot_val in slots.items():
        res = query(accountNumber, slot_name)
        logger.info('query_res={}'.format(res))
        if (str(slot_val).lower() != str(res).lower()):
            validation_result = build_validation_result(False, slot_name, f'The {slot_name} {slot_val} does not exist in our database.')
            logger.debug(validation_result)
            return close( 
                output_session_attributes,
                'Failed',
                {
                    'contentType':'PlainText',
                    'content': f'Sorry! The {slot_name} {slot_val} does not exist in our database.'
                }
            )


    new_checkaccountNumber = update_accountNumber(accountNumber)

    if not new_checkaccountNumber:
        raise Exception('Error generating new debit card number')

    new_accountNumber = str(new_checkaccountNumber)
    street_address = query(accountNumber, 'StreetAddress')
    email_address = query(accountNumber, 'Email Address')

    message = f'An email has been sent to {email_address} containing your new debit card information. ' 
    message2 = f'Your new debit card ending in {new_accountNumber[-4:]} has been mailed out to {street_address}. '
    message3 = 'Please expect it to arrive within five to seven business days.'
    
    return close(
        output_session_attributes,
        'Fulfilled',
        {
            'contentType':'PlainText',
            'content': message+message2+message3
        }
    )


""" --- Intents --- """


def dispatch(intent_request):
    '''
    Called when the user specifies an intent for this bot.
    '''

    logger.debug('dispatch userId= {}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    #Dispatch to your bot's intent handlers

    if intent_name == 'AccountLookUp':
        return retrieve_balance(intent_request)
    
    elif intent_name == 'ReplaceCard':
        return replace_card(intent_request)
    
    else:
        raise Exception('Intent with name ' + intent_name + ' not supported')



''' --- MAIN handler --- '''

def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    """

    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()

    logger.debug('event.bot.name={}, userMessage={}'.format(event['bot']['name'], event['inputTranscript']))

    return dispatch(event)
