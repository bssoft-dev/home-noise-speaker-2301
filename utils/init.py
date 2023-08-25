import configparser, math, os, subprocess
from utils.setLogger import Logger
from time import time

def print_settings(config, deviceId):
    print('')
    print('============= CONFIGS ==============')
    print('')
    for section in config.keys():
        print(f'----------{section}----------')
        for option in config[section]:
            print(option,':',config.get(section, option))
        print('')
    print('--------------------------------')
    print(f'Device ID: {deviceId}')
    print('--------------------------------')

# Read config file
config = configparser.ConfigParser()
core_v2_config = '/mount2/bssoft/config.txt'
else_config = '/boot/bssoft/config.txt'
if os.path.exists(core_v2_config):
    config.read(core_v2_config)
elif os.path.exists(else_config):
    config.read(else_config)
else:
    config.read('./config.ini') 

# Initialize the directory
for dir in config['files'].keys():
    if dir.endswith('dir'):
        os.makedirs(config['files'][dir], exist_ok=True)

# Initialize device ID
if os.path.exists(f'{config["device"]["settings_dir"]}/id.txt'):
    deviceId = open(f'{config["device"]["settings_dir"]}/id.txt', 'r').read()
else:
    deviceId = int(time())
    open('id.txt', 'w').write(str(deviceId))
    subprocess.Popen(f'sudo cp id.txt {config["device"]["settings_dir"]}/', shell=True)

# Add properties of audio card
if config.get('audio', 'audio_card') == 'core_v2':
    config.set('audio', 'mixer_control', 'Playback')
    config.set('audio', 'cardindex', '0')
    config.set('audio', 'deviceindex', '1')
elif config.get('audio', 'audio_card') == 'bank':
    config.set('audio', 'mixer_control', 'PCM')
    config.set('audio', 'cardindex', '1')
    config.set('audio', 'deviceindex', '0')
else:
    config.set('audio', 'mixer_control', 'Playback')
    config.set('audio', 'cardindex', '1')
    config.set('audio', 'deviceindex', '0')
    
# Calculate number of frames for one single chunk
num_frame = config.getint('audio', 'rate') / config.getint('audio', 'chunk') * config.getint('files', 'record_seconds')
config.set('audio', 'num_frame', str(math.ceil(num_frame))) # num_frame is always greater than target seconds
# Calculate number of chunks for one single file
num_sending_bundle = config.getint('files', 'sending_record_seconds')/config.getint('files', 'record_seconds')
if not math.isclose(num_sending_bundle, int(num_sending_bundle)):
    raise Exception("sending_record_seconds divided by record_seconds is NOT INTEGER!")
config.set('files', 'num_sending_bundle', str(int(num_sending_bundle)))

# Set logger
logger = Logger(name=config['device']['name'], logdir=config['files']['log_dir'], level=config['files']['log_level'])

