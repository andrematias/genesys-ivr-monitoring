import os
import argparse
import requests
import json

from dotenv import load_dotenv

def auth(client_id, client_secret):
    TOKEN_URL = f"https://login.mypurecloud.com/oauth/token"
    token_params = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
    request = requests.post(TOKEN_URL, params=token_params)
    if request.status_code == 200: return request.json()

def __list_edges(auth_token):
    EDGE_LIST_URL = 'https://api.mypurecloud.com/api/v2/telephony/providers/edges'
    parammeters = {
        'pageSize': 100
    }
    headers = {
        'Authorization': f"Bearer {auth_token}"
    }
    request = requests.get(EDGE_LIST_URL, headers=headers, params=parammeters)
    if request.status_code == 200: return request.json()

def __get_metrics(entity_id, auth_token):
    ENTITY_METRIC_URL = f"https://api.mypurecloud.com/api/v2/telephony/providers/edges/{entity_id}/metrics"
    headers = {
        'Authorization': f"Bearer {auth_token}"
    }
    request = requests.get(ENTITY_METRIC_URL, headers=headers)
    if request.status_code == 200: return request.json()

def __get_entity_by_hostname(hostname, entities):
    entity = list(filter(lambda entity: entity.get('name') == hostname, entities))
    if len(entity) > 0: return entity.pop(0)

def entity_infos(auth, **kwargs):
    edges = __list_edges(auth.get('access_token'))
    entities = edges.get('entities')
    if('hostname' in kwargs):
        entity = __get_entity_by_hostname(kwargs.get('hostname'), entities)
        if entity is None: return 'Entity not found'
        entity.update(__get_metrics(entity.get('id'), auth.get('access_token')))
        entity.update({ 'trunks': __get_trunks(auth, entity.get('id'))})
        if kwargs.get('calculate'):
            if 'networks' in entity:
                entity['networks'] = calculate_networks(entity.get('networks'))
            if 'memory' in entity:
                entity['memory'] = calculate_memories(entity.get('memory'))
            if 'disks' in entity:
                entity['disks'] = calculate_disks(entity.get('disks'))

        if('filter' in kwargs and kwargs.get('filter') is not None):
            return json.dumps({kwargs.get('filter'): entity.get(kwargs['filter'])})
        return json.dumps(entity)


def calculate_memories(memories):
    calculated = []
    for memory in memories:
        total = 100 - ((100 * memory['availableBytes']) / memory['totalBytes'])
        calculated.append({
            'total': "{:.2f}%".format(round(total, 2)),
            'type': memory['type']
        })
    return calculated

def calculate_disks(disks):
    calculated = []
    for disk in disks:
        if disk['totalBytes'] > 0:
            total = 100 - ((100 * disk['availableBytes']) / disk['totalBytes'])
            calculated.append({
                'total': "{:.2f}%".format(round(total, 2)),
                'partitionName': disk['partitionName']
            })
    return calculated

def calculate_networks(networks):
    calculated = []
    for network in networks:
        if network['utilizationPct'] > 0:
            total = network['utilizationPct'] * 100
            calculated.append({
                'total': "{:.2f}%".format(round(total, 2)),
                'interfaceName': network['ifname']
            })
        else:
            calculated.append({
                'total': "{:.2f}%".format(round(0.0, 2)),
                'interfaceName': network['ifname']
            })
    return calculated

def __get_trunks(auth, edge_id, trunk_type=None):
    EDGE_TRUNKS_LIST_URL = f"https://api.mypurecloud.com/api/v2/telephony/providers/edges/{edge_id}/trunks?pageSize=100"

    headers = {
            'Authorization': f"Bearer {auth.get('access_token')}"
    }
    parammeters = {
        'pageSize': 100
    }

    if trunk_type is not None:
        parammeters.update({'trunkType': trunk_type})
    
    request = requests.get(EDGE_TRUNKS_LIST_URL, headers=headers, params=parammeters)
    if request.status_code == 200: return request.json()


if __name__ == '__main__':
    load_dotenv()
    parser = argparse.ArgumentParser(prog='genesys', description='Interface de metricas URAS Genesys VVJ')
    parser.add_argument('hostname',
                       metavar='hostname',
                       type=str,
                       help='O hostname de um servidor da estrutura genesys vvj')
    parser.add_argument('-f',
                        '--filter',
                       metavar='filter',
                       required=False,
                       type=str,
                       help='Uma chave para filtrar o resultado JSON')
    parser.add_argument('-c',
                        '--calculate',
                       metavar='calculate',
                       type=bool,
                       required=False,
                       help='Caso True o resultado é calculado e apresentado, se False apresenta os dados sem tratativas')
    args = parser.parse_args()

    auth = auth(os.getenv('CLIENT_ID'), os.getenv('CLIENT_SECRET'))
    print(entity_infos(auth, **vars(args)))
