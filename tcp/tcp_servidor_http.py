from time import localtime, strftime
from getopt import getopt, GetoptError
from os.path import isfile
from re import match
import socket
import sys

class ConexionTerminadaExcepcion(Exception):
    pass

# Valores por defecto para host y puerto:
HOST   = 'localhost'
PORT   = 65000
BUFFER = 1024

def buscar_recurso(recurso):
    archivo = 'paginas/' + recurso
    if isfile(archivo):
        status = b'HTTP/1.0 200 OK\r\n'
    else:
        status = b'HTTP/1.0 404 No encontrado\r\n'
        archivo = 'paginas/no_encontrado.html'

    fecha = 'Date: {}\r\n'.format(strftime('%a, %d %b %Y %H:%M:%S %Z', localtime())).encode()
    tipo_contenido = b'Content-Type: text/html;charset=utf-8\r\n'

    html = b''
    with open(archivo, 'rb') as f:
        for linea in f:
            html += linea

    return status + fecha + tipo_contenido + b'\r\n' + html

def procesar(pedido):
    crlf = pedido.find('\r\n')
    primera_linea = pedido[:crlf]
    print('Recibido: "{}"'.format(primera_linea))

    recurso = match(r'^(GET|POST) \/(.*) HTTP\/(1\.0|1\.1|2\.0)$', primera_linea)
    if recurso:
        return buscar_recurso(recurso.group(2))
    else:
        raise Exception('Regex equivocado')

def enviar(s, mensaje):
    try:
        b_mensaje = mensaje.encode()
    except AttributeError:
        b_mensaje = mensaje

    while b_mensaje:
        enviado = s.send(b_mensaje)
        if enviado == 0:
            raise ConexionTerminadaExcepcion()
        b_mensaje = b_mensaje[enviado:]

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

def server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, PORT))
        servidor.listen(5)
        print('Escuchando en <{}:{}>'.format(HOST, PORT))

        try:
            while True:
                print('Esperando conexión...')
                cliente, direccion = servidor.accept()
                print('Conexión establecida: <{}:{}>'.format(direccion[0], direccion[1]))

                try:
                    # Recibir petición:
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

if __name__ == '__main__':
    try:
        # Parámetros de la línea de comandos:
        opts, _ = getopt(sys.argv[1:], 'i:p:')

        for opt, arg in opts:
            if opt == '-i': # Dirección IP
                HOST = arg
            elif opt == '-p': # Puerto
                PORT = int(arg)

        server()

    except GetoptError:
        print('Error con los parámetros: ' + str(sys.argv))