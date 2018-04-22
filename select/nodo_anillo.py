# -*- coding: utf-8 -*-
"""
Parámetros:
* -i: Dirección IP (Opcional)
* -p: Número de puerto (Opcional)
"""
import getopt
import os
from select_server import SelectServer
import socket
import sys


class ConexionTerminadaExcepcion(Exception):
    pass


class NodoAnillo:
    # Número de puerto de los nodos reservado para el anillo.
    puerto = 8025
    id_bcast = (255).to_bytes(1, byteorder='big')

    def __init__(self, servidor_addr):
        # Lista de los nodos en la topología. Cada nodo lo representa una
        # tupla (id, dirección ip)
        self.nodos = []

        # Solicito conectarme al anillo:
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
        # SelectServer((self.direccion, NodoAnillo.puerto),
        #              self._procesar_token)

    def _procesar_confirmacion(self, datos):
        self.id = int.from_bytes(datos[:1], byteorder='big')
        cant_nodos = int.from_bytes(datos[1:2], byteorder='big')
        self.pos = int.from_bytes(datos[2:3], byteorder='big')

        print('>>> Datos\nid\t{0}\npos\t{1}'.format(self.id, self.pos))

        # Lleno la lista de nodos:
        # * En esta lista (propia del nodo) no se incluye al propio nodo.
        print('>>> Nodos:\ni\tid\tip')
        for i in range(cant_nodos):
            offset = 4 + 5 * i
            id_nodo = int.from_bytes(datos[offset:offset + 1], byteorder='big')
            ip_nodo = socket.inet_ntoa(datos[offset + 1:offset + 5])
            print('[{0}]\t{1}\t{2}'.format(i, id_nodo, ip_nodo))
            self.nodos.append((id_nodo, ip_nodo))

        # Determino quienes son los nodos vecinos:
        print('>>> Vecinos:\n\ti\tid\tip')
        self.nodo_izq = (self.pos - 1) % len(self.nodos)
        self.nodo_der = self.pos % len(self.nodos)

        print('Izq\t{}\t{}\t{}'.format(self.nodo_izq, *self.nodos[
            self.nodo_izq]))
        print('Der\t{}\t{}\t{}'.format(self.nodo_der, *self.nodos[
            self.nodo_der]))

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
                        longitud = 4 + 5 * int.from_bytes(cachos[1:2],
                                                          byteorder='big')
                    else:
                        continue
                if len(cachos) >= longitud:
                    break
            else:
                raise ConexionTerminadaExcepcion
        return cachos

    def _procesar_token(self, direccion, token):
        id_receptor = int.from_bytes(token[1:2], byteorder='big')
        if id_receptor == self.id:
            id_origen = int.from_bytes(token[:1], byteorder='big')
            longitud = int.from_bytes(token[3:4], byteorder='big')
            mensaje = token[4:4+longitud].decode()
            print('De: <{}>\n{}\n'.format(id_origen, mensaje))

            # token_vacio =
        else:
            pass

        return b'OK'


if __name__ == '__main__':
    # Parámetros de la línea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'i:p:')
    except getopt.GetoptError as error:
        print('Error con el parámetro {0.opt}: {0.msg}'.format(error))
    else:
        # Parámetros por defecto para host y puerto:
        host = 'localhost'
        port = 8025

        for opt, arg in opts:
            if opt == '-i':  # Dirección IP
                host = arg
            elif opt == '-p':  # Puerto
                port = int(arg)

        NodoAnillo((host, port))
