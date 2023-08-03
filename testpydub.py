from pydub import AudioSegment
from pydub.playback import play

audio = AudioSegment.from_mp3("./mp3/TaylorSwift-ICanSeeYou.mp3")
play(audio)