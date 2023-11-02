from pathlib import Path
import os

def create_vol_file(value):
    for file in os.listdir('../'):
        if file.endswith('.vol'):
            os.remove(f'../{file}')
    Path(f"../{value}.vol").touch()

def change_audio_order(audio_list):
    if "새소리9.wav" in audio_list and "새소리10.wav" in audio_list:
        index_9 = audio_list.index("새소리9.wav")
        index_10 = audio_list.index("새소리10.wav")
        if index_9 < index_10:
            audio_list.remove("새소리10.wav")
            audio_list.insert(index_9 + 1, "새소리10.wav")
            return audio_list
        else:
            audio_list.remove("새소리10.wav")
            audio_list.insert(index_9, "새소리10.wav")
            return audio_list
    else:
        print("해당 오디오 파일이 목록에 존재하지 않습니다.")
        return audio_list
