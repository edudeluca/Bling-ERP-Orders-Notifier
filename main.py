import os
import re
import time
import traceback
import logging

import requests

from src.utils import (
    get_params,
    getNewOrderNotification,
    getLateOrderNotification
)

from src.bling_classes import (
    BlingAPI,
    BlingAuth,
    BlingDfTreat,
    BlingRequests
)

# environment variables
params = get_params()
autoModifySituations = params['autoModifySituations']
situationsToGetLogistics = params['situationsToGetLogistics']
situationToNotify = params['situationToNotify']
late_param = params['late_param']
late_timerLoop = params['late_timerLoop']

# validate variables types
if not(type(situationsToGetLogistics) == list):
    print('situationsToGetLogistics deve ser uma lista')
    input('Pressione ENTER para sair.')
    exit()

if not(type(situationToNotify) == dict):
    print('situationToNotify deve ser uma lista')
    input('Pressione ENTER para sair.')
    exit()

# gets user confirmation to auto update the orders on bling
if autoModifySituations:
    verification = input('Aviso: O update automático das situações de pedido está ativado, deseja prosseguir? [s/n]: ')    
    
    if verification == 's':
        pass
    else:
        exit()

# 
waitingOrdersDict = {}
minutes_running = 0
late_timer = 0

testloop = True
loop_interval = (60 - 20)

while testloop:
    try:
        bling = BlingDfTreat(BlingRequests.rawOrdersDf())
        bling.selectIdOnSituationColumn()
        bling.translateIdOnSituationColumn()
        bling.selectNameOnContactColumn()
        bling.addLogisticColumn(situationsToGetLogistics)
        bling.translateLogisticId()

    except requests.exceptions.ConnectionError as e:
        print('Erro ao conectar, sem conexão...')
        time.sleep(1)
        continue
    except Exception as e:
        logging.basicConfig(filename="error_log.json", level=logging.ERROR, format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"},')
        logging.error(traceback.format_exc())
        print(f'error fetching data from API: {e}')
        BlingAuth.updateBlingToken()
        time.sleep(1)
        continue

    if autoModifySituations:
        bling.autoUpdateSituations()
        
    waitingOrdersMask = bling.dataframe.situacao.str.contains('|'.join(situationToNotify.keys()))
    waitingOrdersDf = bling.dataframe.loc[waitingOrdersMask]

    if waitingOrdersMask.any():
        for i,v in waitingOrdersDf.iterrows():
            if i not in waitingOrdersDict:
                waitingOrdersDict[i] = {
                    'num':v.numero 
                    ,'situation':v.situacao
                    ,'logistic':v.logistics 
                    ,'count':0
                } 
            else:
                waitingOrdersDict[i]['situation'] = v.situacao
                waitingOrdersDict[i]['logistic'] = v.logistics
                waitingOrdersDict[i]['count'] += 1
        
         # removes attended orders
        for i in list(waitingOrdersDict.keys()):
            if  i not in waitingOrdersDf.index:
                waitingOrdersDict.pop(i)
    else:
        waitingOrdersDict = {}

    # displays orders situations
    os.system('cls')

    for situation in situationToNotify.keys():
        ordersBySituation_dict = {k:v for k,v in waitingOrdersDict.items() if re.search(situation,v['situation'])}

        new = [ordersBySituation_dict[i]['num'] for i in ordersBySituation_dict if ordersBySituation_dict[i]['count'] == 0]
        waiting = [ordersBySituation_dict[i]['num'] for i in ordersBySituation_dict\
                if (0 < ordersBySituation_dict[i]['count'] < late_param)]
        late = [ordersBySituation_dict[i]['num'] for i in ordersBySituation_dict if ordersBySituation_dict[i]['count'] >= late_param]

        print(situation.replace('\\',''))
        print('new orders: ', new)
        print('order waiting: ', waiting)
        print(f'orders waiting for {late_param}min or more: ', late,'\n')
        print('#---------------------------------------------------#\n')

    print(f'program running for: {minutes_running} minutes\n')
    minutes_running += 1

    # dicts used for notifications
    new = [
        waitingOrdersDict[i]['num'] for i in waitingOrdersDict\
        if waitingOrdersDict[i]['count'] == 0 and\
        situationToNotify[waitingOrdersDict[i]['situation']\
        .replace('(',r'\(').replace(')',r'\)')]\
        ['notifyNew']
    ]
    
    waiting = [
        waitingOrdersDict[i]['num'] for i in waitingOrdersDict\
        if (0 < waitingOrdersDict[i]['count'] < late_param)
    ]
    
    late = [
        waitingOrdersDict[i]['num'] for i in waitingOrdersDict\
        if waitingOrdersDict[i]['count'] >= late_param and\
        situationToNotify[waitingOrdersDict[i]['situation']\
        .replace('(',r'\(').replace(')',r'\)')]\
        ['notifyOld']
    ]
    
    if new:
        getNewOrderNotification(new)
        late_timer = 0

    elif late and not waiting:
        if late_timer == 0 or late_timer == late_timerLoop:
            late_timer = 1
            getLateOrderNotification(late)
        elif late_timer < late_timerLoop:
            late_timer += 1
    
    # testloop = False
    time.sleep(loop_interval)



