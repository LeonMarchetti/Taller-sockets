# _*_ coding: utf-8 _*_
"""
Parámetros:
* -s: Modo servidor
* -c: Modo cliente
* -i: Dirección IP (Opcional)
* -p: Número de puerto (Opcional)
* -q: Archivo sql (Opcional)
"""
import getopt
import socket
import sys

# Parametros por defecto para host y puerto:
BUFFER = 1024

# Mensaje de tamano fijo:
TAM_MSG = 512
PADDING = b' '


# Comunicación ===============================================================
class ConexionTerminadaExcepcion(Exception):
    pass


def enviar(s, mensaje):
    b_mensaje = mensaje.ljust(TAM_MSG, PADDING)

    total_enviado = 0
    while total_enviado < TAM_MSG:
        enviado = s.send(b_mensaje[total_enviado:])
        if enviado == 0:
            raise ConexionTerminadaExcepcion
        total_enviado += enviado


def enviar_chat(s):
    mensaje = input('> ')

    if mensaje:
        enviar(s, mensaje.encode().ljust(TAM_MSG, PADDING))

    else:
        # Cortar el chat si se ingresa un mensaje vacio.
        raise ConexionTerminadaExcepcion


def recibir(s):
    cachos = b''
    bytes_recibidos = 0

    # while bytes_recibidos < TAM_MSG:
    #     cacho = s.recv(BUFFER)
    #     if cacho == b'':
    #         raise ConexionTerminadaExcepcion
    #
    #     cachos.append(cacho.strip(PADDING))
    #     bytes_recibidos += len(cacho)

    while bytes_recibidos != TAM_MSG:
        try:
            print('Esperando:')
            cacho = s.recv(BUFFER)
            if not cacho:
                # raise socket.error
                raise ConexionTerminadaExcepcion

            cachos += cacho
            bytes_recibidos += len(cacho)
            print(f'Recibidos: {len(cacho)} bytes.')

            if bytes_recibidos > TAM_MSG:
                # Si recibo más bytes que un solo mensaje, empiezo a contar
                # los bytes del siguiente mensaje y sigo recibiendo.
                bytes_recibidos -= TAM_MSG

        except socket.timeout:
            print('Timeout')

    return cachos.strip(PADDING)


def recibir_chat(s):
    print('< ' + recibir(s).decode())


# Servidor ===================================================================
def server(direccion):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_servidor:

        socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_servidor.bind(direccion)
        socket_servidor.listen(5)
        # socket_servidor.settimeout(0.5)
        print('Escuchando en <{}:{}>'.format(direccion[0], direccion[1]))

        while True:  # Ciclo que acepta las conexiones (un cliente a la vez)
            print('Esperando conexion...')
            socket_cliente, direccion = socket_servidor.accept()
            # socket_cliente.settimeout(0.5)
            print('Conexion establecida: <{}:{}>'.format(direccion[0],
                                                         direccion[1]))
            try:
                while True:
                    recibir_chat(socket_cliente)
                    # enviar_chat(socket_servidor)
                    enviar_chat(socket_cliente)

            # except socket.error:
            except ConexionTerminadaExcepcion:
                print('Chat terminado')

            finally:
                socket_cliente.close()


# Cliente ====================================================================
def client(direccion):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_servidor:
        # socket_servidor.settimeout(0.5)
        socket_servidor.connect(direccion)
        try:
            while True:
                # if not enviar_chat(socket_servidor):
                #     break
                enviar_chat(socket_servidor)
                recibir_chat(socket_servidor)

        # except socket.error:
        except ConexionTerminadaExcepcion:
            print('Chat terminado')


# ============================================================================
if __name__ == '__main__':
    # Parámetros de la línea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csi:p:')
    except getopt.GetoptError as error:
        print('Error con el parámetro {0.opt}: {0.msg}'.format(error))
    else:
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
            server((host, port))
        elif modo == 'c':
            client((host, port))
