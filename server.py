"""Afterglow realtime collaboration server. pip install aiohttp; python server.py"""
import asyncio, json, os
from collections import defaultdict
from aiohttp import web
from pathlib import Path
ROOT=Path(__file__).parent
rooms=defaultdict(lambda:{'strokes':[],'clients':set()})
async def home(request):return web.FileResponse(ROOT/'index.html')
async def websocket(request):
    room=request.query.get('room','demo')[:64];data=rooms[room]
    if len(data['clients'])>=5:return web.Response(status=403,text='Room is full (5 people maximum).')
    ws=web.WebSocketResponse(heartbeat=30);await ws.prepare(request);data['clients'].add(ws)
    await ws.send_json({'type':'init','strokes':data['strokes']})
    async def broadcast(msg):
        for client in list(data['clients']):
            if not client.closed:await client.send_json(msg)
    await broadcast({'type':'presence','count':len(data['clients'])})
    try:
        async for message in ws:
            if message.type!=web.WSMsgType.TEXT:continue
            try:m=json.loads(message.data)
            except json.JSONDecodeError:continue
            if m.get('type')=='stroke':
                s=m.get('stroke',{})
                if not isinstance(s,dict) or len(s.get('points',[]))>15000 or len(data['strokes'])>=3000:continue
                data['strokes'].append(s);await broadcast({'type':'stroke','stroke':s})
            elif m.get('type')=='undo':
                ident=m.get('id');user=request.query.get('user')
                data['strokes'][:]=[s for s in data['strokes'] if not(s.get('id')==ident and s.get('user')==user)]
                await broadcast({'type':'undo','id':ident})
    finally:
        data['clients'].discard(ws);await broadcast({'type':'presence','count':len(data['clients'])})
    return ws
app=web.Application();app.router.add_get('/',home);app.router.add_get('/ws',websocket)
if __name__=='__main__':web.run_app(app,host='0.0.0.0',port=int(os.getenv('PORT','8080')))
