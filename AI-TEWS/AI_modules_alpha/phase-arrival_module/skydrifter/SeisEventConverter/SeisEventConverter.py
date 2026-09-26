from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *
from skydrifter.SeisEventConverter.CatalogueCollection import *
from skydrifter.PeculiarSupport.support import make_ot_df,make_at_df

catalogue_type = {
    "Seisgram": "Catalogue_Seisgram",
}

class SeisEventConverter:
    def __init__(self,event,type):
        self.converter = eval(catalogue_type[type])
        self.event = event

    def import_path_collector(self,path_df,path_collector):
        self.path_df = path_df
        self.path_collector = path_collector
    
    def convert_all(self,folder='converted',waveform=False,event=True,**kwargs):
        try:
            dfo = make_ot_df(self.event)
            eventID_index = [dfo[dfo['EventID'] == kwargs['eventID'][i]].index[0] for i in range(0,len(kwargs['eventID']))]
            dfo = dfo.iloc[eventID_index]
            dfo.index = [i for i in range(0,len(dfo))]
        except:
            dfo = make_ot_df(self.event)        
        if waveform == False and event  == True:
            for index in range(0,len(dfo)):
                dfa = make_at_df(self.event,eventID=dfo['EventID'].iloc[index],additional=['year'])
                lines = self.converter.convert_without_waveform(self,dfa,self.event)
                os.makedirs(folder,exist_ok=True)
                filename = join_by([dfo['EventID'].iloc[index],'pick'],separator='.')
                filename = join_by([folder,filename],separator='\\')
                write_to_file(filename,lines)
                print(f"\rEvent Number {index+1} Processed From {len(dfo)} Total Event | {(((index+1)/(len(dfo)))*100):.2f} %",end=' ')
        elif waveform == True and event == True:
            for index in range(0,len(dfo)):
                dfa = make_at_df(self.event,eventID=dfo['EventID'].iloc[index],additional=['year'])
                lines,stn_out = self.converter.convert_with_waveform(self,dfa=dfa,event=self.event,path_df=self.path_df,path_collector=self.path_collector)
                foldername = join_by([folder,dfo['EventID'].iloc[index]],separator='\\')
                os.makedirs(foldername,exist_ok=True)
                filename_pick = join_by([dfo['EventID'].iloc[index],'pick'],separator='.')
                filename_pick = join_by([foldername,filename_pick],separator='\\')
                write_to_file(filename_pick,lines)
                filename_stream = join_by([dfo['EventID'].iloc[index],'mseed'],separator='.')
                filename_stream = join_by([foldername,filename_stream],separator='\\')
                stn_out.write(filename_stream,format="MSEED")
                print(f"\rEvent Number {index+1} Processed From {len(dfo)} Total Event | {(((index+1)/(len(dfo)))*100):.2f} %",end=' ')
        elif waveform == True and event == False:
            for index in range(0,len(dfo)):
                dfa = make_at_df(self.event,eventID=dfo['EventID'].iloc[index],additional=['year'])
                lines,stn_out = self.converter.convert_with_waveform(self,dfa=dfa,event=self.event,path_df=self.path_df,path_collector=self.path_collector)
                os.makedirs(folder,exist_ok=True)
                filename_stream = join_by([dfo['EventID'].iloc[index],'mseed'],separator='.')
                filename_stream = join_by([folder,filename_stream],separator='\\')
                stn_out.write(filename_stream,format="MSEED")
                print(f"\rEvent Number {index+1} Processed From {len(dfo)} Total Event | {(((index+1)/(len(dfo)))*100):.2f} %",end=' ')