import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
let esbuild; try {esbuild=require('esbuild')} catch {esbuild=require('../video/node_modules/esbuild')}
await esbuild.build({entryPoints:['client.js'],bundle:true,format:'esm',outfile:'client.bundle.js',minify:true,legalComments:'eof',nodePaths:['../scripts/node_modules'],platform:'browser',target:['es2022']});
const fs=await import('node:fs/promises');
await fs.rm('dist',{recursive:true,force:true});
await fs.mkdir('dist',{recursive:true});
for(const name of ['index.html','play.html','client.bundle.js','config.js','commitment.js','fonts','brand']) await fs.cp(name,`dist/${name}`,{recursive:true});
