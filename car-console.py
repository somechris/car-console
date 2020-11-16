#!/usr/bin/env python3

import os
# The 'PYGAME_HIDE_SUPPORT_PROMPT' environment variable does not help
# with Debian buster's version of pygame. So we resort to temporarily
# redirecting stdout. Yikes!
import contextlib
with contextlib.redirect_stdout(None):
    import pygame

import time
import subprocess
import gpiozero
import logging
import argparse

IO_TURN_SIGNAL_LEFT_BUTTON = gpiozero.Button("GPIO2")
IO_TURN_SIGNAL_RIGHT_BUTTON = gpiozero.Button("GPIO3")
IO_HORN_BUTTON = gpiozero.Button("GPIO4")
IO_EMERGENCY_BUTTON = gpiozero.Button("GPIO17")
IO_EMERGENCY_LIGHT_BUTTON = gpiozero.Button("GPIO27")
IO_STARTER_BUTTON = gpiozero.Button("GPIO22")

IO_EMERGENCY_LIGHT_RELAIS = gpiozero.DigitalOutputDevice("GPIO14")
IO_TURN_SIGNAL_LEFT_LED = gpiozero.LED("GPIO15")
IO_TURN_SIGNAL_RIGHT_LED = gpiozero.LED("GPIO18")
IO_ENGINE_RUNNABLE_LED = gpiozero.LED("GPIO23")
IO_ENGINE_RUNNING_LED = gpiozero.LED("GPIO24")

IO_MUSIC_BACK_BUTTON = gpiozero.Button("GPIO10")
IO_MUSIC_PLAY_BUTTON = gpiozero.Button("GPIO9")
IO_MUSIC_FORWARD_BUTTON = gpiozero.Button("GPIO11")

IO_GEAR_1_BUTTON = gpiozero.Button("GPIO0")
IO_GEAR_2_BUTTON = gpiozero.Button("GPIO5")
IO_GEAR_3_BUTTON = gpiozero.Button("GPIO6")
IO_GEAR_4_BUTTON = gpiozero.Button("GPIO13")
IO_GEAR_5_BUTTON = gpiozero.Button("GPIO19")
IO_GEAR_R_BUTTON = gpiozero.Button("GPIO26")

USB_DEVICE = '/dev/disk/by-path/platform-3f980000.usb-usb-0:1.4:1.0-scsi-0:0:0:0-part1'
MOUNT_DIR = 'media'

LOOPS_PER_SECOND = 50

LOG_FORMAT = '%(asctime)s.%(msecs)03d %(levelname)-5s [%(threadName)s] %(filename)s:%(lineno)d - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


class CarComponent(object):
    def step(self, time):
        pass


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


class Horn(AudioCarComponent):
    def __init__(self, button):
        super(Horn, self).__init__()
        self.button = button

    def step(self, time):
        super(Horn, self).step(time)
        if self.button.is_pressed:
            self.audio_loop = 'horn'


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

        pressed = self.signal_button.is_pressed or self.emergency_button.is_pressed

        self.led.value = phase and pressed

        self.audio_once = 'turn-signal' if (self.last_phase != phase) and pressed else None

        self.last_phase = phase


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


class Engine(AudioCarComponent):
    def __init__(self, starter_button, led, gear_1_button, gear_2_button, gear_3_button, gear_4_button, gear_5_button, gear_R_button):
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
                    # It's long ago that we had a proper gear, so we need to start afresh
                    if gear in ['1', 'R']:
                        self.audio_once = 'engine-shift-up'
                    else:
                        self.stop(time, grind=True)
                else:
                    # We saw a proper gear recently. So we need to check if the change is sane

                    if ord(gear) == ord(self.last_proper_gear) + 1:
                        # Shift one gear up
                        self.audio_once = 'engine-shift-up'
                    elif ord(gear) == ord(self.last_proper_gear) - 1:
                        # Shift one gear down
                        self.audio_once = 'engine-shift-down'
                    elif gear != self.last_proper_gear:
                        # Neither one up or down and also not to same gear, so we motor stops
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


class Battery(CarComponent):
    def __init__(self, led):
        super(Battery, self).__init__()
        self.led = led

        self.led.value = False

    def step(self, time):
        super(Battery, self).step(time)
        self.led.value = True


class TwoStateButton(object):
    def __init__(self, button, value_short=None, value_long=None, long_interval=0.4):
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

        elif self.last_pressed and self.press_start_time >= time - self.long_interval:
            ret = self.value_short

        self.last_pressed = self.button.is_pressed

        return ret


