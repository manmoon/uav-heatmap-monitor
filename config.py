###############################################################################
# VIDEO CAPTURE CONFIGS
###############################################################################

# Set to 0 to read from the default camera
videoCaptureInputFilename='/Users/mansoor.siddiqui/Workspace/drone/data/stanford_dataset/videos/hyang/video11/video.mov'

# Grab only every xth frame
frameSamplingEnabled=False
frameSamplingInterval=10

# Down-sample the image to the target dimensions
downSamplingEnabled=False
downSamplingSize=(640, 480)

###############################################################################
# ALGO CONFIGS
###############################################################################

# Valid values are 'KNN' or 'MOG2'
bgSubtractionAlgo='KNN'

# Reduce noise in the computed foreground mask
noiseReductionEnabled=True
noiseReductionErosionKernelSize=(8, 8)
noiseReductionDilationKernelSize=(20, 20)

###############################################################################
# RENDERING CONFIGS
###############################################################################

renderInterval=10
renderFrame=False
renderBackground=False
renderForegroundMask=False
renderHeatmap=False
renderBackgroundWithHeatmap=False
renderFrameWithHeatmap=True
