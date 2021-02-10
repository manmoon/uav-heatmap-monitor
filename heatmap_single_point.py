#!/usr/bin/env python3

import asyncio

from mavsdk import System

from config import SinglePointMissionConfig as config
import heatmap as hm
import cv2
import time

async def run():
    drone = System()
    await drone.connect(system_address="udp://:14540")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"Drone discovered with UUID: {state.uuid}")
            break

    print("Waiting for drone to have a global position estimate...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok:
            print("Global position estimate ok")
            break

    print("Fetching amsl altitude at home location....")
    async for home_position in drone.telemetry.home():
        home_altitude = home_position.absolute_altitude_m
        home_latitude = home_position.latitude_deg
        home_longitude = home_position.longitude_deg
        break




    print("-- Arming")
    await drone.action.arm()

    print("-- Taking off")
    await drone.action.takeoff()

    await asyncio.sleep(1)

    print("-- DONE SLEEPIN")

    print("home_altitude=", home_altitude)
    print("home_latitude=", home_latitude)
    print("home_longitude=", home_longitude)
    target_altitude = home_altitude + config.target_altitude_meters
    await drone.action.goto_location(home_latitude, home_longitude, target_altitude, 0)


    in_position = False
    departure_time_ns = time.time_ns()
    while not in_position and time.time_ns() - departure_time_ns < 1e9 * config.target_altitude_timeout_seconds:
        async for current_position in drone.telemetry.position():
            current_altitude = current_position.absolute_altitude_m
            break
        print("CURRENT ALTITUDE =", current_altitude, "m")
        if current_altitude < target_altitude - 0.5:
            await asyncio.sleep(1)
        else:
            print("IN POSITION!!")
            in_position = True
            break



    print("-- DONE GOIN 2 LOCATIONZZZ")

    generated_heatmap, generated_bg = hm.generate_heatmap()
    cv2.imwrite('bg.png', generated_bg)
    cv2.imwrite('heatmap.png', cv2.add(generated_heatmap, generated_bg))

    print ("-- Landing")
    await drone.action.land()

    print("-- ALL DONE SON")

    await drone.action.terminate()

async def is_in_position(drone: System):

    async for position in drone.telemetry.position():
        current_altitude = position.absolute_altitude_m




if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
