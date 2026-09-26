from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *

from skydrifter.SeisArchiveCollector.SeisStreamRecap import *

import obspy as op
import pandas as pd

class SeisArchiveCollector:
    def __init__(self,path):
        self.path = path

    def create_archive(self):
        filename,filepath,channel = [],[],[]
        delta,endtime,index,instrument = [],[],[],[]
        network,npts,sampling_rate,starttime = [],[],[],[]
        station,tracenumber,format = [],[],[]
        year,julday = [],[]
        for i in range(0,len(self.path)):
            filename.append(separate_by(self.path[i])[-1])
            filepath.append(self.path[i])
            stn = SeisStreamRecap(op.read(self.path[i],headonly=True))
            year.append(stn.get_year())
            julday.append(stn.get_julday())
            channel.append(stn.get_channel())
            delta.append(stn.get_delta())
            index.append(stn.get_index())
            instrument.append(stn.get_instrument())
            network.append(stn.get_network())
            npts.append(stn.get_npts())
            sampling_rate.append(stn.get_samplingrate())
            station.append(stn.get_station())
            tracenumber.append(stn.get_tracenumber())
            format.append(stn.get_format())
            print(f"\rCreating Archive: Data Number {i+1} From {len(self.path)} Total Data | {(((i+1)/len(self.path))*100):.2f} %",end=' ')
        self.data = {
            'filepath': filepath,
            'filename': filename,
            'channel': channel,
            'delta': delta,
            'year': year,
            'index': index,
            'instrument': instrument,
            'network': network,
            'npts': npts,
            'sampling': sampling_rate,
            'julday': julday,
            'station': station,
            'tracenumber': tracenumber,
            'format': format,
        }

    def recast_archive(self):
        # Section 1
        unq_year = np.unique(np.array(merge_list(self.data['year'])))
        n1 = len(unq_year)
        n2 = len(self.data['filename'])
        # Section 2
        index_year_in_loop0 = []
        julday_in_loop0 = []
        index_file_in_loop0 = []
        year_in_loop0 = []
        station_in_loop0 = []
        count = 0
        for i in range(0,n1):
            # Section 3
            julday = []
            index_year_in_loop1 = []
            julday_in_loop1 = []
            index_file_in_loop1 = []
            year_in_loop1 = []
            station_in_loop1 = []
            # Section 4
            for j in range(0,n2):
                # Section 5
                index_year = np.where(np.array(self.data['year'][j]) == unq_year[i])
                julday_in_loop = np.unique(([self.data['julday'][j][index_year[0][k]] for k in range(0,np.shape(index_year)[1])])).tolist()
                julday.append(julday_in_loop)
                # Section 6
                index_year_in_loop2 = index_year[0].tolist()        
                julday_in_loop2 = ([self.data['julday'][j][index_year[0][k]] for k in range(0,np.shape(index_year)[1])])
                index_file_in_loop2 = ([j for k in range(0,len(julday_in_loop2))])
                year_in_loop2 = ([unq_year[i] for k in range(0,len(julday_in_loop2))])
                station_in_loop2 = ([self.data['station'][j][index_year[0][k]] for k in range(0,np.shape(index_year)[1])])
                # Section 7
                index_year_in_loop1.append(index_year_in_loop2)
                julday_in_loop1.append(julday_in_loop2)
                index_file_in_loop1.append(index_file_in_loop2)
                year_in_loop1.append(year_in_loop2)
                station_in_loop1.append(station_in_loop2)
                print(f"\rRecast Archive: Data Number {count+1} From {(n1*n2)+1} Total Data | {(((count+1)/((n1*n2)+1))*100):.2f} %",end=' ')
                count += 1
            # Section 8
            julday_year = merge_list(julday)
            julday_year = np.unique(julday_year).tolist()
            julday_year.sort()
            # Section 9
            index_year_in_loop1 = merge_list(index_year_in_loop1)
            julday_in_loop1 = merge_list(julday_in_loop1)
            index_file_in_loop1 = merge_list(index_file_in_loop1)
            year_in_loop1 = merge_list(year_in_loop1)
            station_in_loop1 = merge_list(station_in_loop1)
            # Section 10
            index_year_in_loop0.append(index_year_in_loop1)
            julday_in_loop0.append(julday_in_loop1)
            index_file_in_loop0.append(index_file_in_loop1)
            year_in_loop0.append(year_in_loop1)
            station_in_loop0.append(station_in_loop1)
        # Section 11
        index_year_in_loop0 = merge_list(index_year_in_loop0)
        julday_in_loop0 = merge_list(julday_in_loop0)
        index_file_in_loop0 = merge_list(index_file_in_loop0)
        year_in_loop0 = merge_list(year_in_loop0)
        station_in_loop0 = merge_list(station_in_loop0)
        # Section 12
        self.df = pd.DataFrame()
        self.df['Index Stream'] = index_file_in_loop0
        self.df['Index Trace'] = index_year_in_loop0
        self.df['Year'] = year_in_loop0
        self.df['Julian Day'] = julday_in_loop0
        self.df['Station'] = station_in_loop0
        print(f"\rRecast Archive: Data Number {count+1} From {(n1*n2)+1} Total Data | {(((count+1)/((n1*n2)+1))*100):.2f} %",end=' ')