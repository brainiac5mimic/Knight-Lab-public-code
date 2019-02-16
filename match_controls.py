'''
Created on Jun 24, 2018

@author: Mark Holton
'''

import getopt, sys
import pandas as pd
import numpy as np
import qiime2
import time
import click

from qiime2 import Metadata
from collections import defaultdict


def get_user_input_query_lines(user_input_file_of_queries,input_catagory):
    '''
    converts user_input_file_of_queries file into a list of strings that represent the lines of the file

    Parameters
    ----------
    user_input_file_of_queries : string
        file that contains lines of stings

    Returns
    -------
     if user_input_file_of_queries is not ''
        list of strings that are the lines of the file
     if user_input_file_of_queries is ''
         returns False boolean
    '''
    if user_input_file_of_queries == '':
        if verbose:
            print('null query entered for %s'%(input_catagory))
        return False
    try:
        lines = open('./%s'%(user_input_file_of_queries),'r').readlines()
    except:
        if verbose:
            print('No samples fulfill keep queries. Exited while filtering out unwanted samples')
        return False
    return lines

def keep_samples(original_MD, keep_query_lines):
    '''
    Filters out unwanted rows based on values in chosen columns.

    Parameters
    ----------
    original_MD : Metadata object
        Metadata object with all samples

    keep_query_lines : array of strings
        list of strings that are the lines of the file
        each string is a sqlite query that determines what ids to keep

    Returns
    -------
    shrunk_MD : Metadata object
        original_MD input except that desired exclution has been applied so only the samples that match the input querys
        are kept
    '''
    shrunk_MD = original_MD
    try:
        shrunk_MD = shrunk_MD.filter_ids(shrunk_MD.get_ids(' AND '.join(keep_query_lines)))
    except:
        print('No samples fulfill keep queries. Exited while filtering out unwanted samples')
        return
    return shrunk_MD

def determine_cases_and_controls(afterExclusion_MD, query_line_dict, case_controlDF):
    '''
    Determines what samples are cases or controls using the queries in query_line_array. The labels of each sample are
    stored in case_controlDF

    Parameters
    ----------
    afterExclusion_MD : Metadata object
        Metadata object with unwanted samples filtered out

    query_line_array : array of arrays of strings
        there are two sub arrays
        the first array are made of queries to determine controls
        the second array are made of queries to determine cases

    case_controlDF : dataframe
        dataframe with one column named case_control. The indexs are the same as the indexs of afterExclution_MD
        all values are Undefined to start

    Returns
    -------
    mergedMD : Metadata object
        Metadata object with unwanted samples filtered out and a case_control column that reflects if the index is
        a case, control, or Undefined
    '''
    afterExclusion_MD_full = afterExclusion_MD

    for key in query_line_dict:
        if key != 'case' and key != 'control':
            print("Wrong keys used for query. Must be 'case' or 'control'.")
            continue
        #resets shrunk_MD so that filtering down to control samples does not influence filtering down to case
        shrunk_MD = afterExclusion_MD_full
        #get query and filtering down to control or case samples based on key
        query_lines = query_line_dict[key]
        try:
            shrunk_MD = shrunk_MD.filter_ids(shrunk_MD.get_ids(' AND '.join(query_lines)))
        except:
            print('No samples fulfill %s queries. Exited while determining %s samples'%(key, key))
            return

        #replaces the true values created by the loop above to case or control
        ids = shrunk_MD.ids
        case_controlDF.loc[ids,'case_control'] = key

    #turns case_controlDF into a metadata object
    case_controlMD = Metadata(case_controlDF)

    #merges afterExclution_MD and case_controlMD into one new metadata object
    mergedMD = Metadata.merge(afterExclusion_MD, case_controlMD)

    return mergedMD

