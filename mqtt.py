from src.data.models import User
from src.data.database import db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
import paho.mqtt.client as mqtt
from datetime import datetime
from src.data.models.carddata import Card
from src.data.models.vazby import User_has_group
from src.data.models.group import Group
from src.data.models.grouphastimecard import Group_has_timecard
from src.data.models.timecard import Timecard
from src.data.models.carddata import Card

# CONSTANTS
DEFAULT_CODE = "00000000"
ACCESS_DENIED_CODE = "0"
ACCESS_ALLOWED_CODE = "1"

code = DEFAULT_CODE


def find(topic, hledat):   #stringy se nesmi jmenovat podobne
    pom = topic.find(hledat)
    if (pom < 0):
        return False
    else:
        return True

def can_access(user, topic, chip):
    now = datetime.now().time()
    pom = False
    userGroups = db.session.query(User_has_group.group_id).filter_by(user_id=user).all()     #[(1,)(2,)]
    for i in userGroups:
        timecardInGroup = db.session.query(Group_has_timecard.timecard_id).filter_by(group_id=i[0]).all()
        for j in timecardInGroup:
            timecardName = db.session.query(Timecard.timecard_head).filter_by(id=j[0]).scalar()
            timecardName = "device/" + timecardName + "/ctecka"
            if(find(topic, timecardName)):
                timecardId = j[0]
                pom = True
        if (pom):
            time_from = db.session.query(Group.access_time_from).filter_by(id=i[0]).scalar()
            time_to = db.session.query(Group.access_time_to).filter_by(id=i[0]).scalar()
            # print str(time_from) +" < "+ str(now) +" < "+ str(time_to)
            if time_from is not None or time_to is not None:
                if time_from < now < time_to:
                    pom = True
                    card = Card(card_number="", chip_number=chip, time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_card_reader=timecardId, id_user=user, access=pom)
                    db.session.add(card)
    if(pom==False):
        timecardId = Timecard.getIdAndName()
        for i in range(len(timecardId)):
            if find(topic, timecardId[i][1]):
                card = Card(card_number="", chip_number=chip, time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_card_reader=timecardId[i][0], id_user=user, access=pom)
                db.session.add(card)
    db.session.commit()
    return pom

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("device/+/ctecka/request", qos=0)
    # client.subscribe("device/+/ctecka/log", qos=0)

def on_message(client, userdata, msg):
    print(msg.topic+": "+str(msg.payload))
    if(msg.topic.endswith("ctecka/request")):
        code = msg.payload
        # user = User.find_by_number(code)
        user_chip = User.find_by_chip(code)
        before, sep, after = msg.topic.rpartition('/')
        if (user_chip) and (can_access(user_chip, msg.topic, code)):

            client.publish(before + sep + "potvrzeni", payload=ACCESS_ALLOWED_CODE)
            print("ACCESS ALLOWED")
        else:
            print user_chip
            if user_chip is None:
                timecardId = Timecard.getIdAndName()
                for i in range(len(timecardId)):
                    if find(msg.topic, timecardId[i][1]):
                        card = Card(card_number="", chip_number=code, time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_card_reader=timecardId[i][0], id_user="0", access=False)
                        db.session.add(card)
                        db.session.commit()
            client.publish(before + sep + "potvrzeni", payload=ACCESS_DENIED_CODE)
            print("ACCESS DENIED")

        code = DEFAULT_CODE
        #s.remove();

Base = declarative_base()

engine = create_engine('mysql+mysqlconnector://skola:root@localhost/karty')

session = sessionmaker()
session.configure(bind=engine, autocommit=True)
Base.metadata.create_all(engine)

#client = mqtt.Client(clean_session=False)
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883)
#client.connect("192.168.1.97", 1883)
client.loop_forever()