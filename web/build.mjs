import * as esbuild from 'esbuild';
import {createHash} from 'node:crypto';
import path from 'node:path';
await esbuild.build({entryPoints:['client.js'],bundle:true,format:'esm',outfile:'client.bundle.js',minify:true,legalComments:'eof',platform:'browser',target:['es2022']});
const fs=await import('node:fs/promises');
await fs.rm('dist',{recursive:true,force:true});
await fs.mkdir('dist',{recursive:true});
for(const name of ['index.html','play.html','client.bundle.js','config.js','commitment.js','fonts','brand']) await fs.cp(name,`dist/${name}`,{recursive:true});

// Browsers keep a separate favicon cache. A content-derived filename changes
// whenever the artwork changes, including after the next brand regeneration.
const iconPaths = new Map();
for (const name of ['favicon.ico', 'favicon-32.png', 'favicon.svg', 'apple-touch-icon.png']) {
  const bytes = await fs.readFile(`brand/${name}`);
  const hash = createHash('sha256').update(bytes).digest('hex').slice(0, 12);
  const extension = path.extname(name);
  const versioned = `${path.basename(name, extension)}-${hash}${extension}`;
  await fs.writeFile(`dist/brand/${versioned}`, bytes);
  iconPaths.set(`brand/${name}`, `/brand/${versioned}`);
}
for (const name of ['index.html', 'play.html']) {
  let html = await fs.readFile(`dist/${name}`, 'utf8');
  for (const [original, versioned] of iconPaths) {
    html = html.replaceAll(`href="${original}"`, `href="${versioned}"`);
  }
  await fs.writeFile(`dist/${name}`, html);
}
// Default discovery for browsers and tools that request icons at the root.
for (const name of ['favicon.ico', 'favicon.svg']) await fs.cp(`brand/${name}`, `dist/${name}`);
