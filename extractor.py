"""
GoPro Highlight Parser:  https://github.com/icegoogles/GoPro-Highlight-Parser

The code for extracting the mp4 boxes/atoms is from 'Human Analog' (https://www.kaggle.com/humananalog): 
https://www.kaggle.com/humananalog/examine-mp4-files-with-python-only

"""

import os, sys
import struct
import numpy as np
from math import floor
import subprocess
import shlex

def find_boxes(f, start_offset=0, end_offset=float("inf")):
    """Returns a dictionary of all the data boxes and their absolute starting
    and ending offsets inside the mp4 file.

    Specify a start_offset and end_offset to read sub-boxes.
    """
    s = struct.Struct("> I 4s") 
    boxes = {}
    offset = start_offset
    f.seek(offset, 0)
    while offset < end_offset:
        data = f.read(8)               # read box header
        if data == b"": break          # EOF
        length, text = s.unpack(data)
        f.seek(length - 8, 1)          # skip to next box
        boxes[text] = (offset, offset + length)
        offset += length
    return boxes

def examine_mp4(filename):
        
    with open(filename, "rb") as f:
        boxes = find_boxes(f)

        # Sanity check that this really is a movie file.
        def fileerror():  # function to call if file is not a movie file
            print("")
            print("ERROR, file is not a mp4-video-file!")

            os.system("pause")
            exit()

        try:
            if boxes[b"ftyp"][0] != 0:
                fileerror()
        except:
            fileerror()


        moov_boxes = find_boxes(f, boxes[b"moov"][0] + 8, boxes[b"moov"][1])
       
        udta_boxes = find_boxes(f, moov_boxes[b"udta"][0] + 8, moov_boxes[b"udta"][1])

        if b'GPMF' in udta_boxes.keys():
            ### get GPMF Box
            highlights = parse_highlights(f, udta_boxes[b'GPMF'][0] + 8, udta_boxes[b'GPMF'][1])
        else:
            # parsing for versions before Hero6
            highlights = parse_highlights_old_version(f, udta_boxes[b'HMMT'][0] + 12, udta_boxes[b'HMMT'][1])
        

        print("")
        print("Filename:", filename)
        print("Found", len(highlights), "Highlight(s)!")
        print('The following heighlights will be extracted: ', highlights)

        return highlights

def parse_highlights_old_version(f, start_offset=0, end_offset=float("inf")):
    listOfHighlights = []

    offset = start_offset
    f.seek(offset, 0)

    while True:
        data = f.read(4)

        timestamp = int.from_bytes(data, "big")

        if timestamp != 0:
            listOfHighlights.append(timestamp)
        else:
            break

    return np.array(listOfHighlights)/1000  # convert to seconds and return

def parse_highlights(f, start_offset=0, end_offset=float("inf")):

    inHighlights = False
    inHLMT = False
    skipFirstMANL = True

    listOfHighlights = []

    offset = start_offset
    f.seek(offset, 0)

    def read_highlight_and_append(f, list):
        data = f.read(4)
        timestamp = int.from_bytes(data, "big")

        if timestamp != 0:
            list.append(timestamp)

    while offset < end_offset:
        data = f.read(4)               # read box header
        if data == b"": break          # EOF

        if data == b'High' and inHighlights == False:
            data = f.read(4)
            if data == b'ligh':
                inHighlights = True  # set flag, that highlights were reached

        if data == b'HLMT' and inHighlights == True and inHLMT == False:
            inHLMT = True  # set flag that HLMT was reached

        if data == b'MANL' and inHighlights == True and inHLMT == True:

            currPos = f.tell()  # remember current pointer/position
            f.seek(currPos - 20)  # go back to highlight timestamp

            data = f.read(4)  # readout highlight
            timestamp = int.from_bytes(data, "big")  #convert to integer

            if timestamp != 0:
                listOfHighlights.append(timestamp)  # append to highlightlist

            f.seek(currPos)  # go forward again (to the saved position)


    return np.array(listOfHighlights)/1000  # convert to seconds and return

def sec2dtime(secs):
    """converts seconds to datetimeformat"""
    milsec = (secs - floor(secs)) * 1000
    secs = secs % (24 * 3600) 
    hour = secs // 3600
    secs %= 3600
    min = secs // 60
    secs %= 60
      
    return "%d:%02d:%02d.%03d" % (hour, min, secs, milsec) 

# Main
# CLI args must be in the following order
# input_dir output_dir clip_length

if __name__ == '__main__':

    inputDir = "/var/in"
    outputDir = "/var/out"
    clipLength = int(os.environ['SPAN'])

    fNames = os.listdir(inputDir)
    
    for fName in fNames:  
        
        if not fName.endswith(".MP4"):
            continue

        print("Processing: " + fName)

        highlights = examine_mp4(os.path.join(inputDir, fName))
        highlights.sort()

        for i, highl in enumerate(highlights):
            command = "ffmpeg -ss " + sec2dtime(highl - clipLength) + " -to " + sec2dtime(highl) + " -i " + os.path.join(inputDir, fName) + " -vcodec libx265 -crf 28 " + os.path.join(outputDir, fName + "_" + str(i + 1) + ".mp4")
            print(command)
            print("Extracting: " + str(i + 1))
            os.system(command)
