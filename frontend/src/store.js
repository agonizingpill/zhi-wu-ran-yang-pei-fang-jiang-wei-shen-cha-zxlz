import {api} from './api.js';
export const store={recipes:[],swatches:[],trials:[],atlas:null,revisions:[],batches:[],lots:[],issues:[],dispatches:[],complaints:[]};
export async function refresh(){[store.recipes,store.swatches,store.trials,store.revisions,store.batches,store.lots,store.issues,store.dispatches,store.complaints]=await Promise.all([api('/recipes'),api('/swatches'),api('/trials'),api('/revisions'),api('/batches'),api('/dye-lots'),api('/dye-issues'),api('/color-dispatches'),api('/shade-complaints')]);}
