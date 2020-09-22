from __future__ import print_function
import cv2 as cv
import argparse
import numpy as np

parser = argparse.ArgumentParser(description='This program shows how to use background subtraction methods provided by \
                                              OpenCV. You can process both videos and images.')
parser.add_argument('--input', type=str, help='Path to a video or a sequence of image.', default='vtest.avi')
parser.add_argument('--algo', type=str, help='Background subtraction method (KNN, MOG2).', default='MOG2')
args = parser.parse_args()
if args.algo == 'MOG2':
    backSub = cv.createBackgroundSubtractorMOG2()
else:
    backSub = cv.createBackgroundSubtractorKNN()

# capture = cv.VideoCapture(cv.samples.findFileOrKeep(args.input))
# capture = cv.VideoCapture(0)
capture = cv.VideoCapture('/Users/mansoor.siddiqui/Workspace/drone/data/stanford_dataset/videos/bookstore/video1/video.mov')

if not capture.isOpened:
    print('Unable to open: ' + args.input)
    exit(0)

heatmap = None

while True:
    ret, frame = capture.read()

    # TODO: We can probably afford to grab every Xth (e.g. 10th) frame to save on computation.
    # TODO: Downsample image to save on computation.
    # frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_AREA)

    if frame is None:
        break

    fgMask = backSub.apply(frame)
    bg = backSub.getBackgroundImage()

    # We do this to reduce noise and merge/emphasize the relevant parts of the foreground mask. See:
    # https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_imgproc/py_morphological_ops/py_morphological_ops.html
    erosionKernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (8, 8))
    fgMask = cv.erode(fgMask, erosionKernel)
    dilationKernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (20, 20))
    fgMask = cv.dilate(fgMask, dilationKernel)

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
    if heatmap.max() > 0:
        renderedHeatmap -= renderedHeatmap.min()
        renderedHeatmap = 255 * renderedHeatmap / renderedHeatmap.max()
    renderedHeatmap = renderedHeatmap.astype('uint8')
    renderedHeatmap = cv.applyColorMap(renderedHeatmap, cv.COLORMAP_HOT)

    # cv.imshow('Frame', frame)
    # cv.imshow('BG', bg)
    # cv.imshow('FG Mask', fgMask)
    # cv.imshow('heatmap', renderedHeatmap)
    # bgWithHeatmap = cv.add(renderedHeatmap, bg)
    # cv.imshow('BG with heatmap', bgWithHeatmap)

    # Take the averaged background image and superimpose the heatmap over it.
    frameWithHeatmap = cv.add(renderedHeatmap, frame)
    cv.imshow('Frame with heatmap', frameWithHeatmap)

    keyboard = cv.waitKey(30)
    if keyboard == 'q' or keyboard == 27:
        break
