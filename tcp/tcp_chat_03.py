# _*_ coding: utf-8 _*_
"""
Parámetros:
* -s: Modo servidor
* -c: Modo cliente
* -i: Dirección IP (Opcional)
* -p: Número de puerto (Opcional)

Estructura del mensaje:
 0 1     4 5     8 9
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|l|  id   |  ts   | mensaje |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

l: 1 byte
    Longitud del mensaje

id: 4 bytes
    Identificador del emisor.

ts: 4 bytes
    Timestamp del envío del mensaje.

mensaje: variable
    Mensaje.
"""
import getopt
import random
import socket
import sys
import time


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
            raise ConexionTerminadaExcepcion

        paquete = paquete[enviado:]


def recibir(s):
    paquetes = []
    cachos = b''
    while True:
        cacho = s.recv(1024)
        if cacho:
            cachos += cacho
            longitud = int.from_bytes(cachos[:1], 'big') + 9
            while len(cachos) >= longitud:
                # Si recibo más de un paquete almaceno el primero, lo saco de
                # los cachos y sigo recibiendo el próximo.
                paquetes.append(cachos[:longitud])
                cachos = cachos[longitud:]
                if not cachos:
                    return paquetes

                longitud = int.from_bytes(cachos[:1], 'big') + 9

        else:
            raise ConexionTerminadaExcepcion


def procesar(paquetes):
    # Parseo del/os paquetes:
    for paquete in paquetes:
        longitud = int.from_bytes(paquete[:1], 'big')
        _id = int.from_bytes(paquete[1:5], 'big')
        timestamp = int.from_bytes(paquete[5:9], 'big')
        mensaje = paquete[9:].decode()

        # Conversión de la hora:
        tiempo = time.strftime('%H:%M:%S %z', time.localtime(timestamp))

        print('[{0}] ({1}) < {2}\n....Longitud: {3}'.format(_id,
                                                            tiempo,
                                                            mensaje,
                                                            longitud))


def servidor(direccion):
    _id = 0
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_servidor:
        socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_servidor.bind(direccion)
        socket_servidor.listen(5)
        print('Escuchando en <{}:{}>'.format(direccion[0], direccion[1]))

        while True:  # Ciclo que acepta las conexiones (un cliente a la vez)
            print('--------------------')
            print('Esperando conexión...')
            socket_cliente, direccion = socket_servidor.accept()
            print('--------------------')
            print('Conexión establecida: <{}:{}>\n'.format(direccion[0],
                                                           direccion[1]))
            try:
                while True:
                    # Recibir mensaje/s:
                    procesar(recibir(socket_cliente))

                    # Enviar mensaje:
                    mensaje = input('> ')
                    if mensaje:
                        enviar(socket_cliente, mensaje.encode(), _id)

                    else:  # Cortar el chat si se ingresa un mensaje vacio:
                        print('Chat terminado')
                        break

            except ConexionTerminadaExcepcion:
                print('Chat terminado')

            finally:
                socket_cliente.close()


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

                else:  # Cortar el chat si se ingresa un mensaje vacío.
                    print('Chat terminado')
                    break

                # Recibir mensaje:
                procesar(recibir(socket_servidor))

        except ConexionTerminadaExcepcion:
            print('Chat terminado')


if __name__ == '__main__':
    # Parámetros de la línea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csi:p:')
    except getopt.GetoptError as error:
        print('Error con el parámetro {0.opt}: {0.msg}'.format(error))
    else:
        # Parámetros por defecto para host y puerto:
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
            elif opt == '-i':  # Dirección IP
                host = arg
            elif opt == '-p':  # Puerto
                port = int(arg)

        if modo == '':
            print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
        elif modo == 's':
            servidor((host, port))
        elif modo == 'c':
            cliente((host, port))
