# -*- coding: utf-8 -*-
"""
Parámetros:
* -i Dirección IP o nombre de Host
* -p Número de puerto
"""
import fnmatch
import getopt
import mimetypes
import os.path
import re
from servidor_fork import ServidorFork
import subprocess
import sys
import time
# noinspection PyUnresolvedReferences
from urllib.parse import parse_qsl, urlparse


STATUS = {
    200: 'HTTP/1.0 200 OK\r\n',
    400: 'HTTP/1.0 400 Bad Request\r\n',
    404: 'HTTP/1.0 404 Not Found\r\n',
    406: 'HTTP/1.0 406 Not Acceptable\r\n',
}


class ConexionTerminadaExcepcion(Exception):
    pass


def parsear_header_request(header_completo):
    lista_headers = header_completo.split(b'\r\n')

    # Separo la línea del pedido y obtengo el método:
    request_line = lista_headers.pop(0).decode('ISO-8859-1')
    print('[{0}] {1}'.format(os.getpid(), request_line))

    # Parseo el pedido:
    request_line_match = re.match('^(GET|POST|HEAD) \/(.*) HTTP\/\d\.\d$',
                                  request_line)
    request_method = request_line_match.group(1)
    request_uri = request_line_match.group(2)

    # Diccionario con los encabezados
    headers_dict = {'Request-Method': request_method,
                    'Request-URI': request_uri}

    # Armo el diccionario con los encabezados:
    for linea in lista_headers:
        linea_str = linea.decode('ISO-8859-1')
        n = linea_str.find(': ')
        headers_dict[linea_str[:n]] = linea_str[n + 2:]

    return headers_dict


def recibir_http_request(s):
    # Primero recibo el header:
    cachos = b''
    f = -1
    while f == -1:
        cacho = s.recv(1024)
        if cacho:
            cachos += cacho
            f = cachos.find(b'\r\n\r\n')

        else:
            raise ConexionTerminadaExcepcion

    # Proceso el header:
    headers = parsear_header_request(cachos[:f])
    cachos = cachos[f+4:]

    if headers['Request-Method'] in ('GET', 'HEAD'):
        pass

    elif headers['Request-Method'] == 'POST':
        # Si el mensaje trae la longitud del contenido entonces recibo tantos
        # bytes como indique el encabezado:
        if 'Content-Length' in headers:
            content_length = int(headers['Content-Length'])
            while len(cachos) < content_length:
                cacho = s.recv(1024)
                if cacho:
                    cachos += cacho
                else:
                    raise ConexionTerminadaExcepcion

        else:
            # Si el mensaje no trae la longitud del contenido entonces recibo
            # bytes hasta que se termine la conexión:
            while True:
                cacho = s.recv(1024)
                if cacho:
                    cachos += cacho
                else:
                    break

    else:
        raise NotImplementedError('Solo se soporta GET, HEAD y POST...')

    # Regreso el método, los encabezados y el cuerpo:
    return headers, cachos


def ejecutar_php(script):
    p = subprocess.Popen('php ' + script,
                         shell=True,
                         stdout=subprocess.PIPE)
    return p.stdout.read() + p.stderr.read()


def verificar_aceptacion_tipo(accept, tipo_mime):
    accept_matches = re.findall(r'(\w+\/(?:\w+|\*))', accept)
    if accept_matches:
        for accept_tipo in accept_matches:
            if fnmatch.fnmatch(tipo_mime, accept_tipo):
                return True

    return False


# noinspection PyUnusedLocal
def buscar_recurso(headers_pedido, cuerpo_pedido):

    header_solo = False

    # Parseo el pedido:
    if headers_pedido['Request-Method'] == 'GET':
        u = urlparse(headers_pedido['Request-URI'])
        # query = parse_qsl(u.query)

    elif headers_pedido['Request-Method'] == 'POST':
        u = urlparse(headers_pedido['Request-URI'])
        # query = parse_qsl(cuerpo_pedido)

    elif headers_pedido['Request-Method'] == 'HEAD':
        u = urlparse(headers_pedido['Request-URI'])
        header_solo = True

    else:
        raise NotImplementedError('Solo se soporta GET, HEAD y POST...')

    archivo = 'paginas/' + u.path
    if archivo == 'paginas/':
        archivo = 'paginas/pagina1.html'

    tipo_mime = mimetypes.guess_type(archivo)[0]

    # Verifico si el cliente acepta el tipo de contenido:
    if 'Accept' in headers_pedido and \
       not verificar_aceptacion_tipo(headers_pedido['Accept'], tipo_mime):

        status_line = STATUS[406]
        cuerpo = tipo_mime

    else:
        # Verifico si existe el recurso pedido:
        if os.path.isfile(archivo):
            status_line = STATUS[200]

        else:
            status_line = STATUS[404]
            archivo = 'paginas/no_encontrado' + \
                      mimetypes.guess_extension(tipo_mime)

        if header_solo:
            cuerpo = b''

        else:
            # Abro el archivo del recurso. Si es un script PHP entonces lo
            # ejecuto:
            if os.path.splitext(archivo)[1] == '.php':
                p = subprocess.Popen('php ' + archivo,
                                     shell=True,
                                     stdout=subprocess.PIPE)
                cuerpo = p.stdout.read()

            else:
                cuerpo = b''
                if archivo != '':
                    with open(archivo, 'rb') as f:
                        for linea in f:
                            cuerpo += linea

    # Cabeceras HTTP:
    fecha = 'Date: {}\r\n'.format(time.strftime('%a, %d %b %Y %H:%M:%S %Z',
                                                time.localtime()))
    tipo_contenido = 'Content-Type: {};charset=utf-8\r\n'.format(tipo_mime)

    print('[{0}] {1}'.format(os.getpid(), status_line.strip()))

    # Armado y retorno del paquete:
    return (status_line.encode() +
            fecha.encode() +
            tipo_contenido.encode() +
            b'\r\n' +
            cuerpo)


def proceso(socket_cliente):
    headers, cuerpo = recibir_http_request(socket_cliente)
    salida = buscar_recurso(headers, cuerpo)
    return salida


if __name__ == '__main__':
    # Parámetros de la línea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'i:p:')
    except getopt.GetoptError as error:
        print('Error con el parámetro {0.opt}: {0.msg}'.format(error))
    else:
        # Parámetros por defecto para host y puerto:
        host = 'localhost'
        port = 8080
        modo = ''

        for opt, arg in opts:
            if opt == '-i':  # Dirección IP
                host = arg
            elif opt == '-p':  # Puerto
                port = int(arg)

        ServidorFork((host, port), proceso)
