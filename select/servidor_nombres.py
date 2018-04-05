# _*_ coding: utf-8 _*_
"""
Parámetros:
* -s: Modo servidor
* -c: Modo cliente
* -i: Dirección IP (Opcional)
* -p: Número de puerto (Opcional)
* -n: Nombre a resolver
"""
import getopt
import platform
import select_server
import socket
import sys


BUFFER = 1024
cache = {}

# Obtengo el archivo de hosts según el sistema operativo:
if platform.system() == 'Windows':
    archivo_hosts = 'C:\\Windows\\System32\\drivers\\etc\\hosts'
elif platform.system() == 'Linux':
    archivo_hosts = '/etc/hosts'


# Comunicación ===============================================================
class ConexionTerminadaExcepcion(Exception):
    pass


def enviar(s, datos):
    while datos:
        enviado = s.send(datos)
        datos = datos[enviado:]


def recibir(s):
    cachos = b''
    while True:
        cacho = s.recv(BUFFER)
        if cacho:
            cachos += cacho
            if len(cachos) > 4:

                longitud = int.from_bytes(cachos[:4], byteorder='big')
                if len(cachos) >= longitud + 4:
                    return cachos[4:4 + longitud]
        else:
            raise ConexionTerminadaExcepcion


# Servidor ===================================================================
def iniciar_servidor(direccion):
    select_server.servidor(direccion, procesar)


def procesar(datos):
    return datos


# Cliente ====================================================================
def cliente(direccion):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(direccion)


# ============================================================================
if __name__ == '__main__':
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csi:p:n:')
    except getopt.GetoptError as error:
        print('Error con el parámetro {0.opt}: {0.msg}'.format(error))
    else:
        host = 'localhost'
        port = 2323
        modo = ''
        nombre = ''

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
            elif opt == '-n':
                nombre = arg

        if modo == '':
            print('Usar "-c" para modo Cliente y "-s" para modo Servidor')

        elif modo == 's':
            iniciar_servidor((host, port))
        elif modo == 'c':
            if nombre:
                cliente((host, port))
            else:
                print('Falta especificar nombre a resolver!')
