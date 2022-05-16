import time

import pycomm3
from pycomm3 import LogixDriver
from pycomm3 import Tag


# class Utils:



class Valve:

    def __init__(self, valve_name: str, energise_cmd_tag: str, opn_ind_ls_tag: str, cls_ind_ls_tag: str,
                 plc_address: str, nc_valve=False):
        """
        Valve type object used to represent a Switching valve

        :param valve_name: Valve Name
        :param energise_cmd_tag: Tag used to capture the energise command order to open/close the valve
        :param opn_ind_ls_tag: Tag name to report back the Open LS status
        :param cls_ind_ls_tag: Tag name to report back the Closed LS status
        :param plc_address: PLC IP/Slot number to R/W Tag data
        :param nc_valve: Defines Valve LS behavior, defaults to TRUE for a normal valve, set to FALSE is behavior is
        inverted as with a Normally Open Valve
        """

        self.energise_cmd = False  # Open Command Order Signal from PLC
        self.opn_ind = nc_valve  # Open Indication to Signal PLC
        self.cls_ind = ~nc_valve  # Closed Indication to Signal PLC
        self.opn_time = 2  # Opening Travel time before Open indication
        self.cls_time = 2  # Close Travel time before Open indication
        self.valve_name = valve_name
        self.description = ''
        self.valve_type = nc_valve  # False = Normally Closed Valve, Energise to Open / True = Normally Open Valve, Energise to Close
        self.energise_cmd_tag = energise_cmd_tag
        self.open_ind_tag = opn_ind_ls_tag
        self.close_ind_tag = cls_ind_ls_tag
        self.plc_address = plc_address
        self.timer = 0  # Hold current time
        self.done_time = 0 # Holds Current time + delay
        self.limitswitch_delay = 1  # In sec
        self.last_command = 0

    def update(self, plc: LogixDriver):
        """
        Updates the Valve object, reads tags from the PLC, process the data and Writes back the LS data

        :param plc: Takes a LogixDriver PLC object from Pycomm3 library, connection must be opened before its handed in
        :return:
        """
        # Read data from PLC
        self._read_from_plc(plc)

        # Process Data
        self.energise(self.energise_cmd)

        # Write data back to PLC
        self._write_to_plc(plc)

    def _read_from_plc(self, plc: LogixDriver):
        """
        Reads data from a LogixDriver PLC object

        :param plc: LogixDriver PLC Object, connection needs to be open before its handed in
        :return:
        """
        # Take all data in

        # self.energise_cmd = plc.read(self.energise_cmd_tag).value or bool(plc.read(self.valve_name[:] + '.OUT1').value) or bool(plc.read(self.valve_name[:] + '.OUT2').value)
        self.energise_cmd = plc.read(self.energise_cmd_tag).value or bool(plc.read('O' + self.valve_name[1:] + '_CL').value)


    def energise(self, command: bool):
        """
        Simulates valve limit switch behavior

        :param command: TRUE or FALSE
        :return:
        """

        if self.energise_cmd != self.last_command:  # Check for Energise Status Change
            # Turn OFF Both LS and restart timer
            self.opn_ind = False
            self.cls_ind = False
            self._reset_timer()
            self.last_command = self.energise_cmd

        if self._check_timer():
            if not self.valve_type:  # Normally Closed Valve Type
                if command:
                    self.opn_ind = True
                    self.cls_ind = False
                else:
                    self.opn_ind = False
                    self.cls_ind = True

            if self.valve_type:  # Normally Open Valve Type
                if command:
                    self.opn_ind = False
                    self.cls_ind = True
                else:
                    self.opn_ind = True
                    self.cls_ind = False

    def _write_to_plc(self, plc: LogixDriver):
        """
        Writes data back to a LogixDriver PLC object

        :param plc: LogixDriver PLC Object, connection needs to be open before its handed in
        :return:
        """
        # with LogixDriver(self.plc_address) as plc:
        #     plc.write(self.open_ind_tag, self.opn_ind)
        #     plc.write(self.close_ind_tag, self.cls_ind)
        plc.write(self.open_ind_tag, self.opn_ind)
        plc.write(self.close_ind_tag, self.cls_ind)

    def _reset_timer(self):
        self.timer = time.time()
        self.done_time = self.timer + self.limitswitch_delay

    def _check_timer(self):
        self.timer = time.time()
        if self.done_time - self.timer <= 0:
            return True  # Timer Done
        else:
            return False