class RadioKeyboard(object):
    def __init__(self, back_button, play_button, forward_button):
        super(RadioKeyboard, self).__init__()
        self.back_button = TwoStateButton(back_button, '<', '\033[D')
        self.play_button = TwoStateButton(play_button, ' ', 'toggle-silencing', 2)
        self.forward_button = TwoStateButton(forward_button, '>', '\033[C')

    def get_key(self, time):
        key = self.play_button.get_value(time)
        if key is None:
            key = self.back_button.get_value(time)
        if key is None:
            key = self.forward_button.get_value(time)
        return key


class Radio(AudioCarComponent):
    def __init__(self, device, mount_dir, back_button, play_button, forward_button):
        super(Radio, self).__init__()
        self.device = device
        self.mount_dir = mount_dir
        self.keyboard = RadioKeyboard(back_button, play_button, forward_button)
        self.player_process = None
        self.silence_others = True

        os.makedirs(self.mount_dir, exist_ok=True)

    def device_present(self):
        return os.path.exists(self.device)

    def run(self, command, sudo=False, wait=True):
        if sudo:
            command = ['sudo'] + command
        logger.debug('Executing in %s: %s' % ('foreground' if wait else 'background', str(command)))
        if wait:
            try:
                completed = subprocess.run(command, timeout=1)
                return completed.returncode == 0
            except Exception:
                return False
        else:
            return subprocess.Popen(
                args=command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                bufsize=0, text=True)

    def mount(self):
        command = [
            '/bin/mount',
            '-o', 'defaults,noexec,ro,errors=continue',
            self.device,
            self.mount_dir]
        return self.run(command=command, sudo=True)

    def unmount(self):
        command = ['/bin/umount', '-f', self.mount_dir]
        return self.run(command=command, sudo=True)

    def get_media_files(self):
        media_files = []
        for root, dirs, files in os.walk(self.mount_dir):
            for file in files:
                if len(file) > 4 and file[-4] == '.':
                    ending = file[-3:].lower()
                    if ending in ['mp3', 'wav', 'ogg']:
                        full_name = os.path.join(root, file)
                        media_files.append(full_name)
        return media_files

    def launch_player(self):
        command = ['/usr/bin/mplayer', '-loop', '0'] + self.get_media_files()
        self.player_process = self.run(command, wait=False)

    def stop_player(self):
        ret = True
        if self.player_process is not None:
            process = self.player_process
            self.player_process = None
            process.kill()
            process.communicate()

        return False

    def start(self):
        self.stop()
        if self.mount():
            self.launch_player()
        self.audio_once = 'media-inject'

    def stop(self):
        self.stop_player()
        self.unmount()
        self.audio_once = 'media-eject'

    def step(self, time):
        super(Radio, self).step(time)

        present = self.device_present()

        if present:
            if self.player_process is not None:
                if self.player_process.poll() is not None:
                    self.player_process = None

            if self.player_process is None:
                self.start()

            if self.silence_others:
                self.silence_loop()

            key = self.keyboard.get_key(time)
            if key == 'toggle-silencing':
                self.silence_others = not self.silence_others
                key = None
            if key is not None:
                try:
                    self.player_process.stdin.write(key)
                except Exception as e:
                    pass

        else:
            if self.player_process is not None:
                self.stop()


class AudioOutput(object):
    def __init__(self):
        self.loop_name = 'silence'
        self.sounds = {}

        SIZE = 4096
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


class Car(object):
    def __init__(self):
        logger.debug('Initializing car')

        self.audio_output = AudioOutput()

        self.components = [
            Battery(IO_ENGINE_RUNNABLE_LED),
            Engine(IO_STARTER_BUTTON, IO_ENGINE_RUNNING_LED, IO_GEAR_1_BUTTON, IO_GEAR_2_BUTTON, IO_GEAR_3_BUTTON, IO_GEAR_4_BUTTON, IO_GEAR_5_BUTTON, IO_GEAR_R_BUTTON),
            TurnSignal(IO_TURN_SIGNAL_LEFT_BUTTON, IO_EMERGENCY_BUTTON, IO_TURN_SIGNAL_LEFT_LED),
            TurnSignal(IO_TURN_SIGNAL_RIGHT_BUTTON, IO_EMERGENCY_BUTTON, IO_TURN_SIGNAL_RIGHT_LED),
            EmergencyLight(IO_EMERGENCY_LIGHT_BUTTON, IO_EMERGENCY_LIGHT_RELAIS),
            Radio(USB_DEVICE, MOUNT_DIR, IO_MUSIC_BACK_BUTTON, IO_MUSIC_PLAY_BUTTON, IO_MUSIC_FORWARD_BUTTON),
            Horn(IO_HORN_BUTTON),
            ]
        logger.debug('Car initialized')

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

        delay = 1.0/LOOPS_PER_SECOND
        while True:
            self.step(time.time())
            time.sleep(delay)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Car console controller',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='Increase verbosity')
    args = parser.parse_args()
    if args.verbose > 0:
        logger.setLevel(logging.DEBUG)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    Car().run()
