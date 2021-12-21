# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os
import asyncio
import random
import logging
import json
from CITL_LinuxPy import *
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device.aio import ProvisioningDeviceClient
from azure.iot.device import X509
from azure.iot.device import MethodResponse
from datetime import timedelta, datetime
from enum import IntEnum
import pnp_helper


logging.basicConfig(level=logging.ERROR)




# the interfaces that are pulled in to implement the device.
# User has to know these values as these may change and user can
# choose to implement different interfaces.
rd55up12v_digital_twin_model_identifier = "dtmi:com:example:rd55up12v;1"
device_info_digital_twin_model_identifier = "dtmi:azure:DeviceManagement:DeviceInformation;1"

# The device "TemperatureController" that is getting implemented using the above interfaces.
# This id can change according to the company the user is from
# and the name user wants to call this Plug and Play device
model_id = "dtmi:com:example:iqrcntl;1"

# the components inside this Plug and Play device.
# there can be multiple components from 1 interface
# component names according to interfaces following pascal case.
device_information_component_name = "deviceInformation"
rd55up12v_component_name = "rd55up12v"
#serial_number = "02028527F1210241-E"



#####################################################
# ENUM Defenition : User will define Enum Class
# depending on what Enum Schemas defines

#####################################################
class Status(IntEnum):
    Good = 0
    Bad = 1



iqr_control_status = Status.Good



#####################################################
# COMMAND HANDLERS : User will define these handlers
# depending on what commands the component defines

#####################################################
# GLOBAL VARIABLES
# Rd55up12v = None


class Rd55up12v(object):
    def __init__(self, name):
        self.buf_adderss = 16284
        self.data_size = 1
        self.return_status = -1
        self.good_status = 200
        self.error_status = 400
        self.temp_buf = -1
        self.value = -1
        self.readdata = -1

    async def citl_tobuf_single_handler(self, value):
        self.value = value
        ulTargetAddr = 16284
        #usDataBuf_W = [0xFFFF]
        if(self.value == -1):
            print("write valule must be greater than zero")
            self.return_status = self.error_status

        usDataBuf_W = [value]
        print("Write to Buf_Addr=16284 , Data= {_val}".format(_val=value))
        #to do call CITL_ToBuf function
        sRet = CITL_ToBuf(ulTargetAddr, self.data_size, usDataBuf_W, 0)
        if(sRet != 0):
            print("CITL_ToBuf Failed({})".format(sRet))
            self.return_status = self.error_status
        self.return_status = self.good_status
        

    def citl_tobuf_single_response(self, value):
        self.value = value
        if self.return_status == self.error_status:
            response_dict = {}
            response_dict["ret"] = self.error_status
            print("400 Error at citl_tobuf_single_response")
            return response_dict

        response_dict = {}
        response_dict["ret"] = self.good_status
        print("200 Good  at citl_to_tobuf_single_response: {}".format(response_dict) )
        return response_dict


    async def citl_frombuf_single_handler(self, addr):
        _readData =[]
        if(addr != 16284):
            print("read address was not set expeted value, expected value is 16284")
            return -1, self.error_status
        #to do call CITL_FromBuf function
        sRet = CITL_FromBuf(addr, self.data_size, _readData, 1)
        if(sRet != 0):
            print("CITL_FromBuf Failed({})".format(sRet))
            self.readdata = -1
            self.return_status = self.error_status
        self.readdata = _readData
        self.return_status = self.good_status

    def citl_frombuf_single_response(self, value):
        if( self.return_status == self.error_status):
            response_dict = {}
            response_dict["value"] = self.readdata
            response_dict["ret"]= self.error_status
            print("400 Error at cli_frombuf_single_resposne")
            return response_dict
        response_dict={}
        response_dict["value"]= self.readdata
        response_dict["ret"]= self.good_status 
        print("200 Good  at citl_frombuf_single_response: {}".format(response_dict))
        return response_dict



 ###########################################
 #  If DTDL model uses asyncnous method 
 #  you need to use async def instead of def
 ###########################################


async def hello_handler(values):
    if values:
        print(
            "Recieved Command Hello from IoT Central , Payload:{msg} ".format(msg=values)
        )
    print("Command Hello without payload ")


# END COMMAND HANDLERS
#####################################################

#####################################################
# CREATE RESPONSES TO COMMANDS

def hello_response(values):
    if values:
        response_dict= {
            "response": values,
            "Timestamp":(
                (datetime.now() ).astimezone().isoformat()
            )
        }
    else:
        response_dict = {
            "response" : "Hello",
            "Timestamp" : (
            (datetime.now() ).astimezone().isoformat()
            )
        }
    print(response_dict)
    return response_dict

