from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *

import pandas as pd

class SeisAutoMag:
    def __init__(self,df_event,df_loc):
        self.df_event = df_event
        self.df_loc = df_loc

    def execute(self,automag_model):
        self.df_event = self.df_event.loc[0:3]
        mag_feature = pd.DataFrame()
        reference = self.df_event.loc[0]
        for i in range(1,4):
            mag_feature['tp_' + str(i)] = [abs(self.df_event['P'].iloc[i]-reference['P'])]
        for i in range(1,4):
            mag_feature['ts_' + str(i)] = [abs(self.df_event['S'].iloc[i]-reference['S'])]
        for i in range(1,4):
            mag_feature['x_station_' + str(i)] = [self.df_event['X Station'].iloc[i]]
        for i in range(1,4):
            mag_feature['y_station_' + str(i)] = [self.df_event['Y Station'].iloc[i]]
        for i in range(1,4):
            mag_feature['ts_tp_' + str(i)] = [abs(self.df_event['S'].iloc[i]-self.df_event['P'].iloc[i])]
        mag_feature['Longitude'] = [self.df_loc['Longitude'].iloc[0]]
        mag_feature['Latitude'] = [self.df_loc['Latitude'].iloc[0]]
        mag_feature['Depth'] = [self.df_loc['Depth'].iloc[0]]
        mag_feature['Region'] = [self.df_loc['Region'].iloc[0]]
        mag_feature['Sub Region'] = [self.df_loc['Sub Region'].iloc[0]]
        mag_feature['Terrain'] = [self.df_loc['Terrain'].iloc[0]]
        magnitude = automag_model['model1'].predict(mag_feature)[0]
        self.df_loc['Magnitude'] = [magnitude]