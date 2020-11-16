from .CarComponent import CarComponent


class AudioCarComponent(CarComponent):
    def __init__(self):
        super(AudioCarComponent, self).__init__()
        self.reset_audio()

    def reset_audio(self):
        self.audio_loop = None
        self.audio_once = None

    def silence_loop(self):
        self.audio_loop = 'silence'

    def step(self, time):
        super(AudioCarComponent, self).step(time)
        self.reset_audio()
