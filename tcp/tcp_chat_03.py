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

# Parametros por defecto para host y puerto:
HOST     = 'localhost'
PORT     = 65000
BUFFER  = 1024
ID = 0

def enviar(s, mensaje, id):
    b_mensaje = mensaje.encode()

    b_longitud = len(b_mensaje).to_bytes(1, 'big')
    b_id = id.to_bytes(1, 'big')
    ts = round(time.time()).to_bytes(4, 'big')

    paquete = b_longitud + b_id + ts + b_mensaje
    while paquete:
        enviado = s.send(paquete)
        if enviado == 0:
            raise socket.error()
        paquete = paquete[enviado:]

def recibir(s):
    cachos = []
    while True:
        cacho = s.recv(BUFFER)
        cachos.append(cacho)
        if len(cacho) == 0: # Fin del chat.
            raise socket.error()
        if len(cacho) < BUFFER: # Ultimo cacho.
            break

    paquete = b''.join([cacho for cacho in cachos])

    longitud = int.from_bytes(paquete[0:1], 'big')
    id = int.from_bytes(paquete[1:2], 'big')
    ts = int.from_bytes(paquete[2:6], 'big')
    mensaje = paquete[6: 6+longitud]

    texto = '[id: {}|timestamp: {}]\n{}'.format(id, ts, mensaje.decode())

    if len(mensaje) > longitud:
        texto += '\nLlego un mensaje mas largo...'
    elif len(mensaje) < longitud:
        texto += '\nLlego un mensaje mas corto...'

    return texto

def server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)
        print('Escuchando en <{}:{}>'.format(HOST, PORT))

        while True: # Ciclo que acepta las conexiones (un cliente a la vez)
            print('Esperando conexion...')
            cliente, direccion = s.accept()
            print('Conexion establecida: <{}:{}>'.format(direccion[0], direccion[1]))
            try:
                while True:
                    # Recibir mensaje:
                    print('< ' + recibir(cliente))

                    # Enviar mensaje:
                    mensaje = input('> ')
                    if mensaje:
                        enviar(cliente, mensaje, 0)
                    else:
                        # Cortar el chat si se ingresa un mensaje vacio.
                        break
            except socket.error:
                pass
            finally:
                cliente.close()

def client():
    id = random.randint(1, 255)
    print('Cliente con id: "{}"'.format(id))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        try:
            while True:
                # Enviar mensaje:
                mensaje = input('> ')
                if mensaje:
                    enviar(s, mensaje, id)
                else:
                    # Cortar el chat si se ingresa un mensaje vacio.
                    break

                # Recibir mensaje:
                print('< ' + recibir(s))
        except socket.error:
            pass

if __name__ == '__main__':

    # Parametros de la linea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csi:p:')
    except getopt.GetoptError:
        print('Error con los parametros: ' + str(sys.argv))
        sys.exit(1)

    modo = ''

    for opt, arg in opts:
        if opt == '-c': # Modo Cliente
            if modo == '':
                modo = 'c'
            else:
                print('Error... no se puede ser cliente y servidor al mismo tiempo!')
        elif opt == '-s': # Modo Servidor
            if modo == '':
                modo = 's'
            else:
                print('Error... no se puede ser cliente y servidor al mismo tiempo!')
        elif opt == '-i': # Direccion IP
            HOST = arg
        elif opt == '-p': # Puerto
            PORT = int(arg)

    if modo == '':
        print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
    elif modo == 's':
        server()
    elif modo == 'c':
        client()