def filter_prep_for_matchMD(merged_MD, match_condition_lines, null_value_lines):
    '''
    filters out samples that do not have valid entries (null values) for columns that determine matching

    Parameters
    ----------
    merged_MD : Metadata object
        has case_control with correct labels but some samples might not have all matching information

    match_condition_lines : array of strings
        contains conditons to match samples on. In this function it is used only to get the columns for matching.

    null_value_lines : array of strings
        contains strings that corrrespond to the null values in the dataset that is being analysed

    Returns
    -------
    returned_MD : Metadata object
        Samples that do not have valid entries for columns that determine matching are removed. Everything else is the
        same as merged_MD.
    '''
    returned_MD = merged_MD
    for condition in match_condition_lines:
        column = condition.split('\t')[1].strip()
        try:
            returned_MD.get_column(column)
        except:
            #use raise exeption
            print('Column %s not found in your input data. Correct this error in your --match/-m file'%(column))
            return
        #Get the ids of samples in the metadata object that have non null values for every column used for matching
        try:
            ids = returned_MD.get_ids(column + ' NOT IN ' + null_value_lines[0])
        except:
            print('No samples pass null filter queries. Exited while determining non null samples')
            return
        #shrinks the MD so that future ids do not include samples that fail past queries
        returned_MD = returned_MD.filter_ids(ids)

    return returned_MD


#put in class
def orderDict(dictionary, value_frequency):
    '''
    orders the elements of each array that is associated with a sample key by how often they get matched to other samples
    least to greatest. Ties are sorted Alphanumbericly

    Parameters
    dictionary: dictionary
        keys are linked to arrays that contain strings that correspond to samples that match to the
        sample the key represents

    value_frequency: dictionary
        keys are samples found in arrays of dictionary. Elements are numerical representation of
        how many samples element matches to

    Returns
    dictionary: dictionary
        dictionary with elements of the arrays that correspond to keys ordered from least to greatest abundance
    '''
    for k in dictionary:
        dictionary[k] = sorted(dictionary[k])
        dictionary[k] = sorted(dictionary[k], key = lambda x:value_frequency[x] )

    return dictionary

def order_keys(dictionary):
    '''
    orders the keys of a dictionary so that they can be used properly as the freemen of stable marriage. In order greatest to least since pop is used to get least freeman and pop takes the right most entry.

    Parameters
    dictionary
        dictionary of cases or controls with their matching controls or cases ordered
        by rising abundance

    Return
    keys_greatest_to_least: list
        contains keys in order of greatest to least amount of samples they match to
    '''

    keys_greatest_to_least = sorted(dictionary, key=lambda x: len (dictionary[x]), reverse=True)


    return keys_greatest_to_least

def stable_marriage(case_dictionary, pref_counts_case):
    '''
    based on code shown by Tyler Moore in his slides for Lecture 2 for CSE 3353, SMU, Dallas, TX
    these slides can be found at https://tylermoore.ens.utulsa.edu/courses/cse3353/slides/l02-handout.pdf

    Gets back the best way to match samples to eachother to in a one to one manner. Best way refers to getting back the
    most amount of one to one matches.

    Parameters
    dictionary_pref: dictionary
        dictionary_pref is a dictionary of cases with their matching controls ordered by rising abundance

    pref_counts_case: dictionary
        pref_counts is a dictionary with the frequency cases match to something in dictionary_pref

    Returns
    one_to_one_match_dictionary: dictionary
        dictionary with keys representing control samples and their corresponding values representing a match between a case and control sample
    '''

    #first make master copy
    master_copy_of_case_dict = case_dictionary.copy()
    #cut out keys in case_dictionary that have no possible matches


    for key in case_dictionary:
        if len(case_dictionary[key])==0:
            case_dictionary.pop(key,None)

    free_keys = order_keys(case_dictionary)

    one_to_one_match_dictionary = {}
    while free_keys :
        key = free_keys.pop()
        if case_dictionary[key]==[]:
            continue
        #get the highest ranked woman that has not yet been proposed to
        entry = case_dictionary[key].pop()

        if entry not in one_to_one_match_dictionary:
            one_to_one_match_dictionary[entry] = key
            #remove key to reorder but this my not be the best if a switch is needed later
            if case_dictionary[key]==[]:
                case_dictionary.pop(key,None)
            for case_key in case_dictionary:
                if entry in case_dictionary[case_key]:
                    case_dictionary[case_key].remove(entry)
            #reorder keys
            free_keys = order_keys(case_dictionary)

        else:
            key_in_use = one_to_one_match_dictionary[entry]
            if pref_counts_case[key] < pref_counts_case[key_in_use]:
                one_to_one_match_dictionary[entry] = key
                free_keys.append(key_in_use)
            else:
                free_keys.append(key)

    return one_to_one_match_dictionary




