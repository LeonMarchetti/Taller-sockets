# -*- coding: utf-8 -*-
"""
Parámetros:
* -i: Dirección IP (Opcional)
* -p: Número de puerto (Opcional)
"""
import getopt
# import os
# from select_server import SelectServer
import socket
import sys


class ConexionTerminadaExcepcion(Exception):
    pass


class NodoAnillo:
    # Número de puerto de los nodos reservado para el anillo.
    puerto = 8025
    id_bcast = 255
    token_vacio = b'\x00\x00\x00\x00'

    def __init__(self, servidor_addr):
        # Lista de los nodos en la topología. Cada nodo lo representa una
        # tupla (id, dirección ip)
        self.nodos = []

        # Solicito conectarme al anillo:
        with socket.socket() as socket_servidor:
            socket_servidor.connect(servidor_addr)
            self.direccion = socket_servidor.getsockname()
            try:
                socket_servidor.sendall(b'CON')
                paquete = NodoAnillo._recibir_confirmacion(socket_servidor)
            except ConexionTerminadaExcepcion:
                print('Error: Conexión rechazada.')
                return

        self._procesar_confirmacion(paquete)
        self._atender_anillo()

    def _atender_anillo(self):
        with socket.socket() as self.socket:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(self.direccion)
            self.socket.listen(5)

            salir = False
            while True:
                socket_entrada, direccion = self.socket.accept()
                addr_entrada = socket_entrada.getpeername()
                print('Conexión entrante\t{}'.format(addr_entrada))

                # Determino si la conexión es de alguno de los vecinos del
                # nodo:
                if addr_entrada == self.nodos[self.nodo_izq][1]:
                    print('Conexión desde el vecino izquierdo')
                    addr_salida = self.nodos[self.nodo_der][1]
                elif addr_entrada == self.nodos[self.nodo_der][1]:
                    print('Conexión desde el vecino derecho')
                    addr_salida = self.nodos[self.nodo_izq][1]
                else:
                    print('Conexión desde un host fuera del anillo...')
                    addr_salida = None

                # Si hay una dirección de salida procedo a pasar el token:
                if addr_salida:
                    try:
                        token = NodoAnillo._recibir_token(socket_entrada)
                    except ConexionTerminadaExcepcion:
                        print('Conexión terminada')
                    else:
                        info_token = NodoAnillo._parsear_token(token)

                        if info_token[0] == 0 and info_token[1] == 0:
                            # Token vacío
                            token_salida = self._armar_mensaje()
                        elif info_token[0] == 0 and info_token[1] == 255:
                            # Token de cierre del anillo:
                            token_salida = token
                            salir = True
                        elif info_token[1] == self.id:
                            # Si soy el receptor entonces extraigo el mensaje y
                            # vacío el token:
                            print('De <{0}>:\n{1}'.format(info_token[0],
                                                          info_token[3]))
                            token_salida = self._armar_mensaje()
                        elif info_token[1] == 255:
                            # Si llega un token con el id 255 de broadcast:
                            print('De <{0}>:\n{1}'.format(info_token[0],
                                                          info_token[3]))
                            if info_token[0] == self.id:
                                # El token de broadcast vuelve al origen y se
                                # elimina:
                                token_salida = self._armar_mensaje()
                            else:
                                # Se repropaga el token de broadcast si el nodo
                                # no es el que lo envío:
                                token_salida = token
                        else:
                            # Si no soy el receptor paso el token como vino:
                            token_salida = token

                        # Envío el token:
                        with socket.socket() as socket_salida:
                            try:
                                socket_salida.connect(addr_salida)
                            except TimeoutError:
                                # El siguiente nodo no responde por lo que se
                                # envía al servidor el token avisando que saque
                                # el nodo del anillo.
                                pass
                            else:
                                try:
                                    socket_salida.sendall(token_salida)
                                    if socket_salida.recv(5) == 'OK':
                                        print('Token pasado con éxito.')
                                    else:
                                        print('Error')
                                except ConexionTerminadaExcepcion:
                                    print('Conexión terminada')

                        if salir:
                            break

                socket_entrada.close()

    def _armar_mensaje(self):
        while True:
            try:
                str_input = input('Para > ')
                if str_input:
                    id_destino = int(str_input)
                    if (id_destino not in range(0, 256)) or \
                            not (self._id_existe(id_destino)):
                        raise ValueError
                else:
                    # Si se ingresa un id vacío entonces dejo pasar el token:
                    return NodoAnillo.token_vacio
            except ValueError:
                continue
            else:
                break

        mensaje = input('> ').encode()

        # Armar token:
        return self.id.to_bytes(1, 'big') + \
            id_destino.to_bytes(1, 'big') + \
            len(mensaje).to_bytes(2, 'big') + \
            mensaje

    def _id_existe(self, _id):
        if _id == self.id:
            return True
        for nodo in self.nodos:
            if nodo[0] == _id:
                return True
        return False

    @staticmethod
    def _parsear_token(token):
        id_origen = int.from_bytes(token[:1], 'big')
        id_receptor = int.from_bytes(token[1:2], 'big')
        longitud = int.from_bytes(token[2:4], 'big')
        mensaje = token[4:4 + longitud].decode()

        return id_origen, id_receptor, longitud, mensaje

    def _procesar_confirmacion(self, datos):
        self.id = int.from_bytes(datos[:1], byteorder='big')
        cant_nodos = int.from_bytes(datos[1:2], byteorder='big')
        self.pos = int.from_bytes(datos[2:3], byteorder='big')

        print('>>> Datos\nid\t{0}\npos\t{1}'.format(self.id, self.pos))

        # Lleno la lista de nodos:
        # * En esta lista (propia del nodo) no se incluye al propio nodo.
        print('>>> Nodos:\ni\tid\t(ip, puerto)')
        for i in range(cant_nodos):
            offset = 4 + 7 * i
            id_nodo = int.from_bytes(datos[offset:offset + 1], byteorder='big')
            addr_nodo = (socket.inet_ntoa(datos[offset + 1:offset + 5]),
                         int.from_bytes(datos[offset + 5:offset + 7],
                                        byteorder='big'))
            print('{0}\t{1}\t{2}'.format(i, id_nodo, addr_nodo))
            self.nodos.append((id_nodo, addr_nodo))

        # Determino quienes son los nodos vecinos:
        print('>>> Vecinos:\n\ti\tid\t(ip, puerto)')
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
                        longitud = 4 + 7 * int.from_bytes(cachos[1:2], 'big')
                    else:
                        continue
                if len(cachos) >= longitud:
                    break
            else:
                raise ConexionTerminadaExcepcion
        return cachos

    @staticmethod
    def _recibir_token(s):
        cachos = b''
        longitud = None  # Longitud total del paquete
        while True:
            cacho = s.recv(1024)
            if cacho:
                cachos += cacho
                if not longitud:
                    if len(cachos) >= 4:
                        longitud = 4 + int.from_bytes(cachos[2:4], 'big')
                    else:
                        continue
                if len(cachos) >= longitud:
                    break
            else:
                raise ConexionTerminadaExcepcion
        return cachos


if __name__ == '__main__':
    # Parámetros de la línea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'i:p:')
    except getopt.GetoptError as error:
        print('Error con el parámetro {0.opt}: {0.msg}'.format(error))
    else:
        # Parámetros por defecto para host y puerto:
        host = '192.168.1.40'
        port = 8025

        for opt, arg in opts:
            if opt == '-i':  # Dirección IP
                host = arg
            elif opt == '-p':  # Puerto
                port = int(arg)

        NodoAnillo((host, port))
