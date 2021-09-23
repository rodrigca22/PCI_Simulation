import time
import pandas as pd
from pycomm3 import LogixDriver
import FieldObjects

PLC_IP = '10.20.10.200/0'
TAG_FILENAME = 'CLX_PCIBF5-Tags.CSV'

# READ CONTROLLER TAG CSV FILE
df = pd.read_csv(TAG_FILENAME, encoding='Windows-1252', skiprows=6)

# Get all zz_vnc and zz_vno objects NO Valves and NC Valves
all_valves = df[((df['DATATYPE'] == 'UDT_zzVNC') | (df['DATATYPE'] == 'UDT_zzVNO')) & (df.SCOPE.isnull())]

# Create Valve Objects
valves = []
valve_name = ''
energise_cmd_tag = ''
opn_ind_ls_tag = ''
cls_ind_ls_tag = ''
nc_valve = False

for index, vlv in all_valves.iterrows():
    valve_name = vlv['NAME']
    energise_cmd_tag = 'O' + valve_name[1:] + '_OP'
    opn_ind_ls_tag = 'I' + valve_name[1:] + '_LS1'
    cls_ind_ls_tag = 'I' + valve_name[1:] + '_LS2'
    nc_valve = vlv['DATATYPE'] != 'UDT_zzVNC'

    valves.append(FieldObjects.Valve(vlv['NAME'], energise_cmd_tag, opn_ind_ls_tag, cls_ind_ls_tag, PLC_IP, nc_valve))
    print(f'{vlv["NAME"]} - {energise_cmd_tag} - Valve NC is {nc_valve}')

print(all_valves.head())
# print(zz_vnc.head())
# print(df.columns)
print(f'{len(all_valves)} Valves identified in CSV')
print(f'{len(valves)} Valves Created')

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
