import os,hashlib,hmac,time
import jwt
from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy import select
from .database import session
from .models import User
security=HTTPBearer()
SECRET=os.getenv('JWT_SECRET','change-demo-key')
def hash_password(password):return hashlib.pbkdf2_hmac('sha256',password.encode(),b'dye-atlas-demo',180000).hex()
def issue(user):return jwt.encode({'sub':str(user.id),'role':user.role,'exp':int(time.time())+28800},SECRET,algorithm='HS256')
def current(credentials=Depends(security),db=Depends(session)):
    try:
        token=jwt.decode(credentials.credentials,SECRET,algorithms=['HS256'])
        user=db.get(User,int(token['sub']))
        if not user:raise ValueError()
        return user
    except Exception:raise HTTPException(401,'登录已过期，请重新登录')
def editor(user=Depends(current)):
    if user.role not in ['admin','colorist']:raise HTTPException(403,'观察员不能修改染样或配方')
    return user
def admin(user=Depends(current)):
    if user.role!='admin':raise HTTPException(403,'仅主管可以签批复染')
    return user
