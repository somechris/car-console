from .AudioCarComponent import AudioCarComponent


class EmergencyLight(AudioCarComponent):
    def __init__(self, button, relais):
        super(EmergencyLight, self).__init__()
        self.button = button
        self.relais = relais

        self.relais.value = False

    def step(self, time):
        super(EmergencyLight, self).step(time)

        self.relais.value = self.button.is_pressed

        if self.button.is_pressed:
            self.audio_loop = 'siren'
