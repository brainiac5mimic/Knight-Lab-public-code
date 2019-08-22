# ----------------------------------------------------------------------------
#
# by Mark Holton
#
# ----------------------------------------------------------------------------

import time

import pandas as pd

from qiime2 import Metadata
from qiime2.plugins.metadata.visualizers import tabulate

class Stable_Marriage:

    def orderDict(self, verbose, dictionary, value_frequency):
        '''
        orders the elements of each array that is associated with a sample
            key by how often they get matched to other samples least to
            greatest. Ties are sorted alphanumbericly

        Parameters
        ----------
        verbose: boolean
            Tells function if it should output print statements or not. True
                outputs print statements.

        dictionary: dictionary
            keys are linked to arrays that contain strings that correspond to
                samples that match to the sample the key represents

        value_frequency: dictionary
            keys are samples found in arrays of dictionary. Elements are
                numerical representation of how many samples element
                matches to

        Returns
        -------
        dictionary: dictionary
            dictionary with elements of the arrays that correspond to keys
                ordered from least to greatest abundance
        '''
        for k in dictionary:
            dictionary[k] = sorted(dictionary[k])
            dictionary[k] = sorted(dictionary[k],
                key=lambda x:value_frequency[x])
        '''
        if verbose:
            print("Ordered dictionary is %s"%(dictionary))
        '''
        return dictionary

    def order_keys(self, verbose, dictionary):
        '''
        orders the keys of a dictionary so that they can be used properly as
            the freemen of stable marriage. In order greatest to least number
            of entries since pop is used to get least freeman and pop takes
            the right most entry.

        Parameters
        ----------
        verbose: boolean
            Tells function if it should output print statements or not. True
            outputs print statements.

        dictionary
            dictionary of cases or controls with their matching controls or
                cases ordered by rising abundance

        Return
        ------
        keys_greatest_to_least: list
            contains keys in order of greatest to least amount of samples they
                match to
        '''
        keys_greatest_to_least = sorted(dictionary,
            key=lambda x: len(dictionary[x]), reverse=True)
        '''
        if verbose:
            print("Ordered samples are %s"%(keys_greatest_to_least))
        '''
        return keys_greatest_to_least

    def stableMarriageRunner(self, verbose, case_dictionary,
        pref_counts_control, pref_counts_case):
        '''
        based on code shown by Tyler Moore in his slides for Lecture 2 for
            CSE 3353, SMU, Dallas, TX these slides can be found at
            https://tylermoore.ens.utulsa.edu/courses/cse3353/slides/l02-handout.pdf

        Gets back the best way to match samples to eachother to in a one to
            one manner. Best way refers to getting back the most amount of
            one to one matches.

        Parameters
        ----------
        verbose: boolean
            Tells function if it should output print statements or not. True
                outputs print statements.

        case_dictionary: dictionary
            case_dictionary is a dictionary of cases with their matching
                controls

        pref_counts_control: dictionary
            pref_counts_control is a dictionary with the frequency each control
                sample matches to something in control_dictionary. How many case
                samples each control sample matches to.

        pref_counts_case: dictionary
            pref_counts_case is a dictionary with the frequency each case sample
                matches to something in case_dictionary

        Returns
        -------
        one_to_one_match_dictionary: dictionary
            dictionary with keys representing control samples and their
                corresponding values representing a match between a case and
                control sample
        '''
        #orders control samples (elements) by rising abundance of how many
            #case samples they match to
        case_dictionary = self.orderDict(verbose, case_dictionary,
            pref_counts_control)
        #first make master copy
        master_copy_of_case_dict = case_dictionary.copy()
        free_keys = self.order_keys(verbose, case_dictionary)

        one_to_one_match_dictionary = {}
        while free_keys:
            key = free_keys.pop()
            '''
            if verbose:
                print("Popped the key %s"%(key))
            '''
            if case_dictionary[key] == []:
                continue
            #get the highest ranked control that has not yet been proposed to
            entry = case_dictionary[key].pop()

            if entry not in one_to_one_match_dictionary:
                one_to_one_match_dictionary[entry] = key
                #remove key to reorder but this my not be the best if a switch
                    #is needed later
                if case_dictionary[key] == []:
                    case_dictionary.pop(key, None)
                for case_key in case_dictionary:
                    if entry in case_dictionary[case_key]:
                        case_dictionary[case_key].remove(entry)
                #reorder keys
                free_keys = self.order_keys(verbose, case_dictionary)
                for control in one_to_one_match_dictionary:
                    if one_to_one_match_dictionary[control] in free_keys:
                        free_keys.remove(one_to_one_match_dictionary[control])

            else:
                key_in_use = one_to_one_match_dictionary[entry]
                if pref_counts_case[key] < pref_counts_case[key_in_use]:
                    one_to_one_match_dictionary[entry] = key
                    free_keys.append(key_in_use)
                else:
                    free_keys.append(key)

        '''
        if verbose:
            print("Dictionary of matches after solving stable marriage problem "
                "is %s"%(one_to_one_match_dictionary))
        '''
        return one_to_one_match_dictionary




