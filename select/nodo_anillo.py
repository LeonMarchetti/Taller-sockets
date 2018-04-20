# -*- coding: utf-8 -*-
"""
Parámetros:
* -i: Dirección IP (Opcional)
* -p: Número de puerto (Opcional)
"""
import getopt
import os
import socket
import sys


class ConexionTerminadaExcepcion(Exception):
    pass


class NodoAnillo:
    # Número de puerto de los nodos reservado para el anillo.
    puerto = 8025

    def __init__(self, servidor_addr):
        # Lista de los nodos en la topología. Cada nodo lo representa una
        # tupla (id, dirección ip)
        self.nodos = []

        with socket.socket(socket.AF_INET,
                           socket.SOCK_STREAM) as socket_servidor:
            socket_servidor.connect(servidor_addr)
            self.direccion = socket_servidor.getsockname()[0]
            try:
                socket_servidor.sendall(b'CON')
                paquete = NodoAnillo._recibir_confirmacion(socket_servidor)
            except ConexionTerminadaExcepcion:
                print('Error: Conexión rechazada.')
                return

        self._procesar_confirmacion(paquete)

        pid = os.fork()
        if pid == 0:
            # TODO Proceso hijo del nodo.
            # Abro el socket para unirme al anillo:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM)\
                    as self.socket_escucha:
                self.socket_escucha.bind((self.direccion, NodoAnillo.puerto))
                self.socket_escucha.listen(5)
                try:
                    while True:
                        # Recibir mensaje/s:
                        token = self._recibir_token()
                        
                except ConexionTerminadaExcepcion:
                    print('Conexión terminada')
                    return

        else:
            # TODO Proceso original del nodo.
            pass
        # =====================================================================

    def _procesar_confirmacion(self, datos):
        self.id = int.from_bytes(datos[:1], byteorder='big')
        cant_nodos = int.from_bytes(datos[1:2], byteorder='big')
        self.pos = int.from_bytes(datos[2:3], byteorder='big')

        print(f'Info nodo:\nid: {self.id}\npos: {self.pos}\n'
              f'total nodos: {cant_nodos}\n')

        for i in range(cant_nodos):
            # offset = 4 * (i + 1)
            # self.nodos.append((
            #     socket.inet_ntoa(datos[offset:offset + 4]),
            #    int.from_bytes(datos[offset + 4:offset + 6], byteorder='big'),
            #     int.from_bytes(datos[offset + 6:offset + 7], byteorder='big')
            # ))
            offset = 4 + 5 * i
            self.nodos.append((
                socket.inet_ntoa(datos[offset:offset + 4]),
                int.from_bytes(datos[offset + 4:offset + 5], byteorder='big')
            ))

    @staticmethod
    def _recibir_confirmacion(s):
        cachos = b''
        longitud = None  # Longitud total del paquete
        while True:
            cacho = s.recv(1024)
            if cacho:
                cachos += cacho
                if not longitud:
                    if len(cachos) >= 4:
                        longitud = 4 + 8 * int.from_bytes(cachos[8:16],
                                                          byteorder='big')
                    else:
                        continue
                if len(cachos) >= longitud:
                    break
            else:
                raise ConexionTerminadaExcepcion
        return cachos

    def _recibir_token(self):
        tokens = []
        cachos = b''
        longitud = None
        while True:
            cacho = self.socket_escucha.recv(1024)
            if cacho:
                cachos += cacho
                if not longitud:
                    if len(cachos) >= 4:
                        longitud = 4 + int.from_bytes(cachos[3:4],
                                                      byteorder='big')
                    else:
                        continue

                while len(cachos) >= longitud:
                    tokens.append(cachos[:longitud])
                    cachos = cachos[longitud:]

                    if not cachos:
                        return tokens
            else:
                raise ConexionTerminadaExcepcion
        return tokens


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

        NodoAnillo((host, port))