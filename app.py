import os, json, re
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)
API_URL = os.getenv('TELE68_API_URL', 'https://wtxmd52.tele68.com/v1/txmd5/lite-sessions')
API_TOKEN = os.getenv('TELE68_AT', '')
MAX_HISTORY = 50
TIMEZONE = os.getenv('APP_TIMEZONE', 'Asia/Ho_Chi_Minh')


def tai_xiu(d1, d2, d3):
    return 'Xỉu' if d1 + d2 + d3 <= 10 else 'Tài'

# Exact special combinations from the supplied algorithm file.
BANG_TRA = {
  3:{'result':'Xỉu','percent':80,'note':'111 - trừ khi sún soi'},
  4:{'result':'Xỉu','percent':70,'note':''},
  5:{'result':'Xỉu','percent':70,'note':'113,122,131...'},
  6:{'special':{'123':'Tài','114':'Tài','132':'Tài','213':'Tài','222':'Xỉu','411':'Xỉu'}},
  7:{'special':{'124':{'result':'Tài','percent':89},'133':{'result':'Tài','percent':89},'331':{'result':'Tài','percent':89},'223':'Xỉu','232':'Xỉu','115':'Xỉu','151':'Xỉu','511':'Xỉu','241':'Xỉu'}},
  8:{'special':{'134':'Tài','224':'Tài','323':'Tài','116':'Xỉu','125':'Xỉu','233':'Xỉu','143':'Xỉu','251':'Xỉu','512':'Xỉu','611':'Xỉu','431':'Xỉu'}},
  9:{'special':{'126':'Tài','135':'Tài','144':'Tài','333':'Tài','225':'Xỉu','234':'Xỉu','261':'Xỉu','252':'Xỉu','315':'Xỉu','153':'Xỉu'}},
  10:{'special':{'136':'Tài','145':'Tài','244':'Tài','343':'Tài','226':'Xỉu','235':'Xỉu','334':'Xỉu','163':'Xỉu','316':'Xỉu','424':'Xỉu','613':'Xỉu','451':'Xỉu'}},
  11:{'special':{'236':'Tài','344':'Tài','434':'Tài','632':'Xỉu','263':'Xỉu','326':'Xỉu','155':'Xỉu','461':'Xỉu','146':'Xỉu','614':'Xỉu','452':'Xỉu','254':'Xỉu','353':'Xỉu','533':'Xỉu'}},
  12:{'special':{'156':'Tài','255':'Tài','336':'Tài','345':'Tài','246':'Auto Xỉu','444':'Auto Xỉu','651':'Tài','561':'Tài','165':'Tài','516':'Tài','615':'Tài','552':'Tài','354':'Tài','543':'Tài','633':'Tài','363':'Tài','426':'Tài','624':'Tài'}},
  13:{'special':{'346':'Tài','355':'Tài','445':'Tài','166':'Xỉu','256':'Xỉu'}},
  14:{'special':{'356':'Tài','455':'Tài','266':'Xỉu','446':'Xỉu','554':'Xỉu'}},
  15:{'special':{'456':'Tài','555':'Tài','366':'Xỉu','465':'Xỉu'}},
  16:{'special':{'556':'Xỉu','466':'Xỉu','664':'Tài','646':'Tài'}},
  17:{'special':{'566':'Tài'}}, 18:{'special':{'666':'BỎ'}}
}

def tra_bang_tong(d1,d2,d3):
    total=d1+d2+d3; key=''.join(map(str, sorted([d1,d2,d3])))
    if total == 18: return {'result':'BỎ','percent':0,'note':'666'}
    entry=BANG_TRA.get(total)
    if not entry: return None
    if 'special' in entry:
        match=entry['special'].get(key) or entry['special'].get(f'{d1}{d2}{d3}')
        if match is None: return None
        if isinstance(match,dict): return match
        if match == 'Auto Xỉu': return {'result':'Xỉu','percent':90,'note':'Auto'}
        if match == 'BỎ': return {'result':'BỎ','percent':0,'note':'666'}
        return {'result':match,'percent':75,'note':''}
    return entry

def as_int(v):
    try:
        if v is None or isinstance(v,bool): return None
        return int(float(v))
    except (ValueError,TypeError): return None

def get_first(d, keys):
    if not isinstance(d,dict): return None
    for k in keys:
        if k in d and d[k] is not None: return d[k]
    return None

