import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

def calculate_atlas(samples):
    if len(samples)<3:raise ValueError('至少需要三个已测量染样')
    values=np.array([s['spectrum'] for s in samples],dtype=float)
    scaler=StandardScaler();scaled=scaler.fit_transform(values)
    pca=PCA(n_components=2,svd_solver='full',random_state=42)
    projected=pca.fit_transform(scaled)
    reconstructed=pca.inverse_transform(projected)
    return {'explained_variance':pca.explained_variance_ratio_.tolist(),'reconstruction_mse':float(np.mean((scaled-reconstructed)**2)),
            'points':[{'id':s['id'],'lot':s['lot'],'recipe_id':s['recipe_id'],'x':float(v[0]),'y':float(v[1])} for s,v in zip(samples,projected)],
            'count':len(samples),'method':'StandardScaler → PCA / svd_solver=full / random_state=42'}
