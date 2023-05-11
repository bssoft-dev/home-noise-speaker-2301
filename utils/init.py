import configparser
import os, subprocess
from utils.setLogger import Logger
from time import time

def print_settings(config, deviceId):
    for i in ['device', 'speaker', 'audio', 'files']:
        print(f'----------{i}----------')
        for j in config[i]:
            print(j,':',config[i][j])
        print('')
    print('--------------------------------')
    print(f'Device ID: {deviceId}')
    print('--------------------------------')


p_config = configparser.ConfigParser()
os.makedirs('/boot/bssoft', exist_ok=True)
if os.path.exists('/boot/bssoft/config.txt'):
    p_config.read('/boot/bssoft/config.txt')
else:
    p_config.read('config.ini') 

if os.path.exists('/boot/bssoft/id.txt'):
    deviceId = open('/boot/bssoft/id.txt', 'r').read()
else:
    deviceId = int(time())
    open('id.txt', 'w').write(str(deviceId))
    subprocess.Popen('sudo cp id.txt /boot/bssoft/', shell=True)

# Change config strings to int
config = {s:dict(p_config.items(s)) for s in p_config.sections()}
config['audio']['chunk'] = int(config['audio']['chunk'])
config['audio']['channels'] = int(config['audio']['channels'])
config['audio']['rate'] = int(config['audio']['rate'])
config['audio']['record_seconds'] = int(config['audio']['record_seconds'])
config['files']['num_save'] = int(config['files']['num_save'])
config['files']['sending_record_seconds'] = int(config['files']['sending_record_seconds'])
config['device']['heartbeat_interval'] = int(config['device']['heartbeat_interval'])

# Calculate number of frames for one single chunk
config['audio']['num_frame'] = int(config['audio']['rate'] / config['audio']['chunk'] * config['audio']['record_seconds'])
# Calculate number of chunks for one single file
config['files']['num_sending_bundle'] = int(config['files']['sending_record_seconds']//config['audio']['record_seconds'])

# Set logger
logger = Logger(name='smart_speaker', logdir=config['files']['log_dir'], level=config['files']['log_level'])