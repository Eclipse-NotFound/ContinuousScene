"""Bounded loopback-only native AIR telemetry capture; no global server or install.

AIR reads the per-user telemetry config. Hold a shared game lease, require the
config absent, create exclusively, and remove only our exact bytes in finally.
Caller owns and cleans its isolated AIR; this receiver cannot stop any process.
"""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import importlib.util
import json
import socket
import threading
import time

HERE=Path(__file__).resolve().parent
CONFIG=Path('C:/Users/hello/.telemetry.cfg')
VENDOR_SHA='5069D8CE17858E2625D3C309EDC17099A6DA6C147AC7612BD9D7DB021E2F20F3'

def save(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

@contextmanager
def capture(folder, max_seconds=180):
    assert 1<=max_seconds<=180 and not CONFIG.exists()
    assert not CONFIG.with_name('telemetry.cfg').exists(),'Existing alternate AIR telemetry config'
    assert not (folder/'native.flm').exists()
    server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server.bind(('127.0.0.1',0));server.listen(1);server.settimeout(.2)
    port=server.getsockname()[1]
    config_bytes=('TelemetryAddress = 127.0.0.1:'+str(port)+'\n').encode('ascii')
    stop=threading.Event();done=threading.Event();connected=threading.Event()
    status=dict(address='127.0.0.1',port=port,config=str(CONFIG),configSHA256=hashlib.sha256(config_bytes).hexdigest().upper(),
                configInitiallyAbsent=True,configCreated=False,configRemoved=False,bytes=0,connections=0,complete=False,errors=[])
    def receive():
        connection=None
        deadline=time.monotonic()+max_seconds
        try:
            while not stop.is_set() and time.monotonic()<deadline:
                try:connection,peer=server.accept();break
                except socket.timeout:continue
            if connection is None:return
            assert peer[0]=='127.0.0.1'
            status.update(peer=list(peer),connections=1);connected.set()
            connection.settimeout(.2)
            with (folder/'native.flm').open('xb') as stream:
                while not stop.is_set() and time.monotonic()<deadline:
                    try:chunk=connection.recv(65536)
                    except socket.timeout:continue
                    except ConnectionResetError:
                        status['transportEnd']='reset';break
                    if not chunk:status['complete']=True;break
                    status['bytes']+=len(chunk)
                    if status['bytes']>128*1024**2:raise RuntimeError('128 MiB capture limit')
                    stream.write(chunk)
                stream.flush()
        except BaseException as error:status['errors'].append(repr(error))
        finally:
            if connection is not None:connection.close()
            done.set()
    worker=threading.Thread(target=receive,name='owned-air-telemetry',daemon=True)
    try:
        with CONFIG.open('xb') as stream:stream.write(config_bytes)
        status['configCreated']=True;save(folder/'capture-status.json',status)
        worker.start()
        yield status
    finally:
        # Only exact content created by this context is removed. A competing edit
        # is retained and reported, never replaced or deleted.
        if status['configCreated']:
            if CONFIG.is_file() and CONFIG.read_bytes()==config_bytes:
                CONFIG.unlink();status['configRemoved']=True
            else:status['errors'].append('Owned telemetry config changed; left untouched')
        if worker.ident is not None:
            done.wait(3);stop.set();worker.join(3)
            if worker.is_alive():status['errors'].append('Receiver did not stop')
        server.close();save(folder/'capture-status.json',status)

def metrics(path):
    source=HERE/'vendor/amf3reader.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest().upper()==VENDOR_SHA
    spec=importlib.util.spec_from_file_location('adobe_amf3reader',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    data=path.read_bytes();assert 0<len(data)<=128*1024**2
    reader=module.amf3reader(data);assert reader.getFormat()=='amfstream'
    result=[];stamp=0
    while reader.pos<len(data):
        before=reader.pos;item=reader.readMetric()
        assert item is not None and reader.pos>before,('Truncated record',before,len(data))
        assert isinstance(item,dict) and isinstance(item.get('name'),str),('Invalid metric',before)
        if 'delta' in item:stamp+=item['delta']
        elif 'time' in item:stamp=item['time']
        item['atUs']=stamp;result.append(item)
        assert len(result)<=2000000,'Metric count limit'
    return result