def get_user_input_query_lines(verbose, dictofFiles):
    '''
    Uses a dictionary of files path/names(dictofFiles) to create a new
        dictionary (dict_of_file_lines) of arrays that represent the lines of
        each file from the origianal input dictionary (dictofFiles)

    Parameters
    ----------
    verbose: boolean
        Tells function if it should output print statements or not. True
            outputs print statements.

    dictofFiles: dictionary of strings
        Each key is what the string is for like metadata being the input
            metadata file. The element of the each key is a file path/name

    Returns
    -------
    dict_of_file_lines: dictionary of arrays of strings
        The dictionary has the keys that have some value in dictofFiles. The
            elements are an array of the lines of the file the key corrisponds
            to.

    Raises
    ------
    ValueError
        If a metadata file can't be loaded into a metadata object
        If a file can't be opened and have each of its lines read into the
            dictionary of input files

    '''
    dict_of_file_lines = {}
    for key in dictofFiles:
        if dictofFiles[key] is None:
            continue
        if key == "metadata":
            if isinstance(dictofFiles[key], str):
                #read metadata file into metadata object
                if verbose:
                    print("metadata file path entered is %s"%(dictofFiles[key]))
                dict_of_file_lines[key] = Metadata.load(dictofFiles[key])
            else:
                dict_of_file_lines[key] = dictofFiles[key]
            
        else:
            if verbose:
                    print("file path entered is %s"%(dictofFiles[key]))
            try:
                dict_of_file_lines[key] = open("./%s"%(dictofFiles[key]),
                    "r").read().splitlines()
            except:
                raise ValueError("File could not be opened")

    return dict_of_file_lines


def keep_samples(verbose, original_MD, keep_query_lines):
    '''
    Filters out unwanted rows based on values in chosen columns detailed in
        keep_query_lines.

    Parameters
    ----------
    verbose: boolean
        Tells function if it should output print statements or not. True
            outputs print statements.

    original_MD : Metadata object
        Metadata object with all samples

    keep_query_lines : array of strings
        list of strings that are the lines of the file
        each string is a sqlite query that determines what ids to keep

    Returns
    -------
    shrunk_MD : Metadata object
        original_MD input except that desired exclution has been applied so
            only the samples that match the input querys are kept

    Raises
    ------
    ValueError
        If the input keep file of sql commands is empty
    '''

    if len(keep_query_lines) < 1:
        raise ValueError("The keep query file is empty")
    shrunk_MD = original_MD
    if verbose:
        print("size of original MetaData Object = %s"
            %(shrunk_MD.id_count))
    for line in keep_query_lines:
        initial_size = shrunk_MD.id_count
        ids = shrunk_MD.get_ids(line)
        shrunk_MD = shrunk_MD.filter_ids(ids)
        if verbose:
            print(line)
            print("\tfiltered out %s samples"%(initial_size-shrunk_MD.id_count))    
    if verbose:
        print("size of filtered MetaData Object = %s"
            %(shrunk_MD.id_count))
        print("kept %s samples"%(shrunk_MD.id_count))


    return shrunk_MD


