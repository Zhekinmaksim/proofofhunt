import {Config} from '@remotion/cli/config';

// JPEG frames keep the render light on small machines; the output is H.264.
Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(92);
Config.setOverwriteOutput(true);