def match_samples(prepped_for_match_MD, conditions_for_match_lines):
    '''
    matches case samples to controls and puts the case's id in column matched to on the control sample's row

    Parameters
    ----------
    prepped_for_match_MD : Metadata object
        Samples that do not have valid entries for columns that determine matching are removed. Everything else is the
        same as merged_MD.

    conditions_for_match_lines : dataframe
        contains information on what conditions must be met to constitue a match

    Returns
    -------
    masterDF : dataframe
        masterDF with matches represented by a column called matched to. Values in matched to are the sample ids of the
        sample samples matches to

    '''
    case_dictionary = {}
    control_dictionary = {}
    control_match_count_dictionary = {}
    case_match_count_dictionary = {}

    matchDF = prepped_for_match_MD.to_dataframe()
    case_for_matchDF = matchDF[matchDF['case_control'].isin(['case'])]
    # creates column to show matches. since it will contain the sample number it was matched too the null value will be 0
    matchDF['matched_to'] = '0'

    # loops though case samples and matches them to controls
    for case_index, case_row in case_for_matchDF.iterrows():
        #print('case index is %s'%(case_index))

        # set matchDF to be only the samples of masterDF that are control samples
        controlDF = matchDF[matchDF['case_control'].isin(['control'])]

        # loop though input columns to determine matches
        for conditions in conditions_for_match_lines:

            column_name = conditions.split('\t')[1].strip()

            # get the type of data for the given column. This determine how a match is determined
            if conditions.split('\t')[0] == 'range':
                num = conditions.split('\t')[2].strip()
                try:
                    row_num = float(case_row[column_name])
                except:
                    print('%s is not a a valid number'%(case_row[column_name]))
                    return

                try:
                    fnum = float(num)
                except:
                    print('%s is not a a valid number'%(num))
                    return

                try:
                    nums_in_column = pd.to_numeric(controlDF[column_name])
                except:
                    print('column %s contains a string that can not be converted to a numerical value'%(column_name))
                    sys.exit(2)

                # filters controls based on if the value in the control is not within a given distance form the case
                controlDF = controlDF[
                                    ( nums_in_column >= ( row_num - fnum ) )
                                    &
                                    ( nums_in_column <= ( row_num + fnum ) )
                                    ]
            else:
                # filters controls if the strings for the control and case don't match
                controlDF = controlDF[controlDF[column_name].isin([case_row[column_name]])]

        case_dictionary.update({case_index:controlDF.index.values})

        case_match_count_dictionary.update({case_index:(controlDF.index.values.size)})

        for id_control in controlDF.index:
            if id_control not in control_match_count_dictionary:
                control_match_count_dictionary.update({id_control:0})
            control_match_count_dictionary.update({id_control:(control_match_count_dictionary[id_control]+1)})


    case_dictionary = orderDict(case_dictionary, control_match_count_dictionary)

    case_to_control_match = stable_marriage(case_dictionary, case_match_count_dictionary)


    for key in case_to_control_match:
        key_value = case_to_control_match[key]
        matchDF.loc[ key, 'matched_to'] = key_value
        matchDF.loc[ key_value, 'matched_to'] = key

    return Metadata(matchDF)





'''
format of match
each line is tab seperated
the first element is the type of match: range or exact
    range matches samples if the numerical values compared are with in some other number of eachother
        this is only to be used with numerical values
    exact matches samples if the values compared are exactly the same
        this can be used for strings and numbers
the second element is the column to compare values of for the case and control samples
the third element is the range number if the match type is range
    this determines how far away a sample can be from another sample for the given column to be matched
    there is not third element if the match type is exact
'''

