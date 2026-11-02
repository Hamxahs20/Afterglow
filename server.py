"""Afterglow realtime collaboration server. pip install aiohttp; python server.py"""
import json, os
from collections import defaultdict
from pathlib import Path
from aiohttp import web
ROOT=Path(__file__).parent
rooms=defaultdict(lambda:{'strokes':[],'clients':{}})
async def home(request): return web.FileResponse(ROOT/'index.html')
async def websocket(request):
    room=request.query.get('room','demo')[:64]; data=rooms[room]
    if len(data['clients'])>=5:return web.Response(status=403,text='Room is full (5 people maximum).')
    ws=web.WebSocketResponse(heartbeat=30); await ws.prepare(request)
    uid=request.query.get('user','')[:80]
    name=request.query.get('name','Friend').strip()[:24] or 'Friend'
    data['clients'][ws]={'id':uid,'name':name}
    await ws.send_json({'type':'init','strokes':data['strokes']})
    async def broadcast(msg):
        for client in list(data['clients']):
            if not client.closed: await client.send_json(msg)
    async def presence():
        await broadcast({'type':'presence','people':list(data['clients'].values()),'count':len(data['clients'])})
    await presence()
    try:
        async for message in ws:
            if message.type!=web.WSMsgType.TEXT:continue
            try:m=json.loads(message.data)
            except (json.JSONDecodeError,ValueError):continue
            if m.get('type')=='stroke':
                s=m.get('stroke',{})
                if not isinstance(s,dict) or not isinstance(s.get('points'),list) or len(s['points'])>15000 or len(data['strokes'])>=3000:continue
                s['user']=uid
                data['strokes'].append(s);await broadcast({'type':'stroke','stroke':s})
            elif m.get('type')=='undo':
                ident=m.get('id');data['strokes'][:]=[s for s in data['strokes'] if not(s.get('id')==ident and s.get('user')==uid)]
                await broadcast({'type':'undo','id':ident})
            elif m.get('type')=='finished':
                await broadcast({'type':'finished','user':uid,'name':name})
    finally:
        data['clients'].pop(ws,None);await presence()
    return ws
app=web.Application();app.router.add_get('/',home);app.router.add_get('/ws',websocket)
if __name__=='__main__':web.run_app(app,host='0.0.0.0',port=int(os.getenv('PORT','8080')))
