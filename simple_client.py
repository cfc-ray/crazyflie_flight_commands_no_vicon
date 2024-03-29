import os
import time
import json
import numpy as np
from cflib.crazyflie.log import LogConfig
import cflib.crazyflie as cfc

HEIGHT = 0.5

class SimpleClient:
    def __init__(self, uri, log_variables=[]):
        self.init_time = time.time()
        self.cf = cfc.Crazyflie(rw_cache='./cache')

        # set callbacks
        self.cf.connected.add_callback(self.connected)
        self.cf.connection_failed.add_callback(self.connection_failed)
        self.cf.connection_lost.add_callback(self.connection_lost)
        self.cf.disconnected.add_callback(self.disconnected)
        print(f'Connecting to {uri}')
        self.cf.open_link(uri)

        self.is_connected = False
        self.data = {}
        self.remain_hovering = False
        self.log_variables = log_variables

    def connected(self, uri):
        print(f'Connected to {uri}')
        self.is_connected = True

        # Start logging
        self.logconfs = []
        self.logconfs.append(LogConfig(name=f'LogConf0', period_in_ms=10))
        num_variables = 0
        for v in self.log_variables:
            num_variables += 1
            if num_variables > 5: # <-- could increase if you paid attention to types / sizes (max 30 bytes per packet)
                num_variables = 0
                self.logconfs.append(LogConfig(name=f'LogConf{len(self.logconfs)}', period_in_ms=10))
            self.data[v] = {'time': [], 'data': []}
            self.logconfs[-1].add_variable(v)
        for logconf in self.logconfs:
            try:
                self.cf.log.add_config(logconf)
                logconf.data_received_cb.add_callback(self.log_data)
                logconf.error_cb.add_callback(self.log_error)
                logconf.start()
            except KeyError as e:
                print(f'Could not start {logconf.name} because {e}')
                for v in logconf.variables:
                    print(f' - {v.name}')
            except AttributeError:
                print(f'Could not start {logconf.name} because of bad configuration')
                for v in logconf.variables:
                    print(f' - {v.name}')


    def connection_failed(self, uri, msg):
        print(f'Connection to {uri} failed: {msg}\n\npress ctrl+C to kill the program and restart.')

    def connection_lost(self, uri, msg):
        print(f'Connection to {uri} lost: {msg}')

    def disconnected(self, uri):
        print(f'Disconnected from {uri}')
        self.is_connected = False
        self.remain_hovering = False

    def log_data(self, timestamp, data, logconf):
        for v in logconf.variables:
            self.data[v.name]['time'].append(timestamp)
            self.data[v.name]['data'].append(data[v.name])

    def log_error(self, logconf, msg):
        print(f'Error when logging {logconf}: {msg}')

    def move(self, x, y, z, yaw, dt):
        # print(f'Move to {x}, {y}, {z} with yaw {yaw} degrees for {dt} seconds')
        start_time = time.time()
        while time.time() - start_time < dt:
            self.cf.commander.send_position_setpoint(x, y, z, yaw)
            time.sleep(0.1)

    def move_smooth(self, p1, p2, yaw, dt):
        # print(f'Move smoothly from {p1} to {p2} with yaw {yaw} degrees in {dt} seconds')
        p1 = np.array(p1)
        p2 = np.array(p2)
        start_time = time.time()
        while True:
            current_time = time.time()
            s = (current_time - start_time) / dt
            p = (1 - s) * p1 + (s * p2)
            self.cf.commander.send_position_setpoint(p[0], p[1], p[2], yaw)
            if s >= 1:
                return
            else:
                time.sleep(0.1)

    def stop(self, dt):
        # print(f'Stop for {dt} seconds')
        self.cf.commander.send_stop_setpoint()
        start_time = time.time()
        while time.time() - start_time < dt:
            time.sleep(0.1)

    def disconnect(self):
        self.cf.close_link()

    def write_data(self, filename='logged_data.json'):

        # pull out the desired test name by removing the '.json' in the filename
        testname = filename[0:-5]

        # prepare to check for duplicate filenames
        dirpath = os.path.dirname(os.path.realpath(__file__))
        num = 1
        valid_new_filename = False
        new_filename = filename

        # check for dupliate filenames
        for root, _, files in os.walk(dirpath):
            if root == dirpath:
                same_file_names = [file for file in files if testname in file]
                while valid_new_filename == False:
                    new_filename = testname + str(num) + '.json'
                    valid_new_filename = True if new_filename not in same_file_names else False
                    num += 1
                break

        # write data
        with open(new_filename, 'w') as outfile:
            json.dump(self.data, outfile, indent=4, sort_keys=False)

    def hover(self, x, y, z, yaw):
        self.remain_hovering = True
        while self.remain_hovering:
            self.move(x, y, z, yaw, 0.1)
            time.sleep(0.1)

    def land(self, dt=0):
        start_time = time.time()

        self.cf.commander.send_stop_setpoint()
        time.sleep(0.05)
        self.cf.commander.send_notify_setpoint_stop()

        while time.time() - start_time < dt:
            time.sleep(0.1)

    def switch_controller(self, controller):
        if controller in ["Mellinger", "mellinger", "MELLINGER"]:
            self.cf.param.set_value('stabilizer.controller', 2)
        elif controller in ["L1", "l1"]:
            self.cf.param.set_value('stabilizer.controller', 5)
        else:
            print(f"WARNING: controller {controller} is not supported. the controller will not be switched.")

    def set_L1_gains(self, gains):
        self.cf.param.set_value('ctrlL1params.kp_x', gains[0])
        self.cf.param.set_value('ctrlL1params.kp_y', gains[1])
        self.cf.param.set_value('ctrlL1params.kp_z', gains[2])
        self.cf.param.set_value('ctrlL1params.kv_x', gains[3])
        self.cf.param.set_value('ctrlL1params.kv_y', gains[4])
        self.cf.param.set_value('ctrlL1params.kv_z', gains[5])
        self.cf.param.set_value('ctrlL1params.kr_x', gains[6])
        self.cf.param.set_value('ctrlL1params.kr_y', gains[7])
        self.cf.param.set_value('ctrlL1params.kr_z', gains[8])
        self.cf.param.set_value('ctrlL1params.ko_x', gains[9])
        self.cf.param.set_value('ctrlL1params.ko_y', gains[10])
        self.cf.param.set_value('ctrlL1params.ko_z', gains[11])
        self.cf.param.set_value('ctrlL1params.w_f1', gains[12])
        self.cf.param.set_value('ctrlL1params.w_f2', gains[13])
        self.cf.param.set_value('ctrlL1params.w_m1', gains[14])
        self.cf.param.set_value('ctrlL1params.w_m2', gains[15])