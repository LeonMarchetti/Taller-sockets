# -*- coding: utf-8 -*-
"""
Servidor que usa la llamada al sistema select.
Fuente: https://pymotw.com/3/select/index.html
"""

import select
import socket
import queue


class SelectServer:
    def __init__(self, direccion, proceso):
        """
        Inicia el servidor.
        :param direccion: Par direccion IP y número de puerto asignado al
        servidor.
        :param proceso: Funcion que reciba bytes y regrese bytes, para ser
        ejecutado cada vez que el servidor este listo para procesar los datos
        de salida.
        """
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setblocking(0)
        self.server.bind(direccion)
        self.server.listen(5)
        print('Servidor escuchando en {}:{}...'.format(*direccion))

        self.inputs = [self.server]
        self.outputs = []
        self.message_queues = {}

        while self.inputs:
            readable, writable, exceptional = select.select(self.inputs,
                                                            self.outputs,
                                                            self.inputs)

            self._handle_inputs(readable)
            self._handle_outputs(writable, proceso)
            self._handle_exceptional(exceptional)

    def _handle_inputs(self, readable):
        for readable_socket in readable:
            if readable_socket is self.server:
                # A "readable" socket is ready to accept a connection
                connection, client_address = readable_socket.accept()
                print('Cliente conectado desde: {}:{}'.format(
                    *client_address))

                connection.setblocking(0)
                self.inputs.append(connection)

                # Give the connection a queue for data we want to send
                self.message_queues[connection] = queue.Queue()

            else:
                data = readable_socket.recv(1024)
                if data:
                    # A readable client socket has data
                    self.message_queues[readable_socket].put(data)

                    # Add output channel for response
                    if readable_socket not in self.outputs:
                        self.outputs.append(readable_socket)

                else:
                    # Interpret empty result as closed connection
                    # Stop listening for input on the connection
                    if readable_socket in self.outputs:
                        self.outputs.remove(readable_socket)

                    self.inputs.remove(readable_socket)
                    readable_socket.close()

                    # Remove message queue
                    del self.message_queues[readable_socket]

    def _handle_outputs(self, writable, proceso):
        for writable_socket in writable:
            try:
                next_msg = self.message_queues[writable_socket] \
                    .get_nowait()
            except queue.Empty:
                # No messages waiting so stop checking for writability.
                self.outputs.remove(writable_socket)
            except KeyError:
                pass
            else:
                # Ejecución de la función pasada por parámetro, que recibe la
                # direccion del socket remoto y los datos recibidos como
                # entrada y devuelve los datos a enviar como resultado.
                salida = proceso(writable_socket.getpeername(), next_msg)
                writable_socket.send(salida)

    def _handle_exceptional(self, exceptional):
        for exceptional_socket in exceptional:
            # Stop listening for input on the connection
            self.inputs.remove(exceptional_socket)
            if exceptional_socket in self.outputs:
                self.outputs.remove(exceptional_socket)
            exceptional_socket.close()

            # Remove message queue
            del self.message_queues[exceptional_socket]
