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
import time

# Plotting
import matplotlib.pyplot as plot

# SeaBreeze USB spectrometer access library
import seabreeze
seabreeze.use("pyseabreeze")
import seabreeze.spectrometers as sb


# Global control variable
root = Tk()


class SpectrOMat:
    @staticmethod
    def initialize(root, device='#0', scan_time=100000, reset_after=1, timestamp='%Y-%m-%dT%H:%M:%S%z', couple_times=True):
        """Initialize the entire UI."""
        try:
            if (device[0] == '#'):
                SpectrOMat.spectrometer = sb.Spectrometer(sb.list_devices()[int(device[1:])])
            else:
                SpectrOMat.spectrometer = sb.Spectrometer.from_serial_number(device)
            SpectrOMat.wavelengths = SpectrOMat.spectrometer.wavelengths()
        except:
            print('ERROR: Could not initialize device "' + device + '"!')
            print('Available devices:')
            index = 0
            for dev in sb.list_devices():
                print(' - #' + str(index) + ':', 'Model:', dev.model + '; serial number:', dev.serial)
                index += 1
            sys.exit(1)

        SpectrOMat.run_measurement = False
        SpectrOMat.repeat_measurement = True
        SpectrOMat.button_startpause_texts = { True: 'Pause Measurement', False: 'Start Measurement' }
        SpectrOMat.button_stopdarkness_texts = { True: 'Stop Measurement', False: 'Get Darkness Correction' }

        SpectrOMat.timestamp = timestamp
        SpectrOMat.repeat = IntVar()
