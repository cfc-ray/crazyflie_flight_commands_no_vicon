import logging
import time
import cflib.crtp

from simple_client import SimpleClient, HEIGHT

# which drone to use
URI = 'radio://0/11/2M/E7E7E7E701'


# test specifics
test_duration = 10  # seconds

hover_x = 0.
hover_y = 0.
hover_z = HEIGHT
hover_yaw = 0.


variables = [
    # position, in mm
    'stateEstimateZ.x',
    'stateEstimateZ.y',
    'stateEstimateZ.z',

    # velocity, in mm/s
    'stateEstimateZ.vx',
    'stateEstimateZ.vy',
    'stateEstimateZ.vz',

    # orientation, deg (including legacy CF2 body coordinate system where pitch is inverted)
    'stateEstimate.roll',
    'stateEstimate.pitch',
    'stateEstimate.yaw',

    # angular velocity, milliradians / sec
    'stateEstimateZ.rateRoll',
    'stateEstimateZ.ratePitch',
    'stateEstimateZ.rateYaw',
]


def main():
    # setup 
    logging.basicConfig(level=logging.ERROR)
    cflib.crtp.init_drivers()

    # Create and start the client that will connect to the drone
    client = SimpleClient(URI, log_variables=variables)
    while not client.is_connected:
        print(f' ... connecting ...')
        time.sleep(1.0)

    # Leave time at the start to initialize
    client.stop(1.0)

    # reset state estimate and set controller to Mellinger
    client.cf.param.set_value('kalman.resetEstimation', 1)
    client.switch_controller("mellinger")

    # pause to finish initialization
    time.sleep(0.1)


    # -------------------------------------------------------------------------------------------
    # takeoff
    print('\ntakeoff...')
    client.move_smooth([0., 0., 0.],  [0., 0., 0.1], 0., 0.5)
    client.move_smooth([0., 0., 0.1], [hover_x, hover_y, HEIGHT], hover_yaw, 2.0)
    time.sleep(0.1)

    # hover
    print('hover...')
    start_time = time.time()
    while time.time() - start_time < test_duration:
        client.move(0., 0., HEIGHT, 0., 0.1)


    # land
    print('\nlanding...\n')
    client.move_smooth([0., 0., HEIGHT], [0., 0., 0.1], 0., 1.0)
    client.move(0., 0., 0.1, 0., 0.5)
    client.land()

    # Disconnect from drone
    client.disconnect()


    # Write data from flight
    client.write_data('tuning_data.json')

    # -------------------------------------------------------------------------------------------


if __name__ == '__main__':
    main()