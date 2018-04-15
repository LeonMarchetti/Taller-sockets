# coding=utf-8
"""
Parámetros:
* -i Dirección IP o nombre de Host
* -p Número de puerto
"""

import errno
import getopt
import mimetypes
import os
import os.path
import re
import signal
import socket
import subprocess
import sys
import time
# noinspection PyUnresolvedReferences
from urllib.parse import parse_qsl, urlparse


BUFFER = 1024
STATUS = {
    200: 'HTTP/1.0 200 OK\r\n',
    400: 'HTTP/1.1 400 Solicitud Incorrecta\r\n',
    404: 'HTTP/1.0 404 No encontrado\r\n',
}


class ConexionTerminadaExcepcion(Exception):
    pass


# noinspection PyUnusedLocal,PyUnresolvedReferences
def guarderia(signum, frame):
    """When a child process exits, the kernel sends a SIGCHLD signal. The
    parent process can set up a signal handler to be asynchronously notified of
    that SIGCHLD event and then it can wait for the child to collect its
    termination status, thus preventing the zombie process from being left
    around.
    """
    while True:
        try:
            pid, estado = os.waitpid(-1, os.WNOHANG)
        except OSError:
            return

        if pid == 0:
            return


def enviar(s, datos):
    while datos:
        enviado = s.send(datos)
        if enviado == 0:
            raise ConexionTerminadaExcepcion()
        datos = datos[enviado:]


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

    if 'GET' in headers:
        pass

    elif 'POST' in headers:
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
        raise RuntimeError('Método HTTP no soportado')

    # Regreso el método, los encabezados y el cuerpo:
    return headers, cachos


def parsear_header_request(header):
    lista_headers = header.split(b'\r\n')

    # Separo la línea del pedido y obtengo el método:
    request_line = lista_headers.pop(0).decode('ISO-8859-1')
    print(request_line)

    # Parseo el pedido:
    request_line_match = re.match('^(GET|POST|HEAD) \/(.*) HTTP\/\d\.\d$',
                                  request_line)
    request_method = request_line_match.group(1)
    request_uri = request_line_match.group(2)

    # Diccionario con los encabezados
    headers_dict = {request_method: request_uri}

    # Armo el diccionario con los encabezados:
    # headers_dict = {}
    for linea in lista_headers:
        linea_str = linea.decode('ISO-8859-1')
        n = linea_str.find(': ')
        headers_dict[linea_str[:n]] = linea_str[n + 2:]

    return headers_dict


def ejecutar_php(script):
    p = subprocess.Popen('php ' + script, shell=True, stdout=subprocess.PIPE)
    return p.stdout.read()


# noinspection PyUnusedLocal
def buscar_recurso(headers, cuerpo_post):

    if 'GET' in headers:
        u = urlparse(headers['GET'])
        # query = parse_qsl(u.query)

    elif 'POST' in headers:
        u = urlparse(headers['POST'])
        # query = parse_qsl(cuerpo)

    else:
        raise NotImplementedError('Solo se soporta GET y POST...')

    path = 'paginas/' + u.path
    tipo_mime = mimetypes.guess_type(path)[0]

    if os.path.isfile(path):
        status_line = STATUS[200]

    else:
        status_line = STATUS[404]
        path = 'paginas/no_encontrado' + \
               mimetypes.guess_extension(tipo_mime)

    # Abro el archivo del recurso. Si es un script PHP entonces lo ejecuto:
    if os.path.splitext(path)[1] == '.php':
        p = subprocess.Popen('php ' + path, shell=True, stdout=subprocess.PIPE)
        cuerpo = p.stdout.read()
        tipo_mime = 'text/html'

    else:
        cuerpo = b''
        with open(path, 'rb') as f:
            for linea in f:
                cuerpo += linea

    # Cabeceras HTTP:
    fecha = 'Date: {}\r\n'.format(time.strftime('%a, %d %b %Y %H:%M:%S %Z',
                                                time.localtime()))
    tipo_contenido = 'Content-Type: {};charset=utf-8\r\n'.format(tipo_mime)

    return (status_line.encode() +
            fecha.encode() +
            tipo_contenido.encode() +
            b'\r\n' +
            cuerpo)


def servidor(direccion):
    socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_servidor.bind((host, port))
        socket_servidor.listen(5)
        print('Escuchando en <{}:{}>'.format(direccion[0], direccion[1]))

        signal.signal(signal.SIGCHLD, guarderia)

        while True:
            print('--------------------')
            print('Esperando conexión...')
            try:
                socket_cliente, direccion_cliente = socket_servidor.accept()

            except IOError as e:
                codigo, msg = e.args
                if codigo == errno.EINTR:
                    continue

                else:
                    print('Error: {}'.format(msg))
                    raise

            # Forkeo el proceso: El hijo  se encarga de atender al cliente
            pid = os.fork()
            if pid == 0:  # Proceso hijo:
                servidor_hijo(socket_servidor, socket_cliente)

            else:  # Proceso padre:
                socket_cliente.close()

                print('--------------------')
                print('Conexión establecida: ' +
                      '<{}:{}> con subproceso <{}>\n'.format(
                          direccion_cliente[0],
                          direccion_cliente[1],
                          pid))

    except KeyboardInterrupt:
        print('Programa terminado')

    finally:
        socket_servidor.close()


# noinspection PyProtectedMember
def servidor_hijo(socket_servidor, socket_cliente):
    socket_servidor.close()

    try:
        # Recibe pedido y responde:
        headers, cuerpo = recibir_http_request(socket_cliente)
        paquete = buscar_recurso(headers, cuerpo)
        enviar(socket_cliente, paquete)

    except ConexionTerminadaExcepcion:
        print('Conexión terminada')

    finally:
        print('Cerrando hijo...')
        socket_cliente.close()
        os._exit(0)


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

        servidor((host, port))
