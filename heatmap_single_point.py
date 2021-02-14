#!/usr/bin/env python3

import asyncio
import logging
import math
import sys
import time

import cv2
from mavsdk import System

import heatmap as hm
from config import SinglePointMissionConfig as config

"""
heatmap_single_point.py

This script launches a drone to a specific altitude, then scans the ground (via
a connected camera) for a period of time, building a heatmap to identify busy
pedestrian hotspots on the ground.

The script is intended to be run from a vehicle-based companion computer (e.g.
NavQ) with a camera oriented down towards the ground. Configurations specific
to the management of the drone can be found in config.SinglePointMissionConfig.
Configurations relating to the heatmap generation component of this workflow
can be found in config.HeatmapGenerator.
"""


async def run():
    drone = System()

    logging.info(f"Waiting for drone connection on {config.system_address}")
    await drone.connect(system_address=config.system_address)
    async for state in drone.core.connection_state():
        if state.is_connected:
            logging.info(f"Drone discovered with UUID: {state.uuid}")
            break

    logging.info("Waiting for drone to have a global position estimate")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok:
            logging.info("Global position estimate ok")
            break

    logging.info("Fetching amsl altitude at home location")
    async for home_position in drone.telemetry.home():
        break
    logging.info(f"Home position: {home_position}")

    logging.info("-- ARMING")
    await drone.action.arm()

    logging.info("-- TAKING OFF")
    takeoff_altitude = await drone.action.get_takeoff_altitude()
    await drone.action.takeoff()
    success = await arrive_at_target_altitude(drone, takeoff_altitude)
    if not success:
        logging.error(f"Failed to takeoff to relative altitude of {takeoff_altitude}m; aborting...")
        await land_and_exit(drone)

    logging.info(f"Flying to altitude of {config.target_altitude_meters}m")
    target_absolute_altitude = home_position.absolute_altitude_m + config.target_altitude_meters
    await drone.action.goto_location(home_position.latitude_deg, home_position.longitude_deg, target_absolute_altitude, 0)
    success = await arrive_at_target_altitude(drone, config.target_altitude_meters)
    if not success:
        logging.error(f"Failed to fly to relative altitude of {config.target_altitude_meters}m; aborting...")
        await land_and_exit(drone)

    logging.info("Arrived at target altitude")
    await loop.run_in_executor(None, generate_heatmap)
    await land_and_exit(drone)


async def arrive_at_target_altitude(drone, target_relative_altitude):
    logging.info(f"Waiting to arrive at relative altitude of {target_relative_altitude}m")
    altitude_error_threshold = config.altitude_error_threshold_meters / 2
    in_position = False
    start_time_ns = time.time_ns()
    while not in_position:
        async for position in drone.telemetry.position():
            logging.info(position)
            break
        in_position = target_relative_altitude - altitude_error_threshold < position.relative_altitude_m < target_relative_altitude + altitude_error_threshold
        timed_out = time.time_ns() - start_time_ns > 1e9 * config.altitude_arrival_timeout_seconds
        if in_position or timed_out:
            break
        await asyncio.sleep(1)
    return in_position


async def land_and_exit(drone):
    logging.info("-- LANDING")
    await drone.action.land()
    await arrive_at_target_altitude(drone, 0)
    logging.info("-- TERMINATING")
    await drone.action.terminate()
    sys.exit()


def generate_heatmap():
    logging.info("Generating heatmap")
    generated_heatmap, generated_bg = hm.generate_heatmap()
    ts_millis = math.floor(1e3 * time.time())
    logging.info(f"Done generating heatmap; saving images: bg_{ts_millis}.png, heatmap_{ts_millis}.png")
    cv2.imwrite(f'bg_{ts_millis}.png', generated_bg)
    cv2.imwrite(f'heatmap_{ts_millis}.png', cv2.add(generated_heatmap, generated_bg))


if __name__ == "__main__":
    logging.basicConfig(level=config.log_level, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.FileHandler(config.log_file, "a"), logging.StreamHandler(sys.stdout)])
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
