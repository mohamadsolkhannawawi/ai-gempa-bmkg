from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *

import numpy as np
import obspy as op

class Catalogue_Seisan:
    def __init__(self,path):
        self.line_list = Catalogue_Seisan.get_line_list(self,path)

    def get_line_list(self,path):
        f = open(path,'r')
        line_list = f.readlines()
        f.close()
        return line_list

    def get_index(self):
        self.index = [i+1 for i in range(0,len(self.line_list)-1) if check_whitespace(self.line_list[i]) == True and check_whitespace(self.line_list[i+1]) == False]
        self.index.insert(0,0)
        return self.index

    def get_date(self):
        self.date = []
        for i in range(0,len(self.index)):
            splitted_line1 = remove_whitespace(self.line_list[self.index[i]])
            index_in_loop = [i for i in range(0,len(splitted_line1)) if splitted_line1[i] == 'L'][0]
            splitted_line2 = splitted_line1[0:index_in_loop-2]
            if len(splitted_line2) == 3:
                year = splitted_line2[0]
                month = str_hour(int(splitted_line2[1]))
                day = str_hour(int(splitted_line2[2]))
                self.date.append(join_by([year,month,day],separator='-'))
            if len(splitted_line2) == 2:
                if (len(splitted_line2[-1])) == 3:
                    year = splitted_line2[0]
                    month = str_hour(int(splitted_line2[-1][0]))
                    day = str_hour(int(splitted_line2[-1][1:len(splitted_line2[-1])]))
                    self.date.append(join_by([year,month,day],separator='-'))
                elif (len(splitted_line2[-1])) == 4:
                    year = splitted_line2[0]
                    month = str_hour(int(splitted_line2[-1][0:2]))
                    day = str_hour(int(splitted_line2[-1][2:len(splitted_line2[-1])]))
                    self.date.append(join_by([year,month,day],separator='-'))
        return self.date

    def get_unq_date(self):
        self.unq_date = np.unique(np.array(self.date))
        return self.unq_date

    def get_date_count(self):
        self.date_count = []
        for i in range(0,len(self.unq_date)):
            date_count_loop = []
            for j in range(0,len(self.date)):
                if self.unq_date[i] == self.date[j]:
                    date_count_loop.append(j)
            self.date_count.append(date_count_loop)
            print(f"\rCollect All Event Per Day {i+1} From {len(self.unq_date)} Total Day Available | {(((i+1)/len(self.unq_date))*100):.2f} %",end=' ')
        return self.date_count

    def get_origin_time(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        splitted_line1 = remove_whitespace(event_line_list[0])
        index_in_loop1 = [i for i in range(0,len(splitted_line1)) if splitted_line1[i] == 'L'][0]
        splitted_line2 = splitted_line1[index_in_loop1-2:index_in_loop1]
        hour = str_hour(int(splitted_line2[0][0:2]))
        minute = str_hour(int(splitted_line2[0][2:len(splitted_line2[0])]))
        second = splitted_line2[-1]
        if float(second) == 60:
            second = '00'
        origin_time = self.date[idx] + 'T' + join_by([hour,minute,second],separator=':')
        return origin_time

    def get_latitude(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        splitted_line1 = remove_whitespace(event_line_list[0])
        index_in_loop1 = [i for i in range(0,len(splitted_line1)) if splitted_line1[i] == 'L'][0]
        splitted_line2 = splitted_line1[index_in_loop1-2:index_in_loop1]
        index_in_loop2 = [i for i in range(0,len(splitted_line1)) if splitted_line1[i] == 'BMG'][0]
        splitted_line3 = splitted_line1[index_in_loop1+1:index_in_loop2]
        if len(splitted_line3) == 2:
            lat = float(remove_nonnumber_char(splitted_line3[0]))
        elif len(splitted_line3) == 3:
            lat = float(remove_nonnumber_char(splitted_line3[0]))
        return lat

    def get_longitude(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        splitted_line1 = remove_whitespace(event_line_list[0])
        index_in_loop1 = [i for i in range(0,len(splitted_line1)) if splitted_line1[i] == 'L'][0]
        splitted_line2 = splitted_line1[index_in_loop1-2:index_in_loop1]
        index_in_loop2 = [i for i in range(0,len(splitted_line1)) if splitted_line1[i] == 'BMG'][0]
        splitted_line3 = splitted_line1[index_in_loop1+1:index_in_loop2]
        if len(splitted_line3) == 2:
            long = float(remove_nonnumber_char(splitted_line3[1]))
        elif len(splitted_line3) == 3:
            long = float(remove_nonnumber_char(splitted_line3[1]))
        return long

    def get_depth(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        splitted_line1 = remove_whitespace(event_line_list[0])
        index_in_loop1 = [i for i in range(0,len(splitted_line1)) if splitted_line1[i] == 'L'][0]
        splitted_line2 = splitted_line1[index_in_loop1-2:index_in_loop1]
        index_in_loop2 = [i for i in range(0,len(splitted_line1)) if splitted_line1[i] == 'BMG'][0]
        splitted_line3 = splitted_line1[index_in_loop1+1:index_in_loop2]
        if len(splitted_line3) == 2:
            depth = -1
        elif len(splitted_line3) == 3:
            depth = float(remove_nonnumber_char(splitted_line3[2]))
            if depth == 0:
                depth = -1
        return depth

    def get_magnitude(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        splitted_line1 = remove_whitespace(event_line_list[0])
        index_in_loop1 = [i for i in range(0,len(splitted_line1)) if splitted_line1[i] == 'L'][0]
        splitted_line2 = splitted_line1[index_in_loop1-2:index_in_loop1]
        index_in_loop2 = [i for i in range(0,len(splitted_line1)) if splitted_line1[i] == 'BMG'][0]
        mag = float((splitted_line1[index_in_loop2+1]))
        return mag

    def get_eventID(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        logic = False
        for i in range(0,len(event_line_list)):
            splitted_line = remove_whitespace(event_line_list[i])
            for j in range(0,len(splitted_line)):
                if splitted_line[j] == 'STATUS:':
                    eventID = splitted_line[j+1][3:len(splitted_line[j+1])]
                    logic = True
            if logic == True:
                break
        return eventID

    def get_station(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        station = []
        index_in_loop3 = [i for i in range(0,len(event_line_list)) if remove_whitespace(event_line_list[i])[1] == 'SP'][0]
        for i in range(index_in_loop3+1,len(event_line_list)):
            splitted_line4 = remove_whitespace(event_line_list[i])
            if splitted_line4[2] == 'EP' or splitted_line4[2] == 'ES':
                station.append(splitted_line4[0])
        return station

    def get_phase(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        phase = []
        index_in_loop3 = [i for i in range(0,len(event_line_list)) if remove_whitespace(event_line_list[i])[1] == 'SP'][0]
        for i in range(index_in_loop3+1,len(event_line_list)):
            splitted_line4 = remove_whitespace(event_line_list[i])
            if splitted_line4[2] == 'EP' or splitted_line4[2] == 'ES':
                phase.append(splitted_line4[2][-1])
        return phase

    def get_arrival_time(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        arrival_time = []
        index_in_loop3 = [i for i in range(0,len(event_line_list)) if remove_whitespace(event_line_list[i])[1] == 'SP'][0]
        for i in range(index_in_loop3+1,len(event_line_list)):
            splitted_line4 = remove_whitespace_with_D(event_line_list[i]) # nanti cek lagi
            if splitted_line4[2] == 'EP' or splitted_line4[2] == 'ES':
                if len(splitted_line4[3]) <= 2:
                    try:
                        logic = splitted_line4[3]
                        hour = str_hour(int(float(splitted_line4[3])))
                        minute = str_hour(int(float(splitted_line4[4])))
                        second = str_hour(float(splitted_line4[5]))
                        arrival_time.append(join_by([self.date[idx],'T',join_by([hour,minute,second],separator=':')],separator=''))
                    except:
                        pass
                elif len(splitted_line4[3]) > 2:
                    second = str_hour(float(splitted_line4[4]))
                    splitted_line5 = splitted_line4[3]
                    if len(splitted_line5) == 3:
                        hour = str_hour(int(float(splitted_line5[0])))
                        minute = str_hour(int(float(splitted_line5[1:3])))
                    elif len(splitted_line5) == 4: 
                        hour = str_hour(int(float(splitted_line5[0:2])))
                        minute = str_hour(int(float(splitted_line5[2:4])))
                    arrival_time.append(join_by([self.date[idx],'T',join_by([hour,minute,second],separator=':')],separator=''))
        return arrival_time

class Catalogue_BMKG:
    def __init__(self,path):
        self.line_list = Catalogue_BMKG.get_line_list(self,path)

    def get_line_list(self,path):
        f = open(path,'r')
        line_list = f.readlines()
        f.close()
        return line_list
        
    def get_index(self):
        self.index = []
        for i in range(0,len(self.line_list)):
            splitted_line1 = self.line_list[i].split()
            try:
                if splitted_line1[0] == 'EventID:' and len(splitted_line1) != 0:
                    splitted_line2 = self.line_list[i+2].split()
                    self.index.append(i)
            except:
                continue
        return self.index

    def get_date(self):
        self.date = []
        for i in range(0,len(self.line_list)):
            splitted_line1 = self.line_list[i].split()
            try:
                if splitted_line1[0] == 'EventID:' and len(splitted_line1) != 0:
                    splitted_line2 = self.line_list[i+2].split()
                    self.date.append(splitted_line2[0])
            except:
                continue
        return self.date

    def get_unq_date(self):
        self.unq_date = np.unique(np.array(self.date))
        return self.unq_date

    def get_date_count(self):
        self.date_count = []
        for i in range(0,len(self.unq_date)):
            date_count_loop = []
            for j in range(0,len(self.date)):
                if self.unq_date[i] == self.date[j]:
                    date_count_loop.append(j)
            self.date_count.append(date_count_loop)
            print(f"\rCollect All Event Per Day {i+1} From {len(self.unq_date)} Total Day Available | {(((i+1)/len(self.unq_date))*100):.2f} %",end=' ')
        return self.date_count

    def get_origin_time(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        origin_time = event_line_list[2].split()[1]
        return self.date[idx]+'T'+origin_time
        
    def get_latitude(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        lat = event_line_list[2].split()[2]
        return lat

    def get_longitude(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        long = event_line_list[2].split()[3]
        return long
    
    def get_depth(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        depth = event_line_list[2].split()[4]
        return depth

    def get_magnitude(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        mag = event_line_list[2].split()[5]
        return mag
        
    def get_eventID(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        eventID = event_line_list[0].split()[-1]
        return eventID

    def get_station(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        for i in range(0,len(event_line_list)):
            split = event_line_list[i].split()
            if len(split) != 0:
                if split[0] == 'Net': 
                    start_index = i+1
                    break       
        station = []
        for i in range(start_index,len(event_line_list)):
            split = event_line_list[i].split()
            if len(split) != 0:
                station.append(split[1])
        return station

    def get_phase(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        for i in range(0,len(event_line_list)):
            split = event_line_list[i].split()
            if len(split) != 0:
                if split[0] == 'Net': 
                    start_index = i+1
                    break       
        phase = []
        for i in range(start_index,len(event_line_list)):
            split = event_line_list[i].split()
            if len(split) != 0:
                phase.append(split[2])
        return phase

    def get_arrival_time(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        for i in range(0,len(event_line_list)):
            split = event_line_list[i].split()
            if len(split) != 0:
                if split[0] == 'Net': 
                    start_index = i+1
                    break       
        arrival_time = []
        for i in range(start_index,len(event_line_list)):
            split = event_line_list[i].split()
            if len(split) != 0:
                arrival_time.append(split[4])
        return [self.date[idx]+'T'+arrival_time[i] for i in range(0,len(arrival_time))]

class Catalogue_Seisgram:
    def __init__(self,path):
        self.line_list = Catalogue_Seisgram.get_line_list(self,path)

    def get_line_list(self,path):
        cat_path = scan_format_path(path,format='.pick')
        if len(cat_path) == 1:
            # Read First Path In cat_path
            f = open(cat_path[0],'r')
            line_list_one = f.readlines()
            f.close()
            line_list_one = concat_list([separate_by(cat_path[0])[-1]],line_list_one)
        elif len(cat_path) == 2:
            # Read First Path In cat_path
            f = open(cat_path[0],'r')
            line_list_one1 = f.readlines()
            f.close()
            line_list_one1 = concat_list([separate_by(cat_path[0])[-1]],line_list_one1)
            # Read Second Path In cat_path
            f = open(cat_path[1],'r')
            line_list_one2 = f.readlines()
            f.close()
            line_list_one2 = concat_list([separate_by(cat_path[1])[-1]],line_list_one2)
            # Build line_list
            line_list_one = concat_list(line_list_one1,line_list_one2)
        elif len(cat_path) >= 3:
            # Read First Path In cat_path
            f = open(cat_path[0],'r')
            line_list_one1 = f.readlines()
            f.close()
            line_list_one1 = concat_list([separate_by(cat_path[0])[-1]],line_list_one1)
            # Read Second Path In cat_path
            f = open(cat_path[1],'r')
            line_list_one2 = f.readlines()
            f.close()
            line_list_one2 = concat_list([separate_by(cat_path[1])[-1]],line_list_one2)
            # Read n Path In cat_path
            line_list_one = concat_list(line_list_one1,line_list_one2)
            for i in range(2,len(cat_path)):
                f = open(cat_path[i],'r')
                line_list_one_in_loop = f.readlines()
                f.close()
                if len(line_list_one_in_loop) != 0:
                    line_list_one_in_loop = concat_list([separate_by(cat_path[i])[-1]],line_list_one_in_loop)
                    line_list_one = concat_list(line_list_one,line_list_one_in_loop)
                print(f"\rCollect All Event Per Day {i+1} From {len(cat_path)} Total Day Available | {(((i+1)/len(cat_path))*100):.2f} %",end=' ')
        return line_list_one
    
    def get_index(self):
        self.index = [i for i in range(0,len(self.line_list)-1) if check_specific_string(self.line_list[i],'\n') == True and check_specific_string(self.line_list[i+1],'\n') == False]
        self.index = [i+1 for i in self.index]
        self.index.insert(0,0)
        return self.index

    def get_date(self):
        self.date = []
        for i in range(0,len(self.index)):
            try:
                splitted_line1 = separate_by(self.line_list[self.index[i]+1],separator=' ')[6]
                time = splitted_line1
                self.date.append(join_by([time[0:4],time[4:6],time[6:8]],separator='-'))
            except:
                print(self.index[i])
                pass
        return self.date

    def get_unq_date(self):
        self.unq_date = np.unique(np.array(self.date))
        return self.unq_date

    def get_date_count(self):
        self.date_count = []
        for i in range(0,len(self.unq_date)):
            date_count_loop = []
            for j in range(0,len(self.date)):
                if self.unq_date[i] == self.date[j]:
                    date_count_loop.append(j)
            self.date_count.append(date_count_loop)
        return self.date_count

    def get_origin_time(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        splitted_line1 = separate_by(event_line_list[0],separator='.')[0]
        splitted_line2 = separate_by(splitted_line1,separator='_')
        date = splitted_line2[0]
        time = splitted_line2[1]
        origin_time = join_by([date[0:4],date[4:6],date[6:8]],separator='-') + 'T' + join_by([time[0:2],time[2:4],time[4:6]],separator=':')
        return origin_time

    def get_latitude(self,s_indx,e_indx,idx):
        return '-1'

    def get_longitude(self,s_indx,e_indx,idx):
        return '-1'
    
    def get_depth(self,s_indx,e_indx,idx):
        return '-1'

    def get_magnitude(self,s_indx,e_indx,idx):
        return '-1'

    def get_eventID(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        return separate_by(event_line_list[0],separator='.')[0]
    
    def get_station(self,s_indx,e_indx,idx):
        station = []
        event_line_list = self.line_list[s_indx:e_indx]
        for i in range(1,len(event_line_list)):
            splitted_line1 = remove_whitespace(event_line_list[i])
            station.append(splitted_line1[0])
        return station

    def get_phase(self,s_indx,e_indx,idx):
        phase = []
        event_line_list = self.line_list[s_indx:e_indx]
        for i in range(1,len(event_line_list)):
            splitted_line1 = remove_whitespace(event_line_list[i])
            phase.append(splitted_line1[4])
        return phase

    def get_arrival_time(self,s_indx,e_indx,idx):
        arrival_time = []
        event_line_list = self.line_list[s_indx:e_indx]
        for i in range(1,len(event_line_list)):
            splitted_line1 = remove_whitespace(event_line_list[i])
            date = splitted_line1[6]
            hour_minute = splitted_line1[7]
            second = splitted_line1[8]
            arrival_time.append(join_by([date[0:4],date[4:6],date[6:8]],separator='-') + 'T' + join_by([hour_minute[0:2],hour_minute[2:4],second],separator=':'))
        return arrival_time

class Catalogue_Japan:
    def __init__(self,path):
        self.line_list = Catalogue_Japan.get_line_list(self,path)

    def get_line_list(self,path):
        f = open(path,'r')
        line_list = f.readlines()
        f.close()
        return line_list

    def get_index(self):
        self.index = [i+1 for i in range(0,len(self.line_list)-1) if self.line_list[i][0] == 'E']
        self.index.insert(0,0)
        return self.index
    
    def get_date(self):
        self.date = []
        for i in range(0,len(self.index)):
            year = self.line_list[self.index[i]][1:5]
            month = self.line_list[self.index[i]][5:7]
            day = self.line_list[self.index[i]][7:9]
            self.date.append(join_by([year,month,day],separator='-'))
        return self.date

    def get_unq_date(self):
        self.unq_date = np.unique(np.array(self.date))
        return self.unq_date

    def get_date_count(self):
        self.date_count = []
        for i in range(0,len(self.unq_date)):
            date_count_loop = []
            for j in range(0,len(self.date)):
                if self.unq_date[i] == self.date[j]:
                    date_count_loop.append(j)
            self.date_count.append(date_count_loop)
            # print(f"\rCollect All Event Per Day {i+1} From {len(self.unq_date)} Total Day Available | {(((i+1)/len(self.unq_date))*100):.2f} %",end=' ')
        return self.date_count

    def get_origin_time(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        hour = event_line_list[0][9:11]
        minute = event_line_list[0][11:13]
        second = event_line_list[0][13:17]
        second = insert_string(second,2,'.')
        origin_time = self.date[idx] + 'T' + join_by([hour,minute,second],separator=':')
        return origin_time


    def get_latitude(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        degree = remove_whitespace_string(event_line_list[0][21:24])
        minute = remove_whitespace_string(event_line_list[0][24:28])
        minute = insert_string(minute,2,'.')
        try:
            latitude = float(degree) + (float(minute)/60)
            return latitude
        except:
            return '-1'

    def get_longitude(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        degree = remove_whitespace_string(event_line_list[0][32:36])
        minute = remove_whitespace_string(event_line_list[0][36:40])
        minute = insert_string(minute,2,'.')
        try:
            longitude = float(degree) + (float(minute)/60)
            return longitude
        except:
            return '-1'


    def get_depth(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        depth = remove_whitespace_string(event_line_list[0][44:49])
        if len(depth) == 4:
            depth = insert_string(depth,3,'.')
        elif len(depth) == 5:
            depth = insert_string(depth,3,'.')
        try:
            depth = float(depth)
            return depth
        except:
            return '-1'

    def get_magnitude(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        mag = remove_whitespace_string(event_line_list[0][52:54])
        mag_type = event_line_list[0][54:55]
        try:
            mag = int(mag)
            if mag <= 0:
                mag = -1
            pass
        except:
            mag = -1
        return mag

    def get_eventID(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        eventID = remove_whitespace_string(event_line_list[0][0:18])
        return eventID

    def get_station(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        station = []
        for i in range(1,len(event_line_list)):
            station1 = remove_whitespace_string(event_line_list[i][1:7]) + '_' + remove_whitespace_string(event_line_list[i][7:11])
            station2 = remove_whitespace_string(event_line_list[i][1:7]) + '_' + remove_whitespace_string(event_line_list[i][7:11])
            phase1 = remove_whitespace_string(event_line_list[i][15:19])
            phase2 = remove_whitespace_string(event_line_list[i][27:31])
            if phase1[-1] == 'P' or phase1[-1] == 'S':
                station.append(station1)
            if phase2[-1] == 'S' or phase2[-1] == 'P':
                station.append(station2)
        return station

    def get_phase(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        phase = []
        for i in range(1,len(event_line_list)):
            phase1 = remove_whitespace_string(event_line_list[i][15:19])
            phase2 = remove_whitespace_string(event_line_list[i][27:31])
            if phase1[-1] == 'P' or phase1[-1] == 'S':
                phase.append(phase1[-1])
            if phase2[-1] == 'S' or phase2[-1] == 'P':
                phase.append(phase2[-1])
        return phase

    def get_arrival_time(self,s_indx,e_indx,idx):
        event_line_list = self.line_list[s_indx:e_indx]
        arrival_time = []
        for i in range(1,len(event_line_list)):
            hour = remove_whitespace_string(event_line_list[i][19:21])
            minute_P = remove_whitespace_string(event_line_list[i][21:23])
            second_P = remove_whitespace_string(event_line_list[i][23:27])
            if len(second_P) > 2:
                second_P = insert_string(second_P,2,'.')
            minute_S = remove_whitespace_string(event_line_list[i][31:33])
            second_S = remove_whitespace_string(event_line_list[i][33:37])
            if len(second_S) > 2:
                second_S = insert_string(second_S,2,'.')
            phase1 = remove_whitespace_string(event_line_list[i][15:19])
            phase2 = remove_whitespace_string(event_line_list[i][27:31])
            if phase1[-1] == 'P' or phase1[-1] == 'S':
                try:
                    arrival_P = self.date[idx] + 'T' + join_by([hour,minute_P,second_P],separator=':')
                    test_utcdatetime = op.UTCDateTime(arrival_P)
                    arrival_time.append(arrival_P)
                except:
                    arrival_time.append('-1')
            if phase2[-1] == 'S' or phase2[-1] == 'P':
                try:
                    arrival_S = self.date[idx] + 'T' + join_by([hour,minute_S,second_S],separator=':')
                    test_utcdatetime = op.UTCDateTime(arrival_S)
                    arrival_time.append(arrival_S)
                except:
                    arrival_time.append('-1')
        return arrival_time