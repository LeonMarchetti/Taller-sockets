# coding=utf-8
import errno
from getopt import getopt, GetoptError
from mimetypes import guess_extension, guess_type
import os
from os.path import isfile
from re import match
import signal
import socket
import subprocess
from sys import argv
from time import localtime, strftime


class ConexionTerminadaExcepcion(Exception):
    pass


BUFFER = 1024


def guarderia(signum, frame):
    while True:
        try:
            pid, estado = os.waitpid(
                -1,
                 os.WNOHANG
            )
        except OSError:
            return

        if pid == 0:
            return


def buscar_recurso(recurso):
    # Busco el archivo:
    archivo = 'paginas/' + recurso

    tipo_mime = guess_type(recurso)[0]
    if tipo_mime is None:
        tipo_mime = 'text/plain'

    if isfile(archivo):
        status = 'HTTP/1.0 200 OK\r\n'
    else:
        status = 'HTTP/1.0 404 No encontrado\r\n'
        archivo = 'paginas/no_encontrado' + guess_extension(tipo_mime)

    print('Enviando "{}"'.format(status))

    # Cabeceras de HTTP:
    fecha = 'Date: {}\r\n'.format(strftime('%a, %d %b %Y %H:%M:%S %Z', localtime()))
    tipo_contenido = 'Content-Type: {};charset=utf-8\r\n'.format(tipo_mime)

    # Abro el archivo del recurso
    body = b''
    with open(archivo, 'rb') as f:
        for linea in f:
            body += linea

    # Armo la respuesta:
    return status.encode() + fecha.encode() + tipo_contenido.encode() + b'\r\n' + body


def procesar(pedido):
    # Parseo la primera línea del pedido
    primera_linea = pedido[:pedido.find('\r\n')]

    print('Recibido: "{}"'.format(primera_linea))

    # Busco el recurso y obtengo la respuesta armada
    recurso = match(r'^(GET|POST) \/(.*) HTTP\/(1\.0|1\.1|2\.0)$', primera_linea)
    if recurso:
        #~ return buscar_recurso(recurso[2])
        return buscar_recurso(recurso.group(2)) # Para python < v3.6
    else:
        raise Exception('Regex equivocado')


def enviar(s, datos):
    while datos:
        enviado = s.send(datos)
        if enviado == 0:
            raise ConexionTerminadaExcepcion()
        datos = datos[enviado:]


def recibir(s):
    cachos = []
    while True:
        cacho = s.recv(BUFFER)
        if cacho == b'':
            raise ConexionTerminadaExcepcion()

        f = cacho.find(b'\r\n\r\n')
        if f > -1:
            cachos.append(cacho[:f])
            break
        else:
            cachos.append(cacho)

    return ''.join([cacho.decode() for cacho in cachos])


def server(host, port):
    try:
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((host, port))
        servidor.listen(5)
        print('Escuchando en <{}:{}>'.format(host, port))

        signal.signal(signal.SIGCHLD, guarderia)

        while True:
            print('Esperando conexión...')
            try:
                cliente, direccion = servidor.accept()
            except IOError as e:
                codigo, msg = e.args
                if codigo == errno.EINTR:
                    continue
                else:
                    raise

            pid = os.fork()
            if pid == 0: # hijo
                servidor.close()
                #~ trabajador()

                try:
                    # Recibir pedido:
                    pedido = recibir(cliente)
                    resultado = procesar(pedido)

                    # Enviar resultado:
                    enviar(cliente, resultado)

                except ConexionTerminadaExcepcion:
                    print('Conexión terminada')
                finally:
                    print('Cerrando hijo...')
                    cliente.close()
                    os._exit(0)

            else: # padre
                print('Conexión establecida: <{}:{}> con subproceso <{}>'.format(direccion[0], direccion[1], pid))
                cliente.close()


    except KeyboardInterrupt:
        print('Programa terminado')
    finally:
        servidor.close()


def trabajador():
    pass

def main():
    try:
        # Parámetros de la línea de comandos:
        opts, _ = getopt(argv[1:], 'i:p:')

        # Valores por defecto para host y puerto:
        #~ host = 'localhost'
        host = '192.168.1.42'
        port = 8000

        for opt, arg in opts:
            if opt == '-i':  # Dirección IP
                host = arg
            elif opt == '-p':  # Puerto
                port = int(arg)

        server(host, port)

    except GetoptError:
        print('Error con los parámetros: ' + str(argv))


if __name__ == '__main__':
    main()
