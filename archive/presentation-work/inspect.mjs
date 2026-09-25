import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('/Users/hardik/Desktop/26045_SIH_NAUT IQ.pptx'));
const snap=await p.inspect({kind:'slide,textbox,shape,image,layout',maxChars:150000});
await fs.writeFile(new URL('source.ndjson',import.meta.url),snap.ndjson);
console.log('Slides',p.slides.items.length,'masters',p.masters.items.length);
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.items[i];
 await fs.writeFile(new URL(`source-${i+1}.png`,import.meta.url),new Uint8Array(await (await s.export({format:'png',scale:1})).arrayBuffer()));
 await fs.writeFile(new URL(`source-${i+1}.json`,import.meta.url),await (await s.export({format:'layout'})).text());
}
