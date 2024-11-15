import os
import re
import json
import time
import base64
import logging

import requests
import pandas as pd

# ----------------------------------------------------------------- #
class BlingDfTreat():
    def __init__(self, dataframe):
        self.dataframe = dataframe

    def autoUpdateSituations(self):
        filtered_series = self.dataframe.logistics.dropna()
        
        if 0 < filtered_series.size < 5:
            for index,value in filtered_series.items():
                no_nfe = bool(re.search('FLEX|ERUPÇÃO',value))
                needs_nfe = ( bool(re.search('ENVIOS',value)) and not bool(re.search('ERUPÇÃO',value)) )

                if no_nfe:
                    BlingRequests.patchBlingSituation(orderId=index, situationId=312879)
                elif needs_nfe:
                    BlingRequests.patchBlingSituation(orderId=index, situationId=312950)
    
    
    def translateLogisticId(self):
        if not all(self.dataframe.logistics.isna()):
            self.dataframe.logistics = self.dataframe.logistics.replace(BlingRequests.getLogisticIdsDict(), regex=True)     

    def addLogisticColumn(self,situationsToGetLogistics:list):   
        situationsToGetLogistics = '|'.join(situationsToGetLogistics)

        mask = self.dataframe.situacao.str.contains(situationsToGetLogistics,regex=True)
        logistic_id_series = self.dataframe.loc[mask].apply(lambda x: BlingRequests.getLogisticIdWithOrderId(x.name), axis=1)
        
        self.dataframe.loc[mask,'logistics'] = logistic_id_series
    
    def selectNameOnContactColumn(self):
        self.dataframe.contato = self.dataframe.contato.apply(lambda x: x['nome'])

    def translateIdOnSituationColumn(self):
        translation = BlingRequests.getSituationIdsDict()
        self.dataframe.situacao = self.dataframe.situacao.replace(translation)

    def selectIdOnSituationColumn(self):
        self.dataframe.situacao = self.dataframe.situacao.apply(lambda x: x['id'])

# ----------------------------------------------------------------- #
class BlingRequests():

    def rawOrdersDf():
        ordersDf = pd.DataFrame(BlingRequests.getOrders()).set_index('id')
        return ordersDf
    
    def getOrders():
        url = 'https://www.bling.com.br/Api/v3/pedidos/vendas'
        response = BlingRequests.get(url)
        data = response['data']
        return data

    def getLogisticIdsDict():
        url = f'https://www.bling.com.br/Api/v3/logisticas'
        response = BlingRequests.get(url)
        logistics = response['data']
        
        logistic_ids_dict = {str(logistic['id']):logistic['descricao'] for logistic in logistics}

        return logistic_ids_dict
    
    def getLogisticIdWithOrderId(orderId): 
        try:
            objectId = BlingRequests.getOrderObjectId(orderId)
            serviceId = BlingRequests.getServiceIdWithObjectId(objectId)
            logisticId = BlingRequests.getLogisticIdWithServiceId(serviceId)
        except IndexError:
            logisticId = 0
        return str(logisticId)

    def getLogisticIdWithServiceId(serviceId):
        url = f'https://www.bling.com.br/Api/v3/logisticas/servicos/{serviceId}'
        response = BlingRequests.get(url)
        logisticId = response['data']['logistica']['id']
        
        return logisticId

    def getServiceIdWithObjectId(objectId):
        url = f'https://www.bling.com.br/Api/v3/logisticas/objetos/{objectId}'
        response = BlingRequests.get(url)
        serviceId = response['data']['servico']['id']

        return serviceId

    def getOrderObjectId(orderId):
        url = f'https://www.bling.com.br/Api/v3/pedidos/vendas/{orderId}'
        response = BlingRequests.get(url)
        objectId = response['data']['transporte']['volumes'][0]['id']
        return objectId

    def patchBlingSituation(orderId:int, situationId:int):
        url = f'https://www.bling.com.br/Api/v3/pedidos/vendas/{orderId}/situacoes/{situationId}'
        requests.patch(url, headers=BlingRequests.header())

    def getSituationIdsDict():
        return {situation['id']:situation['nome'] for situation in BlingRequests.getSituationIds()}
    
    def getSituationIds():
        response = BlingRequests.get(url='https://www.bling.com.br/Api/v3/situacoes/modulos/98310')
        data = response['data']
        return data
    
    def get(url: str):
        time.sleep(0.5)
        while True:
            response = requests.get(url=url, headers=BlingRequests.header())
            if response.status_code == 200:
                break
            elif response.status_code == 401:
                raise(ConnectionRefusedError)
                print(response.status_code)
                time.sleep(1)

        json_response = response.json()
        
        return json_response

    def header():
        header = {       
            'Authorization':f'Bearer {BlingAPI.bling_access_token()}'
            ,'accept': 'application/json'
        }
        
        return header