@click.command()
@click.option('--verbose', default=False, type=bool, help='Make print statements appear')
@click.option('--keep', default=1, help='name of file with sqlite lines used to determine what samples to exclude or keep')
@click.option('--control', default=1, help='name of file with sqlite lines used to determine what samples to exclude or keep')
@click.option('--case', default=1, help='Number of greetings.')
@click.option('--nullValues', default=1, help='name of file with sqlite lines used to determine what samples to exclude or keep')
@click.option('--match', default=1, help='name of file with sqlite lines used to determine what samples to exclude or keep')
@click.option('--inputData', required = True, prompt='The name of metadata file with samples is needed', help='Name of file with sample metadata to analyze.')
@click.option('--output', required = True, prompt='The name of file to output data to is needed', help='Name of file to export data to.')




def ExcludeOnly(verbose,inputData,keep,output):
    tstart = time.clock()
    #read metadata file into metadata object
    try:
        originalMD = Metadata.load(inputData)
    except:
        if verbose:
            print('metadata file could not load. If you entered a valid path then try clearing the formating. The file must be a TSV metadata file.')
            print("metadata file path entered is %s"%(inputData))
        return
    #each line is a sqlite query to determine what samples to keep
    keep_query_lines_input = get_user_input_query_lines(keep,"keep")
    tloadedFiles = time.clock()
    if verbose:
        print('time to load input files is %s'%(tloadedFiles - tstart))


    afterExclusionMD = keep_samples(originalMD, keep_query_lines_input)
    afterExclusionMD.to_dataframe().to_csv(output, sep = '\t')

    tkeep = time.clock()
    tend = time.clock()

    if verbose:
        print('time to filter out unwanted samples is %s'%(tkeep - tloadedFiles))
        print('time to do everything %s'%(tend-tstart))




def ControlAndCaseOnly(verbose,inputData,control,case,output):
    tstart = time.clock()
    #read metadata file into metadata object
    try:
        originalMD = Metadata.load(inputData)
    except:
        if verbose:
            print('metadata file could not load. If you entered a valid path then try clearing the formating. The file must be a TSV metadata file.')
            print("metadata file path entered is %s"%(inputData))
        return
    #each line is a sqlite query to determine what samples to label control
    control_query_lines_input = get_user_input_query_lines(control,"control")
    #each line is a sqlite query to determine what samples to label case
    case_query_lines_input = get_user_input_query_lines(case,"case")
    tloadedFiles = time.clock()
    if verbose:
        print('time to load input files is %s'%(tloadedFiles - tstart))
     ids = originalMD.get_ids()
    case_control_Series = pd.Series( ['Unspecified'] * len(ids), ids)
    '''
    ['Unspecified'] * len(ids) creates a list of elements. The list is the
    same length as ids. All the elements are 'Unspecified'
    '''
    case_control_Series.index.name = afterExclusionMD.id_header
    case_controlDF = case_control_Series.to_frame('case_control')
    case_control_dict = {'case':case_query_lines_input, 'control':control_query_lines_input }
    case_controlMD = determine_cases_and_controls(afterExclusionMD, case_control_dict, case_controlDF)

    case_controlMD.to_dataframe().to_csv(outputFileName, sep = '\t')

    tcase_control = time.clock()
    tend = time.clock()
    if verbose:
        print('time to label case and control samples is %s'%(tcase_control - tloadedFiles))
        print('time to do everything %s'%(tend-tstart))



