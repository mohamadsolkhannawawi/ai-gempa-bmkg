def multiply_inside_list(x):
    if len(x) == 0:
        return 0
    elif len(x) == 1:
        return x
    elif len(x) == 2:
        return x[0]*x[1]
    elif len(x) >= 3:
        result = 1
        for i in x:
            result = result*i
        return result

def display(list):
    for i in list:
        print(i)

def isimmutable(x):
    try:
        len(x)
        logic = False
    except:
        logic = True
    return logic

def isStringNumber(input):
    try:
        x = int(input)
        output = True
    except:
        output = False
    return output

def check_specific_string(string,specific_string):
    if string == specific_string:
        return True
    else:
        return False

def str_julday(x):
    if x > 0 and x < 10:
        x = (str('00')+str(x))
    elif x > 9 and x < 100:
        x = (str('0')+str(x))
    elif x > 99 and x < 999:
        x = (str(x))
    elif x == 0:
        x = '000'
    return x

def str_hour(x):
    if x >= 0 and x < 10:
        x = (str('0')+str(x))
    elif x > 9 and x < 100:
        x = (str(x))
    return x

def filetype_string(x,filetype='.mseed'):
    n = len(x)
    filetype_c = x[n-(len(filetype)):n]
    if filetype == filetype_c:
        return 1
    else:
        return 0

def slashing(path,last=False):
    new_path = ''
    for i in range(0,len(path)):
        if path[i] == '\\':
            new_path = "".join([new_path,'/'])
        else:
            new_path = "".join([new_path,path[i]])
    if last == True:
        new_path = "".join([new_path,'/'])
    return new_path

def fix_double_slashing(temp_path):
    try:
        index = []
        path_list = []
        for i in range(0,len(temp_path)-1):
            path_list.append(temp_path[i])
            if temp_path[i] == '/' and temp_path[i+1] == '/':
                index.append(i+1)
        path_list.append(temp_path[-1])
        path_list.pop(index[0])
        result = "".join(path_list)
        return result
    except:
        return temp_path

def join_by(path,separator='/'):
    result = separator.join([path[0],path[1]])
    for i in range(2,len(path)):
        result = separator.join([result,path[i]])
    return result

def separate_by(path,separator='/'):
    index = []
    for i in range(0,len(path)):
        if path[i] == separator:
            index.append(i)
    result = [path[0:index[0]]]
    for i in range(0,len(index)-1):
        result.append(path[index[i]+1:index[i+1]])
    result.append(path[index[-1]+1:len(path)])
    return result

def find_index_list(value,value_list):
    for i in range(0,len(value_list)):
        if value == value_list[i]:
            index = i
            return index
            break

def list_to_percentage(input):
    # Input Type --> List (number)
    # Dependencies --> 1. default package (no imported package)
    sum_input = sum(input)
    output = [(input[i]/sum_input) * 100 for i in range(0,len(input))]
    return output

def str_to_float(input):
    output = [float(input[i]) for i in range(0,len(input))] 
    return output

def permutation2(data):
    new_data = []
    for i in range(0,len(data[0])):
        for j in range(0,len(data[1])):
            new_data.append([data[0][i],data[1][j]])
    return new_data

def permutation3(data):
    new_data = []
    for i in range(0,len(data[0])):
        for j in range(0,len(data[1])):
            for k in range(0,len(data[2])):
                new_data.append([data[0][i],data[1][j],data[2][k]])
    return new_data

def sliding_index(x,window=5,overlap_point=0):
    n = len(x)
    if overlap_point >= window:
        count = n+1
    elif overlap_point < window:
        count = 0
    s_index,e_index = [],[]
    while count <= n-window:
        s_index_in_loop = count
        e_index_in_loop = (count+window)
        if e_index_in_loop < n:
            s_index.append(s_index_in_loop)
            e_index.append(e_index_in_loop)
        elif e_index_in_loop > n:
            s_index.append(n-window)
            e_index.append(n)
        count += window-overlap_point
    return s_index,e_index