def determine_cases_and_controls(verbose, afterExclusion_MD, query_line_dict):
    '''
    Determines what samples are cases or controls using the queries in
        query_line_array. The labels of each sample are stored in
        case_controlDF

    Parameters
    ----------
    verbose: boolean
        Tells function if it should output print statements or not. True
            outputs print statements.

    afterExclusion_MD : Metadata object
        Metadata object with unwanted samples filtered out

    query_line_array : array of arrays of strings
        there are two sub arrays
        the first array are made of queries to determine controls
        the second array are made of queries to determine cases

    Returns
    -------
    mergedMD : Metadata object
        Metadata object with unwanted samples filtered out and a case_control
            column that reflects if the index is a case, control, or Undefined
    Raises
    ------
    ValueError
        If the input file of sql commands for determining case and controls is
            empty
    '''

    ids = afterExclusion_MD.get_ids()
    case_control_Series = pd.Series(["Unspecified"] * len(ids), ids)
    case_control_Series.index.name = afterExclusion_MD.id_header
    case_controlDF = case_control_Series.to_frame("case_control")

    if verbose:
        print("Metadata Object has %s samples"%(afterExclusion_MD.id_count))

    for key in query_line_dict:
        if key != "case" and key != "control":
            if verbose:
                print("Wrong key used for query. Must be 'case' or 'control'.")
            continue
        #resets shrunk_MD so that filtering down to control samples does not
            #influence filtering down to case
        shrunk_MD = afterExclusion_MD
        #get query and filtering down to control or case samples based on key
        query_lines = query_line_dict[key]
        if len(query_lines) < 1:
            raise ValueError("The %s query file is empty"%(key))
            
        for line in query_lines:
            initial_size = shrunk_MD.id_count
            ids = shrunk_MD.get_ids(line)
            shrunk_MD = shrunk_MD.filter_ids(ids)
            if verbose:
                print(line)
                print("\tFilters down number of potental %s samples to %s"%(key, initial_size-shrunk_MD.id_count)) 
            
        if verbose:
            print("Final number of %s samples is %s"%(shrunk_MD.id_count,key))
        #replaces the true values created by the loop above to case or control
        ids = shrunk_MD.ids
        case_controlDF.loc[ids, "case_control"] = key

    #turns case_controlDF into a metadata object
    case_controlMD = Metadata(case_controlDF)
    #merges afterExclution_MD and case_controlMD into one new metadata object
    mergedMD = Metadata.merge(afterExclusion_MD, case_controlMD)

    return mergedMD

