from datetime import date,datetime,timedelta
from src.fulfillment_models import DyeLot,DyeIssue,ColorDispatch,ShadeComplaint
import math,random
from sqlalchemy import select,func
from src.database import Base,engine,Session
from src.models import User,DyeRecipe,Swatch,Trial
from src.production_models import RecipeRevision,DyeBatch
from src.schedule_models import DyeMachine,ScheduleSlot,ColorChangeRecord
from src.schedule_service import judge_transition,snapshot_of
from src.auth import hash_password

def seed():
    Base.metadata.create_all(engine)
    with Session() as db:
        for role in ['admin','colorist','viewer']:
            email=f'{role}@qise.test'
            if not db.scalar(select(User).where(User.email==email)):db.add(User(email=email,password=hash_password('Dye2026!'),role=role))
        recipes=[('DY-021','靛蓝亚麻',1.8,.4,.2),('DY-022','苔绿棉麻',.3,1.7,.7),('DY-023','赤陶平纹',.8,.3,1.5)]
        for code,name,a,b,c in recipes:
            if not db.scalar(select(DyeRecipe).where(DyeRecipe.code==code)):db.add(DyeRecipe(code=code,name=name,dye_a=a,dye_b=b,dye_c=c))
        db.flush();rr=db.scalars(select(DyeRecipe).order_by(DyeRecipe.id)).all();rng=random.Random(42)
        for i in range(60):
            lot=['REF-021','SAMPLE-021','SAMPLE-OFF'][i] if i<3 else f'SW-{i:03}'
            if db.scalar(select(Swatch).where(Swatch.lot==lot)):continue
            group=0 if i<3 else i%3
            l,a,b=(48,-2,-25) if i==0 else (48.7,-1.5,-24.5) if i==1 else (62,8,-14) if i==2 else (48+group*9+rng.uniform(-2,2),-2+group*6+rng.uniform(-1,1),-25+group*15+rng.uniform(-1,1))
            spectrum=[round(min(.95,max(.03,.26+group*.11+.1*math.sin(j/5+group)+rng.gauss(0,.012))),5) for j in range(36)]
            db.add(Swatch(recipe_id=rr[group].id,lot=lot,spectrum=spectrum,l=l,a=a,b=b,measured=True))
        prod=db.scalar(select(DyeRecipe).where(DyeRecipe.code=='DY-PROD'))
        if not prod:
            prod=DyeRecipe(code='DY-PROD',name='量产靛蓝基准',dye_a=1.8,dye_b=.4,dye_c=.2,locked=True);db.add(prod);db.flush()
        for lot,l,a,b in [('PROD-REF',48,-2,-25),('PROD-OK',48.5,-1.8,-24.8)]:
            if not db.scalar(select(Swatch).where(Swatch.lot==lot)):db.add(Swatch(recipe_id=prod.id,lot=lot,spectrum=[.3]*36,l=l,a=a,b=b))
        db.flush();ref=db.scalar(select(Swatch).where(Swatch.lot=='PROD-REF'));candidate=db.scalar(select(Swatch).where(Swatch.lot=='PROD-OK'))
        trial=db.scalar(select(Trial).where(Trial.recipe_id==prod.id,Trial.state=='approved'))
        if not trial:
            trial=Trial(recipe_id=prod.id,reference_swatch_id=ref.id,candidate_swatch_id=candidate.id,delta_e=.574456,state='approved',note='量产演示基准');db.add(trial);db.flush()
        if not db.scalar(select(DyeBatch).where(DyeBatch.code=='DB-DEMO-001')):db.add(DyeBatch(code='DB-DEMO-001',approved_trial_id=trial.id,kg=250,target_snapshot={'lot':ref.lot,'recipe_id':prod.id,'l':ref.l,'a':ref.a,'b':ref.b,'trial_delta_e':trial.delta_e}))
        for code,component,kg,expiry,state in [('DYE-A-1117','A',80,date(2027,12,31),'active'),('DYE-B-1117','B',40,date(2027,12,31),'active'),('DYE-C-1117','C',20,date(2027,12,31),'active'),('DYE-C-HOLD','C',5,date(2027,12,31),'quarantine'),('DYE-B-OLD','B',5,date(2026,1,1),'active')]:
            if not db.scalar(select(DyeLot).where(DyeLot.code==code)):db.add(DyeLot(code=code,component=component,available_kg=kg,expires_on=expiry,state=state))
        db.flush();seed_schedule(db)
        db.commit()
        print({name:db.scalar(select(func.count()).select_from(model)) for name,model in [('users',User),('recipes',DyeRecipe),('swatches',Swatch)]})

