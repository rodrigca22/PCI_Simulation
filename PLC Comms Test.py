import time

import pandas as pd
from pycomm3 import LogixDriver
from pycomm3 import CIPDriver
import FieldObjects
import logging as log, sys #colorama

# ===== OPTIONS =====
generate_csv = True
csv_col_names = ['InputName',
                 'FeedbackTag',
                 'PLCAddress',
                 'ExtReferenceTag1',
                 'IncTag1',
                 'IncTag2',
                 'IncTag3',
                 'DecTag1',
                 'DecTag2',
                 'DecTag3',
                 'IncROC',
                 'DecROC',
                 'Integrating',
                 'AndORMode',
                 'FixedValue']

# ===== PARAMETERS =====
PLC_IP = ['10.20.20.201/3', '10.20.20.201/4', '10.20.20.201/5']
TAG_FILENAME = ['CLX_PCIBF5-Tags.CSV', 'CLX_PCIBF6-Tags.CSV','CLX_DistBF5-Tags.CSV']
# PLC_IP = ['10.20.20.201/3', '10.20.20.201/4', '10.20.20.201/5','10.20.20.211/3', '10.20.20.211/4', '10.20.20.211/5']
# TAG_FILENAME = ['CLX_PCIBF5-Tags.CSV', 'CLX_PCIBF6-Tags.CSV','CLX_DistBF5-Tags.CSV','CLX_PCIBF5-Tags.CSV', 'CLX_PCIBF6-Tags.CSV','CLX_DistBF5-Tags.CSV']
ANL_RELATION_TAG_FILE = 'analog_inputs_relation_list.csv'
RECONNECT_TIME = 5  # PLC Re-Connection timer

# ===== LOGGER SETUP =====
# logging.basicConfig(filename='SimLog.log', format='%(asctime)s - [%(levelname)s] %(message)s', encoding='utf-8', level=logging.DEBUG)
#log.basicConfig(format='%(asctime)s - [%(levelname)s] %(message)s', encoding='utf-8', level=log.INFO, handlers=[log.StreamHandler(stream=sys.stdout), log.FileHandler(filename='SimLog.log')])


# ===== LOAD PLC TAGS =====
# Opens a connection to each PLC, this uploads all the tags in memory, they are stored in a list which is going to be
# passed in subsequent calls, this avoids the overhead of uploading the tags on every control Open connection
# instruction

plc_tags = []  # Stores a list of lists of tags per controller
full_plc_tags = []  # Flat tag list from all controllers, used for global tag search

# Tries to connect to all PLCs to gather the tag database, repeats if fails to connect
plc_connection = False
while plc_connection == False:
    try:
        for PLC in PLC_IP:
            with LogixDriver(PLC, init_tags=True) as plc:
                plc.open()
                # log.info('Connection succeeded!')
                # log.info('Reading tag database...')
                plc_tags.append(plc.tags)
                # log.info('Done!')
        plc_connection = True
    except:
        print(f'PLC not found, retrying... in {RECONNECT_TIME} sec')
        # log.warning(f'PLC not found, retrying... in {RECONNECT_TIME} sec')
        time.sleep(RECONNECT_TIME)


# Create Global Tag List
full_plc_tags = [item for sublist in plc_tags for item in sublist]

# ===========


valves_sw = []  # Switching Valves
valves_anl = []  # Analog Valves
anl_inp = []  # Analog Inputs

