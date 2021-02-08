#!/usr/bin/env python3

import math
import time

import cv2
import numpy as np

from config import HeatmapConfig as config


class _CaptureContext:
    capture: cv2.VideoCapture
    is_live: bool
    _cutoff_time_ns: int  # Used only if is_live is True
    _cutoff_frame: int  # Used only if is_live is False
    _num_frames_read = 0
    _last_capture_time_ns = 0

    def __init__(self):

        # Initialize the video stream
        if config.video_capture_mode == 'FILE':
            self.capture = cv2.VideoCapture(config.video_capture_input_filename)
            self.is_live = False
        elif config.video_capture_mode == 'CAMERA_GSTREAMER':
            self.capture = cv2.VideoCapture(config.video_capture_gstreamer_pipeline, cv2.CAP_GSTREAMER)
            self.is_live = True
        else:
            self.capture = cv2.VideoCapture(0)
            self.is_live = True
        if not self.capture.isOpened():
            print('Unable to open video capture')
            raise IOError

        # If capturing a live stream, stop capturing after the configured amount of time has passed. If capturing from
        # a video file, stop capturing after hitting the appropriate frame.
        if self.is_live:
            self._cutoff_time_ns = time.time_ns() + 1e9 * config.video_capture_time_seconds
        else:
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            self._cutoff_frame = fps * config.video_capture_time_seconds

    def read(self):
        success, frame = self.capture.read()
        if success:
            self._num_frames_read += 1
            self._last_capture_time_ns = time.time_ns()
        return success, frame

    def is_expired(self):
        if not self.capture.isOpened():
            return True
        if self.is_live:
            return time.time_ns() >= self._cutoff_time_ns
        else:
            return self._num_frames_read >= self._cutoff_frame

    def sleep_until_time_to_read(self):
        if not config.frame_sampling_enabled:
            return
        next_sample_time_ns = self._last_capture_time_ns + 1e6 * config.frame_sampling_interval_millis
        time_to_sleep_seconds = 1e-9 * (next_sample_time_ns - time.time_ns())
        if time_to_sleep_seconds <= 0:
            return
        if self.is_live:
            time.sleep(time_to_sleep_seconds)
        else:
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            frames_to_skip = math.ceil(fps * time_to_sleep_seconds)
            for x in range(0, frames_to_skip):
                self.read()

    def close(self):
        if self.capture.isOpened():
            self.capture.release()


class _RenderContext:
    output: cv2.VideoWriter = None

    def __init__(self, capture: cv2.VideoCapture):
        if config.render_to_video:
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) if not config.down_sampling_enabled else config.down_sampling_size[0]
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) if not config.down_sampling_enabled else config.down_sampling_size[1]
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.output = cv2.VideoWriter(config.render_video_filename, fourcc, config.render_video_fps, (width, height))
            if not self.output.isOpened():
                print("Unable to open video file for writing: ", config.render_video_filename)

    def render(self, frame, heatmap):
        frame_with_heatmap = None
        if config.render_to_screen or config.render_to_video:
            rendered_heatmap = _scale_heatmap_for_rendering(heatmap)
            frame_with_heatmap = cv2.add(rendered_heatmap, frame)
        if config.render_to_screen:
            cv2.imshow('Frame with heatmap', frame_with_heatmap)
            cv2.waitKey(1)
        if config.render_to_video and self.output.isOpened():
            self.output.write(frame_with_heatmap)

    def close(self):
        cv2.destroyAllWindows()
        if self.output is not None and self.output.isOpened():
            self.output.release()


def _scale_heatmap_for_rendering(heatmap):
    # The heatmap values are float64's. Scale the values appropriately to uint8's to make it suitable for rendering.
    rendered_heatmap = heatmap.copy()
    rendered_heatmap -= rendered_heatmap.min()
    if rendered_heatmap.max() > 0:
        rendered_heatmap = 255 * rendered_heatmap / rendered_heatmap.max()
    rendered_heatmap = rendered_heatmap.astype('uint8')
    rendered_heatmap = cv2.applyColorMap(rendered_heatmap, cv2.COLORMAP_HOT)
    return rendered_heatmap


def generate_heatmap():
    capture_context = _CaptureContext()
    render_context = _RenderContext(capture_context.capture)

    bg_subtractor = cv2.createBackgroundSubtractorMOG2() if config.bg_subtraction_algo == 'MOG2' else cv2.createBackgroundSubtractorKNN()
    heatmap = None

    while not capture_context.is_expired():

        success, frame = capture_context.read()
        if not success:
            break

        # Down-sample the image to the target dimensions
        if config.down_sampling_enabled:
            frame = cv2.resize(frame, config.down_sampling_size, interpolation=cv2.INTER_AREA)

        # Incorporate the current frame into our averaged background and get the updated foreground mask
        fg_mask = bg_subtractor.apply(frame)
        fg_mask[fg_mask > 0] = 255  # People often seem to get detected as shadows (i.e. 127), so round up to 255
        bg = bg_subtractor.getBackgroundImage()

        # We do this to reduce noise and merge/emphasize the relevant parts of the foreground mask. See:
        # https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_imgproc/py_morphological_ops/py_morphological_ops.html
        if config.noise_reduction_enabled:
            erosion_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, config.noise_reduction_erosion_kernel_size)
            fg_mask = cv2.erode(fg_mask, erosion_kernel)
            dilation_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, config.noise_reduction_dilation_kernel_size)
            fg_mask = cv2.dilate(fg_mask, dilation_kernel)

        # Update the heatmap
        if heatmap is None:
            heatmap = np.zeros(fg_mask.shape, 'float64')
        heatmap += fg_mask

        # TODO: The erosion/dilation above removes noise but might still yield clusters of circles that represent a single
        #       person. From here, we can apply that directly to the heatmap, or we can try clustering blobs to recognize
        #       unique people, then applying their centroid+radius to the heatmap. We might get cleaner results, but it
        #       would probably be more computationally intensive. This stackoverflow answer shows how the dbscan clustering
        #       algorithm can be used to achieve this: https://stackoverflow.com/a/23997322/477451

        render_context.render(frame, heatmap)
        capture_context.sleep_until_time_to_read()

    capture_context.close()
    render_context.close()

    rendered_heatmap = _scale_heatmap_for_rendering(heatmap)
    return rendered_heatmap, bg


if __name__ == "__main__":
    heatmap, bg = generate_heatmap()
    cv2.imwrite('bg.png', bg)
    cv2.imwrite('heatmap.png', cv2.add(heatmap, bg))
