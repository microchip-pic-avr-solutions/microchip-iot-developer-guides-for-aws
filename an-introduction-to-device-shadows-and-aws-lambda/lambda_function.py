import boto3 # AWS SDK for python
    import json  # JSON encoder and decoder

    # Name of the AWS IoT Core thing that should be notified about process anomalies
    notificationThing = 'notificationThingName'

    lightLevelThreshold = 200 # Light threshold for process anomaly notification

    # Main function
    def lambda_handler(event, context):
        # Initialize dictionary for state variables
        dict = {}

        if event['Light'] > lightLevelThreshold:
            dict['anomaly'] = 1
        else:
            dict['anomaly'] = 0

        update_shadow(dict, notificationThing)

    # Updates the device shadow of the specified thing_name
    def update_shadow(state_dict, thing_name):

        # Construct payload and convert it to JSON format
        payload = {
            "state": {
                "desired": state_dict
            }
        }
        JSON_payload = json.dumps(payload)

        # Initialize AWS IoT Core SDK communicaiton client
        IoT_client = boto3.client('iot-data', 'us-east-2')

        # Send shadow update request
        response = IoT_client.update_thing_shadow(thingName=thing_name,payload=JSON_payload)