def seed_schedule(db):
    # 排产换色演示：染机、历史换色证据与一条待排队列；重复 seed 只补缺项。
    machines={}
    for code,name in [('M1','高温溢流染机'),('M2','常温卷染机'),('M3','气流染色机')]:
        m=db.scalar(select(DyeMachine).where(DyeMachine.code==code))
        if not m:m=DyeMachine(code=code,name=name);db.add(m);db.flush()
        machines[code]=m
    db.flush()
    recipes={r.code:r for r in db.scalars(select(DyeRecipe)).all()}
    history=[('M1','DY-021','DY-PROD',False,.9,'靛蓝系免洗直换，首测合格'),('M1','DY-PROD','DY-021',False,1.4,'同色系回换免洗合格'),('M1','DY-021','DY-022',False,4.3,'深靛蓝免洗接苔绿串色超差'),('M1','DY-023','DY-021',True,.6,'清洗后换色合格'),('M2','DY-022','DY-023',False,2.1,'卷染机免洗换色合格')]
    existing=db.scalars(select(ColorChangeRecord)).all()
    for m_code,prev_code,next_code,washed,delta_e,note in history:
        if any(x.machine_id==machines[m_code].id and x.prev_snapshot['code']==prev_code and x.next_snapshot['code']==next_code and x.washed==washed and abs(x.first_delta_e-delta_e)<1e-6 for x in existing):continue
        db.add(ColorChangeRecord(machine_id=machines[m_code].id,prev_snapshot=snapshot_of(recipes[prev_code]),next_snapshot=snapshot_of(recipes[next_code]),washed=washed,first_delta_e=delta_e,source='manual',note=note,recorded_by='seed'))
    db.flush()
    m1=machines['M1']
    if not db.scalar(select(ScheduleSlot).where(ScheduleSlot.code=='Q-1101')):
        done=datetime.utcnow()-timedelta(hours=20)
        db.add(ScheduleSlot(machine_id=m1.id,code='Q-1101',recipe_id=recipes['DY-021'].id,recipe_snapshot=snapshot_of(recipes['DY-021']),kg=300,seq=1,state='completed',started_at=done-timedelta(hours=8),completed_at=done,created_by='seed'))
        db.flush()
    queue=[('Q-1102','DY-PROD',400,2),('Q-1103','DY-023',350,3)]
    for code,recipe_code,kg,seq in queue:
        if db.scalar(select(ScheduleSlot).where(ScheduleSlot.code==code)):continue
        slot=ScheduleSlot(machine_id=m1.id,code=code,recipe_id=recipes[recipe_code].id,recipe_snapshot=snapshot_of(recipes[recipe_code]),kg=kg,seq=seq,created_by='seed')
        db.add(slot);db.flush()
        pred=db.scalar(select(ScheduleSlot).where(ScheduleSlot.machine_id==m1.id,ScheduleSlot.seq<slot.seq).order_by(ScheduleSlot.seq.desc()).limit(1))
        j=judge_transition(db,m1.id,pred.recipe_snapshot if pred else None,slot.recipe_snapshot)
        j['prev_slot_id']=pred.id if pred else None;j['prev_code']=pred.code if pred else None;j['slot_id']=slot.id
        slot.judgment=j;slot.inspection_reserved=bool(j.get('inspection'))
    db.flush()
if __name__=='__main__':seed()
