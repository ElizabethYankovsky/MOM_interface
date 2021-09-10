#!/usr/bin/env python

""" Convert MARBL diagnostics file to diag_table_MARBL.json

MARBL diagnostics file is a file containing a list of

    DIAGNOSTIC_NAME : frequency_operator[,frequency2frequency2_operator2, ..., frequencyN_operatorN]

MOM uses this same format for defining its ecosystem-based diagnostics to allow
users to change the requested MOM and MARBL diagnostics in the same place.

usage: MARBL_diags_to_diag_table.py [-h] -i ECOSYS_DIAGNOSTICS_IN -t
                                    DIAG_TABLE_OUT [-l LOW_FREQUENCY_STREAM]
                                    [-m MEDIUM_FREQUENCY_STREAM]
                                    [-g HIGH_FREQUENCY_STREAM]
                                    [--lMARBL_output_all LMARBL_OUTPUT_ALL]
                                    [--lMARBL_output_alt_co2 LMARBL_OUTPUT_ALT_CO2]

Generate MOM diag table from MARBL diagnostics

optional arguments:
  -h, --help            show this help message and exit
  -i ECOSYS_DIAGNOSTICS_IN, --ecosys_diagnostics_in ECOSYS_DIAGNOSTICS_IN
                        File generated by MARBL_generate_diagnostics_file
                        (default: None)
  -t DIAG_TABLE_OUT, --diag_table_out DIAG_TABLE_OUT
                        Location of diag table (JSON) file to create (default:
                        None)
  -l LOW_FREQUENCY_STREAM, --low_frequency_stream LOW_FREQUENCY_STREAM
                        Stream to put low frequency output into (required if
                        not lMARBL_output_all) (default: 0)
  -m MEDIUM_FREQUENCY_STREAM, --medium_frequency_stream MEDIUM_FREQUENCY_STREAM
                        Stream to put medium frequency output into (required
                        if not lMARBL_output_all) (default: 0)
  -g HIGH_FREQUENCY_STREAM, --high_frequency_stream HIGH_FREQUENCY_STREAM
                        Stream to put high frequency output into (required if
                        not lMARBL_output_all) (default: 0)
  --lMARBL_output_all LMARBL_OUTPUT_ALL
                        Put all MARBL diagnostics in hm_bgc stream (default:
                        False)
  --lMARBL_output_alt_co2 LMARBL_OUTPUT_ALT_CO2
                        Include ALT_CO2 diagnostics in streams (default:
                        False)
"""

#######################################

