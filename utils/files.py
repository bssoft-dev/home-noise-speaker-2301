from pathlib import Path
import os

def create_vol_file(value):
    for file in os.listdir('../'):
        if file.endswith('.vol'):
            os.remove(f'../{file}')
    Path(f"../{value}.vol").touch()