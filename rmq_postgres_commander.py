from amqp_handler import AMQPHandler
from postgres_handler import PostgresHandler
import asyncio
import json
import difflib
import sys
import logging
import json
import requests
import os

logger = logging.getLogger('rmq_postgres_comander')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
bf = logging.Formatter('{asctime} {name} {levelname:8s} {message}', style='{')
handler.setFormatter(bf)
logger.addHandler(handler)

# old fashion config from the config.json
# with open('config.json') as jcf:
#     config = json.load(jcf)

config = {}

config['postgres_db_name'] = os.environ.get('DEVICE_CONFIG_BACKUP_DB_NAME', 'device_config_backup_db_name')
config['postgres_username'] = os.environ.get('DEVICE_CONFIG_BACKUP_DB_USER_NAME', 'postgres_username')
config['postgres_password'] = os.environ.get('DEVICE_CONFIG_BACKUP_DB_PASSWORD', 'postgres_password')
config['postgres_host_name'] = os.environ.get('DEVICE_CONFIG_BACKUP_HOST_ADDRESS', '')
config['rmq_host'] = os.environ.get('RMQ_HOST', '')
config['postgres_commander_rmq_exchange'] = os.environ.get('POSTGRES_COMMANDER_RMQ_EXCHANGE', '')
config['postgres_commander_rmq_queue_in'] = os.environ.get('POSTGRES_COMMANDER_RMQ_QUEUE_IN', '')

config['easy_crossing_post_address'] = os.environ.get('EASY_CROSSING_POST_ADDRESS', '')

def send_to_easy_crossing_via_post(msg, ip_addr):
    try:
        msg = json.loads(msg)
        msg['config'] = str(msg['config'])
        msg['ip_addr'] = ip_addr
        req = requests.post(config['easy_crossing_post_address'], data=msg)
        logger.info('sent to easy crossing {} {}'.format(req.status_code, req.reason))
        logger.info(req.text[:300] + '...')
    except Exception as exc:
        logger.error('unable sent to easy crossing: {}'.format(exc))    

def rmq_msg_proc(msg):
    try:
        process_message_status = False
        msg = msg.decode('utf-8')
        msg = json.loads(msg)

        PH = PostgresHandler(
            config['postgres_db_name'], 
            config['postgres_username'], 
            config['postgres_password'], 
            config['postgres_host_name']
        )

        # find last version and compare

        sql_find_last_string = \
            "SELECT id,device_id,device_name,device_config,greatest(created_at,updated_at) FROM device_config_operator_deviceconfig where device_id = {} ORDER BY greatest(created_at,updated_at) DESC LIMIT 1".format(msg['device_id'])

        sql_get_ip_addr = \
            "SELECT device_ipv4 FROM device_config_operator_device where id = {}".format(msg['device_id'])

        find_last_operation_result = PH.execute(sql_find_last_string)
        
        latest_config = []
        
        if find_last_operation_result != []:
            latest_config = find_last_operation_result[0][3]['config']

        current_config = msg['main_output'].split('\r\n')

        # get out some \r \n characters
        current_config = [cc.strip() for cc in current_config]


        # compare
        if latest_config == current_config:

            logger.info('current config for a device: {} is the same as the latest in the db. we are going to DO NOTHING!'.format(msg['device_name']))
            process_message_status = True
        
        # insert it if different
        else:

            current_config = \
            {
                "config" : current_config

            }

            process_message_status = PH.insert(
                'device_config_operator_deviceconfig', 
                (
                    'device_config', 'device_id', 'created_at', 'updated_at', 'device_name'
                ), 
                (
                    json.dumps(current_config), msg['device_id'], msg['datetime'], msg['datetime'], msg['device_name']
                )
            )

            try:
                ip_addr = PH.execute(sql_get_ip_addr)
                send_to_easy_crossing_via_post(json.dumps(current_config), ip_addr)
            except Exception as exc:
                logger.error('Unfortunetely we can`t send info to the easy crossing {}'.format(exc))

            try:
                PH.update(
                    'device_config_operator_device', 
                    (
                        'device_name'
                    ), 
                    (
                        "'{}'".format(msg['device_name'])
                    ),
                    'id', msg['device_id']
                )
            except Exception as exc:
                logger.error('can not update device name: {}'.format(exc))

            logger.info('current config for a device: {} is different than the latest in the db. we are going to SAVE IT!'.format(msg['device_name']))
        # send True if we successfully proccesed it.
        # send not None (the message) if we need to forward it somwhere
        return (process_message_status, None)
    except Exception as exc:
        print('unable to save the data: {}'.format(exc))

def main():
    
    loop = asyncio.get_event_loop()

    AMQPH = AMQPHandler(loop)
    print(config['rmq_host'])

    loop.run_until_complete(AMQPH.connect(amqp_connect_string=config['rmq_host']))

    loop.run_until_complete(
        AMQPH.receive(
            config['rmq_exchange'], 
            config['rmq_queue_in'], 
            rmq_msg_proc
        )
    )
    loop.close()

if __name__ == '__main__':
    main()