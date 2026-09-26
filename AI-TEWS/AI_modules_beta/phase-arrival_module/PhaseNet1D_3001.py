import torch
from torch import nn

activation_function_type = {
    "ReLU": "nn.ReLU(inplace=True)",
    "ELU": "nn.ELU(inplace=True)",
    "LReLU": "nn.LeakyReLU(inplace=True)",
    "GELU": "nn.GELU()",
    "Sigmoid": "nn.Sigmoid()"
}

logical_batchnorm = {
    True: "nn.BatchNorm1d(out_channel,0.1)",
    False: "None"
}

class SingleConv(nn.Module):
    def __init__(self,in_channel,out_channel,in_activation='ReLU',in_batchnorm=True,in_padding_mode='zeros'):
        super().__init__()
        self.model = nn.Sequential(
            nn.Conv1d(in_channel,out_channel,kernel_size=7,padding=3,padding_mode=in_padding_mode),
            eval(logical_batchnorm[in_batchnorm]),
            eval(activation_function_type[in_activation]),
        )
    def forward(self,x):
        return self.model(x)

class DownSampling(nn.Module):
    def __init__(self,in_channel,out_channel,in_activation='ReLU',in_batchnorm=True,in_padding_mode='zeros'):
        super().__init__()
        self.model = nn.Sequential(
            nn.Conv1d(out_channel,out_channel,kernel_size=7,padding=3,stride=4,padding_mode=in_padding_mode),
            eval(logical_batchnorm[in_batchnorm]),
            eval(activation_function_type[in_activation])
        )
    def forward(self,x):
        return self.model(x)

class UpSampling(nn.Module):
    def __init__(self,in_channel,out_channel,in_kersize=7,in_padding=3,in_stride=4,in_activation='ReLU',in_padding_mode='zeros'):
        super().__init__()
        self.model = nn.Sequential(
            nn.ConvTranspose1d(in_channel,out_channel,kernel_size=in_kersize,padding=in_padding,stride=in_stride,padding_mode=in_padding_mode),
            eval(activation_function_type[in_activation]),
        )
    def forward(self,x):
        return self.model(x)

class PhaseNet1D_3001(nn.Module):
    def __init__(self,in_channel=3,out_channel=1,ch=[8,11,16,22,32],in_activation='ReLU'):
        super(PhaseNet1D_3001,self).__init__()
        # Encoder
        # Encoder Layer 1
        self.block_e1 = SingleConv(in_channel,ch[0],in_activation=in_activation)
        self.block_e2 = SingleConv(ch[0],ch[0],in_activation=in_activation)
        # Encoder Layer 2
        self.block_e3 = DownSampling(ch[0],ch[0],in_activation=in_activation)
        self.block_e4 = SingleConv(ch[0],ch[1],in_activation=in_activation)
        # Encoder Layer 3
        self.block_e5 = DownSampling(ch[1],ch[1],in_activation=in_activation)
        self.block_e6 = SingleConv(ch[1],ch[2],in_activation=in_activation)
        # Encoder Layer 4
        self.block_e7 = DownSampling(ch[2],ch[2],in_activation=in_activation)
        self.block_e8 = SingleConv(ch[2],ch[3],in_activation=in_activation)

        # Transisition Layer
        self.block_e9 = DownSampling(ch[3],ch[3],in_activation=in_activation)
        self.block_e10 = SingleConv(ch[3],ch[4],in_activation=in_activation)
        
        # Decoder
        # Decoder Block 1
        self.block_d1 = UpSampling(ch[4],ch[3],in_kersize=7,in_padding=2,in_stride=4,in_activation=in_activation)
        self.block_d2 = SingleConv(ch[3]*2,ch[3],in_activation=in_activation)
        # Decoder Block 2
        self.block_d3 = UpSampling(ch[3],ch[2],in_kersize=8,in_padding=2,in_stride=4,in_activation=in_activation)
        self.block_d4 = SingleConv(ch[2]*2,ch[2],in_activation=in_activation)
        # Decoder Block 3
        self.block_d5 = UpSampling(ch[2],ch[1],in_kersize=7,in_padding=2,in_stride=4,in_activation=in_activation)
        self.block_d6 = SingleConv(ch[1]*2,ch[1],in_activation=in_activation)
        # Decoder Block 4
        self.block_d7 = UpSampling(ch[1],ch[0],in_kersize=7,in_padding=3,in_stride=4,in_activation=in_activation)
        self.block_d8 = SingleConv(ch[0]*2,ch[0],in_activation=in_activation)
        
        # Output Layer
        self.block_d9 = SingleConv(ch[0],out_channel,in_activation='Sigmoid')
        
    def forward(self,x):
        # 1. Encoder Layer
        # Encoder Block 1
        x1 = self.block_e1(x)
        x1 = self.block_e2(x1)
        # Encoder Block 2
        x2 = self.block_e3(x1)
        x2 = self.block_e4(x2)
        # Encoder Block 3
        x3 = self.block_e5(x2)
        x3 = self.block_e6(x3)
        # Encoder Block 4
        x4 = self.block_e7(x3)
        x4 = self.block_e8(x4)
        
        # 2. Transisition Layer
        x = self.block_e9(x4)
        x = self.block_e10(x)
        
        # 3. Decoder Layer
        # Decoder Block 1
        x = self.block_d1(x)
        x = torch.cat([x,x4],dim=1)
        x = self.block_d2(x)
        # Decoder Block 2
        x = self.block_d3(x)
        x = torch.cat([x,x3],dim=1)
        x = self.block_d4(x)
        # Decoder Block 3
        x = self.block_d5(x)
        x = torch.cat([x,x2],dim=1)
        x = self.block_d6(x)
        # Decoder Block 4
        x = self.block_d7(x)
        x = torch.cat([x,x1],dim=1)
        x = self.block_d8(x)
        
        # 4. Output Layer
        x = self.block_d9(x)
        return x