def ControlCaseAndMatch(verbose,inputData,control,case,match,output):
    tstart = time.clock()
    #read metadata file into metadata object
    try:
        originalMD = Metadata.load(inputData)
    except:
        if verbose:
            print('metadata file could not load. If you entered a valid path then try clearing the formating. The file must be a TSV metadata file.')
            print("metadata file path entered is %s"%(inputData))
        return

    #each line is a sqlite query to determine what samples to label control
    control_query_lines_input = get_user_input_query_lines(control,"control")
    #each line is a sqlite query to determine what samples to label case
    case_query_lines_input = get_user_input_query_lines(case,"case")
    match_condition_lines_input = get_user_input_query_lines(match,"match")
    tloadedFiles = time.clock()
    if verbose:
        print('time to load input files is %s'%(tloadedFiles - tstart))

    ids = originalMD.get_ids()
    case_control_Series = pd.Series( ['Unspecified'] * len(ids), ids)
    '''
    ['Unspecified'] * len(ids) creates a list of elements. The list is the
    same length as ids. All the elements are 'Unspecified'
    '''
    case_control_Series.index.name = afterExclusionMD.id_header
    case_controlDF = case_control_Series.to_frame('case_control')
    case_control_dict = {'case':case_query_lines_input, 'control':control_query_lines_input }
    case_controlMD = determine_cases_and_controls(afterExclusionMD, case_control_dict, case_controlDF)


    tcase_control = time.clock()
    if verbose:
        print('time to label case and control samples is %s'%(tcase_control - tloadedFiles))


    matchedMD = match_samples( prepped_for_matchMD, match_condition_lines_input )
    matchedMD.to_dataframe().to_csv(outputFileName, sep = '\t')


    tmatch = time.clock()
    tend = time.clock()
    if verbose:
        print('time to match is %s'%(tmatch- tcase_control))
        print('time to do everything %s'%(tend-tstart))






def ControlCaseNullAndMatch(verbose,inputData,control,case,nullValues,match,output):
    tstart = time.clock()
    #read metadata file into metadata object
    try:
        originalMD = Metadata.load(inputData)
    except:
        if verbose:
            print('metadata file could not load. If you entered a valid path then try clearing the formating. The file must be a TSV metadata file.')
            print("metadata file path entered is %s"%(inputData))
        return
    #each line is a sqlite query to determine what samples to label control
    control_query_lines_input = get_user_input_query_lines(control,"control")
    #each line is a sqlite query to determine what samples to label case
    case_query_lines_input = get_user_input_query_lines(case,"case")
    null_values_lines_input = get_user_input_query_lines(nullValues,"nullValues")
    match_condition_lines_input = get_user_input_query_lines(match,"match")
    tloadedFiles = time.clock()
    if verbose:
        print('time to load input files is %s'%(tloadedFiles - tstart))

    ids = originalMD.get_ids()
    case_control_Series = pd.Series( ['Unspecified'] * len(ids), ids)
    '''
    ['Unspecified'] * len(ids) creates a list of elements. The list is the
    same length as ids. All the elements are 'Unspecified'
    '''
    case_control_Series.index.name = afterExclusionMD.id_header
    case_controlDF = case_control_Series.to_frame('case_control')
    case_control_dict = {'case':case_query_lines_input, 'control':control_query_lines_input }

    case_controlMD = determine_cases_and_controls(afterExclusionMD, case_control_dict, case_controlDF)



    tcase_control = time.clock()
    print('time to label case and control samples is %s'%(tcase_control - tloadedFiles))


    prepped_for_matchMD= filter_prep_for_matchMD(case_controlMD, match_condition_lines_input, null_values_lines_input)


    tprepped = time.clock()
    print('time to filter Metadata information for samples with null values is %s'%(tprepped - tcase_control))



    if match_condition_lines_input != False:
        matchedMD = match_samples( prepped_for_matchMD, match_condition_lines_input )
        matchedMD.to_dataframe().to_csv(outputFileName, sep = '\t')


    tmatch = time.clock()
    tend = time.clock()
    print('time to match is %s'%(tmatch- tprepped))
    print('time to do everything %s'%(tend-tstart))