def flatten_records(obj):
    """Find session-like objects in common API envelope shapes."""
    found=[]
    def walk(x, depth=0):
        if depth > 8: return
        if isinstance(x,dict):
            if any(k in x for k in ('phien','session','session_id','round','round_id','issue','period','resultTruyenThong')):
                found.append(x)
            for v in x.values():
                if isinstance(v,(dict,list)): walk(v,depth+1)
        elif isinstance(x,list):
            for v in x: walk(v,depth+1)
    walk(obj)
    # de-duplicate object references / identical session IDs
    out=[]; seen=set()
    for r in found:
        sid=get_first(r,['phien','session','session_id','round','round_id','issue','period','id'])
        key=str(sid) if sid is not None else json.dumps(r,sort_keys=True,ensure_ascii=False,default=str)
        if key not in seen: seen.add(key); out.append(r)
    return out

def normalize_record(r):
    sid=get_first(r,['phien','session','session_id','round','round_id','issue','period','id'])
    dice=get_first(r,['xuc_xac','dice','dices','dice_result','diceResults','dice_results','result_dice'])
    d1=as_int(get_first(r,['xuc_xac_1','dice1','dice_1','d1']))
    d2=as_int(get_first(r,['xuc_xac_2','dice2','dice_2','d2']))
    d3=as_int(get_first(r,['xuc_xac_3','dice3','dice_3','d3']))
    if isinstance(dice,dict):
        d1=d1 if d1 is not None else as_int(get_first(dice,['1','dice1','d1','x1']))
        d2=d2 if d2 is not None else as_int(get_first(dice,['2','dice2','d2','x2']))
        d3=d3 if d3 is not None else as_int(get_first(dice,['3','dice3','d3','x3']))
    elif isinstance(dice,(list,tuple)) and len(dice)>=3:
        d1=d1 if d1 is not None else as_int(dice[0]); d2=d2 if d2 is not None else as_int(dice[1]); d3=d3 if d3 is not None else as_int(dice[2])
    total=as_int(get_first(r,['tong','total','sum','dice_sum','point']))
    if total is None and None not in (d1,d2,d3): total=d1+d2+d3
    result=get_first(r,['ket_qua','result','resultTruyenThong','outcome','tai_xiu','tx','label'])
    if isinstance(result,dict): result=get_first(result,['name','label','result','outcome'])
    if isinstance(result,str):
        low=result.strip().lower()
        if low in ('tai','tài','big','over'): result='Tài'
        elif low in ('xiu','xỉu','small','under'): result='Xỉu'
        else: result=None
    if result is None and total is not None and 3 <= total <= 18: result=tai_xiu(d1,d2,d3) if None not in (d1,d2,d3) else ('Xỉu' if total<=10 else 'Tài')
    return {'phien':sid,'ket_qua':result,'tong':total,'xuc_xac_1':d1,'xuc_xac_2':d2,'xuc_xac_3':d3,'trang_thai':get_first(r,['trang_thai','status','state'])}

def normalize_history(payload):
    records=flatten_records(payload)
    history=[]
    for r in records:
        n=normalize_record(r)
        if n['ket_qua'] in ('Tài','Xỉu') and n['tong'] is not None:
            history.append(n)
    # APIs usually return newest first; sort descending by numeric session when possible.
    try: history.sort(key=lambda x:int(x['phien']),reverse=True)
    except (ValueError,TypeError): pass
    return history[:MAX_HISTORY]

def nhan_dien_cau(history):
    if len(history)<3:return None
    seq=[h['ket_qua'] for h in history]; ts=[h['tong'] for h in history]
    if (seq[:3]==['Tài','Xỉu','Tài'] or seq[:3]==['Xỉu','Tài','Xỉu']) and any(t in (9,10,7) for t in ts[:3]):
        return {'result':'Xỉu' if seq[0]=='Tài' else 'Tài','confidence':80,'reason':'Cầu 3 trắng đen + 9-10-7'}
    if len(ts)>=4 and (ts[:4]==[10,11,10,11] or ts[:4]==[8,9,8,9]):
        return {'result':'Xỉu' if seq[0]=='Tài' else 'Tài','confidence':80,'reason':'Cầu lặp 10-11 hoặc 8-9'}
    if ts[:3]==[12,8,12]: return {'result':'Xỉu','confidence':99,'reason':'Cầu 12-8-12 auto bẻ X10'}
    if ts[:3]==[7,12,7]: return {'result':'Xỉu','confidence':85,'reason':'Cầu 7-12-7'}
    if len(ts)>=7 and all(ts[i]==8 for i in (0,2,4,6)): return {'result':'Xỉu','confidence':90,'reason':'Cầu 8 xen kẽ auto bẻ Xỉu'}
    if len(seq)>=5 and seq[1]==seq[2]==seq[3] and seq[0]!=seq[1] and all(11<=t<=14 for t in ts[1:4]):
        return {'result':'Xỉu' if seq[0]=='Tài' else 'Tài','confidence':61,'reason':'Cầu bệt 11-14 + con mới'}
    if seq[0]==seq[1]==seq[2]: return {'result':'Xỉu' if seq[0]=='Tài' else 'Tài','confidence':65,'reason':'3 trắng/3 đen bẻ nhẹ'}
    if sorted(ts[:3],reverse=True)==[5,4,3]: return {'result':'BỎ','confidence':0,'reason':'Cầu 5-4-3 đứt'}
    return None

