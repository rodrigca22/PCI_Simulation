import time
import pandas as pd
from pycomm3 import LogixDriver
import FieldObjects

PLC_IP = '10.20.10.200/0'
TAG_FILENAME = 'CLX_PCIBF5-Tags.CSV'

# READ CONTROLLER TAG CSV FILE
df = pd.read_csv(TAG_FILENAME, encoding='Windows-1252', skiprows=6)

# Get all zz_vnc and zz_vno objects NO Valves and NC Valves
all_sw_valves = df[((df['DATATYPE'] == 'UDT_zzVNC') | (df['DATATYPE'] == 'UDT_zzVNO')) & (df.SCOPE.isnull())]
all_analog_valves = df[(df["DATATYPE"] == "UDT_zzAnaIN") & (df.SCOPE.isnull())]

print(all_sw_valves.head())
print(all_analog_valves.head())

# Create Valve Objects
valves_sw = []
valves_anl = []
valve_name = ''
energise_cmd_tag = ''
opn_ind_ls_tag = ''
cls_ind_ls_tag = ''
nc_valve = False
vlv_setpoint_tag = ''

# ============================
# For analog Valves the UDT is UDT_zzAnaIN (Valve Name)
# Output data is at ie. O5_1_1VC02_SET where valve name is A5_1_1VC02
# Value is in Engineering Units, it might have to be scaled to Output counts
# ============================

for index, vlv in all_sw_valves.iterrows():
    valve_name = vlv['NAME']
    energise_cmd_tag = 'O' + valve_name[1:] + '_OP'
    opn_ind_ls_tag = 'I' + valve_name[1:] + '_LS1'
    cls_ind_ls_tag = 'I' + valve_name[1:] + '_LS2'
    nc_valve = vlv['DATATYPE'] != 'UDT_zzVNC'

    valves_sw.append(FieldObjects.Valve(vlv['NAME'], energise_cmd_tag, opn_ind_ls_tag, cls_ind_ls_tag, PLC_IP, nc_valve))
    print(f'{vlv["NAME"]} - {energise_cmd_tag} - Valve NC is {nc_valve}')

print(f'{len(all_sw_valves)} Switching Valves identified in CSV')
print(f'{len(valves_sw)} Switching Valves Created')

for index, vlv in all_analog_valves.iterrows():
    valve_name = vlv['NAME']
    vlv_setpoint_tag = 'O' + valve_name[1:] + '_SET'

    valves_anl.append(FieldObjects.Valve_Analog(vlv['NAME'], vlv_setpoint_tag, PLC_IP))
    print(f'{vlv["NAME"]} - {vlv_setpoint_tag}')

print(f'{len(all_sw_valves)} Control Valves identified in CSV')
print(f'{len(valves_sw)} Control Valves Created')
#
# with LogixDriver(PLC_IP) as plc:
#     print(plc)
#     print(plc.info)
#     print(f'TestBool is {plc.read("TestBool").value}')
#     plc.write('TestBool',1)
#
# vlv1 = FieldObjects.Valve('Valve1','OpenCmd','CloseCmd','OpenInd','CloseInd',PLC_IP)


# while True:
#     vlv1.update()
#     time.sleep(1)
