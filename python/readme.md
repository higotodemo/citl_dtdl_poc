Python code of CITL poc


Example of how-to-set your ENVIRONMENT to run sample python code
(you can add following lines in .bashrc)


export IOTHUB_DEVICE_DPS_ENDPOINT="global.azure-devices-provisioning.net"

export IOTHUB_DEVICE_SECURITY_TYPE="DPS"

export IOTHUB_DEVICE_DPS_ID_SCOPE="your-iot-central-scope-id"

export IOTHUB_DEVICE_DPS_DEVICE_ID="Your-Device-id"

export IOTHUB_DEVICE_X509_CERT="/root/YourDeviceid_cert.pem"

export IOTHUB_DEVICE_X509_KEY="/root/YourDeviceid_key.pem"

export PASS_PHRASE="xxxxxxx" 

export DST="/usr/local/lib/python3.7/site-packages"

