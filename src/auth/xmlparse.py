# -*- coding: utf-8 -*-
"""

    ~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2012 by Aukce Elevo s.r.o.
"""
import xmltodict
from datetime import datetime
from itertools import groupby
from ..data.database import db
from ..data.models import User, Card
def mujxmlparse(data):
    data = data.decode("windows-1250").encode("utf-8")
    doc=xmltodict.parse(data, xml_attribs=True)
    do = doc['DATAPACKET']['ROWDATA']['ROW']
    mydata = []
    for d in do:
        mydata.append([d['@CHECKTIME'],d['@PIN'],d['@Name']])
    result = {}
    sortkeyfn = key=lambda s:s[1]
    for key,valuesiter in groupby(mydata, key=sortkeyfn):
        result[key] = list(v[2] for v in valuesiter)
    # pridani uzivatelu pokud neexistuji
    for i in result:
        if not db.session.query(User).filter(User.card_number == i).filter(User.second_name == result[i][0]).first():
            i=User(card_number=int(i),username=i,second_name=result[i][0],email=i+'@sspu-opava.cz')
            db.session.add(i)
    db.session.commit()

    result = {}
    for i in mydata:
        i=Card(card_number=i[1],time=datetime.strptime(i[0], "%Y-%m-%d %H:%M:%S"))
        db.session.add(i)
    db.session.commit()


    return True