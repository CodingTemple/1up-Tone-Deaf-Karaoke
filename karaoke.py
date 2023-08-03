import os
import re
import time
import shutil
import threading
from collections import deque
from pydub import AudioSegment
from pydub.playback import _play_with_ffplay_suppress as play
from colorama import Fore, Back, Style
import sounddevice as sd
import soundfile as sf
from pyfiglet import Figlet
import numpy as np

def play_microphone(recording_buffer=[]):
    fs = 44100  # Sample rate
    buffer = deque(maxlen=10)

    def callback(indata, outdata, frames, time, status):
        # if status:  # This is here for debugging purposes only
        #     print(status)

        buffer.append(indata.copy())
        recording_buffer.extend(indata.copy())

        if buffer:
            audio_data = buffer.popleft()
            outdata[:] = audio_data

    stream = sd.Stream(callback=callback, channels=2, samplerate=fs)
    stream.start()
    return stream, recording_buffer


def stop_microphone(stream, recording_buffer, filename=None):
    stream.stop()
    if filename:
        sf.write(filename, np.array(recording_buffer, dtype=np.float32), 44100)
    recording_buffer.clear()
    stream.close()


def sanitize_filename(filename):
    return filename.replace(' ', '_').replace('-', '_')


def center_text(text):
    terminal_width = shutil.get_terminal_size().columns
    return text.center(terminal_width)


def remove_vocals(audio_path):
    audio_filename = os.path.basename(audio_path).split('.')[0]
    accompaniment_path = f"output_folder/{audio_filename}/accompaniment.wav"
    if not os.path.exists(accompaniment_path):
        command = f'spleeter separate {audio_path} -o ./output_folder'
        os.system(command)
    return AudioSegment.from_wav(accompaniment_path)


def parse_lrc(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lrc_content = f.read()

    parsed_lyrics = {}
    for line in lrc_content.split("\n"):
        if line.startswith("["):
            timestamp, lyric = line.split("]", 1)
            timestamp = timestamp[1:]
            if not any(char.isalpha() for char in timestamp[:2]):
                minutes, seconds = map(float, timestamp.split(":"))
                parsed_lyrics[int(minutes * 60 + seconds)] = lyric.strip()

    return parsed_lyrics


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def play_audio_and_display_lyrics(audio, lrc_file, base_file):
    parsed_lyrics = parse_lrc(lrc_file)
    played_lyrics_buffer = deque(maxlen=4)
    recording_buffer = []

    def display_lyrics():
        start_time = time.time()
        for i, (time_stamp, lyric) in enumerate(parsed_lyrics.items()):
            while time.time() - start_time < time_stamp:
                time.sleep(0.1)
            clear_screen()
            print(Back.BLACK)
            terminal_height = shutil.get_terminal_size().lines

            if i <= 4:
                print('\n' * ((terminal_height // 2) - 6 + 5 - i), end='')
            else:
                print('\n' * ((terminal_height // 2) - 6), end='')
            for pl in played_lyrics_buffer:
                print(Fore.MAGENTA, center_text(pl))

            print(Fore.LIGHTMAGENTA_EX, center_text(lyric))
            played_lyrics_buffer.append(lyric)

    stream, recording_buffer = play_microphone(recording_buffer)
    audio_thread = threading.Thread(target=play, args=(audio,))
    vocals_thread = threading.Thread(target=display_lyrics)

    vocals_thread.start()
    audio_thread.start()
    vocals_thread.join()
    audio_thread.join()
    print(base_file)

    stop_microphone(stream, recording_buffer, f"./my_recordings_temp/{base_file}.wav")
    combine_audio(base_file)


def combine_audio(base_file):
    output_vocals_file = f"./my_recordings_temp/{base_file}.wav"
    output_vocals_mp3_file = f"./my_recordings/{base_file}.mp3"
    accompaniment_path = f"./output_folder/{base_file}/accompaniment.wav"
    vocals = AudioSegment.from_wav(output_vocals_file)
    accompaniment = AudioSegment.from_wav(accompaniment_path)
    combined = vocals.overlay(accompaniment)
    combined.export(output_vocals_mp3_file, format="mp3")
    os.remove(output_vocals_file)


def find_songs(directory):
    files = [os.path.splitext(entry.name)[0] for entry in os.scandir(directory) if entry.is_file()]
    return files


def main():
    while True:
        clear_screen()
        print(Style.RESET_ALL)
        print(Back.BLACK, Fore.RED)

        title = Figlet(font="caligraphy")
        print('\n', title.renderText('ReDub'), '\n')

        print("Pick Your Song")
        SONGS = sorted(find_songs('./mp3'))

        for num, track in enumerate(SONGS):
            artist, title = re.match(r'(.+) ?- ?(.+)', track).groups()
            artist = artist.replace('_', ' ')
            title = title.replace('_', ' ')
            print(f"{str(num + 1).rjust(3)} | {artist.ljust(20)} | {title}")

        print("- press ctrl-c to exit at any time -")
        user_input = input("What is your choice? ")

        if not user_input.isdigit() or int(user_input) not in range(1, len(SONGS) + 1):
            print("Invalid input")
            continue

        print("Processing...")
        audio = remove_vocals(f'./mp3/{SONGS[int(user_input) - 1]}.mp3')
        clear_screen()
        play_audio_and_display_lyrics(audio, f'./lrc/{SONGS[int(user_input) - 1]}.lrc', SONGS[int(user_input) - 1])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\rThanks for Singing")
        print(Style.RESET_ALL)