def markov(seq,order):
    transitions={}
    for i in range(len(seq)-order):
        key=tuple(seq[i:i+order]); nxt=seq[i+order]
        transitions.setdefault(key,{'Tài':0,'Xỉu':0})[nxt]+=1
    state=tuple(seq[:order])
    counts={'Tài':0.5,'Xỉu':0.5}
    if state in transitions:
        n=sum(transitions[state].values())
        if n: counts={k:transitions[state][k]/n for k in ('Tài','Xỉu')}
    return counts

def patterns(seq):
    scores={'Tài':0.5,'Xỉu':0.5}; plen=3
    if len(seq)<plen+2:return scores
    current=''.join(seq[:plen]); a=b=total=0
    for i in range(plen,len(seq)-1):
        if ''.join(seq[i-plen:i])==current:
            if seq[i]=='Tài':a+=1
            elif seq[i]=='Xỉu':b+=1
            total+=1
    if total:scores={'Tài':a/total,'Xỉu':b/total}
    return scores

def analyze_tong(ts):
    if len(ts)<3:return {'Tài':0.5,'Xỉu':0.5}
    inc=sum(ts[i]>ts[i-1] for i in range(1,len(ts))); dec=sum(ts[i]<ts[i-1] for i in range(1,len(ts)))
    if inc>dec:return {'Tài':0.7,'Xỉu':0.3}
    if dec>inc:return {'Tài':0.3,'Xỉu':0.7}
    tai=0.6 if sum(ts)/len(ts)>10.5 else 0.4
    return {'Tài':tai,'Xỉu':1-tai}

