from .AudioCarComponent import AudioCarComponent


class TurnSignal(AudioCarComponent):
    def __init__(self, signal_button, emergency_button, led):
        super(TurnSignal, self).__init__()
        self.signal_button = signal_button
        self.emergency_button = emergency_button
        self.led = led
        self.last_phase = 0

        self.led.value = False

    def step(self, time):
        super(TurnSignal, self).step(time)
        phase = (int(time * 2) % 2) == 0

        pressed = self.signal_button.is_pressed \
            or self.emergency_button.is_pressed

        self.led.value = phase and pressed

        self.audio_once = 'turn-signal' if (self.last_phase != phase) \
            and pressed else None

        self.last_phase = phase
