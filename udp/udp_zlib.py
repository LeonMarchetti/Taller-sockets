# coding=utf-8
"""
Parámetros:
* -c    Modo cliente
* -s    Modo servidor
* -i    Dirección IP o nombre de host
* -p    Número de puerto
* -v    Verboso: Se muestran mensajes de control (cuando no sean errores)

PDU:
 0
 0       4 5
+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   CS  |T| Mensaje       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+
CS: 4 bytes
    Checksum del mensaje.
T: 1 byte
    Tamaño del mensaje.
Mensaje: Variable
    Mensaje comprimido.

"""

import getopt
import socket
import sys
import zlib

TAM_BUFFER = 1024
VERBOSE = False


def ingresar_mensaje():
    while True:
        texto = input('> ')

        if len(texto) >= TAM_BUFFER:
            print('Mensaje demasiado largo...')
        else:
            mensaje_comp = armar_mensaje(texto)
            if mensaje_comp:
                return mensaje_comp
            else:
                # Se pide el ingreso hasta que no haya errores:
                print('Ingrese otra vez el mensaje...')


def armar_mensaje(texto):
    # Comprimir mensaje:
    try:
        texto_bytes = texto.encode()
        mensaje_comp = zlib.compress(texto_bytes)
        tam_comp = len(mensaje_comp)

        # Calcular checksum del mensaje comprimido, y convertirlo en bytes:
        cs_crc = zlib.crc32(mensaje_comp)

        # Información de la transimisión:
        if VERBOSE:
            print(('Tamaño descomprimido: {0}' +
                   '\nTamaño comprimido:    {1}' +
                   '\nChecksum:             {2}'
                   ).format(len(texto_bytes), tam_comp, cs_crc))

        # Unir ambos en un string de bytes, usando un separador para separar
        # ambos valores:
        return cs_crc.to_bytes(4, 'big') \
            + tam_comp.to_bytes(1, 'big') \
            + mensaje_comp

    except zlib.error as error:
        print('Error al comprimir el mensaje: {}'.format(error))
        return b''


def mostrar_mensaje(datos):
    # Separo checksum, tamaño de mensaje y mensaje:
    checksum_int = int.from_bytes(datos[:4], 'big')
    tam_comp = int.from_bytes(datos[4:5], 'big')
    mensaje_comp = datos[5:]

    # Tamaño del mensaje comprimido medido en el receptor:
    tam_comp_local = len(mensaje_comp)

    # Comparar tamaño:
    if tam_comp < tam_comp_local:
        print(('Llegaron menos datos de los esperados...' +
               '\nEsperados: {0}' +
               '\nRecibidos: {1}'
               ).format(tam_comp, tam_comp_local))

    elif tam_comp > tam_comp_local:
        print(('Llegaron más datos de los esperados...' +
               '\nEsperados: {0}' +
               '\nRecibidos: {1}'
               ).format(tam_comp, tam_comp_local))

    elif tam_comp == tam_comp_local:
        # Comparar checksum:
        checksum = zlib.crc32(mensaje_comp)
        if checksum != checksum_int:
            print(('Error detectado a través del cálculo del checksum:' +
                   '\nchecksum recibido:  {0}' +
                   '\nchecksum calculado: {1}')
                  .format(checksum_int, checksum))
        else:
            try:
                mensaje = zlib.decompress(mensaje_comp)
                print('< ' + mensaje.decode())

                # Información de la transmisión:
                if VERBOSE:
                    print(('Tamaño descomprimido: {0}' +
                           '\nTamaño comprimido:    {1}'
                           ).format(len(mensaje), tam_comp))

            except zlib.error as error:
                print('Error al descomprimir el mensaje: {}'.format(error))


def server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as servidor:
        servidor.bind((host, port))
        print('Escuchando en: <{}:{}>'.format(host, port))
        try:
            while True:
                # Recibir mensaje del cliente:
                datos_in, cliente = servidor.recvfrom(TAM_BUFFER)

                mostrar_mensaje(datos_in)

                # Enviar mensaje al cliente:
                datos_out = ingresar_mensaje()
                servidor.sendto(datos_out, cliente)
        except KeyboardInterrupt:
            pass


def client(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cliente:
        try:
            while True:
                # Enviar mensaje a cliente:
                datos_out = ingresar_mensaje()
                cliente.sendto(datos_out, (host, port))

                # Recibir mensaje del servidor:
                datos_in, _ = cliente.recvfrom(TAM_BUFFER)
                mostrar_mensaje(datos_in)
        except KeyboardInterrupt:
            pass


def main(argv):
    # Parámetros de la línea de comandos:
    try:
        opts, _ = getopt.getopt(argv[1:], 'csi:p:v')
    except getopt.GetoptError:
        print('Error con los parámetros: ' + str(argv))
        return

    # Valores por defecto para host y puerto:
    host = 'localhost'
    port = 65000
    modo = ''  # modo Cliente o Servidor

    for opt, arg in opts:
        if opt == '-c':  # Modo Cliente
            if modo == '':
                modo = 'c'
            else:
                print('Error... no se puede ser cliente y servidor al mismo '
                      'tiempo!')
                return
        elif opt == '-s':  # Modo Servidor
            if modo == '':
                modo = 's'
            else:
                print('Error... no se puede ser cliente y servidor al mismo '
                      'tiempo!')
                return
        elif opt == '-i':  # Dirección IP
            host = arg
        elif opt == '-p':  # Puerto
            port = int(arg)
        elif opt == '-v':  # Verboso
            global VERBOSE
            VERBOSE = True

    if modo == '':
        print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
    elif modo == 's':
        server(host, port)
    elif modo == 'c':
        client(host, port)


if __name__ == '__main__':
    main(sys.argv)