#        SpectrOMat.couple_times = IntVar

        # Initialize variables
        SpectrOMat.darkness_correction = [0.0]*(len(SpectrOMat.spectrometer.wavelengths()))
        SpectrOMat.measurement = 0
        SpectrOMat.data = [0.0]*(len(SpectrOMat.spectrometer.wavelengths()))

        # Plot setup
        plot.ion()

        # Define the layout elements
        SpectrOMat.reset_after = Scale(root, from_=0, to=100000, label='Reset after', orient=HORIZONTAL, command=SpectrOMat.update_reset_after)
        SpectrOMat.reset_after.set(reset_after)

        SpectrOMat.scan_time = Scale(root, from_=SpectrOMat.spectrometer.minimum_integration_time_micros, to=10000000, label='Scan time', orient=HORIZONTAL, command=SpectrOMat.update_scan_time)
        SpectrOMat.scan_time.set(scan_time)

        SpectrOMat.button_startpause_text = StringVar()
        SpectrOMat.button_startpause_text.set(SpectrOMat.button_startpause_texts[SpectrOMat.run_measurement])
        SpectrOMat.button_startpause = Button(root, textvariable=SpectrOMat.button_startpause_text, command=SpectrOMat.startpause)

        SpectrOMat.checkbutton_repeat = Checkbutton(root, text='Auto Repeat', variable=SpectrOMat.repeat)

        SpectrOMat.button_stopdarkness_text = StringVar()
        SpectrOMat.button_stopdarkness_text.set(SpectrOMat.button_stopdarkness_texts[SpectrOMat.run_measurement])
        SpectrOMat.button_stopdarkness = Button(root, textvariable=SpectrOMat.button_stopdarkness_text, command=SpectrOMat.stopdarkness)

        SpectrOMat.button_reset = Button(root, text='Reset', command=SpectrOMat.reset)
        SpectrOMat.button_exit = Button(root, text='Exit', command=SpectrOMat.exit)

        # Define the layout
        SpectrOMat.reset_after.grid(column=0, columnspan=2, row=0, rowspan=3)
        SpectrOMat.scan_time.grid(column=0, columnspan=2, row=3, rowspan=3)
        SpectrOMat.button_startpause.grid(column=0, columnspan=2, row=7)
        SpectrOMat.checkbutton_repeat.grid(column=0, columnspan=2, row=8)
        SpectrOMat.button_stopdarkness.grid(column=0, columnspan=2, row=9)
        SpectrOMat.button_reset.grid(column=0, row=10)
        SpectrOMat.button_exit.grid(column=1, row=10)

    @staticmethod
    def update_reset_after(newValue):
        True

    @staticmethod
    def update_scan_time(newValue):
        SpectrOMat.spectrometer.integration_time_micros(int(newValue))

    @staticmethod
    def startpause():
        SpectrOMat.run_measurement = not SpectrOMat.run_measurement
        SpectrOMat.button_startpause_text.set(SpectrOMat.button_startpause_texts[SpectrOMat.run_measurement])
        SpectrOMat.button_stopdarkness_text.set(SpectrOMat.button_stopdarkness_texts[SpectrOMat.run_measurement])

    @staticmethod
    def stopdarkness():
        if SpectrOMat.run_measurement:
            SpectrOMat.run_measurement = False
            SpectrOMat.button_startpause_text.set(SpectrOMat.button_startpause_texts[SpectrOMat.run_measurement])
            SpectrOMat.button_stopdarkness_text.set(SpectrOMat.button_stopdarkness_texts[SpectrOMat.run_measurement])
            SpectrOMat.measurement = 0
        else:
            newData = SpectrOMat.spectrometer.intensities()
            SpectrOMat.darkness_correction = newData
            print('Darkness correction:', SpectrOMat.darkness_correction)

    @staticmethod
    def reset():
        SpectrOMat.run_measurement = False
        SpectrOMat.button_startpause_text.set(SpectrOMat.button_startpause_texts[SpectrOMat.run_measurement])
        SpectrOMat.button_stopdarkness_text.set(SpectrOMat.button_stopdarkness_texts[SpectrOMat.run_measurement])
        SpectrOMat.darkness_correction = [0.0]*(len(SpectrOMat.spectrometer.wavelengths()))
        SpectrOMat.measurement = 0

    @staticmethod
    def exit():
        sys.exit(0)


    @staticmethod
    def measure():
        if SpectrOMat.run_measurement:
            reset_after = SpectrOMat.reset_after.get()
            newData = list(map(lambda x,y:x-y, SpectrOMat.spectrometer.intensities(), SpectrOMat.darkness_correction))
            if (SpectrOMat.measurement == 0):
                SpectrOMat.data = newData
            else:
                SpectrOMat.data = list(map(lambda x,y:x+y, SpectrOMat.data, newData))
            SpectrOMat.measurement += 1
            plot.clf()
            plot.suptitle(time.strftime(SpectrOMat.timestamp, time.gmtime()) +
                         ' (sum of ' + str(SpectrOMat.measurement) + ' measurement(s)' +
                         ' with integration time ' + str(SpectrOMat.scan_time.get()) + ' µs)')
            plot.xlabel('Wavelengths [nm]')
            plot.ylabel('Intensities [count]')
            plot.plot(SpectrOMat.wavelengths, SpectrOMat.data)
            plot.show()
            plot.pause(0.0001)
            if (reset_after > 0):
                SpectrOMat.measurement %= reset_after
            if (SpectrOMat.measurement == 0):
                print(time.strftime(SpectrOMat.timestamp, time.gmtime()), SpectrOMat.data) 
                if SpectrOMat.repeat.get() == 0:
                    SpectrOMat.run_measurement = False
                    SpectrOMat.button_startpause_text.set(SpectrOMat.button_startpause_texts[SpectrOMat.run_measurement])
                    SpectrOMat.button_stopdarkness_text.set(SpectrOMat.button_stopdarkness_texts[SpectrOMat.run_measurement])

        root.after(1, SpectrOMat.measure)


def main(device='#0', scan_time=100000, reset_after=1, timestamp='%Y-%m-%dT%H:%M:%S%z'):
    global root
    root.title('Spectr-O-Mat')
    SpectrOMat.initialize(root, device, scan_time, reset_after, timestamp)
    root.after(1, SpectrOMat.measure)
    root.mainloop()

if __name__ == "__main__":
    # Parse args
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-d', '--device', dest='device', default='#0', help='input device to use; "<serial number>" or "#<device number>" (default: #0)')
    parser.add_argument('-r', '--reset_after', dest='reset_after', default='1', help='reset after n measurement cycles with 0 meaning indefinite (default: 1)')
    parser.add_argument('-s', '--scan_time', dest='scan_time', default='100000', help='scan time in microseconds (default: 100000)')
    parser.add_argument('-t', '--timestamp',  dest='timestamp', default='%Y-%m-%dT%H:%M:%S%z', help='itemstamp format string (default: "%%Y-%%m-%%dT%%H:%%M:%%S%%z")')
    args = parser.parse_args()

    main(args.device, args.scan_time, args.reset_after, args.timestamp)
