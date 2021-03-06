#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 20 12:20:32 2018

@author: Thomas Bury

Script to simluate stationary trajectories of May's harvesting model at different
proximities to the bifurcation, and analyse the EWS behaviour at these proximities.
Does Smax serve as a more reliable inidicator under different applications of noise?
"""

# import python libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# import EWS function
import sys
sys.path.append('../../early_warnings')
from ews_compute import ews_compute
from ews_spec import pspec_welch, pspec_metrics




#----------------------
# Useful functions
#-----------------------

# Apply operation to column of DataFrame in place
def apply_inplace(df, field, fun):
    """ Apply function to a column of a DataFrame in place."""
    return pd.concat([df.drop(field, axis=1), df[field].apply(fun)], axis=1)




#--------------------------------
# Global parameters
#–-----------------------------


# Simulation parameters
dt = 0.02
t0 = 0
tmax = 1000 # make large (to get idealised statistics from stationary distribution)
tburn = 100 # burn-in period
seed = 0 # random number generation seed
hbif = 0.260437 # Fold bifurcation (computed in XPPAUT)
hl = 0.1 # low delta value
hh = 0.27 # high delta value
hinc = 0.001 # increment in h value
numSims = 1 # One simulation for each h value


# noise amplitudes
r_amp = 0.2
k_amp = 0.1
s_amp = 0.2
state_add_amp = 0.01 # additive noise to state
state_multi_amp = 0.02 # multiplicative noise proportional to size of state



# EWS parameters
dt2 = 1 # spacing between time-series for EWS computation
rw = 1 # rolling window (compute EWS using full time-series)
bw = 1 # bandwidth (take the whole dataset as stationary)
lags = [1,2,3] # autocorrelation lag times
ews = ['var','ac','sd','cv','skew','kurt','smax'] # EWS to compute
ham_length = 40 # number of data points in Hamming window
ham_offset = 0.5 # proportion of Hamming window to offset by upon each iteration
pspec_roll_offset = 20 # offset for rolling window when doing spectrum metrics



#----------------------------------
# Model details
#----------------------------------


# Function for model dynamics (variables [x])
def de_fun(state, control, params):
    '''
    Inputs:
        state: population size, x
        control: control parameter that is to be varied
        params: list of parameter values [r, k, s]
    Output:
        array of gradient vector (derivative)
    '''
    x = state
    [r, s, k] = params
    h = control
    
    # Gradients for each variable to increment by
    x_grad = r*x*(1-x/k)  - h*(x**2/(s**2 + x**2))
            
    return x_grad
 
    

# Control parameter values
hVals = np.arange(hl, hh, hinc)

# Initialise a list to collect trajectories
list_traj_append = []




#----------------------
# Run simulation
#------------------------

# Set seed
np.random.seed(seed)

# Loop through noise type
for noisy_params in ['add', 'multi', 'k']:

    ## Implement Euler Maryuyama for stocahstic simulation
    
    
    
    # Loop through h values
    print('\nBegin simulations with noise: '+noisy_params)
    for h in hVals:
        
        
        # Model parameters (average)
        r = 1 # growth rate
        k = 1 # carrying capacity
        s = 0.1 # half-saturation constant of harvesting function
            
        # Parameter list
        params = [r, k, s]

        
        # Initialise array to store time-series data
        t = np.arange(t0,tmax,dt) # Time array
        x = np.zeros([len(t), 1]) # State array

    
        # Create noisy parameter values
        if 'r' in noisy_params:
            r_burn = r + np.random.normal(loc=0, scale=r_amp, size = int(tburn/dt))
            r = r + np.random.normal(loc=0, scale=r_amp, size = len(t))
        else:
            r_burn = r*np.ones(int(tburn/dt))
            r = r*np.ones(len(t))
            
        if 's' in noisy_params:
            s_burn = s + np.random.normal(loc=0, scale=s_amp, size = int(tburn/dt))
            s = s + np.random.normal(loc=0, scale=s_amp, size = len(t))
        else:
            s_burn = s*np.ones(int(tburn/dt))
            s = s*np.ones(len(t))    
            
        if 'k' in noisy_params:
            k_burn = k + np.random.normal(loc=0, scale=k_amp, size = int(tburn/dt))
            k = k + np.random.normal(loc=0, scale=k_amp, size = len(t))
        else:
            k_burn = k*np.ones(int(tburn/dt))
            k = k*np.ones(len(t))   
        
        # create additive / multiplicative noise components    
        if 'add' in noisy_params:
            add_burn_comps = np.random.normal(loc=0, scale=np.sqrt(dt)*state_add_amp, size = int(tburn/dt))
            add_comps = np.random.normal(loc=0, scale=np.sqrt(dt)*state_add_amp, size = len(t))
        else:
            add_burn_comps = np.zeros(int(tburn/dt))
            add_comps = np.zeros(len(t))  
            
        if 'multi' in noisy_params:
            multi_burn_comps = np.random.normal(loc=0, scale=np.sqrt(dt)*state_multi_amp, size = int(tburn/dt))
            multi_comps = np.random.normal(loc=0, scale=np.sqrt(dt)*state_multi_amp, size = len(t))
        else:
            multi_burn_comps = np.zeros(int(tburn/dt))
            multi_comps = np.zeros(len(t))   
            
            
        x0 = 1 # initialisation value

    
        # Run burn-in period on x0
        for i in range(int(tburn/dt)):
            params = [r_burn[i], s_burn[i], k_burn[i]]
            control = h
            x0 = x0 + de_fun(x0, control, params)*dt + add_burn_comps[i] + multi_burn_comps[i]*x0
            # make sure remains >=0
            x0 = np.max([x0,0])
        # Initial condition post burn-in period
        x[0]=x0
        
        # Run simulation
        for i in range(len(t)-1):
            params = [r[i], s[i], k[i]]
            control = h
            x[i+1] = x[i] + de_fun(x[i], control, params)*dt +  add_comps[i] + multi_comps[i]*x[i]
            # make sure that state variable remains >= 0 
            x[i+1] = np.max([x[i+1], 0])
        
        # Write simulation as a DataFrame with info on h and noise type
        dict_data = {"Time": t, "State": x[:,0], "h": h, "Noise": noisy_params}
        df_traj_temp = pd.DataFrame(dict_data)
                
        # Add DataFrame to list
        list_traj_append.append(df_traj_temp)
        
        # Print update
        print('h = %5.4f complete' %h)
 

       
# Concatenate all trajectory DataFrames
df_traj = pd.concat(list_traj_append).set_index(['Noise','h','Time'])   
    
## Plot some trajectories at a value of h
#df_traj.loc[0.1].loc['s'].plot()



# Coarsen time-series to have spacing dt2 (for EWS computation)
df_traj_filt = df_traj.loc[::int(dt2/dt)]

     
#--------------------------------------
# Compute EWS of each trajectory
#–------------------------------------


# Set up a list to store output dataframes from ews_compute
# We will concatenate them at the end
appended_ews = []

# Print update
print('\nBegin EWS computation\n')

# Loop through noise type
for noise_type in ['add', 'multi', 'k']:
    
    # Loop through h value
    for h in hVals:
        
        ews_dic = ews_compute(df_traj_filt.loc[noise_type].loc[h]['State'], 
                          roll_window = rw, 
                          band_width = bw,
                          lag_times = lags, 
                          ews = ews,
                          ham_length = ham_length,
                          ham_offset = ham_offset,
                          pspec_roll_offset = pspec_roll_offset
                          )
        
        # The DataFrame of EWS
        df_ews_temp = ews_dic['EWS metrics']
        
        # Include a column in the DataFrames for noise type and h value
        df_ews_temp['h'] = h
        df_ews_temp['Noise'] = noise_type

                
        # Add DataFrames to list
        appended_ews.append(df_ews_temp)
        
    # Print status every realisation
    print('EWS for noise type =  '+str(noise_type)+' complete')


# Concatenate EWS DataFrames. Index [Delta, Variable, Time]
df_ews_full = pd.concat(appended_ews).reset_index().set_index(['Noise','h','Time'])


# Refine DataFrame to just have EWS data (no time dependence)
df_ews = df_ews_full.dropna().reset_index(level=2, drop=True)


# Export EWS dataframe
df_ews.to_csv('data_export/ews_stat_hnoise.csv')




#--------------------------
# Plots of EWS with different noise
#–--------------------------



df_ews['Smax'].unstack(level=0).plot(title = 'Smax', ylim = (0,0.00004))

df_ews['Variance'].unstack(level=0).plot(title = 'Variance', ylim=(0,0.0004))

df_ews['Coefficient of variation'].unstack(level=0).plot(title = 'CV', ylim=(0,0.04))

df_ews['Lag-1 AC'].unstack(level=0).plot(title = 'Lag-1 AC')