def ExcludeControlCaseAndMatch(verbose,inputData,keep,control,case,match,output):
    tstart = time.clock()
    #read metadata file into metadata object
    try:
        originalMD = Metadata.load(inputData)
    except:
        if verbose:
            print('metadata file could not load. If you entered a valid path then try clearing the formating. The file must be a TSV metadata file.')
            print("metadata file path entered is %s"%(inputData))
        return

    #each line is a sqlite query to determine what samples to keep
    keep_query_lines_input = get_user_input_query_lines(keep,"keep")
    #each line is a sqlite query to determine what samples to label control
    control_query_lines_input = get_user_input_query_lines(control,"control")
    #each line is a sqlite query to determine what samples to label case
    case_query_lines_input = get_user_input_query_lines(case,"case")
    match_condition_lines_input = get_user_input_query_lines(match,"match")
    tloadedFiles = time.clock()
    if verbose:
        print('time to load input files is %s'%(tloadedFiles - tstart))
    afterExclusionMD = keep_samples(originalMD, keep_query_lines_input)
    tkeep = time.clock()
    if verbose:
        print('time to filter out unwanted samples is %s'%(tkeep - tloadedFiles))
    ids = afterExclusionMD.get_ids()
    case_control_Series = pd.Series( ['Unspecified'] * len(ids), ids)
    '''
    ['Unspecified'] * len(ids) creates a list of elements. The list is the
    same length as ids. All the elements are 'Unspecified'
    '''
    case_control_Series.index.name = afterExclusionMD.id_header
    case_controlDF = case_control_Series.to_frame('case_control')
    case_control_dict = {'case':case_query_lines_input, 'control':control_query_lines_input }

    case_controlMD = determine_cases_and_controls(afterExclusionMD, case_control_dict, case_controlDF)


    tcase_control = time.clock()
    print('time to label case and control samples is %s'%(tcase_control - tkeep))

    if match_condition_lines_input != False:
        matchedMD = match_samples( prepped_for_matchMD, match_condition_lines_input )
        matchedMD.to_dataframe().to_csv(outputFileName, sep = '\t')


    tmatch = time.clock()
    tend = time.clock()
    print('time to match is %s'%(tmatch- tcase_control))
    print('time to do everything %s'%(tend-tstart))



def Everything(verbose,inputData,keep,control,case,nullValues,match,output):
    tstart = time.clock()
    #read metadata file into metadata object
    try:
        originalMD = Metadata.load(inputData)
    except:
        if verbose:
            print('metadata file could not load. If you entered a valid path then try clearing the formating. The file must be a TSV metadata file.')
            print("metadata file path entered is %s"%(inputData))
        return

    #each line is a sqlite query to determine what samples to keep
    keep_query_lines_input = get_user_input_query_lines(keep,"keep")
    #each line is a sqlite query to determine what samples to label control
    control_query_lines_input = get_user_input_query_lines(control,"control")
    #each line is a sqlite query to determine what samples to label case
    case_query_lines_input = get_user_input_query_lines(case,"case")
    null_values_lines_input = get_user_input_query_lines(nullValues,"nullValues")
    match_condition_lines_input = get_user_input_query_lines(match,"match")
    tloadedFiles = time.clock()
    if verbose:
        print('time to load input files is %s'%(tloadedFiles - tstart))
    afterExclusionMD = keep_samples(originalMD, keep_query_lines_input)
    tkeep = time.clock()
    if verbose:
        print('time to filter out unwanted samples is %s'%(tkeep - tloadedFiles))
    ids = afterExclusionMD.get_ids()
    case_control_Series = pd.Series( ['Unspecified'] * len(ids), ids)
    '''
    ['Unspecified'] * len(ids) creates a list of elements. The list is the
    same length as ids. All the elements are 'Unspecified'
    '''
    case_control_Series.index.name = afterExclusionMD.id_header
    case_controlDF = case_control_Series.to_frame('case_control')
    case_control_dict = {'case':case_query_lines_input, 'control':control_query_lines_input }

    case_controlMD = determine_cases_and_controls(afterExclusionMD, case_control_dict, case_controlDF)

    tcase_control = time.clock()
    print('time to label case and control samples is %s'%(tcase_control - tkeep))



    prepped_for_matchMD= filter_prep_for_matchMD(case_controlMD, match_condition_lines_input, null_values_lines_input)


    tprepped = time.clock()
    print('time to filter Metadata information for samples with null values is %s'%(tprepped - tcase_control))

    if match_condition_lines_input != False:
        matchedMD = match_samples( prepped_for_matchMD, match_condition_lines_input )
        matchedMD.to_dataframe().to_csv(outputFileName, sep = '\t')

    tmatch = time.clock()
    tend = time.clock()
    print('time to match is %s'%(tmatch- tprepped))
    print('time to do everything %s'%(tend-tstart))