def filter_prep_for_matchMD(verbose, merged_MD, match_condition_lines,
    null_value_lines):
    '''
    filters out samples that do not have valid entries (null values) for
        columns that determine matching

    Parameters
    ----------
    verbose: boolean
        Tells function if it should output print statements or not. True
            outputs print statements.

    merged_MD : Metadata object
        has case_control with correct labels but some samples might not have
            all matching information

    match_condition_lines : array of strings
        contains conditons to match samples on. In this function it is used
            only to get the columns for matching.

    null_value_lines : array of strings
        contains strings that corrrespond to the null values in the dataset
            that is being analysed

    Returns
    -------
    returned_MD : Metadata object
        Samples that do not have valid entries for columns that determine
            matching are removed. Everything else is the same as merged_MD.

    Raises
    ------
    KeyError
        match_condition_lines tells the program to match based on a column
            that does not exist in the metadata
    '''
    returned_MD = merged_MD
    if verbose:
        totalNumOfSamples = returned_MD.id_count
        print("%s samples before filtered out null samples"
              %(returned_MD.id_count))
    if len(null_value_lines) == 0:
        if verbose:
            print("No null values given so no samples were filtered out")
        return returned_MD
    for condition in match_condition_lines:
        column = condition.split("\t")[1].strip()
        try:
            returned_MD.get_column(column)
        except:
            raise KeyError("Column %s not found in your input data. "
                         "Correct this error in your --match file"
                             %(column))

        #Get the ids of samples in the metadata object that have non null
            #values for every column used for matching

        ids = returned_MD.get_ids(column + " NOT IN " + null_value_lines[0])

        #shrinks the MD so that future ids do not include samples that fail
            #past queries
        returned_MD = returned_MD.filter_ids(ids)

    if verbose:
        print("%s samples filtered out due to null samples"
              %(totalNumOfSamples - returned_MD.id_count))
        print("%s samples after filtering out null samples"
              %(returned_MD.id_count))
        print("%s case samples after filtering out null samples"
              %(len(returned_MD.get_ids("'case_control' IN ('case')"))))
        print("%s control samples after filtering out null samples"
              %(len(returned_MD.get_ids("'case_control' IN ('control')"))))

    return returned_MD