class DiagTableClass(object):
    """
        Class that is used to generate JSON file to extend diag_table from ecosys_diagnostics file
    """
    def __init__(self, vert_grid):
        """
            Constructor: creates a dictionary object to eventually dump to JSON
        """
        # TODO: other streams change names in spinup mode, so I kept that practice here. However,
        #       I don't like how I handle the names... namely, hm_bgc_annual in spinup mode has
        #       completely different variables from hm_bgc_annual in "regular" mode
        self._diag_table_dict = dict()

        # NOTE: the "_z" in frequency => convert to z-space rather than output on native grid
        # NOTE: "hm" => 3D vars on model grid, "h" => interpolated

        # "medium" frequency should be treated like "mom6.hm" stream -- annual in spinup runs, monthly otherwise
        # i. 2D vars
        suffix_dict = {'$OCN_DIAG_MODE == "spinup"': "h_bgc_annual%4yr", "$TEST == True": "h_bgc_daily%4yr-%2mo-%2dy", "else": "h_bgc_monthly%4yr-%2mo"}
        output_freq_units_dict = {'$OCN_DIAG_MODE == "spinup"': "years", "$TEST == True": "days", "else": "months"}
        self._diag_table_dict["medium"] = self._dict_template(suffix_dict, output_freq_units_dict)
        # ii. 3D vars on interpolated grid
        if vert_grid in ["interpolated", "both"]:
            suffix_dict = {'$OCN_DIAG_MODE == "spinup"': "h_bgc_annual_z%4yr", "$TEST == True": "h_bgc_daily_z%4yr-%2mo-%2dy", "else": "h_bgc_monthly_z%4yr-%2mo"}
            self._diag_table_dict["medium_z"] = self._dict_template(suffix_dict, output_freq_units_dict, module="ocean_model_z")
        # iii. 3D vars on native grid
        if vert_grid in ["native", "both"]:
            suffix_dict = {'$OCN_DIAG_MODE == "spinup"': "hm_bgc_annual_z%4yr", "$TEST == True": "hm_bgc_daily_z%4yr-%2mo-%2dy", "else": "hm_bgc_monthly_z%4yr-%2mo"}
            self._diag_table_dict["medium_native_z"] = self._dict_template(suffix_dict, output_freq_units_dict, module="ocean_model")

        # "high" frequency should be treated like "mom6.sfc" stream -- 5-day averages in spinup, daily otherwise
        # unlike "sfc", this stream will write one file per month instead of per year (except in spinup)
        # i. 2D vars
        suffix_dict = {'$OCN_DIAG_MODE == "spinup"': "h_bgc_daily5%4yr", "else": "h_bgc_daily%4yr-%2mo"}
        output_freq_dict = {'$OCN_DIAG_MODE == "spinup"': 5, "else": 1}
        new_file_freq_units_dict = {'$OCN_DIAG_MODE == "spinup"': "years", "else": "months"}
        self._diag_table_dict["high"] = self._dict_template(suffix_dict, "days", new_file_freq_units_dict, output_freq_dict)
        # ii. 3D vars on interpolated grid
        if vert_grid in ["interpolated", "both"]:
            suffix_dict = {'$OCN_DIAG_MODE == "spinup"': "h_bgc_daily5_z%4yr", "else": "h_bgc_daily_z%4yr-%2mo"}
            self._diag_table_dict["high_z"] = self._dict_template(suffix_dict, "days", new_file_freq_units_dict, output_freq_dict, module="ocean_model_z")
        # iii. 3D vars on native grid
        if vert_grid in ["native", "both"]:
            suffix_dict = {'$OCN_DIAG_MODE == "spinup"': "hm_bgc_daily5_z%4yr", "else": "hm_bgc_daily_z%4yr-%2mo"}
            self._diag_table_dict["high_native_z"] = self._dict_template(suffix_dict, "days", new_file_freq_units_dict, output_freq_dict, module="ocean_model")

        # "low" frequency should be treated as annual averages
        # i. 2D vars
        suffix_dict = {'$OCN_DIAG_MODE == "spinup"': "h_bgc_annual2%4yr", "else": "h_bgc_annual%4yr"}
        self._diag_table_dict["low"] = self._dict_template(suffix_dict, "years")
        # ii. 3D vars on interpolated grid
        if vert_grid in ["interpolated", "both"]:
            suffix_dict = {'$OCN_DIAG_MODE == "spinup"': "h_bgc_annual2_z%4yr", "else": "h_bgc_annual_z%4yr"}
            self._diag_table_dict["low_z"] = self._dict_template(suffix_dict, "years", module="ocean_model_z")
        # iii. 3D vars on native grid
        if vert_grid in ["native", "both"]:
            suffix_dict = {'$OCN_DIAG_MODE == "spinup"': "hm_bgc_annual2_z%4yr", "else": "hm_bgc_annual_z%4yr"}
            self._diag_table_dict["low_native_z"] = self._dict_template(suffix_dict, "years", module="ocean_model")


    def update(self, varname, frequency, is2D, lMARBL_output_all, vert_grid):
        if lMARBL_output_all:
            use_freq = ['medium']
        else:
            use_freq = []
            for freq in frequency:
                use_freq.append(freq)

        # iv. Update dictionary
        for freq in use_freq:
            if freq == "never":
                continue
            # append _z to frequency for 3D vars
            if is2D:
                self._diag_table_dict[f"{freq}"]["fields"][0]["lists"][0].append(varname)
            else:
                if vert_grid in ["interpolated", "both"]:
                    self._diag_table_dict[f"{freq}_z"]["fields"][0]["lists"][0].append(varname)
                if vert_grid in ["native", "both"]:
                    self._diag_table_dict[f"{freq}_native_z"]["fields"][0]["lists"][0].append(varname)


    def dump_to_json(self, filename):
        import json

        out_dict = dict()
        out_dict["Files"] = dict()
        for freq in self._diag_table_dict:
            if len(self._diag_table_dict[freq]["fields"][0]["lists"][0]) > 0:
                out_dict["Files"][freq] = self._diag_table_dict[freq].copy()
                if out_dict["Files"][freq]["fields"][0]["module"] == "ocean_model" and freq[-2:] == "_z":
                    transports = ["volcello", "vmo", "vhGM", "vhml", "umo", "uhGM", "uhml"]
                    out_dict["Files"][freq]["fields"][0]["lists"].append(transports)
        if out_dict["Files"]:
            with open(filename, "w") as fp:
                json.dump(out_dict, fp, separators=(',', ': '), sort_keys=False, indent=3)
        else:
            print("WARNING: no JSON file written as no variables were requested")


    def _dict_template(self, suffix, output_freq_units, new_file_freq_units=None, output_freq=1, new_file_freq=1, module="ocean_model", packing=1):
        """
            Return the basic template for MOM6 diag_table dictionary.
            Variables will be added to output file by appending to template["fields"][0]["lists"][0]

            Parameters:
                * suffix: string used to identify output file; could also be a dictionary
                          where keys are logical evaluations
                * output_freq_units: units used to determine how often to output; similar
                                     to suffix, this can also be a dictionary
                * new_file_freq_units: units used to determine how often to generate new stream
                                       files; if None, will use output_freq_units (default: None)
                * output_freq: how frequently to output (default: 1)
                * new_file_freq: how frequently to create new files (default: 1)
                * module: string that determines vertical grid; "ocean_model_z" maps to Z space, "ocean_model" stays on native grid, "ocean_model_rho2" is sigma2
                * packing: integer that is used to determine precision when writing output; 1 => double precision, 2 => single
                           (default: 1)
        """
        template = dict()
        template["suffix"] = suffix
        template["output_freq"] = output_freq
        template["new_file_freq"] = new_file_freq
        template["output_freq_units"] = output_freq_units
        if new_file_freq_units:
            template["new_file_freq_units"] = new_file_freq_units
        else:
            template["new_file_freq_units"] = output_freq_units
        template["time_axis_units"] = "days"
        template["reduction_method"] = "mean"
        template["regional_section"] = "none"
        template["fields"] = [{"module": module, "packing": packing, "lists" : [[]]}]
        return template


