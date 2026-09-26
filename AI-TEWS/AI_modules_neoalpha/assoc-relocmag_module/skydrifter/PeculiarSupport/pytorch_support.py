import torch
import copy


def pytorch_predict(stn,model,s_index,e_index):
    # Convert Data to Torch Tensor
    X = torch.zeros(1,3,3001)
    for i in range(0,3):
        X[:,i,:] = copy.deepcopy(torch.FloatTensor((stn[i].data)[s_index:e_index]))
    # Predict With Your Model
    with torch.no_grad():
        model.eval()
        y = model(X)
    # Convert Back to Numpy
    output = copy.deepcopy(y[0,0].numpy())
    return output