"""
% IEEE 738-2012 Python implementation
%
% IEEE Standard for Calculating the Current-Temperature of Bare Overhead Conductors
%
% Copyright (c) 2018 Saul CG via the excellent work of Steven Blair
%
% Permission is hereby granted, free of charge, to any person obtaining a copy
% of this software and associated documentation files (the "Software"), to deal
% in the Software without restriction, including without limitation the rights
% to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
% copies of the Software, and to permit persons to whom the Software is
% furnished to do so, subject to the following conditions:
%
% The above copyright notice and this permission notice shall be included in
% all copies or substantial portions of the Software.
%
% THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
% IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
% FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
% AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
% LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
% OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
% THE SOFTWARE.
"""

import numpy as np
import matplotlib.pyplot as plt
from math import sqrt, cos, acos, sin


total_time = 7200 #seconds
points_per_second = 50
number_of_points = points_per_second * total_time
dt = 1 / points_per_second #time step

I_ss = 500              # RMS steady-state load current (A)
I_f = 20000             # RMS fault current (A)
D = 22.8                # Conductor diameter (mm)
area = D/1000           # Projected area of conducter per unit length (m^2/m)
rho_f = 1.029           # Density of air (kg/m^3)
H_e = 25                # Elevation of conductor above sea level (m)
Ta = 25.0               # Ambient temperature (C)
epsilon = 0.5           # Emissivity
alpha = 0.5             # Solar absorptivity
H_c = 72.5              # Altitude of sun (degrees)
Z_c = 139               # Azimuth of sun (degrees)
Z_l = 90.0              # Azimuth of electrical line (degrees): 90 degrees (or 270 degrees) for east-west
R_T_high = 8.688e-5     # Conductor unit resistance at high temperature reference (ohm/m)
R_T_low = 7.283e-5      # Conductor unit resistance at low temperature reference (ohm/m)
T_high = 75.0           # High temperature reference (C)
T_low = 25.0            # Low temperature reference (C)
mCp = 1.0 * 534         # Conductor total heat capacity (J/m-C). This value assumes 1.0 kg/m cable of Aluminium Clad Steel, with specific heat = 534 J/(kg-C)
Q_s = -42.2391 + 63.8044*H_c - 1.9220*H_c**2 + 3.46921e-2*H_c**3 - 3.61118e-4*H_c**4 + 1.94318e-6*H_c**5 - 4.07608e-9*H_c**6
K_solar = 1 + 1.148e-4*H_e - 1.108e-8*H_e**2
Q_se = K_solar * Q_s
theta = acos(cos(H_c) * cos(Z_c - Z_l))

melting_point_temperature = 660     # Conductor melting point temperature (degrees Celcius) (660C for aluminium)
found_melting_point = 0             # Initialize
time_to_melt = 0                    # Initialize


# Calculate initial (steady-state) conductor temperature from the steady-state load current, using a binary search
I_ss_threshold = 0.01
Tc_min = Ta
Tc_max = Ta*1000
I_ss_result = 0.0
Tc_test = 0.0


# Returns the current required for a conductor temperature, Tc, and other parameters
def get_i(Tc, R_T_high, R_T_low, T_high, T_low, Ta, rho_f, D, epsilon, alpha, Q_se, theta, area):

    R_Tc = ((R_T_high - R_T_low) / (T_high - T_low)) * (Tc - T_low) + R_T_low

    # Conductor heat loss from natural convection, assuming no wind
    q_cn = 0.0205 * rho_f**0.5 * D**0.75 * (Tc - Ta)**1.25

    # Conductor heat loss from radiation
    q_r = 0.0178 * D * epsilon * (((Tc + 273)/100)**4 - ((Ta + 273)/100)**4)

    # Solar heat gain in conductor
    q_s = alpha * Q_se * sin(theta) * area

    I = sqrt((q_cn + q_r - q_s) / R_Tc)

    return I


while ((I_ss_result > I_ss + I_ss_threshold) or (I_ss_result < I_ss - I_ss_threshold)):
    Tc_test = (Tc_max + Tc_min) / 2

    I_ss_result = np.real(get_i(Tc_test, R_T_high, R_T_low, T_high, T_low, Ta, rho_f, D, epsilon, alpha, Q_se, theta, area))

    if (I_ss_result == I_ss):
        break
    elif (I_ss_result > I_ss):
        Tc_max = Tc_test
    else:
        Tc_min = Tc_test


Tc_ss = Tc_test                     # Estimate of steady-state conductor temperature (degrees Celcius)


"""
Calculate the conductor temperature for a change in current that mimics a
fault and a two-shot auto-reclosure scheme.
"""
dTc_dt = np.zeros(number_of_points)     # array of temperature increments per timestep
I = np.zeros(number_of_points + 1)      # array of current "waveform" over time
Tc = np.zeros(number_of_points + 1)     # array of conductor temperature over time
time = np.zeros(number_of_points + 1)   # array of time
Tc[0] = Tc_ss

# Set current values
I[0                         :   0.1*points_per_second] = I_ss   # pre-fault current
I[0.1*points_per_second     :   0.2*points_per_second] = I_f    # fault occurs
I[0.2*points_per_second     :   0.5*points_per_second] = 0      # circuit breaker opened, no current for 0.3s
I[0.5*points_per_second     :   0.6*points_per_second] = I_f    # 1st reclosure
I[0.6*points_per_second     :   1.6*points_per_second] = 0      # circuit breaker opened, no current for 1.0s
I[1.6*points_per_second     :   1.7*points_per_second] = I_f    # 2nd reclosure
I[1.7*points_per_second     :   number_of_points + 1]  = 0      # lock-out

# loop through each time-step
for x in range(number_of_points):
    R_Tc = ((R_T_high - R_T_low) / (T_high - T_low)) * (Tc[x] - T_low) + R_T_low      # replace with calculation
    T_film = (Tc[x] + Ta) / 2

    # Conductor heat loss from natural convection, assuming no wind
    q_cn = 0.0205 * rho_f**0.5 * D**0.75 * (Tc[x] - Ta)**1.25

    # Conductor heat loss from radiation
    q_r = 0.0178 * D * epsilon * (((Tc[x] + 273)/100)**4 - ((Ta + 273)/100)**4)

    # Solar heat gain in conductor
    q_s = alpha * Q_se * sin(theta) * area

    # Rate of change of temperature
    dTc_dt[x] = (1 / (mCp)) * (R_Tc * I[x + 1]**2 + q_s - q_cn - q_r)

    # Calculate new conductor temperature, using an Euler integral
    Tc[x + 1] = Tc[x] + dTc_dt[x] * dt
    time[x + 1] = time[x] + dt

    # Find if conductor melting point has been exceeded
    if Tc[x + 1] >= melting_point_temperature and found_melting_point == 0:
        found_melting_point = 1
        time_to_melt = time[x + 1]


# Calculate thermal time constant.
# NB: tau is only valid when "total_time" is suffiently large for Tc to settle
tau = ((Tc[number_of_points] - Tc_ss) * mCp) / (R_Tc * (I_f**2 - I_ss**2))


# Plot
plt.plot(time,Tc)
plt.xscale('log')
plt.xlabel('Time (s) - 2 hours Total')
plt.ylabel('Conductor Temperature ($^\circ$ C)')
plt.title('Conductor Temperature in a Two-Shot Auto-Reclosure')
plt.text(60, .025, r'$\mu=100,\ \sigma=15$')
#plt.text(60, .025, r'$\mu=100,\ \sigma=15$')
