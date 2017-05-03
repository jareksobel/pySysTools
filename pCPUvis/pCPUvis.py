'''
App: pCPUvis - process CPU visualizer
Author: Jarek Sobel (copyright 2017)
URL: www.xenthusiast.com
Version: 0.7
'''

import csv
import json
import datetime
import time
import logging
import sys
import getopt
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.dates as md
from prettytable import PrettyTable

app_version = "0.7"
app_name = "pCPUvis"

# logger objects
logger = logging.getLogger()
formatter = logging.Formatter(fmt = '[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# logging to console
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)

# passing handlers into logging mechanism
logger.addHandler(ch)
logger.setLevel(logging.INFO)


#
# show console progress bar
#

def progress(count, total, suffix=''):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', suffix))
    sys.stdout.flush()

#
# print progam info
#

def print_progam_info():
    print('')
    print('%s v%s - parse and visualize processes CPU usage' % (app_name, app_version))
    print('Copyright (c) 2017, Jarek Sobel')
    print('URL: www.xenthusiast.com')

#
# print help
#

def print_help():
    print_progam_info()
    print('')
    print('usage: %s -i <input_file> -c <cores> [-n -o <output_file> -p <picture_file> -t <picture_title> -s(how) -d(etails) -v(erbose)]' % app_name)
    print('')
    print('   -h                    print this help')
    print('   -i <input_file>       input file to process (CSV format)')
    print('   -c <cores>            number od CPUs/cores on a system')
    print('   -n                    process ID number (after _) instead of next process number (#)')
    print('   -o <output_file>      output file containing processes name and CPU summary utilization')
    print('   -p <picture_file>     output image file name containing graph of proceses CPU utilization (PNG format)')
    print('   -t <picture_title>    image file title (information shows above graph)')
    print('   -s(how)               show image graph interactively')
    print('   -d(etails)            show detailed information including each process individually')
    print('   -v(erbose)            show debug information')

#
# print parsed parameters
#

def print_progra_params(input_file, cores_cnt, numeric_pid, output_file, picture_file, picture_title, show_graph, details, verbose):
    print_progam_info()
    print('')
    print('Program parameters:')
    print('- Input file:   %s' % (input_file))
    print('- Cores count:  %s' % (cores_cnt))

    if numeric_pid:
        print('- Process ID:   true')
    else:
        print('- Process ID:   false')

    if output_file:
        print('- Output file:  %s' % (output_file))
    if picture_file:
        print('- Picture file: %s' % (picture_file))
    if picture_title:
        print('- Title file:   %s' % (picture_title))

    if show_graph:
        print('- Show graph:   true')
    else:
        print('- Show graph:   false')

    if details:
        print('- Details:      true')
    else:
        print('- Details:      false')

    if verbose:
        print('- Verbose:      true')
    else:
        print('- Verbose:      false')

    print('')

    logger.debug('Program parameters:')
    logger.debug('- Input file:   %s' % (input_file))
    logger.debug('- Cores count:  %s' % (cores_cnt))
    logger.debug('- Process ID:  %s' % (numeric_pid))
    logger.debug('- Output file:  %s' % (output_file))
    logger.debug('- Picture file:  %s' % (picture_file))
    logger.debug('- Title file:  %s' % (picture_title))
    logger.debug('- Show graph:  %s' % (show_graph))
    logger.debug('- Details:  %s' % (details))
    logger.debug('- Verbose:  %s' % (verbose))

#
# parse input parameters
#

def parse_params(argv):

    input_file = ''
    cores_cnt = 0
    correct_params = 0

    output_file = ''
    picture_file = ''
    picture_title = ''
    show_graph = 0
    details = 0
    verbose = 0
    numeric_pid = 0

    try:
        opts, args = getopt.getopt(argv, "hi:c:o:p:t:sdvn")
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_help()
            sys.exit()
        elif opt in ("-i"):
            input_file = arg
        elif opt in ("-c"):
            if arg.isnumeric():
                cores_cnt = int(arg)
        elif opt in ("-o"):
            output_file = arg
        elif opt in ("-p"):
            picture_file = arg
        elif opt in ("-t"):
            picture_title = arg
        elif opt in ("-s"):
            show_graph = 1
        elif opt in ("-d"):
            details = 1
        elif opt in ("-v"):
            verbose = 1
        elif opt in ("-n"):
            numeric_pid = 1

    my_file = Path(input_file)
    if my_file.is_file() and cores_cnt > 0:
        correct_params = 1

    if correct_params:

        if verbose:
            # logging to file
            fh = logging.FileHandler("./%s.log" % app_name)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            logger.setLevel(logging.DEBUG)

            logger.debug('===========================================================================================')
            logger.debug('Started program. DEBUG mode ON. App version %s' % app_version)

        print_progra_params(input_file, cores_cnt, numeric_pid, output_file, picture_file, picture_title, show_graph, details, verbose)
        main(input_file, cores_cnt, numeric_pid, output_file, picture_file, picture_title, show_graph, details)
    else:
        print_help()