#######################################

def _parse_args():
    """ Parse command line arguments
    """

    import argparse

    parser = argparse.ArgumentParser(description="Generate MOM diag table from MARBL diagnostics",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Command line argument to point to MARBL diagnostics input file (required!)
    parser.add_argument('-i', '--ecosys_diagnostics_in', action='store', dest='ecosys_diagnostics_in',
                        required=True, help='File generated by MARBL_generate_diagnostics_file')

    # Command line argument to point to diag table output file (required!)
    parser.add_argument('-t', '--diag_table_out', action='store', dest='diag_table_out',
                        required=True, help='Location of diag table (JSON) file to create')

    # Command line arguments for the different streams to use (low, medium, high)
    parser.add_argument('-l', '--low_frequency_stream', action='store', dest='low_frequency_stream',
                        type=int, default= 0, help='Stream to put low frequency output into (required if not lMARBL_output_all)')

    parser.add_argument('-m', '--medium_frequency_stream', action='store', dest='medium_frequency_stream',
                        type=int, default= 0, help='Stream to put medium frequency output into (required if not lMARBL_output_all)')

    parser.add_argument('-g', '--high_frequency_stream', action='store', dest='high_frequency_stream',
                        type=int, default= 0, help='Stream to put high frequency output into (required if not lMARBL_output_all)')

    parser.add_argument('-v', '--vert_grid', action='store', dest='vert_grid',
                        default= 'native', choices=['native', 'interpolated', 'both'],
                        help='BGC history output grid')

    # Should all MARBL diagnostics be included in the hm_bgc stream?
    parser.add_argument('--lMARBL_output_all', action='store', dest='lMARBL_output_all',
                        type=bool, default=False, help="Put all MARBL diagnostics in hm_bgc stream")

    # Should MARBL's ALT_CO2 diagnostics be included in the diag table?
    parser.add_argument('--lMARBL_output_alt_co2', action='store', dest='lMARBL_output_alt_co2',
                        type=bool, default=False, help="Include ALT_CO2 diagnostics in streams")

    return parser.parse_args()

#######################################

def _parse_line(line_in):
    """ Take a line of input from the MARBL diagnostic output and return the variable
        name, frequency, and operator. Lines that are commented out or empty should
        return None for all three; non-empty lines that are not in the proper format
        should trigger errors.

        If they are not None, frequency and operator are always returned as lists
        (although they often have just one element).
    """
    import logging
    import sys

    line_loc = line_in.split('#')[0].strip()
    # Return None, None if line is empty
    if len(line_loc) == 0:
        return None, None, None

    logger = logging.getLogger("__name__")
    line_split = line_loc.split(':')
    if len(line_split) != 2:
        logger.error("Can not determine variable name from following line: '%s'" % line_in)
        sys.exit(1)

    freq = []
    op = []
    for freq_op in line_split[1].split(','):
        freq_op_split = freq_op.strip().split('_')
        if len(freq_op_split) != 2:
            logger.error("Can not determine frequency and operator from following entry: '%s'" % line_split[1])
            sys.exit(1)
        freq.append(freq_op_split[0])
        op.append(freq_op_split[1])

    return line_split[0].strip(), freq, op

#######################################


def diagnostics_to_diag_table(ecosys_diagnostics_in,
                              diag_table_out,
                              diag2D_list,
                              vert_grid,
                              lMARBL_output_all,
                              lMARBL_output_alt_co2):
    """
        Build a diag_table dictionary to dump to JSON format
    """

    import os, sys, logging
    logger = logging.getLogger("__name__")
    labort = False
    processed_vars = dict()

    # 1. Check arguments:
    #    ecosys_diagnostics_in can not be None and must be path of an existing file
    if ecosys_diagnostics_in == None:
        logger.error("Must specific ecosys_diagnostics_in")
        labort = True
    elif not os.path.isfile(ecosys_diagnostics_in):
        logger.error("File not found %s" % ecosys_diagnostics_in)
        labort = True
    if labort:
        sys.exit(1)

    # 2. Set up diag_table object
    diag_table = DiagTableClass(vert_grid)

    # 3. Read ecosys_diagnostics_in line by line, convert each line to diag table entry
    with open(ecosys_diagnostics_in, 'r') as file_in:
        all_lines = file_in.readlines()

    for line in all_lines:
        varname, frequency, operator = _parse_line(line.strip())
        # i. Continue to next line in the following circumstances
        #    * varname = None
        if varname == None:
            continue
        #    * Skip ALT_CO2 vars unless explicitly requested
        if (not lMARBL_output_alt_co2) and ("ALT_CO2" in varname):
            continue

        # ii. Abort if varname has already appeared in file at given frequency
        for freq in frequency:
            if freq not in processed_vars:
                processed_vars[freq] = []
            if varname in processed_vars[freq]:
                logger.error(f"{varname} appears in {ecosys_diagnostics_in} with frequency %{freq} multiple times")
                sys.exit(1)
            processed_vars[freq].append(varname)

        # iii. Update diag table
        is2D = varname in diag2D_list
        diag_table.update(varname, frequency, is2D, lMARBL_output_all, vert_grid)

    # File footer
    diag_table.dump_to_json(diag_table_out)

#######################################

if __name__ == "__main__":
    # Parse command line arguments
    import logging
    args = _parse_args()

    logging.basicConfig(format='%(levelname)s (%(funcName)s): %(message)s', level=logging.DEBUG)

    # call diagnostics_to_diag_table()
    diagnostics_to_diag_table(args.ecosys_diagnostics_in,
                              args.diag_table_out,
                              args.diag2D_list,
                              args.vert_grid,
                              args.lMARBL_output_all,
                              args.lMARBL_output_alt_co2)