# ----------------------------------------------------------------- #
class BlingAuth():

    def getBlingClient():
        with open('params.json','r') as file:
            params_string = file.read()

        params = json.loads(params_string)
        return params

    def encode_to_base64(string):
        encoded_bytes = base64.b64encode(string.encode('utf-8'))
        encoded_string = encoded_bytes.decode('utf-8')
        return encoded_string

    client_id = getBlingClient()['bling_client_id']
    client_secret = getBlingClient()['bling_client_secret']
    encoded_authorization = encode_to_base64(f'{client_id}:{client_secret}')

    def updateBlingToken():
        if not os.path.exists('bling_tokens.json'):
            BlingAuth.getFirstBlingToken()
        else:
            BlingAuth.refreshTokens()

    def getFirstBlingToken():
        url = 'https://www.bling.com.br/Api/v3/oauth/token'

        state = 'expedicao'
        authorization_url = f'https://www.bling.com.br/Api/v3/oauth/authorize?response_type=code&client_id={BlingAuth.client_id}&state={state}'
        print('Para obter o authorization_code, acesse este site:\n',authorization_url)

        authorization_code = input('authorization_code here: ')

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
            ,'Accept': '1.0'
            ,'Authorization': f'Basic {BlingAuth.encoded_authorization}'
        }

        data = {
            'grant_type':'authorization_code'
            ,'code':f'{authorization_code}'
        }

        token_reponse_json = BlingAuth.get_post_token_response_json(url, headers, data)
        BlingAuth.write_bling_tokens(token_reponse_json)


    def refreshTokens():
        url = 'https://www.bling.com.br/Api/v3/oauth/token'
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
            ,'Accept': '1.0'
            ,'Authorization': f'Basic {BlingAuth.encoded_authorization}'
        }

        data = {
            'grant_type':'refresh_token'
            ,'refresh_token':BlingAPI.bling_refresh_token()
        }
       
        token_reponse_json = BlingAuth.get_post_token_response_json(url, headers, data)
        BlingAuth.write_bling_tokens(token_reponse_json)
                
    def get_post_token_response_json(url, headers, data):
        while True:
            while True:
                try:
                    token_response = requests.post(url,headers=headers, data=data)
                    break
                except ConnectionError:
                    print('ConnectionError')

            status_code = token_response.status_code
            token_response_json = token_response.json()

            if token_response.status_code == 200:
                return token_response_json
            else:
                print(f"token_response status code: {status_code}")

    def write_bling_tokens(token_response):
        print(token_response)
        # FIXME remover ou melhorar esse log
        with open('token_response.json', 'a') as file:
            for i in [time.asctime(),json.dumps(token_response)]:
                file.writelines(i)
                file.writelines(' - ')
                
            file.writelines('\n')
        
        bling_tokens = {k:v for k,v in token_response.items() if k == 'access_token' or k == 'refresh_token'}
        
        if bling_tokens:
            with open('bling_tokens.json', 'w') as file:
                json.dump(bling_tokens,file,indent=4)
        else:
            input('Dados de token vazios. Pressione ENTER para continuar...')

# ----------------------------------------------------------------- #
class BlingAPI:
    def read_bling_token():
        with open('bling_tokens.json', 'r') as file:
            json_string = file.read()

        bling_tokens = json.loads(json_string)

        return bling_tokens
    
    def bling_access_token():
        return BlingAPI.read_bling_token()['access_token']
    
    def bling_refresh_token():
        return BlingAPI.read_bling_token()['refresh_token']
# ----------------------------------------------------------------- #