class Valve_Analog:

    def __init__(self, valve_name, valve_sp_tag, valve_fbk_tag, opn_ind_ls_tag, cls_ind_ls_tag, plc_address):
        """
        Valve type object used to represent a Control Valve

        :param valve_name: Valve Name
        :param valve_sp_tag: SP tag name, used as data source
        :param valve_fbk_tag: Feedback tag name, written back to PLC
        :param opn_ind_ls_tag: Open LS indication tag name, written back to PLC
        :param cls_ind_ls_tag: Closed LS indication tag name, written back to PLC
        :param plc_address: Destination IP/Slot PLC
        """

        self.valve_name = valve_name
        self.valve_sp_tag = valve_sp_tag
        self.valve_sp_value = 0
        self.valve_fbk_tag = valve_fbk_tag
        self.valve_fbk_value = 0
        self.plc_address = plc_address
        self._tag_sp_data = Tag
        self._tag_data = Tag
        self.opn_ind_ls_tag = opn_ind_ls_tag
        self.cls_ind_ls_tag = cls_ind_ls_tag
        self.opn_ind_ls_value = 0
        self.cls_ind_ls_value = 0
        self.minRng = 6240 + 100
        self.maxRng = 31208
        # self.maxRng = 24968 - 100


    def update(self, plc: LogixDriver):
        """
        Updates the Control Valve

        :param plc: LogixDriver PLC Object, connection needs to be open before its handed in
        :return:
        """
        # Read data from PLC
        self._read_from_plc(plc)

        # Process Data
        self._process_data()

        # Write data back to PLC
        self._write_to_plc(plc)

    def _read_from_plc(self, plc: LogixDriver):
        """

        :param plc: LogixDriver PLC Object, connection needs to be open before its handed in
        :return:
        """

        self._tag_sp_data = plc.read(self.valve_sp_tag)
        self._tag_data = plc.read(self.valve_name)
        # print(self._tag_sp_data)

    def _write_to_plc(self, plc: LogixDriver):
        """

        :param plc: LogixDriver PLC Object, connection needs to be open before its handed in
        :return:
        """
        print(self._tag_data)
        print(f'"Channel is " {self._tag_data.value["Channel"]}')
        plc.write((self.valve_fbk_tag, self.valve_fbk_value))
        plc.write((self.cls_ind_ls_tag, self.cls_ind_ls_value))
        plc.write((self.opn_ind_ls_tag, self.opn_ind_ls_value))
        print(f'"Written Channel to " {self.valve_fbk_value}')

    def _process_data(self):
        """

        :return:
        """



        if self._tag_sp_data.type is not None:
            max_rng = self._tag_data.value['MAX']
            min_rng = self._tag_data.value['MIN']
            self.valve_sp_value = self._tag_sp_data.value
            self.valve_fbk_value = int(((24968 * (self.valve_sp_value - min_rng)) / (max_rng - min_rng)) + 6240)
            if self.valve_fbk_value <= self.minRng:
                self.cls_ind_ls_value = True
            else:
                self.cls_ind_ls_value = False

            if self.valve_fbk_value >= self.maxRng:
                self.opn_ind_ls_value = True
            else:
                self.opn_ind_ls_value = False
            # print(self.valve_fbk_value)