#
# main program function
#

def main(input_file, cores_cnt, numeric_pid, output_file, picture_file, picture_title, show_graph, details):

    csvRowCnt = -1
    with open(input_file, 'r') as f:
        # TODO: test, if this is correct CSV file
        reader = csv.reader(f)
        csvData = list(reader)

        for rIndex in enumerate(csvData):
            csvRowCnt += 1

    #
    # Process CSV file header
    #

    columns = []
    timeOffset = 0
    validCSVFile = 0

    for hIndex, headCol in enumerate(csvData[0]):

        if hIndex > 0:
            row = headCol.split('\\')

            objOrig = row[3]
            sepPos = objOrig.find('(')
            if sepPos == -1:
                instanceExists = 0
                object = objOrig
                instance = ''
            else:
                instanceExists = 1
                object = objOrig[0:sepPos]
                instance = objOrig[sepPos+1:len(objOrig)-1]

            if numeric_pid:
                sep_pos = instance.rfind('_') # PID process separator
            else:
                sep_pos = instance.rfind('#') # standard process separator

            if (sep_pos == -1) or (sep_pos == 0): # Exclude '_Total'
                groupName = instance
                instanceGroup = 0
            else:
                groupName = instance[0:sep_pos]
                process_numer = instance[sep_pos+1:]
                if process_numer.isdigit():
                    instanceGroup = 1
                else:
                    groupName = instance
                    instanceGroup = 0
                    logger.debug('Found incorrect process name column: %s' % instance)

            columns.append({'instance': instance, 'instanceGroup': instanceGroup, 'groupName': groupName})
        else:
            # TODO: test by () - without replace
            columns.append({'objName': 'datetime'})
            headCol = headCol.replace('(', '_').replace(')', '_').split('_')
            csvValidHeader = headCol[1].strip()
            if csvValidHeader == 'PDH-CSV 4.0':
                validCSVFile = 1
            else:
                logger.debug('Invalid file header: %s' % headCol)

    # DEBUG
    json_debug_dump = json.dumps(columns)
    logger.debug('Columns JSON: %s' % json_debug_dump)

    #
    # Process CSV file data
    #

    globalPerfData = {}
    globalPerfSum = {}

    if validCSVFile == 1:
        logger.debug('- file: "%s" is valid' % input_file)

        perfData = []
        perfSum = []
        rowNumber = 2

        for rIndex, row in enumerate(csvData):
            if rIndex > 1:

                progress(rowNumber, csvRowCnt, 'processing %s/%s row' % (rowNumber, csvRowCnt))
                rowNumber += 1

                perfStats = {}
                perfStatsGroup = {}

                for cIndex, colValue in enumerate(row):

                    if cIndex > 0:

                        instance = columns[cIndex]['instance']
                        instanceGroup = columns[cIndex]['groupName']

                        floatVal = 0.0
                        try:
                            floatVal += float(colValue)
                        except ValueError:
                            logger.debug('Float convert error for instance: %s in row: %s' % (instance, cIndex))

                        floatVal = round(floatVal/cores_cnt, 3)
                        # normalize all values above 100
                        if floatVal > 100:
                            if floatVal > 101:
                                logger.debug('Value over 100. Instance %s, value: %s ' % (instance, floatVal))
                            floatVal = 100

                        perfStats[instance] = floatVal

                        if instanceGroup in perfStatsGroup:
                            perfStatsGroup[instanceGroup] += floatVal
                        else:
                            perfStatsGroup[instanceGroup] = floatVal

                        # global values
                        if instanceGroup in globalPerfData:
                            globalPerfData[instance] += floatVal
                        else:
                            globalPerfData[instance] = floatVal

                        if instanceGroup in globalPerfSum:
                            globalPerfSum[instanceGroup] += floatVal
                        else:
                            globalPerfSum[instanceGroup] = floatVal


                timestring = row[0]
                d = datetime.datetime.strptime(timestring, "%m/%d/%Y %H:%M:%S.%f" )
                #localDateStr = d.strftime("%Y-%m-%d %H:%M:%S")
                localUnixTime = int(time.mktime(d.timetuple()))

                perfData.append({'date': timestring, 'unix': localUnixTime, 'perf': perfStats, 'perfGroup': perfStatsGroup})

        print('')

    # DEBUG
    json_debug_dump = json.dumps(perfData)
    logger.debug('Perf Data JSON: %s' % json_debug_dump)

    #
    # analyze the data and generate charts
    #

    if details:
        # detailed information for each instance process
        newPerfData = globalPerfData.copy()
        newPerfDataWithTotal = globalPerfData.copy()
        perfKey = 'perf'
    else:
        # summary information for all processes instances
        newPerfData = globalPerfSum.copy()
        newPerfDataWithTotal = globalPerfSum.copy()
        perfKey = 'perfGroup'


    del newPerfData['_Total']
    del newPerfData['Idle']
    newPerfData = sorted(newPerfData.items(), key=lambda newPerfData: newPerfData[1], reverse=True)

    # DEBUG
    json_debug_dump = json.dumps(newPerfData)
    logger.debug('Perf Data after modification JSON: %s' % json_debug_dump)


    totalCpu = newPerfDataWithTotal['_Total']

    ptGlobalPerfSum = PrettyTable(["Process name", "% Total CPU Usage"])
    ptGlobalPerfSum.align["Process name"] = "l"
    ptGlobalPerfSum.align["% Total CPU Usage"] = "r"
    ptGlobalPerfSum.padding_width = 1 # One space between column edges and contents (default)

    for key, value in newPerfDataWithTotal.items():
        cpuUtil = round(value * 100 / totalCpu, 3)
        ptGlobalPerfSum.add_row([key, cpuUtil])

    ptOutputString = ptGlobalPerfSum.get_string(sortby="% Total CPU Usage", reversesort=True)
    # show PrettyTable with results
    print(ptOutputString)

    # save PrettyTable TOP processes data to file
    if output_file:
        with open(output_file,'w') as file:
            file.write(ptOutputString)

    globalPerfDataLen = len(globalPerfData) - 2
    globalPerfSumLen = len(newPerfDataWithTotal) - 2

    print("Number of process groups: %s (%s unique processes)" % (globalPerfSumLen, globalPerfDataLen))
    logger.debug("Number of process groups: %s (%s unique processes)" % (globalPerfSumLen, globalPerfDataLen))

    maxProcessesDict = {}
    maxProcessesList = []

    for i in range(5):
        maxProcessesDict[newPerfData[i][0]] = {'sum': 0, 'cnt': 0}
        maxProcessesList.append(newPerfData[i][0])

    logger.debug('TOP processes name: %s' % maxProcessesList)

    #
    # generate graphs
    #

    if show_graph or picture_file:

        valuesX = []
        valuesYDict = {}

        indexX = 1
        otherAvgSum = 0
        otherAvgCnt = 0

        for row in perfData:
            valuesX.append(datetime.datetime.fromtimestamp(int(row['unix'])))

            for procIndex in maxProcessesList:

                if int(round(row[perfKey][procIndex])) > 100:
                    vNorm = 100
                else:
                    vNorm = int(round(row[perfKey][procIndex]))

                if procIndex in valuesYDict:
                    valuesYDict[procIndex].append(vNorm)
                else:
                    valuesYDict[procIndex] = [vNorm]

                maxProcessesDict[procIndex]['sum'] += vNorm
                maxProcessesDict[procIndex]['cnt'] += 1

            other = 0

            for kSubProc, vSubProc in row[perfKey].items():
                if kSubProc != '_Total' and kSubProc != 'Idle' and kSubProc not in  maxProcessesList:
                    other += vSubProc

            if int(round(other)) > 100:
                other = 100
            else:
                other = int(round(other))

            if '_Other' in valuesYDict:
                valuesYDict['_Other'].append(other)
            else:
                valuesYDict['_Other'] = [other]

            otherAvgSum += other
            otherAvgCnt += 1

            indexX += 1


        logger.debug('TOP processes details: %s' % maxProcessesDict)

        valuesY = []
        label_list = []

        for procIndex in maxProcessesList:
            valuesY.append(valuesYDict[procIndex])
            procAvg = round(maxProcessesDict[procIndex]['sum'] / maxProcessesDict[procIndex]['cnt'], 1)
            label_list.append(procIndex + ': ' + str(procAvg) + '%')

        valuesY.append(valuesYDict['_Other'])
        otherAvg = round(otherAvgSum / otherAvgCnt, 1)
        label_list.append('Other' + ': ' + str(otherAvg) + '%')

        fig, ax = plt.subplots(figsize=(15,5), dpi=100)
        plt.tight_layout()

        stack_coll = ax.stackplot(valuesX, valuesY)

        xfmt = md.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(xfmt)
        plt.xticks(rotation=15)
        plt.rc("font", size=10)
        ax.set_title(picture_title)

        # set the ylim
        ax.set_ylim([0,100])
        # make proxy artists
        proxy_rects = [Rectangle((0, 0), 1, 1, fc=pc.get_facecolor()[0]) for pc in stack_coll]
        # make the legend
        ax.legend(proxy_rects, label_list)
        # re-draw the canvas
        plt.draw()

        if show_graph:
            plt.show()

        if picture_file:
            fig.savefig(picture_file, dpi=100, format='png')

#
# execute main program function
#

if __name__ == "__main__":
    parse_params(sys.argv[1:])