def matcher(verbose, prepped_for_match_MD, conditions_for_match_lines,
          one_to_one, only_matches):
    '''
    matches case samples to controls and puts the case's id in column matched
        to on the control sample's row

    Parameters
    ----------
    verbose: boolean
        Tells function if it should output print statements or not. True
            outputs print statements.

    prepped_for_match_MD : Metadata object
        Samples that do not have valid entries for columns that determine
            matching are removed. Everything else is the same as merged_MD.

    conditions_for_match_lines : array of strings
        contains information on what conditions must be met to constitue a
            match

    one_to_one: boolean
        determines if match does one to one matching using stable marriage

    only_matches: boolean
        determines if the returned metadata object should only include
            samples with matches

    Returns
    -------
    matchedMD : Metadata object
        Metadata based of the samples in prepped_for_match_MD with
            matches represented by a column called matched to. Values
            in matched to are the sample ids of the sample samples
            matches to

    Raises
    ------
    KeyError
        conditions_for_match_lines tells the program to match based on a
            column that does not exist in the metadata
        conditions_for_match_lines has a range value that can not be converted
            to a float
        For one of the columns that conditions_for_match_lines tells to match
            on using a range a control or case sample in prepped_for_match_MD
            has a value that can not be converted into a float

    '''
    case_dictionary = {}
    control_dictionary = {}
    control_match_count_dictionary = {}
    case_match_count_dictionary = {}

    matchDF = prepped_for_match_MD.to_dataframe()
    case_for_matchDF = matchDF[matchDF["case_control"].isin(["case"])]
    # creates column to show matches. since it will contain the sample number
        #it was matched too the null value will be 0
    matchDF["matched_to"] = 'none'

    # loops though case samples and matches them to controls
    for case_index, case_row in case_for_matchDF.iterrows():
        #set matchDF to be only the samples of masterDF that are control samples
        controlDF = matchDF[matchDF["case_control"].isin(["control"])]
        if controlDF.size == 0:
            return Metadata(matchDF)

        # loop though input columns to determine matches
        for conditions in conditions_for_match_lines:

            column_name = conditions.split("\t")[1].strip()
            try:
                matchDF[column_name]
            except:
                raise KeyError("Column %s not found in your input data. "
                               "Correct this error in your --match file"
                               %(column_name))

            # get the type of data for the given column. This determine how a
                #match is determined
            if conditions.split("\t")[0] == "range":
                num = conditions.split("\t")[2].strip()

                try:
                    row_num = float(case_row[column_name])
                except:
                    raise ValueError("column %s contains a string that can "
                                     "not be converted to a numerical value"
                                     %(column_name))
                try:
                    fnum = float(num)
                except:
                    raise ValueError("input number for condition %s is not a "
                                     "valid number"%(column_name))
                try:
                    nums_in_column = pd.to_numeric(controlDF[column_name])
                except:
                    raise ValueError("column %s contains a string that can "
                                     "not be converted to a numerical value"
                                     %(column_name))

                # filters controls based on if the value in the control is not
                    #within a given distance form the case
                controlDF = controlDF[(nums_in_column >= (row_num - fnum))
                                      & (nums_in_column <= (row_num + fnum))]
            else:
                # filters controls if the strings for the control and case
                    #don't match
                controlDF = controlDF[controlDF[column_name].isin(
                    [case_row[column_name]])]
        if controlDF.index.values.size > 0:
            case_dictionary.update({case_index:controlDF.index.values})
            case_match_count_dictionary.update(
                {case_index:(controlDF.index.values.size)})

        for id_control in controlDF.index:
            if id_control not in control_match_count_dictionary:
                control_match_count_dictionary.update({id_control:0})
            control_match_count_dictionary.update(
                {id_control:(control_match_count_dictionary[id_control]+1)})

    '''
    if verbose:
        print("case_dictionary is %s"
              %(case_dictionary))
        print("control_match_count_dictionary is %s"
              %(control_match_count_dictionary))
        print("case_match_count_dictionary is %s"
              %(case_match_count_dictionary))
    '''
    
    if one_to_one:
        stable = Stable_Marriage()
        case_to_control_match = stable.stableMarriageRunner(verbose,
            case_dictionary, control_match_count_dictionary,
            case_match_count_dictionary)

        if verbose:
            print("%s sample pairs matched together"%(
                len(case_to_control_match.keys())))

        for key in case_to_control_match:
            key_value = case_to_control_match[key]
            matchDF.at[key, "matched_to"] = str(key_value)
            matchDF.at[key_value, "matched_to"] = str(key)
    else:
        if verbose:
            print("%s cases matched"%(
                len(case_dictionary.keys())))
        for case in case_dictionary:
            for control in case_dictionary[case]:
                if control in control_dictionary:
                    control_dictionary[control].append(case)
                else:
                    control_dictionary[control] = [case]
            matchDF.at[case, "matched_to"] = ", ".join(
                sorted(case_dictionary[case]))
    
        for control in control_dictionary:
            matchDF.at[control, "matched_to"] = ", ".join(
                sorted(control_dictionary[control]))
    
    
    
    matchedMD = Metadata(matchDF)
    if only_matches:
        ids = matchedMD.get_ids("matched_to NOT IN ('none')")
        #shrinks the MD to only have matched samples
        matchedMD = matchedMD.filter_ids(ids)
    '''
    if verbose:
        print("matched_to column")
        print(matchedMD.to_dataframe()["matched_to"])
    '''
    return matchedMD