class AnalogInput:

    def __init__(self, input_name, input_feedback_tag, plc_address, ext_reference_tag1='', ext_reference_tag2='',
                 inc_condition_tag1='', inc_condition_tag2='', inc_condition_tag3='', dec_condition_tag1='',
                 dec_condition_tag2='', dec_condition_tag3='', inc_ROC=10, decROC=10, integrating_process=0,
                 andormode=0, fixed_value=0):

        self.input_name = input_name
        self.feedback_tag = input_feedback_tag
        self.feedback_tag_value = 6240
        self.plc_address = plc_address

        self.fixed_value = fixed_value
        # self.maxRng = 24968
        self.maxRng = 31208
        self.minRng = 6240

        self.incROC = inc_ROC
        self.decROC = decROC
        self.simulated_value = self.minRng

        self.integrating_process = integrating_process
        self.andormode = andormode
        self.ext_reference_tag1 = ext_reference_tag1
        self.ext_reference_tag2 = ext_reference_tag2

        self.inc_condition_tag1 = inc_condition_tag1
        self.inc_condition_tag2 = inc_condition_tag2
        self.inc_condition_tag3 = inc_condition_tag3
        self.dec_condition_tag1 = dec_condition_tag1
        self.dec_condition_tag2 = dec_condition_tag2
        self.dec_condition_tag3 = dec_condition_tag3

        self.ext_reference_tag1_data = Tag
        self.ext_reference_tag2_data = Tag

        self.inc_condition_tag1_data = Tag
        self.inc_condition_tag2_data = Tag
        self.inc_condition_tag3_data = Tag
        self.dec_condition_tag1_data = Tag
        self.dec_condition_tag2_data = Tag
        self.dec_condition_tag3_data = Tag

        self.increase_allowed = False
        self.decrease_allowed = False

        self.time_diff = 0.0
        self.time_last = time.time()

    def update(self, plc):
        self._read_from_plc(plc)
        self._process_data()
        self._write_to_plc(plc)

    def _read_from_plc(self, plc: LogixDriver):

        self.ext_reference_tag1_data = plc.read(self.ext_reference_tag1)
        self.ext_reference_tag2_data = plc.read(self.ext_reference_tag2)

        self.inc_condition_tag1_data = plc.read(self.inc_condition_tag1)
        self.inc_condition_tag2_data = plc.read(self.inc_condition_tag2)
        self.inc_condition_tag3_data = plc.read(self.inc_condition_tag3)

        self.dec_condition_tag1_data = plc.read(self.dec_condition_tag1)
        self.dec_condition_tag2_data = plc.read(self.dec_condition_tag2)
        self.dec_condition_tag3_data = plc.read(self.dec_condition_tag3)

    def _write_to_plc(self, plc: LogixDriver):

        self._trim_signal()
        # print(f'"Channel is " {self._tag_data.value["Channel"]}')
        plc.write((self.feedback_tag, self.feedback_tag_value))
        # print(f'"Written Channel to " {self.valve_fbk_value}')

        self.time_last = time.time()    # Routine finished, snapshot current time to be compared on next call

    def _process_data(self):

        self.increase_allowed = False
        self.decrease_allowed = False

        self.time_diff = time.time() - self.time_last   # Calculate time difference between now and last update, used
                                                        # to calculate amount of process units to change per call

        # Check which tags are available and define signal treatment depending on what data is made available
        # ==============================================
        # Handle Non-Integrating Process
        # If ExtReferenceTag1 or 2 is != 0 and tag exist, use External Reference
        if self.ext_reference_tag1 != '0' or self.ext_reference_tag2 != '0' and self.integrating_process == 0:
            # Both tags are invalid condition
            if not self._check_tag(self.ext_reference_tag1_data) and not self._check_tag(self.ext_reference_tag2_data):
                print('External Reference Tags are Invalid...')
                return

            # At least one tag is valid
            if self._check_tag(self.ext_reference_tag1_data) or self._check_tag(self.ext_reference_tag2_data):
                # Choose max between the two tagname values
                self.feedback_tag_value = max(self._extract_tag_value(self.ext_reference_tag1_data),self._extract_tag_value(self.ext_reference_tag2_data),self.minRng)
                self.simulated_value = self.feedback_tag_value
                return


        # ==============================================
        # Handle Integrating Process
        # Check for data type, if real comes from analog

        # Handle Increase Condition Tags
        # Check if there's at least a tagname available and if process is integrating type
        if self.inc_condition_tag1 != '0' or self.inc_condition_tag2 != '0' or self.inc_condition_tag3 != '0' and self.integrating_process == 1:
            self.increase_allowed = True
            if self.andormode == 1: self.increase_allowed = False # OR Mode Selected
            self._handle_integrating_inc_condition(self.inc_condition_tag1_data)
            self._handle_integrating_inc_condition(self.inc_condition_tag2_data)
            self._handle_integrating_inc_condition(self.inc_condition_tag3_data)

        # Handle Decrease Condition Tags
        if self.dec_condition_tag1 != '0' or self.dec_condition_tag2 != '0' or self.dec_condition_tag3 != '0' and self.integrating_process == 1:
            self.decrease_allowed = True
            if self.andormode == 1: self.decrease_allowed = False
            self._handle_integrating_dec_condition(self.dec_condition_tag1_data)
            self._handle_integrating_dec_condition(self.dec_condition_tag2_data)
            self._handle_integrating_dec_condition(self.dec_condition_tag3_data)

        # If all increment or decrement are not Boolean, set its allowed flag to FALSE, only Booleans can yield TRUE
        if self.inc_condition_tag1_data.type != 'BOOL' and self.inc_condition_tag2_data.type != 'BOOL' and self.inc_condition_tag3_data.type != 'BOOL':
            self.increase_allowed = False

        if self.dec_condition_tag1_data.type != 'BOOL' and self.dec_condition_tag2_data.type != 'BOOL' and self.dec_condition_tag3_data.type != 'BOOL':
            self.decrease_allowed = False

        # Check for Increase/Decrease allowed and adjust the feedback signal
        if self.increase_allowed or self.decrease_allowed:
            if self.increase_allowed:
                self.simulated_value += int(self.incROC * self.time_diff)
                self.simulated_value = min(self.simulated_value, self.maxRng)

            if self.decrease_allowed:
                self.simulated_value -= int(self.decROC * self.time_diff)
                self.simulated_value = max(self.simulated_value, self.minRng)

            self.feedback_tag_value = self.simulated_value
            return

        # Sends FixedValue if no tags have been specified
        if self.ext_reference_tag1 == '0' and self.ext_reference_tag1 == '0' and self.inc_condition_tag1 == '0' and self.inc_condition_tag2 == '0' and self.inc_condition_tag3 == '0' \
                and self.dec_condition_tag1 == '0' and self.dec_condition_tag2 == '0' and self.dec_condition_tag3 == '0':
            self.feedback_tag_value = self.fixed_value

    def _handle_integrating_dec_condition(self, tagname_data: Tag):
        if self._check_tag(tagname_data):
            if tagname_data.type == 'BOOL':
                if self.andormode == 1: # OR Mode Selected
                    self.decrease_allowed = self.decrease_allowed | tagname_data.value
                else:
                    self.decrease_allowed = self.decrease_allowed & tagname_data.value
            else:
                # self.decrease_allowed = False
                if self._extract_tag_value(tagname_data) > self.minRng:
                    self.feedback_tag_value -= self._calculated_roc(tagname_data, int(self.decROC * self.time_diff))
                    self.simulated_value = self.feedback_tag_value

    def _handle_integrating_inc_condition(self, tagname_data: Tag):
        if self._check_tag(tagname_data):
            if tagname_data.type == 'BOOL':
                if self.andormode == 1:  # OR Mode Selected
                    self.increase_allowed = self.increase_allowed | tagname_data.value
                else:
                    self.increase_allowed = self.increase_allowed & tagname_data.value
            else:
                # self.increase_allowed = False
                if self._extract_tag_value(tagname_data) > self.minRng:
                    self.feedback_tag_value += self._calculated_roc(tagname_data, int(self.incROC * self.time_diff))
                    self.simulated_value = self.feedback_tag_value

    def _extract_tag_value(self, tag: Tag, unscaled=True):
        """
        Extracts the value from a Pycomm3 Tag, returns zero if tag doesn't exists

        :param tag: Pycomm3 Tag
        :return: Returns the tag value
        """

        if tag.type is None:
            return 0

        if tag.type == 'UDT_zzAnaIN':
            return tag.value['Channel']

        if tag.type == 'REAL':
            if unscaled:
                return self._unscale(tag.value)
            else:
                return tag.value

    def _check_tag(self, tag_to_check: Tag):
        """
        Verifies if a tag exists in the PLC by looking at the response from the PLC when read, if Tag.error is different
        from None, returns TRUE, meaning Tag exists and haves valid data

        :param tag_to_check: Tag to be checked, takes a Pycomm3 Tag type
        :return:
        """
        # print(type(tag_to_check))
        # print(tag_to_check)
        # print(str(tag_to_check.error))
        if tag_to_check.type is None:
            return False
        else:
            return True

    def _trim_signal(self):
        self.feedback_tag_value = max(min(self.maxRng, self.feedback_tag_value), self.minRng)

    def _unscale(self, engineering_value):
        """
        Unscales an engineering value back to raw PLC counts

        :param engineering_value: 0..100%
        :return:
        """
        max_rng = 31208
        min_rng = 6240

        return int(((max_rng - min_rng) * engineering_value / 100) + min_rng)

    @staticmethod
    def _calculated_roc(tagname: Tag, roc_max: int) -> int:
        """
        Calculates a ROC (Rate of Change) value from a PLC Count value

        :param tagname: Tagname whose Channel is to be used for calculation
        :param roc_max: ROC value coming from CSV file setting, this is the max ROC at max PLC counts
        :return: Returns a proportionally scaled ROC value based on the PLC counts and the roc_max from the CSV
        """
        max_rng = 31208
        min_rng = 6240

        plc_counts = max(min_rng, tagname.value['Channel'])
        roc_set = roc_max

        calculated_roc = int((plc_counts-min_rng)*roc_set/(max_rng-min_rng))

        return calculated_roc

    # def _unscale_tag(self, tag: Tag):
    #     """
    #     Unscales an engineering value back to raw PLC counts
    #
    #     :param engineering_value: 0..100%
    #     :return:
    #     """
    #     max_rng = 24968
    #     min_rng = 6240
    #
    #     return int((24968 * engineering_value /100) + 6240)

class Tank:

    def __init__(self, name: str):
        self.name = name
        self.level = 0  # Tank Level
        self.pressure = 0  # Tank Pressure