# END CREATE RESPONSES TO COMMANDS
#####################################################

#####################################################
# TELEMETRY TASKS


async def send_telemetry_from_temp_controller(device_client, telemetry_msg, component_name=None):
    msg = pnp_helper.create_telemetry(telemetry_msg, component_name)
    await device_client.send_message(msg)
    print("Sent message")
    print(msg)
    await asyncio.sleep(5)

async def send_telemetry_from_citl_buf(device_client, citl_msg, component_name=None):
    msg = pnp_helper.create_telemetry( citl_msg, component_name)
    await device_client.send_message(msg)
    print("Send CITL msg")
    print(msg)
    await asyncio.sleep(5)

#####################################################
# COMMAND TASKS


async def execute_command_listener(
    device_client,
    component_name=None,
    method_name=None,
    user_command_handler=None,
    create_user_response_handler=None,
):
    """
    Coroutine for executing listeners. These will listen for command requests.
    They will take in a user provided handler and call the user provided handler
    according to the command request received.
    :param device_client: The device client
    :param component_name: The name of the device like "sensor"
    :param method_name: (optional) The specific method name to listen for. Eg could be "blink", "turnon" etc.
    If not provided the listener will listen for all methods.
    :param user_command_handler: (optional) The user provided handler that needs to be executed after receiving "command requests".
    If not provided nothing will be executed on receiving command.
    :param create_user_response_handler: (optional) The user provided handler that will create a response.
    If not provided a generic response will be created.
    :return:
    """
    while True:
        if component_name and method_name:
            command_name = component_name + "*" + method_name
        elif method_name:
            command_name = method_name
        else:
            command_name = None

        command_request = await device_client.receive_method_request(command_name)
        print("Command request received with payload")
        values = command_request.payload
        print(values)

        if user_command_handler:
            await user_command_handler(values)
        else:
            print("No handler provided to execute")

        (response_status, response_payload) = pnp_helper.create_response_payload_with_status(
            command_request, method_name, create_user_response=create_user_response_handler
        )

        command_response = MethodResponse.create_from_method_request(
            command_request, response_status, response_payload
        )

        try:
            await device_client.send_method_response(command_response)
        except Exception:
            print("responding to the {command} command failed".format(command=method_name))


#####################################################
# PROPERTY TASKS


async def execute_property_listener(device_client):
    while True:
        patch = await device_client.receive_twin_desired_properties_patch()  # blocking call
        print(patch)
        properties_dict = pnp_helper.create_reported_properties_from_desired(patch)

        await device_client.patch_twin_reported_properties(properties_dict)


#####################################################
# An # END KEYBOARD INPUT LISTENER to quit application


def stdin_listener():
    """
    Listener for quitting the sample
    """
    while True:
        selection = input("Press Q to quit\n")
        if selection == "Q" or selection == "q":
            print("Quitting...")
            break


# END KEYBOARD INPUT LISTENER
#####################################################


#####################################################
# MAIN STARTS
async def provision_device(provisioning_host, id_scope, registration_id, x509, model_id):
    provisioning_device_client = ProvisioningDeviceClient.create_from_x509_certificate(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        x509=x509,
    )

    provisioning_device_client.provisioning_payload = {"modelId": model_id}
    return await provisioning_device_client.register()


