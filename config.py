import logging


class SinglePointMissionConfig:
    system_address = "udp://:14540"
    target_altitude_meters = 20
    altitude_error_threshold_meters = 0.5
    altitude_arrival_timeout_seconds = 30
    log_level = logging.DEBUG
    log_file = 'heatmap_single_point.log'


class MultiPointMissionConfig:
    system_address = "udp://:14540"
    waypoint_stabilization_time_seconds = 2
    log_level = logging.DEBUG
    log_file = 'heatmap_multi_point.log'


class HeatmapConfig:
    ###########################################################################
    # VIDEO CAPTURE CONFIGS
    ###########################################################################

    # Valid values are 'FILE', 'CAMERA_DIRECT', or 'CAMERA_GSTREAMER'
    video_capture_mode = 'FILE'
    video_capture_time_seconds = 300

    # Set to 0 to read from the default camera
    video_capture_input_filename = '/Users/mansoor.siddiqui/Workspace/drone/data/stanford_dataset/videos/gates5.mov'
    video_capture_gstreamer_pipeline = 'v4l2src ! video/x-raw,width=640,height=480 ! decodebin ! videoconvert ! appsink'

    # Grab camera frames only every x milliseconds; if simulating using input video
    frame_sampling_enabled = True
    frame_sampling_interval_millis = 200

    # Down-sample the image to the target dimensions
    down_sampling_enabled = False
    down_sampling_size = (640, 480)

    ###########################################################################
    # ALGO CONFIGS
    ###########################################################################

    # Valid values are 'KNN' or 'MOG2'
    bg_subtraction_algo = 'KNN'

    # Reduce noise in the computed foreground mask
    noise_reduction_enabled = True
    noise_reduction_erosion_kernel_size = (8, 8)
    noise_reduction_dilation_kernel_size = (20, 20)

    ###########################################################################
    # RENDERING CONFIGS
    ###########################################################################

    # Output live heatmap generation to screen
    render_to_screen = True

    # Save a video of live heatmap generation
    render_to_video = False
    render_video_filename = 'output.avi'
    render_video_fps = 5

    # Flatten heatmap values in the bottom x percent (represented as a decimal) to zero to clean up the output
    render_cutoff_percent = 0.0

    # Scale all values in the heatmap so that they fall between this value and 255; set to zero for no scaling
    render_brighten_threshold = 0

    ###########################################################################
    # LOGGING CONFIGS
    ###########################################################################

    log_level = logging.DEBUG
    log_file = 'heatmap_generator.log'
