import {spawn} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
const backend=fileURLToPath(new URL('../backend/',import.meta.url))
const python=path.join(backend,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python')
const tasks={test:['-m','pytest','-q'],provider:['-m','scripts.provider_check'],evaluate:['-m','scripts.evaluate_knowledge'],index:['-m','scripts.index_embeddings'],reparse:['-m','scripts.reparse_corpus'],corpus:['-m','scripts.ingest_corpus'],openapi:['-m','scripts.export_openapi'],migrate:['-m','alembic','upgrade','head']}
const command=tasks[process.argv[2]]
if(!command){console.error('Choose test, evaluate, corpus, openapi or migrate');process.exit(1)}
const child=spawn(python,[...command,...process.argv.slice(3)],{cwd:backend,stdio:'inherit',env:process.env})
child.on('error',()=>{console.error('Backend virtual environment is unavailable. See backend/README.md.');process.exitCode=1})
child.on('exit',code=>{process.exitCode=code??1})
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>child.kill(signal))
