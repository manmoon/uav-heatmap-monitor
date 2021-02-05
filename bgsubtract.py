import cv2
import numpy as np

import config

backSub = cv2.createBackgroundSubtractorMOG2() if config.bgSubtractionAlgo == 'MOG2' else cv2.createBackgroundSubtractorKNN()
capture = cv2.VideoCapture(config.videoCaptureInputFilename)

if not capture.isOpened:
    print('Unable to open: ' + config.videoCaptureInputFilename)
    exit(0)

heatmap = None
skippedFrames = 0

while True:
    ret, frame = capture.read()

    # Grab only every xth frame
    if config.frameSamplingEnabled and skippedFrames < config.frameSamplingInterval:
        skippedFrames += 1
        continue

    # Down-sample the image to the target dimensions
    if config.downSamplingEnabled:
        cv2.resize(frame, config.downSamplingSize, interpolation=cv2.INTER_AREA)

    # Encorporate the current frame into our averaged background and get the updated foreground mask
    fgMask = backSub.apply(frame)
    fgMask[fgMask > 0] = 255  # People often seem to get detected as shadows (i.e. 127), so round up to 255
    bg = backSub.getBackgroundImage()

    # We do this to reduce noise and merge/emphasize the relevant parts of the foreground mask. See:
    # https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_imgproc/py_morphological_ops/py_morphological_ops.html
    if config.noiseReductionEnabled:
        erosionKernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, config.noiseReductionErosionKernelSize)
        fgMask = cv2.erode(fgMask, erosionKernel)
        dilationKernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, config.noiseReductionDilationKernelSize)
        fgMask = cv2.dilate(fgMask, dilationKernel)

    # Update the heatmap
    if heatmap is None:
        heatmap = np.zeros(fgMask.shape, 'float64')
    heatmap += fgMask

    # TODO: The erosion/dilation above removes noise but might still yield clusters of circles that represent a single
    #       person. From here, we can apply that directly to the heatmap, or we can try clustering blobs to recognize
    #       unique people, then applying their centroid+radius to the heatmap. We might get cleaner results, but it
    #       would probably be more computationally intensive. This stackoverflow answer shows how the dbscan clustering
    #       algorithm can be used to achieve this: https://stackoverflow.com/a/23997322/477451

    # The heatmap values are float64's. Scale the values appropriately to uint8's to make it suitable for rendering.
    renderedHeatmap = heatmap.copy()
    renderedHeatmap -= renderedHeatmap.min()
    if renderedHeatmap.max() > 0:
        renderedHeatmap = 255 * renderedHeatmap / renderedHeatmap.max()
    renderedHeatmap = renderedHeatmap.astype('uint8')
    renderedHeatmap = cv2.applyColorMap(renderedHeatmap, cv2.COLORMAP_HOT)

    if config.renderFrame:
        cv2.imshow('Frame', frame)
    if config.renderBackground:
        cv2.imshow('BG', bg)
    if config.renderForegroundMask:
        cv2.imshow('FG Mask', fgMask)
    if config.renderHeatmap:
        cv2.imshow('heatmap', renderedHeatmap)
    if config.renderBackgroundWithHeatmap:
        bgWithHeatmap = cv2.add(renderedHeatmap, bg)
        cv2.imshow('BG with heatmap', bgWithHeatmap)
    if config.renderFrameWithHeatmap:
        frameWithHeatmap = cv2.add(renderedHeatmap, frame)
        cv2.imshow('Frame with heatmap', frameWithHeatmap)

    keyboard = cv2.waitKey(30)
    if keyboard == 'q' or keyboard == 27:
        break
