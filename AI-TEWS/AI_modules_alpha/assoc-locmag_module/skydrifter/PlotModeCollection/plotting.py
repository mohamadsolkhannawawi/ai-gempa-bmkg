from skydrifter.PeculiarSupport.obspy_support import *

import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

def plot_pred_true_pick_type1(stn,true_pick,pred_pick,pick_type,rolling_index=0,max_data=3001):
    # Section 1 Convert Stream Time to Timestamp
    converted_t = convert_timestamp(stn[0])
    s_index,e_index = sliding_index(stn[0].data,window=max_data,overlap_point=max_data-500)
    now_t = converted_t[s_index[rolling_index]:e_index[rolling_index]]
    # Section 2 Locate True Pick to Timestamp Index
    true_index = np.argmin([abs(now_t[i] - (true_pick.timestamp)) for i in range(0,len(now_t))])
    true_plot_pick = [0 for i in range(0,len(now_t))]
    true_plot_pick[true_index] = 1
    # Section 3 Locate Pred Pick to Timestamp Index
    pred_index = np.argmin([abs(now_t[i] - (pred_pick.timestamp)) for i in range(0,len(now_t))])
    pred_plot_pick = [0 for i in range(0,len(now_t))]
    pred_plot_pick[pred_index] = 1
    # Section 4 Make Title String
    string_date = join_by([str(stn[0].stats.starttime.year),str(stn[0].stats.starttime.month),str(stn[0].stats.starttime.day)],separator='-')
    station = stn[0].stats.station
    title_string = 'Station = ' + station + '\n' + 'Date = ' + string_date + '\nTrue ' + pick_type  + ' Pick = ' + str(true_pick) + '\nPred ' + pick_type  + ' Pick = ' + str(pred_pick)
    # Section 5 Plot and Define Figure and Axis
    fig, axs = plt.subplots(4,figsize=(20,10),gridspec_kw={'hspace': 0.2})
    fig.suptitle(title_string)
    for i in range(0,3):
        axs[i].plot(stn[i].data[s_index[rolling_index]:e_index[rolling_index]],label=stn[i].stats.channel)
        axs[i].set_ylabel('Amplitude')
        axs[i].set_xticks([])
        axs[i].legend()
    axs[3].plot(true_plot_pick,label='True')
    axs[3].plot(pred_plot_pick,label='Pred')
    t_tick = np.linspace(start=stn[i].stats.starttime.timestamp,stop=stn[i].stats.endtime.timestamp,num=len(axs[3].get_xticklabels()))
    t_tick = [(op.UTCDateTime(t_tick[3])).time.strftime('%H:%M:%S') for j in range(0,len(t_tick))]
    tick_labels = axs[3].get_xticklabels()
    count = 0
    for tick in tick_labels:
        tick.set_text(t_tick[count])
        count += 1
    axs[3].set_xticklabels(tick_labels)
    axs[3].set_xlabel('Time')
    axs[3].set_ylabel('Pick Probabilty')
    axs[3].legend()

def plot_pred_true_pick_type2(stn,true_pick,pred_pick,pick_type,rolling_index=0,max_data=3001):
    # Section 1 Convert Stream Time to Timestamp
    converted_t = convert_timestamp(stn[0])
    s_index,e_index = sliding_index(stn[0].data,window=max_data,overlap_point=max_data-500)
    now_t = converted_t[s_index[rolling_index]:e_index[rolling_index]]
    # Section 2 Locate True Pick to Timestamp Index
    true_index = np.argmin([abs(now_t[i] - (true_pick.timestamp)) for i in range(0,len(now_t))])
    true_plot_pick = [0 for i in range(0,len(now_t))]
    true_plot_pick[true_index] = 1
    # Section 3 Locate Pred Pick to Timestamp Index
    pred_index = np.argmin([abs(now_t[i] - (pred_pick.timestamp)) for i in range(0,len(now_t))])
    pred_plot_pick = [0 for i in range(0,len(now_t))]
    pred_plot_pick[pred_index] = 1
    # Section 4 Make Title String
    string_date = join_by([str(stn[0].stats.starttime.year),str(stn[0].stats.starttime.month),str(stn[0].stats.starttime.day)],separator='-')
    station = stn[0].stats.station
    title_string = 'Station = ' + station + '\n' + 'Date = ' + string_date + '\nTrue ' + pick_type  + ' Pick = ' + str(true_pick) + '\nPred ' + pick_type  + ' Pick = ' + str(pred_pick)
    # Section 5 Plot and Define Figure and Axis
    fig, axs = plt.subplots(3,figsize=(20,8),gridspec_kw={'hspace': 0.2})
    fig.suptitle(title_string)
    for i in range(0,3):
        axs[i].plot(stn[i].data[s_index[rolling_index]:e_index[rolling_index]],label=stn[i].stats.channel)
        axs[i].set_ylabel('Amplitude')
        if i != 2:
            axs[i].set_xticks([])
        if i == 0:
            axs[i].axvline(x=true_index, color='red', linestyle='--',label='True Pick')
            axs[i].axvline(x=pred_index, color='green', linestyle='--',label='Pred Pick')
            axs[i].legend()
        elif i != 0:
            axs[i].axvline(x=true_index, color='red', linestyle='--')
            axs[i].axvline(x=pred_index, color='green', linestyle='--')
            axs[i].legend()
    t_tick = np.linspace(start=stn[2].stats.starttime.timestamp,stop=stn[2].stats.endtime.timestamp,num=len(axs[2].get_xticklabels()))
    t_tick = [(op.UTCDateTime(t_tick[2])).time.strftime('%H:%M:%S') for j in range(0,len(t_tick))]
    tick_labels = axs[2].get_xticklabels()
    count = 0
    for tick in tick_labels:
        tick.set_text(t_tick[count])
        count += 1
    axs[2].set_xticklabels(tick_labels)
    axs[2].set_xlabel('Time')