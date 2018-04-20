# -*- coding: utf-8 -*-
"""
Parámetros:
* -i: Dirección IP (Opcional)
* -p: Número de puerto (Opcional)
"""
import getopt
import os
from select_server import SelectServer
import sys


_id = 0  # id del servidor
lista_nodos = []


class ServidorAnillo:
    def __init__(self, direccion):
        pid = os.fork()
        if pid == 0:
            # El proceso original atiende las solicitudes de conexión
            # select_server.servidor(direccion, self._atender_conexiones)
            SelectServer(direccion, self._atender_conexiones)
        else:
            # El proceso hijo forma parte del anillo
            SelectServer((direccion[0], 0), self._escuchar_anillo)

    def _atender_conexiones(self, socket, datos):
        return datos

    def _escuchar_anillo(self, socket, datos):
        return datos


if __name__ == '__main__':
    # Parámetros de la línea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'i:p:')
    except getopt.GetoptError as error:
        print('Error con el parámetro {0.opt}: {0.msg}'.format(error))
    else:
        # Parámetros por defecto para host y puerto:
        host = 'localhost'
        port = 10000

        for opt, arg in opts:
            if opt == '-i':  # Dirección IP
                host = arg
            elif opt == '-p':  # Puerto
                port = int(arg)

        ServidorAnillo((host, port))
