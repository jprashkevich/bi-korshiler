import {Config} from '@remotion/cli/config';

// Единые настройки рендера. Изменяйте только если понимаете зачем.
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setPublicDir('./public');
// Качество финального mp4 (crf 18 = высокое, подходит для Instagram)
Config.setCrf(18);
