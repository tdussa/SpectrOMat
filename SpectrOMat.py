#! /usr/bin/env python
# -*- coding: utf-8 -*-
import timeit
try:
    # for Python2
    from Tkinter import *   ## notice capitalized T in Tkinter
    input = raw_input
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


# Global helper function
def StringIsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


# SeaBreeze spectrograph simulator
class SBSimulator:
    """SeaBreeze specrograph simulator class"""
    def __init__(self,
                 integration_time_micros=10000,
                 minimum_integration_time_micros = 8000,
                 wavelengths=list(range(2048)),
                 generator=numpy.random.normal):
        self.integration_time_micros = integration_time_micros
        self.minimum_integration_time_micros = minimum_integration_time_micros
        self._wavelengths = wavelengths
        self.samplesize = len(wavelengths)
        self.generator = generator

    def integration_time_micros(self, newValue):
        if (newValue >= self.minimum_integration_time_micros):
            self.integration_time_micros = newValue

    def intensities(self):
        return(self.generator(size=self.samplesize))

    def wavelengths(self):
        return(self._wavelengths)



class SpectrOMat:
    @staticmethod
    def initialize(root,
                   autoexposure=False,
                   autorepeat=False,
                   autosave=True,
                   dark_frames=1,
                   device='#0',
                   enable_plot=True,
                   output_file='Snapshot-%Y-%m-%dT%H:%M:%S%z.dat',
                   scan_frames=1,
                   scan_time=100000,
                   timestamp='%Y-%m-%dT%H:%M:%S%z',
                   ):
        try:
            if ('SIMULATOR'.startswith(device.upper())):
                SpectrOMat.spectrometer = SBSimulator()
            elif (device[0] == '#'):
                SpectrOMat.spectrometer = sb.Spectrometer(sb.list_devices()[int(device[1:])])
            else:
                SpectrOMat.spectrometer = sb.Spectrometer.from_serial_number(device)
            print(SpectrOMat.spectrometer)
            SpectrOMat.wavelengths = SpectrOMat.spectrometer.wavelengths()
        except:
            print('ERROR: Could not initialize device "' + device + '"!')
            print('Available devices:')
            index = 0
            for dev in sb.list_devices():
                print(' - #' + str(index) + ':', 'Model:', dev.model + '; serial number:', dev.serial)
                index += 1
            if ('Y'.startswith(input('Simulate spectrometer device instead?  [Y/n] ').upper())):
                SpectrOMat.spectrometer = SBSimulator()
            else:
                sys.exit(1)

        SpectrOMat.wavelengths = SpectrOMat.spectrometer.wavelengths()

        SpectrOMat.run_measurement = False
        SpectrOMat.have_darkness_correction = False
        SpectrOMat.button_startpause_texts = { True: 'Pause Measurement', False: 'Start Measurement' }
        SpectrOMat.button_stopdarkness_texts = { True: 'Stop Measurement', False: 'Get Darkness Correction' }

        SpectrOMat.autoexposure = IntVar(value=autoexposure)
        SpectrOMat.autorepeat = IntVar(value=autorepeat)
        SpectrOMat.autosave = IntVar(value=autosave)
        SpectrOMat.dark_frames = StringVar(value=dark_frames)
        SpectrOMat.enable_plot = IntVar(value=enable_plot)
        SpectrOMat.output_file = StringVar(value=output_file)
        SpectrOMat.scan_frames = StringVar(value=scan_frames)
        SpectrOMat.scan_time = StringVar(value=scan_time)
        SpectrOMat.timestamp = timestamp

        SpectrOMat.message = StringVar()

        SpectrOMat.total_exposure = int(scan_frames) * int(scan_time)

        # Initialize variables
        SpectrOMat.darkness_correction = [0.0]*(len(SpectrOMat.spectrometer.wavelengths()))
        SpectrOMat.measurement = 0
        SpectrOMat.data = [0.0]*(len(SpectrOMat.spectrometer.wavelengths()))

        # Plot setup
        plot.ion()

        # Define the layout elements
        SpectrOMat.label_scan_frames = Label(root, text='Scan Frame Count', justify=LEFT)
        SpectrOMat.scale_scan_frames = Scale(root, from_=0, to=10000, showvalue=0, orient=HORIZONTAL, command=SpectrOMat.update_scan_frames)
        SpectrOMat.entry_scan_frames = Entry(root, textvariable=SpectrOMat.scan_frames, validate='focusout')

        SpectrOMat.label_scan_time = Label(root, text='Scan Time [µs]', justify=LEFT)
        SpectrOMat.scale_scan_time = Scale(root, from_=SpectrOMat.spectrometer.minimum_integration_time_micros, to=10000000, showvalue=0, orient=HORIZONTAL, command=SpectrOMat.update_scan_time)
        SpectrOMat.entry_scan_time = Entry(root, textvariable=SpectrOMat.scan_time, validate='focusout')

        SpectrOMat.label_dark_frames = Label(root, text='Dark Frame Count', justify=LEFT)
        SpectrOMat.scale_dark_frames = Scale(root, from_=1, to=10000, showvalue=0, orient=HORIZONTAL, command=SpectrOMat.update_dark_frames)
        SpectrOMat.entry_dark_frames = Entry(root, textvariable=SpectrOMat.dark_frames, validate='focusout')

        SpectrOMat.entry_scan_frames.config({'validatecommand': SpectrOMat.validate_scan_frames})
        SpectrOMat.entry_scan_time.config({'validatecommand': SpectrOMat.validate_scan_time})
        SpectrOMat.entry_dark_frames.config({'validatecommand': SpectrOMat.validate_dark_frames})

        SpectrOMat.button_startpause_text = StringVar()
        SpectrOMat.button_startpause_text.set(SpectrOMat.button_startpause_texts[SpectrOMat.run_measurement])
        SpectrOMat.button_startpause = Button(root, textvariable=SpectrOMat.button_startpause_text, command=SpectrOMat.startpause)

        SpectrOMat.checkbutton_enable_plot = Checkbutton(root, text='Enable Live Plotting', variable=SpectrOMat.enable_plot)

        SpectrOMat.checkbutton_autorepeat = Checkbutton(root, text='Auto Repeat', variable=SpectrOMat.autorepeat)
        SpectrOMat.checkbutton_autosave = Checkbutton(root, text='Auto Save', variable=SpectrOMat.autosave)
        SpectrOMat.checkbutton_autoexposure = Checkbutton(root, text='Constant Total Exposure', variable=SpectrOMat.autoexposure)

        SpectrOMat.button_stopdarkness_text = StringVar()
        SpectrOMat.button_stopdarkness_text.set(SpectrOMat.button_stopdarkness_texts[SpectrOMat.run_measurement])
        SpectrOMat.button_stopdarkness = Button(root, textvariable=SpectrOMat.button_stopdarkness_text, command=SpectrOMat.stopdarkness)

        SpectrOMat.button_save = Button(root, text='Save to File', command=SpectrOMat.save)
        SpectrOMat.button_reset = Button(root, text='Reset', command=SpectrOMat.reset)
        SpectrOMat.button_exit = Button(root, text='Exit', command=SpectrOMat.exit)

        SpectrOMat.textbox = Label(root, fg='white', bg='black', textvariable=SpectrOMat.message)
        SpectrOMat.message.set('Ready.')

        # Define the layout
        SpectrOMat.label_scan_frames.grid(rowspan=2)
        SpectrOMat.scale_scan_frames.grid(row=0, column=1, rowspan=2)
        SpectrOMat.entry_scan_frames.grid(row=1, column=2)

        SpectrOMat.label_scan_time.grid(rowspan=2)
        SpectrOMat.scale_scan_time.grid(row=2, column=1, rowspan=2)
        SpectrOMat.entry_scan_time.grid(row=3, column=2)

        SpectrOMat.label_dark_frames.grid(rowspan=2)
        SpectrOMat.scale_dark_frames.grid(row=4, column=1, rowspan=2)
        SpectrOMat.entry_dark_frames.grid(row=5, column=2)

        SpectrOMat.checkbutton_autorepeat.grid(row=6)
        SpectrOMat.checkbutton_autosave.grid(row=6, column=1)
        SpectrOMat.checkbutton_autoexposure.grid(row=6, column=2)

        SpectrOMat.button_startpause.grid(row=7)
        SpectrOMat.checkbutton_enable_plot.grid(row=7, column=1)
        SpectrOMat.button_stopdarkness.grid(row=7, column=2)

        SpectrOMat.button_save.grid(row=8)
        SpectrOMat.button_reset.grid(row=8, column=1)
        SpectrOMat.button_exit.grid(row=8, column=2)

        SpectrOMat.textbox.grid(columnspan=3)


    @staticmethod
    def update_scan_frames(newValue):
        newValue = int(newValue)
        if SpectrOMat.autoexposure.get() > 0:
            if newValue == 0 or newValue * 10000000 > SpectrOMat.total_exposure:
                newValue = int(SpectrOMat.total_exposure / 10000000)
                if newValue == 0:
                    newValue = 1
                SpectrOMat.scale_scan_frames.set(newValue)
            elif newValue * SpectrOMat.spectrometer.minimum_integration_time_micros < SpectrOMat.total_exposure:
                newValue = int(SpectrOMat.total_exposure / SpectrOMat.spectrometer.minimum_integration_time_micros)
                SpectrOMat.scale_scan_frames.set(newValue)
            newTime = int(SpectrOMat.total_exposure / newValue)
            print('v', newValue)
            print('t: ', newTime)
            #SpectrOMat.scan_time.set(newTime)
            SpectrOMat.scale_scan_time.set(newTime)
        SpectrOMat.scan_frames.set(newValue)
        SpectrOMat.dark_frames.set(newValue)
        SpectrOMat.scale_dark_frames.set(newValue)
        SpectrOMat.total_exposure = int(SpectrOMat.scan_frames.get()) * int(SpectrOMat.scan_time.get())

    @staticmethod
    def validate_scan_frames():
        newValue = SpectrOMat.scan_frames.get()
        if StringIsInt(newValue) and \
           int(newValue) >= 0 and \
           int(newValue) <= 10000:
            SpectrOMat.scale_scan_frames.set(int(newValue))
            SpectrOMat.scale_dark_frames.set(int(newValue))
            SpectrOMat.dark_frames.set(newValue)
        else:
            SpectrOMat.scan_frames.set(SpectrOMat.scale_scan_frames.get())
            SpectrOMat.entry_scan_frames.after_idle(SpectrOMat.entry_scan_frames.config, {'validate': 'focusout', 'validatecommand': SpectrOMat.validate_scan_frames})
        return True


    @staticmethod
    def update_scan_time(newValue):
        newValue = int(newValue)
        if SpectrOMat.autoexposure.get() > 0 and \
           int(SpectrOMat.scan_frames.get()) != 0:
            if newValue * 10000 > SpectrOMat.total_exposure:
                newValue = int(SpectrOMat.total_exposure / 10000)
                print(newValue)
                SpectrOMat.scale_scan_time.set(newValue)
            newFrames = int(SpectrOMat.total_exposure / newValue)
            SpectrOMat.scan_frames.set(newFrames)
            SpectrOMat.dark_frames.set(newFrames)
            SpectrOMat.scale_scan_frames.set(newFrames)
            SpectrOMat.scale_dark_frames.set(newFrames)
        SpectrOMat.scan_time.set(newValue)
        SpectrOMat.spectrometer.integration_time_micros(newValue)
        SpectrOMat.total_exposure = int(SpectrOMat.scan_frames.get()) * int(SpectrOMat.scan_time.get())

    @staticmethod
    def validate_scan_time():
        newValue = SpectrOMat.scan_time.get()
        if StringIsInt(newValue) and \
           int(newValue) >= SpectrOMat.spectrometer.minimum_integration_time_micros and \
           int(newValue) <= 10000000:
            SpectrOMat.scale_scan_time.set(int(newValue))
        else:
            SpectrOMat.scan_time.set(SpectrOMat.scale_scan_time.get())
            SpectrOMat.entry_scan_time.after_idle(SpectrOMat.entry_scan_time.config, {'validate': 'focusout', 'validatecommand': SpectrOMat.validate_scan_time})
        return True


    @staticmethod
    def update_dark_frames(newValue):
        SpectrOMat.dark_frames.set(newValue)

    @staticmethod
    def validate_dark_frames():
        newValue = SpectrOMat.dark_frames.get()
        if StringIsInt(newValue) and \
           int(newValue) >= 1 and \
           int(newValue) <= 10000:
            SpectrOMat.scale_dark_frames.set(int(newValue))
        else:
            SpectrOMat.dark_frames.set(SpectrOMat.scale_scan_frames.get())
            SpectrOMat.entry_dark_frames.after_idle(SpectrOMat.entry_dark_frames.config, {'validate': 'focusout', 'validatecommand': SpectrOMat.validate_dark_frames})
        return True


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
            SpectrOMat.message.set('Ready.')
            SpectrOMat.measurement = 0
        else:
            newData = SpectrOMat.spectrometer.intensities()
            count = 1
            SpectrOMat.message.set('Scanning dark frame ' + str(count) + '/' + str(SpectrOMat.dark_frames.get()))
            root.update()
            while count < int(SpectrOMat.dark_frames.get()):
                newData = list(map(lambda x,y:x+y, SpectrOMat.spectrometer.intensities(), newData))
                if (count % 100 == 0):
                    print('O', end='', flush=True)
                elif (count % 10 == 0):
                    print('o', end='', flush=True)
                else:
                    print('.', end='', flush=True)
                count += 1
                SpectrOMat.message.set('Scanning dark frame ' + str(count) + '/' + str(SpectrOMat.dark_frames.get()))
                root.update()
            SpectrOMat.darkness_correction = list(map(lambda x:x/count, newData))
            SpectrOMat.have_darkness_correction = True
            SpectrOMat.message.set(str(SpectrOMat.dark_frames.get()) + ' dark frames scanned. Ready.')
            print(str(SpectrOMat.dark_frames.get()) + ' dark frames scanned.')

    @staticmethod
    def save():
        try:
            with open(time.strftime('Snapshot-%Y-%m-%dT%H:%M:%S.dat', time.gmtime()), 'w') as f:
                f.write('# Spectr-O-Mat data format: 2')
                f.write('\n# Time of snapshot: ' + time.strftime(SpectrOMat.timestamp, time.gmtime()))
                f.write('\n# Number of frames accumulated: ' + str(SpectrOMat.measurement))
                f.write('\n# Scan time per exposure [µs]: ' + str(SpectrOMat.scan_time.get()))
                if SpectrOMat.have_darkness_correction:
                    f.write('\n# Number of dark frames accumulated: ' + str(SpectrOMat.dark_frames.get()))
                    f.write('\n# Wavelength [nm], dark frame correction data [averaged count]:\n# ')
                    f.write('\n# '.join(map(lambda x,y:str(x)+', '+str(y), SpectrOMat.spectrometer.wavelengths(), SpectrOMat.darkness_correction)))
                    f.write('\n# Wavelength [nm], Intensity [corrected count]:\n')
                else:
                    f.write('\n# Number of dark frames accumulated: None.')
                    f.write('\n# Wavelength [nm], Intensity [count]:\n')
                f.write('\n'.join(map(lambda x,y:str(x)+', '+str(y), SpectrOMat.spectrometer.wavelengths(), SpectrOMat.data)) + '\n')
            SpectrOMat.message.set('Data saved to ' + time.strftime('Snapshot-%Y-%m-%dT%H:%M:%S.dat', time.gmtime()) + '. Ready.')
            print('Data saved to ' + time.strftime('Snapshot-%Y-%m-%dT%H:%M:%S.dat', time.gmtime()))
        except:
            SpectrOMat.message.set('Error while writing ' + time.strftime('Snapshot-%Y-%m-%dT%H:%M:%S.dat', time.gmtime()) + '. Ready.')
            print('Error while writing ' + time.strftime('Snapshot-%Y-%m-%dT%H:%M:%S.dat', time.gmtime()))
        root.update()


    @staticmethod
    def reset():
        SpectrOMat.run_measurement = False
        SpectrOMat.button_startpause_text.set(SpectrOMat.button_startpause_texts[SpectrOMat.run_measurement])
        SpectrOMat.button_stopdarkness_text.set(SpectrOMat.button_stopdarkness_texts[SpectrOMat.run_measurement])
        SpectrOMat.darkness_correction = [0.0]*(len(SpectrOMat.spectrometer.wavelengths()))
        SpectrOMat.have_darkness_correction = False
        SpectrOMat.measurement = 0
        SpectrOMat.message.set('All parameters reset. Ready.')

    @staticmethod
    def exit():
        sys.exit(0)


    @staticmethod
    def measure():
        if SpectrOMat.run_measurement:
            scan_frames = int(SpectrOMat.scan_frames.get())
            if (scan_frames > 0):
                SpectrOMat.message.set('Scanning frame ' + str(SpectrOMat.measurement+1) + '/' + str(scan_frames) + '...')
            else:
                SpectrOMat.message.set('Scanning frame...')
            root.update()
            newData = list(map(lambda x,y:x-y, SpectrOMat.spectrometer.intensities(), SpectrOMat.darkness_correction))
            if (SpectrOMat.measurement == 0):
                SpectrOMat.data = newData
            else:
                SpectrOMat.data = list(map(lambda x,y:x+y, SpectrOMat.data, newData))
            SpectrOMat.measurement += 1

            if (SpectrOMat.measurement == scan_frames) or \
               (SpectrOMat.enable_plot.get() > 0):
                plot.clf()
                plot.suptitle(time.strftime(SpectrOMat.timestamp, time.gmtime()) +
                             ' (sum of ' + str(SpectrOMat.measurement) + ' measurement(s)' +
                             ' with scan time ' + str(SpectrOMat.scan_time.get()) + ' µs)')
                plot.xlabel('Wavelengths [nm]')
                if SpectrOMat.have_darkness_correction:
                    plot.ylabel('Intensities [corrected count]')
                else:
                    plot.ylabel('Intensities [count]')
                plot.plot(SpectrOMat.wavelengths, SpectrOMat.data)
                plot.show()
                plot.pause(0.0001)

            if (SpectrOMat.measurement % 100 == 0):
                print('O', end='', flush=True)
            elif (SpectrOMat.measurement % 10 == 0):
                print('o', end='', flush=True)
            else:
                print('.', end='', flush=True)
            if (scan_frames > 0):
                if SpectrOMat.measurement % scan_frames == 0:
                    #print(time.strftime(SpectrOMat.timestamp, time.gmtime()), SpectrOMat.data)
                    if SpectrOMat.autosave.get() != 0:
                        SpectrOMat.save()
                    SpectrOMat.measurement = 0
                    if SpectrOMat.autorepeat.get() == 0:
                        SpectrOMat.run_measurement = False
                        SpectrOMat.button_startpause_text.set(SpectrOMat.button_startpause_texts[SpectrOMat.run_measurement])
                        SpectrOMat.button_stopdarkness_text.set(SpectrOMat.button_stopdarkness_texts[SpectrOMat.run_measurement])
                        SpectrOMat.message.set('Ready.')

        root.after(1, SpectrOMat.measure)


def main(device='#0', scan_time=100000, scan_frames=1, timestamp='%Y-%m-%dT%H:%M:%S%z'):
    global root
    root.title('Spectr-O-Mat')
    SpectrOMat.initialize(root, device=device, scan_time=scan_time, scan_frames=scan_frames, timestamp=timestamp)
    root.after(1, SpectrOMat.measure)
    root.mainloop()

if __name__ == "__main__":
    # Parse args
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-d', '--device', dest='device', default='#0', help='input device to use; "<serial number>" or "#<device number>" or "SIMULATOR" (default: #0)')
    parser.add_argument('-r', '--scan_frames', dest='scan_frames', default='1', help='reset after n measurement cycles with 0 meaning indefinite (default: 1)')
    parser.add_argument('-s', '--scan_time', dest='scan_time', default='100000', help='scan time in microseconds (default: 100000)')
    parser.add_argument('-t', '--timestamp',  dest='timestamp', default='%Y-%m-%dT%H:%M:%S%z', help='itemstamp format string (default: "%%Y-%%m-%%dT%%H:%%M:%%S%%z")')
    args = parser.parse_args()

    main(args.device, args.scan_time, args.scan_frames, args.timestamp)
