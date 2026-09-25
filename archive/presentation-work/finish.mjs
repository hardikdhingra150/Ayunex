import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const root='/Users/hardik/Desktop/SIH (Moa_26045)';
const p=await PresentationFile.importPptx(await FileBlob.load(root+'/output/26045_SIH_NAUT_IQ_Updated.pptx'));
for(let i=0;i<8;i++)await fs.writeFile(`${root}/.ppt_revision/final-${i+1}.png`,new Uint8Array(await(await p.slides.items[i].export({format:'png',scale:1})).arrayBuffer()));
console.log('Rendered final eight slides');
