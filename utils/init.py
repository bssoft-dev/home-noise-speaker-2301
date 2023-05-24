import configparser
import os, subprocess
from utils.setLogger import Logger
from time import time

def print_settings(config, deviceId):
    print('')
    print('============= CONFIGS ==============')
    print('')
    for key in config.keys():
        print(f'----------{key}----------')
        for i in config[key]:
            print(i,':',config[key][i])
        print('')
    print('--------------------------------')
    print(f'Device ID: {deviceId}')
    print('--------------------------------')

ori_config = configparser.ConfigParser()
os.makedirs('/boot/bssoft', exist_ok=True)
if os.path.exists('/boot/bssoft/config.txt'):
    ori_config.read('/boot/bssoft/config.txt')
else:
    ori_config.read('config.ini') 

# Set logger
logger = Logger(name='therapy_speaker', logdir=ori_config['files']['log_dir'], level=ori_config['files']['log_level'])

if os.path.exists(f'{ori_config["files"]["settings_dir"]}/id.txt'):
    deviceId = open(f'{ori_config["files"]["settings_dir"]}/id.txt', 'r').read()
else:
    deviceId = int(time())
    logger.info(f"Device ID has been written to id.txt")
    open('id.txt', 'w').write(str(deviceId))
    subprocess.Popen('sudo cp id.txt /boot/bssoft/', shell=True)

# Change config strings to int
config = {s:dict(ori_config.items(s)) for s in ori_config.sections()}
config['audio']['chunk'] = int(config['audio']['chunk'])
config['audio']['channels'] = int(config['audio']['channels'])
config['audio']['rate'] = int(config['audio']['rate'])
config['audio']['record_seconds'] = int(config['audio']['record_seconds'])
config['files']['num_save'] = int(config['files']['num_save'])
config['files']['sending_record_seconds'] = int(config['files']['sending_record_seconds'])
config['device']['heartbeat_interval'] = int(config['device']['heartbeat_interval'])

# Add properties of audio card
if config['audio']['audio_card'] == 'core_v2':
    config['audio']['mixer_control'] = 'Playback'
    config['audio']['cardindex'] = 0
elif config['audio']['audio_card'] == 'bank':
    config['audio']['mixer_control'] = 'PCM'
    config['audio']['cardindex'] = 1
else:
    config['audio']['mixer_control'] = 'Playback'
    config['audio']['cardindex'] = 1
    
# Calculate number of frames for one single chunk
config['audio']['num_frame'] = int(config['audio']['rate'] / config['audio']['chunk'] * config['audio']['record_seconds'])
# Calculate number of chunks for one single file
config['files']['num_sending_bundle'] = int(config['files']['sending_record_seconds']//config['audio']['record_seconds'])
