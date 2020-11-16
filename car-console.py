#!/usr/bin/env python3

import os

import gpiozero
import logging
import argparse

import console

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

USB_DEVICE = ('/dev/disk/by-path/'
              'platform-3f980000.usb-usb-0:1.4:1.0-scsi-0:0:0:0-part1')
MOUNT_DIR = 'media'

SIMULATION_FREQUENCY = 50  # updates per second

LOG_FORMAT = ('%(asctime)s.%(msecs)03d %(levelname)-5s [%(threadName)s] '
              '%(filename)s:%(lineno)d - %(message)s')
LOG_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


def build_car():
    car = console.Car(simulation_frequency=SIMULATION_FREQUENCY)

    car.add(console.Battery(IO_ENGINE_RUNNABLE_LED))
    car.add(console.Engine(IO_STARTER_BUTTON, IO_ENGINE_RUNNING_LED,
                           IO_GEAR_1_BUTTON, IO_GEAR_2_BUTTON,
                           IO_GEAR_3_BUTTON, IO_GEAR_4_BUTTON,
                           IO_GEAR_5_BUTTON, IO_GEAR_R_BUTTON))

    car.add(console.TurnSignal(IO_TURN_SIGNAL_LEFT_BUTTON,
                               IO_EMERGENCY_BUTTON, IO_TURN_SIGNAL_LEFT_LED))
    car.add(console.TurnSignal(IO_TURN_SIGNAL_RIGHT_BUTTON,
                               IO_EMERGENCY_BUTTON, IO_TURN_SIGNAL_RIGHT_LED))
    car.add(console.EmergencyLight(IO_EMERGENCY_LIGHT_BUTTON,
                                   IO_EMERGENCY_LIGHT_RELAIS))

    car.add(console.Radio(USB_DEVICE, MOUNT_DIR, IO_MUSIC_BACK_BUTTON,
                          IO_MUSIC_PLAY_BUTTON, IO_MUSIC_FORWARD_BUTTON))
    car.add(console.Horn(IO_HORN_BUTTON))

    return car


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

    car = build_car()
    car.run()
