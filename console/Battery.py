from .CarComponent import CarComponent


class Battery(CarComponent):
    def __init__(self, led):
        super(Battery, self).__init__()
        self.led = led

        self.led.value = False

    def step(self, time):
        super(Battery, self).step(time)
        self.led.value = True
