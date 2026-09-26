# nonpartisan imported funtion
from skydrifter.Utils.nonpartisan import *

# built-in python imported funtion
import os
import copy

# installed library imported funtion
import numpy as np


# Partisan 1
# all functions in this group depend on only nonpartisan group of function
def concat_list(x,y):
    if isimmutable(x) == True and isimmutable(y) == False:
        x = [x] + y
    elif isimmutable(x) == False and isimmutable(y) == True:
        x.append(y)
    elif isimmutable(x) == False and isimmutable(y) == False:
        for i in range(0,len(y)):
            x.append(y[i])
    elif isimmutable(x) == True and isimmutable(y) == True:
        x = [x,y]
    return x

def remove_nonnumber_char(string1):
    string2 = []
    dot_count = 0
    strip_count = 0
    for i in range(0,len(string1)):
        try:
            logic = float(string1[i])
            string2.append(string1[i])
        except:
            if string1[i] == '.' and dot_count == 0:
                string2.append(string1[i])
                dot_count += 1
            if string1[i] == '-' and strip_count == 0:
                string2.append(string1[i])
                strip_count += 1
    return (join_by(string2,separator=''))

def remove_whitespace_with_D(string):
    try:
        string1 = separate_by(string,separator=' ')
        string2 = [string1[i] for i in range(0,len(string1)) if string1[i] != '']
        try:
            check = int(string2[3]) 
        except:
            string2.pop(3)
        return string2
    except:
        return string

def remove_whitespace_string(x):
    try:
        new_x = [x[i] for i in range(0,len(x)) if x[i] != ' ']
        if len(new_x) == 1:
            new_x = new_x[0]
        elif len(new_x) != 1:
            new_x = join_by(new_x,separator='')
        return new_x
    except:
        return x

def insert_string(x,index,char):
    count = 0
    new_x = []
    for i in range(0,len(x)+1):
        if i != index:
            new_x.append(x[count])
            count += 1
        elif i == index:
            new_x.append(char)
    return join_by(new_x,separator='')
    
def remove_whitespace(string):
    try:
        string1 = separate_by(string,separator=' ')
        string2 = [string1[i] for i in range(0,len(string1)) if string1[i] != '']
        return string2
    except:
        return string

def path_filenumber_correction(path):
    # Section 1
    filenumber = []
    logic = 0
    for i in range(0,len(path)):
        try:
            split = separate_by((separate_by(path[i])[-1]),separator='_')[-1]
            filenumber.append(int((separate_by(split,separator='.'))[0]))
            logic = 1
        except:
            split = (separate_by(path[i])[-1])
            filenumber.append(int((separate_by(split,separator='.'))[0]))
    filenumber.sort()
    # Section 2
    if logic == 1:
        additional_join = separate_by((separate_by(path[i])[-1]),separator='_')
        additional_join = join_by(additional_join[0:len(additional_join)-1],separator='_')
        split = separate_by(path[0],separator='/')
        split = join_by(split[0:len(split)-1],separator='/')
        split = join_by([split,additional_join])
        new_path = [join_by([split,join_by([str(filenumber[i]),'pth'],separator='.')],separator='_') for i in range(0,len(filenumber))]
    elif logic == 0:
        split = separate_by(path[0],separator='/')
        split = join_by(split[0:len(split)-1],separator='/')
        new_path = [join_by([split,join_by([str(filenumber[i]),'pth'],separator='.')],separator='/') for i in range(0,len(filenumber))]
    return new_path
# Partisan 1


# Partisan 2
# all function in this group depend on nonpartisan group of funtion, imported built-in python function, and installed library funtion
def write_to_file(filename, content):
    if os.path.exists(filename):
        os.remove(filename)
    with open(filename, 'w') as file:
        for i in range(0,len(content)):
            file.write(content[i])
            if i != len(content)-1:
                file.write('\n')

def scan_subdir(path):
    path = slashing(path,last=True)
    try:
        folder_list = os.listdir(path)
    except:
        folder_list = []
    new_pathdir = []
    for i in range(0,len(folder_list)):
        new_pathdir.append((path+folder_list[i]))
    return new_pathdir

def copy_file_path(input_path,output_path):
    if isinstance(input_path,list) == True:
        for i in range(0,len(input_path)):
            os.system(join_by(['copy',input_path[i],output_path],separator=' '))
            print(f"\rFile Number {i+1} Copied From {len(input_path)} Total File | {(((i+1)/len(input_path))*100):.2f} %",end=' ')
    elif isinstance(input_path,list) == False:
        os.system(join_by(['copy',input_path,output_path],separator=' '))

def permutation(a,b):
    p = []
    for i in range(0,len(a)):
        for j in range(0,len(b)):
            if np.shape(a[i]) == ():
                c = [a[i]]
            else:
                c = a[i]
            if np.shape(b[j]) == ():
                d = [b[j]]
            else:
                d = b[j]
            p.append(c + d)
    return p

def remove_cover_whitespace(input):
    if input[0] == ' ':
        input = input[1:len(input)]
    if input[-1] == ' ':
        input = input[0:len(input)-1]
    output = copy.deepcopy(input)
    return output

def generate_combinations(lists):
    return (np.array(np.meshgrid(*lists)).T.reshape(-1, len(lists))).tolist()
# Partisan 2


# Partisan 3
# all function in this group depend on nonpartisan group of funtion, imported built-in python function, installed library funtion and on-site function
def scan_format_path(input_path,format='.mseed'):
    temp_path = []
    current_path = [input_path]
    count = 0
    while len(current_path) > 0:
        count = count + 1
        loop_path = scan_subdir(current_path[0])
        if len(scan_subdir(current_path[0])) == 0 and filetype_string(current_path[0],format) == 1:
            temp_path.append(current_path[0])
        for i in range(1,len(current_path)):
            loop_path = concat_list(loop_path,scan_subdir(current_path[i]))
            if len(scan_subdir(current_path[i])) == 0 and filetype_string(current_path[i],format) == 1:
                temp_path.append(current_path[i])
        current_path = copy.deepcopy(loop_path)
    return [fix_double_slashing(temp_path[i]) for i in range(0,len(temp_path))]

def merge_identical_dict(dict1,dict2):
    keys1 = list(dict1.keys())
    keys2 = list(dict2.keys())
    for i in range(0,len(keys1)):
        if keys1[i] != keys2[i]:
            raise Exception("Sorry, your dictionary is not identical in their keys")
    dict_merge = {}
    for i in range(0,len(keys1)):
        dict_merge[keys1[i]] = concat_list(dict1[keys1[i]],dict2[keys1[i]])
    return dict_merge

def check_whitespace(string):
    if remove_whitespace(string)[0] == '\n':
        return True
    else:
        return False

def merge_list(x):
    if len(x) == 1:
        y = x[0]
    elif len(x) == 2:
        y = concat_list(copy.deepcopy(x[0]),copy.deepcopy(x[1]))
    elif len(x) > 2:
        y = concat_list(copy.deepcopy(x[0]),copy.deepcopy(x[1]))
        for i in range(2,len(x)):
            y = concat_list(y,copy.deepcopy(x[i]))
    return y
# Partisan 3