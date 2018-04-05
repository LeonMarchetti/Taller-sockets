# _*_ coding: utf-8 _*_
import getopt
import random
import socket
import sys
import time

"""

Estructura:
Longitud , 1 byte
ID       , 1 byte
timestamp, 4 bytes
mensaje  , variable

"""

BUFFER = 1024
ID = 0


class ConexionTerminadaExcepcion(Exception):
    pass


def enviar(s, mensaje, _id):
    longitud = len(mensaje)
    ts = round(time.time())

    paquete = (longitud.to_bytes(1, 'big') +
               _id.to_bytes(4, 'big') +
               ts.to_bytes(4, 'big') +
               mensaje)

    while paquete:
        enviado = s.send(paquete)
        if enviado == 0:
            raise socket.error()
        paquete = paquete[enviado:]


def recibir(s):
    cachos = b''
    i = 0
    while True:
        cacho = s.recv(BUFFER)
        if cacho:
            cachos += cacho
            longitud = int.from_bytes(cachos[i:i+1], 'big')
            if len(cachos) + 1 >= longitud:
                break
            # if len(cachos) + 1 == longitud:
            #     break
            # elif len(cachos) + 1 > longitud:
            #     i = longitud

        else:
            raise ConexionTerminadaExcepcion

    return cachos


def servidor(direccion):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_servidor:

        socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_servidor.bind(direccion)
        socket_servidor.listen(5)
        print('Escuchando en <{}:{}>'.format(direccion[0], direccion[1]))

        while True:  # Ciclo que acepta las conexiones (un cliente a la vez)
            print('Esperando conexión...')
            socket_cliente, direccion = socket_servidor.accept()
            print('Conexión establecida: <{}:{}>'.format(direccion[0],
                                                         direccion[1]))
            try:
                while True:
                    # Recibir mensaje:
                    procesar(recibir(socket_cliente))

                    # Enviar mensaje:
                    mensaje = input('> ')
                    if mensaje:
                        enviar(socket_cliente, mensaje.encode(), 0)
                    else:  # Cortar el chat si se ingresa un mensaje vacio:
                        print('Chat terminado')
                        break

            except ConexionTerminadaExcepcion:
                print('Chat terminado')

            finally:
                socket_cliente.close()

            print('--------------------')


def cliente(direccion):
    _id = random.randint(1, 255)
    print('Cliente con id: "{}"'.format(_id))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_servidor:
        socket_servidor.connect(direccion)
        try:
            while True:
                # Enviar mensaje:
                mensaje = input('> ')
                if mensaje:
                    enviar(socket_servidor, mensaje.encode(), _id)
                else:
                    # Cortar el chat si se ingresa un mensaje vacio.
                    print('Chat terminado')
                    break

                # Recibir mensaje:
                procesar(recibir(socket_servidor))
        except ConexionTerminadaExcepcion:
            print('Chat terminado')


def procesar(mensaje):
    longitud = int.from_bytes(mensaje[:1], 'big')
    _id = int.from_bytes(mensaje[1:5], 'big')
    timestamp = int.from_bytes(mensaje[5:9], 'big')
    texto = mensaje[9:].decode()

    tiempo = time.strftime('%H:%M:%S %z', time.localtime(timestamp))

    print('[{0}] ({1}) < {2}\n....Longitud: {3}'.format(_id,
                                                        tiempo,
                                                        texto,
                                                        longitud))


if __name__ == '__main__':

    # Parametros de la linea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csi:p:')
    except getopt.GetoptError as error:
        print('Error con el parámetro {0.opt}: {0.msg}'.format(error))
    else:
        # Parametros por defecto para host y puerto:
        host = 'localhost'
        port = 10000
        modo = ''

        for opt, arg in opts:
            if opt == '-c':  # Modo Cliente
                if modo == '':
                    modo = 'c'
                else:
                    print('Error... no se puede ser cliente y servidor al '
                          'mismo tiempo!')
                    sys.exit(1)
            elif opt == '-s':  # Modo Servidor
                if modo == '':
                    modo = 's'
                else:
                    print('Error... no se puede ser cliente y servidor al '
                          'mismo tiempo!')
                    sys.exit(1)
            elif opt == '-i':  # Direccion IP
                host = arg
            elif opt == '-p':  # Puerto
                port = int(arg)

        if modo == '':
            print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
        elif modo == 's':
            servidor((host, port))
        elif modo == 'c':
            cliente((host, port))
