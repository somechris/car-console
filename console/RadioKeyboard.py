from .TwoStateButton import TwoStateButton


class RadioKeyboard(object):
    def __init__(self, back_button, play_button, forward_button):
        super(RadioKeyboard, self).__init__()
        TSB = TwoStateButton
        self.back_button = TSB(back_button, '<', '\033[D')
        self.play_button = TSB(play_button, ' ', 'toggle-silencing', 2)
        self.forward_button = TSB(forward_button, '>', '\033[C')

    def get_key(self, time):
        key = self.play_button.get_value(time)
        if key is None:
            key = self.back_button.get_value(time)
        if key is None:
            key = self.forward_button.get_value(time)
        return key
