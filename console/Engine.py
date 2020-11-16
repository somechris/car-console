import logging

from .AudioCarComponent import AudioCarComponent

logger = logging.getLogger(__name__)


class Engine(AudioCarComponent):
    def __init__(self, starter_button, led, gear_1_button, gear_2_button,
                 gear_3_button, gear_4_button, gear_5_button, gear_R_button):
        super(Engine, self).__init__()
        self.starter_button = starter_button
        self.led = led
        self.gear_1_button = gear_1_button
        self.gear_2_button = gear_2_button
        self.gear_3_button = gear_3_button
        self.gear_4_button = gear_4_button
        self.gear_5_button = gear_5_button
        self.gear_R_button = gear_R_button

        self.running = False
        self.stop_time = 0
        self.start_time = 0
        self.last_gear = 'N'
        self.last_proper_gear = '1'
        self.to_neutral_time = 0

        self.led.value = False

    def get_gear(self):
        if self.gear_1_button.is_pressed:
            return '1'
        elif self.gear_2_button.is_pressed:
            return '2'
        elif self.gear_3_button.is_pressed:
            return '3'
        elif self.gear_4_button.is_pressed:
            return '4'
        elif self.gear_5_button.is_pressed:
            return '5'
        elif self.gear_R_button.is_pressed:
            return 'R'
        return 'N'

    def stop(self, time, grind=False):
        logger.debug('Engine stopped')
        self.stop_time = time
        self.running = False
        self.reset_audio()
        self.audio_once = 'engine-%s' % ('wrong-gear' if grind else 'stop')

    def step(self, time):
        super(Engine, self).step(time)

        gear = self.get_gear()
        if self.running:
            self.audio_loop = 'engine-gear-%s' % (gear)

            if self.last_gear != gear and gear != 'N':
                # There was a change to a proper gear
                if self.to_neutral_time < time - 4:
                    # It's long ago that we had a proper gear, so we need to
                    # start afresh.
                    if gear in ['1', 'R']:
                        self.audio_once = 'engine-shift-up'
                    else:
                        self.stop(time, grind=True)
                else:
                    # We saw a proper gear recently. So we need to check if
                    # the change is sane
                    if ord(gear) == ord(self.last_proper_gear) + 1:
                        # Shift one gear up
                        self.audio_once = 'engine-shift-up'
                    elif ord(gear) == ord(self.last_proper_gear) - 1:
                        # Shift one gear down
                        self.audio_once = 'engine-shift-down'
                    elif gear != self.last_proper_gear:
                        # Neither one up or down and also not to same gear, so
                        # we motor stops
                        self.stop(time, grind=True)

            if self.starter_button.is_pressed and self.start_time < time - 2:
                self.stop(time)

            self.led.value = True
        else:
            if self.stop_time < time - 5:
                if self.starter_button.is_pressed:
                    if gear == 'N':
                        self.start_time = time
                        self.running = True
                        self.audio_once = 'engine-start'
                        logger.debug('Engine started')
                    else:
                        self.stop(time, grind=True)
                self.led.value = ((int(time * 2) % 3) == 0)
            else:
                self.led.value = False

        if self.last_gear != 'N' and gear == 'N':
            self.to_neutral_time = time

        self.last_gear = gear
        if gear != 'N':
            self.last_proper_gear = gear
