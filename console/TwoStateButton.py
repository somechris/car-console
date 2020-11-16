class TwoStateButton(object):
    def __init__(self, button, value_short=None, value_long=None,
                 long_interval=0.4):
        self.button = button
        self.value_short = value_short
        self.value_long = value_long
        self.value_undecided = ''
        self.long_interval = long_interval

        self.last_pressed = False
        self.press_start_time = 0
        self.last_send_time = 0

    def get_value(self, time):
        ret = None
        if self.button.is_pressed:
            ret = self.value_undecided
            if not self.last_pressed:
                self.press_start_time = time
                self.last_send_time = time

            if self.last_send_time <= time - self.long_interval:
                ret = self.value_long
                self.last_send_time = time

        elif self.last_pressed \
                and self.press_start_time >= time - self.long_interval:
            ret = self.value_short

        self.last_pressed = self.button.is_pressed

        return ret