def cycles(seq):
    scores={'Tài':0.5,'Xỉu':0.5}
    if len(seq)<6:return scores
    best_cycle=0; best_corr=0
    for c in range(2,min(10,len(seq)//2)+1):
        total=len(seq)-c; matches=sum(seq[i]==seq[i+c] for i in range(total)); corr=matches/total if total else 0
        if corr>best_corr:best_corr=corr;best_cycle=c
    if best_cycle and best_corr>0.6:
        pred=seq[len(seq)-best_cycle]
        scores={'Tài':0.8,'Xỉu':0.2} if pred=='Tài' else {'Tài':0.2,'Xỉu':0.8}
    return scores

def predict(history,last_n=15):
    if len(history)<3:return {'result':'Chưa có dữ liệu','confidence':0,'reason':'Thiếu dữ liệu'}
    try: hour=datetime.now(ZoneInfo(TIMEZONE)).hour
    except Exception: hour=datetime.now().hour
    if 0<=hour<5:return {'result':'TÀI/XỈU','confidence':0,'reason':'Khung giờ không áp dụng (0h-5h)'}
    cau=nhan_dien_cau(history)
    if cau:
        if cau['result']!='BỎ': return cau
        return cau
    seq=[h['ket_qua'] for h in history]; ts=[h['tong'] for h in history]
    recent=seq[:min(last_n,len(seq))]; rt=ts[:min(last_n,len(ts))]
    f={'Tài':recent.count('Tài')/len(recent),'Xỉu':recent.count('Xỉu')/len(recent)}
    m2=markov(seq,2);m3=markov(seq,3);m={k:m2[k]*0.4+m3[k]*0.6 for k in ('Tài','Xỉu')}
    p=patterns(seq); t=analyze_tong(rt); c=cycles(seq)
    score={k:f[k]*.15+m[k]*.25+p[k]*.25+t[k]*.15+c[k]*.20 for k in ('Tài','Xỉu')}
    diff=abs(score['Tài']-score['Xỉu'])
    if diff<.08:
        last3=recent[:3]
        if last3.count('Tài')>last3.count('Xỉu'):return {'result':'Tài','confidence':55,'reason':'Trend 3 phiên'}
        if last3.count('Xỉu')>last3.count('Tài'):return {'result':'Xỉu','confidence':55,'reason':'Trend 3 phiên'}
        return {'result':'Tài' if recent.count('Tài')>=recent.count('Xỉu') else 'Xỉu','confidence':52,'reason':'Tần suất tổng'}
    return {'result':max(score,key=score.get),'confidence':min(round(max(score.values())*100),95),'reason':'Tổng hợp đa thuật toán'}

def fetch_api():
    if not API_TOKEN:
        raise RuntimeError('Thiếu biến môi trường TELE68_AT trên Render')
    r=requests.get(API_URL,params={'cp':'R','cl':'R','pf':'web','at':API_TOKEN},timeout=15,headers={'Accept':'application/json','User-Agent':'AUZA/1.0'})
    r.raise_for_status()
    return r.json()

def make_response(payload):
    history=normalize_history(payload)
    prediction=predict(history)
    # TELE68 list is newest-first: latest is the most recent completed round.
    latest=history[0] if history else {}
    try: next_session=int(latest.get('phien'))+1 if latest.get('phien') is not None else None
    except (TypeError,ValueError): next_session=None
    tai=sum(x['ket_qua']=='Tài' for x in history); xiu=sum(x['ket_qua']=='Xỉu' for x in history); n=len(history)
    # Streak metrics are based on consecutive actual Tài/Xỉu outcomes, newest first.
    outcomes=[x['ket_qua'] for x in history]
    current_side=outcomes[0] if outcomes else None
    current_streak=0
    for outcome in outcomes:
        if outcome != current_side: break
        current_streak += 1
    longest={'Tài':0,'Xỉu':0}; run_side=None; run_len=0
    for outcome in reversed(outcomes):
        if outcome == run_side: run_len += 1
        else:
            run_side=outcome; run_len=1
        longest[run_side]=max(longest[run_side],run_len)
    data={
      'id':'@tiendataox','game':'LC79 MD5',
      'phien_truoc':latest.get('phien'), 'xuc_xac1':latest.get('xuc_xac_1',0) or 0,'xuc_xac2':latest.get('xuc_xac_2',0) or 0,'xuc_xac3':latest.get('xuc_xac_3',0) or 0,
      'phien_nay':next_session, 'du_doan':prediction['result'],
      'do_tin_cay':f"{prediction['confidence']:.1f}%", 'thong_ke':{'thang':tai,'thua':xiu,'tong':n,'ti_le_thang':f"{(tai/n*100 if n else 0):.1f}%",'chuoi_thang_hien_tai':current_streak if current_side=='Tài' else 0,'chuoi_thua_hien_tai':current_streak if current_side=='Xỉu' else 0,'chuoi_thang_dai_nhat':longest['Tài'],'chuoi_thua_dai_nhat':longest['Xỉu']},
      'lich_su':[{'phien':h.get('phien'),'du_doan':h.get('ket_qua'),'ket_qua':h.get('ket_qua'),'tong':h.get('tong'),'xuc_xac':[h.get('xuc_xac_1'),h.get('xuc_xac_2'),h.get('xuc_xac_3')],'trang_thai':h.get('trang_thai') or 'đã có kết quả'} for h in history],
      'trang_thai':'ok' if history else 'khong_co_du_lieu','ly_do':prediction.get('reason'),'nguon':'TELE68 lite-sessions'
    }
    if not history: data['canh_bao']='API đã trả lời nhưng backend chưa nhận diện được cấu trúc lịch sử phiên.'
    return data

@app.get('/')
def index():
    return jsonify({'service':'AUZA LC79 MD5 API','status':'online','endpoints':['/api/predict','/health']})

@app.get('/health')
def health(): return jsonify({'status':'ok'})

@app.get('/api/predict')
def api_predict():
    try:
        payload=fetch_api()
        return jsonify(make_response(payload))
    except requests.HTTPError as e:
        code=e.response.status_code if e.response is not None else 502
        return jsonify({'trang_thai':'api_error','error':'TELE68 trả về lỗi HTTP','http_status':code}),502
    except requests.RequestException as e:
        return jsonify({'trang_thai':'api_error','error':'Không kết nối được API TELE68','detail':str(e)}),502
    except (ValueError,RuntimeError) as e:
        return jsonify({'trang_thai':'config_error','error':str(e)}),503
    except Exception as e:
        app.logger.exception('prediction failed')
        return jsonify({'trang_thai':'server_error','error':'Lỗi xử lý dữ liệu','detail':str(e)}),500

@app.get('/api/raw')
def api_raw():
    """Diagnostic endpoint; avoid exposing this publicly in production."""
    try: return jsonify(fetch_api())
    except Exception as e: return jsonify({'error':str(e)}),502

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
