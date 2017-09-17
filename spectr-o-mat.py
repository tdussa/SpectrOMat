#! /usr/bin/env python
# -*- coding: utf-8 -*-

try:
    # for Python2
    from Tkinter import *   ## notice capitalized T in Tkinter
except ImportError:
    # for Python3
    from tkinter import *   ## notice here too
from math import log
import numpy
from datetime import datetime
import signal

# Plotting
import matplotlib.pyplot as plot

# SeaBreeze USB spectrometer access library
import seabreeze
seabreeze.use("pyseabreeze")
import seabreeze.spectrometers as sb


# Global control variable
run_measurement = False


# Interrupt handling
def catch_sigint(signal, frame):
    global run_measurement
    if run_measurement:
        run_measurement = False
    else:
        sys.exit(0)


class SpectrOMat:
    @staticmethod
    def initialize(root, device='#0', integration_time_micros=100000, reset_after=1):
        """Initialize the entire UI."""
        try:
            if (device[0] == '#'):
                SpectrOMat.spectrometer = sb.Spectrometer(sb.list_devices()[int(device[1:])])
            else:
                SpectrOMat.spectrometer = sb.Spectrometer.from_serial_number(device)
        except:
            print('ERROR: Could not initialize device "' + device + '"!')
            print('Available devices:')
            index = 0
            for dev in sb.list_devices():
                print(' - #' + str(index) + ':', 'Model:', dev.model + '; serial number:', dev.serial)
                index += 1
            sys.exit(1)

        # Initialize darkness correction
        SpectrOMat.darkness_correction = [0.0]*(len(SpectrOMat.spectrometer.wavelengths()))

        # Define the layout elements
        SpectrOMat.reset_after = Scale(root, from_=0, to=100000, label='Reset after', orient=HORIZONTAL)
        SpectrOMat.reset_after.set(reset_after)
        SpectrOMat.integration_time = Scale(root, from_=SpectrOMat.spectrometer.minimum_integration_time_micros, to=10000000000, label='Integration time', orient=HORIZONTAL)
        SpectrOMat.integration_time.set(integration_time_micros)
        SpectrOMat.button_start = Button(root, text='Start Measurement', command=SpectrOMat.measure)
        SpectrOMat.button_darkness = Button(root, text='Get Darkness Correction', command=SpectrOMat.get_darkness_correction)
        SpectrOMat.button_exit = Button(root, text='Exit', command=SpectrOMat.exit)

        # Define the layout
        SpectrOMat.reset_after.grid(column=0, row=0, rowspan=3)
        SpectrOMat.integration_time.grid(column=0, row=3, rowspan=3)
        SpectrOMat.button_start.grid(column=0, row=6)
        SpectrOMat.button_darkness.grid(column=0, row=7)
        SpectrOMat.button_exit.grid(column=0, row=8)

    @staticmethod
    def measure():
        global run_measurement
        run_measurement = True
        SpectrOMat.spectrometer.integration_time_micros(SpectrOMat.integration_time.get())
        reset_after = SpectrOMat.reset_after.get()
        measurement = 0
        while run_measurement:
            newData = list(map(lambda x,y:x-y, SpectrOMat.spectrometer.intensities(), SpectrOMat.darkness_correction))
            if (measurement == 0):
                data = newData
            else:
                data = list(map(lambda x,y:x+y, data, newData))
            measurement += 1
            if (reset_after > 0):
                measurement %= reset_after
            print(data)

    @staticmethod
    def get_darkness_correction():
        SpectrOMat.spectrometer.integration_time_micros(SpectrOMat.integration_time.get())
        measurement = 0
        while measurement < 1:
            newData = SpectrOMat.spectrometer.intensities()
            if (measurement == 0):
                data = newData
            else:
                data = list(map(lambda x,y:x+y, data, newData))
            measurement += 1
        SpectrOMat.darkness_correction = list(map(lambda x:x/measurement, data))
        print(SpectrOMat.darkness_correction)


    @staticmethod
    def exit():
        sys.exit(0)


def main(device='#0', integration_time_micros=100000, reset_after=1):
    root = Tk()
    root.title('Spectr-O-Mat')
    SpectrOMat.initialize(root, device, integration_time_micros, reset_after)
    root.mainloop()

if __name__ == "__main__":
    # Parse args
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-d', '--device', dest='device', default='#0', help='input device to use; "<serial number>" or "#<device number>" (default: #0)')
    parser.add_argument('-r', '--reset_after', dest='reset_after', default='1', help='reset after n measurement cycles with 0 meaning indefinite (default: 1)')
    parser.add_argument('-t', '--integration_time_micros', dest='integration_time_micros', default='100000', help='integration time in microseconds (default: 100000)')
    args = parser.parse_args()

    signal.signal(signal.SIGINT, catch_sigint)

    main(args.device, args.integration_time_micros, args.reset_after)
