import wave
def open_wav_file(filename: str, sample_rate: int) -> None:
    with wave.open(filename, 'rb') as wav:
        print(f'Sample rate: {wav.getframerate()} Hz')
open_wav_file('test.wav', 44100)