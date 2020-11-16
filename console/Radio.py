import logging
import os
import subprocess

from .AudioCarComponent import AudioCarComponent
from .RadioKeyboard import RadioKeyboard

logger = logging.getLogger(__name__)


class Radio(AudioCarComponent):
    def __init__(self, device, mount_dir, back_button, play_button,
                 forward_button):
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
        environment = 'foreground' if wait else 'background'
        logger.debug('Executing in %s: %s' % (environment, str(command)))
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
        if self.player_process is not None:
            process = self.player_process
            self.player_process = None
            process.kill()
            process.communicate()

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
                except Exception:
                    logger.exception("Failed to write %s to mplayer" % (key))

        else:
            if self.player_process is not None:
                self.stop()
