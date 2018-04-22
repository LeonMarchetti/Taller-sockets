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

    def __init__(self, direccion):
        self.id = 0
        self.nodos = [(self.id, direccion[0])]  # Lista de tuplas (id, ip)
        SelectServer((direccion[0], ServidorAnillo.puerto), self._proceso)

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

            print('>>> Datos:\nid\t{}\nip\t{}'.format(nuevo_id, direccion[0]))
            nuevo_nodo = (nuevo_id, direccion[0])

            cantidad = len(self.nodos)
            nuevo_pos = len(self.nodos)

            lista_nodos = b''

            for i in range(cantidad):
                nodo = self.nodos[i]
                lista_nodos += nodo[0].to_bytes(1, byteorder='big') + \
                               socket.inet_aton(nodo[1])

                if nodo[0] > nuevo_nodo[0] and nuevo_pos > i:
                    nuevo_pos = i

            self.nodos.insert(nuevo_pos, nuevo_nodo)

            confirmacion = (nuevo_id.to_bytes(1, byteorder='big') +
                            cantidad.to_bytes(1, byteorder='big') +
                            nuevo_pos.to_bytes(1, byteorder='big') +
                            b' ' +
                            lista_nodos)

            print('>>> Confirmacion:\n{}'.format(
                binascii.hexlify(confirmacion).decode()))

            print('>>> Nodos:\ni\tid\tip')
            i = 0
            for nodo in self.nodos:
                print('{}\t{}\t{}'.format(i, *nodo))
                i += 1

            print('')

            return confirmacion
        else:
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
