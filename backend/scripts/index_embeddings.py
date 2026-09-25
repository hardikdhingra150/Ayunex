"""Explicit, bounded paid operation. Index only approved public passages."""
import argparse
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.environment import load_local_env
from app.config import Settings
from app.ai_provider import HostedProvider
from app.hybrid import index_batch,eligible_rows
from datetime import date


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--max-batches',type=int,default=1);args=parser.parse_args()
    if not 1<=args.max_batches<=100:raise SystemExit('Choose 1 to 100 batches')
    load_local_env(Path(__file__).resolve().parents[1]/'.env')
    settings=Settings();engine=create_engine(settings.database_url)
    with Session(engine) as db:
        if not args.execute:
            print({'mode':'DRY_RUN','eligible_sample':len(list(db.execute(eligible_rows('IN',date.today().isoformat()).limit(1000)))),
                   'note':'Use --execute only after reviewing provider terms/costs. At most 16 passages per batch.'})
        else:
            if not all((settings.cloud_processing_allowed,settings.ai_key,settings.embedding_model)):
                raise SystemExit('Configure provider, key, embedding model and cloud processing permission first')
            provider=HostedProvider(settings);count=0
            for _ in range(args.max_batches):
                batch=index_batch(db,provider);db.commit();count+=batch
                if not batch:break
            print({'indexed':count,'model':provider.embedding_model,'private_case_data_sent':False})
