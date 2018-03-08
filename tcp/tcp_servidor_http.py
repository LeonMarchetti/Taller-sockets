# coding=utf-8
from getopt import getopt, GetoptError
from mimetypes import guess_extension, guess_type
from os.path import isfile
from re import match
import socket
from sys import argv
from time import localtime, strftime


class ConexionTerminadaExcepcion(Exception):
    pass


BUFFER = 1024


def buscar_recurso(recurso):
    # Busco el archivo:
    archivo = 'paginas/' + recurso
    tipo_mime = guess_type(recurso)[0]
    if isfile(archivo):
        status = 'HTTP/1.0 200 OK\r\n'
    else:
        status = 'HTTP/1.0 404 No encontrado\r\n'
        archivo = 'paginas/no_encontrado' + guess_extension(tipo_mime)

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
        return buscar_recurso(recurso[2])
        # return buscar_recurso(recurso.group(2)) # Para Python < v3.6
    else:
        raise Exception('Regex equivocado')


def enviar(s, datos):
    while datos:
        enviado = s.send(datos)
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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((host, port))
        servidor.listen(5)
        print('Escuchando en <{}:{}>'.format(host, port))

        try:
            while True:
                print('Esperando conexión...')
                cliente, direccion = servidor.accept()
                print('Conexión establecida: <{}:{}>'.format(direccion[0], direccion[1]))

                try:
                    # Recibir pedido:
                    pedido = recibir(cliente)
                    resultado = procesar(pedido)

                    # Enviar resultado:
                    enviar(cliente, resultado)

                except ConexionTerminadaExcepcion:
                    print('Conexión terminada')
                finally:
                    cliente.close()

        except KeyboardInterrupt:
            print('Programa terminado')


def main():
    try:
        # Parámetros de la línea de comandos:
        opts, _ = getopt(argv[1:], 'i:p:')

        # Valores por defecto para host y puerto:
        host = 'localhost'
        port = '65000'

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
