import os,json,uuid,time,logging
from contextlib import asynccontextmanager
from fastapi import FastAPI,Depends,HTTPException,Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select,text
from sqlalchemy.exc import IntegrityError
import redis
from .database import session,engine,Base
from .models import User,DyeRecipe,Swatch,Trial,Audit
from .schemas import Login,RecipeInput,SwatchInput,TrialInput
from .auth import current,editor,admin,hash_password,issue
from . import recipe_service as svc
from .production_routes import router as production_router
from .fulfillment_routes import router as fulfillment_router
queue=redis.Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    if os.getenv('SEED_DEMO','true').lower()=='true':
        try:
            from scripts.seed_demo import seed
            seed()
        except Exception:logging.exception('seed failed')
    yield
app=FastAPI(title='栖色染样图谱',lifespan=lifespan)
app.include_router(production_router)
app.include_router(fulfillment_router)
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:18220'],allow_methods=['*'],allow_headers=['*'])
@app.middleware('http')
async def request_trace(request:Request,call_next):
    started=time.monotonic();response=await call_next(request)
    response.headers['X-Elapsed-Ms']=str(round((time.monotonic()-started)*1000,2));return response
@app.middleware('http')
async def guard_errors(request:Request,call_next):
    try:return await call_next(request)
    except IntegrityError:return JSONResponse({'detail':'数据关联或唯一性冲突，请刷新后重试'},409)
    except Exception:
        logging.exception('request failure');return JSONResponse({'detail':'服务暂时无法完成操作，请重试'},500)
@app.get('/health')
def health(db=Depends(session)):
    db.execute(text('SELECT 1'));queue.ping();return {'status':'ok'}
@app.post('/auth/login')
def login(body:Login,db=Depends(session)):
    user=db.scalar(select(User).where(User.email==body.email))
    if not user or user.password!=hash_password(body.password):raise HTTPException(401,'邮箱或密码错误')
    return {'token':issue(user),'email':user.email,'role':user.role}
@app.get('/recipes')
def recipes(user=Depends(current),db=Depends(session)):return db.scalars(select(DyeRecipe).order_by(DyeRecipe.id)).all()
@app.post('/recipes')
def create_recipe(body:RecipeInput,user=Depends(editor),db=Depends(session)):return svc.save_recipe(db,body,user)
@app.put('/recipes/{key}')
def edit_recipe(key:int,body:RecipeInput,user=Depends(editor),db=Depends(session)):return svc.save_recipe(db,body,user,key)
@app.get('/swatches')
def swatches(user=Depends(current),db=Depends(session)):return db.scalars(select(Swatch).order_by(Swatch.id)).all()
@app.post('/swatches')
def create_swatch(body:SwatchInput,user=Depends(editor),db=Depends(session)):return svc.create_swatch(db,body,user)
@app.post('/atlas')
def atlas(user=Depends(editor)):
    jobid=uuid.uuid4().hex;queue.set('atlas:result:'+jobid,json.dumps({'state':'queued'}),ex=86400);queue.rpush('atlas:queue',jobid);return {'job_id':jobid}
@app.get('/atlas/{jobid}')
def atlas_result(jobid:str,user=Depends(current)):
    value=queue.get('atlas:result:'+jobid)
    if not value:raise HTTPException(404,'图谱任务已过期，请重新生成')
    return json.loads(value)
@app.get('/trials')
def trials(user=Depends(current),db=Depends(session)):return db.scalars(select(Trial).order_by(Trial.id.desc())).all()
@app.post('/trials')
def create_trial(body:TrialInput,user=Depends(editor),db=Depends(session)):return svc.create_trial(db,body,user)
@app.post('/trials/{key}/verify')
def verify(key:int,user=Depends(editor),db=Depends(session)):return svc.transition(db,key,'verify',user)
@app.post('/trials/{key}/approve')
def approve(key:int,user=Depends(admin),db=Depends(session)):return svc.transition(db,key,'approve',user)
@app.get('/audits')
def audits(user=Depends(current),db=Depends(session)):return db.scalars(select(Audit).order_by(Audit.id.desc()).limit(50)).all()
