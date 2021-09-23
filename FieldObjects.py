from pycomm3 import LogixDriver


class Valve:

    def __init__(self, valve_name, energise_cmd_tag, opn_ind_ls_tag, cls_ind_ls_tag, plc_address, nc_valve=False):
        """

        :param valve_name:
        :param energise_cmd_tag:
        :param opn_ind_ls_tag:
        :param cls_ind_ls_tag:
        :param plc_address:
        :param nc_valve:
        """
        self.energise_cmd = False  # Open Command Order Signal from PLC
        self.opn_ind = nc_valve  # Open Indication to Signal PLC
        self.cls_ind = ~nc_valve  # Closed Indication to Signal PLC
        self.opn_time = 2  # Opening Travel time before Open indication
        self.cls_time = 2  # Close Travel time before Open indication
        self.valve_name = valve_name
        self.description = ''
        self.valve_type = nc_valve # False = Normally Closed Valve, Energise to Open / True = Normally Open Valve, Energise to Close
        self.energise_cmd_tag = energise_cmd_tag
        self.open_ind_tag = opn_ind_ls_tag
        self.close_ind_tag = cls_ind_ls_tag
        self.plc_address = plc_address

    def update(self):
        # Read data from PLC
        self._read_from_plc()

        # Process Data
        self.energise(self.energise_cmd)

        # Write data back to PLC
        self._write_to_plc()

    def _read_from_plc(self):

        # Take all data in
        with LogixDriver(self.plc_address) as plc:
            self.energise_cmd = plc.read(self.energise_cmd_tag).value

    def _write_to_plc(self):

        with LogixDriver(self.plc_address) as plc:
            plc.write(self.open_ind_tag, self.opn_ind)
            plc.write(self.close_ind_tag, self.cls_ind)

    def energise(self, command):

        if not self.valve_type:    # Normally Closed Valve Type
            if command:
                self.opn_ind = True
                self.cls_ind = False
            else:
                self.opn_ind = False
                self.cls_ind = True

        if self.valve_type:    # Normally Open Valve Type
            if command:
                self.opn_ind = False
                self.cls_ind = True
            else:
                self.opn_ind = True
                self.cls_ind = False




class Tank:

    def __init__(self):
        self.level = 0  # Tank Level
