import os
from pydub import AudioSegment

def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)


def mix_by_ratio(files: list, ratios: list, dir="sounds"):
    audios = files.copy()
    for i, file in enumerate(files):
        print(i)
        audios[i] = AudioSegment.from_wav(os.path.join(dir, file))
        print(audios[i].dBFS)
        audio = match_target_amplitude(audios[i], audios[i].dBFS*(0.5/ratios[i]))
        print(audio.dBFS)
        if i != 0:
            audios[i] = audios[i-1].overlay(audio)
    audios[-1].export("mixed.wav", format="wav")
    return "mixed.wav"


if __name__=="__main__":
    mix_by_ratio(["singingball.wav", "자연의 소리.wav"], [0.7, 0.3])
