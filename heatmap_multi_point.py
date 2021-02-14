#!/usr/bin/env python3

import asyncio
import logging
import math
import sys
import time

import cv2
from mavsdk import System
from mavsdk.mission import MissionError
from mavsdk.mission import MissionPlan

import heatmap as hm
from config import MultiPointMissionConfig as config

"""
heatmap_multi_point.py

This script waits for a simple waypoint-based mission plan to be uploaded to
the drone. Once a valid mission plan is received, it will have the drone follow
the mission plan. At each waypoint, the script will have the drone pause for a
period of time during which it will build a heatmap to identify busy pedestrian
hotspots on the ground.

The script is intended to be run from a vehicle-based companion computer (e.g.
NavQ) with a camera oriented down towards the ground. Configurations specific
to the management of the drone can be found in config.MultiPointMissionConfig.
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

    logging.info("Waiting for valid mission plan")
    mission = None
    while mission is None:
        try:
            mission_candidate = await drone.mission.download_mission()
            if is_mission_plan_valid(mission_candidate):
                mission = mission_candidate
                break
            else:
                logging.debug(f"Got invalid mission; waiting for a valid mission to be uploaded")
        except MissionError:
            logging.error("Failed to get mission")
        await asyncio.sleep(5)
    mission_string = '\n'.join([str(item) for item in mission.mission_items])
    logging.info(f"Successfully retrieved mission plan:\n{mission_string}")

    logging.info("Waiting for drone to have a global position estimate")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok:
            logging.info("Global position estimate ok")
            break

    logging.info("Fetching launch point")
    async for launch_point in drone.telemetry.home():
        break
    logging.info(f"Launch point: {launch_point}")

    logging.info("-- ARMING")
    await drone.action.arm()

    logging.info("-- STARTING MISSION")
    await drone.mission.start_mission()

    async for mission_progress in drone.mission.mission_progress():
        if mission_progress.current > 0:
            logging.info(f"Reached waypoint {mission_progress.current} of {mission_progress.total}; pausing mission to capture heatmap data")
            await drone.mission.pause_mission()
            await loop.run_in_executor(None, lambda: generate_heatmap(mission_progress, mission.mission_items[mission_progress.current - 1]))
        if mission_progress.current < mission_progress.total:
            logging.info(f"Heading to waypoint {mission_progress.current + 1} of {mission_progress.total}: {mission.mission_items[mission_progress.current]}")
            await drone.mission.start_mission()
        else:
            logging.info(f"All waypoints reached; returning to launch point")
            break

    logging.info("-- RETURNING TO LAUNCH POINT")
    await drone.action.return_to_launch()
    async for in_air in drone.telemetry.in_air():
        if not in_air:
            async for landing_point in drone.telemetry.position():
                break
            logging.info(f"Landed at {landing_point}")
            break

    logging.info("-- TERMINATING")
    await drone.action.terminate()
    sys.exit()


def is_mission_plan_valid(mission_plan: MissionPlan):
    if mission_plan is None:
        return False
    if len(mission_plan.mission_items) == 0:
        return False
    for mission_item in mission_plan.mission_items:
        if math.isnan(mission_item.latitude_deg) or math.isnan(mission_item.longitude_deg) or math.isnan(mission_item.relative_altitude_m):
            return False
    return True


def generate_heatmap(mission_progress, waypoint):
    if config.waypoint_stabilization_time_seconds > 0:
        logging.debug(f"Waiting {config.waypoint_stabilization_time_seconds} seconds for drone to stabilize")
        time.sleep(config.waypoint_stabilization_time_seconds)
    logging.info(f"Generating heatmap {mission_progress.current} of {mission_progress.total} at waypoint: {waypoint}")
    generated_heatmap, generated_bg = hm.generate_heatmap()
    bg_out_file = f"bg_{mission_progress.current}_of_{mission_progress.total}.png"
    heatmap_out_file = f"heatmap_{mission_progress.current}_of_{mission_progress.total}.png"
    logging.info(f"Done generating heatmap {mission_progress.current} of {mission_progress.total}; saving images: {bg_out_file}, {heatmap_out_file}")
    cv2.imwrite(bg_out_file, generated_bg)
    cv2.imwrite(heatmap_out_file, cv2.add(generated_heatmap, generated_bg))


if __name__ == "__main__":
    logging.basicConfig(level=config.log_level, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.FileHandler(config.log_file, "a"), logging.StreamHandler(sys.stdout)])
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