def mainControler(verbose, output, metadata, keep, control, case,
    nullvalues, match, one, only_matches, unit, stand):
    '''
    Parameters
    ----------
    verbose: boolean
        Tells function if it should output print statements or not.
            True outputs print statements.
    metadata: string
        Name of file with sample metadata to analyze.
    keep: string
        name of file with sqlite lines used to determine what samples to
            exclude or keep
    control: string
        name of file with sqlite lines used to determine what samples to
            label control
    case: string
        name of file with sqlite lines used to determine what samples to
            label case
    nullvalues: string
        name of file with strings that represent null values so that
            samples where one of these null values are in a category
            that is used to determine matches are filtered out
    match: string
        name of file which contains information on what conditions
            must be met to constitue a match
    one: boolean
        When given as a parameter match_samples will do one to
             one matching instead of all matches
    only_matches: boolean
        When given as a parameter match_samples will filter out
            non-matched samples from output file
    unit: boolean
        When given as a parameter will print out statements used
            for unit tests of the mainControler function. These
            statements indicate what the program is doing.
    output: string
        File location for visualization of metadata to be outputted to. 
    stand: boolean
        If True then fuctions returns metadata object. This is used 
            when running in a qiime2 enviroment but not as a plugin.

    Returns
    -------
    Metadata object that contains the filtered, labeled, and or matched
        samples

    '''
    
    tstart = time.clock()
    inputDict = {"metadata":metadata, "keep":keep, "control":control,
        "case":case, "nullvalues":nullvalues, "match":match}
    #loads and opens input files
    inputDict = get_user_input_query_lines(verbose, inputDict)
    if verbose:
        print("The file parameters found are")
        print(", ".join(inputDict.keys()))
        tloadedFiles = time.clock()
        print("Time to load input files is %s"%(tloadedFiles - tstart))
    if "keep" in inputDict:
        if verbose or unit:
            print("Calling keep_samples")
        afterExclusionMD = keep_samples(verbose, inputDict["metadata"],
            inputDict["keep"])

        if verbose:
            tkeep = time.clock()
            print("Time to filter out unwanted samples is %s"
                  %(tkeep - tloadedFiles))
    else:
        if verbose or unit:
            print("Skipped keep_samples")
        if verbose:
            tkeep = tloadedFiles
        afterExclusionMD = inputDict["metadata"]


    if "case" in inputDict and "control" in inputDict:
        if verbose or unit:
            print("Calling determine_cases_and_controls")
        case_control_dict = {"case":inputDict["case"],
            "control":inputDict["control"]}

        case_controlMD = determine_cases_and_controls(verbose,
            afterExclusionMD, case_control_dict)

        if verbose:
            tcase_control = time.clock()
            print("Time to label case and control samples is %s"
                  %(tcase_control - tkeep))
    else:
        if verbose or unit:
            print("Skipped determine_cases_and_controls and returning the "
                  "metadata")
        if verbose:
            tend = time.clock()
            print("Time to do everything %s"%(tend - tstart))
        if stand:
            return afterExclusionMD
        return tabulate(afterExclusionMD)


    if "nullvalues" in inputDict:
        if "match" in inputDict:
            if verbose or unit:
                print("Calling filter_prep_for_matchMD")
            prepped_for_matchMD= filter_prep_for_matchMD(verbose,
                case_controlMD, inputDict["match"], inputDict["nullvalues"])

            if verbose:
                tprepped = time.clock()
                print("Time to filter Metadata information for samples "
                      "with null values is %s"%(tprepped - tcase_control))
        else:
            if verbose or unit:
                print("--nullvalues was given but --match was not so returning "
                      "current metadata withouth null filtering")
            if verbose:
                tend = time.clock()
                print("Time to do everything %s"%(tend - tstart))
            if stand:
                return case_controlMD
            return tabulate(case_controlMD)
    else:
        if verbose or unit:
                print("Skipped filter_prep_for_matchMD")
        prepped_for_matchMD = case_controlMD
        if verbose:
            tprepped = tcase_control


    if "match" in inputDict:
        if verbose or unit:
                print("Calling matcher")
        matchedMD = matcher(verbose, prepped_for_matchMD,
                            inputDict["match"], one, only_matches)
        if verbose:
            tmatch = time.clock()
            tend = time.clock()
            print("Time to match is %s"%(tmatch- tprepped))
            print("Time to do everything %s"%(tend - tstart))
        if verbose or unit:
            print("Returning metadata")
        if stand:
            return matchedMD
        return tabulate(matchedMD)
    else:
        if verbose or unit:
                print("Skipping matcher and returning metadata")
        if verbose:
            tend = time.clock()
            print("Time to do everything %s"%(tend - tstart))
        if stand:
            return prepped_for_matchMD
        return tabulate(prepped_for_matchMD)


    if verbose or unit:
        print("Ended program without returning metadata")



