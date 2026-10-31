import {Config} from '@remotion/cli/config';

// Remotion 4 otherwise defaults to full-range JPEG color, which some players shift.
Config.setColorSpace('bt709');
Config.setPixelFormat('yuv420p');
