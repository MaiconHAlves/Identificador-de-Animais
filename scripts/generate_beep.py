import wave
import struct
import math

def generate_beep(filename="assets/beep.wav", duration=0.1, freq=1000.0):
    import os
    if not os.path.exists("assets"):
        os.makedirs("assets")
        
    sample_rate = 44100.0
    num_samples = int(duration * sample_rate)
    
    with wave.open(filename, "w") as wav_file:
        wav_file.setparams((1, 2, int(sample_rate), num_samples, "NONE", "not compressed"))
        for i in range(num_samples):
            value = int(32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            wav_file.writeframes(struct.pack('h', value))

if __name__ == "__main__":
    generate_beep()
    print("Bipe tático gerado em assets/beep.wav")
