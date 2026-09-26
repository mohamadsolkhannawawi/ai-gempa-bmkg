class SeisStreamRecap:
    def __init__(self,stream):
        self.stream = stream

    def get_format(self):
        return self.stream[0].stats._format
        
    def get_tracenumber(self):
        return len(self.stream)
        
    def get_network(self):
        network = [self.stream[i].stats.network for i in range(0,len(self.stream))]
        return network
        
    def get_station(self):
        station = [self.stream[i].stats.station for i in range(0,len(self.stream))]
        return station

    def get_channel(self):
        channel = [self.stream[i].stats.channel[-1] for i in range(0,len(self.stream))]
        return channel

    def get_instrument(self):
        instrument = [self.stream[i].stats.channel[0:1] for i in range(0,len(self.stream))]
        return instrument

    def get_detail_instrument(self):
        detail_instrument = [self.stream[i].stats.channel[0:2] + '.' + self.stream[i].stats.mseed.dataquality for i in range(0,len(self.stream))]
        return detail_instrument

    def get_starttime(self):
        starttime = [str(self.stream[i].stats.starttime) for i in range(0,len(self.stream))]
        return starttime

    def get_endtime(self):
        endtime = [str(self.stream[i].stats.endtime) for i in range(0,len(self.stream))]
        return endtime

    def get_year(self):
        year = [(self.stream[i].stats.starttime.year) for i in range(0,len(self.stream))]
        return year

    def get_julday(self):
        julday = [(self.stream[i].stats.starttime.julday) for i in range(0,len(self.stream))]
        return julday
        
    def get_samplingrate(self):
        sampling_rate = [self.stream[i].stats.sampling_rate for i in range(0,len(self.stream))]
        return sampling_rate

    def get_delta(self):
        delta = [self.stream[i].stats.delta for i in range(0,len(self.stream))]
        return delta

    def get_npts(self):
        npts = [self.stream[i].stats.npts for i in range(0,len(self.stream))]
        return npts
        
    def get_index(self):
        index = [i for i in range(0,len(self.stream))]
        return index