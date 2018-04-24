# -*- coding: utf-8 -*-
"""
Parámetros:
* -i: Dirección IP (Opcional)
* -p: Número de puerto (Opcional)
"""
import binascii
import getopt
import random
from select_server import SelectServer
import socket
import sys


class ServidorAnillo:
    # Número de puerto de los nodos reservado para el anillo.
    puerto = 8025
    # Nodos vecinos:
    nodo_izq = 1
    nodo_der = -1

    def __init__(self, direccion):
        # Estado inicial del servidor:
        self.id = 0
        # Nodos en el anillo:
        self.nodos = [(self.id, direccion)]  # Lista de tuplas (id, ip)

        # Inicio el servidor:
        SelectServer((direccion[0], ServidorAnillo.puerto), self._proceso)

    @staticmethod
    def _nodo_to_bytes(nodo):
        return nodo[0].to_bytes(1, 'big') + \
               socket.inet_aton(nodo[1][0]) + \
               nodo[1][1].to_bytes(2, 'big')

    def _proceso(self, direccion, datos):
        if datos == b'CON':
            # Generación de id único para el nuevo nodo:
            while True:
                nuevo_id = random.randint(1, 254)
                esta = False
                for nodo in self.nodos:
                    if nodo[0] == nuevo_id:
                        esta = True
                        break
                if not esta:
                    break

            nuevo_nodo = (nuevo_id, direccion)
            print('>>> Datos:\nid\t{}\naddr\t{}'.format(*nuevo_nodo))

            cantidad = len(self.nodos)
            nuevo_pos = len(self.nodos)

            lista_nodos = b''

            # Armo la lista de nodos para mandarle al nodo nuevo:
            for i in range(cantidad):
                nodo = self.nodos[i]

                # Agrego a cada nodo en la lista de la forma:
                # id(1) + ip(4) + puerto(2)
                lista_nodos += ServidorAnillo._nodo_to_bytes(nodo)

                # Ubico al nuevo nodo en la lista:
                if nodo[0] > nuevo_nodo[0] and nuevo_pos > i:
                    nuevo_pos = i

            # Agrego el nuevo nodo a la lista del servidor:
            self.nodos.insert(nuevo_pos, nuevo_nodo)

            self._show_nodos()

            confirmacion = (nuevo_id.to_bytes(1, 'big') +
                            cantidad.to_bytes(1, 'big') +
                            nuevo_pos.to_bytes(1, 'big') +
                            b' ' +
                            lista_nodos)

            print('>>> Confirmacion:\n{}'.format(
                binascii.hexlify(confirmacion).decode()))

            return confirmacion

        else:
            return b''

    def _show_nodos(self):
        print('>>> Nodos:\ni\tid\t(ip, puerto)')
        i = 0
        for nodo in self.nodos:
            print('{}\t{}\t{}'.format(i, *nodo))
            i += 1


if __name__ == '__main__':
    # Parámetros de la línea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'i:p:')
    except getopt.GetoptError as error:
        print('Error con el parámetro {0.opt}: {0.msg}'.format(error))
    else:
        # Parámetros por defecto para host y puerto:
        # host = 'localhost'
        host = '192.168.1.40'
        port = 10000

        for opt, arg in opts:
            if opt == '-i':  # Dirección IP
                host = arg
            elif opt == '-p':  # Puerto
                port = int(arg)

        ServidorAnillo((host, port))
