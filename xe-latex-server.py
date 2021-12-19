# A simple implementation of a web server support ithoutghts latex.
# Verything based on Texlive/texlive docker.
# set your latex server in ithoughts as: http://localhost:8888/index.php?tex=%TEX%&scale=%SCALE%
# "steal" the code from https://github.com/DMOJ/texoid and change a little on the asynchronous implementation of native coroutines
# first release on 19 December 2021

#-*- coding:utf-8 -*-
import json
import logging
import os
import re
import shutil
import struct
import subprocess
import tempfile
from base64 import b64encode
from urllib.parse import unquote

import tornado.ioloop
import tornado.web
from tornado import gen
from tornado.options import define, options, parse_command_line
from tornado.process import Subprocess

def utf8bytes(maybe_text):
    if maybe_text is None:
        return
    if isinstance(maybe_text, type(b'')):
        return maybe_text
    return maybe_text.encode('utf-8')


def utf8text(maybe_bytes, errors='strict'):
    if maybe_bytes is None:
        return
    if isinstance(maybe_bytes, type(u'')):
        return maybe_bytes
    return maybe_bytes.decode('utf-8', errors)

def latex_validate(latex_str):
    pass

header = struct.Struct('!III')
size_struct = struct.Struct('!I')

redimensions = re.compile(br'.*?(\d+)x(\d+).*?')


class XeLaTeXBackend(object):
    def __init__(self):
        self.latex_path = os.environ.get('LATEX_BIN', '/usr/bin/xelatex')
        self.convert_path = os.environ.get('CONVERT_BIN', '/usr/bin/pdftocairo')

        for path in [self.latex_path, self.convert_path]:
            if not os.path.isfile(path):
                raise RuntimeError('necessary file "%s" is not a file' % path)

    async def render(self, source, scale):
        with XeLaTeXWorker(self) as worker:
            result = await worker.render(source, scale)
        return result


class XeLaTeXWorker(object):
    devnull = open(os.devnull)

    def __init__(self, backend):
        self.backend = backend

    def __enter__(self):
        self.dir = tempfile.mkdtemp()
        return self

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.dir)
        pass

    async def render(self, source, scale):
        # print(f'render: {source}')
        f_name = "render" # 'tex-source'+str(uuid.uuid1())
        f_tex = f_name+".tex"
        f_pdf = f_name+".pdf"
        f_png = f_name+"-1.png"
        
        with open(os.path.join(self.dir, f_tex), 'wb') as f:
            f.write(utf8bytes(source))
        print('save to tex file. start xelatex_to_png()')    
        await self.xelatex_to_pdf(f_tex)
        print('back from xelatex_to_pdf()')
        await self.pdf_to_png(f_pdf)
        png = None
        try:
            with open(os.path.join(self.dir, f_png), 'rb') as f:
                png = f.read()
        except Exception as error:
            print('File png not found. ')
        # f_png = os.path.join(self.dir, f_name + "-1.png")
        return png

    async def xelatex_to_pdf(self, f_tex="render.tex"):
        # print(f'render:{f_tex}')
        print(f'subprocess:{self.backend.latex_path}')
        latex = Subprocess([
            self.backend.latex_path, '-interaction=nonstopmode', f_tex
        ], stdout=Subprocess.STREAM, stderr=subprocess.STDOUT, cwd=self.dir)
        print (f'create pdf subprocess latex:{latex}')
        log = await latex.stdout.read_until_close()
        print('wait pdf subprocess to end.....')
        try:
            await latex.wait_for_exit()
        except subprocess.CalledProcessError:
            # raise RuntimeError('Failed to run latex, full log:\n' + utf8text(log, errors='backslashreplace'))
            print('Failed to run latex, full log:\n' + utf8text(log, errors='backslashreplace'))
        print('subprocess pdf ended. ')

    async def pdf_to_png(self, f_pdf="render.pdf"):
        converter = Subprocess([
            self.backend.convert_path, '-png', '-transp',  f_pdf
        ], stdout=Subprocess.STREAM, stderr=subprocess.STDOUT, cwd=self.dir)
        log = await converter.stdout.read_until_close()
        try:
            await converter.wait_for_exit()
        except subprocess.CalledProcessError:
            # raise RuntimeError('Failed to run latex, full log:\n' + utf8text(log, errors='backslashreplace'))
            print('Failed to run converter, full log:\n' + utf8text(log, errors='backslashreplace'))

class MainHandler(tornado.web.RequestHandler):
    @classmethod
    def with_backend(cls, backend):
        return type('MainHandler', (cls,), {'backend': backend})

    async def post(self):
        print(f'post:{self.request.uri}')
        self.write('unsupported POST method')

    async def get(self):
        print(f'url:{self.request.uri}')
        tex_str = self.get_query_argument('tex')
        scale = self.get_query_argument('scale')
        # print(f'ithouts sending:\n===========================\n{tex_str}\n\n------------------------------\n scale=[{scale}] \n========================================\n')
        png = await self.backend.render(tex_str, scale)
        if png is None:
            png = ''
            # f_png = "2.png"
            # with open(f_png, 'rb') as f:
            #     png = f.read()
        self.write(png)
        self.set_header("Content-type", "image/png")   


def main():
    define('port', default=8888, help='run on the given port', type=int)
    define('address', default='localhost', help='run on the given address', type=str)
    # define('docker', default=False, help='run with docker', type=bool)
    # define('skip_docker_pull', default=False, help='skip pulling latest texbox docker image', type=bool)
    parse_command_line()
    
    backend = XeLaTeXBackend()

    application = tornado.web.Application([
        (r'/index.php', MainHandler.with_backend(backend)),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port) #, address=options.address)
    print(f'Xe-latex-server started on: {options.address}:{options.port}')
    tornado.ioloop.IOLoop.current().start()
    

if __name__ == '__main__':
    main()


