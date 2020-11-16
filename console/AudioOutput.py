# The 'PYGAME_HIDE_SUPPORT_PROMPT' environment variable does not help
# with Debian buster's version of pygame. So we resort to temporarily
# redirecting stdout. Yikes!
import contextlib
with contextlib.redirect_stdout(None):
    import pygame

import logging
import os

logger = logging.getLogger(__name__)


class AudioOutput(object):
    def __init__(self):
        self.loop_name = 'silence'
        self.sounds = {}

        pygame.mixer.init(44100, -16, 2, 4096)

        self.load_sounds()

    def get_sound_directory(self, kind):
        return os.path.join('sounds', kind)

    def load_sounds(self):
        samples_dir = self.get_sound_directory('samples')
        for file_relative in os.listdir(samples_dir):
            name = file_relative.rsplit('.', 2)[0]
            file_absolute = os.path.join(samples_dir, file_relative)
            self.sounds[name] = pygame.mixer.Sound(file_absolute)
            logger.debug('Loading sound \'%s\' ...' % (file_absolute))

    def loop(self, name):
        if name is None:
            name = 'silence'

        if name != self.loop_name:
            logger.debug('Playing loop %s' % (name))
            self.loop_name = name
            loops_dir = self.get_sound_directory('loops')
            file_name = os.path.join(loops_dir, name + '.wav')
            pygame.mixer.music.load(file_name)
            pygame.mixer.music.play(-1)

    def play(self, name):
        logger.debug('Playing sample %s' % (name))
        pygame.mixer.Sound.play(self.sounds[name])
