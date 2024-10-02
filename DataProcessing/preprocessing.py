import numpy as np 
import pandas as pd
import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(path))
import matplotlib.pyplot as plt
import scipy.signal as signal

def convert_to_physical(df):
    """
    df --> pandas dataframe containing:
    Motor_fl	Motor_fr	Motor_bl	Motor_br	Gyro_x	Gyro_y	Gyro_z	Accel_x	Accel_y	Accel_z	Alt

    returns: 
    Motor in percentage

    """
    pass

def get_euler_angles_from_accels(df):
    pass

def freq_analysis(dfs, column_name):
    pass

def design_notch_filter(sample_rate, notch_freq, Q):
    """
    Design a notch filter.
    
    :param sample_rate: The sampling rate of the signal in Hz
    :param notch_freq: The frequency to be removed (notched) in Hz
    :param Q: Quality factor, controls the width of the notch
    :return: The filter coefficients (b, a) for the digital filter
    """
    # Normalize the notch frequency to the Nyquist frequency
    w0 = notch_freq / (sample_rate / 2)  # Normalize frequency
    
    # Compute the notch filter coefficients
    b, a = signal.iirnotch(w0, Q)
    
    return b, a

def design_bandstop_filter(sample_rate, lowcut, highcut, order=1):
    """
    Design a band-stop filter.
    
    :param sample_rate: Sampling rate in Hz
    :param lowcut: Lower frequency bound of the stop band in Hz
    :param highcut: Upper frequency bound of the stop band in Hz
    :param order: Order of the filter
    :return: Filter coefficients (b, a)
    """
    nyquist = 0.5 * sample_rate
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = signal.butter(order, [low, high], btype='bandstop')
    return b, a

def apply_filter(signal_data, b, a):
    """
    Apply a digital filter to the signal data.
    
    :param signal_data: The input signal to be filtered
    :param b: Numerator coefficients of the filter
    :param a: Denominator coefficients of the filter
    :return: The filtered signal
    """
    return signal.lfilter(b, a, signal_data)


df_iter = pd.read_csv(os.path.join(os.path.dirname(path), "Raw_Data/Log_2024-08-24_20-01-57.csv"), chunksize=50000)

first_chunk = next(df_iter)
#print(first_chunk)


signal_data = first_chunk['Alt']

fft_values = np.fft.fft(signal_data)
fft_frequencies = np.fft.fftfreq(len(signal_data), d=0.004)

fft_magnitude = np.abs(fft_values)

# plt.figure(figsize=(10, 6))
# plt.plot(fft_frequencies, fft_magnitude)
# plt.title('Frequency Domain Analysis')
# plt.xlabel('Frequency (Hz)')
# plt.ylabel('Magnitude')
# plt.grid(True)
# plt.show()

sample_rate = 250  # Hz
duration = 200  # seconds

lowcut = 60  # Lower bound of stop band in Hz
highcut = 88


t = np.linspace(0, duration, 50000, endpoint=False)

# Create a signal with a 50 Hz sine wave and some noise
notch_freq = 71.5  # Frequency to remove

# Design the notch filter
Q = 5.0  # Quality factor
b, a = design_bandstop_filter(sample_rate, lowcut, highcut, order=1)
print(b, a)

# Apply the notch filter to the signal
filtered_signal = apply_filter(signal_data, b, a)

def plot_frequency_spectrum(signal_data, sample_rate, title):
    """
    Plot the frequency spectrum of a signal.
    
    :param signal_data: The signal to be plotted
    :param sample_rate: The sampling rate of the signal in Hz
    :param title: Title for the plot
    """
    # Compute the FFT of the signal
    N = len(signal_data)
    fft_values = np.fft.fft(signal_data)
    fft_frequencies = np.fft.fftfreq(N, d=1/sample_rate)
    
    # Compute magnitude spectrum
    fft_magnitude = np.abs(fft_values)
    
    # Plot the frequency spectrum
    plt.figure(figsize=(12, 6))
    plt.plot(fft_frequencies[:N//2], fft_magnitude[:N//2])  # Plot positive frequencies only
    plt.title(title)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude')
    plt.grid(True)

plot_frequency_spectrum(signal_data, sample_rate, 'Original Signal Frequency Spectrum')
plot_frequency_spectrum(filtered_signal, sample_rate, 'Filtered Signal Frequency Spectrum')

plt.tight_layout()
plt.show()