async def main():
    #Init CITL Function
    CITLAppInit()

    switch = os.getenv("IOTHUB_DEVICE_SECURITY_TYPE")
    if switch == "DPS":
        provisioning_host = (
            os.getenv("IOTHUB_DEVICE_DPS_ENDPOINT")
            if os.getenv("IOTHUB_DEVICE_DPS_ENDPOINT")
            else "global.azure-devices-provisioning.net"
        )
        id_scope = os.getenv("IOTHUB_DEVICE_DPS_ID_SCOPE")
        registration_id = os.getenv("IOTHUB_DEVICE_DPS_DEVICE_ID")
        x509 = X509(
            cert_file=os.getenv("IOTHUB_DEVICE_X509_CERT"),
            key_file=os.getenv("IOTHUB_DEVICE_X509_KEY"),
            pass_phrase=os.getenv("PASS_PHRASE")
        )

        registration_result = await provision_device(
            provisioning_host, id_scope, registration_id, x509, model_id
        )

        if registration_result.status == "assigned":
            print("Device was assigned")
            print(registration_result.registration_state.assigned_hub)
            print(registration_result.registration_state.device_id)
            device_client = IoTHubDeviceClient.create_from_x509_certificate(
                x509=x509,
                hostname=registration_result.registration_state.assigned_hub,
                device_id=registration_result.registration_state.device_id,
                product_info=model_id,
            )
        else:
            raise RuntimeError(
                "Could not provision device. Aborting Plug and Play device connection."
            )

    elif switch == "connectionString":
        conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
        print("Connecting using Connection String " + conn_str)
        device_client = IoTHubDeviceClient.create_from_connection_string(
            conn_str, product_info=model_id
        )
    else:
        raise RuntimeError(
            "At least one choice needs to be made for complete functioning of this sample."
        )

    # Connect the client.
    await device_client.connect()

    ################################################
    # Update readable properties from various components

    properties_root = pnp_helper.create_reported_properties(iqrcntlstatus=iqr_control_status)
    properties_rd55up12v = pnp_helper.create_reported_properties(
        rd55up12v_component_name, hoge_property=12345
    )

    properties_device_info = pnp_helper.create_reported_properties(
        device_information_component_name,
        swVersion="Kernel 4.9.76-rt61-ltsi",
        manufacturer="MELCO",
        model="RD55UP12-V",
        osName="debian",
        processorArchitecture="arm9",
        processorManufacturer="ARM",
        totalStorage=8192,
        totalMemory=1024,
    )

    property_updates = asyncio.gather(
        device_client.patch_twin_reported_properties(properties_root),
        device_client.patch_twin_reported_properties(properties_rd55up12v),
        device_client.patch_twin_reported_properties(properties_device_info),
    )

    ################################################
    # Get all the listeners running
    print("Listening for command requests and property updates")

    global RD55UP12V
    RD55UP12V = Rd55up12v(rd55up12v_component_name)


    listeners = asyncio.gather(
        execute_command_listener(
            device_client, 
            method_name="Hello", 
            user_command_handler=hello_handler,
            create_user_response_handler=hello_response,        ),
        execute_command_listener(
            device_client,
            rd55up12v_component_name,
            method_name="CITL_ToBuf_Single",
            user_command_handler=RD55UP12V.citl_tobuf_single_handler,
            create_user_response_handler=RD55UP12V.citl_tobuf_single_response,
        ),
        execute_command_listener(
            device_client,
            rd55up12v_component_name,
            method_name="CITL_FromBuf_Single",
            user_command_handler=RD55UP12V.citl_frombuf_single_handler,
            create_user_response_handler=RD55UP12V.citl_frombuf_single_response,
        ),

        execute_property_listener(device_client),
    )

    ################################################
    # Function to send telemetry every 8 seconds

    async def send_telemetry():
        
        ulTargetAddr = 16384
        readDataBuf_W =[0]

        print("Sending simulated temprature telemetry -- range 10 to 50")

        while True:
            curr_temp_ext = random.randrange(10, 50)
            temperature_msg1 = {"temperature": curr_temp_ext}
            await send_telemetry_from_temp_controller(
                device_client, temperature_msg1, None
            )

            sRet= CITL_FromBuf(ulTargetAddr, 1, readDataBuf_W, 1)
            if(sRet != 0):
                print("CITL_FromBuf Faild({})".format(sRet))
            
            if(readDataBuf_W[0] < 500):
                readDataBuf_W[0]+=1
                print("Val = {}".format(readDataBuf_W))
                sRet = CITL_ToBuf(ulTargetAddr, 1, readDataBuf_W, 0)
                if(sRet != 0):
                    print("CITL_ToBuf Failed({})".format(sRet))
            else:
                print("Reset Val = 1")
                readDataBuf_W[0] = 1
                sRet = CITL_ToBuf(ulTargetAddr, 1, readDataBuf_W, 0)

            citl_msg1 = { "CTIL_16384": readDataBuf_W[0]}
            await send_telemetry_from_citl_buf(device_client, citl_msg1, rd55up12v_component_name)

    send_telemetry_task = asyncio.ensure_future(send_telemetry())

    # Run the stdin listener in the event loop
    loop = asyncio.get_running_loop()
    user_finished = loop.run_in_executor(None, stdin_listener)
    # # Wait for user to indicate they are done listening for method calls
    await user_finished

    if not listeners.done():
        listeners.set_result("DONE")

    if not property_updates.done():
        property_updates.set_result("DONE")

    listeners.cancel()
    property_updates.cancel()

    send_telemetry_task.cancel()

    # Finally, shut down the client
    await device_client.shutdown()


#####################################################
# EXECUTE MAIN

if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