# READ CONTROLLER TAG CSV FILES
# log.info('Reading Controller Tag CSV Files')
for idx, TAG_FILE in enumerate(TAG_FILENAME):
    df = pd.read_csv(TAG_FILE, encoding='Windows-1252', skiprows=6)

    # df = pd.read_csv(TAG_FILENAME, encoding='Windows-1252', skiprows=6)

    # Get all zz_vnc and zz_vno objects NO Valves and NC Valves
    all_sw_valves = df[((df['DATATYPE'] == 'UDT_zzVNC') | (df['DATATYPE'] == 'UDT_zzVNO')) & (df.SCOPE.isnull())]
    all_analog_valves = df[(df["DATATYPE"] == "UDT_zzAnaIN") & (df.SCOPE.isnull())]

    print(all_sw_valves.head())
    print(all_analog_valves.head())

    # Create Valve Objects
    valve_name = ''
    energise_cmd_tag = ''
    opn_ind_ls_tag = ''
    cls_ind_ls_tag = ''
    nc_valve = False
    vlv_setpoint_tag = ''
    vlv_feedback_tag = ''

    # ============================
    # For analog Valves the UDT is UDT_zzAnaIN (Valve Name)
    # Output data is at ie. O5_1_1VC02_SET where valve name is A5_1_1VC02
    # Feedback data is at ie 05_1_1VC01.Channel, Data must be returned in PLC RAW Counts 0-65535
    # Value is in Engineering Units, it might have to be scaled to Output counts
    # ============================
    print('==============================')
    print('Processing Switching Valves...')
    for index, vlv in all_sw_valves.iterrows():
        valve_name = vlv['NAME']
        energise_cmd_tag = 'O' + valve_name[1:] + '_OP'
        opn_ind_ls_tag = 'I' + valve_name[1:] + '_LS1'
        cls_ind_ls_tag = 'I' + valve_name[1:] + '_LS2'

        nc_valve = vlv['DATATYPE'] != 'UDT_zzVNC'

        valves_sw.append(
            FieldObjects.Valve(vlv['NAME'], energise_cmd_tag, opn_ind_ls_tag, cls_ind_ls_tag, PLC_IP[idx], nc_valve))
        print(f'{vlv["NAME"]} - {energise_cmd_tag} - Valve NC is {nc_valve}')

    print(f'{len(all_sw_valves)} Switching Valves identified in CSV {TAG_FILE}')
    print(f'{len(valves_sw)} Switching Valves')

    print('==============================')
    print('Processing Analog Valves and Inputs...')
    for index, vlv in all_analog_valves.iterrows():
        valve_name = vlv['NAME']
        vlv_setpoint_tag = 'O' + valve_name[1:] + '_SET'
        vlv_feedback_tag = valve_name + '.Channel'
        opn_ind_ls_tag = 'I' + valve_name[1:] + '_LS1'
        cls_ind_ls_tag = 'I' + valve_name[1:] + '_LS2'

        # Check if Setpoint tag exists in any taglist, if it does, create an Analog valve, otherwise is a regular
        # analog input
        # if vlv_setpoint_tag in full_plc_tags is FALSE, it is a Analog Input, if is TRUE, it is a Analog Valve

        if vlv_setpoint_tag in full_plc_tags:  # TRUE = Valve
            valves_anl.append(FieldObjects.Valve_Analog(vlv['NAME'], vlv_setpoint_tag, vlv_feedback_tag, opn_ind_ls_tag,
                                                        cls_ind_ls_tag, PLC_IP[idx]))
            print(f'{vlv["NAME"]} - {vlv_setpoint_tag} as Control Valve')
        else:  # FALSE = Analog Input
            anl_inp.append(FieldObjects.AnalogInput(valve_name, vlv_feedback_tag, PLC_IP[idx]))
            print(f'{vlv["NAME"]} as Analog Input')
    print(f'{len(all_analog_valves)} Analog Devices identified in CSV {TAG_FILE}')
    print(f'{len(valves_anl)} Control Valves')
    print(f'{len(anl_inp)} Analog Inputs')

    print(CIPDriver.discover())
    with LogixDriver(PLC_IP[idx]) as plc:
        print(plc)
        print(plc.info)
        print('=================')

    # ===== GENERATE CSV =====
    if generate_csv:
        anl_inp_csv = []

        for inp in anl_inp:
            anl_inp_csv.append([inp.input_name, inp.feedback_tag, inp.plc_address, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

        df_csv = pd.DataFrame(anl_inp_csv, columns=csv_col_names)
        df_csv.to_csv('analog_inputs.csv', index=False)

# Read in Relation CSV and update analog inputs data
df_rel = pd.read_csv(ANL_RELATION_TAG_FILE, encoding='Windows-1252')
print(df_rel.head())
for index, row in df_rel.iterrows():
    print(row['InputName'])
    for inp in anl_inp:
        if inp.input_name == row['InputName']:
            inp.ext_reference_tag1 = str(row['ExtReferenceTag1'])
            inp.ext_reference_tag2 = str(row['ExtReferenceTag2'])

            inp.inc_condition_tag1 = str(row['IncTag1'])
            inp.inc_condition_tag2 = str(row['IncTag2'])
            inp.inc_condition_tag3 = str(row['IncTag3'])

            inp.dec_condition_tag1 = str(row['DecTag1'])
            inp.dec_condition_tag2 = str(row['DecTag2'])
            inp.dec_condition_tag3 = str(row['DecTag3'])
            inp.incROC = int(row['IncROC'])
            inp.decROC = int(row['DecROC'])

            inp.integrating_process = int(row['Integrating'])
            inp.andormode = int(row['AndORMode'])

            inp.fixed_value = row['FixedValue']

# Connect to PLCs
plc_objects = []
def connect_to_PLCs():
    plcs = []
    for idx, PLC in enumerate(PLC_IP):
        plcs.append(LogixDriver(PLC_IP[idx], init_tags=False))
        plcs[idx].open()
        print(plcs[idx].info)
    return plcs

plc_objects = connect_to_PLCs()

while True:
    # vlv1.update()
    try:
        for idx, plc in enumerate(plc_objects):
            plc._tags = plc_tags[idx]  # Pass on the tag list uploaded at the beginning
            # Update Switching Valves
            for sw_vlv in valves_sw:
                if sw_vlv.plc_address == PLC_IP[idx]:
                    sw_vlv.update(plc)
                    # time.sleep(0.05)
                print(sw_vlv.valve_name)
                if sw_vlv.valve_name == 'A5_2_1VBCM04':
                    print('Valve name ', sw_vlv.valve_name)
                    print('Open tag ', sw_vlv.open_ind_tag)
                    print('Close tag ', sw_vlv.close_ind_tag)
                    print('Output tag ', sw_vlv.energise_cmd_tag)

            # Update Analog Valves
            for anl_vlv in valves_anl:
                if anl_vlv.plc_address == PLC_IP[idx]:
                    anl_vlv.update(plc)
                    # time.sleep(0.05)
                print(anl_vlv.valve_name)
                if anl_vlv.valve_name == 'A5_1_1FT3':
                    print('Valve name ', anl_vlv.valve_name)
                    print(f'"PLC Address " {anl_vlv.plc_address}')
                    print(f'"Setpoint tag " {anl_vlv.valve_sp_tag} " - Value = " {anl_vlv.valve_sp_value}')
                    print(f'"Feedback tag " {anl_vlv.valve_fbk_tag} " - Value = " {anl_vlv.valve_fbk_value}')

            # Update Analog Inputs
            for anl in anl_inp:
                if anl.plc_address == PLC_IP[idx]:
                    anl.update(plc)
                    # time.sleep(0.05)
                print(anl.input_name)
                if anl.input_name == 'A5_1_1FT3':
                    print('Valve name ', anl.input_name)
                    print(f'"PLC Address " {anl.plc_address}')
                    # print(f'"Setpoint tag " {anl_vlv.valve_sp_tag} " - Value = " {anl_vlv.valve_sp_value}')
                    print(f'"Feedback tag " {anl.feedback_tag} " - Value = " {anl.feedback_tag}')
    except:
        print(f'Connection lost to PLC {PLC_IP[idx]}!')
        try:
            print("Trying to re-connect...")
            plc_objects = connect_to_PLCs()
        except:
            print(f'Failed to connect to PLCs!, check that all PLCs are available, re-trying in {RECONNECT_TIME}sec...')
            time.sleep(5)
    time.sleep(0.5)

