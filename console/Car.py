import logging
import time

from .AudioOutput import AudioOutput
from .AudioCarComponent import AudioCarComponent

logger = logging.getLogger(__name__)


class Car(object):
    def __init__(self, simulation_frequency=50):
        logger.debug('Initializing ...')

        self.audio_output = AudioOutput()
        self.components = []
        self.simulation_frequency = simulation_frequency
        logger.debug('Initialized')

    def add(self, component):
        self.components.append(component)

    def step(self, time):
        audio_loop = None
        for component in self.components:
            component.step(time)

            if isinstance(component, AudioCarComponent):
                if component.audio_once is not None:
                    self.audio_output.play(component.audio_once)

                if component.audio_loop is not None:
                    audio_loop = component.audio_loop

        self.audio_output.loop(audio_loop)

    def run(self):
        logger.debug('Starting car main loop')

        delay = 1.0 / self.simulation_frequency
        while True:
            self.step(time.time())
            time.sleep(delay)
