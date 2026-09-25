import {Presentation} from '@oai/artifact-tool';
const p=Presentation.create();
console.log(p.help('*',{search:'slide.shapes.delete|shape.delete|deleteAll',include:['index','examples','notes'],maxChars:12000}).ndjson);
