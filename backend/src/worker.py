import os,time,json,traceback
from pathlib import Path
import redis
from sqlalchemy import select
from .database import Session
from .models import Swatch
from .atlas import calculate_atlas
queue=redis.Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
while True:
    Path('/tmp/worker-heartbeat').touch()
    job=queue.blpop('atlas:queue',timeout=3)
    if not job:continue
    jobid=job[1]
    try:
        with Session() as db:
            swatches=db.scalars(select(Swatch).where(Swatch.measured==True)).all()
            result=calculate_atlas([{'id':s.id,'lot':s.lot,'recipe_id':s.recipe_id,'spectrum':s.spectrum} for s in swatches])
        Path('/artifacts').mkdir(exist_ok=True)
        Path(f'/artifacts/{jobid}.json').write_text(json.dumps(result))
        queue.set('atlas:result:'+jobid,json.dumps({'state':'done','result':result}),ex=86400)
    except Exception as e:
        queue.set('atlas:result:'+jobid,json.dumps({'state':'failed','error':str(e)}),ex=86400)
        traceback.print_exc()
