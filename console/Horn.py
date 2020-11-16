from .AudioCarComponent import AudioCarComponent


class Horn(AudioCarComponent):
    def __init__(self, button):
        super(Horn, self).__init__()
        self.button = button

    def step(self, time):
        super(Horn, self).step(time)
        if self.button.is_pressed:
            self.audio_loop = 'horn'
