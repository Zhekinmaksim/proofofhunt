import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

// loadFont holds the render until each face is ready, so no frame is ever
// captured in a fallback font. All three are SIL OFL; see public/fonts.
export const fontsReady = Promise.all([
  loadFont({
    family: 'Sofia Sans Extra Condensed',
    url: staticFile('fonts/sofia-sans-extra-condensed.woff2'),
    weight: '1 1000',
  }),
  loadFont({
    family: 'Sofia Sans',
    url: staticFile('fonts/sofia-sans.woff2'),
    weight: '1 1000',
  }),
  loadFont({
    family: 'Martian Mono',
    url: staticFile('fonts/martian-mono.woff2'),
    weight: '100 800',
  }),
]);
