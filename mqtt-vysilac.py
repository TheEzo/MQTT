import paho.mqtt.client as mqtt
import sys

KOD = "005d88b5"
KOD2 = "00ab00ba"
KOD3 = "xxxxxxx"

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    #client.subscribe("device/+/ctecka/potvrzeni", qos=2)
    client.publish("device/domecek/ctecka/request", payload=KOD3)
    #client.publish("device/domecek/ctecka/request", payload=KOD2)
    print "Kod odeslan"


#client = mqtt.Client(clean_session=False)
client = mqtt.Client()
client.on_connect = on_connect
client.connect("localhost", 1883)
#client.connect("192.168.1.97", 1883)
client.loop_forever()