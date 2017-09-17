#! /usr/bin/env python
# -*- coding: utf-8 -*-

try:
    # for Python2
    from Tkinter import *   ## notice capitalized T in Tkinter
except ImportError:
    # for Python3
    from tkinter import *   ## notice here too
from math import log
from datetime import datetime

# Plotting
import matplotlib.pyplot as plot

# SeaBreeze USB spectrometer access library
import seabreeze
seabreeze.use("pyseabreeze")
import seabreeze.spectrometers as sb


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
            exit(1)

        # Define the layout elements
        SpectrOMat.reset_after = Scale(root, from_=0, to=100000, label='Reset after # measurements', orient=HORIZONTAL)
        SpectrOMat.reset_after = Scale(root, from_=0, to=100000, label='Reset after # measurements', orient=HORIZONTAL)
        SpectrOMat.reset_after.set(reset_after)
        SpectrOMat.button_start = Button(root, text='Start Measurement', command=SpectrOMat.measure)

        # Define the layout
        SpectrOMat.entropy.grid(column=0, row=0, rowspan=3)
        SpectrOMat.equivalent_length.grid(column=0, row=3)
        SpectrOMat.button_KIT.grid(column=1, row=0, sticky=W)
        SpectrOMat.button_KITSCC.grid(column=1, row=1, sticky=W)
        SpectrOMat.button_SCC.grid(column=1, row=2, sticky=W)
        SpectrOMat.button_extended.grid(column=1, row=3, sticky=W)
        Label(root).grid(column=0, row=4) # Add spacing
        SpectrOMat.button_generate.grid(column=0, row=5, columnspan=2)
        Label(root).grid(column=0, row=6) # Add spacing
        SpectrOMat.output.grid(column=0, row=7, columnspan=2)

    @staticmethod
    def generate():
        SpectrOMat.output.delete(1.0, END)
        retries = 0
        entropy = SpectrOMat.entropy.get()
        check_method = SpectrOMat.check_method.get()
        use_extended_separator_set = not SpectrOMat.use_extended_separator_set.get() == 0
        for item in range(5):
            kit_check = 1
            scc_check = 1
            while ((kit_check > 0) or ((scc_check > 0) and (check_method == 'SCC'))):
                password = SpectrOMat.generator.generate(randomBits=entropy, use_extended=use_extended_separator_set)
                kit_check = KITPasswordChecker.check(password)
                scc_check = SCCPasswordChecker.check(password)
                retries += 1
                if (retries >= SpectrOMat.max_retries):
                    SpectrOMat.output.insert(END, '\nDid not find a password that satisfies the requested\nruleset within a reasonable time; giving up.\nTry increasing the target entropy to ' + str(SpectrOMat.min_entropy[check_method]) + ' bits or higher.', 'error')
                    break
            if (retries >= SpectrOMat.max_retries):
                break
            if ((scc_check == 0) or (check_method == 'KIT')):
                SpectrOMat.output.insert(END, '\n  ' + password, 'okay')
            else:
                SpectrOMat.output.insert(END, '\n  ' + password, 'warning')


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

    main(args.device, args.integration_time_micros, args.reset_after)
