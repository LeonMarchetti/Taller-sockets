import getopt
import socket
import sys

# Parametros por defecto para host y puerto:
HOST    = 'localhost'
PORT    = 65000
BUFFER  = 1024

# Mensaje de tamano fijo:
TAM_MSG = 512
PADDING = b' '

def enviar(s, mensaje):
    b_mensaje = mensaje.encode().ljust(TAM_MSG, PADDING)

    total_enviado = 0
    while total_enviado < TAM_MSG:
        enviado = s.send(b_mensaje[total_enviado:])
        if enviado == 0:
            raise socket.error()
        total_enviado += enviado

def recibir(s):
    cachos = []
    bytes_recibidos = 0
    while bytes_recibidos < TAM_MSG:
        cacho = s.recv(BUFFER)
        if cacho == b'':
            raise socket.error()

        cachos.append(cacho.strip(PADDING))
        bytes_recibidos += len(cacho)

    return ''.join([cacho.decode() for cacho in cachos])

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
                        enviar(cliente, mensaje)
                    else:
                        # Cortar el chat si se ingresa un mensaje vacio.
                        break

            except socket.error:
                print('Chat terminado')
            finally:
                cliente.close()

def client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        try:
            while True:
                # Enviar mensaje:
                mensaje = input('> ')
                if mensaje:
                    enviar(s, mensaje)
                else:
                    # Cortar el chat si se ingresa un mensaje vacio.
                    break

                # Recibir mensaje:
                print('< ' + recibir(s))
        except socket.error:
            print('Chat terminado')

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
    # => for opt, arg in opts:

    if modo == '':
        print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
    elif modo == 's':
        server()
    elif modo == 'c':
        client()